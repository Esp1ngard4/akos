# -*- coding: utf-8 -*-
"""The team's status board for one sprint, and its consolidation into the WBS
(TSP.15 Team Status Board).

    python board.py setup   <WBS register> [--sprint S26.Q4.2] [--force]
    python board.py sync    <WBS register> [--ids 58 61] [--consolidated]
    python board.py propose <WBS register> [--json]
    python board.py link    <WBS register> --row 7 --id 61
    python board.py show    <WBS register>
    python board.py find    <folder>

The board is an Excel workbook beside the WBS, one per sprint, which the team
updates itself or through Copilot. The WBS keeps one writer: the product
manager, through the agent. `propose` reads the board and says what would
change in the WBS; every change is then made through wbs.py, confirmed. The
board is written only by `setup`, `sync` and `link`, each re-reading it first
and keeping every cell the team entered.

Standard library only; needs wbs-manager installed beside this skill.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
from datetime import date

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import xlsx                                                     # noqa: E402

KIND = "akos-status-board"
COLUMNS = ["WBS ID", "Title", "Owner", "Status", "Note", "AC verdict", "Updated on", "Updated by"]
WIDTHS = [9, 48, 18, 12, 44, 14, 13, 16]
STATUSES = ["To do", "Doing", "Done", "Blocked", "Cancelled"]
VERDICTS = ["met", "partly met", "not met"]
ARCHIVE = "Archive"
MAX_ROWS = 500
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def sibling(skill):
    """A sibling skill's folder: beside this one once installed, or anywhere in
    the catalogue's TSP/ while developing."""
    skills = os.path.dirname(os.path.dirname(HERE))
    for path in [os.path.join(skills, skill)] + sorted(glob.glob(os.path.join(skills, "..", "*", skill))):
        if os.path.isdir(path):
            return os.path.abspath(path)
    sys.exit("The %s skill is not installed beside this one (looked in %s).\n"
             "Install it: python install.py add %s --into <project>" % (skill, skills, skill))


WBS_SCRIPTS = os.path.join(sibling("wbs-manager"), "scripts")
sys.path.insert(0, WBS_SCRIPTS)
import registry as R                                            # noqa: E402
import wbs as W                                                 # noqa: E402


# ─── The WBS side ────────────────────────────────────────────────────────────

def sprint_window(data, sprint):
    for s in data.get("sprints", []):
        if s.get("Sprint") == sprint:
            return s
    sys.exit("Sprint %s is not in this register's calendar." % sprint)


def the_sprint(data, given):
    sprint = given or W.current_sprint(data)
    if not sprint:
        sys.exit("No sprint in the calendar holds today; pass --sprint.")
    sprint_window(data, sprint)
    return sprint


def cards(data, sprint):
    """The rows the team works on this sprint: committed or pulled in, and
    leaves among them. A committed parent with its children in the sprint is
    worked through those children; closing it stays the product manager's."""
    rows = R.rows(data, W.ITEMS)
    committed, pulled, _ = W.sprint_populations(rows, sprint)
    held = {str(r.get("ID")): r for r in committed + pulled}
    parents = {str(r.get("Parent")) for r in held.values() if r.get("Parent") not in (None, "")}
    return [r for k, r in sorted(held.items(), key=lambda kv: int(kv[0])) if k not in parents]


def board_status(wbs_status):
    return {"Implementing": "Doing", "Done": "Done", "Cancelled": "Cancelled"}.get(wbs_status, "To do")


def wbs_date(iso):
    d = date.fromisoformat(iso)
    return "%d-%s-%d" % (d.year, MONTHS[d.month - 1], d.day)


# ─── The board ───────────────────────────────────────────────────────────────

def board_name(scope, sprint):
    return "Status Board %s %s.xlsx" % (re.sub(r'[\\/:*?"<>|]', "-", scope), sprint)


def is_board(path):
    try:
        about = xlsx.read(path).get("About") or []
    except Exception:                                           # noqa: BLE001 - not a workbook we can read
        return False
    return bool(about) and about[0] and about[0][0] == KIND


