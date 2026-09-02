#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to a RAID register.

    python raid.py add    <register> "Short handle" --type Risk \\
                          --because "..." --risk-that "..." --may-result-in "..."
    python raid.py log    <register> --id 5 -m "what happened"
    python raid.py update <register> --id 5 --set Status=Closed -m "why"
    python raid.py close  <register> --id 5 -m "outcome"
    python raid.py review <register> --id 5 [--next 2026-12-01]
    python raid.py check  <register>
    python raid.py migrate <register> [--apply]

These are the operations with rules attached - claiming an ID that is never
reused, writing the Description in its type's skeleton, and above all appending
to the Action Log so that a field change carries the reason it was made.
Everything else is a field edit: the register is JSON.
"""
import argparse
import datetime as dt
import getpass
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402

ENTRIES = "entries"
ID = "RAID.ID"
LOG = "Action Log"

# Fields whose value is a number, so a --set writes 3 and not "3".
NUMERIC = set(["Urgency (1-5)", "Consequences (1-5)", "Feasibility",
               "Probability of Occurrence (1-5)", "Severity (1-5)",
               "Mitigation Target %", "Residual Risk Score",
               "Estimated Effort", "ETC", "ETC Renegotiated"])

# Every RAID type gets one sentence shape, so that a reader meets the same
# three slots in the same order every time and can skim a register without
# re-reading each entry to work out which part is the cause.
#
# Risk and Issue deliberately share their slots: an issue is a risk that has
# already happened, and keeping the shape identical makes that promotion a
# tense change rather than a rewrite.
SKELETONS = {
    "Risk":     (u"Because of %s, there is a risk that %s, which may result in %s.",
                 ("because_of", "risk_that", "may_result_in"),
                 ("cause", "uncertain event", "impact if it happens")),
    "Issue":    (u"Because of %s, %s, which is resulting in %s.",
                 ("because_of", "happened", "resulting_in"),
                 ("cause", "what has gone wrong", "impact being felt")),
    "Action":   (u"Do %s, by %s, so that %s.",
                 ("do", "by_when", "so_that"),
                 ("the work", "when", "outcome it buys")),
    "Decision": (u"Chose %s, over %s, because %s.",
                 ("chose", "over", "because"),
                 ("option taken", "alternatives rejected", "reason")),
    "Idea":     (u"If %s, then %s.",
                 ("if_we", "then"),
                 ("the change", "expected benefit")),
}

# What a filled-in skeleton looks like from the outside, for `check` to
# recognise. Loose on purpose: it is a drafting aid, not a gate.
SHAPES = {
    "Risk":     re.compile(u"because of .+ there is a risk that .+ "
                           u"(which )?may result in ", re.I | re.S),
    "Issue":    re.compile(u"because of .+ which is resulting in ", re.I | re.S),
    "Action":   re.compile(u"^do .+ so that ", re.I | re.S),
    "Decision": re.compile(u"^chose .+ because ", re.I | re.S),
    "Idea":     re.compile(u"^if .+ then ", re.I | re.S),
}


def today_iso(value=None):
    return value or dt.date.today().isoformat()


def author(args, data):
    """Who is writing. Named explicitly, or the register's default, or the
    account running this - in that order, because a log entry whose author is
    wrong is worse than one that stops to ask."""
    if getattr(args, "by", None):
        return args.by
    who = R.setting(data, "author") or os.environ.get("RAID_AUTHOR")
    if who:
        return who
    try:
        who = getpass.getuser()
    except Exception:
        who = ""
    if not who:
        sys.exit("No author. Pass --by NAME, or set meta.settings.author in the "
                 "register so every entry is attributed the same way.")
    return who


def find(data, wanted):
    row = R.get(data, ENTRIES, ID, wanted)
    if row is None:
        sys.exit("No entry R.%s in this register." % wanted)
    return row


def vocabulary(data, name):
    return R.setting(data, "vocabularies", {}).get(name) or []


def check_vocab(data, name, value):
    allowed = vocabulary(data, name)
    if value and allowed and value not in allowed:
        sys.exit("%r is not in the %s vocabulary.\n  allowed: %s"
                 % (value, name, ", ".join(allowed)))


def fields_of(data):
    return R.setting(data, "fields", {}).get(ENTRIES) or []


# --- the log ----------------------------------------------------------------

def entries_of(row):
    """The Action Log as a list, whatever it is on disk.

    A register written before the log was structured holds one free-text
    string. Read it as a single undated entry rather than failing: the
    dashboard and `check` both have to cope with a register that has not been
    migrated yet, and silently dropping the text would be the worst outcome.
    """
    log = row.get(LOG)
    if not log:
        return []
    if isinstance(log, list):
        return log
    return [{"note": R.clean(log)}]


def append_log(row, on, by, note, changed=None):
    entry = {"on": on, "by": by}
    if note:
        entry["note"] = note
    if changed:
        entry["changed"] = changed
    log = entries_of(row)
    log.append(entry)
    row[LOG] = log
    return entry


def render(entry):
    bits = []
    if entry.get("changed"):
        bits.append(", ".join(
            "%s %s -> %s" % (k, v[0] or "(empty)", v[1] or "(empty)")
            for k, v in sorted(entry["changed"].items())))
    if entry.get("note"):
        bits.append(entry["note"])
    return "%s  %-10s %s" % (entry.get("on", "??????????"),
                             entry.get("by", "?"), "  ".join(bits))


# --- validation -------------------------------------------------------------

def run_checks(data):
    """Read-only. Errors are things that will misrender or mislead; warnings are
    conventions worth following that no one should be blocked on."""
    errors, warnings = [], []
    known = set(fields_of(data))
    types, statuses = vocabulary(data, "type"), vocabulary(data, "status")

    for row in R.rows(data, ENTRIES):
        rid = R.clean(row.get(ID)) or "?"
        typ, status = R.clean(row.get("Type")), R.clean(row.get("Status"))

        if types and typ and typ not in types:
            errors.append("R.%s Type %r is not in the vocabulary" % (rid, typ))
        if statuses and status and status not in statuses:
            errors.append("R.%s Status %r is not in the vocabulary" % (rid, status))
        for name in row:
            if known and name not in known:
                errors.append("R.%s has field %r, which the schema does not "
                              "define" % (rid, name))

        log = row.get(LOG)
        if isinstance(log, list):
            for i, e in enumerate(log):
                if not isinstance(e, dict):
                    errors.append("R.%s Action Log entry %d is not an object"
                                  % (rid, i + 1))
                elif not e.get("on") or not e.get("by"):
                    warnings.append("R.%s Action Log entry %d has no date or "
                                    "author" % (rid, i + 1))
        elif log:
            warnings.append("R.%s Action Log is still free text - run "
                            "`raid.py migrate`" % rid)

        shape = SHAPES.get(typ)
        desc = R.clean(row.get("Description"))
        if shape and desc and not shape.search(desc):
            warnings.append("R.%s Description does not follow the %s shape: %s"
                            % (rid, typ, template_hint(typ)))
        if status == "Closed" and not R.clean(row.get("Closed On")):
            warnings.append("R.%s is Closed with no Closed On" % rid)
        if typ == "Risk" and not (row.get("Probability of Occurrence (1-5)")
                                  and row.get("Severity (1-5)")):
            warnings.append("R.%s is a Risk with no Probability/Severity, so it "
                            "has no residual risk" % rid)
    return errors, warnings


def template_hint(typ):
    shape, _slots, labels = SKELETONS[typ]
    return shape % tuple("<%s>" % l for l in labels)


def report(args, data, note):
    print(note)
    if getattr(args, "dry_run", False):
        print("\n  dry run - nothing written.")
        return 0
    R.save(args.register, data)
    errors, warnings = run_checks(data)
    for name, _reason in R.stale_views(args.register):
        warnings.append("%s was built from different data - regenerate it" % name)
    print("\n  check   %d error(s), %d warning(s)" % (len(errors), len(warnings)))
    for msg in errors[:5]:
        print("          ERROR   %s" % msg)
    for msg in warnings[:5]:
        print("          warning %s" % msg)
    if len(warnings) > 5:
        print("          ... and %d more (run `raid.py check`)" % (len(warnings) - 5))
    return 0


# --- commands ---------------------------------------------------------------

def cmd_add(args):
    data = R.load(args.register)
    check_vocab(data, "type", args.type)
    rows = R.rows(data, ENTRIES)

    shape, slots, _labels = SKELETONS[args.type]
    given = [getattr(args, s, None) for s in slots]
    if args.description and any(given):
        sys.exit("Pass either --description or the %s slots (%s), not both."
                 % (args.type, ", ".join("--" + s.replace("_", "-") for s in slots)))
    if args.description:
        description = args.description
    elif all(given):
        description = shape % tuple(given)
    elif any(given):
        missing = [s for s, v in zip(slots, given) if not v]
        sys.exit("A %s needs all %d slots. Missing: %s\n  %s"
                 % (args.type, len(slots),
                    ", ".join("--" + m.replace("_", "-") for m in missing),
                    template_hint(args.type)))
    else:
        sys.exit("A %s needs a description. Either:\n  %s\nor pass "
                 "--description to write it freehand."
                 % (args.type, template_hint(args.type)))

    new_id = R.next_id(data, ENTRIES, ID) or 1
    if not R.rows(data, ENTRIES):
        new_id = 1
    on, by = today_iso(args.on), author(args, data)
    row = {ID: new_id, "Detail": args.detail, "Type": args.type,
           "Status": "Open", "Description": description,
           "Opened On": on, "DRI": args.dri or by}
    for key, value in (("MoSCoW", args.moscow), ("Category", args.category),
                       ("Action Plan", args.action_plan),
                       ("Acceptance Criteria", args.acceptance),
                       ("Requested By", args.requested_by)):
        if value:
            row[key] = value
    append_log(row, on, by, "Opened.")
    rows.append(row)
    return report(args, data, "Added R.%d  %s  (%s)\n  %s"
                  % (new_id, args.detail, args.type, description))


def cmd_log(args):
    data = R.load(args.register)
    row = find(data, args.id)
    entry = append_log(row, today_iso(args.on), author(args, data), args.message)
    return report(args, data, "R.%s  %s" % (args.id, render(entry)))


def cmd_update(args):
    data = R.load(args.register)
    row = find(data, args.id)
    known = fields_of(data)
    changed = {}
    for pair in args.set:
        if "=" not in pair:
            sys.exit("--set wants Field=Value, got %r" % pair)
        name, _, value = pair.partition("=")
        name, value = name.strip(), value.strip()
        if known and name not in known:
            sys.exit("%r is not a field in this register.\n  fields: %s"
                     % (name, ", ".join(known)))
        if name == LOG:
            sys.exit("The Action Log is append-only. Use `raid.py log` instead.")
        if name in ("Type", "Status"):
            check_vocab(data, name.lower(), value)
        was = row.get(name)
        if name in NUMERIC and value:
            try:
                value = int(value) if "." not in value else float(value)
            except ValueError:
                sys.exit("%s takes a number, got %r" % (name, value))
        if str(was or "") == str(value):
            continue
        changed[name] = [R.clean(was), value]
        if value:
            row[name] = value
        else:
            row.pop(name, None)
    if not changed:
        sys.exit("Nothing changed - every --set already holds that value.")

    # The whole point: a field change and the reason for it are one entry, so
    # the register can never say what changed without saying why.
    entry = append_log(row, today_iso(args.on), author(args, data),
                       args.message, changed)
    return report(args, data, "R.%s  %s" % (args.id, render(entry)))


def cmd_close(args):
    data = R.load(args.register)
    row = find(data, args.id)
    if R.clean(row.get("Status")) == "Closed":
        sys.exit("R.%s is already Closed." % args.id)
    on, by = today_iso(args.on), author(args, data)
    changed = {"Status": [R.clean(row.get("Status")), "Closed"]}
    row["Status"], row["Closed On"], row["Closed By"] = "Closed", on, by
    entry = append_log(row, on, by, args.message, changed)
    return report(args, data, "Closed R.%s  %s\n  %s"
                  % (args.id, R.clean(row.get("Detail")), render(entry)))


def cmd_review(args):
    data = R.load(args.register)
    on, by = today_iso(args.on), author(args, data)
    if args.id:
        rows = [find(data, args.id)]
    else:
        rows = [r for r in R.rows(data, ENTRIES)
                if R.clean(r.get("Status")) != "Closed"]
    for row in rows:
        changed = {"Last Review": [R.clean(row.get("Last Review")), on]}
        row["Last Review"] = on
        if args.next:
            changed["Next Review On"] = [R.clean(row.get("Next Review On")),
                                         args.next]
            row["Next Review On"] = args.next
        append_log(row, on, by, args.message or "Reviewed; no change.", changed)
    return report(args, data, "Reviewed %d entr%s, Last Review = %s"
                  % (len(rows), "y" if len(rows) == 1 else "ies", on))


def cmd_check(args):
    data = R.load(args.register)
    errors, warnings = run_checks(data)
    for name, reason in R.stale_views(args.register):
        warnings.append("%s %s" % (name, reason))
    print("%s\n  %d entries, %d error(s), %d warning(s)\n"
          % (args.register, len(R.rows(data, ENTRIES)), len(errors), len(warnings)))
    for msg in errors:
        print("  ERROR   %s" % msg)
    for msg in warnings:
        print("  warning %s" % msg)
    return 1 if errors else 0


# A free-text log written before the log was structured. These carried their
# date inline, in the two shapes people actually used.
LEADING_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})[.\s]+")
WORD_DATE = re.compile(r"^(\w+)\s+(\d{4}-\d{2}-\d{2})\.?\s+")


def split_date(text):
    """(date, remaining note). Only strips what it is certain is a date."""
    match = LEADING_DATE.match(text)
    if match:
        return match.group(1), text[match.end():].strip()
    match = WORD_DATE.match(text)
    if match:
        return match.group(2), (match.group(1) + ". " + text[match.end():]).strip()
    return None, text.strip()


def cmd_migrate(args):
    """Turn free-text Action Logs into dated entries.

    Dry by default. The date is only ever taken from the text itself and the
    author only from the row's DRI - neither is invented, so an entry that
    carried neither stays undated rather than being given a plausible date.
    """
    data = R.load(args.register)
    plan = []
    for row in R.rows(data, ENTRIES):
        log = row.get(LOG)
        if not log or isinstance(log, list):
            continue
        on, note = split_date(R.clean(log))
        entry = {}
        if on:
            entry["on"] = on
        by = R.clean(row.get("DRI"))
        if by:
            entry["by"] = by
        entry["note"] = note
        plan.append((row, entry))

    if not plan:
        print("Nothing to migrate - every Action Log is already structured.")
        return 0
    for row, entry in plan:
        print("R.%s  %s" % (R.clean(row.get(ID)), R.clean(row.get("Detail"))))
        print("   from  %r" % R.clean(row.get(LOG))[:100])
        print("   to    on=%s by=%s\n         note=%r"
              % (entry.get("on") or "(none in the text)",
                 entry.get("by") or "(no DRI)", entry["note"][:100]))
    print("\n%d entr%s to convert." % (len(plan), "y" if len(plan) == 1 else "ies"))
    if not args.apply:
        print("Dry run. Re-run with --apply to write.")
        return 0
    for row, entry in plan:
        row[LOG] = [entry]
    if args.author and not R.setting(data, "author"):
        data["meta"].setdefault("settings", {})["author"] = args.author
    R.save(args.register, data)
    print("Written.")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = p.add_subparsers(dest="command")

    def shared(sub, dated=True):
        sub.add_argument("register")
        if dated:
            sub.add_argument("--on", metavar="YYYY-MM-DD",
                             help="date for the log entry (default: today)")
            sub.add_argument("--by", metavar="NAME", help="author of the entry")
            sub.add_argument("--dry-run", action="store_true")

    s = subs.add_parser("add", help="add an entry, claiming the next ID")
    shared(s)
    s.add_argument("detail", help="short handle, not the full sentence")
    s.add_argument("--type", required=True, choices=sorted(SKELETONS))
    seen = set()
    for typ in sorted(SKELETONS):
        shape, slots, labels = SKELETONS[typ]
        for slot, label in zip(slots, labels):
            flag = "--" + slot.replace("_", "-")
            if flag not in seen:
                seen.add(flag)
                s.add_argument(flag, help="%s: %s" % (typ, label))
    s.add_argument("--description", help="freehand, bypassing the type's shape")
    s.add_argument("--dri")
    s.add_argument("--moscow")
    s.add_argument("--category")
    s.add_argument("--action-plan")
    s.add_argument("--acceptance", help="Acceptance Criteria")
    s.add_argument("--requested-by")
    s.set_defaults(func=cmd_add)

    s = subs.add_parser("log", help="append a note to an entry's Action Log")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("-m", "--message", required=True)
    s.set_defaults(func=cmd_log)

    s = subs.add_parser("update", help="change fields, logging what and why")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("--set", action="append", default=[], metavar="Field=Value",
                   help="repeatable; empty value clears the field")
    s.add_argument("-m", "--message", help="why - recorded with the change")
    s.set_defaults(func=cmd_update)

    s = subs.add_parser("close", help="close an entry and record the outcome")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("-m", "--message", help="the outcome")
    s.set_defaults(func=cmd_close)

    s = subs.add_parser("review", help="stamp Last Review and log the review")
    shared(s)
    s.add_argument("--id", help="omit to review every open entry")
    s.add_argument("--next", metavar="YYYY-MM-DD", help="set Next Review On")
    s.add_argument("-m", "--message")
    s.set_defaults(func=cmd_review)

    s = subs.add_parser("check", help="read-only health report")
    shared(s, dated=False)
    s.set_defaults(func=cmd_check)

    s = subs.add_parser("migrate", help="free-text Action Logs -> dated entries")
    shared(s, dated=False)
    s.add_argument("--apply", action="store_true", help="write (default: dry run)")
    s.add_argument("--author", help="also set meta.settings.author")
    s.set_defaults(func=cmd_migrate)

    args = p.parse_args()
    if not getattr(args, "command", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
