# -*- coding: utf-8 -*-
"""The project's onboarding guide, in two editions (TSP.16 Onboarding).

    python onboard.py guide <project folder> [--records <sprint records>] [--as-of YYYY-MM-DD]
    python onboard.py show  <project folder>          # the record it would write, as JSON

Gathers a record from the project's own files - its brief, its registers (found
by meta.kind), the tools installed (tools.lock.json), the artifact register's
folder descriptions, the stakeholder register and the sprint calendar - and
renders the team guide and the executive overview from it, into the project's
onboarding folder. Generated, never written: regenerating is how the guide
stays true. A tool not installed is a section left out or said plainly, never a
failure.

Only what changes when a tool, the brief or the team changes goes in: the
sprint's pattern, never the running sprint, its goals or this sprint's board.
The guide says where the current state is instead.

Standard library only. Reads, where installed beside it: project-definition-
manager (the brief), status-board-manager (how its boards are named).
"""
import argparse
import glob
import io
import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import render as G                                              # noqa: E402

LOCK_NAME = "tools.lock.json"
REPORTS_DIR = re.compile(r"^(\d+[.\s]\s*)?Reports$")
ONBOARDING_DIR = re.compile(r"^(\d+[.\s]\s*)?Onboarding$")
EXECUTION_DIR = re.compile(r"^(\d+[.\s]\s*)?Execution$")
GUIDE = "Guide"
SPRINT_FILE = re.compile(r"^S\d{2}\.Q\d\.\d+\.md$")
SKIP = ("PreviousV", "Archive", "AuxMat")


def optional_sibling(skill):
    skills = os.path.dirname(os.path.dirname(HERE))
    for path in [os.path.join(skills, skill)] + sorted(glob.glob(os.path.join(skills, "..", "*", skill))):
        if os.path.isdir(path):
            return os.path.abspath(path)
    return None


def module(skill, name):
    folder = optional_sibling(skill)
    if not folder:
        return None
    scripts = os.path.join(folder, "scripts")
    if scripts not in sys.path:
        sys.path.append(scripts)
    try:
        return __import__(name)
    except (ImportError, SystemExit):
        return None


# ─── Finding things ──────────────────────────────────────────────────────────

def load_json(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def kinds(folder):
    """{meta.kind: [paths]} for every JSON under the folder, reports and
    archives left out."""
    out = {}
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP and not REPORTS_DIR.match(d) and not ONBOARDING_DIR.match(d))
        for name in sorted(files):
            if name.endswith(".json") and name != LOCK_NAME:
                data = load_json(os.path.join(root, name))
                meta = data.get("meta") if isinstance(data, dict) else None
                if isinstance(meta, dict) and meta.get("kind"):
                    out.setdefault(meta["kind"], []).append(os.path.join(root, name))
    return out


def find_up(folder, name, levels=4):
    cur = os.path.abspath(folder)
    for _ in range(levels):
        cand = os.path.join(cur, name)
        if os.path.isfile(cand):
            return cand
        up = os.path.dirname(cur)
        if up == cur:
            break
        cur = up
    return None


def reports_root(folder):
    for name in sorted(os.listdir(folder)):
        if REPORTS_DIR.match(name) and os.path.isdir(os.path.join(folder, name)):
            return os.path.join(folder, name)
    return os.path.join(folder, "Reports")


def onboarding_root(folder):
    """The project's onboarding folder: one named Onboarding, numbered or not,
    as the artifact register names it; else Onboarding/."""
    for name in sorted(os.listdir(folder)):
        if ONBOARDING_DIR.match(name) and os.path.isdir(os.path.join(folder, name)):
            return os.path.join(folder, name)
    return os.path.join(folder, "Onboarding")


def execution(project, wbs_path, wbs):
    """Where each piece of work keeps its trail: the backlog's declared
    meta.execution, else an Execution folder beside the planning folder or in
    it, else the standard name."""
    ex = ((wbs or {}).get("meta") or {}).get("execution") or {}
    path = None
    if ex.get("folder") and wbs_path:
        path = os.path.normpath(os.path.join(os.path.dirname(wbs_path), ex["folder"]))
    else:
        for root in (os.path.dirname(os.path.abspath(project)), project):
            hit = next((n for n in sorted(os.listdir(root)) if EXECUTION_DIR.match(n) and os.path.isdir(os.path.join(root, n))), None)
            if hit:
                path = os.path.join(root, hit)
                break
    return {"folder": os.path.basename(path) if path else "1. Execution", "found": bool(path and os.path.isdir(path)),
            "inputs": ex.get("inputs") or "Inputs", "deliverables": ex.get("deliverables") or "Deliverables", "declared": bool(ex)}


