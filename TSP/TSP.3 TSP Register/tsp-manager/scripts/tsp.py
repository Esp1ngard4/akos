#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to the TSP Register.

    python tsp.py register <register> "Tool Name" --type Tool --relevancy Often
    python tsp.py retire   <register> --id 26 --superseded-by 18
    python tsp.py review   <register> --id 23
    python tsp.py review   <register> --all --before 2024-01-01
    python tsp.py done     <register> --control 96 [--on 2026-09-01]
    python tsp.py change   <register> --tool "Artifact Register" -m "what changed"

These are the operations with rules attached - claiming an ID that is never
reused, computing Next Due from the Frequency's Days, appending to the activity
log when a control runs. Everything else is a field edit: the register is JSON.
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks                                                   # noqa: E402
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402


def today_iso(value=None):
    return value or dt.date.today().isoformat()


def find(rows, wanted):
    for row in rows:
        if S.clean(row.get("ID")) == str(wanted):
            return row
    return None


def check_vocab(data, name, value):
    allowed = S.vocabulary(data, name)
    if value and allowed and value not in allowed:
        sys.exit("%r is not in the %s vocabulary.\n  allowed: %s"
                 % (value, name, ", ".join(allowed)))


def finish(args, data, note):
    print(note)
    if args.dry_run:
        print("\n  dry run - nothing written.")
        return 0
    R.save(args.register, data)
    errors, warnings, _ = checks.run(data)
    for name, _reason in R.stale_views(args.register):
        warnings.setdefault("generated view is stale", []).append(name)
    print("\n  check   %d error(s), %d warning class(es)"
          % (len(errors), len(warnings)))
    for msg in errors[:5]:
        print("          ERROR %s" % msg)
    return 0


def cmd_register(args):
    data = R.load(args.register)
    tools = R.rows(data, S.TOOLS)
    if any(S.tool_name(r).lower() == args.name.lower()
           for r in tools):
        sys.exit("A tool named %r is already registered. Duplicate registration "
                 "is the most common error here - check the name and any alias "
                 "first." % args.name)
    for field, vocab in (("type", "type"), ("relevancy", "relevancy"),
                         ("status", "status")):
        check_vocab(data, vocab, getattr(args, field))

    # Gaps are retired IDs. Never fill them: an old reference to that number
    # would resolve to something new.
    new_id = max([int(S.clean(r.get("ID"))) for r in tools
                  if S.clean(r.get("ID")).isdigit()] or [0]) + 1
    row = {"ID": new_id, "Name": args.name,
           "Status": args.status, "Doc Aux": "No",
           "Last Reviewed": today_iso(args.on)}
    for key, value in (("Description", args.description), ("Type", args.type),
                       ("Relevancy", args.relevancy), ("Primary AF", args.area),
                       ("Skill", args.skill), ("Links", args.links)):
        if value:
            row[key] = value
    tools.append(row)
    R.rows(data, S.CHANGES).append({
        "ID": max([int(S.clean(c.get("ID"))) for c in R.rows(data, S.CHANGES)
                   if S.clean(c.get("ID")).isdigit()] or [0]) + 1,
        "Tool": args.name, "Changed On": today_iso(args.on),
        "Description": args.reason or "Tool registered."})
    return finish(args, data, "Registered TSP.%d  %s" % (new_id, args.name))


def cmd_retire(args):
    data = R.load(args.register)
    row = find(R.rows(data, S.TOOLS), args.id)
    if row is None:
        sys.exit("No tool with ID %s." % args.id)
    obsolete = next((v for v in S.vocabulary(data, "status")
                     if checks.is_obsolete(v)), "Obsolete")
    name = S.tool_name(row)
    row["Status"] = obsolete
    row["Last Reviewed"] = today_iso(args.on)
    note = args.reason or "Tool retired."
    if args.superseded_by:
        replacement = find(R.rows(data, S.TOOLS), args.superseded_by)
        if replacement is None:
            sys.exit("No tool with ID %s to supersede it." % args.superseded_by)
        note = "%s Superseded by TSP.%s %s." % (
            note, args.superseded_by, S.tool_name(replacement))
    R.rows(data, S.CHANGES).append({
        "ID": max([int(S.clean(c.get("ID"))) for c in R.rows(data, S.CHANGES)
                   if S.clean(c.get("ID")).isdigit()] or [0]) + 1,
        "Tool": name, "Changed On": today_iso(args.on), "Description": note})
    # The row and its ID stay. A tool's number and history are permanent, and
    # old formats sometimes still hold data worth recovering.
    return finish(args, data,
                  "Retired TSP.%s %s -> %s (row kept; ID stays spent)"
                  % (args.id, name, obsolete))


