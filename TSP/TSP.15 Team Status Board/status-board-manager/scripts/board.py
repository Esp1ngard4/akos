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
updates itself or through Copilot. Each row is a task of the team's, and names
the WBS row it helps deliver; one WBS row may have several tasks. The WBS keeps
one writer: the product manager, through the agent. `propose` rolls the tasks
up per WBS row and says what would change in the WBS; every change is then made
through wbs.py, confirmed. The board is written only by `setup`, `sync` and
`link`, each re-reading it first and keeping every cell the team entered.

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
COLUMNS = ["WBS ID", "WBS item", "Task", "Owner", "Status", "Notes", "AC verdict", "Updated on", "Updated by"]
WIDTHS = [9, 34, 40, 18, 12, 52, 13, 13, 16]
# Older boards named two columns differently; they read the same.
RENAMED = {"Note": "Notes", "Title": "Task"}
# One entry per line, newest on top: "2026-10-28 · Tom Becker: link works".
NOTE_LINE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s*(?:[·\-–|]\s*([^:]+?))?\s*:\s*(.+?)\s*$")
STATUSES = ["To do", "Doing", "Done", "Blocked", "Cancelled"]
VERDICTS = ["met", "partly met", "not met"]
OPEN = ("To do", "Doing", "Blocked")
NOT_STARTED = ("Not Started", "Portfolio Backlog", "Funnel")
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
    """The WBS rows the team works on this sprint: committed or pulled in, and
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


MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def as_iso(s):
    """A board date as YYYY-MM-DD: Excel's real dates already read that way;
    one typed as text, 29-Oct-2026 or 2026-10-29, is read too."""
    s = (s or "").strip()
    m = re.match(r"^(\d{1,2})[-/ ]([A-Za-z]{3})[A-Za-z]*[-/ ](\d{4})$", s)
    if m and m.group(2).lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS.index(m.group(2).lower()) + 1, int(m.group(1))).isoformat()
        except ValueError:
            return s
    return s


def is_date(s):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s or "")) and s <= date.today().isoformat()


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
    header = [RENAMED.get(h.strip(), h.strip()) for h in sheet[hi]]
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
    ["This is the team's board for one sprint. Each row is a task. Update your own as the work moves; the product manager brings the board into the project's WBS at the weekly review and at the sprint's close-out."],
    [""],
    ["WBS ID", "The WBS row the task helps deliver, picked from the list. Several tasks can name the same WBS row: add a row, pick its WBS ID, give it a Task."],
    ["WBS item", "The WBS row's title. Filled in by the product manager's agent; leave it."],
    ["Task", "What this piece of work is, in the team's words."],
    ["Status", "To do, Doing, Done or Blocked. Cancelled is set by the product manager only. A WBS row is done when all its tasks are."],
    ["Notes", "A dated log, newest on top, one entry per line (Alt+Enter for a new line): 2026-10-28 · Your name: where it stands, or what is in the way. Add a line; never edit an older one."],
    ["AC verdict", "On a Done task: met, partly met or not met, against the WBS row's acceptance criteria it covers. A partly met says in Notes what is left."],
    ["Updated on / by", "When, and who. Type the date any way Excel reads one (29-Oct-2026, or Ctrl+; for today); it shows as 29-Oct-2026."],
    ["New work", "A task with no WBS ID is new work, or work whose WBS row you don't know. Give it a Task and a dated note; the product manager links it to a WBS row or brings it in as new work."],
    ["Don't", "Change a task's WBS ID once it is set, delete a row, or rename a column: the consolidation reads them."],
    [""],
    ["Asking Copilot in Excel"],
    ["", "Mark the task Login form as Doing, updated today by me."],
    ["", "Add a task under WBS 12: Write the unit tests, owner me, status Doing."],
    ["", "Add a note on top of the Notes of the task Login form, dated today with my name: expiry after 24h still to do."],
    ["", "Mark the task Login form as Done, AC verdict met, and add a dated note on top: released to production."],
    ["", "Set the task Password reset to Blocked and add a dated note on top: waiting for the test environment."],
    ["", "Add a task with no WBS ID: Fix the login timeout, status Doing, with a dated note: found in testing."],
]


def save(path, about, rows, extra, title, ids=None):
    """Write the board. ids: the sprint's WBS IDs, offered as the WBS ID list."""
    header = COLUMNS + extra
    body = [header]
    for r in rows:
        body.append([int(r[h]) if h == "WBS ID" and str(r.get(h, "")).isdigit() else r.get(h, "") for h in header])
    validations = [(COLUMNS.index("Status"), STATUSES, 1, MAX_ROWS),
                   (COLUMNS.index("AC verdict"), VERDICTS, 1, MAX_ROWS)]
    ids = sorted({str(i) for i in (ids or [])}, key=int)
    if ids and len(",".join(ids)) < 250:                        # Excel's limit for a typed list
        validations.append((0, ids, 1, MAX_ROWS))
    board = xlsx.Sheet("Board", body, widths=WIDTHS + [18] * len(extra), styles={0: "bold"}, table=("Board", 0),
                       dates=[COLUMNS.index("Updated on")],
                       validations=validations, freeze=True)
    how = xlsx.Sheet("How to update", [list(r) for r in HOW_TO], widths=[18, 110],
                     styles={0: "title", HOW_TO.index(["Asking Copilot in Excel"]): "bold"})
    order = ["Scope", "Sprint", "Starts", "Ends", "WBS", "Set up on", "Consolidated on"]
    about_rows = [[KIND, "Read by the status board tool: leave this sheet as it is."]]
    about_rows += [[k, about.get(k, "")] for k in order] + [[k, v] for k, v in about.items() if k not in order]
    meta = xlsx.Sheet("About", about_rows, widths=[18, 60], styles={0: "bold"})
    xlsx.write(path, [board, how, meta], title=title)


