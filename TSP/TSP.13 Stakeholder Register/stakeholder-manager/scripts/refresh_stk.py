#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate a project's stakeholder dashboard from its register.

    python refresh_stk.py "<register.json or its folder>" [--as-of YYYY-MM-DD] [--out "<html>"]

Reads the register, runs the same checks as `stk.py check`, works out what is
derived (quadrant, gap, when each communication is due, how many people an
audience reaches), and injects it into templates/dashboard.html. Writes
`Stakeholder Dashboard.html` beside the register unless --out says otherwise
(a generated file: keep `* Dashboard.html` out of git).

**No contact details reach the page**: a dashboard is what gets
shared, and the contacts stay in their own file. Only a count of recipients
is passed.
The dashboard is a static snapshot: rerun this after any edit to the register.
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import stk_register as STK                                      # noqa: E402
import stk_schema as S                                          # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "templates", "dashboard.html")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("register")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD")
    parser.add_argument("--out")
    args = parser.parse_args()

    path = STK.resolve(args.register)
    data = R.load(path)
    scope = data["meta"].get("scope", "")
    as_of = dt.date.fromisoformat(S.parse_date(args.as_of, "--as-of")) if args.as_of else dt.date.today()
    sprints = STK.sprint_calendar(path)
    findings = STK.check(data, path)

    people = []
    for row in R.rows(data, S.STAKEHOLDERS):
        rec = dict(row)
        rec["quadrant"] = S.quadrant(row)
        rec["gap"] = S.gap(row, data)
        people.append(rec)

    comms = []
    for row in R.rows(data, S.COMMS):
        rec = dict(row)
        state, when = STK.due(row, as_of, sprints)
        res = STK.resolve_audience(data, row)        # no contacts: names and levels only
        rec.update({"state": state, "due": when.isoformat() if when else "",
                    "share_level": res["share_level"], "public": res["public"],
                    "recipients": None if res["public"] else len(res["people"])})
        comms.append(rec)

    payload = {
        "SCOPE": scope,
        "GROUPS": R.rows(data, S.GROUPS),
        "STAKEHOLDERS": people,
        "COMMS": comms,
        "FINDINGS": [{"Severity": s, "Item": i, "Finding": m} for s, i, m in findings],
        "CHANGES": R.rows(data, S.CHANGES),
    }

    if not os.path.isfile(TEMPLATE):
        raise SystemExit("Dashboard template not found: %s\nIt ships with the skill at "
                         "<skill>/templates/dashboard.html." % os.path.abspath(TEMPLATE))
    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    for key, records in payload.items():
        placeholder = "{{%s}}" % key
        if placeholder not in html:
            raise SystemExit("Template is missing the %s placeholder." % placeholder)
        # "</" is escaped so a note containing "</script>" cannot end the block.
        html = html.replace(placeholder, json.dumps(records, ensure_ascii=False,
                                                    default=str).replace("</", "<\\/"))
    html = html.replace("{{GENERATED}}", as_of.isoformat())
    html = html.replace("{{HASH}}", data["meta"].get("values_hash", ""))

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(path)),
                                   "Stakeholder Dashboard.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    errors = sum(1 for f in findings if f[0] == "error")
    overdue = sum(1 for c in comms if c["state"] == "overdue")
    print("Wrote %s" % out)
    print("  %d stakeholders, %d communications (%d overdue), %d findings (%d errors)%s"
          % (len(people), len(comms), overdue, len(findings), errors,
             "" if sprints else " - no sprint calendar: per sprint read as every 14 days"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