def work_sizes(project):
    """The size table from Work Management's sizes guideline, where it is installed
    (at the project root for the team, or beside this skill): [[size, typical
    work, what to expect]]. The guide shows it; the guidelines own it."""
    candidates = [os.path.join(base, ".agents", "skills", "work-manager") for base in
                  (os.path.abspath(project), os.path.dirname(os.path.abspath(project)))]
    candidates.append(optional_sibling("work-manager"))
    for skill in candidates:
        path = os.path.join(skill, "references", "sizes.md") if skill else None
        if path and os.path.isfile(path):
            rows = []
            for line in io.open(path, encoding="utf-8"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if line.startswith("|") and len(cells) == 3 and cells[0] in ("Small", "Medium", "Large"):
                    rows.append(cells)
            return rows
    return []


def find_records(folder):
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP]
        if any(SPRINT_FILE.match(f) for f in files):
            return root
    return None


def installed(folder):
    """The skills installed for this project: its lock, else the skills beside this one."""
    lock = find_up(folder, LOCK_NAME)
    if lock:
        data = load_json(lock) or {}
        return sorted(k for k in data.get("tools", {}) if not k.endswith(" docs"))
    skills = os.path.dirname(os.path.dirname(HERE))
    return sorted(n for n in os.listdir(skills) if os.path.isfile(os.path.join(skills, n, "SKILL.md")))


def rows(data, coll):
    return [r for r in (data or {}).get(coll, []) if isinstance(r, dict)]


def active(r):
    return (r.get("Status") or "Active").strip() in ("", "Active")


def first_sentence(text):
    m = re.match(r"(.+?[.;:])(\s|$)", (text or "").strip())
    return (m.group(1) if m else (text or "")).rstrip(".;:")[:110]


def md_sections(text):
    out, cur = {}, None
    for line in text.split("\n"):
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# ─── The record ──────────────────────────────────────────────────────────────

def gather(project, as_of, records=None):
    found = kinds(project)
    skills = installed(project)
    rel = lambda p: os.path.relpath(p, project).replace(os.sep, "/") if p else None
    wbs_path = (found.get("wbs-register") or [None])[0]
    wbs = load_json(wbs_path) if wbs_path else None
    scope = ((wbs or {}).get("meta") or {}).get("scope") or os.path.basename(os.path.abspath(project))
    records = records or find_records(project)

    # The sprint's pattern, never the running sprint: its length and the
    # weekday it starts on, from the sprint running on as_of, else the latest.
    cadence = None
    cal = rows(wbs, "sprints") or rows(load_json((found.get("agile-conventions") or [""])[0]) if found.get("agile-conventions") else None, "sprints")
    cal = [s for s in cal if s.get("Starts") and s.get("Ends")]
    iso = as_of.isoformat()
    win = next((s for s in cal if s["Starts"] <= iso <= s["Ends"]), None) or (max(cal, key=lambda s: s["Starts"]) if cal else None)
    if win:
        start, end = date.fromisoformat(win["Starts"]), date.fromisoformat(win["Ends"])
        cadence = {"days": (end - start).days + 1, "starts": start.strftime("%A")}

    brief, bpath = None, None
    B = module("project-definition-manager", "brief")
    if B:
        bpath = B.find(project) or B.resolve(project)
        if bpath:
            text = io.open(bpath, encoding="utf-8").read()
            parts, secs = B.parse(text), md_sections(text)
            brief = {"statement": parts["statement"], "outcome": parts["outcome"], "done_when": parts["done_when"],
                     "stop_if": parts["stop_if"], "serves": parts["serves"], "why": secs.get("Why") or None,
                     "measures": [r.get("Measure") for r in parts["rows"] if r.get("Measure")]}

    # How the boards are named, never this sprint's file: a new board each sprint.
    board_where = None
    if "status-board-manager" in skills and wbs_path:
        BD = module("status-board-manager", "board")
        name = BD.board_name(scope, "<sprint>") if BD and hasattr(BD, "board_name") else "Status Board %s <sprint>.xlsx" % scope
        board_where = ("%s/%s, one per sprint" % (os.path.dirname(rel(wbs_path)), name)).lstrip("/")

    stk_path = (found.get("stakeholder-register") or [None])[0]
    stk = load_json(stk_path) if stk_path else None
    people, comms, pm = {}, [], None
    if stk:
        ppl = [s for s in rows(stk, "stakeholders") if active(s)]
        groups = []
        for g in rows(stk, "groups"):
            members = [{"name": s.get("Name"), "role": s.get("Role") or ""} for s in ppl if g.get("ID") in (s.get("Groups") or [])]
            if active(g) and members:
                groups.append({"name": g.get("Name"), "members": members})
        loose = [{"name": s.get("Name"), "role": s.get("Role") or ""} for s in ppl if not s.get("Groups")]
        if loose:
            groups.append({"name": "Others", "members": loose})
        people = {"groups": groups}
        gname = {g.get("ID"): g.get("Name") for g in rows(stk, "groups")}
        by_id = {s.get("ID"): s for s in ppl}
        for c in rows(stk, "communications"):
            if active(c):
                aud = [gname.get(a) or (by_id.get(a) or {}).get("Role") or "" for a in (c.get("Audience") or [])]
                comms.append({"what": c.get("What"), "cadence": c.get("Cadence"), "audience": ", ".join(x for x in aud if x)})
        pm = next((s.get("Name") for s in ppl if "product manager" in (s.get("Role") or "").lower()), None)
    if not pm:
        for p in (found.get("raid-register") or []) + ([wbs_path] if wbs_path else []):
            pm = (((load_json(p) or {}).get("meta") or {}).get("settings") or {}).get("author")
            if pm:
                break

    art = (found.get("artifact-register") or [None])[0]
    about = {}
    if art:
        for a in rows(load_json(art), "artifacts"):
            if a.get("Type") == "Folder" and a.get("ID") is not None:
                about[str(a["ID"])] = first_sentence(a.get("Description"))
    folders = []
    for name in sorted(os.listdir(project)):
        if name.startswith((".", "~$")) or not os.path.isdir(os.path.join(project, name)) or name in SKIP:
            continue
        m = re.match(r"^0*(\d+)\.\s*", name)
        folders.append({"name": name, "about": about.get(m.group(1)) if m else None})

    where = {
        "project-definition-manager": rel(bpath) or "no brief yet",
        "wbs-manager": rel(wbs_path),
        "status-board-manager": board_where or "set up at each sprint's planning",
        "raid-manager": rel((found.get("raid-register") or [None])[0]),
        "sprint-facilitator": rel(records),
        "reporting": rel(reports_root(project)),
        "stakeholder-manager": rel(stk_path) or "no register yet",
        "weekly-review-facilitator": "the product manager's weekly records",
        "action-tracker-manager": "beside the work each tracker serves",
        "artifact-register": rel(art),
        "tsp-manager": rel((found.get("tsp-register") or [None])[0]),
    }
    order = ["status-board-manager", "project-definition-manager", "raid-manager", "reporting", "wbs-manager", "sprint-facilitator",
             "weekly-review-facilitator", "stakeholder-manager", "action-tracker-manager", "artifact-register", "tsp-manager"]
    tools = [{"skill": s, "where": where.get(s)} for s in order if s in skills]
    registers = [n for n, have in (("Brief", brief), ("Backlog", wbs), ("Team board", board_where), ("Risks and decisions", found.get("raid-register")),
                                   ("Sprint records", records)) if have]
    return {"kind": "onboarding-guide", "version": 1, "scope": scope, "as_of": as_of.isoformat(),
            "generated": datetime.now().isoformat(timespec="seconds"), "folder_name": os.path.basename(os.path.abspath(project)),
            "pm": pm, "brief": brief, "cadence": cadence, "status_tool": "board" if "status-board-manager" in skills else "agent",
            "ceremonies": {"planning": "sprint-facilitator" in skills, "closeout": "sprint-facilitator" in skills,
                                           "weekly": "weekly-review-facilitator" in skills, "daily": "daily-loop-facilitator" in skills},
            "tools": tools, "folders": folders, "folders_from": "artifact-register" if art else None,
            "people": people, "comms": comms, "registers": registers, "execution": execution(project, wbs_path, wbs),
            "sizes": work_sizes(project),
            "now": [n for n, have in (("this sprint's board", board_where), ("the sprint record", records),
                                      ("the latest status report", "reporting" in skills)) if have]}