def parse_notes(cell):
    """The Notes cell as entries, newest first: [{date, by, text}]. A line with
    no date is kept, dated None, so nothing the team wrote is dropped."""
    out = []
    for line in (cell or "").splitlines():
        if not line.strip():
            continue
        m = NOTE_LINE.match(line)
        if m:
            out.append({"date": m.group(1), "by": (m.group(2) or "").strip() or None, "text": m.group(3)})
        else:
            out.append({"date": None, "by": None, "text": line.strip()})
    return out


def add_note(cell, text, by, day=None):
    """A new entry on top of the Notes cell."""
    line = "%s · %s: %s" % (day or date.today().isoformat(), by, text)
    return line + ("\n" + cell if cell else "")


def wbs_note(n, task=None):
    """How a board note reads on the WBS row, so a later consolidation can tell
    it is already there. The task is named where the row has several."""
    who = ", " + n["by"] if n.get("by") else ""
    return "On the team board, %s%s%s: %s" % (n.get("date") or "undated", who, " (%s)" % task if task else "", n["text"])


def new_row(r):
    """The first task of a WBS row: named after it, until the team says otherwise."""
    return {"WBS ID": str(r.get("ID")), "WBS item": r.get("Title", ""), "Task": r.get("Title", ""),
            "Owner": r.get("Owner", ""), "Status": board_status(r.get("Status")), "Notes": "",
            "AC verdict": "", "Updated on": "", "Updated by": ""}


def live_board(wbs_path, sprint):
    folder = os.path.dirname(os.path.abspath(wbs_path))
    hits = [(p, a) for p, a in find(folder) if a.get("Sprint") == sprint]
    if not hits:
        return None
    if len(hits) > 1:
        sys.exit("Two boards for %s in %s: %s. Keep one." % (sprint, folder, ", ".join(os.path.basename(p) for p, _ in hits)))
    return hits[0][0]


def fill_items(data, rows):
    """Write each task's WBS item from the register, where it is blank."""
    by_id = {str(r.get("ID")): r for r in R.rows(data, W.ITEMS)}
    n = 0
    for row in rows:
        w = by_id.get(row.get("WBS ID", ""))
        if w and not row.get("WBS item"):
            row["WBS item"] = w.get("Title", "")
            n += 1
    return n


