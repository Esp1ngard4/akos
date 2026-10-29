#!/usr/bin/env python3
"""End-to-end smoke test for every tool this repository publishes.

Usage:
    python tests/smoke_test.py              # test the working tree
    python tests/smoke_test.py --packaged   # test what git actually ships
    python tests/smoke_test.py --keep       # leave the scratch directory behind

Each tool is exercised the way a new user would: create a register, render its
dashboard, and check the output is real rather than merely present.

--packaged is the mode that matters. It exports `git archive HEAD` into a scratch
directory and runs the tools from there, so anything not committed is simply
absent. A working-tree run passes happily while a file sits untracked on disk;
that exact gap shipped a tool whose dashboard template had never been committed,
and every clone failed on first use. CI always runs --packaged.

Exits non-zero on the first failure, with the command and its output.
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every tool, and the assets it must ship for a clean checkout to work.
TOOLS = [
    {
        "name": "TSP.1 WBS Register",
        "skill": "TSP/TSP.1 WBS Register/wbs-manager",
        "assets": [],
        "register": "WBS Demo.json",
        "dashboard": "WBS Dashboard.html",
        # key_deliverables stopped being a collection when deliverables became
        # a view of items; sprints is the imported cadence calendar.
        "collections": ["items", "sprints"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_wbs.py"), r, "Demo"],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_wbs.py"), r, d, "Demo"],
    },
    {
        "name": "TSP.2 RAID Register",
        "skill": "TSP/TSP.2 RAID Register/raid-manager",
        "assets": [],
        "register": "RAID Demo.json",
        "dashboard": "RAID Dashboard.html",
        "collections": ["entries"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_raid.py"), r, "Demo"],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_raid.py"), r, d, "Demo"],
    },
    {
        "name": "TSP.3 TSP Register",
        "skill": "TSP/TSP.3 TSP Register/tsp-manager",
        "assets": [os.path.join("templates", "dashboard.html")],
        "register": "TSP Register.json",
        "dashboard": "TSP Dashboard.html",
        "collections": ["tools", "control_activities", "activity_log",
                        "change_log"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_tsp.py"), r],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_tsp.py"), r,
                                    "--out", d],
        "audit": lambda s, r: [os.path.join(s, "scripts", "audit_tsp.py"), r,
                               "--tools-root", os.path.dirname(r) or ".",
                               "--skills", os.path.dirname(r) or "."],
    },
    {
        "name": "TSP.5 Artifact Register",
        "skill": "TSP/TSP.5 Artifact Register/artifact-register",
        "assets": [],
        "register": "05. Artifact Register, Demo.json",
        "dashboard": "Artifact Dashboard.html",
        "collections": ["artifacts", "locations", "areas_of_focus"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_artifact_register.py"),
                                   r, "Demo"],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_artifact_register.py"),
                                    r, d, "--scope", "Demo"],
        "audit": lambda s, r: [os.path.join(s, "scripts", "audit_artifact_register.py"), r],
    },
    {
        "name": "TSP.13 Stakeholder Register",
        "skill": "TSP/TSP.13 Stakeholder Register/stakeholder-manager",
        "assets": [os.path.join("templates", "dashboard.html"),
                   os.path.join("examples", "Stakeholders Atlas.json")],
        "register": "Stakeholders Demo.json",
        "dashboard": "Stakeholder Dashboard.html",
        "collections": ["groups", "stakeholders", "communications", "change_log"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_stk.py"),
                                   os.path.dirname(r), "--scope", "Demo"],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_stk.py"), r, "--out", d],
    },
]

MIN_DASHBOARD_BYTES = 5000
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
failures = []


def check(label, ok, detail=""):
    print("  %-52s %s" % (label, "PASS" if ok else "FAIL"))
    if not ok:
        failures.append("%s%s" % (label, "\n      " + detail if detail else ""))
    return ok


def run_raw(cmd, cwd):
    """Run a script with the current interpreter. Returns (ok, combined output)."""
    proc = subprocess.run([sys.executable] + cmd, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode == 0, proc.stdout.decode("utf-8", "replace").strip()


GATE = "so this is a pull-in or work outside the sprint"


def run(cmd, cwd):
    """run_raw, answering the WBS pull-in gate as a user would when it asks.

    The gate asks only while a sprint in a register's calendar runs today, so
    whether a test's `set --status Implementing` is asked depends on the date
    the test runs. Tests not about the gate answer it here and stay date-proof;
    test_pull_ins drives it with run_raw."""
    ok, out = run_raw(cmd, cwd)
    if not ok and GATE in out:
        ok, out = run_raw(cmd + ["--outside-sprint", "smoke test: not about the sprint"], cwd)
    return ok, out


def export_head(dest):
    """Export exactly what git tracks at HEAD - untracked files do not appear."""
    os.makedirs(dest, exist_ok=True)
    archive = os.path.join(dest, "_head.tar")
    subprocess.check_call(["git", "archive", "HEAD", "--format=tar", "-o", archive],
                          cwd=REPO)
    with tarfile.open(archive) as tar:
        tar.extractall(dest)
    os.remove(archive)
    # install.py addresses versions by commit, so the exported tree has to be a
    # repository for it to be testable here. -f because the extracted .gitignore
    # would otherwise drop the shipped .xlsx and .html assets on the way back in.
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.check_call(["git", "init", "-q", "."], cwd=dest, **quiet)
    subprocess.check_call(["git", "add", "-A", "-f", "."], cwd=dest, **quiet)
    subprocess.check_call(["git", "-c", "user.email=smoke@test",
                           "-c", "user.name=smoke", "commit", "-qm", "packaged"],
                          cwd=dest, **quiet)
    return dest


def test_tool(tool, root, work):
    print("\n%s" % tool["name"])
    skill = os.path.join(root, tool["skill"])

    if not check("skill folder present", os.path.isdir(skill), skill):
        return
    check("SKILL.md present", os.path.isfile(os.path.join(skill, "SKILL.md")))

    for asset in tool["assets"]:
        path = os.path.join(skill, asset)
        check("ships asset: %s" % asset, os.path.isfile(path), path)

    register = os.path.join(work, tool["register"])
    ok, out = run(tool["create"](skill, register, ""), work)
    if not check("create runs", ok, out):
        return
    if not check("register created", os.path.isfile(register), register):
        return

    try:
        import json
        data = json.load(io.open(register, encoding="utf-8"))
        missing = [c for c in tool["collections"] if c not in data]
        check("expected collections present", not missing,
              "missing %s; found %s" % (missing, sorted(data)))
        check("register carries a values_hash",
              bool(data.get("meta", {}).get("values_hash")), str(data.get("meta")))
    except Exception as exc:                                  # noqa: BLE001
        check("register parses as JSON", False, str(exc))
        return

    dashboard = os.path.join(work, tool["dashboard"])
    ok, out = run(tool["refresh"](skill, register, dashboard), work)
    if not check("refresh runs", ok, out):
        return
    if not check("dashboard created", os.path.isfile(dashboard), dashboard):
        return

    html = io.open(dashboard, encoding="utf-8").read()
    # The view must record which data it was built from, or nothing can tell
    # that it has gone stale - and the edit commands do not regenerate it.
    check("dashboard stamps the register hash it was built from",
          'data-values-hash="sha256:' in html,
          html[:400])
    check("dashboard is non-trivial (>%dB)" % MIN_DASHBOARD_BYTES,
          len(html) > MIN_DASHBOARD_BYTES, "got %d bytes" % len(html))
    # A template that loads but never substitutes still produces a file. It would
    # pass a "does it exist" check and render a broken page.
    check("no unfilled {{PLACEHOLDER}}", "{{" not in html,
          "found: %s" % html[html.find("{{"):html.find("{{") + 40] if "{{" in html else "")

    if "audit" in tool:
        ok, out = run(tool["audit"](skill, register), work)
        check("audit runs clean", ok, out)


def test_init(root, scratch):
    """A new project from the project pack: every skill in the project-management
    folder, a tool register with each tool's TD, the registers made by their own
    tools, stakeholders in a confidential folder out of git, a workspace per
    profile; and a second init refused."""
    print("\ninstall.py init")
    installer = os.path.join(root, "install.py")
    with io.open(os.path.join(root, "packs", "project.json"), encoding="utf-8") as fh:
        pack = json.load(fh)
    project = os.path.join(scratch, "greenfield")
    ok, out = run([installer, "init", project, "--name", "Greenfield", "--first-day", "2026-11-02",
                   "--catalogue", root, "--source", root], root)
    if not check("init runs on an empty folder", ok, out[-600:]):
        return
    plan = os.path.join(project, "00. PrjMgm")
    check("the top folders numbered 00 to 03: PrjMgm, Execution, General Ref Materials and its Workspaces",
          all(os.path.isdir(p) for p in (plan, os.path.join(project, "01. Execution"),
                                         os.path.join(project, "02. General Ref Materials", "03. Workspaces"))),
          sorted(os.listdir(project)))
    with io.open(os.path.join(project, "tools.lock.json"), encoding="utf-8") as fh:
        root_lock = json.load(fh)
    check("at the root, the team's tools only, with their own lock",
          sorted(root_lock["tools"]) == sorted(pack["team_skills"]) and not os.path.exists(os.path.join(project, ".agents", "skills", "wbs-manager")),
          sorted(root_lock["tools"]))
    with io.open(os.path.join(plan, "tools.lock.json"), encoding="utf-8") as fh:
        lock = json.load(fh)
    check("every skill in the pack installed and locked in the project-management folder",
          all(s in lock["tools"] for s in pack["skills"]) and "action-tracker-manager" not in lock["tools"],
          sorted(set(pack["skills"]) - set(lock["tools"])))
    top = sorted(os.listdir(plan))
    want = ["04. Artifact Register", "05. TSP", "06. WBS", "07. RAID", "08. Sprints", "09. Comms", "10. Reports",
            "11. Onboarding", "12. Confidential", "14. Change Requests", "15. Project Brief.md"]
    check("the project-management folder continues the sequence", all(w in top for w in want), top)
    tsp = os.path.join(plan, "05. TSP", "TSP Register Greenfield.json")
    with io.open(tsp, encoding="utf-8") as fh:
        tools = json.load(fh)["tools"]
    check("the tool register numbers the tools itself and names each one's AKOS tool",
          [t["ID"] for t in tools] == list(range(1, len(tools) + 1)) and all(t.get("Upstream", "").startswith("AKOS TSP.") for t in tools)
          and any(t["Upstream"] == "AKOS TSP.15" and t["Skill"] == "status-board-manager" for t in tools), tools[:2])
    check("each tool's TD in the register's folder, and locked",
          all(t.get("Doc Aux") == "Yes" and os.path.isfile(os.path.join(plan, "05. TSP", t["Links"])) for t in tools)
          and all(("%s docs" % t["Upstream"].split()[1]) in lock["tools"] for t in tools), [t.get("Links") for t in tools][:2])
    wbs = os.path.join(plan, "06. WBS", "WBS Greenfield.json")
    with io.open(wbs, encoding="utf-8") as fh:
        data = json.load(fh)
    sprints = data.get("sprints") or []
    check("a WBS with a sprint calendar from the first day", sprints and sprints[0]["Starts"] <= "2026-11-02" <= sprints[-1]["Ends"], len(sprints))
    check("the WBS declares the execution folder", (data["meta"].get("execution") or {}).get("folder") == "../../01. Execution")
    check("the stakeholder register in Confidential/Stakeholder Mgm",
          os.path.isfile(os.path.join(plan, "12. Confidential", "13. Stakeholder Mgm", "Stakeholders Greenfield.json")))
    with io.open(os.path.join(project, ".gitignore"), encoding="utf-8") as fh:
        check("the confidential folder kept out of git", "00. PrjMgm/12. Confidential/" in fh.read().split("\n"))
    ws = os.path.join(project, "02. General Ref Materials", "03. Workspaces")
    with io.open(os.path.join(ws, "Product manager.code-workspace"), encoding="utf-8") as fh:
        pm = [f["path"] for f in json.load(fh)["folders"]]
    with io.open(os.path.join(ws, "Team.code-workspace"), encoding="utf-8") as fh:
        team = [f["path"] for f in json.load(fh)["folders"]]
    check("the team's workspace opens the project; the product manager's adds the project-management folder, where the skills load",
          team == ["../.."] and pm == ["../..", "../../00. PrjMgm"], (pm, team))
    check("the onboarding guide", os.path.isfile(os.path.join(plan, "11. Onboarding", "Guide.html")))
    check("the tool register holds the team's tools too", {"AKOS TSP.17", "AKOS TSP.18"} <= {t.get("Upstream") for t in tools})
    skills = os.path.join(plan, ".agents", "skills")
    reg = os.path.join(plan, "04. Artifact Register", "Artifact Register Greenfield.json")
    ok, out = run([os.path.join(skills, "artifact-register", "scripts", "audit_artifact_register.py"), reg, "--root", project], root)
    check("the artifact register audits the whole project clean", "0 error(s), 0 warning(s)" in out, out[-400:])
    ok, out = run([os.path.join(skills, "tsp-manager", "scripts", "audit_tsp.py"), tsp], root)
    check("the tool register audits clean", "0 error(s), 0 warning(s)" in out, out[-400:])
    ok, out = run([installer, "status", "--project", plan, "--check"], root)
    check("status --check clean", ok, out[-300:])
    ok, out = run([installer, "init", project, "--name", "Again", "--catalogue", root], root)
    check("init refuses a folder that already holds a project", not ok and "already holds a project" in out, out[-300:])
    nogit = os.path.join(scratch, "akos-zip")
    shutil.copytree(root, nogit, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    ok, out = run([os.path.join(nogit, "install.py"), "init", os.path.join(scratch, "from-zip"), "--name", "Zip"], nogit)
    check("a ZIP download is told to clone, not shown a traceback", not ok and "git clone" in out and "Traceback" not in out, out[-300:])


def test_upstream(root, scratch):
    """status --upstream: which installed tools the catalogue has changed since."""
    print("\ninstall.py status --upstream")
    installer = os.path.join(root, "install.py")
    cat = os.path.join(scratch, "upstream-cat")
    subprocess.check_call(["git", "clone", "-q", root, cat])
    project = os.path.join(scratch, "upstream-project")
    ok, out = run([os.path.join(cat, "install.py"), "add", "status-board-manager", "--into", project, "--docs", "TSP"], cat)
    if not check("a tool and its TD installed from a clone", ok, out[-300:]):
        return
    status = lambda *extra: run([installer, "status", "--project", project, "--upstream", "--source", cat] + list(extra), root)
    ok, out = status()
    check("just installed: every tool up to date", ok and "Every tool is up to date." in out and "behind" not in out, out[-400:])

    def commit(rel, text, message):
        with io.open(os.path.join(cat, rel), "a", encoding="utf-8") as fh:
            fh.write(text)
        subprocess.check_call(["git", "-c", "user.name=smoke", "-c", "user.email=smoke@example.com", "commit", "-qam", message], cwd=cat)

    tool = "TSP/TSP.15 Team Status Board"
    commit(tool + "/status-board-manager/scripts/board.py", "\n# a later change\n", "a change to the skill")
    ok, out = status()
    lines = {l.split()[0]: l for l in out.splitlines() if l.strip()}
    check("a change to the skill: the skill is behind, its TD is not",
          "1 change(s) behind: " in lines.get("status-board-manager", "") and "up to date" in lines.get("TSP.15", ""), out[-500:])
    check("the hint names the tool to update", 'update "status-board-manager"' in out, out[-300:])
    commit(tool + "/TD.15 - Team Status Board.md", "\nA later line.\n", "a change to the TD")
    ok, out = status()
    lines = {l.split()[0]: l for l in out.splitlines() if l.strip()}
    check("a change to the TD: the TD entry is behind too", "1 change(s) behind: " in lines.get("TSP.15", ""), out[-500:])
    ok, out = status("--check")
    check("--check fails while a tool is behind", not ok, out[-300:])
    ok, out = run([installer, "status", "--project", project, "--upstream", "--source", root], root)
    check("compared with another clone holding the lock's commit, it still reads", ok and "source:" in out, out[-300:])


def test_installer(root, scratch):
    """Vendor a tool into a throwaway project and drive the drift check.

    The interesting assertion is the last pair: an edited copy must fail
    `status --check`, and must pass again only once someone has said why.
    """
    print("\ninstall.py")
    installer = os.path.join(root, "install.py")
    if not check("installer present", os.path.isfile(installer), installer):
        return

    project = os.path.join(scratch, "consumer")
    os.makedirs(project, exist_ok=True)

    ok, out = run([installer, "add", "wbs-manager", "--into", project,
                   "--catalogue", root, "--source", root], root)
    if not check("add runs", ok, out):
        return
    skill = os.path.join(project, ".agents", "skills", "wbs-manager", "SKILL.md")
    check("skill vendored into the project", os.path.isfile(skill), skill)
    lock = os.path.join(project, "tools.lock.json")
    if not check("lock written", os.path.isfile(lock), lock):
        return

    import json
    rec = json.load(io.open(lock, encoding="utf-8"))["tools"]["wbs-manager"]
    check("lock records origin and commit",
          bool(rec.get("commit")) and rec.get("origin", "").startswith("TSP/"),
          str(rec)[:200])

    ok, out = run([installer, "status", "--project", project, "--check"], root)
    check("status --check passes on a fresh copy", ok, out)

    with io.open(skill, "a", encoding="utf-8") as fh:
        fh.write("\nlocal edit\n")
    ok, out = run([installer, "status", "--project", project, "--check"], root)
    check("status --check catches an edited copy", not ok, out)

    ok, out = run([installer, "accept", "wbs-manager", "--project", project,
                   "-m", "smoke test"], root)
    check("accept records the change", ok, out)
    ok, out = run([installer, "status", "--project", project, "--check"], root)
    check("status --check passes once declared", ok, out)


def test_concurrent_save(root, scratch):
    """A save refuses when someone else wrote the register after it was loaded.

    Each save rewrites the whole file, so without this a writer saving a copy it
    read before another's save would erase that save and nothing would say so.
    Driven through registry.py itself, since every tool saves through it and
    the copies are held identical by test_shared_modules.
    """
    import importlib.util
    import json
    print("\nconcurrent saves")
    scripts = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    spec = importlib.util.spec_from_file_location(
        "akos_registry_smoke", os.path.join(scripts, "registry.py"))
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    work = os.path.join(scratch, "concurrent")
    os.makedirs(work, exist_ok=True)
    reg = os.path.join(work, "WBS Atlas.json")
    ok, out = run([os.path.join(scripts, "create_wbs.py"), reg, "Atlas"], work)
    if not check("concurrent: a register to write to", ok, out):
        return

    def refused(data, **kw):
        try:
            R.save(reg, data, **kw)
            return False
        except SystemExit as exc:
            return "changed on disk after it was loaded" in str(exc)

    before = io.open(reg, "rb").read()
    unchanged = R.load(reg)
    R.save(reg, unchanged, touch=False)
    check("concurrent: a save with no other writer changes nothing",
          io.open(reg, "rb").read() == before)

    first, second = R.load(reg), R.load(reg)
    second["items"].append({"ID": 1, "Title": "Second writer's row", "Type": "Story",
                            "Status": "Portfolio Backlog"})
    R.save(reg, second)
    on_disk = io.open(reg, "rb").read()
    first["items"].append({"ID": 1, "Title": "First writer's row", "Type": "Story",
                           "Status": "Portfolio Backlog"})
    check("concurrent: the stale writer's save is refused", refused(first))
    check("concurrent: nothing is written when it is refused",
          io.open(reg, "rb").read() == on_disk)
    titles = [r["Title"] for r in json.load(io.open(reg, encoding="utf-8"))["items"]]
    check("concurrent: the other writer's change survives",
          titles == ["Second writer's row"], str(titles))

    second["items"][0]["Owner"] = "Ana"
    check("concurrent: the same writer can save again", not refused(second))

    meta_only = R.load(reg)
    stale = R.load(reg)
    meta_only["meta"]["execution"] = {"inputs": "Client input"}
    R.save(reg, meta_only, touch=False)
    check("concurrent: a change to meta alone is caught too", refused(stale))
    check("concurrent: force=True overwrites deliberately",
          not refused(stale, force=True))


def test_execution_layout(root, scratch):
    """A project's own folder names, declared once in meta.execution.

    The standard layout needs no declaration and shows nothing; a project that
    differs says so in its register, the dashboard header names the difference,
    and refined finds specs in the declared folder without being told where.
    """
    import json
    print("\nExecution layout")
    scripts = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    wbs, refresh = os.path.join(scripts, "wbs.py"), os.path.join(scripts, "refresh_wbs.py")
    project = os.path.join(scratch, "layout", "Atlas")
    pm, work = os.path.join(project, "PM"), os.path.join(project, "01. Work")
    os.makedirs(pm, exist_ok=True)
    os.makedirs(os.path.join(work, "WP.1 Login"), exist_ok=True)
    io.open(os.path.join(work, "WP.1 Login", "WP1 Login - Specification.md"), "w",
            encoding="utf-8").write("# WP1 Login\n\n**Story:** ID 1 · **Written:** 2026-03-12\n")
    reg = os.path.join(pm, "WBS Atlas.json")
    html = os.path.join(pm, "WBS Dashboard.html")
    ok, out = run([os.path.join(scripts, "create_wbs.py"), reg, "Atlas"], pm)
    ok = ok and run([wbs, "add", reg, "Login page", "--type", "Story"], pm)[0]
    if not check("layout: a register with one story", ok, out):
        return

    ok, _ = run([refresh, reg, html, "Atlas"], pm)
    check("layout: a standard project shows no folder line",
          ok and "Folders:" not in io.open(html, encoding="utf-8").read())

    data = json.load(io.open(reg, encoding="utf-8"))
    data["meta"]["execution"] = {"folder": "../01. Work", "inputs": "Client input"}
    io.open(reg, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([refresh, reg, html, "Atlas"], pm)
    page = io.open(html, encoding="utf-8").read() if ok else ""
    check("layout: the dashboard names the declared differences",
          "Folders:" in page and "01. Work" in page and "Client input" in page
          and "Deliverables <code>" not in page, out[:200])
    ok, out = run([wbs, "refined", reg, "--ids", "1"], pm)
    check("layout: refined finds the spec in the declared folder",
          ok and "no spec naming it" not in out, out[:300])

    data["meta"]["execution"]["folder"] = "../Nowhere"
    io.open(reg, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([wbs, "refined", reg, "--ids", "1"], pm)
    check("layout: a declared folder that does not exist is refused, not ignored",
          not ok and "No Execution folder" in out, out[:300])


def test_shared_modules(root, scratch):
    """Modules copied into every skill folder must be identical.

    A skill has to be self-contained to be installable, so the shared code is
    duplicated rather than imported from one place. That is a deliberate trade,
    and it makes silent divergence the thing to guard: an edit applied to three
    of four copies leaves one tool quietly behaving differently.
    """
    print("\nshared modules")
    import hashlib
    for name in ("registry.py",):
        copies = {}
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, "TSP")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            if name in filenames:
                blob = io.open(os.path.join(dirpath, name), "rb").read()
                normalised = blob.replace(bytes([13, 10]), bytes([10]))
                digest = hashlib.sha256(normalised).hexdigest()[:12]
                copies.setdefault(digest, []).append(
                    os.path.relpath(dirpath, root))
        if not check("%s found in the tools" % name, bool(copies)):
            continue
        detail = "; ".join("%s: %s" % (d, ", ".join(v)) for d, v in copies.items())
        check("every copy of %s is identical (%d copies)"
              % (name, sum(len(v) for v in copies.values())),
              len(copies) == 1, detail)


def test_docs_match_code(root, scratch):
    """A tool's prose must describe the tool it actually ships.

    Both halves of this have already gone wrong here. Docs drifted behind a
    format change - a SKILL.md telling the reader to call `load_workbook` on a
    JSON register, and to save a `.xlsx` that no script writes. And code drifted
    ahead of docs - a create script whose Status vocabulary said `Backlog` where
    every document and the dashboard said `Portfolio Backlog`, so a register
    created from it disagreed with its own documentation on day one.

    Neither is caught by anything else: the scripts run, the links resolve, the
    registers round-trip. Only reading the two against each other finds it.
    """
    print("\ndocs match code")

    # Terms that only mean something for a spreadsheet-backed tool.
    SPREADSHEET = ("openpyxl", "load_workbook", ".xlsx", "merged cell",
                   "worksheet", "conditional formatting")

    for tool in TOOLS:
        skill = os.path.join(root, tool["skill"])
        folder = os.path.dirname(skill)
        docs = [os.path.join(skill, "SKILL.md")]
        docs += [os.path.join(folder, n) for n in sorted(os.listdir(folder))
                 if n.startswith("TD.") and n.endswith(".md")]

        scripts_dir = os.path.join(skill, "scripts")
        code = ""
        if os.path.isdir(scripts_dir):
            for n in sorted(os.listdir(scripts_dir)):
                if n.endswith(".py"):
                    code += io.open(os.path.join(scripts_dir, n),
                                    encoding="utf-8").read()

        prose = ""
        for d in docs:
            if os.path.exists(d):
                prose += io.open(d, encoding="utf-8").read()

        # The version history is where a format change is *supposed* to be
        # narrated, so it is exempt - only the body has to describe today.
        body = prose.split("## Version history")[0]

        stale = [w for w in SPREADSHEET
                 if w.lower() in body.lower() and w.lower() not in code.lower()]
        check("%s: prose describes the format the scripts implement" % tool["name"],
              not stale, "no script uses: %s" % ", ".join(stale) if stale else "")

        # Vocabularies defined in code must be documented.
        create = [n for n in os.listdir(scripts_dir)] if os.path.isdir(scripts_dir) else []
        create = [n for n in create if n.startswith("create_") and n.endswith(".py")]
        missing = []
        for n in create:
            src = io.open(os.path.join(scripts_dir, n), encoding="utf-8").read()
            for match in re.finditer(
                    r"^([A-Z][A-Z_]+)\s*=\s*\[([^\]]*)\]", src, re.M):
                name, blob = match.group(1), match.group(2)
                if name.endswith("FIELDS") or name.startswith("DEFAULT_"):
                    continue          # field names and seed rows, not vocabularies
                values = re.findall(r'"([^"]+)"', blob)
                for v in values:
                    if len(v) > 2 and v not in prose:
                        missing.append("%s: %r" % (name, v))
        check("%s: every vocabulary value is documented" % tool["name"],
              not missing, "; ".join(missing))


def test_catalogue(root, scratch):
    """The repo's own registry must describe the repo, and be regenerable.

    REGISTRY.md is a generated view. A generated file whose generator is never
    run in CI is a file that silently stops matching its source.
    """
    print("\ncatalogue")
    register = os.path.join(root, "registry", "TSP Register.json")
    if not check("registry present", os.path.isfile(register), register):
        return
    import json
    data = json.load(io.open(register, encoding="utf-8"))
    tools = data.get("tools", [])
    check("registry lists tools", bool(tools), str(sorted(data)))

    # Every skill the registry claims must exist beside its tool.
    missing = []
    for row in tools:
        for skill in str(row.get("Skill") or "").split(","):
            skill = skill.strip()
            if not skill:
                continue
            hits = [d for d in os.listdir(os.path.join(root, "TSP"))
                    if os.path.isfile(os.path.join(root, "TSP", d, skill, "SKILL.md"))]
            if not hits:
                missing.append("TSP.%s -> %s" % (row.get("ID"), skill))
    check("every claimed skill is present", not missing, "; ".join(missing))

    before = io.open(os.path.join(root, "registry", "REGISTRY.md"),
                     encoding="utf-8").read()
    ok, out = run([os.path.join(root, "registry", "build_registry.py")], root)
    if not check("REGISTRY.md regenerates", ok, out):
        return
    after = io.open(os.path.join(root, "registry", "REGISTRY.md"),
                    encoding="utf-8").read()
    check("REGISTRY.md was already up to date",
          before.split("Generated from")[0] == after.split("Generated from")[0],
          "regenerating changed it - it had drifted from the register")


def test_reconciliation(root, scratch):
    """The artifact register's claim about the disk must actually be checkable.

    Every other tool here can only be checked against itself. This one asserts
    something about the filesystem, so the test is: break the filing, and confirm
    the audit notices. A check that cannot fail is not a check.
    """
    print("\nTSP.5 reconciliation")
    skill = os.path.join(root, "TSP", "TSP.5 Artifact Register", "artifact-register")
    if not check("skill present", os.path.isdir(skill), skill):
        return
    scripts = os.path.join(skill, "scripts")

    work = os.path.join(scratch, "filing")
    os.makedirs(work, exist_ok=True)
    register = os.path.join(work, "00. Artifact Register, Filing.xlsx")

    ok, out = run([os.path.join(scripts, "create_artifact_register.py"),
                   register, "Filing"], work)
    if not check("create runs", ok, out):
        return

    ok, out = run([os.path.join(scripts, "audit_artifact_register.py"),
                   register, "--root", work], work)
    if not check("clean filing passes the disk check", ok, out):
        return

    # Break it exactly the way real filing breaks: a file arrives without an ID.
    stray = os.path.join(work, "invoice scan.pdf")
    io.open(stray, "w", encoding="utf-8").write("x")
    ok, out = run([os.path.join(scripts, "audit_artifact_register.py"),
                   register, "--root", work], work)
    check("unfiled document is caught", not ok, out)
    check("and named in the output", "invoice scan.pdf" in out, out)

    # Filing it properly must both register it and rename it.
    ok, out = run([os.path.join(scripts, "artifact.py"), "add", register, stray,
                   "--name", "Invoice Scan", "--type", "Document",
                   "--parent-digital", "Main", "--root", work], work)
    check("add runs", ok, out)
    # 01. not 1. - lexicographic and numeric order only agree when padded, and
    # they disagree by platform, so this is a real regression to guard.
    check("file was renamed to carry its zero-padded ID",
          any(f.startswith("01. Invoice Scan") for f in os.listdir(work)),
          str(os.listdir(work)))

    ok, out = run([os.path.join(scripts, "audit_artifact_register.py"),
                   register, "--root", work], work)
    check("disk check passes once filed", ok, out)


CONTENT_TOOL = "TSP.6 Content System"
CONTENT_SKILLS = ["content-idea-capture", "content-plan-author",
                  "content-post-writer", "content-review",
                  "content-strategy-author"]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def broken_links(root):
    """Relative markdown links under root that point at nothing."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            text = io.open(path, encoding="utf-8", errors="replace").read()
            for match in LINK_RE.finditer(text):
                target = match.group(1)
                if target.startswith(("http", "#", "mailto")):
                    continue
                resolved = os.path.normpath(
                    os.path.join(dirpath, target.split("#")[0]))
                if not os.path.exists(resolved):
                    out.append("%s -> %s" % (
                        os.path.relpath(path, root).replace(os.sep, "/"), target))
    return out