def cmd_review(args):
    data = R.load(args.register)
    tools = R.rows(data, S.TOOLS)
    stamp = today_iso(args.on)
    if args.id:
        rows = [find(tools, args.id)]
        if rows[0] is None:
            sys.exit("No tool with ID %s." % args.id)
    else:
        rows = []
        for row in tools:
            if checks.is_obsolete(row.get("Status")):
                continue
            reviewed = S.clean(row.get("Last Reviewed"))
            if args.before and reviewed and reviewed >= args.before:
                continue
            rows.append(row)
    for row in rows[:10]:
        print("  TSP.%-4s %-34s was %s" % (S.clean(row.get("ID")),
                                           S.tool_name(row)[:34],
                                           S.clean(row.get("Last Reviewed")) or "never"))
    if len(rows) > 10:
        print("  ... and %d more" % (len(rows) - 10))
    if not args.dry_run:
        for row in rows:
            row["Last Reviewed"] = stamp
    return finish(args, data, "Stamped Last Reviewed = %s on %d tool(s)"
                  % (stamp, len(rows)))


def cmd_done(args):
    """Record that a control activity ran.

    Next Due is Last Done plus the Frequency's Days - the one piece of arithmetic
    in this register, and the reason Days is stored alongside each Frequency.
    """
    data = R.load(args.register)
    row = find(R.rows(data, S.CONTROLS), args.control)
    if row is None:
        sys.exit("No control activity with ID %s." % args.control)
    done = today_iso(args.on)
    days = S.frequency_days(data, row.get("Frequency"))
    if days is None:
        sys.exit("Frequency %r has no Days value in this register's vocabulary, "
                 "so Next Due cannot be computed." % S.clean(row.get("Frequency")))
    nxt = (dt.datetime.strptime(done, "%Y-%m-%d")
           + dt.timedelta(days=days)).date().isoformat()

    previous = S.clean(row.get("Next Due"))
    postponed = 0
    if previous and done > previous:
        postponed = 1
    row["Last Done"], row["Next Due"] = done, nxt

    log = R.rows(data, S.ACTIVITY)
    log.append({"ID": max([int(S.clean(a.get("ID"))) for a in log
                           if S.clean(a.get("ID")).isdigit()] or [0]) + 1,
                "Activity": S.clean(row.get("Activity Name")),
                "Done On": done, "Planned For": previous or None,
                "Notes": args.notes, "Times Postponed": postponed or None})
    log[-1] = dict((k, v) for k, v in log[-1].items() if v is not None)

    return finish(args, data,
                  "Recorded %s: %s\n  done %s, %s every %d days -> next due %s"
                  % (args.control, S.clean(row.get("Activity Name")), done,
                     S.clean(row.get("Frequency")), days, nxt))


def cmd_change(args):
    data = R.load(args.register)
    log = R.rows(data, S.CHANGES)
    log.append({"ID": max([int(S.clean(c.get("ID"))) for c in log
                           if S.clean(c.get("ID")).isdigit()] or [0]) + 1,
                "Tool": args.tool, "Changed On": today_iso(args.on),
                "Description": args.message})
    return finish(args, data, "Change log entry %d added for %s"
                  % (log[-1]["ID"], args.tool))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = p.add_subparsers(dest="command")

    def shared(sub):
        sub.add_argument("register")
        sub.add_argument("--on", metavar="YYYY-MM-DD", help="date (default: today)")
        sub.add_argument("--dry-run", action="store_true")

    s = subs.add_parser("register", help="add a tool, claiming the next ID")
    shared(s)
    s.add_argument("name")
    s.add_argument("--description")
    s.add_argument("--type")
    s.add_argument("--status", default="Implemented")
    s.add_argument("--relevancy")
    s.add_argument("--area", help="Primary AF")
    s.add_argument("--skill")
    s.add_argument("--links")
    s.add_argument("--reason", help="change log entry")
    s.set_defaults(func=cmd_register)

    s = subs.add_parser("retire", help="mark a tool obsolete; keep the row and ID")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("--superseded-by", help="ID of the tool that replaced it")
    s.add_argument("--reason")
    s.set_defaults(func=cmd_retire)

    s = subs.add_parser("review", help="stamp Last Reviewed")
    shared(s)
    s.add_argument("--id")
    s.add_argument("--all", action="store_true", help="every non-obsolete tool")
    s.add_argument("--before", metavar="YYYY-MM-DD")
    s.set_defaults(func=cmd_review)

    s = subs.add_parser("done", help="record a control activity execution")
    shared(s)
    s.add_argument("--control", required=True)
    s.add_argument("--notes")
    s.set_defaults(func=cmd_done)

    s = subs.add_parser("change", help="append a change log entry")
    shared(s)
    s.add_argument("--tool", required=True)
    s.add_argument("-m", "--message", required=True)
    s.set_defaults(func=cmd_change)

    args = p.parse_args()
    if not getattr(args, "command", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