def write_back(path, data, sprint, b):
    save(path, b["about"], b["rows"], b["extra"], "%s %s status board" % (b["about"].get("Scope", ""), sprint),
         ids=[r.get("ID") for r in cards(data, sprint)])


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
    write_back(path, data, sprint, {"about": about, "rows": rows, "extra": []})
    print("Set up %s: %d task(s), one per WBS row; the team adds more under a row as it splits the work."
          % (os.path.basename(path), len(rows)))
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
    """Bring the board in line with the WBS: a committed WBS row with no task
    gets one (all, or only --ids), a WBS row cancelled marks its tasks, blank
    WBS items are filled, and with --consolidated the date is stamped. The
    team's cells are kept."""
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
            row["Notes"] = add_note(row.get("Notes", ""), "cancelled in the WBS", "product manager")
            changes.append("marked the task %s of WBS %s cancelled" % (row.get("Task", ""), row["WBS ID"]))
    filled = fill_items(data, b["rows"])
    if filled:
        changes.append("filled %d WBS item(s)" % filled)
    if args.consolidated:
        b["about"]["Consolidated on"] = date.today().isoformat()
        changes.append("consolidated on %s" % b["about"]["Consolidated on"])
    if not changes:
        print("The board already matches the WBS for %s; nothing written." % sprint)
        return 0
    write_back(path, data, sprint, b)
    print("%s:" % os.path.basename(path))
    for c in changes:
        print("  %s" % c)
    return 0


def cmd_link(args):
    """Write a WBS ID into a task that had none: an existing row it serves, or
    the new row it became."""
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    w = W.find(data, args.id)
    if not w:
        sys.exit("WBS %s is not in the register." % args.id)
    row = next((r for r in b["rows"] if r["_row"] == args.row), None)
    if not row:
        sys.exit("Row %d of the board is empty." % args.row)
    if row.get("WBS ID"):
        sys.exit("Row %d already names WBS %s." % (args.row, row["WBS ID"]))
    row["WBS ID"], row["WBS item"] = str(args.id), w.get("Title", "")
    write_back(path, data, sprint, b)
    print("Row %d (%s) now names WBS %s %s." % (args.row, row.get("Task", ""), args.id, w.get("Title", "")))
    return 0


def _task(row):
    return {"row": row["_row"], "task": row.get("Task", ""), "status": row.get("Status") or "To do",
            "verdict": row.get("AC verdict", ""), "owner": row.get("Owner", ""),
            "updated": as_iso(row.get("Updated on", "")), "by": row.get("Updated by", ""),
            "notes": parse_notes(row.get("Notes", ""))}


def _worst(verdicts):
    """The weakest verdict among the done tasks; '' when any gave none."""
    if any(not v for v in verdicts):
        return ""
    for v in ("not met", "partly met", "met"):
        if v in verdicts:
            return v
    return ""