def test_content_system(root, scratch):
    """TSP.6 ships no code, so what can rot is its cross-references.

    Every skill defers its formats to a contract in `_shared/`, and install.py
    places `_shared` beside the skill rather than inside it. Two things follow,
    and both are asserted: the references must resolve in the catalogue, and
    they must still resolve after installation, which is a different layout.

    The last check breaks a link on purpose. A link checker that has never
    failed is indistinguishable from one that always passes.
    """
    print("\nTSP.6 Content System")
    tool = os.path.join(root, "TSP", CONTENT_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return

    for skill in CONTENT_SKILLS:
        path = os.path.join(tool, skill, "SKILL.md")
        if not check("%s has SKILL.md" % skill, os.path.isfile(path), path):
            continue
        head = io.open(path, encoding="utf-8").read()[:600]
        check("%s declares name and description" % skill,
              "name:" in head and "description:" in head, head[:120])

    shared = os.path.join(tool, "_shared")
    contracts = os.path.join(shared, "contracts")
    check("_shared ships the contracts", os.path.isdir(contracts), contracts)

    # A contract nothing reads is either dead or a reference someone dropped.
    text = ""
    for skill in CONTENT_SKILLS:
        path = os.path.join(tool, skill)
        for dirpath, _, filenames in os.walk(path):
            for name in filenames:
                if name.endswith(".md"):
                    text += io.open(os.path.join(dirpath, name),
                                    encoding="utf-8", errors="replace").read()
    orphans = [c for c in sorted(os.listdir(contracts)) if c not in text]
    check("every contract is referenced by a skill", not orphans,
          "unreferenced: %s" % ", ".join(orphans))

    check("links resolve in the catalogue", not broken_links(tool),
          "; ".join(broken_links(tool)[:5]))

    # Installed layout: _shared becomes a sibling of the skill, so every
    # ../_shared/ reference crosses a directory boundary that does not exist
    # in the catalogue. This is the check that would have caught the port.
    project = os.path.join(scratch, "content-project")
    os.makedirs(project, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", "content-post-writer",
                   "--into", project, "--catalogue", root], root)
    if not check("install.py add brings the skill in", ok, out):
        return
    skills_root = os.path.join(project, ".agents", "skills")
    check("_shared installed beside the skill",
          os.path.isdir(os.path.join(skills_root, "_shared")),
          "\n".join(sorted(os.listdir(skills_root))) if os.path.isdir(skills_root) else "")
    installed_bad = broken_links(skills_root)
    check("links still resolve once installed", not installed_bad,
          "; ".join(installed_bad[:5]))

    # A second skill from the same tool must reuse the one copy, not a second.
    ok, out = run([os.path.join(root, "install.py"), "add", "content-review",
                   "--into", project, "--catalogue", root], root)
    check("a second skill reuses the shared copy",
          ok and "reused" in out, out)

    # Negative case: the checker must be able to fail.
    canary = os.path.join(skills_root, "_canary.md")
    io.open(canary, "w", encoding="utf-8").write("[x](./nothing-here.md)\n")
    check("a broken link is actually detected", bool(broken_links(skills_root)),
          "the link checker passed a file it should have failed")
    os.remove(canary)


