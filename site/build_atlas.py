#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Atlas example and publish its guides into docs/atlas/.

Atlas is a made-up project. This script sets it up in a scratch folder the way
a team would, with the catalogue's own tools (a WBS with a sprint calendar, a
RAID, a stakeholder register, an artifact register, the brief in
site/atlas/), then has TSP.16 Onboarding generate both editions of its guide:

    docs/atlas/index.html        the team guide
    docs/atlas/executive.html    the executive overview

    python site/build_atlas.py           # build and write docs/atlas/
    python site/build_atlas.py --check   # exit 1 if docs/atlas/ is behind the tools (CI)

The as-of date is fixed, so the same tools give the same pages.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSP = os.path.join(ROOT, "TSP")
FIXTURES = os.path.join(ROOT, "site", "atlas")
OUT = os.path.join(ROOT, "docs", "atlas")
AS_OF = date(2026, 10, 28)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

# The tools Atlas's team runs: the project tools, not the personal ones.
SKILLS = ["wbs-manager", "raid-manager", "sprint-facilitator", "weekly-review-facilitator", "reporting",
          "project-definition-manager", "status-board-manager", "stakeholder-manager", "artifact-register",
          "action-tracker-manager", "tsp-manager", "onboarding-guide"]


def script(tool, skill, name):
    return os.path.join(TSP, tool, skill, "scripts", name)


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", env=ENV)
    if p.returncode != 0:
        sys.exit("Failed: %s\n%s" % (" ".join(os.path.basename(a) for a in args[:2]), (p.stdout + p.stderr)[-1500:]))
    return p.stdout


def build(where):
    """Set Atlas up under `where` and return its planning folder."""
    prj = os.path.join(where, "Atlas", "0. PrjMgm")
    os.makedirs(os.path.join(where, "Atlas", "1. Execution"))
    folders = [(1, "WBS", "The backlog: every piece of work, and the sprint calendar"),
               (2, "RAID", "Risks, actions, issues and decisions, each with an owner"),
               (3, "Sprints", "The sprint records the ceremonies write"),
               (4, "Comms", "The stakeholder register and the communications plan"),
               (5, "Reports", "The status reports, generated each close-out"),
               (6, "Onboarding", "This guide, generated from the project's own files"),
               (7, "Artifact Register", "Where every document lives")]
    for i, name, _ in folders:
        os.makedirs(os.path.join(prj, "%d. %s" % (i, name)))
    shutil.copy(os.path.join(FIXTURES, "Project Brief.md"), os.path.join(prj, "Project Brief.md"))
    with io.open(os.path.join(prj, "tools.lock.json"), "w", encoding="utf-8") as fh:
        json.dump({"source": "https://github.com/Esp1ngard4/akos.git", "tools": {s: {} for s in SKILLS}}, fh, indent=2)

    # The backlog, with a two-week sprint calendar from a Monday.
    wbs = os.path.join(prj, "1. WBS", "WBS Atlas.json")
    conv = os.path.join(where, "conventions.json")
    w = lambda *a: run(script("TSP.1 WBS Register", "wbs-manager", "wbs.py"), *a)
    run(script("TSP.1 WBS Register", "wbs-manager", "create_wbs.py"), wbs, "Atlas")
    w("sprints", "seed", conv, "--scope", "Atlas", "--year", "2026", "--anchor", "2026-07-06")
    w("sprints", "import", wbs, "--from", conv)
    w("add", wbs, "Self-service sign-up", "--type", "Deliverable", "--key-deliverable", "Y")
    for title in ("Sign-up form", "Email verification", "Identity check", "Welcome to the dashboard"):
        w("add", wbs, title, "--type", "Feature", "--parent", "1")

    raid = os.path.join(prj, "2. RAID", "RAID Atlas.json")
    r = lambda *a: run(script("TSP.2 RAID Register", "raid-manager", "raid.py"), *a)
    run(script("TSP.2 RAID Register", "raid-manager", "create_raid.py"), raid, "Atlas")
    r("add", raid, "Identity check in the sandbox", "--type", "Risk", "--because-of", "a provider release we do not control",
      "--risk-that", "the payments provider's identity check is not in its sandbox by sprint two",
      "--may-result-in", "the identity step slipping a sprint", "--dri", "Maya Torres")
    r("add", raid, "One flow for web and mobile", "--type", "Decision", "--chose", "one responsive flow", "--over", "a separate mobile flow",
      "--because", "the same steps, half the testing")

    with io.open(os.path.join(prj, "3. Sprints", "S26.Q4.2.md"), "w", encoding="utf-8") as fh:
        fh.write("# Sprint S26.Q4.2\n\n## Planning\n")

    comms = os.path.join(prj, "4. Comms")
    s = lambda *a: run(script("TSP.13 Stakeholder Register", "stakeholder-manager", "stk.py"), *a)
    run(script("TSP.13 Stakeholder Register", "stakeholder-manager", "create_stk.py"), comms, "--scope", "Atlas")
    stk = next(os.path.join(comms, n) for n in os.listdir(comms) if n.endswith(".json"))
    s("add-group", stk, "Product team", "--purpose", "Builds and verifies the product")
    s("add-group", stk, "Steering", "--purpose", "Owns the outcome and the budget")
    for name, role, group in (("Maya Torres", "Product manager", "G.1"), ("Leo Brandt", "Developer", "G.1"), ("Sara Lind", "Developer", "G.1"),
                              ("Ines Okafor", "Validation and quality", "G.1"), ("Ruth Calder", "Sponsor", "G.2"), ("Tom Reyes", "Head of support", "G.2")):
        s("add", stk, name, "--role", role, "--groups", group)
    s("add-comm", stk, "Status report", "--mode", "push", "--audience", "G.2", "--cadence", "per sprint", "--channel", "email")
    s("add-comm", stk, "Sprint review", "--mode", "push", "--audience", "G.1,G.2", "--cadence", "per sprint", "--channel", "meeting")

    art = os.path.join(prj, "7. Artifact Register", "Artifact Register Atlas.json")
    run(script("TSP.5 Artifact Register", "artifact-register", "create_artifact_register.py"), art, "Atlas")
    sys.path.insert(0, script("TSP.5 Artifact Register", "artifact-register", ""))
    import registry as R
    data = R.load(art)
    rows = data.setdefault("artifacts", [])
    for i, name, about in folders:
        rows.append({"ID": i, "Name": name, "Type": "Folder", "Description": about, "Status": "Active", "Parent Digital": "0"})
    R.save(art, data)
    return prj


def render(prj):
    """Both editions, as {file name: page}."""
    sys.path.insert(0, script("TSP.16 Onboarding", "onboarding-guide", ""))
    import onboard as O
    rec = O.gather(prj, AS_OF)
    return {"index.html": O.G.render_team(rec, "executive.html"), "executive.html": O.G.render_exec(rec)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Build the Atlas example's guides into docs/atlas/.")
    ap.add_argument("--check", action="store_true", help="exit 1 if docs/atlas/ differs from a fresh build")
    args = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="atlas-")
    try:
        pages = render(build(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if args.check:
        stale = [n for n, text in pages.items()
                 if not os.path.isfile(os.path.join(OUT, n)) or io.open(os.path.join(OUT, n), encoding="utf-8").read() != text]
        if stale:
            sys.exit("docs/atlas/ is behind the tools (%s). Run: python site/build_atlas.py" % ", ".join(stale))
        print("docs/atlas/ is current.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    for n, text in pages.items():
        with io.open(os.path.join(OUT, n), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print("Atlas guides written to docs/atlas/: %s" % ", ".join(sorted(pages)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