def find(folder):
    """Every board directly in a folder (not its archive), as (path, about)."""
    out = []
    for p in sorted(glob.glob(os.path.join(folder, "*.xlsx"))):
        if os.path.basename(p).startswith("~$"):
            continue
        if is_board(p):
            out.append((p, load(p)["about"]))
    return out


def load(path):
    """{'about': {field: value}, 'rows': [{column: value, '_row': excel row}], 'extra': [column]}."""
    book = xlsx.read(path)
    about = {}
    for r in (book.get("About") or [])[1:]:
        if r and r[0]:
            about[r[0]] = r[1] if len(r) > 1 else ""
    sheet = book.get("Board") or []
    hi = next((i for i, r in enumerate(sheet) if "WBS ID" in r and "Status" in r), None)
    if hi is None:
        sys.exit("%s has no Board sheet with a WBS ID and a Status column." % path)
    header = [h.strip() for h in sheet[hi]]
    extra = [h for h in header if h and h not in COLUMNS]
    rows = []
    for i, r in enumerate(sheet[hi + 1:], start=hi + 2):
        rec = {h: (r[j].strip() if j < len(r) else "") for j, h in enumerate(header) if h}
        if any(rec.values()):
            rec["_row"] = i
            rows.append(rec)
    return {"about": about, "rows": rows, "extra": extra}


HOW_TO = [
    ["How to update this board"],
    [""],
    ["This is the team's board for one sprint. Update your own rows as the work moves; the product manager brings them into the project's WBS at the weekly review and at the sprint's close-out."],
    [""],
    ["Status", "To do, Doing, Done or Blocked. Cancelled is set by the product manager only."],
    ["Note", "One line on where it stands, or what is in the way when Blocked."],
    ["AC verdict", "On a Done row: met, partly met or not met, against the row's acceptance criteria in the WBS. A partly met says in the Note what is left."],
    ["Updated on / by", "When, and who. A date as YYYY-MM-DD."],
    ["New work", "A row with no WBS ID is new work. Add a Title and a Note; the product manager decides with you whether it comes into the sprint."],
    ["Don't", "Change a WBS ID, delete a row, or rename a column: the consolidation reads them."],
    [""],
    ["Asking Copilot in Excel"],
    ["", "Mark WBS 12 as Doing, updated today by me."],
    ["", "Mark WBS 12 as Done, AC verdict met, note: released to production."],
    ["", "Set WBS 14 to Blocked with the note: waiting for the test environment."],
    ["", "Add a row with no WBS ID: title Fix the login timeout, note found in testing, status Doing."],
]


def save(path, about, rows, extra, title):
    header = COLUMNS + extra
    body = [header]
    for r in rows:
        line = []
        for h in header:
            v = r.get(h, "")
            line.append(int(v) if h == "WBS ID" and str(v).isdigit() else v)
        body.append(line)
    n = max(len(body), 2)
    board = xlsx.Sheet("Board", body, widths=WIDTHS + [18] * len(extra), styles={0: "bold"}, table=("Board", 0),
                       validations=[(3, STATUSES, 1, MAX_ROWS), (5, VERDICTS, 1, MAX_ROWS)], freeze=True)
    how = xlsx.Sheet("How to update", [list(r) for r in HOW_TO], widths=[18, 110], styles={0: "title", 11: "bold"})
    order = ["Scope", "Sprint", "Starts", "Ends", "WBS", "Set up on", "Consolidated on"]
    about_rows = [[KIND, "Read by the status board tool: leave this sheet as it is."]]
    about_rows += [[k, about.get(k, "")] for k in order] + [[k, v] for k, v in about.items() if k not in order]
    meta = xlsx.Sheet("About", about_rows, widths=[18, 60], styles={0: "bold"})
    xlsx.write(path, [board, how, meta], title=title)
    return n


def new_row(r):
    return {"WBS ID": str(r.get("ID")), "Title": r.get("Title", ""), "Owner": r.get("Owner", ""),
            "Status": board_status(r.get("Status")), "Note": "", "AC verdict": "",
            "Updated on": "", "Updated by": ""}


