#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for board.py and xlsx.py. Builds a scratch project with a sprint
running today, never touching a real one. One line per check; exits 1 on the
first failure.

    python smoke_test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xlsx                                                     # noqa: E402
import board as B                                               # noqa: E402

WBS = os.path.join(B.WBS_SCRIPTS, "wbs.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
DOT = "·"


def ok(cond, what, detail=""):
    print("  %s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        if detail:
            print("        %s" % str(detail)[:800])
        sys.exit(1)


def run(script, *args):
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True,
                       encoding="utf-8", env=ENV)
    return p.returncode == 0, p.stdout + p.stderr


def board(*args):
    return run(os.path.join(HERE, "board.py"), *args)


def wbs(*args):
    return run(WBS, *args)


def excel_like(path):
    """A workbook laid out the way Excel saves one: shared strings, and a date
    as a serial number in a cell styled with a date format."""
    sheet = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="%s"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
             '<row r="2"><c r="A2"><v>12</v></c><c r="B2" s="1"><v>46322</v></c></row>'
             '<row r="3"><c r="A3" t="s"><v>2</v></c><c r="B3" t="b"><v>1</v></c></row>'
             '</sheetData></worksheet>' % xlsx.NS["m"])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="%s" xmlns:r="%s"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>'
                   % (xlsx.NS["m"], xlsx.NS["r"]))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>' % xlsx.NS["rel"])
        z.writestr("xl/sharedStrings.xml", '<sst xmlns="%s"><si><t>WBS ID</t></si><si><t>Updated on</t></si><si><r><t>rich </t></r><r><t>text</t></r></si></sst>' % xlsx.NS["m"])
        z.writestr("xl/styles.xml", '<styleSheet xmlns="%s"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>' % xlsx.NS["m"])
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def edit(path, by_task=None, add=None, drop=None, about=None):
    """Change the board as the team would: cells by task name, new rows, rows
    dropped by task name."""
    b = B.load(path)
    for row in b["rows"]:
        row.update((by_task or {}).get(row.get("Task"), {}))
    if drop:
        b["rows"] = [r for r in b["rows"] if r.get("Task") not in drop]
    for r in add or []:
        b["rows"].append(r)
    if about:
        b["about"].update(about)
    B.save(path, b["about"], b["rows"], b["extra"], "test")


def kinds(props):
    return {(p["kind"], p.get("id")) for p in props}


