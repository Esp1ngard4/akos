#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to a WBS register.

    python wbs.py add     <register> "Title" --type Story --parent 37
    python wbs.py set     <register> --id 42 --status Done --nature Improve
    python wbs.py check   <register>
    python wbs.py migrate <register> [--apply]
    python wbs.py sprints seed   <conventions.json> --scope "Project name" --year 2026
    python wbs.py sprints import <register> --from <conventions.json>

These are the operations with rules attached - claiming an ID that is never
reused, refusing a Parent that does not exist or that would close a cycle,
keeping Key Deliverable off rows that cannot carry it, and holding every
vocabulary field to the register's own vocabulary. Everything else is a field
edit: the register is JSON.

The axes a row carries are deliberately separate, and `check` enforces the
separation:

    Type      the level             Deliverable / Feature / Story / Task
    Class     what value it serves  Product / Management / Enabler
    Delivers  the artifact kind     Tool / System / Process / Document
    Nature    what is being done    Build / Improve / Analyse / Fix / Maintain

None of the levels is defined by duration. A Story is the smallest slice that
is independently valuable and independently verifiable; a Task is a step that
is not independently valuable. How long either takes is Estimated Effort (h),
which says it better than a level name ever did.

A deliverable is not a collection of its own - it is a row whose Key
Deliverable is Y. `Parent` is what connects it to the work that delivers it,
and it holds the parent's stable `ID`, never its `Code`.

Two more fields say *when*, and they are not the same question:

    Horizon         how soon I want it    Next / Future
    Sprint Planned  which sprint it is in a sprint ID from the calendar