def live_board(wbs_path, sprint):
    folder = os.path.dirname(os.path.abspath(wbs_path))
    hits = [(p, a) for p, a in find(folder) if a.get("Sprint") == sprint]
    if not hits:
        return None
    if len(hits) > 1:
        sys.exit("Two boards for %s in %s: %s. Keep one." % (sprint, folder, ", ".join(os.path.basename(p) for p, _ in hits)))
    return hits[0][0]


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_setup(args):
    data = R.load(args.register)
    sprint = the_sprint(data, args.sprint)
    win = sprint_window(data, sprint)
    folder = os.path.dirname(os.path.abspath(args.register))
    scope = W.scope_code(data) or os.path.splitext(os.path.basename(args.register))[0]
    if live_board(args.register, sprint):
        sys.exit("A board for %s already exists. To bring it up to date with the WBS: board.py sync." % sprint)
    # The closed sprints' boards go to the archive, once consolidated after their end.
    moves, stale = [], []
    for p, a in find(folder):
        if a.get("Sprint") == sprint:
            continue
        cons, ends = a.get("Consolidated on", ""), a.get("Ends", "")
        if not cons or (ends and cons < ends):
            stale.append("%s (sprint ended %s, consolidated %s)" % (os.path.basename(p), ends or "?", cons or "never"))
        moves.append(p)
    if stale and not args.force:
        sys.exit("Not consolidated since its sprint ended: %s.\nConsolidate it first (the close-out does), "
                 "or pass --force to archive it as it is." % "; ".join(stale))
    rows = [new_row(r) for r in cards(data, sprint)]
    path = os.path.join(folder, board_name(scope, sprint))
    about = {"Scope": scope, "Sprint": sprint, "Starts": win.get("Starts", ""), "Ends": win.get("Ends", ""),
             "WBS": os.path.basename(args.register), "Set up on": date.today().isoformat(), "Consolidated on": ""}
    save(path, about, rows, [], "%s %s status board" % (scope, sprint))
    print("Set up %s: %d row(s) from the WBS." % (os.path.basename(path), len(rows)))
    if moves:
        arch = os.path.join(folder, ARCHIVE)
        os.makedirs(arch, exist_ok=True)
        for p in moves:
            dest = os.path.join(arch, os.path.basename(p))
            if os.path.exists(dest):
                sys.exit("%s is already in %s; moved nothing." % (os.path.basename(p), ARCHIVE))
            shutil.move(p, dest)
            print("  archived %s" % os.path.basename(p))
    print("Tell the team the board is ready; nobody needs to have it open while it is written.")
    return 0


def _open(args, data):
    sprint = the_sprint(data, getattr(args, "sprint", None))
    path = live_board(args.register, sprint)
    if not path:
        sys.exit("No board for %s beside %s. Set one up: board.py setup." % (sprint, os.path.basename(args.register)))
    return sprint, path, load(path)


def cmd_sync(args):
    """Bring the board in line with the WBS: committed rows it lacks are added
    (all, or only --ids), rows cancelled in the WBS are marked, and with
    --consolidated the date is stamped. The team's cells are kept."""
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    on_board = {r.get("WBS ID") for r in b["rows"] if r.get("WBS ID")}
    wanted = {str(i) for i in (args.ids or [])}
    changes = []
    for r in cards(data, sprint):
        rid = str(r.get("ID"))
        if rid not in on_board and (not wanted or rid in wanted):
            b["rows"].append(new_row(r))
            changes.append("added WBS %s %s" % (rid, r.get("Title", "")))
    by_id = {str(r.get("ID")): r for r in R.rows(data, W.ITEMS)}
    for row in b["rows"]:
        w = by_id.get(row.get("WBS ID", ""))
        if w and w.get("Status") == "Cancelled" and row.get("Status") != "Cancelled" \
                and (not wanted or row.get("WBS ID") in wanted):
            row["Status"] = "Cancelled"
            row["Note"] = ("cancelled in the WBS; " + row.get("Note", "")).strip("; ")
            changes.append("marked WBS %s cancelled" % row["WBS ID"])
    if args.consolidated:
        b["about"]["Consolidated on"] = date.today().isoformat()
        changes.append("consolidated on %s" % b["about"]["Consolidated on"])
    if not changes:
        print("The board already matches the WBS for %s; nothing written." % sprint)
        return 0
    save(path, b["about"], b["rows"], b["extra"], "%s %s status board" % (b["about"].get("Scope", ""), sprint))
    print("%s:" % os.path.basename(path))
    for c in changes:
        print("  %s" % c)
    return 0