NOTEBOOK_TOOL = "TSP.7 Notebook Manager"
NOTEBOOK_SKILL = "notebook-capture"
NOTEBOOK_TREE = ["index.md", "diary/index.md", "projects/index.md",
                 "areaOfFocus/index.md", "areaOfInterest/index.md",
                 "meetings/index.md", "eDiary/index.md", "eDiary/style.css"]


def test_notebook_manager(root, scratch):
    """TSP.7 ships no code and no data, so what can rot is first use.

    The installer copies the skill folder and nothing else, and the user's
    notebooks/ does not exist yet. Everything the skill needs on day one must
    therefore travel inside it, as assets/, and first use must build the tree
    from there without ever overwriting a note. Each of those is asserted on a
    real install, not on the catalogue layout.
    """
    print("\nTSP.7 Notebook Manager")
    tool = os.path.join(root, "TSP", NOTEBOOK_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    path = os.path.join(tool, NOTEBOOK_SKILL, "SKILL.md")
    if not check("%s has SKILL.md" % NOTEBOOK_SKILL, os.path.isfile(path), path):
        return
    text = io.open(path, encoding="utf-8").read()
    check("%s declares name and description" % NOTEBOOK_SKILL,
          "name:" in text[:600] and "description:" in text[:600], text[:120])
    check("TD.7 present", any(n.startswith("TD.7") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool),
          "; ".join(broken_links(tool)[:5]))

    project = os.path.join(scratch, "notebook-project")
    os.makedirs(project, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", NOTEBOOK_SKILL,
                   "--into", project, "--catalogue", root], root)
    if not check("install.py add brings the skill in", ok, out):
        return
    skill = os.path.join(project, ".agents", "skills", NOTEBOOK_SKILL)
    assets = os.path.join(skill, "assets", "notebooks")
    check("assets/ installed with the skill", os.path.isdir(assets), skill)
    notebooks = os.path.join(project, "notebooks")
    check("no notebooks data ships with the tool", not os.path.exists(notebooks))

    # The base path rule: notebooks/ sits beside the folder that holds the
    # skills folder - here, the project root.
    unit = os.path.dirname(os.path.dirname(os.path.dirname(skill)))
    check("base path resolves to the project root",
          os.path.normcase(unit) == os.path.normcase(project), unit)

    def first_use():
        """What the skill's First use section tells the agent to do."""
        copied = 0
        for dirpath, _, filenames in os.walk(assets):
            for name in filenames:
                src = os.path.join(dirpath, name)
                dst = os.path.join(notebooks, os.path.relpath(src, assets))
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
                    copied += 1
        return copied

    first_use()
    missing = [f for f in NOTEBOOK_TREE
               if not os.path.isfile(os.path.join(notebooks, f))]
    check("first use builds the whole tree", not missing, ", ".join(missing))
    check("links resolve in the new tree", not broken_links(notebooks),
          "; ".join(broken_links(notebooks)[:5]))

    # A second run must copy nothing: first use can never overwrite a note.
    diary = os.path.join(notebooks, "diary", "index.md")
    io.open(diary, "a", encoding="utf-8").write(u"| 2026-01-01 | kept | | | |\n")
    check("a second first use copies nothing", first_use() == 0)
    check("an edited index survives",
          "kept" in io.open(diary, encoding="utf-8").read())

    # A post is drafted from the template in place; its stylesheet link must
    # resolve from where posts live.
    template = os.path.join(skill, "assets", "post-template.html")
    if check("post template installed", os.path.isfile(template), template):
        href = re.search(r'rel="stylesheet" href="([^"]+)"',
                         io.open(template, encoding="utf-8").read())
        target = os.path.normpath(os.path.join(
            notebooks, "eDiary", "entries", href.group(1) if href else ""))
        check("a post finds the stylesheet", bool(href) and os.path.isfile(target),
              target)

    named = set(re.findall(r"`(assets/[^`]+)`", text))
    absent = [a for a in named if not os.path.exists(os.path.join(skill, a))]
    check("every assets/ path the skill names exists", named and not absent,
          ", ".join(absent) or "SKILL.md names no assets/ path")


SPRINT_TOOL = "TSP.8 Sprint Ceremonies"
SPRINT_SKILLS = ["sprint-facilitator", "sprint-planning-precheck"]


def test_sprint_ceremonies(root, scratch):
    """TSP.8: the record script driven through a sprint, and the skills' claims.

    The script is the one part that writes, so every command and every refusal
    is run for real against a seeded calendar. The skills are prose that names
    commands in other tools; a renamed subcommand there would leave a ceremony
    step that fails only when someone runs it, so each one named is checked to
    exist.
    """
    import json
    print("\nTSP.8 Sprint Ceremonies")
    tool = os.path.join(root, "TSP", SPRINT_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    texts = {}
    for name in SPRINT_SKILLS:
        path = os.path.join(tool, name, "SKILL.md")
        if not check("%s has SKILL.md" % name, os.path.isfile(path), path):
            return
        texts[name] = io.open(path, encoding="utf-8").read()
        check("%s declares name and description" % name,
              "name: %s" % name in texts[name][:600]
              and "description:" in texts[name][:600], texts[name][:120])
    check("TD.8 present", any(n.startswith("TD.8") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool),
          "; ".join(broken_links(tool)[:5]))

    # Every wbs.py / tsp.py subcommand the skills name must exist.
    scripts = {
        "wbs.py": os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager",
                               "scripts", "wbs.py"),
        "tsp.py": os.path.join(root, "TSP", "TSP.3 TSP Register", "tsp-manager",
                               "scripts", "tsp.py"),
        "stk.py": os.path.join(root, "TSP", "TSP.13 Stakeholder Register", "stakeholder-manager",
                               "scripts", "stk.py"),
    }
    prose = "\n".join(texts.values())
    unknown = []
    for script, path in scripts.items():
        src = io.open(path, encoding="utf-8").read()
        offered = set(re.findall(r'add_parser\(\s*"([a-z-]+)"', src))
        for cmd in set(re.findall(r"%s\s+([a-z][a-z-]+)" % re.escape(script), prose)):
            if cmd not in offered:
                unknown.append("%s %s" % (script, cmd))
    check("every wbs.py / tsp.py / stk.py command the skills name exists", not unknown,
          ", ".join(sorted(unknown)))
    facilitator = texts.get("sprint-facilitator", "")
    check("a pull-in states its effect, and the close-out reads the effects first",
          "## A pull-in states its effect on committed work" in facilitator
          and "Read the pull-ins' `effect:` lines first" in facilitator)
    check("planning commits a parent a goal means to close", "A goal that closes a parent commits the parent" in facilitator)
    check("the close-out sends the communications due", "stk.py due --all" in facilitator and "stk.py done" in facilitator)

    # --- the record, through one sprint and into the next ---------------------
    sr = os.path.join(tool, "sprint-facilitator", "scripts", "sprint_record.py")
    wbs = scripts["wbs.py"]
    work = os.path.join(scratch, "sprints")
    rec = os.path.join(work, "records")
    conv = os.path.join(work, "conventions.json")
    os.makedirs(work, exist_ok=True)
    ok, out = run([wbs, "sprints", "seed", conv, "--scope", "Atlas", "--year", "2026",
                   "--anchor", "2026-07-19"], work)
    if not check("seed a sprint calendar", ok, out):
        return

    ok, out = run([sr, "status", rec], work)
    check("status: an empty folder says nothing was ever planned",
          ok and "No sprint has ever been recorded" in out, out[:200])
    ok, out = run([sr, "plan", rec, "S26.Q3.6", "--calendar", conv], work)
    if not check("plan creates the record", ok, out):
        return
    record = os.path.join(rec, "S26.Q3.6.md")
    first = io.open(record, encoding="utf-8").readline().strip()
    check("plan dates the heading from the calendar",
          first == "# Sprint S26.Q3.6 (13-Sep / 26-Sep)", first)
    ok, _ = run([sr, "plan", rec, "S26.Q3.6"], work)
    check("planning a sprint twice is refused", not ok)

    ok, out = run([sr, "status", rec, "--calendar", conv, "--as-of", "2026-09-10"], work)
    check("status: quiet mid-sprint", ok and "No ceremony is due" in out, out[:200])
    ok, out = run([sr, "status", rec, "--calendar", conv, "--as-of", "2026-09-25"], work)
    check("status: the close-out is due near the end",
          ok and "close-out is due" in out, out[:200])
    ok, out = run([sr, "status", rec, "--calendar", conv, "--as-of", "2026-09-29"], work)
    check("status: a missed close-out is overdue",
          ok and "no close-out - 3 days overdue" in out, out[:200])

    ok, out = run([sr, "review", rec, "S26.Q3.6"], work)
    check("review appends", ok, out)
    ok, _ = run([sr, "review", rec, "S26.Q3.6"], work)
    check("a second review is refused", not ok)
    ok, out = run([sr, "retro", rec, "S26.Q3.6"], work)
    check("retro appends", ok, out)
    ok, _ = run([sr, "retro", rec, "S26.Q3.6"], work)
    check("a second retro is refused", not ok)
    ok, _ = run([sr, "review", rec, "S26.Q3.9"], work)
    check("a ceremony on a sprint never planned is refused", not ok)

    text = io.open(record, encoding="utf-8").read()
    order = [text.find(h) for h in ("## Planning", "## Review", "## Retrospective",
                                    "## Noticed", "## Next sprint - draft")]
    check("the arc reads Planning, Review, Retro, then the living sections",
          -1 not in order and order == sorted(order), str(order))
    ok, out = run([sr, "status", rec, "--calendar", conv, "--as-of", "2026-09-29"], work)
    check("status: a closed sprint with nothing after it needs planning",
          ok and "No sprint has been planned since" in out, out[:200])

    io.open(record, "w", encoding="utf-8").write(
        text.replace("### Draft goals", "### Draft goals\n\n- Ship the login page", 1))
    ok, out = run([sr, "plan", rec, "S26.Q3.7", "--calendar", conv], work)
    nxt = io.open(os.path.join(rec, "S26.Q3.7.md"), encoding="utf-8").read() if ok else ""
    check("plan carries the last sprint's draft goals in",
          "| G1 | draft: Ship the login page |" in nxt, out[:200])

    # --- the goals are data a report reads back -----------------------------
    nxt_path = os.path.join(rec, "S26.Q3.7.md")
    nxt = nxt.replace("| G1 | draft: Ship the login page |  |  |  |",
                      "| G1 | Ship the login page | Login live | Q4-26.B1 |  |")
    nxt = nxt.replace("| Item | Effort | Area | Goal | Notes |\n|---|---|---|---|---|\n|  |  |  |  |  |",
                      "| Item | Effort | Area | Goal | Notes |\n|---|---|---|---|---|\n"
                      "| Atlas#2 Login page | 4h | Product | G1 |  |\n| Atlas#5 Cache | 2h | Product |  |  |")
    io.open(nxt_path, "w", encoding="utf-8").write(nxt)
    ok, out = run([sr, "review", rec, "S26.Q3.7"], work)
    reviewed = io.open(nxt_path, encoding="utf-8").read()
    check("review pre-fills the goals by ID", ok and "| G1 | Ship the login page |  |  |" in reviewed, out[:200])
    io.open(nxt_path, "w", encoding="utf-8").write(
        reviewed.replace("| G1 | Ship the login page |  |  |", "| G1 | Ship the login page | Yes |  |"))
    ok, out = run([sr, "goals", rec, "--json"], work)
    try:
        goals = {g["sprint"]: g for g in json.loads(out)}
    except ValueError:
        goals = {}
    g7 = goals.get("S26.Q3.7") or {}
    check("goals reads the verdict, the bet and the goal-linked hours",
          ok and (g7.get("goals") or [{}])[0].get("achieved") == "Yes"
          and g7["goals"][0].get("bet") == "Q4-26.B1"
          and (g7.get("hours") or {}).get("goal_linked") == 4.0, out[:300])
    io.open(nxt_path, "w", encoding="utf-8").write(
        reviewed.replace("| G1 | Ship the login page |  |  |", "| G1 | Ship the login page | Mostly |  |"))
    ok, out = run([sr, "goals", rec], work)
    check("goals flags a verdict that is not Yes / Partial / No", not ok and "Mostly" in out, out[:300])
    old = os.path.join(rec, "S26.Q2.1.md")
    io.open(old, "w", encoding="utf-8").write(
        u"# Sprint S26.Q2.1\n\n## Planning — 2026-04-01\n\n### Iteration goals\n\n"
        u"| Goal | Achieved |\n|---|---|\n| Old goal | Yes |\n")
    ok, out = run([sr, "goals", rec], work)
    check("a record from before goal IDs reads as unstructured", "S26.Q2.1  unstructured" in out, out[:300])

    bad = os.path.join(work, "empty.json")
    io.open(bad, "w", encoding="utf-8").write(u"{}")
    ok, _ = run([sr, "status", rec, "--calendar", bad], work)
    check("a calendar with no sprints is refused", not ok)

    # --- installed the way the TD says, together with what they need -----------
    project = os.path.join(scratch, "sprint-project")
    os.makedirs(project, exist_ok=True)
    for name in SPRINT_SKILLS + ["wbs-manager"]:
        ok, out = run([os.path.join(root, "install.py"), "add", name,
                       "--into", project, "--catalogue", root], root)
        if not check("install.py add %s" % name, ok, out):
            return
    installed = os.path.join(project, ".agents", "skills", "sprint-facilitator",
                             "scripts", "sprint_record.py")
    check("the record script arrives with the skill", os.path.isfile(installed), installed)
    lock = json.load(io.open(os.path.join(project, "tools.lock.json"), encoding="utf-8"))
    check("both skills recorded in the lock",
          all(n in lock.get("tools", {}) for n in SPRINT_SKILLS), str(sorted(lock.get("tools", {}))))


STK_TOOL = "TSP.13 Stakeholder Register"
STK_SKILL = "stakeholder-manager"


