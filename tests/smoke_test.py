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
          "| draft: Ship the login page |" in nxt, out[:200])

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


DAILY_TOOL = "TSP.9 Daily Loop"
DAILY_SKILLS = ["standup-facilitator", "morning-planner"]
DAY_SECTIONS = ["## Today's update", "## Next steps", "## Risks/Blockers",
                "## Notes", "### Morning"]


def test_daily_loop(root, scratch):
    """TSP.9 has no code; what can break is the contract between its halves.

    The morning creates the day's record from a template the evening owns, and
    each half reads what the other wrote: the morning reads `status: closed`
    and the evening's frogs, the evening reads `### Morning`. If one skill's
    wording drifts from the other's, a record one writes is one the other
    cannot read, and nothing fails until a real morning. So the shared terms
    are asserted to appear in both.
    """
    print("\nTSP.9 Daily Loop")
    tool = os.path.join(root, "TSP", DAILY_TOOL)
    if not check("tool folder present", os.path.isdir(tool), tool):
        return
    texts = {}
    for name in DAILY_SKILLS:
        path = os.path.join(tool, name, "SKILL.md")
        if not check("%s has SKILL.md" % name, os.path.isfile(path), path):
            return
        texts[name] = io.open(path, encoding="utf-8").read()
        check("%s declares name and description" % name,
              "name: %s" % name in texts[name][:600]
              and "description:" in texts[name][:600], texts[name][:120])
    check("TD.9 present", any(n.startswith("TD.9") for n in os.listdir(tool)))
    check("links resolve in the catalogue", not broken_links(tool),
          "; ".join(broken_links(tool)[:5]))

    evening, morning = texts["standup-facilitator"], texts["morning-planner"]
    block = re.search(r"```markdown\n(---\nkind: day-record.*?)```", evening, re.S)
    if not check("the stand-up owns a day-record template", bool(block)):
        return
    template = block.group(1)
    missing = [s for s in DAY_SECTIONS if s not in template]
    check("the template holds the four sections and ### Morning", not missing,
          ", ".join(missing))
    for term in ("kind: day-record", "status: closed", "### Morning",
                 "standup-facilitator"):
        check("both halves name %r" % term, term in evening and term in morning,
              "evening: %s, morning: %s" % (term in evening, term in morning))
    check("the morning reads the evening's frogs where the evening writes them",
          "Next steps" in morning and "**Frogs for tomorrow:**" in evening)
    check("the evening reads the morning's frogs where the morning writes them",
          "### Morning" in evening and "**Frogs:**" in morning)

    sr = os.path.join(root, "TSP", "TSP.8 Sprint Ceremonies", "sprint-facilitator",
                      "scripts", "sprint_record.py")
    named = re.findall(r"sprint_record\.py\s+([a-z]+)", evening)
    offered = set(re.findall(r'add_parser\(\s*"([a-z]+)"', io.open(sr, encoding="utf-8").read()))
    check("the ceremony command the stand-up names exists",
          named and all(c in offered for c in named), str(named))

    project = os.path.join(scratch, "daily-project")
    os.makedirs(project, exist_ok=True)
    for name in DAILY_SKILLS:
        ok, out = run([os.path.join(root, "install.py"), "add", name,
                       "--into", project, "--catalogue", root], root)
        check("install.py add %s" % name, ok, out)


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
        test_content_system(root, scratch)
        test_notebook_manager(root, scratch)
        test_sprint_ceremonies(root, scratch)
        test_daily_loop(root, scratch)
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
              "docs-versus-code pass, "
              "the content system, the notebook manager, the sprint "
              "ceremonies and the daily loop)." % len(TOOLS))
        return 0
    finally:
        if args.keep:
            print("\nScratch kept at %s" % scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