def proposals(data, sprint, b):
    """What the board says that the WBS does not, per WBS row, from all its
    tasks. Read-only."""
    by_id = {str(r.get("ID")): r for r in R.rows(data, W.ITEMS)}
    since = b["about"].get("Consolidated on") or ""
    out, groups = [], {}
    for row in b["rows"]:
        rid, status = row.get("WBS ID", ""), row.get("Status", "")
        t = _task(row)
        if status and status not in STATUSES:
            out.append({"row": t["row"], "id": rid or None, "title": t["task"], "kind": "unreadable",
                        "say": "Status %r is not one of %s: ask its owner." % (status, ", ".join(STATUSES))})
            continue
        if not rid:
            if t["task"]:
                out.append({"row": t["row"], "id": None, "title": t["task"], "kind": "unlinked", "tasks": [t],
                            "say": "A task with no WBS ID: link it to the WBS row it serves, or bring it in as new work "
                                   "(a pull-in: ask what it displaces) or as work outside the sprint; then link the row."})
            continue
        if rid not in by_id:
            out.append({"row": t["row"], "id": rid, "title": t["task"], "kind": "unknown",
                        "say": "WBS %s is not in the register: ask the task's owner which row it serves." % rid})
            continue
        groups.setdefault(rid, []).append(t)

    for rid in sorted(groups, key=int):
        tasks, w = groups[rid], by_id[rid]
        ws, live = w.get("Status"), [t for t in groups[rid] if t["status"] != "Cancelled"]
        several = len(tasks) > 1
        base = {"id": rid, "title": w.get("Title", ""), "wbs": ws, "tasks": tasks}
        moving = [t for t in live if t["status"] in ("Doing", "Done", "Blocked")]
        done = [t for t in live if t["status"] == "Done"]
        if live and len(done) == len(live) and ws not in ("Done", "Cancelled"):
            verdict = _worst([t["verdict"] for t in done])
            ends = [t["updated"] for t in done if is_date(t["updated"])]
            happened = "; ".join(("%s: %s" % (t["task"], t["notes"][0]["text"].rstrip(".")) if several else
                                  t["notes"][0]["text"].rstrip(".")) for t in done if t["notes"])
            by_task = ", ".join("%s %s" % (t["task"], t["verdict"] or "no verdict") for t in done) if several else ""
            draft = "What happened: %s. AC: %s on the board%s; confirm each criterion. Follow-up: %s." % (
                happened or "done on the team's board", verdict or "no verdict given",
                " (%s)" % by_task if by_task else "",
                "the rest, as the notes say" if verdict in ("partly met", "not met") else "none")
            out.append(dict(base, kind="close", closure=draft, actual_end=wbs_date(max(ends)) if ends else None,
                            say="All %d task(s) done on the board: close it in the WBS with a closure note confirmed per criterion."
                            % len(done)))
        elif moving and ws in NOT_STARTED:
            starts = [t["updated"] for t in moving if is_date(t["updated"])]
            out.append(dict(base, kind="start", actual_start=wbs_date(min(starts)) if starts else None,
                            say="%d of %d task(s) moving on the board: set it Implementing." % (len(moving), len(live))))
        elif ws == "Implementing" and live and all(t["status"] == "To do" for t in live):
            out.append(dict(base, kind="back", say="Every task back to To do while the WBS says Implementing: ask why; change nothing unasked."))
        elif ws == "Done" and any(t["status"] in OPEN for t in live):
            out.append(dict(base, kind="reopened", say="A task open on the board, the WBS row Done: ask. Work found after a close is "
                                                         "new work or a reopening, on purpose."))
        blocked = [t for t in live if t["status"] == "Blocked"]
        if blocked:
            out.append(dict(base, kind="blocked", blocked=[t["task"] for t in blocked],
                            say="Blocked on the board (%s): offer a RAID issue with an owner." % ", ".join(t["task"] for t in blocked)))
        # Notes dated on or after the last consolidation, less those the WBS
        # row already holds: a note written on a consolidation's own day is
        # neither missed nor brought in twice.
        held = w.get("Comments") or ""
        fresh = []
        for t in tasks:
            label = t["task"] if several or (t["task"] and t["task"] != w.get("Title")) else None
            for n in t["notes"]:
                if (not n["date"] or n["date"] >= since) and wbs_note(n, label) not in held:
                    fresh.append((n, label))
        if fresh and ws != "Cancelled":                         # a cancelled row's story ends in its closure
            fresh.sort(key=lambda x: x[0]["date"] or "")
            out.append(dict(base, kind="notes", entries=[dict(n, task=lab) for n, lab in fresh],
                            commands=["wbs.py note <wbs> --id %s \"%s\"" % (rid, wbs_note(n, lab)) for n, lab in fresh],
                            say="%d note(s) since the last consolidation: each becomes a dated note on the WBS row, oldest first."
                            % len(fresh)))
    for r in cards(data, sprint):
        if str(r.get("ID")) not in groups:
            out.append({"row": None, "id": str(r.get("ID")), "title": r.get("Title", ""), "kind": "missing",
                        "say": "Committed in the WBS with no task on the board: sync adds one."})
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
        if p["kind"] in ("close", "start") and len(p.get("tasks", [])) > 1:
            for t in p["tasks"]:
                print("              task: %s · %s%s" % (t["task"], t["status"], " · " + t["verdict"] if t["verdict"] else ""))
        if p.get("closure"):
            print("            draft: %s" % p["closure"])
        for n in p.get("entries", []):
            print("            %s%s%s: %s" % (n["date"] or "undated", " · " + n["by"] if n["by"] else "",
                                             " (%s)" % n["task"] if n.get("task") else "", n["text"]))
    return 0


def cmd_show(args):
    data = R.load(args.register)
    sprint, path, b = _open(args, data)
    counts = {}
    for r in b["rows"]:
        counts[r.get("Status") or "(none)"] = counts.get(r.get("Status") or "(none)", 0) + 1
    rows = {r.get("WBS ID") for r in b["rows"] if r.get("WBS ID")}
    print("%s: %d task(s) on %d WBS row(s): %s" % (os.path.basename(path), len(b["rows"]), len(rows),
                                                   ", ".join("%s %d" % (k, v) for k, v in counts.items()) or "empty"))
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
                          ("link", cmd_link, "write a WBS ID into a task that had none"),
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