def cmd_link(args):
    """Write the WBS ID a new row was given into that row."""
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    if not W.find(data, args.id):
        sys.exit("WBS %s is not in the register." % args.id)
    row = next((r for r in b["rows"] if r["_row"] == args.row), None)
    if not row:
        sys.exit("Row %d of the board is empty." % args.row)
    if row.get("WBS ID"):
        sys.exit("Row %d already names WBS %s." % (args.row, row["WBS ID"]))
    row["WBS ID"] = str(args.id)
    save(path, b["about"], b["rows"], b["extra"], "%s %s status board" % (b["about"].get("Scope", ""), sprint))
    print("Row %d now names WBS %s." % (args.row, args.id))
    return 0


def proposals(data, sprint, b):
    """What the board says that the WBS does not, row by row. Read-only."""
    by_id = {str(r.get("ID")): r for r in R.rows(data, W.ITEMS)}
    out = []
    for row in b["rows"]:
        rid, status = row.get("WBS ID", ""), row.get("Status", "")
        who = " by %s" % row["Updated by"] if row.get("Updated by") else ""
        when = row.get("Updated on", "")
        base = {"row": row["_row"], "id": rid or None, "title": row.get("Title", ""), "board": status,
                "note": row.get("Note", ""), "verdict": row.get("AC verdict", ""), "updated": when + who}
        if status and status not in STATUSES:
            out.append(dict(base, kind="unreadable", say="Status %r is not one of %s." % (status, ", ".join(STATUSES))))
            continue
        if not rid:
            if row.get("Title"):
                out.append(dict(base, kind="new", say="New work on the board: bring it in as a pull-in (ask what it "
                                "displaces) or as work outside the sprint, or leave it; then link the row to its ID."))
            continue
        w = by_id.get(rid)
        if not w:
            out.append(dict(base, kind="unknown", say="WBS %s is not in the register." % rid))
            continue
        ws = w.get("Status")
        base["wbs"] = ws
        date_ok = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", when)) and when <= date.today().isoformat()
        if status == "Done" and ws not in ("Done", "Cancelled"):
            draft = "What happened: %s. AC: %s on the board; confirm each criterion. Follow-up: %s." % (
                row.get("Note") or "done on the team's board",
                row.get("AC verdict") or "no verdict given",
                "the rest, as the note says" if row.get("AC verdict") == "partly met" else "none")
            out.append(dict(base, kind="close", closure=draft, actual_end=wbs_date(when) if date_ok else None,
                            say="Done on the board: close it in the WBS with a closure note confirmed per criterion."))
        elif status == "Doing" and ws in ("Not Started", "Portfolio Backlog", "Funnel"):
            out.append(dict(base, kind="start", actual_start=wbs_date(when) if date_ok else None,
                            say="Started on the board: set it Implementing."))
        elif status == "Blocked":
            out.append(dict(base, kind="blocked", say="Blocked on the board: offer a RAID issue with an owner%s."
                            % ("; and set it Implementing" if ws in ("Not Started", "Portfolio Backlog", "Funnel") else "")))
        elif status == "To do" and ws == "Implementing":
            out.append(dict(base, kind="back", say="Back to To do on the board while the WBS says Implementing: ask why; change nothing unasked."))
        elif status in ("To do", "Doing", "Blocked") and ws == "Done":
            out.append(dict(base, kind="reopened", say="Open on the board, Done in the WBS: ask; a closed row is reopened only on purpose."))
    on_board = {r.get("WBS ID") for r in b["rows"] if r.get("WBS ID")}
    for r in cards(data, sprint):
        if str(r.get("ID")) not in on_board:
            out.append({"row": None, "id": str(r.get("ID")), "title": r.get("Title", ""), "kind": "missing",
                        "say": "Committed in the WBS and not on the board: sync adds it."})
    return out


