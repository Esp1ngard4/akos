#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for onboard.py and render.py. Builds a scratch project with a
brief, a sprint running today, a team board and a stakeholder register, never
touching a real one. One line per check; exits 1 on the first failure.

    python smoke_test.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import onboard as O                                             # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
SKILLS = ["wbs-manager", "raid-manager", "sprint-facilitator", "weekly-review-facilitator", "reporting",
          "project-definition-manager", "status-board-manager", "stakeholder-manager", "onboarding-guide"]


def ok(cond, what, detail=""):
    print("  %s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        if detail:
            print("        %s" % str(detail)[:600])
        sys.exit(1)


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", env=ENV)
    return p.returncode == 0, p.stdout + p.stderr


def lock(project, skills):
    with io.open(os.path.join(project, O.LOCK_NAME), "w", encoding="utf-8") as fh:
        json.dump({"source": "test", "tools": {s: {} for s in skills}}, fh)


def main():
    tmp = tempfile.mkdtemp(prefix="onboard-smoke-")
    try:
        proj = os.path.join(tmp, "0. PrjMgm")
        wdir = os.path.join(proj, "10. WBS, Demo")
        os.makedirs(wdir)
        wbs_scripts = os.path.join(O.optional_sibling("wbs-manager"), "scripts")
        reg, conv = os.path.join(wdir, "WBS Demo.json"), os.path.join(tmp, "conventions.json")
        year = date.today().year
        for args in ([os.path.join(wbs_scripts, "create_wbs.py"), reg, "Demo"],
                     [os.path.join(wbs_scripts, "wbs.py"), "sprints", "seed", conv, "--scope", "Demo", "--year", str(year), "--anchor", "%d-07-19" % year],
                     [os.path.join(wbs_scripts, "wbs.py"), "sprints", "import", reg, "--from", conv]):
            good, out = run(*args)
            ok(good, "setup: %s" % os.path.basename(args[0]), out)
        data = json.load(io.open(reg, encoding="utf-8"))
        today = date.today().isoformat()
        sprint = next(s["Sprint"] for s in data["sprints"] if s["Starts"] <= today <= s["Ends"])
        good, out = run(os.path.join(wbs_scripts, "wbs.py"), "add", reg, "Signup page", "--sprint-planned", sprint, "--owner", "Sam")
        ok(good, "setup: a committed row", out)
        B = O.module("project-definition-manager", "brief")
        B.new(proj, "Demo", size="lean", serves="G-1")
        bp = os.path.join(proj, "Project Brief.md")
        t = io.open(bp, encoding="utf-8").read()
        t = t.replace("> **To** <what the project does> **so that** <the outcome it serves>.", "> **To** rebuild signup **so that** customers join on their own.")
        t = t.replace("<The outcome in one sentence. This line is the project's outcome wherever it is shown.>", "Customers sign up on their own.")
        t = t.replace("1. …", "1. Signup is live.")
        io.open(bp, "w", encoding="utf-8").write(t)
        stk = {"meta": {"kind": "stakeholder-register", "scope": "Demo"},
               "groups": [{"ID": "G.1", "Name": "Delivery team", "Status": "Active"}, {"ID": "G.2", "Name": "Steering group", "Status": "Active"}],
               "stakeholders": [{"ID": "S.1", "Name": "Kim Owner", "Role": "Product manager", "Groups": ["G.1"], "Status": "Active"},
                                {"ID": "S.2", "Name": "Lou Sponsor", "Role": "Sponsor", "Groups": ["G.2"], "Status": "Active"}],
               "communications": [{"ID": "C.1", "What": "Status report", "Audience": ["G.2"], "Cadence": "per sprint", "Status": "Active"}]}
        os.makedirs(os.path.join(proj, "13. Comms"))
        os.makedirs(os.path.join(proj, "Reports"))
        json.dump(stk, io.open(os.path.join(proj, "13. Comms", "Stakeholders Demo.json"), "w", encoding="utf-8"))
        board = os.path.join(O.optional_sibling("status-board-manager"), "scripts", "board.py")
        good, out = run(board, "setup", reg)
        ok(good, "setup: the team board", out)
        lock(proj, SKILLS)

        print("\nthe record")
        rec = O.gather(proj, date.today())
        ok(rec["scope"] == "Demo" and rec["cadence"] and rec["cadence"]["days"] == 14, "it finds the scope and the sprint's pattern", rec.get("cadence"))
        ok(sprint not in json.dumps(rec), "the record holds nothing of the sprint running now", sprint)
        ok(rec["brief"] and rec["brief"]["outcome"] == "Customers sign up on their own.", "it reads the brief through project-definition-manager", rec.get("brief"))
        ok(rec["status_tool"] == "board" and rec["now"] == ["this sprint's board", "the latest status report"], "it knows where the current state is", rec.get("now"))
        ok(rec["pm"] == "Kim Owner" and rec["comms"] and rec["comms"][0]["audience"] == "Steering group", "it reads who's who and what goes to whom", (rec["pm"], rec["comms"]))
        ok(rec["ceremonies"]["weekly"] and not rec["ceremonies"]["daily"], "the ceremonies follow the installed tools", rec["ceremonies"])

        print("\nthe pages")
        good, out = run(os.path.join(HERE, "onboard.py"), "guide", proj)
        gdir = os.path.join(proj, "Onboarding")
        team = io.open(os.path.join(gdir, "Guide.html"), encoding="utf-8").read() if good else ""
        execu = io.open(os.path.join(gdir, "Guide (executive).html"), encoding="utf-8").read() if good else ""
        ok(good and team and execu, "guide writes both editions into the onboarding folder, undated", out)
        ok(all(sprint not in page and ">today<" not in page for page in (team, execu)), "neither page names the sprint running now, or today")
        ok("Every sprint · 14 days" in team and "What this sprint is about" in team, "the rhythm is the sprint's pattern, and says where the current state is")
        ok("You and the agents do the work" in team and "do the work · keep records" in execu, "people and agents both do the work; people decide")
        for sid in ("welcome", "why", "agents", "toolkit", "where", "who", "rhythm", "work", "first-week", "glossary"):
            ok('id="%s"' % sid in team, "the team guide has its %s section" % sid)
        ok("We rebuild signup" in team and "so that customers join on their own" in team, "the welcome opens on the brief's statement")
        ok("@font-face" in team and "data:font/woff2;base64," in team, "the fonts are embedded")
        ok("Copilot in Excel" in team and "Status Board Demo &lt;sprint&gt;.xlsx, one per sprint" in team and "Kim Owner" in team, "it teaches the board, how its files are named, and the people")
        ok(all(r in team for r in ("Product manager", "Developer", "Validation and quality")) and '"agent"' in team and '"person"' in team,
           "three role paths, each step saying who acts")
        ok(team.count('class="stage') == 6 and "WP12 Login form - Plan.md" in team and "Nothing is built until the plan is approved" in team,
           "the work loop: six stops, each leaving its document in the work's folder, the plan approved first")
        ok(execu.count('class="stage') == 6 and ".md" not in execu, "the executive overview shows the loop, without file names")
        ok('href="Guide (executive).html"' in team, "the team guide links to the executive overview")
        ok(all(x not in execu for x in ("Kim Owner", "Lou Sponsor", "Status Board Demo", "WBS Demo.json", "onboard.py", "Copilot in Excel")),
           "the executive overview holds no name, file or command")
        ok(execu.count('class="pnum"') == 6 and "WORKING TOGETHER" in execu and "Steering group" in execu,
           "it carries the principles, the people-and-agents loop and what each audience receives")

        print("\nfinding Work Management")
        site = os.path.join(tmp, "Site")
        plan = os.path.join(site, "General", "0.PrjMgm")
        os.makedirs(plan)
        wm = O.optional_sibling("work-manager")
        if wm:
            shutil.copytree(wm, os.path.join(site, "tools", "skills", "work-manager"))
            with io.open(os.path.join(site, O.LOCK_NAME), "w", encoding="utf-8") as fh:
                json.dump({"tools": {"work-manager": {"path": "tools/skills/work-manager"}}}, fh)
            saved, O.optional_sibling = O.optional_sibling, (lambda s: None)
            try:
                ok(len(O.work_sizes(plan)) == 3, "installed in a non-default place, it is found through the lock file")
            finally:
                O.optional_sibling = saved

        print("\nwithout a board")
        lock(proj, [s for s in SKILLS if s != "status-board-manager"])
        rec = O.gather(proj, date.today())
        ok(rec["status_tool"] == "agent", "the record says the team works through the agent", rec["status_tool"])
        team = O.G.render_team(rec)
        ok("Copilot in Excel" not in team and "I'm starting the login form." in team, "the paths say to tell the agent, not the board")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("All checks passed.")


if __name__ == "__main__":
    main()