def write(project, rec):
    out_dir = onboarding_root(project)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, GUIDE)
    with io.open(base + ".json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    exec_name = os.path.basename(base) + " (executive).html"
    pages = [(base + ".html", G.render_team(rec, exec_name)), (base + " (executive).html", G.render_exec(rec))]
    for path, text in pages:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return base


def cmd_guide(args):
    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        sys.exit("No folder at %s" % project)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    rec = gather(project, as_of, args.records)
    base = write(project, rec)
    print("Guide for %s (as of %s)" % (rec["scope"], rec["as_of"]))
    print("  brief: %s · sprints: %s · status: %s · %d tool(s) · people: %s"
          % ("yes" if rec["brief"] else "none yet", "%d days from a %s" % (rec["cadence"]["days"], rec["cadence"]["starts"]) if rec["cadence"] else "no calendar",
             "the team board" if rec["status_tool"] == "board" else "through the agent", len(rec["tools"]),
             "%d group(s)" % len(rec["people"].get("groups", [])) if rec["people"] else "no register"))
    print("  Team:      %s.html\n  Executive: %s (executive).html" % (base, base))
    return 0


def cmd_show(args):
    project = os.path.abspath(args.project)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    print(json.dumps(gather(project, as_of, args.records), ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="The project's onboarding guide (TSP.16).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, hlp in (("guide", cmd_guide, "write the team guide and the executive overview"),
                          ("show", cmd_show, "print the record the guide is built from")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("project", help="the folder holding the project's brief and registers")
        s.add_argument("--records", help="the sprint records folder, when it is not found under the project")
        s.add_argument("--as-of", metavar="YYYY-MM-DD")
        s.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
