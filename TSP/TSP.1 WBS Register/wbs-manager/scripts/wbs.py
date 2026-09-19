#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to a WBS register.

    python wbs.py add     <register> "Title" --type Story --parent 37
    python wbs.py set     <register> --id 42 --status Done --nature Improve
    python wbs.py check   <register>
    python wbs.py migrate <register> [--apply]

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
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402

ITEMS = "items"
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
                         ("status", args.status), ("priority", args.priority)):
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
                         ("status", args.status), ("priority", args.priority)):
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
                       ("Key Deliverable", args.key_deliverable)):
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
                         ("nature", C.NATURES),
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

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