def cmd_propose(args):
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    props = proposals(data, sprint, b)
    if args.json:
        print(json.dumps({"board": path, "sprint": sprint, "about": b["about"], "proposals": props}, ensure_ascii=False, indent=1))
        return 0
    print("%s (%s, consolidated %s)" % (os.path.basename(path), sprint, b["about"].get("Consolidated on") or "never"))
    if not props:
        print("  The board and the WBS agree; nothing to bring in.")
        return 0
    for p in props:
        label = "WBS %s" % p["id"] if p.get("id") else "row %s" % p["row"]
        print("  %-9s %s %s" % (p["kind"], label, p.get("title", "")[:60]))
        print("            %s" % p["say"])
        if p.get("closure"):
            print("            draft: %s" % p["closure"])
    return 0


def cmd_show(args):
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    counts = {}
    for r in b["rows"]:
        counts[r.get("Status") or "(none)"] = counts.get(r.get("Status") or "(none)", 0) + 1
    print("%s: %s" % (os.path.basename(path), ", ".join("%s %d" % (k, v) for k, v in counts.items()) or "empty"))
    print("  set up %s, consolidated %s" % (b["about"].get("Set up on") or "?", b["about"].get("Consolidated on") or "never"))
    return 0


def cmd_find(args):
    hits = []
    for dirpath, dirnames, _ in os.walk(args.folder):
        dirnames[:] = [d for d in dirnames if d != ARCHIVE and not d.startswith(".")]
        hits += find(dirpath)
    if not hits:
        print("No status board under %s." % args.folder)
        return 1
    for p, a in hits:
        print("%s  %s %s, consolidated %s" % (p, a.get("Scope", ""), a.get("Sprint", ""), a.get("Consolidated on") or "never"))
    return 0


def last_consolidated(wbs_path, sprint=None):
    """The live board's consolidation date beside a WBS, or None when there is
    no board. For the reports: the WBS is only as fresh as this."""
    folder = os.path.dirname(os.path.abspath(wbs_path))
    boards = find(folder)
    if sprint:
        boards = [(p, a) for p, a in boards if a.get("Sprint") == sprint] or boards
    if not boards:
        return None
    p, a = boards[-1]
    return {"board": os.path.basename(p), "sprint": a.get("Sprint"), "consolidated": a.get("Consolidated on") or None}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="The team's status board for a sprint (TSP.15).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, hlp in (("setup", cmd_setup, "write the sprint's board from the WBS; archive the closed sprint's"),
                          ("sync", cmd_sync, "bring the board in line with the WBS, keeping the team's cells"),
                          ("propose", cmd_propose, "what the board says that the WBS does not; read-only"),
                          ("link", cmd_link, "write a new row's WBS ID into it"),
                          ("show", cmd_show, "the board in one line")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("register", help="the project's WBS register")
        s.add_argument("--sprint")
        s.set_defaults(fn=fn)
        if name == "setup":
            s.add_argument("--force", action="store_true", help="archive a board not consolidated since its sprint ended")
        if name == "sync":
            s.add_argument("--ids", nargs="*", help="only these WBS IDs")
            s.add_argument("--consolidated", action="store_true", help="stamp today as the consolidation date")
        if name == "propose":
            s.add_argument("--json", action="store_true")
        if name == "link":
            s.add_argument("--row", type=int, required=True, help="the board's row number, as Excel shows it")
            s.add_argument("--id", type=int, required=True)
    f = sub.add_parser("find", help="every live board under a folder")
    f.add_argument("folder")
    f.set_defaults(fn=cmd_find)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
