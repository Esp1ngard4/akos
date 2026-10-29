#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for work.py. Builds a scratch project with a WBS (through
wbs-manager, found beside this skill) and an Execution folder, never touching a
real one. One line per check; exits 1 on the first failure.

    python smoke_test.py
"""
import glob
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def ok(cond, what, detail=""):
    print("  %s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        if detail:
            print("        %s" % str(detail)[:600])
        sys.exit(1)


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", env=ENV)
    return p.returncode == 0, p.stdout + p.stderr


def wbs_scripts():
    skills = os.path.dirname(os.path.dirname(HERE))
    for path in [os.path.join(skills, "wbs-manager")] + sorted(glob.glob(os.path.join(skills, "..", "*", "wbs-manager"))):
        if os.path.isdir(path):
            return os.path.join(path, "scripts")
    sys.exit("wbs-manager not found beside this skill")


def main():
    tmp = tempfile.mkdtemp(prefix="work-smoke-")
    try:
        proj = os.path.join(tmp, "Demo")
        plan, execution = os.path.join(proj, "00. PrjMgm", "06. WBS"), os.path.join(proj, "01. Execution")
        os.makedirs(plan)
        os.makedirs(execution)
        reg = os.path.join(plan, "WBS Demo.json")
        good, out = run(os.path.join(wbs_scripts(), "create_wbs.py"), reg, "Demo", "--execution", "../../01. Execution")
        ok(good, "setup: a WBS declaring its Execution folder", out)
        good, out = run(os.path.join(wbs_scripts(), "wbs.py"), "add", reg, "Login form: SSO", "--type", "Feature")
        ok(good, "setup: a row", out)

        print("\nstart")
        good, out = run(WORK, "start", proj, "--id", "1", "--size", "medium", "--on", "2026-10-29")
        folder = os.path.join(execution, "WP.1 Login form - SSO")
        spec = os.path.join(folder, "WP1 Login form - SSO - Specification.md")
        ok(good and os.path.isfile(spec), "medium work: its folder, named for the row, and a specification", out)
        text = io.open(spec, encoding="utf-8").read()
        ok("**Feature:** ID 1 · **Written:** 2026-10-29 · **Size:** medium" in text and "## Plan" in text,
           "the header names the row, the date and the size; the plan is a checklist in the spec", text[:300])
        ok("Next: Specification." in out, "an untouched specification is not started yet", out)
        io.open(spec, "a", encoding="utf-8").write("\n- Users sign in with the company SSO.\n")
        good, out = run(WORK, "next", proj, "--id", "1")
        ok(good and "Next: Implement." in out and "verdict" in out, "once written, next is implement, with its guideline", out)

        print("\nmoving up a size")
        good, out = run(WORK, "start", proj, "--id", "1", "--size", "large")
        names = sorted(os.listdir(folder))
        ok(good and len([n for n in names if n.endswith(".md")]) == 4 and io.open(spec, encoding="utf-8").read().endswith("SSO.\n"),
           "large adds discovery, plan and notes, and leaves the specification as written", names)
        good, out = run(WORK, "next", proj, "--id", "1")
        ok("(large)" in out and "Next: Discovery." in out, "the size read is the largest, and discovery comes first", out)

        print("\nfiling")
        received = os.path.join(tmp, "brief.pdf")
        io.open(received, "w").write("x")
        good, out = run(WORK, "file", proj, "--id", "1", received)
        ok(good and os.path.isfile(os.path.join(folder, "Inputs", "brief.pdf")), "an input lands in Inputs/", out)
        good, out = run(WORK, "file", proj, "--id", "1", received, "--deliverable")
        ok(good and os.path.isfile(os.path.join(folder, "Deliverables", "brief.pdf")), "a deliverable in Deliverables/", out)
        good, out = run(WORK, "file", proj, "--id", "1", received)
        ok(not good and "already there" in out, "a file already filed is not overwritten", out)

        print("\nas many documents as a stage needs")
        good, out = run(WORK, "add", proj, "--id", "1", "--stage", "discovery", "--subject", "Vendor survey", "--on", "2026-10-30")
        survey = os.path.join(folder, "WP1 Login form - SSO - Discovery - Vendor survey.md")
        ok(good and os.path.isfile(survey) and io.open(survey, encoding="utf-8").readline().strip() == "# WP1 Login form: SSO — Discovery: Vendor survey",
           "another discovery document, named and titled by its subject", out)
        good, out = run(WORK, "next", proj, "--id", "1")
        ok("Discovery - Vendor survey.md  (not started)" in out and "Next: Discovery." in out, "next lists it, by stage, and an untouched one does not count", out)
        io.open(survey, "a", encoding="utf-8").write("\nThree vendors offer SSO; two support SAML.\n")
        good, out = run(WORK, "next", proj, "--id", "1")
        ok("Next: Plan." in out, "any written document starts its stage: discovery and the spec done, the plan is next", out)
        good, out = run(WORK, "add", proj, "--id", "1", "--stage", "discovery", "--subject", "Interviews", "--subfolder")
        ok(good and os.path.isfile(os.path.join(folder, "Discovery", "WP1 Login form - SSO - Discovery - Interviews.md")),
           "a stage can keep its documents in a subfolder of its own", out)
        good, out = run(WORK, "add", proj, "--id", "1", "--stage", "discovery", "--subject", "Current system")
        ok(good and os.path.isfile(os.path.join(folder, "Discovery", "WP1 Login form - SSO - Discovery - Current system.md")),
           "and once it has one, its next documents go there", out)
        good, out = run(WORK, "next", proj, "--id", "1")
        ok(out.count("discovery ") == 4, "next reads the subfolder too", out)

        print("\nflat until it isn't")
        good, out = run(os.path.join(wbs_scripts(), "wbs.py"), "add", reg, "Forgotten password", "--type", "Story", "--parent", "1")
        ok(good, "setup: a story under the feature", out)
        good, out = run(WORK, "start", proj, "--id", "2", "--size", "small")
        ok(good and os.path.isfile(os.path.join(folder, "WP2 Forgotten password - Notes.md")) and "parent's folder" in out,
           "a story's documents sit in its parent's folder", out)
        good, out = run(WORK, "next", proj, "--id", "2")
        ok(good and "WP2 Forgotten password - Notes.md" in out and "WP1 " not in out, "and are read as its own, not its parent's", out)
        good, out = run(WORK, "start", proj, "--id", "2", "--size", "medium", "--own-folder")
        ok(good and os.path.isdir(os.path.join(execution, "WP.2 Forgotten password")), "--own-folder gives it a folder of its own", out)

        print("\nthe rest")
        good, out = run(WORK, "next", proj, "--id", "99")
        ok(not good and "No row 99" in out, "an unknown row says so", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("All checks passed.")


if __name__ == "__main__":
    main()