def main():
    tmp = tempfile.mkdtemp(prefix="board-smoke-")
    try:
        print("xlsx")
        p = os.path.join(tmp, "excel.xlsx")
        excel_like(p)
        rows = xlsx.read(p)["Data"]
        ok(rows[0] == ["WBS ID", "Updated on"], "shared strings read", rows)
        ok(rows[1] == ["12", "2026-10-27"], "a number reads as text, a date serial as YYYY-MM-DD", rows)
        dated = os.path.join(tmp, "dated.xlsx")
        xlsx.write(dated, [xlsx.Sheet("Board", [["Task", "Updated on"], ["Form", "2026-10-29"]], widths=[20, 14], table=("Board", 0), dates=[1])])
        with zipfile.ZipFile(dated) as z:
            styles, sheet = z.read("xl/styles.xml").decode("utf-8"), z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        ok('formatCode="dd\\-mmm\\-yyyy"' in styles and '<c r="B2" s="4"><v>46324</v></c>' in sheet and 'style="4"' in sheet,
           "a date column is written as real dates shown 29-Oct-2026, and keeps the format for what is typed later", sheet[-400:])
        ok(xlsx.read(dated)["Board"][1] == ["Form", "2026-10-29"], "and reads back as YYYY-MM-DD")
        ok([B.as_iso(s) for s in ("29-Oct-2026", "5 Nov 2026", "2026-10-29", "")] == ["2026-10-29", "2026-11-05", "2026-10-29", ""],
           "a date typed as text reads as one")
        ok(rows[2] == ["rich text", "TRUE"], "rich text and booleans", rows)
        legacy = os.path.join(tmp, "legacy.xlsx")
        xlsx.write(legacy, [xlsx.Sheet("Board", [["WBS ID", "Title", "Status", "Note"], [3, "Old", "Doing", "2026-10-01 %s Ann: x" % DOT]]),
                            xlsx.Sheet("About", [[B.KIND, ""], ["Sprint", "S1"]])])
        lb = B.load(legacy)
        ok(lb["rows"][0].get("Notes", "").endswith("Ann: x") and lb["rows"][0].get("Task") == "Old" and not lb["extra"],
           "a board with the older Title and Note columns reads as Task and Notes", lb)
        ok(B.parse_notes("2026-10-28 %s Tom Becker: link works\nplain line\n2026-10-26: no name" % DOT)
           == [{"date": "2026-10-28", "by": "Tom Becker", "text": "link works"}, {"date": None, "by": None, "text": "plain line"},
               {"date": "2026-10-26", "by": None, "text": "no name"}], "notes parse by line: date, author, text; an undated line kept")

        print("\nboard")
        reg = os.path.join(tmp, "10. WBS", "WBS Demo.json")
        os.makedirs(os.path.dirname(reg))
        conv = os.path.join(tmp, "conventions.json")
        for cmd in ([os.path.join(B.WBS_SCRIPTS, "create_wbs.py"), reg, "Demo"],
                    [WBS, "sprints", "seed", conv, "--scope", "Demo", "--year", str(date.today().year), "--anchor", "2026-07-19"],
                    [WBS, "sprints", "import", reg, "--from", conv]):
            good, out = run(*cmd)
            ok(good, "setup: %s" % os.path.basename(cmd[0]), out)
        data = B.R.load(reg)
        sprint = B.W.current_sprint(data)
        ok(bool(sprint), "a sprint in the calendar holds today", data.get("sprints", [])[:2])
        nxt = data["sprints"][[s["Sprint"] for s in data["sprints"]].index(sprint) + 1]["Sprint"]
        for args in (["Website", "--type", "Deliverable", "--sprint-planned", sprint],
                     ["Login page", "--parent", "1", "--sprint-planned", sprint, "--owner", "Sam"],
                     ["Signup page", "--parent", "1", "--sprint-planned", sprint],
                     ["Help text", "--parent", "1", "--sprint-planned", sprint],
                     ["Terms page", "--parent", "1", "--sprint-planned", sprint],
                     ["Cookie banner", "--parent", "1", "--sprint-planned", sprint]):
            good, out = wbs("add", reg, *args)
            ok(good, "row: %s" % args[0], out)
        wbs("set", reg, "--id", "5", "--status", "Implementing")
        wbs("set", reg, "--id", "6", "--status", "Done", "--closure", "What happened: shipped. AC: (1) met. Follow-up: none.")

        good, out = board("setup", reg)
        path = B.live_board(reg, sprint)
        ok(good and path and os.path.basename(path) == "Status Board Demo %s.xlsx" % sprint, "setup writes the sprint's board beside the WBS", out)
        b = B.load(path)
        ok([r["WBS ID"] for r in b["rows"]] == ["2", "3", "4", "5", "6"], "one task per WBS leaf, the parent left out", b["rows"])
        first = b["rows"][0]
        ok(first["WBS item"] == "Login page" and first["Task"] == "Login page" and first["Owner"] == "Sam",
           "a first task is named after its WBS row, with its owner", first)
        ok(b["rows"][3]["Status"] == "Doing" and b["rows"][4]["Status"] == "Done", "the WBS status comes across", b["rows"])
        with zipfile.ZipFile(path) as z:
            sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        ok('sqref="A2:A' in sheet and '"2,3,4,5,6"' in sheet, "the WBS ID column offers the sprint's IDs as a list", sheet[-600:])
        good, out = board("setup", reg)
        ok(not good and "already exists" in out, "a second setup for the sprint is refused", out)

        today, old = date.today().isoformat(), "2000-01-01"
        edit(path, by_task={
            "Login page": {"Task": "Login form", "Status": "Done", "AC verdict": "met", "Updated on": today, "Updated by": "Sam",
                           "Notes": "%s %s Sam: released\n%s %s Sam: started on the form" % (today, DOT, old, DOT)},
            "Signup page": {"Status": "Doing", "Updated on": today},
            "Help text": {"Status": "Blocked", "Notes": "%s %s Kim: waiting for the test environment" % (today, DOT)},
            "Terms page": {"Status": "To do"},
            "Cookie banner": {"Status": "Doing"}},
            add=[{"WBS ID": "2", "Task": "Login tests", "Status": "Doing", "Notes": "%s %s Ann: half written" % (today, DOT)},
                 {"Task": "Fix the login timeout", "Status": "Doing", "Notes": "%s %s Sam: found in testing" % (today, DOT)},
                 {"WBS ID": "99", "Task": "Odd one", "Status": "Doing"}])
        good, out = board("propose", reg, "--json")
        props = json.loads(out)["proposals"] if good else []
        k = kinds(props)
        ok(("start", "2") in k and ("close", "2") not in k, "a WBS row with one task done and one open starts, it does not close", props)
        start2 = next(p for p in props if p["kind"] == "start" and p["id"] == "2")
        ok([t["task"] for t in start2["tasks"]] == ["Login form", "Login tests"], "the row's tasks are listed with it", start2)
        ok(("start", "3") in k, "one task moving starts its WBS row", props)
        ok(("blocked", "4") in k and ("start", "4") in k, "a blocked task offers a RAID issue, and starts its row", props)
        ok(("back", "5") in k, "every task To do on an Implementing row is asked about", props)
        ok(("reopened", "6") in k, "a task open on a Done row is asked about", props)
        ok(any(p["kind"] == "unlinked" and p["title"] == "Fix the login timeout" for p in props), "a task with no WBS ID is unlinked", props)
        ok(("unknown", "99") in k, "a WBS ID the register lacks is flagged", props)
        notes = next((p for p in props if p["kind"] == "notes" and p["id"] == "2"), None)
        ok(notes and [(n["task"], n["text"]) for n in notes["entries"]] == [("Login form", "started on the form"), ("Login form", "released"), ("Login tests", "half written")]
           and "2000-01-01, Sam (Login form): started on the form" in notes["commands"][0],
           "the notes of every task reach the row oldest first, each named by its task", notes)

        edit(path, by_task={"Login tests": {"Status": "Done", "AC verdict": "partly met", "Updated on": today,
                                            "Notes": "%s %s Ann: two edge cases left\n%s %s Ann: half written" % (today, DOT, today, DOT)}})
        good, out = board("propose", reg, "--json")
        props = json.loads(out)["proposals"]
        close = next((p for p in props if p["kind"] == "close" and p["id"] == "2"), None)
        ok(close and "partly met on the board" in close["closure"] and "Login form met" in close["closure"]
           and "Login tests partly met" in close["closure"] and "Login form: released" in close["closure"]
           and "Login tests: two edge cases left" in close["closure"] and "the rest, as the notes say" in close["closure"],
           "all tasks done closes the row, with the weakest verdict and each task's newest note", close)
        ok(close["actual_end"] == B.wbs_date(today), "the close takes the latest date the tasks give", close)

        edit(path, drop=["Help text"])
        good, out = board("propose", reg, "--json")
        ok(("missing", "4") in kinds(json.loads(out)["proposals"]), "a committed WBS row with no task is flagged", out)

        wbs("add", reg, "Password reset", "--parent", "1", "--sprint-added", sprint)
        wbs("set", reg, "--id", "3", "--status", "Cancelled", "--closure", "What happened: dropped. AC: none. Follow-up: none.")
        edit(path, add=[{"WBS ID": "3", "Task": "Signup copy", "Status": "To do"}])
        good, out = board("sync", reg, "--ids", "7", "3")
        b = B.load(path)
        by_task = {r.get("Task"): r for r in b["rows"]}
        ok(good and "Password reset" in by_task and "Help text" not in by_task, "sync --ids adds the pull-in and only what it names", out)
        ok(by_task["Signup page"]["Status"] == "Cancelled" and by_task["Signup copy"]["Status"] == "Cancelled"
           and B.parse_notes(by_task["Signup copy"]["Notes"])[0]["by"] == "product manager",
           "a cancelled WBS row marks every task, each with a dated note", by_task["Signup copy"])
        good, out = board("propose", reg, "--json")
        ok(not [p for p in json.loads(out)["proposals"] if p["id"] == "3" and p["kind"] == "notes"],
           "a cancelled WBS row gets no notes proposed", out)
        ok(by_task["Signup copy"]["WBS item"] == "Signup page", "a task added with a WBS ID gets its WBS item filled", by_task["Signup copy"])
        ok(by_task["Fix the login timeout"]["Notes"].endswith("found in testing") and by_task["Terms page"]["Status"] == "To do",
           "the team's other cells are kept", by_task)

        row = by_task["Fix the login timeout"]["_row"]
        good, out = board("link", reg, "--row", str(row), "--id", "4")
        b = B.load(path)
        lt = next(r for r in b["rows"] if r.get("Task") == "Fix the login timeout")
        ok(good and lt["WBS ID"] == "4" and lt["WBS item"] == "Help text", "link names the WBS row an unlinked task serves", out)
        good, out = board("link", reg, "--row", str(row), "--id", "4")
        ok(not good and "already names" in out, "link refuses a task that has an ID", out)

        good, out = board("sync", reg, "--consolidated")
        b = B.load(path)
        ok(good and b["about"]["Consolidated on"] == today, "sync stamps the consolidation", out)
        wbs("note", reg, "--id", "2", B.wbs_note({"date": today, "by": "Ann", "text": "two edge cases left"}, "Login tests"))
        good, out = board("propose", reg, "--json")
        fresh = {p["id"]: [n["text"] for n in p["entries"]] for p in json.loads(out)["proposals"] if p["kind"] == "notes"}
        ok("two edge cases left" not in fresh.get("2", []) and "half written" in fresh.get("2", []),
           "a note already on the WBS row is not proposed again", fresh)
        ok("started on the form" not in str(fresh), "a note dated before the last consolidation is not proposed", fresh)
        lc = B.last_consolidated(reg, sprint)
        ok(lc and lc["consolidated"] == today, "last_consolidated reads the stamp, for the reports", lc)

        good, out = board("setup", reg, "--sprint", nxt)
        ok(not good and "Not consolidated since its sprint ended" in out, "the next setup refuses a board not consolidated after its sprint", out)
        edit(path, about={"Consolidated on": b["about"]["Ends"]})
        good, out = board("setup", reg, "--sprint", nxt)
        arch = os.path.join(os.path.dirname(reg), "Archive", os.path.basename(path))
        ok(good and os.path.exists(arch) and B.live_board(reg, nxt), "a consolidated board is archived when the next is set up", out)
        good, out = board("find", tmp)
        ok(good and nxt in out and "Archive" not in out, "find lists the live board, not the archive", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("All checks passed.")


if __name__ == "__main__":
    main()
