#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for board.py and xlsx.py. Builds a scratch project with a sprint
running today, never touching a real one. One line per check; exits 1 on the
first failure.

    python smoke_test.py
"""
import io
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


def ok(cond, what, detail=""):
    print("  %s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        if detail:
            print("        %s" % str(detail)[:600])
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


def edit_board(path, changes, about=None, drop=None):
    b = B.load(path)
    for row in b["rows"]:
        for k, v in changes.get(row.get("WBS ID") or row.get("Title"), {}).items():
            row[k] = v
    if drop:
        b["rows"] = [r for r in b["rows"] if r.get("WBS ID") != drop]
    for title, row in changes.get("_new", {}).items():
        b["rows"].append(dict(row, Title=title))
    if about:
        b["about"].update(about)
    B.save(path, b["about"], b["rows"], b["extra"], "test")


def main():
    tmp = tempfile.mkdtemp(prefix="board-smoke-")
    try:
        print("xlsx")
        p = os.path.join(tmp, "excel.xlsx")
        excel_like(p)
        rows = xlsx.read(p)["Data"]
        ok(rows[0] == ["WBS ID", "Updated on"], "shared strings read", rows)
        ok(rows[1] == ["12", "2026-10-27"], "a number reads as text, a date serial as YYYY-MM-DD", rows)
        ok(rows[2] == ["rich text", "TRUE"], "rich text and booleans", rows)

        legacy = os.path.join(tmp, "legacy.xlsx")
        xlsx.write(legacy, [xlsx.Sheet("Board", [["WBS ID", "Title", "Status", "Note"], [3, "Old", "Doing", "2026-10-01 \u00b7 Ann: x"]]),
                            xlsx.Sheet("About", [[B.KIND, ""], ["Sprint", "S1"]])])
        lb = B.load(legacy)
        ok(lb["rows"][0].get("Notes") == "2026-10-01 \u00b7 Ann: x" and not lb["extra"], "a board with the older Note column reads as Notes", lb)
        ok(B.parse_notes("2026-10-28 \u00b7 Tom Becker: link works\nplain line\n2026-10-26: no name")
           == [{"date": "2026-10-28", "by": "Tom Becker", "text": "link works"}, {"date": None, "by": None, "text": "plain line"},
               {"date": "2026-10-26", "by": None, "text": "no name"}], "notes parse by line: date, author, text; an undated line kept")

        print("\nboard")
        reg = os.path.join(tmp, "10. WBS", "WBS Demo.json")
        os.makedirs(os.path.dirname(reg))
        conv = os.path.join(tmp, "conventions.json")
        for cmd in ([os.path.join(B.WBS_SCRIPTS, "create_wbs.py"), reg, "Demo"],
                    [WBS, "sprints", "seed", conv, "--scope", "Demo", "--year", "2026", "--anchor", "2026-07-19"],
                    [WBS, "sprints", "import", reg, "--from", conv]):
            good, out = run(*cmd)
            ok(good, "setup: %s" % os.path.basename(cmd[0]), out)
        data = B.R.load(reg)
        sprint = B.W.current_sprint(data)
        if not sprint:
            seed_year = date.today().year
            ok(False, "a sprint holds today (calendar seeded for %d)" % seed_year)
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
        ok([r["WBS ID"] for r in b["rows"]] == ["2", "3", "4", "5", "6"], "its rows are the sprint's leaves, the parent left out", b["rows"])
        ok(b["rows"][0]["Owner"] == "Sam" and b["rows"][3]["Status"] == "Doing" and b["rows"][4]["Status"] == "Done",
           "owner and the WBS status come across", b["rows"])
        ok(b["about"].get("Sprint") == sprint and b["about"].get("WBS") == "WBS Demo.json", "About names the sprint and the WBS", b["about"])
        good, out = board("setup", reg)
        ok(not good and "already exists" in out, "a second setup for the sprint is refused", out)

        today = date.today().isoformat()
        old = "2000-01-01"
        edit_board(path, {"2": {"Status": "Done", "Notes": "%s \u00b7 Sam: released\n%s \u00b7 Sam: started on the form" % (today, old),
                                "AC verdict": "met", "Updated on": today, "Updated by": "Sam"},
                          "3": {"Status": "Doing"},
                          "4": {"Status": "Blocked", "Notes": "%s \u00b7 Kim: waiting for the test environment" % today},
                          "5": {"Status": "To do"},
                          "6": {"Status": "Doing"},
                          "_new": {"Fix the login timeout": {"Status": "Doing", "Notes": "%s \u00b7 Sam: found in testing" % today},
                                   "Odd one": {"WBS ID": "99", "Status": "Doing"}}}, drop=None)
        b = B.load(path)
        new_row = next(r["_row"] for r in b["rows"] if r.get("Title") == "Fix the login timeout")
        edit_board(path, {}, drop="3")
        edit_board(path, {"_new": {"Signup page": {"WBS ID": "3", "Status": "Doing"}}})
        good, out = board("propose", reg, "--json")
        props = json.loads(out)["proposals"] if good else []
        kinds = {(p["kind"], p.get("id")) for p in props}
        ok(("close", "2") in kinds, "Done on the board proposes a close", props)
        close = next(p for p in props if p["kind"] == "close")
        ok("released" in close["closure"] and "met on the board" in close["closure"] and close["actual_end"] == B.wbs_date(today),
           "the close drafts its note from the note and verdict, and takes the board's date", close)
        ok(("start", "3") in kinds, "Doing on the board proposes a start", props)
        ok(("blocked", "4") in kinds, "Blocked proposes a RAID issue", props)
        ok(("back", "5") in kinds, "To do on the board, Implementing in the WBS, is asked about", props)
        ok(("reopened", "6") in kinds, "open on the board, Done in the WBS, is asked about", props)
        ok(any(p["kind"] == "new" and p["title"] == "Fix the login timeout" for p in props), "a row with no WBS ID is new work", props)
        ok(("unknown", "99") in kinds, "a WBS ID the register lacks is flagged", props)
        notes = next((p for p in props if p["kind"] == "notes" and p["id"] == "2"), None)
        ok(notes and [n["text"] for n in notes["entries"]] == ["released", "started on the form"]
           and notes["commands"][0].endswith("Sam: started on the form\"") and "2000-01-01" in notes["commands"][0],
           "each dated note becomes a WBS note, oldest first, with its date and author", notes)
        ok("released" in close["closure"] and "started on the form" not in close["closure"], "the closure draft takes the newest note; the history goes as notes", close)

        edit_board(path, {}, drop="4")
        good, out = board("propose", reg, "--json")
        ok(("missing", "4") in {(p["kind"], p.get("id")) for p in json.loads(out)["proposals"]}, "a committed row missing from the board is flagged", out)

        wbs("add", reg, "Password reset", "--parent", "1", "--sprint-added", sprint)
        wbs("set", reg, "--id", "2", "--status", "Cancelled", "--closure", "What happened: dropped. AC: none. Follow-up: none.")
        good, out = board("sync", reg, "--ids", "7", "2")
        b = B.load(path)
        rows = {r.get("WBS ID"): r for r in b["rows"]}
        ok(good and "7" in rows and "4" not in rows, "sync --ids adds the pull-in and only what it names", out)
        ent = B.parse_notes(rows["2"]["Notes"])
        ok(rows["2"]["Status"] == "Cancelled" and ent[0]["text"] == "cancelled in the WBS" and ent[0]["by"] == "product manager"
           and ent[1]["text"] == "released", "a cancellation is marked with a dated note on top, the team's notes kept", rows["2"])
        ok(rows["5"]["Status"] == "To do" and any(r.get("Title") == "Fix the login timeout" and r.get("Notes", "").endswith("found in testing") for r in b["rows"]),
           "the team's other cells are kept", b["rows"])

        wbs("add", reg, "Fix the login timeout", "--parent", "1")
        new_row = next(r["_row"] for r in B.load(path)["rows"] if r.get("Title") == "Fix the login timeout")
        good, out = board("link", reg, "--row", str(new_row), "--id", "8")
        b = B.load(path)
        ok(good and any(r.get("WBS ID") == "8" and r.get("Title") == "Fix the login timeout" for r in b["rows"]), "link writes the new row's ID", out)
        good, out = board("link", reg, "--row", str(new_row), "--id", "8")
        ok(not good and "already names" in out, "link refuses a row that has an ID", out)

        good, out = board("sync", reg, "--consolidated")
        b = B.load(path)
        ok(good and "4" in {r.get("WBS ID") for r in b["rows"]} and b["about"]["Consolidated on"] == today,
           "sync brings the board in line and stamps the consolidation", out)
        wbs("note", reg, "--id", "4", B.wbs_note({"date": today, "by": "Kim", "text": "waiting for the test environment"}))
        edit_board(path, {"4": {"Notes": "%s \u00b7 Kim: still waiting\n%s \u00b7 Kim: waiting for the test environment" % (today, today)}})
        good, out = board("propose", reg, "--json")
        fresh = {p["id"]: [n["text"] for n in p["entries"]] for p in json.loads(out)["proposals"] if p["kind"] == "notes"}
        ok(good and fresh.get("4") == ["still waiting"], "a note already on the WBS row is not proposed again", fresh)
        ok("started on the form" not in str(fresh), "a note dated before the last consolidation is not proposed", fresh)
        lc = B.last_consolidated(reg, sprint)
        ok(lc and lc["consolidated"] == today, "last_consolidated reads the stamp, for the reports", lc)

        good, out = board("setup", reg, "--sprint", nxt)
        ok(not good and "Not consolidated since its sprint ended" in out, "the next setup refuses a board not consolidated after its sprint", out)
        edit_board(path, {}, about={"Consolidated on": b["about"]["Ends"]})
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
