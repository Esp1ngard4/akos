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
]

MIN_DASHBOARD_BYTES = 5000
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
failures = []


def check(label, ok, detail=""):
    print("  %-52s %s" % (label, "PASS" if ok else "FAIL"))
    if not ok:
        failures.append("%s%s" % (label, "\n      " + detail if detail else ""))
    return ok


def run(cmd, cwd):
    """Run a script with the current interpreter. Returns (ok, combined output)."""
    proc = subprocess.run([sys.executable] + cmd, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode == 0, proc.stdout.decode("utf-8", "replace").strip()


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
    skill = os.path.join(project, ".github", "skills", "wbs-manager", "SKILL.md")
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
    skills_root = os.path.join(project, ".github", "skills")
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
    skill = os.path.join(project, ".github", "skills", NOTEBOOK_SKILL)
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
    }
    prose = "\n".join(texts.values())
    unknown = []
    for script, path in scripts.items():
        src = io.open(path, encoding="utf-8").read()
        offered = set(re.findall(r'add_parser\(\s*"([a-z-]+)"', src))
        for cmd in set(re.findall(r"%s\s+([a-z][a-z-]+)" % re.escape(script), prose)):
            if cmd not in offered:
                unknown.append("%s %s" % (script, cmd))
    check("every wbs.py / tsp.py command the skills name exists", not unknown,
          ", ".join(sorted(unknown)))

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
    installed = os.path.join(project, ".github", "skills", "sprint-facilitator",
                             "scripts", "sprint_record.py")
    check("the record script arrives with the skill", os.path.isfile(installed), installed)
    lock = json.load(io.open(os.path.join(project, "tools.lock.json"), encoding="utf-8"))
    check("both skills recorded in the lock",
          all(n in lock.get("tools", {}) for n in SPRINT_SKILLS), str(sorted(lock.get("tools", {}))))


REPORT_TOOL = "TSP.10 Reporting"


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
    template = io.open(os.path.join(root, "templates", "Project-Brief-template.md"), encoding="utf-8").read()
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
    check("the view opens with the Outcome section", "<h2>Outcome</h2>" in page and "On Outcome" in page)
    io.open(brief, "w", encoding="utf-8").write(filled.split("### Measures")[0])
    ok, out = run([report, "status", project, "--records", records, "--sprint", "S26.Q4.1",
                   "--as-of", "2026-10-19"], work)
    rec = json.load(io.open(os.path.join(project, "Reports", "Status", "2026-10-19 Status.json"),
                            encoding="utf-8")) if ok else {}
    check("a lean brief, with no Measures table, proposes no On Outcome",
          ok and "outcome" not in rec.get("signals", {}) and not rec["outcome"]["present"], out[:300])
    os.remove(brief)

    # --- installed together with what it needs, it finds its siblings ----------
    target = os.path.join(scratch, "report-project")
    os.makedirs(target)
    for name in ("reporting", "wbs-manager", "sprint-facilitator"):
        ok, out = run([os.path.join(root, "install.py"), "add", name, "--into", target,
                       "--catalogue", root], root)
        if not check("install.py add %s" % name, ok, out[:300]):
            return
    installed = os.path.join(target, ".github", "skills", "reporting", "scripts", "report.py")
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
        test_reconciliation(root, scratch)
        test_catalogue(root, scratch)
        test_tsp_fields(root, scratch)
        test_sync_commands(root, scratch)
        test_concurrent_save(root, scratch)
        test_execution_layout(root, scratch)
        test_content_system(root, scratch)
        test_notebook_manager(root, scratch)
        test_sprint_ceremonies(root, scratch)
        test_daily_loop(root, scratch)
        test_reporting(root, scratch)
        test_shared_modules(root, scratch)
        test_docs_match_code(root, scratch)

        print("\n" + "=" * 60)
        if failures:
            print("FAILED - %d check(s):" % len(failures))
            for f in failures:
                print("  - %s" % f)
            return 1
        print("All checks passed (%d tools, plus the installer, the "
              "reconciliation case, the catalogue, the shared modules, the "
              "concurrent-save check, the Execution layout, the "
              "docs-versus-code pass, "
              "the content system, the notebook manager, the sprint "
              "ceremonies, the daily loop and reporting)." % len(TOOLS))
        return 0
    finally:
        if args.keep:
            print("\nScratch kept at %s" % scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