Horizon is an intention and Sprint Planned is a commitment, so assigning a
sprint supersedes the horizon and `check` says so. The sprint calendar is
defined by the sprint ceremonies, kept in the project's agile conventions file, and imported
here - the register never invents one.
"""
import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402

ITEMS = "items"
SPRINTS = "sprints"
# Assigning a real sprint, or closing the row, both supersede an intention
# about how soon. Without this the field rots exactly as Next/Future did in
# Sprint Planned - 18 of 45 rows stale and nothing to catch it.
HORIZON_CLEARS_ON = ("Done", "Cancelled")
SPRINT_FIELDS_ON_ITEM = ("Sprint Planned", "Sprint Added", "Sprint Ended")
# Only these levels name a thing rather than an activity, so only these can be
# put in front of a sponsor as a deliverable. Key Deliverable is curation, not
# classification - it marks what earns a line in an executive report, which is
# a smaller set than everything with Class = Product.
DELIVERABLE_LEVELS = ("Deliverable", "Feature")

# Old Type values, which mixed level with artifact kind and with nature.
# Each maps onto the three axes that replaced it.
LEGACY_TYPES = {
    "Enabler":    {"Type": "Feature", "Class": "Enabler"},
    "Feature":    {"Type": "Feature"},
    "Story":      {"Type": "Story"},
    "Tool":       {"Type": "Feature", "Delivers": "Tool"},
    "System":     {"Type": "Feature", "Delivers": "System"},
    "Process":    {"Type": "Feature", "Delivers": "Process"},
    "DocSection": {"Type": "Story",   "Delivers": "Document"},
    "Analysis":   {"Type": "Story",   "Nature": "Analyse"},
    "Improve":    {"Type": "Story",   "Nature": "Improve"},
}


def vocabulary(data, name):
    return (data.get("meta", {}).get("settings", {})
                .get("vocabularies", {}).get(name) or [])


def check_vocab(data, name, value):
    allowed = vocabulary(data, name)
    if value and allowed and value not in allowed:
        sys.exit("%r is not in the %s vocabulary.\n  allowed: %s"
                 % (value, name, ", ".join(allowed)))


def as_id(value):
    """IDs are integers; keep them that way however they arrived."""
    if value in (None, ""):
        return value
    text = str(value).strip()
    return int(text) if text.lstrip("-").isdigit() else text


def find(data, wanted):
    for row in R.rows(data, ITEMS):
        if str(row.get("ID")) == str(wanted):
            return row
    return None


def ancestors(data, start):
    """Walk Parent upward, stopping on a cycle rather than looping forever."""
    seen, node = [], find(data, start)
    while node is not None and node.get("Parent") not in (None, ""):
        pid = str(node["Parent"])
        if pid in seen:
            break
        seen.append(pid)
        node = find(data, pid)
    return seen


def check_parent(data, child_id, parent):
    if parent in (None, ""):
        return
    if find(data, parent) is None:
        sys.exit("No item with ID %s to be the parent. Parent holds the "
                 "parent's stable ID, never its Code." % parent)
    if child_id is not None and str(parent) == str(child_id):
        sys.exit("An item cannot be its own parent.")
    if child_id is not None and str(child_id) in ancestors(data, parent):
        sys.exit("That parent is a descendant of item %s - it would close a "
                 "cycle." % child_id)


def check_deliverable(row):
    if row.get("Key Deliverable") == "Y" and row.get("Type") not in DELIVERABLE_LEVELS:
        sys.exit("Key Deliverable = Y needs Type to be one of %s - it is %r. "
                 "Deliverables and Features name things; Stories and Tasks name "
                 "activity, and an activity cannot be reported as a deliverable."
                 % (" / ".join(DELIVERABLE_LEVELS), row.get("Type")))


def finish(args, data, note):
    print(note)
    if getattr(args, "dry_run", False):
        print("\n  dry run - nothing written.")
        return 0
    R.save(args.register, data)
    for name, _reason in R.stale_views(args.register):
        print("  note: %s is now stale - rerun refresh_wbs.py" % name)
    return 0


# --------------------------------------------------------------------------- #

def cmd_add(args):
    data = R.load(args.register)
    for field, value in (("type", args.type), ("class", args.klass),
                         ("nature", args.nature), ("delivers", args.delivers),
                         ("status", args.status), ("priority", args.priority),
                         ("horizon", args.horizon)):
        check_vocab(data, field, value)
    check_parent(data, None, args.parent)

    # next_id returns 0 for an empty collection; IDs here start at 1.
    row = {"ID": R.next_id(data, ITEMS) or 1, "Title": args.title}
    for key, value in (("Parent", as_id(args.parent)), ("Code", args.code),
                       ("Type", args.type), ("Class", args.klass),
                       ("Nature", args.nature),
                       ("Delivers", args.delivers), ("Status", args.status),
                       ("Priority", args.priority), ("Owner", args.owner),
                       ("Key Deliverable", args.key_deliverable),
                       ("Horizon", args.horizon),
                       ("Description", args.description)):
        if value:
            row[key] = value
    row.setdefault("Status", "Portfolio Backlog")
    row.setdefault("Type", "Story")
    row.setdefault("Nature", "Build")
    row.setdefault("Class", "Product")
    check_deliverable(row)
    R.rows(data, ITEMS).append(row)
    return finish(args, data, "Added item %s  %s" % (row["ID"], args.title))


def cmd_set(args):
    data = R.load(args.register)
    row = find(data, args.id)
    if row is None:
        sys.exit("No item with ID %s." % args.id)
    for field, value in (("type", args.type), ("class", args.klass),
                         ("nature", args.nature), ("delivers", args.delivers),
                         ("status", args.status), ("priority", args.priority),
                         ("horizon", args.horizon)):
        check_vocab(data, field, value)
    if args.parent is not None:
        check_parent(data, args.id, args.parent)

    changed = []
    for key, value in (("Parent", as_id(args.parent)), ("Code", args.code),
                       ("Title", args.title), ("Type", args.type),
                       ("Class", args.klass),
                       ("Nature", args.nature), ("Delivers", args.delivers),
                       ("Status", args.status), ("Priority", args.priority),
                       ("Owner", args.owner),
                       ("Key Deliverable", args.key_deliverable),
                       ("Horizon", args.horizon)):
        if value is None:
            continue
        if value == "":                      # explicit clear
            row.pop(key, None)
            changed.append("%s cleared" % key)
        else:
            row[key] = value
            changed.append("%s=%s" % (key, value))
    check_deliverable(row)
    if not changed:
        sys.exit("Nothing to change. Pass at least one field.")
    return finish(args, data, "Item %s: %s" % (args.id, ", ".join(changed)))


def cmd_check(args):
    data = R.load(args.register)
    items = R.rows(data, ITEMS)
    known_sprints = {s.get("Sprint") for s in data.get(SPRINTS) or []}
    errors, warnings = [], []

    seen = {}
    for row in items:
        rid = row.get("ID")
        if rid in seen:
            errors.append("duplicate ID %s" % rid)
        seen[rid] = row

    for row in items:
        rid = row.get("ID")
        for field, vocab in (("Type", "type"), ("Class", "class"),
                             ("Nature", "nature"),
                             ("Delivers", "delivers"), ("Status", "status"),
                             ("Priority", "priority"),
                             ("Key Deliverable", "key deliverable")):
            value = row.get(field)
            allowed = vocabulary(data, vocab)
            if value and allowed and value not in allowed:
                errors.append("item %s: %s=%r not in vocabulary" % (rid, field, value))

        parent = row.get("Parent")
        if parent not in (None, ""):
            if find(data, parent) is None:
                errors.append("item %s: Parent %s does not exist" % (rid, parent))
            elif str(rid) in ancestors(data, parent):
                errors.append("item %s: Parent %s closes a cycle" % (rid, parent))
        elif row.get("Type") not in DELIVERABLE_LEVELS and row.get("Type"):
            warnings.append("item %s: %s with no Parent" % (rid, row.get("Type")))

        if row.get("Key Deliverable") == "Y" and row.get("Type") not in DELIVERABLE_LEVELS:
            errors.append("item %s: Key Deliverable=Y on a %s"
                          % (rid, row.get("Type") or "row with no Type"))
        if not row.get("Type"):
            warnings.append("item %s: no Type" % rid)

        # Horizon is an intention about how soon. A real sprint, or a closed
        # row, settles the question and the intention has to go.
        horizon = row.get("Horizon")
        if horizon:
            if row.get("Status") in HORIZON_CLEARS_ON:
                errors.append("item %s: Horizon=%s on a %s row - closing the "
                              "row supersedes it" % (rid, horizon, row.get("Status")))
            if row.get("Sprint Planned"):
                errors.append("item %s: Horizon=%s and Sprint Planned=%s - a "
                              "commitment supersedes an intention"
                              % (rid, horizon, row.get("Sprint Planned")))

        # Sprint fields hold calendar IDs and nothing else. Silent until the
        # register has a calendar: with no sprints imported there is nothing
        # to check against, and guessing would be worse than saying nothing.
        for field in SPRINT_FIELDS_ON_ITEM:
            value = row.get(field)
            if value and known_sprints and value not in known_sprints:
                errors.append("item %s: %s=%r is not a sprint in the calendar"
                              % (rid, field, value))

    if not known_sprints and any(row.get(f) for row in items
                                 for f in SPRINT_FIELDS_ON_ITEM):
        warnings.append("sprint IDs are in use but the register has no "
                        "calendar - run: wbs.py sprints import")

    if "key_deliverables" in data:
        warnings.append("register still carries a key_deliverables collection "
                        "- run migrate")

    for line in errors:
        print("  ERROR   %s" % line)
    for line in warnings[:20]:
        print("  warn    %s" % line)
    if len(warnings) > 20:
        print("  warn    ... and %d more" % (len(warnings) - 20))
    print("\n  %d item(s), %d error(s), %d warning(s)"
          % (len(items), len(errors), len(warnings)))
    return 1 if errors else 0


def cmd_migrate(args):
    """Bring a register onto the three-axis schema. Dry run unless --apply."""
    data = R.load(args.register)
    items = R.rows(data, ITEMS)
    notes = []

    for row in items:
        legacy = row.get("Type")
        if legacy in LEGACY_TYPES:
            mapped = LEGACY_TYPES[legacy]
            if mapped.get("Type") != legacy or len(mapped) > 1:
                row.update(mapped)
                notes.append("item %s: Type %s -> %s"
                             % (row.get("ID"), legacy,
                                ", ".join("%s=%s" % kv for kv in mapped.items())))
        row.setdefault("Nature", "Build")
        row.setdefault("Class", "Product")

    # Next/Future were living in Sprint Planned, mirroring the task tracker's labels.
    # They are a horizon, not a commitment, and the wrong home is why 18 of
    # 45 went stale unnoticed - a field nothing validates cannot rot loudly.
    # Closing the row settles the question, so those are dropped, not moved.
    for row in items:
        horizon = row.get("Sprint Planned")
        if horizon not in ("Next", "Future"):
            continue
        del row["Sprint Planned"]
        if row.get("Status") in HORIZON_CLEARS_ON:
            notes.append("item %s: Sprint Planned=%s dropped - row is %s"
                         % (row.get("ID"), horizon, row.get("Status")))
        else:
            row["Horizon"] = horizon
            notes.append("item %s: Sprint Planned=%s -> Horizon"
                         % (row.get("ID"), horizon))

    # Parent from Code, which is the only place the hierarchy exists today.
    by_code = {str(r.get("Code")): r for r in items if r.get("Code") not in (None, "")}
    for row in items:
        if row.get("Parent") not in (None, ""):
            continue
        code = str(row.get("Code") or "")
        if "." not in code:
            continue
        parent = by_code.get(code.rsplit(".", 1)[0])
        if parent is not None:
            row["Parent"] = parent["ID"]
            notes.append("item %s: Parent <- %s (from Code %s)"
                         % (row.get("ID"), parent["ID"], code))

    settings = data.setdefault("meta", {}).setdefault("settings", {})
    vocabs = settings.setdefault("vocabularies", {})
    import create_wbs as C
    for name, values in (("type", C.TYPES), ("class", C.CLASSES),
                         ("nature", C.NATURES), ("horizon", C.HORIZONS),
                         ("delivers", C.DELIVERS), ("key deliverable", C.YESNO)):
        if vocabs.get(name) != values:
            vocabs[name] = values
            notes.append("vocabulary %r registered" % name)
    if vocabs.get("status") != C.STATUSES:
        vocabs["status"] = C.STATUSES
        notes.append("vocabulary 'status' corrected (Portfolio Backlog)")
    for row in items:
        if row.get("Status") == "Backlog":
            row["Status"] = "Portfolio Backlog"
            notes.append("item %s: Status Backlog -> Portfolio Backlog" % row.get("ID"))
    if settings.get("fields", {}).get("items") != C.ITEM_FIELDS:
        settings.setdefault("fields", {})["items"] = C.ITEM_FIELDS
        notes.append("item field order updated")

    if "key_deliverables" in data:
        rows = data["key_deliverables"]
        if rows:
            notes.append("!! %d key_deliverables row(s) still present - fold them "
                         "into items as Feature rows with Key Deliverable=Y "
                         "before this collection can be dropped" % len(rows))
        else:
            settings.get("fields", {}).pop("key_deliverables", None)
            del data["key_deliverables"]
            notes.append("empty key_deliverables collection dropped")

    for line in notes:
        print("  %s" % line)
    print("\n  %d change(s)" % len(notes))
    if not args.apply:
        print("\n  dry run - nothing written. Pass --apply to write.")
        return 0
    R.save(args.register, data)
    print("  written to %s" % args.register)
    return 0


# --------------------------------------------------------------------------- #
# The sprint calendar. The ceremonies own the convention; these two commands seed a
# project's copy of it and pull it into a register. Nothing here decides what
# a sprint is - it only arithmetic on an anchor the ceremony supplies.

def sprint_series(year, anchor, length):
    """Every sprint starting in `year`, as (id, start, end) triples.

    `anchor` is any real sprint start date, not 1 January: the cadence is
    whatever the ceremonies have actually been running, and rounding it to the
    calendar year moved the one recorded 2026 sprint by three days. A sprint
    belongs to the quarter it starts in and keeps its length at the boundary,
    so the quarters hold uneven counts and the last sprint of the year runs
    into the next one. Both are correct, not artefacts to square off.
    """
    step = timedelta(days=length)
    start = anchor
    while start - step >= date(year, 1, 1):
        start -= step
    while start < date(year, 1, 1):
        start += step
    series, counts = [], {}
    while start.year == year:
        q = (start.month - 1) // 3 + 1
        counts[q] = counts.get(q, 0) + 1
        series.append(("S%02d.Q%d.%d" % (year % 100, q, counts[q]),
                       start, start + timedelta(days=length - 1)))
        start += step
    return series


def cmd_sprints_seed(args):
    if os.path.exists(args.output) and not args.force:
        sys.exit("%s already exists. Pass --force to regenerate it - but a "
                 "stored calendar outranks a derived one the moment a ceremony "
                 "has actually moved." % args.output)
    anchor = date.fromisoformat(args.anchor)
    series = sprint_series(args.year, anchor, args.length)
    import create_wbs as C
    data = R.new("agile-conventions", args.scope,
                 {"sprints": [{"Sprint": sid, "Starts": a.isoformat(),
                               "Ends": b.isoformat()} for sid, a, b in series]},
                 settings={"fields": {"sprints": C.SPRINT_FIELDS},
                           "cadence": {"anchor": args.anchor,
                                       "length_days": args.length,
                                       "seeded_for": args.year}})
    R.save(args.output, data)
    counts = {}
    for sid, _a, _b in series:
        q = sid.split(".")[1]
        counts[q] = counts.get(q, 0) + 1
    print("Seeded %s with %d sprint(s): %s"
          % (args.output, len(series),
             ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
    print("  %s %s -> %s (last)" % (series[-1][0], series[-1][1], series[-1][2]))
    print("\n  This is a seed. Once a ceremony moves, edit the row - the stored "
          "date is\n  the record and regenerating would discard it.")
    return 0


def cmd_sprints_import(args):
    data = R.load(args.register)
    src = R.load(args.source)
    kind = src.get("meta", {}).get("kind")
    if kind != "agile-conventions":
        sys.exit("%s is a %r, not an agile-conventions file. The calendar comes "
                 "from the project's agile conventions file."
                 % (args.source, kind))

    current = {s.get("Sprint"): s for s in data.get(SPRINTS) or []}
    incoming = {s.get("Sprint"): s for s in src.get("sprints") or []}
    added = [k for k in incoming if k not in current]
    removed = [k for k in current if k not in incoming]
    changed = [k for k in incoming if k in current and incoming[k] != current[k]]

    in_use = {row.get(f) for row in R.rows(data, ITEMS)
              for f in SPRINT_FIELDS_ON_ITEM if row.get(f)}
    orphaned = sorted(s for s in removed if s in in_use)

    for k in sorted(added):
        print("  +   %s  %s -> %s" % (k, incoming[k].get("Starts"), incoming[k].get("Ends")))
    for k in sorted(changed):
        print("  ~   %s  %s -> %s  (was %s -> %s)"
              % (k, incoming[k].get("Starts"), incoming[k].get("Ends"),
                 current[k].get("Starts"), current[k].get("Ends")))
    for k in sorted(removed):
        print("  -   %s%s" % (k, "   IN USE" if k in in_use else ""))
    if not (added or changed or removed):
        print("  calendar already matches - nothing to do.")
        return 0
    print("\n  %d added, %d changed, %d removed" % (len(added), len(changed), len(removed)))

    if orphaned and not args.force:
        sys.exit("\n  Refusing: %s %s referenced by items and would be dropped.\n"
                 "  Fix the conventions file, or pass --force to leave those "
                 "references dangling." % (", ".join(orphaned),
                                           "is" if len(orphaned) == 1 else "are"))
    if args.dry_run:
        print("\n  dry run - nothing written.")
        return 0
    data[SPRINTS] = [dict(incoming[k]) for k in sorted(incoming)]
    data.setdefault("meta", {}).setdefault("settings", {}) \
        .setdefault("fields", {})[SPRINTS] = \
        src.get("meta", {}).get("settings", {}).get("fields", {}).get("sprints")
    return finish(args, data, "  imported from %s" % args.source)


# --------------------------------------------------------------------------- #

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = p.add_subparsers(dest="command")

    def fields(sub):
        sub.add_argument("--parent", help="parent item's stable ID")
        sub.add_argument("--code")
        sub.add_argument("--type")
        sub.add_argument("--class", dest="klass")
        sub.add_argument("--nature")
        sub.add_argument("--delivers")
        sub.add_argument("--status")
        sub.add_argument("--priority")
        sub.add_argument("--owner")
        sub.add_argument("--key-deliverable", choices=["Y", "N"])
        sub.add_argument("--horizon", help="Next / Future, or '' to clear")
        sub.add_argument("--dry-run", action="store_true")

    s = subs.add_parser("add", help="add an item, claiming the next ID")
    s.add_argument("register")
    s.add_argument("title")
    s.add_argument("--description")
    fields(s)
    s.set_defaults(func=cmd_add)

    s = subs.add_parser("set", help="change fields on an item")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("--title")
    fields(s)
    s.set_defaults(func=cmd_set)

    s = subs.add_parser("check", help="validate IDs, parents and vocabularies")
    s.add_argument("register")
    s.set_defaults(func=cmd_check)

    s = subs.add_parser("migrate", help="bring a register onto the current schema")
    s.add_argument("register")
    s.add_argument("--apply", action="store_true",
                   help="write the changes (default is a dry run)")
    s.set_defaults(func=cmd_migrate)

    sp = subs.add_parser("sprints", help="seed or import the sprint calendar")
    sps = sp.add_subparsers(dest="sprints_command")

    s = sps.add_parser("seed", help="generate a default series into a "
                                    "conventions file")
    s.add_argument("output", help="the project's agile conventions file")
    s.add_argument("--scope", required=True, help='e.g. "Project name"')
    s.add_argument("--year", type=int, required=True)
    s.add_argument("--anchor", required=True, metavar="YYYY-MM-DD",
                   help="a real sprint start date, from the ceremony record")
    s.add_argument("--length", type=int, default=14, metavar="DAYS")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_sprints_seed)

    s = sps.add_parser("import", help="read a conventions file into the register")
    s.add_argument("register")
    s.add_argument("--from", dest="source", required=True)
    s.add_argument("--force", action="store_true",
                   help="drop sprints even when items still reference them")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_sprints_import)

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
