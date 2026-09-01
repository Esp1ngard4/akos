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
        "collections": ["items", "key_deliverables"],
        "create": lambda s, r, d: [os.path.join(s, "scripts", "create_wbs.py"), r, "Demo"],
        "refresh": lambda s, r, d: [os.path.join(s, "scripts", "refresh_wbs.py"), r, d, "Demo"],
    },
    {
        "name": "TSP.2 RAID Register",
        "skill": "TSP/TSP.2 RAID Register/raid-dashboard",
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

        print("\n" + "=" * 60)
        if failures:
            print("FAILED - %d check(s):" % len(failures))
            for f in failures:
                print("  - %s" % f)
            return 1
        print("All checks passed (%d tools, plus the installer, the "
              "reconciliation case and the catalogue)." % len(TOOLS))
        return 0
    finally:
        if args.keep:
            print("\nScratch kept at %s" % scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
