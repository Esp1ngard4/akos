#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for cr.py. Builds a scratch project with a WBS and a RAID (through
wbs-manager and raid-manager, found beside this skill) and a Change Requests
folder, never touching a real one. One line per check; exits 1 on the first failure.

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
CR = os.path.join(HERE, "cr.py")
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


def sibling(skill):
    skills = os.path.dirname(os.path.dirname(HERE))
    for path in [os.path.join(skills, skill)] + sorted(glob.glob(os.path.join(skills, "..", "*", skill))):
        if os.path.isdir(path):
            return os.path.join(path, "scripts")
    sys.exit("%s not found beside this skill" % skill)


def main():
    tmp = tempfile.mkdtemp(prefix="cr-smoke-")
    try:
        proj = os.path.join(tmp, "Demo")
        plan = os.path.join(proj, "00. PrjMgm")
        for d in ("06. WBS", "07. RAID", "14. Change Requests"):
            os.makedirs(os.path.join(plan, d))
        wbs, raid = os.path.join(plan, "06. WBS", "WBS Demo.json"), os.path.join(plan, "07. RAID", "RAID Demo.json")
        for args in ([os.path.join(sibling("wbs-manager"), "create_wbs.py"), wbs, "Demo"],
                     [os.path.join(sibling("wbs-manager"), "wbs.py"), "add", wbs, "Login form: SSO", "--type", "Feature"],
                     [os.path.join(sibling("raid-manager"), "create_raid.py"), raid, "Demo"],
                     [os.path.join(sibling("raid-manager"), "raid.py"), "add", raid, "Identity check in the sandbox", "--type", "Risk",
                      "--because-of", "a provider release", "--risk-that", "the check is late", "--may-result-in", "a slip", "--dri", "Maya"]):
            good, out = run(*args)
            ok(good, "setup: %s" % os.path.basename(args[0]), out)
        folder = os.path.join(plan, "14. Change Requests")

        print("\nraising")
        good, out = run(CR, "lookup", proj, "identity", "check")
        ok(good and "RAID 1" in out and "Risk" in out, "lookup finds the RAID entry by its words", out)
        good, out = run(CR, "lookup", proj, "login")
        ok(good and "WBS 1" in out, "and the WBS row", out)
        good, out = run(CR, "draft", proj, "--type", "change", "--what", "Add SSO to the login form.", "--why", "The client asked.",
                        "--impact", "Two more days.", "--affects", "WBS 1, RAID 1", "--by", "Leo", "--on", "2026-10-29")
        drafted = [n for n in os.listdir(folder) if n.endswith(".md")]
        ok(good and drafted == ["CR 2026-10-29 Add SSO to the login form.md"], "a draft lands in Change Requests, named by date and words", (out, drafted))
        text = io.open(os.path.join(folder, drafted[0]), encoding="utf-8").read()
        ok("**Type:** change · **Requested by:** Leo · **On:** 2026-10-29" in text and "WBS 1, RAID 1" in text,
           "it carries its type, who asked, when, and what it affects", text[:300])
        run(CR, "draft", proj, "--type", "risk", "--what", "Add SSO to the login form.", "--why", "Again.", "--by", "Sara", "--on", "2026-10-29")
        ok(len([n for n in os.listdir(folder) if n.endswith(".md")]) == 2, "a second request with the same words is kept apart")

        print("\nprocessing")
        good, out = run(CR, "list", proj)
        ok(good and "2 open request(s)" in out and "Leo" in out, "list shows the open requests", out)
        good, out = run(CR, "close", proj, "Add SSO", "--accepted", "as WBS 2", "--by", "Maya")
        ok(not good and "2 open request(s) match" in out, "an ambiguous name is refused", out)
        good, out = run(CR, "close", proj, "form.md", "--accepted", "as WBS 2", "--by", "Maya", "--on", "2026-11-01")
        done = os.path.join(folder, "Processed", "CR 2026-10-29 Add SSO to the login form.md")
        ok(good and os.path.isfile(done) and "2026-11-01 · Maya: Accepted as WBS 2" in io.open(done, encoding="utf-8").read(),
           "close writes the outcome on it and moves it to Processed/", out)
        good, out = run(CR, "close", proj, "(2)", "--declined", "--by", "Maya")
        ok(not good, "a decline needs its reason", out)
        good, out = run(CR, "close", proj, "(2)", "--declined", "the same as the other", "--by", "Maya")
        good2, out2 = run(CR, "list", proj, "--all")
        ok(good and "0 open request(s)" in out2 and "2 processed" in out2, "declined with a reason, it is processed too", out + out2)

        print("\nno folder")
        shutil.rmtree(folder)
        good, out = run(CR, "draft", proj, "--type", "idea", "--what", "x", "--why", "y", "--by", "Leo")
        ok(not good and "No Change Requests folder" in out, "without the folder, it says who sets one up", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("All checks passed.")


if __name__ == "__main__":
    main()