def test_stakeholder_register(root, scratch):
    """TSP.13 on a scratch project in its own git repository.

    The rules worth guarding are the ones a slip would break silently: no
    address reaching the dashboard, the contacts file kept out of git (and the
    tool saying so when it is not), an audience resolved to each person once
    with the external copy split out, `per sprint` read from the project's own
    calendar and said plainly when there is none, and the solo default for a
    project with no register. The example register must pass its own check.
    """
    print("\nTSP.13 Stakeholder Register")
    skill = os.path.join(root, "TSP", STK_TOOL, STK_SKILL)
    scripts = os.path.join(skill, "scripts")
    stk = os.path.join(scripts, "stk.py")
    check("TD.13 present", any(n.startswith("TD.13") for n in os.listdir(os.path.join(root, "TSP", STK_TOOL))))
    check("links resolve in the catalogue", not broken_links(os.path.join(root, "TSP", STK_TOOL)),
          "; ".join(broken_links(os.path.join(root, "TSP", STK_TOOL))[:5]))

    project = os.path.join(scratch, "stk-project")
    plan = os.path.join(project, "planning")
    os.makedirs(plan, exist_ok=True)
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.check_call(["git", "init", "-q", "."], cwd=project, **quiet)

    ok, out = run([os.path.join(scripts, "create_stk.py"), plan, "--scope", "Atlas"], project)
    if not check("create runs", ok, out):
        return
    check("create prints the .gitignore line in a repository", "Contacts *.csv" in out, out)
    reg = os.path.join(plan, "Stakeholders Atlas.json")
    steps = [
        ["add-group", plan, "Steering group"],
        ["add", plan, "Sponsor One", "--groups", "G.1", "--power", "High", "--interest", "High",
         "--current", "Supportive", "--desired", "Supportive"],
        ["add", plan, "Client Lead", "--groups", "G.1", "--share", "external", "--power", "High",
         "--interest", "High", "--current", "Neutral", "--desired", "Supportive"],
        ["add", plan, "Finance Office", "--groups", "G.1", "--power", "High", "--interest", "Low",
         "--current", "Neutral", "--desired", "Neutral"],
        ["add-comm", plan, "Status report", "--report", "status-report", "--mode", "push",
         "--audience", "S.1", "--cadence", "per sprint", "--channel", "email"],
        ["add-comm", plan, "Steering update", "--mode", "push", "--audience", "G.1,S.2",
         "--cadence", "monthly", "--channel", "email"],
        ["contact", plan, "--id", "S.1", "--email", "sponsor@example.com"],
        ["contact", plan, "--id", "S.2", "--email", "client@example.com"],
        ["done", plan, "--id", "C.1", "--on", "2026-01-02"],
    ]
    for step in steps:
        ok, out = run([stk] + step, project)
        if not check("stk.py %s %s" % (step[0], step[2] if step[0] != "contact" else step[3]), ok, out):
            return
    ok, out = run([stk, "contact", plan, "--id", "S.1", "--phone", "+00 555 0100"], project)
    check("contact never echoes the values", ok and "555" not in out and "example.com" not in out, out)

    ok, out = run([stk, "audience", plan, "--id", "C.2", "--split"], project)
    check("audience splits the external copy", ok and "-- external copy --" in out
          and "client@example.com" in out and out.count("Client Lead") == 1, out)

    ok, out = run([stk, "due", plan, "--as-of", "2026-01-20"], project)
    check("no calendar: per sprint read as every 14 days, said", ok and "no sprint calendar" in out, out)
    conventions = {"meta": {"kind": "agile-conventions", "version": 1, "scope": "Atlas"},
                   "sprints": [{"Starts": "2026-01-01", "Ends": "2026-01-14"},
                               {"Starts": "2026-01-15", "Ends": "2026-01-28"},
                               {"Starts": "2026-01-29", "Ends": "2026-02-11"}]}
    import json
    with io.open(os.path.join(plan, "Agile Conventions Atlas.json"), "w", encoding="utf-8") as fh:
        json.dump(conventions, fh)
    ok, out = run([stk, "due", plan, "--as-of", "2026-01-20"], project)
    check("per sprint: done last sprint is due this one", ok and "no sprint calendar" not in out
          and re.search(r"due\s+Atlas\s+C\.1", out), out)
    ok, out = run([stk, "due", plan, "--as-of", "2026-02-01", "--overdue"], project)
    check("per sprint: a whole sprint missed is overdue", ok and re.search(r"overdue\s+Atlas\s+C\.1", out), out)
    ok, out = run([stk, "due", "--all", "--root", project, "--as-of", "2026-01-20"], project)
    check("--all finds the register under --root", ok and "C.1" in out, out)

    ok, out = run([stk, "check", plan], project)
    check("check: a stakeholder with no contacts row", "S.3" in out and "no row in the contacts file" in out, out)
    check("check: a gap with no engagement action", "no Engagement Action" in out, out)
    check("check: a contacts file git would take", "not ignored by git" in out, out)
    with io.open(os.path.join(project, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("Contacts *.csv\n")
    ok, out = run([stk, "check", plan], project)
    check("check: quiet once git ignores it", "ignored by git" not in out and "tracked by git" not in out, out)
    subprocess.check_call(["git", "add", "-f", os.path.join("planning", "Contacts Atlas.csv")], cwd=project, **quiet)
    ok, out = run([stk, "check", plan], project)
    check("check: a tracked contacts file is an error", not ok and "tracked by git" in out, out)

    dash = os.path.join(plan, "Stakeholder Dashboard.html")
    ok, out = run([os.path.join(scripts, "refresh_stk.py"), plan], project)
    if check("refresh runs", ok, out) and os.path.isfile(dash):
        html = io.open(dash, encoding="utf-8").read()
        check("no address reaches the dashboard", "example.com" not in html)

    empty = os.path.join(project, "no-register")
    os.makedirs(empty, exist_ok=True)
    code = ("import sys; sys.path.insert(0, %r); import stk_register as STK; "
            "d = STK.load_or_default(%r, scope='X'); "
            "print(d['meta'].get('default'), [l for c, l in STK.audiences_for(d, 'status-report')])"
            % (scripts, empty))
    ok, out = run(["-c", code], project)
    check("the solo default: the owner and a status report", ok and out.startswith("True ['owner']"), out)

    example = os.path.join(skill, "examples")
    ok, out = run([stk, "check", example], project)
    check("the example register passes its check, with its intended findings",
          ok and "no Engagement Action" in out and "ERROR" not in out, out)

    consumer = os.path.join(scratch, "stk-consumer")
    os.makedirs(consumer, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", STK_SKILL,
                   "--into", consumer, "--catalogue", root], root)
    check("install.py add %s" % STK_SKILL, ok, out)


REPORT_TOOL = "TSP.10 Reporting"


PD_TOOL = "TSP.14 Project Definition"


TEAM_TOOLS = [("TSP.17 Work Management", "work-manager", ["work.py", "smoke_test.py"], ["references/sizes.md", "references/stages/discovery.md", "references/stages/implement.md", "templates/Specification.md"]),
              ("TSP.18 Change Requests", "change-request", ["cr.py", "smoke_test.py"], [])]


def test_team_tools(root, scratch):
    """Work Management and Change Requests: what they ship, and their own smoke tests."""
    for folder, skill, scripts, extra in TEAM_TOOLS:
        print("\n%s" % folder)
        tool = os.path.join(root, "TSP", folder)
        if not check("tool folder present", os.path.isdir(tool), tool):
            continue
        check("TD present", any(n.startswith("TD.") for n in os.listdir(tool)))
        check("links resolve in the catalogue", not broken_links(tool), str(broken_links(tool))[:200])
        base = os.path.join(tool, skill)
        for rel in ["SKILL.md"] + ["scripts/" + s for s in scripts] + extra:
            check("ships %s" % rel, os.path.isfile(os.path.join(base, rel.replace("/", os.sep))))
        ok, out = run([os.path.join(base, "scripts", "smoke_test.py")], scratch)
        check("its own smoke test passes", ok and "All checks passed." in out, out[-500:])


ONBOARD_TOOL = "TSP.16 Onboarding"


def test_onboarding(root, scratch):
    """The onboarding guide: its own smoke test, and an install that carries its fonts."""
    print("\nTSP.16 Onboarding")
    tool = os.path.join(root, "TSP", ONBOARD_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    check("TD.16 present", any(n.startswith("TD.16") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), str(broken_links(tool))[:200])
    skill = os.path.join(tool, "onboarding-guide")
    fonts = ("BricolageGrotesque-latin.woff2", "Geist-latin.woff2", "GeistMono-latin.woff2",
             "OFL-bricolagegrotesque.txt", "OFL-geist.txt", "OFL-geistmono.txt")
    for rel in ["SKILL.md"] + [os.path.join("scripts", f) for f in ("onboard.py", "render.py", "guide.css", "guide.js", "smoke_test.py")] \
            + [os.path.join("assets", "fonts", f) for f in fonts]:
        check("ships %s" % rel.replace(os.sep, "/"), os.path.isfile(os.path.join(skill, rel)))
    ok, out = run([os.path.join(skill, "scripts", "smoke_test.py")], scratch)
    check("its own smoke test passes", ok and "All checks passed." in out, out[-500:])
    proj = os.path.join(scratch, "onboard-project")
    os.makedirs(proj, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", "onboarding-guide", "--into", proj, "--catalogue", root], scratch)
    installed = os.path.join(proj, ".agents", "skills", "onboarding-guide", "assets", "fonts")
    check("install.py add onboarding-guide carries the fonts and their licences",
          ok and all(os.path.isfile(os.path.join(installed, f)) for f in fonts), out[-300:])


BOARD_TOOL = "TSP.15 Team Status Board"


def test_status_board(root, scratch):
    """The team's board: its own smoke test, installed into a project with the
    WBS, and the status report saying how fresh the WBS is."""
    print("\nTSP.15 Team Status Board")
    tool = os.path.join(root, "TSP", BOARD_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    check("TD.15 present", any(n.startswith("TD.15") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), str(broken_links(tool))[:200])
    skill = os.path.join(tool, "status-board-manager")
    for rel in ("SKILL.md", os.path.join("scripts", "board.py"), os.path.join("scripts", "xlsx.py"),
                os.path.join("scripts", "smoke_test.py")):
        check("ships %s" % rel.replace(os.sep, "/"), os.path.isfile(os.path.join(skill, rel)))
    ok, out = run([os.path.join(skill, "scripts", "smoke_test.py")], scratch)
    check("its own smoke test passes", ok and "All checks passed." in out, out[-400:])

    proj = os.path.join(scratch, "board-project")
    os.makedirs(proj, exist_ok=True)
    installer = os.path.join(root, "install.py")
    for name in ("wbs-manager", "sprint-facilitator", "reporting", "status-board-manager"):
        ok, out = run([installer, "add", name, "--into", proj, "--catalogue", root], scratch)
        if not check("install %s" % name, ok, out[-300:]):
            return
    skills = os.path.join(proj, ".agents", "skills")
    planning = os.path.join(proj, "0. PrjMgm")
    os.makedirs(planning, exist_ok=True)
    wbs = os.path.join(skills, "wbs-manager", "scripts")
    reg, conv, records = os.path.join(planning, "WBS Demo.json"), os.path.join(proj, "conventions.json"), os.path.join(proj, "records")
    board = os.path.join(skills, "status-board-manager", "scripts", "board.py")
    for cmd in ([os.path.join(wbs, "create_wbs.py"), reg, "Demo"],
                [os.path.join(wbs, "wbs.py"), "sprints", "seed", conv, "--scope", "Demo", "--year", "2026", "--anchor", "2026-07-19"],
                [os.path.join(wbs, "wbs.py"), "sprints", "import", reg, "--from", conv],
                [os.path.join(wbs, "wbs.py"), "add", reg, "Signup page", "--sprint-planned", "S26.Q4.1"],
                [os.path.join(skills, "sprint-facilitator", "scripts", "sprint_record.py"), "plan", records, "S26.Q4.1", "--calendar", conv],
                [board, "setup", reg, "--sprint", "S26.Q4.1"]):
        ok, out = run(cmd, scratch)
        if not check("setup: %s %s" % (os.path.basename(cmd[0]), cmd[1] if len(cmd) > 1 and not os.path.isabs(cmd[1]) else ""), ok, out[-300:]):
            return
    report = os.path.join(skills, "reporting", "scripts", "report.py")

    def header(day):
        ok, out = run([report, "status", planning, "--records", records, "--sprint", "S26.Q4.1", "--as-of", day], scratch)
        page = os.path.join(planning, "Reports", "Status", "%s Status.html" % day)
        return ok, out, (io.open(page, encoding="utf-8").read() if os.path.exists(page) else "")

    ok, out, page = header("2026-10-12")
    check("the status report says the team board is not consolidated yet", ok and "team board not consolidated yet" in page, out[-300:])
    ok, out = run([board, "sync", reg, "--sprint", "S26.Q4.1", "--consolidated"], scratch)
    ok, out, page = header("2026-10-13")
    check("after a consolidation, it says the WBS is as of that date",
          ok and ("the WBS as of the team board&#x27;s last consolidation" in page
                  or "the WBS as of the team board's last consolidation" in page), out[-300:])


def test_project_definition(root, scratch):
    """The brief's tool: its own smoke test, installed into an empty project, and
    the status report reading the brief through it, or saying it is not there."""
    import json
    print("\nTSP.14 Project Definition")
    tool = os.path.join(root, "TSP", PD_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    check("TD.14 present", any(n.startswith("TD.14") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), str(broken_links(tool))[:200])
    skill = os.path.join(tool, "project-definition-manager")
    for rel in ("SKILL.md", os.path.join("templates", "Project Brief.md"),
                os.path.join("scripts", "brief.py"), os.path.join("scripts", "smoke_test.py")):
        check("ships %s" % rel.replace(os.sep, "/"), os.path.isfile(os.path.join(skill, rel)))
    ok, out = run([os.path.join(skill, "scripts", "smoke_test.py")], scratch)
    check("its own smoke test passes", ok and "All checks passed." in out, out[-400:])

    # Installed beside the status report, in a project with nothing else.
    proj = os.path.join(scratch, "pd-project")
    os.makedirs(proj, exist_ok=True)
    installer = os.path.join(root, "install.py")
    ok, out = run([installer, "add", "wbs-manager", "--into", proj, "--catalogue", root], scratch)
    ok1, _ = run([installer, "add", "sprint-facilitator", "--into", proj, "--catalogue", root], scratch)
    ok = ok and ok1
    ok2, out2 = run([installer, "add", "reporting", "--into", proj, "--catalogue", root], scratch)
    check("installing reporting names the brief's tool as not installed yet",
          ok and ok2 and "Works with, not installed here:" in out2 and "project-definition-manager" in out2, out2[-400:])
    skills = os.path.join(proj, ".agents", "skills")
    report = os.path.join(skills, "reporting", "scripts", "report.py")
    planning = os.path.join(proj, "0. PrjMgm")
    os.makedirs(planning, exist_ok=True)
    wbs = os.path.join(skills, "wbs-manager", "scripts")
    reg, conv = os.path.join(planning, "WBS Demo.json"), os.path.join(proj, "conventions.json")
    records = os.path.join(proj, "records")
    for cmd in ([os.path.join(wbs, "create_wbs.py"), reg, "Demo"],
                [os.path.join(wbs, "wbs.py"), "sprints", "seed", conv, "--scope", "Demo",
                 "--year", "2026", "--anchor", "2026-07-19"],
                [os.path.join(wbs, "wbs.py"), "sprints", "import", reg, "--from", conv],
                [os.path.join(skills, "sprint-facilitator", "scripts", "sprint_record.py"),
                 "plan", records, "S26.Q4.1", "--calendar", conv]):
        ok, out = run(cmd, scratch)
        if not check("setup: %s" % os.path.basename(cmd[0]), ok, out[-300:]):
            return
    brief = (u"# Demo — Project Brief\n\n**Size:** lean · **Written:** 2026-10-01 · **Last revised:** 2026-10-01 · **Serves:** G-1\n\n"
             u"> **To** test the tool **so that** the brief has one reader.\n\n## Why\n\nBecause.\n\n## Outcome and done-when\n\n"
             u"The brief is read the same way everywhere.\n\nDone when:\n\n1. Read.\n\n**Stop if:** nobody reads it.\n")
    io.open(os.path.join(planning, "Project Brief.md"), "w", encoding="utf-8").write(brief)

    def status(day):
        ok, out = run([report, "status", planning, "--records", records, "--sprint", "S26.Q4.1",
                       "--as-of", day], scratch)
        path = os.path.join(planning, "Reports", "Status", "%s Status.json" % day)
        return ok, out, (json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else {})

    ok, out, rec = status("2026-10-12")
    check("without it, the status report says the brief's tool is not installed, and runs on",
          ok and "not installed" in ((rec.get("outcome") or {}).get("reason") or ""), (str(rec.get("outcome")) + out)[:400])
    ok, out = run([installer, "add", "project-definition-manager", "--into", proj, "--catalogue", root], scratch)
    check("install.py add project-definition-manager succeeds", ok, out[-300:])
    ok, out, rec = status("2026-10-13")
    o = rec.get("outcome") or {}
    check("with it, the status report takes the outcome and what it serves from the brief",
          ok and o.get("outcome") == "The brief is read the same way everywhere." and o.get("serves") == "G-1", str(o)[:400])
    pd = os.path.join(skills, "project-definition-manager", "scripts", "brief.py")
    ok, out = run([pd, "check", planning, "--today", "2026-12-01"], scratch)
    check("check, as the weekly review runs it, names a brief due a revisit",
          not ok and "revisit due: last revised 2026-10-01" in out, out[-300:])
    ok, out = run([pd, "check", proj, "--wbs", "--today", "2026-10-11"], scratch)
    check("a project folder resolves to its brief, and a lean one with a WBS is told to grow",
          "grow it to full" in out, out[-300:])


def test_reporting(root, scratch):
    """Both reports, end to end, on a project built with AKOS's own tools.

    Nothing is copied from anywhere: the WBS, the RAID register and the sprint
    records are made by their own scripts, the way a new user would make them,
    so a report that runs here runs on anything those tools produce.
    """
    import json
    print("\nTSP.10 Reporting")
    tool = os.path.join(root, "TSP", REPORT_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    check("TD.10 present", any(n.startswith("TD.10") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), str(broken_links(tool))[:200])
    report = os.path.join(tool, "reporting", "scripts", "report.py")
    wbs_dir = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    wbs = os.path.join(wbs_dir, "wbs.py")
    raid = os.path.join(root, "TSP", "TSP.2 RAID Register", "raid-manager", "scripts", "raid.py")
    sr = os.path.join(root, "TSP", SPRINT_TOOL, "sprint-facilitator", "scripts", "sprint_record.py")

    work = os.path.join(scratch, "reporting")
    project, records = os.path.join(work, "atlas"), os.path.join(work, "records")
    os.makedirs(project)
    reg, conv = os.path.join(project, "WBS Atlas.json"), os.path.join(work, "conventions.json")
    raid_reg = os.path.join(project, "RAID Atlas.json")
    for label, cmd in [
            ("create the WBS", [os.path.join(wbs_dir, "create_wbs.py"), reg, "Atlas"]),
            ("seed and import a calendar", [wbs, "sprints", "seed", conv, "--scope", "Atlas",
                                            "--year", "2026", "--anchor", "2026-07-19"]),
            ("", [wbs, "sprints", "import", reg, "--from", conv]),
            ("a key deliverable", [wbs, "add", reg, "Website", "--type", "Deliverable",
                                   "--key-deliverable", "Y", "--baseline-end", "2026-Nov-30"]),
            ("two stories committed", [wbs, "add", reg, "Login page", "--parent", "1",
                                       "--sprint-planned", "S26.Q4.1"]),
            ("", [wbs, "add", reg, "Signup page", "--parent", "1", "--sprint-planned", "S26.Q4.1"]),
            ("one of them done", [wbs, "set", reg, "--id", "2", "--status", "Done", "--closure",
                                  "What happened: shipped. AC: (1) met. Follow-up: none."]),
            ("a RAID register with a risk",
             [os.path.join(os.path.dirname(raid), "create_raid.py"), raid_reg, "Atlas"]),
            ("", [raid, "add", raid_reg, "Design late", "--type", "Risk",
                  "--because-of", "a shared designer", "--risk-that", "signup slips",
                  "--may-result-in", "a late launch"]),
            ("plan the last sprint and this one", [sr, "plan", records, "S26.Q3.7", "--calendar", conv]),
            ("", [sr, "plan", records, "S26.Q4.1", "--calendar", conv])]:
        ok, out = run(cmd, work)
        if not ok or label:
            if not check(label or "setup", ok, out[:300]):
                return
    path = os.path.join(records, "S26.Q4.1.md")
    text = io.open(path, encoding="utf-8").read()
    text = text.replace("**Capacity:** _h available_ · _h planned_", "**Capacity:** 40h available · 30h planned")
    text = text.replace("|  |  |  |  |  |\n\n### Committed", "| G1 | Signup is live | Signup accepts users |  |  |\n\n### Committed", 1)
    text = text.replace("| Item | Effort | Area | Goal | Notes |\n|---|---|---|---|---|\n|  |  |  |  |  |",
                        "| Item | Effort | Area | Goal | Notes |\n|---|---|---|---|---|\n| Atlas#3 Signup page | 4h | Product | G1 |  |")
    text = text.replace("|  |  |  |\n\n### Iteration goals", "| Sam | 4 |  |\n\n### Iteration goals", 1)
    io.open(path, "w", encoding="utf-8").write(text)

    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-14"], work)
    status = os.path.join(project, "Reports", "Status", "2026-10-14 Status.json")
    check("status writes a record and a view",
          ok and os.path.exists(status) and os.path.exists(status[:-5] + ".html"), out[:300])
    rec = json.load(io.open(status, encoding="utf-8")) if os.path.exists(status) else {}
    sig = rec.get("signals") or {}
    check("the four signals are proposed with evidence, and Mood from the fist of five",
          all(sig.get(k, {}).get("evidence") for k in ("time", "scope", "quality", "resources"))
          and "mood" in sig, str(sorted(sig))[:200])
    check("the top risk comes from the RAID register",
          any(r.get("detail") == "Design late" for r in rec.get("risks") or []), str(rec.get("risks"))[:200])
    ok, _ = run([report, "confirm", status, "--signal", "time", "--rating", "red"], work)
    check("an override without a reason is refused", not ok)
    ok, out = run([report, "confirm", status, "--signal", "all"], work)
    check("confirm all accepts the proposals", ok, out[:200])
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-14"], work)
    check("a same-day rerun refuses to drop confirmed ratings", not ok, out[:200])

    ok, out = run([report, "sprint", "--sprint", "S26.Q4.2", "--records", records,
                   "--project", project], work)
    check("a sprint not yet planned is refused", not ok and "has not been planned" in out, out[:200])
    ok, out = run([report, "sprint", "--sprint", "S26.Q4.1", "--records", records,
                   "--project", project, "--as-of", "2026-10-14"], work)
    update = os.path.join(work, "Reports", "Sprint Update", "S26.Q4.1 Sprint Update.json")
    check("the sprint update lands beside the records", ok and os.path.exists(update), out[:300])
    rec = json.load(io.open(update, encoding="utf-8")) if os.path.exists(update) else {}
    lanes = [l for p in (rec.get("board") or {}).get("projects") or [] for l in p["lanes"]]
    check("this sprint's goals, capacity, confidence and hours by area are read",
          (rec.get("this") or {}).get("goals") and (rec.get("capacity") or {}).get("available") == 40
          and rec.get("mood") == 4 and (rec.get("area") or {}).get("Product") == 4, str(rec.get("area")))
    check("the board puts both cards in the deliverable's lane",
          len(lanes) == 1 and lanes[0]["id"] == 1 and len(lanes[0]["cards"]) == 2, str(lanes)[:300])
    page = io.open(update[:-5] + ".html", encoding="utf-8").read() if os.path.exists(update) else ""
    check("the board is on its own tab", 'id="v-board"' in page and "Sprint board" in page)
    ok, _ = run([report, "confirm", update, "--summary", "Smoke summary."], work)
    ok, _ = run([report, "sprint", "--sprint", "S26.Q4.1", "--records", records,
                 "--project", project, "--as-of", "2026-10-15"], work)
    kept = json.load(io.open(update, encoding="utf-8")).get("summary", {}).get("text") if ok else None
    check("a rerun mid-sprint keeps the confirmed summary", kept == "Smoke summary.", str(kept))

    # --- the brief: outcome and measures in the status report -----------------
    brief = os.path.join(project, "Project Brief.md")
    template = io.open(os.path.join(root, "TSP", PD_TOOL, "project-definition-manager", "templates",
                                    "Project Brief.md"), encoding="utf-8").read()
    io.open(brief, "w", encoding="utf-8").write(template)
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-17"], work)
    rec = json.load(io.open(os.path.join(project, "Reports", "Status", "2026-10-17 Status.json"),
                            encoding="utf-8")) if ok else {}
    check("the brief template, unfilled, reads as findings to fix, not a failure",
          ok and (rec.get("outcome") or {}).get("findings"), out[:300])
    filled = (u"# Atlas — Project Brief\n\n**Size:** full · **Written:** 2026-10-01 · **Serves:** OBJ-1\n\n"
              u"> **To** ship the website **so that** customers can sign up.\n\n## Outcome and done-when\n\n"
              u"Customers sign up on their own.\n\nDone when:\n\n1. Signup is live.\n\n### Measures\n\n"
              u"| ID | Measure | Role | Kind | C/A | Baseline | From | Target | By | How measured | Every | Current | As of | Source | WBS |\n"
              u"|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
              u"| M1 | Signups | lag | N | C | 0 | 2026-10-01 | 100 | 2026-12-31 | count | month | 30 | 2026-10-15 | measured | |\n"
              u"| M2 | Launch | lead | M | C | not done | 2026-10-01 | done | 2026-10-10 | release | month | not done | 2026-10-15 | asked | 3 |\n")
    io.open(brief, "w", encoding="utf-8").write(filled)
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-18"], work)
    rec = json.load(io.open(os.path.join(project, "Reports", "Status", "2026-10-18 Status.json"),
                            encoding="utf-8")) if ok else {}
    o = rec.get("outcome") or {}
    ms = {m["id"]: m for m in o.get("measures") or []}
    check("the outcome, what it serves and the done-when come from the brief",
          o.get("outcome") == "Customers sign up on their own." and o.get("serves") == "OBJ-1"
          and o.get("done_when") == ["Signup is live."], str(o)[:300])
    check("measures are scored, and a milestone past its date makes On Outcome red",
          (ms.get("M1") or {}).get("score") == 0.3 and "past due" in (ms.get("M2") or {}).get("flags", [])
          and (rec.get("signals") or {}).get("outcome", {}).get("proposed") == "red", str(ms)[:300])
    page = io.open(os.path.join(project, "Reports", "Status", "2026-10-18 Status.html"), encoding="utf-8").read() if ok else ""
    check("the view opens with the Outcome section, its explanation behind an info icon", "<h2>Outcome<span class=\"info\"" in page and "On Outcome" in page)
    io.open(brief, "w", encoding="utf-8").write(filled.split("### Measures")[0])
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-19"], work)
    rec = json.load(io.open(os.path.join(project, "Reports", "Status", "2026-10-19 Status.json"),
                            encoding="utf-8")) if ok else {}
    check("a lean brief, with no Measures table, proposes no On Outcome",
          ok and "outcome" not in rec.get("signals", {}) and not rec["outcome"]["present"], out[:300])
    os.remove(brief)

    # --- audiences, the external copy and the charter ---------------------------
    io.open(brief, "w", encoding="utf-8").write(filled + u"\n## Scope\n\nThe signup flow, nothing else.\n")
    stk = os.path.join(root, "TSP", "TSP.13 Stakeholder Register", "stakeholder-manager", "scripts")
    for label, cmd in [
            ("a stakeholder register", [os.path.join(stk, "create_stk.py"), project, "--scope", "Atlas"]),
            ("", [os.path.join(stk, "stk.py"), "add-group", project, "Steering group"]),
            ("", [os.path.join(stk, "stk.py"), "add", project, "Sam Owner", "--role", "Project manager",
                  "--groups", "G.1"]),
            ("", [os.path.join(stk, "stk.py"), "add", project, "Kim Client", "--role", "Client lead",
                  "--groups", "G.1", "--share", "external"]),
            ("", [os.path.join(stk, "stk.py"), "add-comm", project, "Status report", "--report", "status-report",
                  "--mode", "push", "--audience", "G.1", "--cadence", "per sprint", "--channel", "email"])]:
        ok, out = run(cmd, work)
        if not ok or label:
            if not check(label or "stakeholder setup", ok, out[:300]):
                return
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-20"], work)
    status = os.path.join(project, "Reports", "Status", "2026-10-20 Status.json")
    rec = json.load(io.open(status, encoding="utf-8")) if ok else {}
    comms = (rec.get("audiences") or {}).get("comms") or []
    check("a status report records who receives it, from the stakeholder register",
          len(comms) == 1 and comms[0]["share_level"] == "external"
          and sorted(comms[0]["recipients"]) == ["Kim Client", "Sam Owner"], str(rec.get("audiences"))[:300])
    page = io.open(status[:-5] + ".html", encoding="utf-8").read() if ok else ""
    check("the owner's view says who receives it", "Who receives this" in page and "Kim Client" in page)
    ok, out = run([report, "export", status, "--comm", "C.1"], work)
    check("an unconfirmed report is not shared", not ok, out[:300])
    run([report, "confirm", status, "--signal", "all"], work)
    run([report, "confirm", status, "--summary", "Signup is on its way."], work)
    shared = status[:-5] + " (external).html"
    ok, out = run([report, "export", status, "--comm", "C.1"], work)
    html = io.open(shared, encoding="utf-8").read() if os.path.exists(shared) else ""
    check("export --comm writes the external copy, holding back a risk not marked Sharable",
          ok and html and "Design late" not in html and "Kim Client" not in html, out[:300])
    run([raid, "update", raid_reg, "--id", "1", "--set", "Sharable=Y", "-m", "the client knows", "--by", "Smoke"], work)
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-20", "--force"], work)
    run([report, "confirm", status, "--signal", "all"], work)
    run([report, "confirm", status, "--summary", "Signup is on its way."], work)
    ok, out = run([report, "export", status, "--comm", "C.1"], work)
    html = io.open(shared, encoding="utf-8").read() if os.path.exists(shared) else ""
    check("a risk marked Sharable reaches the external copy", ok and "Design late" in html, out[:300])

    ok, out = run([report, "charter", project, "--as-of", "2026-10-20"], work)
    charter = os.path.join(project, "Reports", "Charter", "2026-10-20 Charter.json")
    page = io.open(charter[:-5] + ".html", encoding="utf-8").read() if os.path.exists(charter) else ""
    check("charter: one page from the brief and the registers, each section naming its source",
          ok and "ship the website" in page and "The signup flow" in page and "From the WBS" in page
          and "From the Stakeholder Register" in page and "Design late" in page, out[:300])
    check("charter: the owner's copy names the stakeholders", "Kim Client" in page)
    ok, out = run([report, "export", charter], work)
    shared = charter[:-5] + " (external).html"
    html = io.open(shared, encoding="utf-8").read() if os.path.exists(shared) else ""
    check("charter: the shared copy shows roles and groups, never names",
          ok and "Client lead" in html and "Kim Client" not in html, out[:300])

    # --- a project folder holding a lock and a numbered reports folder ----------
    io.open(os.path.join(project, "tools.lock.json"), "w", encoding="utf-8").write('{"source": "x", "tools": {}}')
    os.makedirs(os.path.join(project, "05. Reports"), exist_ok=True)
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-21"], work)
    check("a JSON that is not a register (a lock) is skipped, not fatal", ok, out[-300:])
    check("a numbered reports folder is used as the project's reports folder",
          os.path.isfile(os.path.join(project, "05. Reports", "Status", "2026-10-21 Status.json")), out[-200:])
    os.remove(brief)

    # --- installed together with what it needs, it finds its siblings ----------
    target = os.path.join(scratch, "report-project")
    os.makedirs(target)
    for name in ("reporting", "wbs-manager", "sprint-facilitator"):
        ok, out = run([os.path.join(root, "install.py"), "add", name, "--into", target,
                       "--catalogue", root], root)
        if not check("install.py add %s" % name, ok, out[:300]):
            return
    installed = os.path.join(target, ".agents", "skills", "reporting", "scripts", "report.py")
    ok, out = run([installed, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-16"], work)
    check("the installed copy finds wbs-manager and sprint-facilitator beside it", ok, out[:300])


DAILY_TOOL = "TSP.9 Daily Loop"
DAILY_SKILL = "daily-loop-facilitator"
DAILY_RETIRED = ["standup-facilitator", "morning-planner"]
DAY_SECTIONS = ["## Today's update", "## Next steps", "## Risks/Blockers",
                "## Notes", "### Morning"]


def test_daily_loop(root, scratch):
    """TSP.9 has no code; what can break is the contract between its flows.

    The morning creates the day's record from the skill's template, and each
    flow reads what the other wrote: the morning reads `status: closed` and the
    evening's frogs, the evening reads `### Morning`. If one flow's wording
    drifts from the other's, a record one writes is one the other cannot read,
    and nothing fails until a real morning. So the skill is split at its flow
    headings and each marker is asserted where it is written and where it is
    read.
    """
    print("\nTSP.9 Daily Loop")
    tool = os.path.join(root, "TSP", DAILY_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    path = os.path.join(tool, DAILY_SKILL, "SKILL.md")
    if not check("%s has SKILL.md" % DAILY_SKILL, os.path.isfile(path), path):
        return
    text = io.open(path, encoding="utf-8").read()
    check("%s declares name and description" % DAILY_SKILL,
          "name: %s" % DAILY_SKILL in text[:300] and "description:" in text[:300],
          text[:120])
    stale = [n for n in DAILY_RETIRED if os.path.exists(os.path.join(tool, n))]
    check("the skills it replaced no longer ship", not stale, ", ".join(stale))
    check("TD.9 present", any(n.startswith("TD.9") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool),
          "; ".join(broken_links(tool)[:5]))

    block = re.search(r"```markdown\n(---\nkind: day-record.*?)```", text, re.S)
    if not check("the skill owns a day-record template", bool(block)):
        return
    template = block.group(1)
    missing = [s for s in DAY_SECTIONS if s not in template]
    check("the template holds the four sections and ### Morning", not missing,
          ", ".join(missing))
    flows = re.search(r"\n## Morning\n(.*?)\n## Evening\n(.*?)\n## ", text, re.S)
    if not check("the skill has a Morning and an Evening flow", bool(flows)):
        return
    morning, evening = flows.group(1), flows.group(2)
    check("the morning reads the evening's frogs where the evening writes them",
          "Next steps" in morning and "**Frogs for tomorrow:**" in evening)
    check("the evening reads the morning's frogs where the morning writes them",
          "### Morning" in evening and "**Frogs:**" in morning)
    check("the morning reads whether the evening closed the record",
          "status: closed" in morning)
    wbs_src = io.open(os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts", "wbs.py"),
                      encoding="utf-8").read()
    check("the evening runs the pull-in check, a command wbs.py offers",
          "wbs.py pullins" in evening and 'add_parser("pullins"' in wbs_src)

    sr = os.path.join(root, "TSP", "TSP.8 Sprint Ceremonies", "sprint-facilitator",
                      "scripts", "sprint_record.py")
    named = re.findall(r"sprint_record\.py\s+([a-z]+)", evening)
    offered = set(re.findall(r'add_parser\(\s*"([a-z]+)"', io.open(sr, encoding="utf-8").read()))
    check("the ceremony command the evening names exists",
          named and all(c in offered for c in named), str(named))

    project = os.path.join(scratch, "daily-project")
    os.makedirs(project, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", DAILY_SKILL,
                   "--into", project, "--catalogue", root], root)
    check("install.py add %s" % DAILY_SKILL, ok, out)


WEEKLY_TOOL = "TSP.11 Weekly Review"
WEEKLY_SKILL = "weekly-review-facilitator"
WEEK_SECTIONS = ["## Get clear", "## Last week", "## Beyond the sprint", "## Sprint check",
                 "## The week ahead", "## Notes"]


def test_weekly_review(root, scratch):
    """TSP.11 has no code; what can break is its record and the commands it names.

    The record's date is what the daily loop's evening reads to say a week went
    without a review, so the template's kind and sections are asserted, and the
    evening is checked for the weekly check. The review runs other tools'
    scripts (sprint_record.py goals, report.py sprint); a renamed command would
    fail only in a real review, so each one the skill names must exist.
    """
    print("\nTSP.11 Weekly Review")
    tool = os.path.join(root, "TSP", WEEKLY_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    path = os.path.join(tool, WEEKLY_SKILL, "SKILL.md")
    if not check("%s has SKILL.md" % WEEKLY_SKILL, os.path.isfile(path), path):
        return
    text = io.open(path, encoding="utf-8").read()
    check("%s declares name and description" % WEEKLY_SKILL,
          "name: %s" % WEEKLY_SKILL in text[:300] and "description:" in text[:300], text[:120])
    check("TD.11 present", any(n.startswith("TD.11") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), "; ".join(broken_links(tool)[:5]))

    block = re.search(r"```markdown\n(---\nkind: weekly-record.*?)```", text, re.S)
    if not check("the skill owns a weekly-record template", bool(block)):
        return
    template = block.group(1)
    missing = [x for x in WEEK_SECTIONS if x not in template]
    check("the template holds every section", not missing, ", ".join(missing))
    check("the template carries the sprint and whether it is a planning day",
          "sprint:" in template and "planning_day:" in template)

    for script, rel in (("sprint_record.py", ("TSP.8 Sprint Ceremonies", "sprint-facilitator", "scripts", "sprint_record.py")),
                        ("report.py", ("TSP.10 Reporting", "reporting", "scripts", "report.py")),
                        ("stk.py", ("TSP.13 Stakeholder Register", "stakeholder-manager", "scripts", "stk.py"))):
        src = io.open(os.path.join(root, "TSP", *rel), encoding="utf-8").read()
        named = re.findall(r"%s\s+([a-z]+)" % re.escape(script), text)
        offered = set(re.findall(r'add_parser\(\s*"([a-z]+)"', src))
        check("every %s command the review names exists" % script,
              named and all(c in offered for c in named), str(named))

    daily = io.open(os.path.join(root, "TSP", DAILY_TOOL, DAILY_SKILL, "SKILL.md"), encoding="utf-8").read()
    evening = daily.split("\n## Evening\n", 1)[-1]
    check("the daily loop's evening checks for a weekly record",
          "kind: weekly-record" in evening and WEEKLY_SKILL in evening)
    check("the sprint check reads the stakeholder registers, overdue and gaps",
          "stk.py due --all --overdue" in text and "stk.py gaps --all" in text)

    project = os.path.join(scratch, "weekly-project")
    os.makedirs(project, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", WEEKLY_SKILL,
                   "--into", project, "--catalogue", root], root)
    check("install.py add %s" % WEEKLY_SKILL, ok, out)


TRACKER_TOOL = "TSP.12 Action Tracker"
TRACKER_SKILL = "action-tracker-manager"
TRACKER_META = ["scope:", "owner:", "anchor:", "related_wbs:", "related_raid:",
                "created:", "last_reviewed:", "status:"]
TRACKER_SECTIONS = ["## Current position", "## Sections", "## Status key", "## Attention required",
                    "### Actions", "## Closed actions", "## Update history"]
TRACKER_STATUS = ["⬜ Not Started", "🔄 In Progress", "⛔ Blocked", "✅ Done", "🚫 Cancelled"]


def test_action_tracker(root, scratch):
    """TSP.12 has no code; what can break is the template and the rules around it.

    A tracker is edited by hand and by the agent, so the template is the only
    shape every tracker starts from: its meta keys, its sections, the five
    status values, and the Status column that tells a dropped action from a
    delivered one. The two date rules the walk-through added (a dated Latest
    update, a TBD's checkpoint in the Due date cell) must survive in both the
    template and the conventions, and the weekly review must still read the
    trackers. Create, update and close are exercised in the walk-through in
    TD.12, since there is no script to run.
    """
    print("\nTSP.12 Action Tracker")
    tool = os.path.join(root, "TSP", TRACKER_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    skill = os.path.join(tool, TRACKER_SKILL)
    path = os.path.join(skill, "SKILL.md")
    if not check("%s has SKILL.md" % TRACKER_SKILL, os.path.isfile(path), path):
        return
    text = io.open(path, encoding="utf-8").read()
    check("%s declares name and description" % TRACKER_SKILL,
          "name: %s" % TRACKER_SKILL in text[:300] and "description:" in text[:300], text[:120])
    check("TD.12 present", any(n.startswith("TD.12") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool), "; ".join(broken_links(tool)[:5]))
    check("the tool ships no scripts", not os.path.isdir(os.path.join(skill, "scripts")))

    template_path = os.path.join(skill, "templates", "action-tracker.md")
    if not check("the template is shipped", os.path.isfile(template_path), template_path):
        return
    template = io.open(template_path, encoding="utf-8").read()
    meta = re.match(r"<!-- action-tracker-meta\n(.*?)-->", template, re.S)
    check("the template opens with the meta block", bool(meta), template[:80])
    missing = [k for k in TRACKER_META if not meta or k not in meta.group(1)]
    check("the meta block holds every key", not missing, ", ".join(missing))
    missing = [x for x in TRACKER_SECTIONS if x not in template]
    check("the template holds every section", not missing, ", ".join(missing))
    missing = [x for x in TRACKER_STATUS if x not in template]
    check("the template names the five status values", not missing, ", ".join(missing))
    closed = template.split("## Closed actions", 1)[-1].split("\n|", 1)[-1].split("\n", 1)[0]
    check("closed actions keep their Status", "Status" in closed, closed)
    check("the template's TBD carries its checkpoint", "TBD · checkpoint YYYY-MM-DD" in template)

    conv_path = os.path.join(skill, "references", "conventions.md")
    if check("the conventions are shipped", os.path.isfile(conv_path), conv_path):
        conv = io.open(conv_path, encoding="utf-8").read()
        check("the conventions state the ID, checkpoint and dated-update rules",
              "<CODE>-NN" in conv and "TBD · checkpoint" in conv and "opens with its date" in conv)

    weekly = io.open(os.path.join(root, "TSP", WEEKLY_TOOL, WEEKLY_SKILL, "SKILL.md"), encoding="utf-8").read()
    check("the weekly review reads the trackers",
          "action-tracker-meta" in weekly and TRACKER_SKILL in weekly)

    project = os.path.join(scratch, "tracker-project")
    os.makedirs(project, exist_ok=True)
    ok, out = run([os.path.join(root, "install.py"), "add", TRACKER_SKILL,
                   "--into", project, "--catalogue", root], root)
    check("install.py add %s" % TRACKER_SKILL, ok, out)


def test_tsp_fields(root, scratch):
    """A row written by tsp.py must be a row the dashboard can show.

    An empty register cannot catch this, which is why test_tool did not: the
    script wrote one column name and the dashboard read another, and every
    tool rendered with a blank name. So register a tool, then check what was
    written against what the template reads.
    """
    print("\nTSP.3 field names")
    skill = os.path.join(root, "TSP", "TSP.3 TSP Register", "tsp-manager")
    register = os.path.join(scratch, "fields", "TSP Register.json")
    os.makedirs(os.path.dirname(register), exist_ok=True)
    ok, out = run([os.path.join(skill, "scripts", "create_tsp.py"), register], scratch)
    if not check("create runs", ok, out):
        return
    ok, out = run([os.path.join(skill, "scripts", "tsp.py"), "register", register,
                   "Probe Tool", "--type", "Tool", "--area", "Probe Area"], scratch)
    if not check("register a tool", ok, out):
        return
    import json
    row = json.load(io.open(register, encoding="utf-8"))["tools"][0]
    check("the area is written as Primary Area",
          row.get("Primary Area") == "Probe Area" and "Primary AF" not in row,
          str(row))
    template = io.open(os.path.join(skill, "templates", "dashboard.html"),
                       encoding="utf-8").read()
    reads = [l for l in template.splitlines() if "Tool/System Name" in l]
    check("the dashboard reads the Name column it is given",
          reads and all("t.Name" in l for l in reads),
          "; ".join(l.strip()[:80] for l in reads))
    check("the dashboard reads the Primary Area column it is given",
          "t['Primary Area']" in template)


def test_sync_commands(root, scratch):
    """The commands the WBS, RAID and TSP registers gained, each run for real.

    test_tool builds empty registers, so none of these would be exercised by
    it: a close refused without a note, a carried sprint, the planning
    checks, the RAID reference they read, and a retired control dropping out
    of what is due. Each is driven through its command line, the way a user
    or an agent would.
    """
    import json
    print("\nRegister commands")
    work = os.path.join(scratch, "sync")
    os.makedirs(work, exist_ok=True)
    wbs = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts", "wbs.py")
    raid_dir = os.path.join(root, "TSP", "TSP.2 RAID Register", "raid-manager", "scripts")
    tsp_dir = os.path.join(root, "TSP", "TSP.3 TSP Register", "tsp-manager", "scripts")

    # --- WBS ---------------------------------------------------------------
    reg = os.path.join(work, "WBS Atlas.json")
    conv = os.path.join(work, "conventions.json")
    steps = [
        ("create", [os.path.join(os.path.dirname(wbs), "create_wbs.py"), reg, "Atlas"]),
        ("seed a sprint calendar", [wbs, "sprints", "seed", conv, "--scope", "Atlas",
                                    "--year", "2026", "--anchor", "2026-07-19"]),
        ("import it", [wbs, "sprints", "import", reg, "--from", conv]),
        ("add a deliverable", [wbs, "add", reg, "Website", "--type", "Deliverable"]),
        ("mark it key", [wbs, "set", reg, "--id", "1", "--key-deliverable", "Y"]),
        ("add a story", [wbs, "add", reg, "Login page", "--type", "Story", "--parent", "1"]),
        ("plan it into a sprint", [wbs, "set", reg, "--id", "2", "--sprint-planned", "S26.Q3.6"]),
    ]
    for label, cmd in steps:
        ok, out = run(cmd, work)
        if not check("wbs: %s" % label, ok, out):
            return
    row = [r for r in json.load(io.open(reg, encoding="utf-8"))["items"] if r["ID"] == 2][0]
    check("wbs: committing a backlog row moves it to Not Started",
          row.get("Status") == "Not Started", str(row.get("Status")))
    ok, out = run([wbs, "add", reg, "Signup page", "--parent", "1",
                   "--status", "Implementing"], work)
    row = [r for r in json.load(io.open(reg, encoding="utf-8"))["items"] if r["ID"] == 3][0]
    check("wbs: add stamps Actual Start on an Implementing row, and says so",
          ok and row.get("Actual Start") and "stamped" in out, out[:200])
    ok, out = run([wbs, "set", reg, "--id", "2", "--planned-end", "2026-Sep-26"], work)
    check("wbs: a first planned date needs no reason", ok, out)
    ok, _ = run([wbs, "set", reg, "--id", "2", "--planned-end", "2026-Oct-10"], work)
    check("wbs: moving a planned date without a reason is refused", not ok)
    ok, out = run([wbs, "set", reg, "--id", "2", "--planned-end", "2026-Oct-10",
                   "--reason", "design slipped"], work)
    log = json.load(io.open(reg, encoding="utf-8")).get("schedule_log") or []
    check("wbs: a move with a reason is logged, the first value is not",
          ok and len(log) == 1 and log[0].get("From") == "2026-Sep-26", str(log)[:200])
    ok, _ = run([wbs, "set", reg, "--id", "2", "--sprint-carried", "S26.Q3.7"], work)
    check("wbs: a carried sprint without a reason is refused", not ok)
    ok, out = run([wbs, "set", reg, "--id", "2", "--sprint-carried", "S26.Q3.7",
                   "--reason", "blocked on design"], work)
    check("wbs: a carried sprint with a reason is kept", ok, out)
    ok, out = run([wbs, "note", reg, "--id", "2", "Scope revised."], work)
    check("wbs: note runs", ok, out)
    ok, _ = run([wbs, "set", reg, "--id", "2", "--status", "Done"], work)
    check("wbs: a close without a closure note is refused", not ok)
    ok, out = run([wbs, "set", reg, "--id", "2", "--status", "Done", "--closure",
                   "What happened: shipped. AC: (1) met. Follow-up: none."], work)
    check("wbs: a close with a closure note runs", ok, out)
    row = [r for r in json.load(io.open(reg, encoding="utf-8"))["items"] if r["ID"] == 2][0]
    comments = row.get("Comments") or ""
    check("wbs: the closure note is pinned above the note",
          comments.startswith("Closure ") and "Scope revised." in comments, comments[:120])
    check("wbs: the carried sprint is recorded",
          row.get("Sprint Carried") == ["S26.Q3.7"], str(row.get("Sprint Carried")))
    ok, out = run([wbs, "metrics", reg, "--sprint", "S26.Q3.7", "--json"], work)
    try:
        m = json.JSONDecoder().raw_decode(out[out.index("{"):])[0] if ok else {}
    except ValueError:
        m = {}
    check("wbs: a carried row counts as committed to its new sprint",
          (m.get("committed") or {}).get("n") == 1, out[:200])
    ok, out = run([wbs, "deliverables", reg, "--sprint", "S26.Q3.7"], work)
    check("wbs: deliverables names the open Key Deliverable", ok and "Website" in out, out[:200])
    data = json.load(io.open(reg, encoding="utf-8"))
    data["items"].append({"ID": 4, "Title": "Orphan task", "Type": "Task",
                          "Status": "Portfolio Backlog", "Sprint Planned": "S26.Q3.7"})
    io.open(reg, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([wbs, "check", reg], work)
    check("wbs: check warns on a committed row still in the backlog",
          "a commitment means Not Started" in out, out[:300])
    html = os.path.join(work, "WBS Dashboard.html")
    ok, out = run([os.path.join(os.path.dirname(wbs), "refresh_wbs.py"), reg, html, "Atlas"], work)
    page = io.open(html, encoding="utf-8").read() if ok else ""
    try:
        boards = json.loads(page.split("const BOARDS=", 1)[1].split(";\n", 1)[0])
    except (IndexError, ValueError):
        boards = {}
    cards = (boards.get("S26.Q3.7") or {}).get("cards") or {}
    check("wbs: the Current Sprint board puts a card in its deliverable's lane, with its role",
          (cards.get("2") or {}).get("l") == 1 and (cards.get("2") or {}).get("r") == "Carried in",
          str(cards)[:200])
    check("wbs: a card with no parent has no lane",
          "4" in cards and cards["4"].get("l") is None, str(cards)[:200])

    # --- RAID, and the reference refined reads -------------------------------
    raid = os.path.join(work, "RAID Atlas.json")
    ok, out = run([os.path.join(raid_dir, "create_raid.py"), raid, "Atlas"], work)
    if not check("raid: create runs", ok, out):
        return
    data = json.load(io.open(raid, encoding="utf-8"))
    data["entries"] = [{"RAID.ID": 1, "Type": "Risk", "Status": "Open",
                        "Detail": "Design late", "WBS Ref": "Atlas 2"}]
    io.open(raid, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([os.path.join(raid_dir, "raid.py"), "check", raid], work)
    check("raid: a WBS Ref that is not project#id is reported", "WBS Ref" in out, out[:200])
    data["entries"][0]["WBS Ref"] = "Atlas#2"
    io.open(raid, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([wbs, "refined", reg, "--ids", "1,2", "--raid", raid], work)
    check("wbs: refined shows the open RAID entry against its row",
          ok and "Design late" in out, out[:300])
    check("wbs: refined reports a row with no description",
          ok and "no description" in out, out[:300])

    # --- TSP: a retired control is not due ------------------------------------
    treg = os.path.join(work, "TSP Register.json")
    for label, cmd in [
            ("create", [os.path.join(tsp_dir, "create_tsp.py"), treg]),
            ("register two tools", [os.path.join(tsp_dir, "tsp.py"), "register", treg,
                                    "Old Tool", "--type", "Tool"]),
            ("", [os.path.join(tsp_dir, "tsp.py"), "register", treg, "Live Tool", "--type", "Tool"]),
            ("retire one", [os.path.join(tsp_dir, "tsp.py"), "retire", treg, "--id", "1"])]:
        ok, out = run(cmd, work)
        if not ok or label:
            if not check("tsp: %s" % (label or "register"), ok, out):
                return
    data = json.load(io.open(treg, encoding="utf-8"))
    data["control_activities"] = [
        {"ID": 1, "Activity Name": "Check the old tool", "Frequency": "Monthly",
         "Importance": "Important", "Linked Tool": "Old Tool", "Next Due": "2020-01-01"},
        {"ID": 2, "Activity Name": "Check the live tool", "Frequency": "Monthly",
         "Importance": "Important", "Linked Tool": "Live Tool", "Next Due": "2020-01-01"}]
    io.open(treg, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run([os.path.join(tsp_dir, "tsp.py"), "due", treg], work)
    check("tsp: due lists the live tool's control",
          ok and "Check the live tool" in out, out[:300])
    check("tsp: due leaves out the retired tool's control",
          ok and "Check the old tool" not in out, out[:300])


def test_pull_ins(root, scratch):
    """Work the sprint never committed to asks first, and the daily check finds
    the pull-ins the record does not name.

    The calendar is built around today, so the gate is always live here. A row
    nobody committed to is refused until it is answered; a pull-in sets Sprint
    Added and prints its record line; a parent counts only when committed
    itself; `pullins` lists what the record lacks until the record names it.
    A split into an earlier sprint keeps later commitments off the delivered part.
    """
    import json
    from datetime import date, timedelta
    print("\nPull-ins")
    work = os.path.join(scratch, "pullins")
    plan = os.path.join(work, "planning")
    os.makedirs(plan, exist_ok=True)
    scripts = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    wbs = os.path.join(scripts, "wbs.py")
    reg = os.path.join(plan, "WBS Atlas.json")
    ok, out = run_raw([os.path.join(scripts, "create_wbs.py"), reg, "Atlas"], work)
    if not check("pull-ins: create", ok, out):
        return
    t = date.today()
    iso = lambda d: d.isoformat()
    data = json.load(io.open(reg, encoding="utf-8"))
    data["sprints"] = [
        {"Sprint": "S1", "Starts": iso(t - timedelta(days=28)), "Ends": iso(t - timedelta(days=15))},
        {"Sprint": "S2", "Starts": iso(t - timedelta(days=14)), "Ends": iso(t + timedelta(days=5))},
        {"Sprint": "S3", "Starts": iso(t + timedelta(days=6)), "Ends": iso(t + timedelta(days=19))}]
    story = lambda i, title, **kw: dict({"ID": i, "Title": title, "Type": "Story", "Class": "Product",
                                         "Nature": "Build", "Status": "Not Started",
                                         "Estimated Effort (h)": 1}, **kw)
    data["items"] = [
        dict(story(1, "Committed parent", **{"Sprint Planned": "S2"}), Type="Feature"),
        story(2, "Child of the committed parent", Parent=1),
        story(4, "Committed row", **{"Sprint Planned": "S2"}),
        story(6, "Uncommitted row to pull in"),
        story(8, "Uncommitted row worked outside"),
        story(10, "Uncommitted row, other edits"),
        story(11, "Uncommitted row, refused"),
        dict(story(12, "Uncommitted parent of a committed child"), Type="Feature"),
        story(13, "Committed child", Parent=12, **{"Sprint Planned": "S2"}),
        story(30, "Split me", Status="Implementing",
              **{"Sprint Planned": "S1", "Sprint Carried": ["S2", "S3"], "Estimated Effort (h)": 4}),
    ]
    io.open(reg, "w", encoding="utf-8").write(json.dumps(data, indent=2))
    record = os.path.join(plan, "S2.md")
    io.open(record, "w", encoding="utf-8").write(
        "# Sprint S2\n\n## Planning\n\n### Committed items\n\n| Item | Effort | Area | Goal | Notes |\n"
        "|---|---|---|---|---|\n| Atlas 1 Committed parent | 1h | |  | |\n| Atlas 4 Committed row | 1h | |  | |\n"
        "| Atlas 13 Committed child | 1h | |  | |\n")
    row = lambda rid: [r for r in json.load(io.open(reg, encoding="utf-8"))["items"] if r["ID"] == rid][0]

    ok, out = run_raw([wbs, "set", reg, "--id", "11", "--status", "Implementing"], work)
    check("pull-ins: starting an uncommitted row is refused, both answers shown",
          not ok and "--pulled-in" in out and "--outside-sprint" in out
          and row(11).get("Status") == "Not Started", out)
    ok, out = run_raw([wbs, "set", reg, "--id", "6", "--status", "Implementing",
                       "--pulled-in", "displaces nothing"], work)
    r6 = row(6)
    check("pull-ins: --pulled-in sets Sprint Added and notes the effect",
          ok and r6.get("Sprint Added") == "S2" and "effect: displaces nothing" in (r6.get("Comments") or ""), out)
    check("pull-ins: a pull-in prints its record line, Area left blank",
          "| Atlas 6 Uncommitted row to pull in | 1h |  |" in out and "**pulled in" in out, out)
    ok, out = run_raw([wbs, "set", reg, "--id", "8", "--status", "Implementing",
                       "--outside-sprint", "a correction of past work"], work)
    r8 = row(8)
    check("pull-ins: --outside-sprint notes why and marks nothing",
          ok and not r8.get("Sprint Added") and "outside the sprint" in (r8.get("Comments") or ""), out)
    ok, out = run_raw([wbs, "set", reg, "--id", "4", "--status", "Implementing"], work)
    check("pull-ins: a committed row starts with no question", ok, out)
    ok, out = run_raw([wbs, "set", reg, "--id", "2", "--status", "Implementing"], work)
    check("pull-ins: a child of a committed parent starts with no question", ok, out)
    ok, out = run_raw([wbs, "set", reg, "--id", "12", "--status", "Implementing"], work)
    check("pull-ins: a committed child does not commit its parent", not ok and "--pulled-in" in out, out)
    ok, out = run_raw([wbs, "set", reg, "--id", "10", "--priority", "Must"], work)
    check("pull-ins: other edits to an uncommitted row are not asked", ok, out)
    ok, out = run_raw([wbs, "set", reg, "--id", "4", "--status", "Done", "--closure",
                       "What happened: smoke. AC: none.", "--pulled-in", "displaces nothing"], work)
    check("pull-ins: an answer on a committed row is refused as not needed",
          not ok and "no answer is needed" in out, out)
    ok, out = run_raw([wbs, "add", reg, "New work, straight in", "--status", "Implementing"], work)
    check("pull-ins: adding a row straight into Implementing asks too", not ok and "--pulled-in" in out, out)

    ok, out = run_raw([wbs, "pullins", "--root", work], work)
    check("pullins: a pulled-in row the record does not name is listed, with its line",
          ok and "1 row(s) pulled into S2" in out and "| Atlas 6 " in out, out)
    with io.open(record, "a", encoding="utf-8") as fh:
        fh.write("| Atlas 6 Uncommitted row to pull in | 1h | |  | **pulled in**; effect: displaces nothing |\n")
    ok, out = run_raw([wbs, "pullins", "--root", work], work)
    check("pullins: once the record names it, nothing is missing",
          ok and "No pull-in into S2 is missing" in out, out)
    refs = os.path.join(work, "refs.md")
    io.open(refs, "w", encoding="utf-8").write(
        "### Committed items\n\n| Item | Effort |\n|---|---|\n| Atlas 145, 166 Reporting | 4h |\n"
        "| Atlas Web pilot (18, 3, 4) | 7h |\n| Atlas 20-22 Search | 3h |\n| ~~Atlas 99 Struck~~ | 1h |\n")
    code = ("import sys; sys.path.insert(0, %r); import wbs as W; "
            "print(sorted(W.record_refs(%r, ['Atlas'])))" % (scripts, refs))
    ok, out = run_raw(["-c", code], work)
    check("pullins: an item naming several rows, a range or a bracketed list names each",
          ok and all("('Atlas', %d)" % n in out for n in (145, 166, 18, 3, 4, 20, 21, 22))
          and "99" not in out, out)

    ok, out = run_raw([wbs, "split", reg, "--id", "30", "--sprint", "S1", "--delivered", "2", "--closure",
                       "What happened: smoke. AC: none. Follow-up: the rest piece."], work)
    pieces = [x for x in json.load(io.open(reg, encoding="utf-8"))["items"] if x.get("Parent") == 30]
    done = next((x for x in pieces if x.get("Status") == "Done"), {})
    rest = next((x for x in pieces if x.get("Status") != "Done"), {})
    check("split: the delivered part keeps only the commitments up to its sprint",
          ok and done.get("Sprint Planned") == "S1" and not done.get("Sprint Carried"), out if not ok else str(done))
    check("split: the rest keeps the whole history", rest.get("Sprint Carried") == ["S2", "S3"], str(rest))

    dash = os.path.join(work, "WBS Dashboard.html")
    ok, out = run_raw([os.path.join(scripts, "refresh_wbs.py"), reg, dash, "Atlas"], work)
    html = io.open(dash, encoding="utf-8").read() if ok else ""
    check("dashboard: a card's details link its parents (breadcrumb) and list its children",
          ok and "function ancestors(" in html and 'class="crumbs"' in html and "Children (" in html, out[-200:])
    check("dashboard: a sprint card links its direct parent only, the full chain in its tooltip",
          "p=a[a.length-1]" in html and 'class="kb-path" title=' in html and "a.map(crumbLink)" not in html)
    check("dashboard: the Sprints tab reads the sprint metrics (BOARDS), newest first, with the trend and velocity in Analytics",
          "['sprints','Sprints']" in html and "function sprintTrend(" in html and "sprintGroups" not in html
          and "[...list].reverse()" in html and "Velocity " in html)
    check("dashboard: the Breakdown shows level-1 bands, a guide per level and titles wrapped at their level",
          'class="tree-l1"' in html and 'class="guide"' in html and 'class="tcell"' in html and 'class="tt"' in html)
    check("dashboard: #item=<ID> opens a card, with Copy link and the browser's Back",
          "itemFromHash()" in html and "#item=" in html and "Copy link" in html and "hashchange" in html)


def test_raid_lessons(root, scratch):
    """Lessons as a RAID type and the page across projects; Trend read up as
    better; Sharable, what may leave the project.

    The page must read every register under a root, archived ones included, and
    lead with the reusable lessons. `migrate` must add what an older register
    lacks without touching a row, and list the trends already set, since their
    reading has turned round.
    """
    import json
    print("\nRAID lessons, trend and sharable")
    scripts = os.path.join(root, "TSP", "TSP.2 RAID Register", "raid-manager", "scripts")
    raid = os.path.join(scripts, "raid.py")
    work = os.path.join(scratch, "lessons")
    active = os.path.join(work, "Atlas", "planning", "RAID")
    archived = os.path.join(work, "Archive", "Old project", "planning")
    os.makedirs(active, exist_ok=True)
    os.makedirs(archived, exist_ok=True)
    reg = os.path.join(active, "RAID Atlas.json")
    old = os.path.join(archived, "RAID Old.json")
    load = lambda path: json.load(io.open(path, encoding="utf-8"))
    for path, scope in ((reg, "Atlas"), (old, "Old project")):
        ok, out = run_raw([os.path.join(scripts, "create_raid.py"), path, scope], work)
        if not check("raid: create %s" % scope, ok, out):
            return
    # The archived register predates Lessons and Sharable: strip what this version added.
    data = load(old)
    fields = data["meta"]["settings"]["fields"]
    key = "entries" if isinstance(fields, dict) else None
    if key:
        fields[key] = [f for f in fields[key] if f not in ("Reusable", "Applied By", "Sharable")]
    vocab = data["meta"]["settings"]["vocabularies"]
    vocab.pop("reusable", None)
    vocab.pop("sharable", None)
    vocab["type"].remove("Lesson")
    data["entries"] = [{"RAID.ID": 1, "Detail": "An old risk", "Type": "Risk", "Status": "Open", "Trend": u"\u2191",
                        "Description": "Because of x, there is a risk that y, which may result in z."}]
    io.open(old, "w", encoding="utf-8").write(json.dumps(data))

    ok, out = run_raw([raid, "add", reg, "Confirm a pull-in when work starts", "--type", "Lesson",
                       "--learned", "pull-ins go unrecorded when starting work asks nothing",
                       "--because", "most pull-ins reached the record only at the close-out",
                       "--next-time", "the tool asks pulled in or outside the sprint when work starts",
                       "--category", "Process", "--reusable", "Y", "--applied-by", "Atlas 14", "--by", "Smoke"], work)
    row = next((e for e in load(reg)["entries"] if e.get("Type") == "Lesson"), {})
    check("raid: a Lesson is added through its shape, with Reusable and Applied By",
          ok and row.get("Description", "").startswith("We learned that pull-ins")
          and row.get("Reusable") == "Y" and row.get("Applied By") == "Atlas 14", out)
    ok, out = run_raw([raid, "add", reg, "Half a lesson", "--type", "Lesson", "--learned", "something",
                       "--by", "Smoke"], work)
    check("raid: a Lesson missing a slot is refused, naming it", not ok and "--next-time" in out, out)
    ok, out = run_raw([raid, "add", reg, "A risk", "--type", "Risk", "--description",
                       "Because of a, there is a risk that b, which may result in c.",
                       "--reusable", "Y", "--by", "Smoke"], work)
    check("raid: --reusable belongs to a Lesson only", not ok and "belong to a Lesson" in out, out)
    run_raw([raid, "add", reg, "Freehand lesson", "--type", "Lesson", "--description", "Phones matter.",
             "--category", "Tooling", "--reusable", "N", "--by", "Smoke"], work)

    ok, out = run_raw([raid, "update", reg, "--id", "1", "--set", "Trend=better", "-m", "smoke", "--by", "Smoke"], work)
    check("raid: Trend takes the chip's short word, stored as the up arrow",
          ok and load(reg)["entries"][0].get("Trend") == u"\u2197", out)
    ok, out = run_raw([raid, "update", reg, "--id", "1", "--set", "Sharable=Y", "-m", "can be shared",
                       "--by", "Smoke"], work)
    check("raid: Sharable takes Y", ok and load(reg)["entries"][0].get("Sharable") == "Y", out)
    ok, out = run_raw([raid, "update", reg, "--id", "1", "--set", "Sharable=Maybe", "-m", "smoke",
                       "--by", "Smoke"], work)
    check("raid: Sharable holds to its vocabulary", not ok, out)

    before = load(old)["entries"]
    ok, out = run_raw([raid, "migrate", old, "--apply"], work)
    after = load(old)
    check("raid: migrate adds Lesson, Reusable, Applied By and Sharable, touching no row",
          ok and "Lesson" in after["meta"]["settings"]["vocabularies"]["type"]
          and "sharable" in after["meta"]["settings"]["vocabularies"] and after["entries"] == before, out)
    check("raid: migrate lists the trends already set, converting none",
          "1 entry carries a Trend" in out and "R.1" in out, out)
    run_raw([raid, "add", old, "An archived lesson", "--type", "Lesson", "--learned", "a", "--because", "b",
             "--next-time", "c", "--category", "Planning", "--reusable", "Y", "--by", "Smoke"], work)

    page = os.path.join(work, "Lessons.html")
    ok, out = run_raw([raid, "lessons", "--root", work, "--out", page], work)
    html = io.open(page, encoding="utf-8").read() if os.path.exists(page) else ""
    check("raid: lessons reads every register under the root, archived ones included",
          ok and "3 lesson(s) from 2 RAID register(s) (1 archived)" in out, out)
    check("raid: the page leads with reusable lessons, with what applied them",
          html.find("Confirm a pull-in") < html.find("Freehand lesson") and "An archived lesson" in html
          and "Atlas 14" in html, html[:300])

    board = os.path.join(active, "RAID Dashboard.html")
    ok, out = run_raw([os.path.join(scripts, "refresh_raid.py"), reg, board, "Atlas"], work)
    bhtml = io.open(board, encoding="utf-8").read() if os.path.exists(board) else ""
    check("raid: the board gives a Lesson its badge and fields",
          ok and ".badge-lesson" in bhtml and "'Applied By'" in bhtml, out)


def test_numbered_layout(root, scratch):
    """A project that numbers its folders (an artifact register writes its IDs
    into folder names) and holds an installer's lock: a new TSP register
    accepts the catalogue's status words, and the artifact disk check skips the
    files a tool owns while still flagging an unnumbered document."""
    import json
    print("\nNumbered project layout")
    work = os.path.join(scratch, "numbered")
    os.makedirs(work, exist_ok=True)
    tsp = os.path.join(root, "TSP", "TSP.3 TSP Register", "tsp-manager", "scripts")
    treg = os.path.join(work, "02. TSP Register.json")
    run_raw([os.path.join(tsp, "create_tsp.py"), treg], work)
    vocab = json.load(io.open(treg, encoding="utf-8"))["meta"]["settings"]["vocabularies"]["status"]
    check("layout: a new TSP register uses the catalogue's status words", "In Progress" in vocab, str(vocab))
    art = os.path.join(root, "TSP", "TSP.5 Artifact Register", "artifact-register", "scripts")
    areg = os.path.join(work, "04. Artifact Register, Demo.json")
    run_raw([os.path.join(art, "create_artifact_register.py"), areg, "Demo"], work)
    settings = json.load(io.open(areg, encoding="utf-8"))["meta"]["settings"]
    check("layout: a new artifact register ignores the installer's lock", "tools.lock.json" in settings.get("ignore", []),
          str(settings))
    io.open(os.path.join(work, "tools.lock.json"), "w", encoding="utf-8").write("{}")
    io.open(os.path.join(work, "Loose notes.md"), "w", encoding="utf-8").write("x")
    ok, out = run_raw([os.path.join(art, "audit_artifact_register.py"), areg, "--root", work], work)
    check("layout: the disk check skips the ignored lock and still flags an unnumbered file",
          "tools.lock.json" not in out and "Loose notes.md" in out, out[-400:])


def test_migrate_vocabulary(root, scratch):
    """migrate adds what a register's vocabulary lacks and never drops a value
    the project added: dropping one turns every row using it into an error."""
    import json
    print("\nMigrate keeps a register's own vocabulary")
    scripts = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    work = os.path.join(scratch, "vocab")
    os.makedirs(work, exist_ok=True)
    reg = os.path.join(work, "WBS Atlas.json")
    run_raw([os.path.join(scripts, "create_wbs.py"), reg, "Atlas"], work)
    data = json.load(io.open(reg, encoding="utf-8"))
    vocab = data["meta"]["settings"]["vocabularies"]
    vocab["delivers"] = ["Tool", "Document", "Capability"]
    vocab["status"] = ["Backlog" if v == "Portfolio Backlog" else v for v in vocab["status"]]
    data["items"] = [{"ID": 1, "Title": "A capability", "Type": "Feature", "Class": "Product", "Nature": "Build",
                      "Status": "Not Started", "Delivers": "Capability"}]
    io.open(reg, "w", encoding="utf-8").write(json.dumps(data))
    ok, out = run_raw([os.path.join(scripts, "wbs.py"), "migrate", reg, "--apply"], work)
    vocab = json.load(io.open(reg, encoding="utf-8"))["meta"]["settings"]["vocabularies"]
    check("migrate: the register's own value is kept, the standard's missing ones added",
          ok and "Capability" in vocab["delivers"] and "Process" in vocab["delivers"], out[:300])
    check("migrate: a renamed standard value is renamed in place",
          "Portfolio Backlog" in vocab["status"] and "Backlog" not in vocab["status"], str(vocab["status"]))
    ok, out = run_raw([os.path.join(scripts, "wbs.py"), "check", reg], work)
    check("migrate: rows using the register's own value still pass check", " 0 error(s)" in out, out[-200:])
    ok, out = run_raw([os.path.join(scripts, "wbs.py"), "migrate", reg], work)
    check("migrate: a second run has nothing to do", "0 change(s)" in out, out[:200])


def test_installer_docs(root, scratch):
    """--docs places a tool's TD in the project's TSP folder, locked as its own
    entry, and every command works on it while seeing the TD files only.

    The project here is a project-management folder, as at work: skills under
    its .agents/skills, TDs under its TSP folder. Upstream moves in a clone of
    the catalogue, so update has a real base, theirs and mine to merge.
    """
    import json
    print("\nInstaller: tool definitions (--docs)")
    installer = os.path.join(root, "install.py")
    project = os.path.join(scratch, "docs-project", "General", "0.PrjMgm")
    os.makedirs(project, exist_ok=True)
    lock_path = os.path.join(project, "tools.lock.json")
    td8 = os.path.join(project, "TSP", "TSP.8 Sprint Ceremonies", "TD.8 - Sprint Ceremonies.md")
    td4 = os.path.join(project, "TSP", "TSP.4 Tool Installer", "TD.4 - Tool Installer.md")

    ok, out = run_raw([installer, "add", "sprint-facilitator", "--into", project, "--catalogue", root,
                       "--docs", "TSP"], root)
    lock = json.load(io.open(lock_path, encoding="utf-8")) if os.path.exists(lock_path) else {"tools": {}}
    rec = lock["tools"].get("TSP.8 docs") or {}
    check("docs: add --docs places the skill and its TD, each locked",
          ok and os.path.isfile(td8) and "sprint-facilitator" in lock["tools"]
          and rec.get("only") == "TD" and list(rec.get("files") or {}) == ["TD.8 - Sprint Ceremonies.md"], out[:300])
    ok, out = run_raw([installer, "add", "sprint-planning-precheck", "--into", project, "--catalogue", root,
                       "--docs", "TSP"], root)
    check("docs: a second skill of the same tool reuses its TD", ok and "TD reused" in out, out[:300])
    ok, out = run_raw([installer, "add", "TSP.4", "--into", project, "--catalogue", root], root)
    check("docs: a tool ID without --docs is refused", not ok and "--docs" in out, out[:200])
    ok, out = run_raw([installer, "add", "TSP.4", "--into", project, "--catalogue", root, "--docs", "TSP"], root)
    check("docs: add TSP.4 --docs places a TD alone, for a tool with no skill",
          ok and os.path.isfile(td4) and not os.path.isdir(os.path.join(project, ".agents", "skills", "TSP.4")), out[:300])

    io.open(os.path.join(os.path.dirname(td4), "Our install notes.md"), "w", encoding="utf-8").write("ours\n")
    ok, out = run_raw([installer, "status", "--project", project, "--check"], root)
    check("docs: another file beside a TD is not drift", ok, out[-300:])
    with io.open(td4, "a", encoding="utf-8") as fh:
        fh.write("\n## Our adaptation\n\nInstalled into the PM folder.\n")
    ok, out = run_raw([installer, "status", "--project", project, "--check"], root)
    check("docs: an edited TD is reported", not ok and "TSP.4 docs" in out and "MODIFIED" in out, out[-300:])

    # Upstream moves: a clone of the catalogue with a change to TD.4's opening line.
    upstream = os.path.join(scratch, "docs-upstream")
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.check_call(["git", "clone", "-q", root, upstream], **quiet)
    up_td = os.path.join(upstream, "TSP", "TSP.4 Tool Installer", "TD.4 - Tool Installer.md")
    text = io.open(up_td, encoding="utf-8").read().split("\n")
    text[0] = text[0] + " (upstream revision)"
    io.open(up_td, "w", encoding="utf-8", newline="\n").write("\n".join(text))
    subprocess.check_call(["git", "-c", "user.email=smoke@test", "-c", "user.name=smoke", "commit", "-qam",
                           "upstream TD change"], cwd=upstream, **quiet)
    ok, out = run_raw([installer, "update", "TSP.4 docs", "--project", project, "--source", upstream], root)
    merged = io.open(td4, encoding="utf-8").read()
    check("docs: update merges the upstream TD change and keeps the local edit",
          ok and "(upstream revision)" in merged and "## Our adaptation" in merged
          and os.path.isfile(os.path.join(os.path.dirname(td4), "Our install notes.md")), out[-300:])
    ok, out = run_raw([installer, "accept", "TSP.4 docs", "--project", project, "-m", "adapted for the PM folder"], root)
    ok2, out2 = run_raw([installer, "status", "--project", project, "--check"], root)
    check("docs: accept records the adapted TD, and status is clean again",
          ok and ok2 and "declared: adapted for the PM folder" in out2, out2[-300:])
    tsp_scripts = os.path.join(root, "TSP", "TSP.3 TSP Register", "tsp-manager", "scripts")
    code = ("import sys; sys.path.insert(0, %r); import schema as S; "
            "print([r.replace(chr(92), '/') for r in S.find_skill_roots(%r, None)])" % (tsp_scripts, project))
    ok, out = run_raw(["-c", code], root)
    check("docs: the TSP audit finds the project's .agents/skills by itself", ok and ".agents/skills" in out, out[:200])


def test_effort_and_splits(root, scratch):
    """Effort that rolls up, requirements that say whether they were verified,
    and partly done work split so its hours count where they were done.

    Driven through the command line on a small register: a parent estimated
    before it was broken down, a deliverable committed with its last piece,
    and a story split at a sprint's close and split again at the next.
    """
    import json
    print("\nEffort, verification and splits")
    work = os.path.join(scratch, "effort")
    os.makedirs(work, exist_ok=True)
    scripts = os.path.join(root, "TSP", "TSP.1 WBS Register", "wbs-manager", "scripts")
    wbs = os.path.join(scripts, "wbs.py")
    reg = os.path.join(work, "WBS Atlas.json")
    conv = os.path.join(work, "conventions.json")
    for label, cmd in [
            ("create", [os.path.join(scripts, "create_wbs.py"), reg, "Atlas"]),
            ("seed", [wbs, "sprints", "seed", conv, "--scope", "Atlas", "--year", "2026",
                      "--anchor", "2026-07-19"]),
            ("import", [wbs, "sprints", "import", reg, "--from", conv]),
            ("root", [wbs, "add", reg, "Website", "--type", "Deliverable"]),
            ("guide", [wbs, "add", reg, "User guide", "--type", "Feature", "--parent", "1"]),
            ("draft", [wbs, "add", reg, "Draft the guide", "--parent", "2"]),
            ("last piece", [wbs, "add", reg, "Screenshots", "--parent", "2"]),
            ("story", [wbs, "add", reg, "Search page", "--parent", "1"])]:
        ok, out = run(cmd, work)
        if not check("effort: %s" % label, ok, out):
            return

    def edit(**rows):
        data = json.load(io.open(reg, encoding="utf-8"))
        for r in data["items"]:
            r.update(rows.get(str(r["ID"]), {}))
        io.open(reg, "w", encoding="utf-8").write(json.dumps(data))

    def metrics(sprint):
        ok, out = run([wbs, "metrics", reg, "--sprint", sprint, "--json"], work)
        try:
            m = json.JSONDecoder().raw_decode(out[out.index("{"):])[0]
        except ValueError:
            return None
        return (m["committed"]["n"], m["committed"]["h"], m["delivered"]["n"],
                m["delivered"]["h"], m["carryover"]["n"], m["carryover"]["h"])

    # The 100% rule: a parent's own estimate is compared with its leaves', never added.
    edit(**{"2": {"Estimated Effort (h)": 10}, "3": {"Estimated Effort (h)": 18},
            "4": {"Estimated Effort (h)": 2},
            "5": {"Estimated Effort (h)": 10, "Acceptance Criteria": "(1) results. (2) filters."}})
    ok, out = run([wbs, "check", reg], work)
    check("effort: check warns when a parent's estimate and its leaves disagree",
          "item 2" in out and "10" in out and "20" in out, out[:300])

    # A deliverable committed with its last piece: 2 items, the piece's hours.
    S1, S2, S3 = "S26.Q4.3", "S26.Q4.4", "S26.Q4.5"
    for cmd in ([wbs, "set", reg, "--id", "3", "--status", "Done", "--sprint-ended", "S26.Q4.2",
                 "--closure", "What happened: drafted. AC: (1) met."],
                [wbs, "set", reg, "--id", "2", "--sprint-planned", S1],
                [wbs, "set", reg, "--id", "4", "--sprint-planned", S1]):
        run(cmd, work)
    ok, out = run([wbs, "check", reg], work)
    check("effort: a committed parent with its work in the sprint is not flagged",
          "none of its children" not in out, out[:300])
    check("effort: a committed parent counts as an item with its children's hours",
          metrics(S1) == (2, 2, 0, 0, 2, 2), str(metrics(S1)))

    # Split a 10h story with 6h done, then split the rest again.
    run([wbs, "set", reg, "--id", "5", "--sprint-planned", S2, "--status", "Implementing"], work)
    ok, out = run([wbs, "split", reg, "--id", "5", "--delivered", "6", "--sprint", S2, "--closure",
                   "What happened: results. AC: (1) met. (2) partial: rest in the new row."], work)
    check("split: runs, and says what to change in the task tracker", ok and "Task tracker:" in out, out[:300])
    data = json.load(io.open(reg, encoding="utf-8"))
    kids = [r for r in data["items"] if r.get("Parent") == 5]
    check("split: the row becomes the parent of a done piece and the rest",
          sorted((r["Status"], r["Estimated Effort (h)"]) for r in kids)
          == [("Done", 6), ("Not Started", 4)], str(kids)[:300])
    check("split: the sprint shows what it committed and what was delivered",
          metrics(S2) == (3, 10, 1, 6, 2, 4), str(metrics(S2)))
    rest = [r for r in kids if r["Status"] == "Not Started"][0]["ID"]
    run([wbs, "set", reg, "--id", str(rest), "--sprint-carried", S3, "--reason", "split at the close"], work)
    ok, out = run([wbs, "split", reg, "--id", str(rest), "--delivered", "1", "--sprint", S3,
                   "--closure", "What happened: filters begun. AC: (2) partial."], work)
    data = json.load(io.open(reg, encoding="utf-8"))
    check("split: a piece split again adds the rest beside it, not a level deeper",
          ok and len([r for r in data["items"] if r.get("Parent") == 5]) == 3, out[:300])
    check("split: the earlier sprint keeps its figures",
          metrics(S2) == (4, 10, 1, 6, 3, 4), str(metrics(S2)))
    ok, _ = run([wbs, "split", reg, "--id", "5", "--delivered", "1", "--closure", "x"], work)
    check("split: a row with children is refused", not ok)
    last = max(r["ID"] for r in data["items"])
    run([wbs, "set", reg, "--id", str(last), "--sprint-carried", "S26.Q4.6", "--reason", "slid"], work)
    ok, out = run([wbs, "check", reg], work)
    check("split: a rest carried into two sprints is flagged", "carried into 2 sprints" in out, out[:300])

    html = os.path.join(work, "WBS Dashboard.html")
    ok, out = run([os.path.join(scripts, "refresh_wbs.py"), reg, html, "Atlas"], work)
    page = io.open(html, encoding="utf-8").read() if ok else ""
    try:
        boards = json.loads(page.split("const BOARDS=", 1)[1].split(";\n", 1)[0])
    except (IndexError, ValueError):
        boards = {}
    card = ((boards.get(S1) or {}).get("cards") or {}).get("2") or {}
    check("dashboard: a parent card reads its children's hours in the sprint",
          card.get("h") == 2 and card.get("pa") is True, str(card))
    check("dashboard: total effort counts leaves only (18 + 2 + 6 + 1 + 3)", '"total_effort": 30' in page,
          re.search(r'"total_effort": [0-9.]+', page).group(0) if '"total_effort"' in page else "none")
    check("dashboard: the Verification tab is there", "Verification" in page)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--packaged", action="store_true",
                        help="test git archive HEAD instead of the working tree")
    parser.add_argument("--keep", action="store_true",
                        help="do not delete the scratch directory")
    args = parser.parse_args()

    scratch = tempfile.mkdtemp(prefix="akos-smoke-")
    try:
        if args.packaged:
            root = export_head(os.path.join(scratch, "packaged"))
            print("Testing PACKAGED tree (git archive HEAD)")
        else:
            root = REPO
            print("Testing WORKING tree")
        print("  root: %s" % root)

        work = os.path.join(scratch, "work")
        os.makedirs(work, exist_ok=True)

        for tool in TOOLS:
            test_tool(tool, root, work)
        test_installer(root, scratch)
        test_init(root, scratch)
        test_upstream(root, scratch)
        test_reconciliation(root, scratch)
        test_catalogue(root, scratch)
        test_tsp_fields(root, scratch)
        test_sync_commands(root, scratch)
        test_effort_and_splits(root, scratch)
        test_pull_ins(root, scratch)
        test_migrate_vocabulary(root, scratch)
        test_numbered_layout(root, scratch)
        test_installer_docs(root, scratch)
        test_raid_lessons(root, scratch)
        test_concurrent_save(root, scratch)
        test_execution_layout(root, scratch)
        test_content_system(root, scratch)
        test_notebook_manager(root, scratch)
        test_sprint_ceremonies(root, scratch)
        test_daily_loop(root, scratch)
        test_weekly_review(root, scratch)
        test_action_tracker(root, scratch)
        test_stakeholder_register(root, scratch)
        test_project_definition(root, scratch)
        test_status_board(root, scratch)
        test_onboarding(root, scratch)
        test_team_tools(root, scratch)
        test_reporting(root, scratch)
        test_shared_modules(root, scratch)
        test_docs_match_code(root, scratch)

        print("\n" + "=" * 60)
        if failures:
            print("FAILED - %d check(s):" % len(failures))
            for f in failures:
                print("  - %s" % f)
            return 1
        print("All checks passed (%d tools, plus the installer, init and status --upstream, the "
              "reconciliation case, the catalogue, the shared modules, effort "
              "and splits, the "
              "concurrent-save check, the Execution layout, the "
              "docs-versus-code pass, "
              "the content system, the notebook manager, the sprint "
              "ceremonies, the daily loop, the weekly review, the action tracker, the "
              "stakeholder register, project definition, the team status board, onboarding, work management, change requests and reporting)." % len(TOOLS))
        return 0
    finally:
        if args.keep:
            print("\nScratch kept at %s" % scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
