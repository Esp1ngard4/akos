#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to a WBS register.

    python wbs.py add     <register> "Title" --type Story --parent 37
    python wbs.py set     <register> --id 42 --status Done --nature Improve
    python wbs.py check   <register>
    python wbs.py rebaseline <register> --id 42 --baseline-end Q2-26 --reason "..."
    python wbs.py metrics <register> --sprint S26.Q3.5
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
import dates as D                                               # noqa: E402
import create_wbs as C                                          # noqa: E402

ITEMS = "items"
SPRINTS = "sprints"
SCHEDULE_LOG = "schedule_log"
# --flag -> field. The six schedule dates; see dates.py for what a value
# may look like and why precision is derived rather than stored.
DATE_ARGS = [(f.lower().replace(" ", "_"), f) for f in C.DATE_FIELDS]
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


def has_children(data, item_id):
    return any(str(r.get("Parent")) == str(item_id) for r in R.rows(data, ITEMS))


def check_date(field, value):
    """Reject what cannot be parsed rather than coercing it (R8).

    A date nobody can parse is worse than a blank one: blank is honestly
    unknown, while a silently coerced value looks like an answer.
    """
    if value in (None, ""):
        return
    if D.resolve(value) is None:
        sys.exit("%r is not a date I can read for %s.\n  Use %s."
                 % (value, field, D.FORMS))


def log_schedule(data, item_id, field, before, after, reason):
    rows = data.setdefault(SCHEDULE_LOG, [])
    rows.append({"ID": (max([r.get("ID", 0) for r in rows]) + 1) if rows else 1,
                 "Changed On": date.today().isoformat(),
                 "Item": as_id(item_id), "Field": field,
                 "From": before or "", "To": after or "", "Reason": reason})


def apply_dates(data, row, args, changed, creating=False):
    """Set the schedule fields, with the three rules that make them mean something.

    A baseline is write-once (R9) - one that can be quietly edited is not a
    baseline, it is just another plan. A parent derives its plan and actuals
    from its children (R16), so setting them there would create a second
    answer the render would ignore. And every move of a planned date is
    logged with a reason (R12), because today's variance says a deliverable
    is late while the log says it has moved right three times, and the
    second is the more useful signal.
    """
    for dest, field in DATE_ARGS:
        value = getattr(args, dest, None)
        if value is None:
            continue
        check_date(field, value)
        before = row.get(field)

        if field in C.BASELINE_FIELDS and before and not creating:
            sys.exit("%s is already %r on item %s. A baseline is set once - "
                     "use `wbs.py rebaseline` to move it, which records the "
                     "previous value and why." % (field, before, row.get("ID")))
        if field not in C.BASELINE_FIELDS and not creating \
                and has_children(data, row.get("ID")) and value != "":
            sys.exit("%s is derived on item %s, which has children - it is the "
                     "span of its descendants, computed at render time. Set it "
                     "on the leaves instead. (A baseline may be carried on a "
                     "parent; a plan may not.)" % (field, row.get("ID")))
        if field in C.PLANNED_FIELDS and not creating and str(before or "") != str(value):
            if not getattr(args, "reason", None):
                sys.exit("Moving %s needs --reason. The log of why a date moved "
                         "is the point of keeping one." % field)
            log_schedule(data, row.get("ID"), field, before, value, args.reason)

        if value == "":
            row.pop(field, None)
            changed.append("%s cleared" % field)
        else:
            row[field] = value
            changed.append("%s=%s" % (field, value))


# Status is the trigger for an actual date - they are two halves of one fact,
# and letting them move apart is how Next/Future rotted in Sprint Planned.
# Stamped rather than asked for, because a date nobody is prompted for is a
# date nobody writes; announced rather than silent, because a wrong one has
# to be correctable.
STATUS_STAMPS = (("Implementing", "Actual Start"),
                 ("Done", "Actual End"), ("Cancelled", "Actual End"))


def stamp_actuals(data, row, args, changed):
    if not args.status:
        return
    if has_children(data, row.get("ID")):
        return                       # a parent's actuals are its children's
    for status, field in STATUS_STAMPS:
        if args.status != status or row.get(field):
            continue
        if getattr(args, field.lower().replace(" ", "_"), None):
            continue                 # an explicit value was passed; leave it
        today = date.today()
        row[field] = "%d-%s-%d" % (today.year, D.MONTHS[today.month - 1], today.day)
        changed.append("%s=%s (stamped: Status is now %s; pass --%s to correct)"
                       % (field, row[field], status,
                          field.lower().replace(" ", "-")))


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
    created = []
    apply_dates(data, row, args, created, creating=True)
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
    apply_dates(data, row, args, changed)
    stamp_actuals(data, row, args, changed)
    check_deliverable(row)
    if not changed:
        sys.exit("Nothing to change. Pass at least one field.")
    return finish(args, data, "Item %s: %s" % (args.id, ", ".join(changed)))


def cmd_check(args):
    data = R.load(args.register)
    items = R.rows(data, ITEMS)
    known_sprints = {s.get("Sprint") for s in data.get(SPRINTS) or []}
    sprint_window = {s.get("Sprint"): (s.get("Starts"), s.get("Ends"))
                     for s in data.get(SPRINTS) or []}
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

        # Schedule dates. Two answers to whether something finished is one
        # too many, so the dates and the Status have to agree.
        resolved = {}
        for field in C.DATE_FIELDS:
            value = row.get(field)
            if not value:
                continue
            got = D.resolve(value)
            if got is None:
                errors.append("item %s: %s=%r is not a readable date (%s)"
                              % (rid, field, value, D.FORMS))
            else:
                resolved[field] = got

        status = row.get("Status")
        if row.get("Actual End") and status not in ("Done", "Cancelled"):
            errors.append("item %s: Actual End is set but Status is %r"
                          % (rid, status or "unset"))
        if row.get("Actual Start") and status in ("Not Started", "Portfolio Backlog",
                                                  "Funnel"):
            errors.append("item %s: Actual Start is set but Status is %r"
                          % (rid, status))
        if not has_children(data, rid):
            if status == "Done" and not row.get("Actual End"):
                warnings.append("item %s: Done with no Actual End - the "
                                "roadmap cannot place it" % rid)
            if status == "Implementing" and not row.get("Actual Start"):
                warnings.append("item %s: Implementing with no Actual Start"
                                % rid)
        for start_field, end_field in C.DATE_PAIRS:
            a, b = resolved.get(start_field), resolved.get(end_field)
            if a and b and b["end"] < a["start"]:
                errors.append("item %s: %s (%s) ends before %s (%s) begins"
                              % (rid, end_field, b["text"], start_field, a["text"]))

        # A parent's plan and actuals are the span of its descendants, so a
        # stored value there is a second answer the render ignores.
        if has_children(data, rid):
            stored = [f for f in C.PLANNED_FIELDS + C.ACTUAL_FIELDS if row.get(f)]
            if stored:
                warnings.append("item %s: %s stored on a parent - derived at "
                                "render time, so the stored value is ignored"
                                % (rid, ", ".join(stored)))

        # Usually a stale field rather than a mistake, so a warning (R22).
        planned = resolved.get("Planned End")
        sprint_id = row.get("Sprint Planned")
        if planned and sprint_id and sprint_id in sprint_window:
            window = sprint_window[sprint_id]
            if window[1] and (planned["end"] < window[0] or planned["start"] > window[1]):
                warnings.append("item %s: Sprint Planned %s (%s..%s) and Planned "
                                "End %s do not overlap"
                                % (rid, sprint_id, window[0], window[1], planned["text"]))

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

    # Planned Release and Released On fold into the six-field schedule.
    # Eight overlapping date fields would let a row hold two answers to
    # when it shipped - the duplication the three-axis Type work removed.
    for row in items:
        for old_field, new_field in (("Planned Release", "Planned End"),
                                     ("Released On", "Actual End")):
            if old_field not in row:
                continue
            value = row.pop(old_field)
            if not value:
                continue
            if D.resolve(value) is None:
                notes.append("!! item %s: %s=%r is not a readable date and was "
                             "left in Comments rather than dropped"
                             % (row.get("ID"), old_field, value))
                row["Comments"] = ("%s [%s was %s]" % (row.get("Comments", ""),
                                                       old_field, value)).strip()
            elif row.get(new_field):
                notes.append("!! item %s: %s=%r dropped - %s already holds %r"
                             % (row.get("ID"), old_field, value, new_field,
                                row[new_field]))
            else:
                row[new_field] = value
                notes.append("item %s: %s -> %s (%s)"
                             % (row.get("ID"), old_field, new_field, value))

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
    for name, spec in ((SPRINTS, C.SPRINT_FIELDS),
                       (SCHEDULE_LOG, C.SCHEDULE_LOG_FIELDS)):
        if name not in data:
            data[name] = []
            notes.append("%s collection added" % name)
        if settings.setdefault("fields", {}).get(name) != spec:
            settings["fields"][name] = spec
            notes.append("%s field order registered" % name)
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


def cmd_rebaseline(args):
    """Move a baseline deliberately, recording what it was and why (R10).

    Re-baselining is a real project event, not an edit. Making it its own
    verb is what lets `set` refuse a baseline outright: there is somewhere
    else to go, so the refusal costs nothing and the record survives.
    """
    data = R.load(args.register)
    row = find(data, args.id)
    if row is None:
        sys.exit("No item with ID %s." % args.id)
    wanted = [(f, getattr(args, f.lower().replace(" ", "_")))
              for f in C.BASELINE_FIELDS]
    wanted = [(f, v) for f, v in wanted if v is not None]
    if not wanted:
        sys.exit("Pass at least one of --baseline-start / --baseline-end.")

    changed = []
    for field, value in wanted:
        check_date(field, value)
        before = row.get(field)
        if str(before or "") == str(value):
            continue
        log_schedule(data, row.get("ID"), field, before, value, args.reason)
        if value == "":
            row.pop(field, None)
            changed.append("%s cleared (was %s)" % (field, before))
        else:
            row[field] = value
            changed.append("%s %s -> %s" % (field, before or "unset", value))
    if not changed:
        sys.exit("The baseline already reads that. Nothing recorded.")
    return finish(args, data, "Rebaselined item %s: %s\n  reason: %s"
                  % (args.id, "; ".join(changed), args.reason))


# --------------------------------------------------------------------------- #
# Sprint metrics. The retro asks these, and the register is what can answer
# them: it holds sprint membership, status, effort and the actual dates.
# The task tracker holds the same work as labels, but nothing enforces that the two
# agree, so it verifies rather than computes.

def hours(rows):
    return round(sum(r.get("Estimated Effort (h)") or 0 for r in rows), 2)


def estimated(rows):
    return [r for r in rows if r.get("Estimated Effort (h)")]


def cycle_days(row):
    """Calendar days from starting a row to finishing it, or None.

    Only possible since the actual dates existed; a task tracker has no
    equivalent. Uses each date's own resolved span, so a month-precision
    actual measures from the start of that month, not a guessed day in it.
    """
    began, ended = D.resolve(row.get("Actual Start")), D.resolve(row.get("Actual End"))
    if not began or not ended:
        return None
    return (date.fromisoformat(ended["end"]) - date.fromisoformat(began["start"])).days


def sprint_metrics(data, sprint):
    """The four populations, and what each one is worth.

    Committed and pulled-in are kept apart because the difference is where
    over-commitment shows: a sprint that delivered its plan and absorbed
    more is not the same as one that merely hit its number.
    """
    live = [r for r in R.rows(data, ITEMS) if r.get("Status") != "Cancelled"]
    committed = [r for r in live if r.get("Sprint Planned") == sprint]
    pulled = [r for r in live if r.get("Sprint Added") == sprint
              and r.get("Sprint Planned") != sprint]
    delivered = [r for r in live if r.get("Sprint Ended") == sprint
                 and r.get("Status") == "Done"]
    carried = [r for r in committed if r not in delivered]
    spans = sorted(d for d in (cycle_days(r) for r in delivered) if d is not None)
    median = None
    if spans:
        mid = len(spans) // 2
        median = spans[mid] if len(spans) % 2 else (spans[mid - 1] + spans[mid]) / 2

    return {
        "sprint": sprint,
        "committed": {"n": len(committed), "h": hours(committed),
                      "estimated": len(estimated(committed))},
        "pulled_in": {"n": len(pulled), "h": hours(pulled)},
        "delivered": {"n": len(delivered), "h": hours(delivered),
                      "estimated": len(estimated(delivered))},
        "carryover": {"n": len(carried), "h": hours(carried),
                      "ids": [r.get("ID") for r in carried]},
        "cycle_time": {"median_days": median, "measured": len(spans),
                       "of": len(delivered)},
    }


def pct(part, whole):
    return None if not whole else round(part / whole * 100)


def cmd_metrics(args):
    data = R.load(args.register)
    known = {s.get("Sprint") for s in data.get(SPRINTS) or []}
    if known and args.sprint not in known:
        sys.exit("%r is not a sprint in this register's calendar.\n  known: %s"
                 % (args.sprint, ", ".join(sorted(known)) or "(none imported)"))
    m = sprint_metrics(data, args.sprint)

    if args.json:
        import json
        print(json.dumps(m, indent=2))
        return 0

    c, p, dl, co, ct = (m["committed"], m["pulled_in"], m["delivered"],
                        m["carryover"], m["cycle_time"])
    print("Sprint %s\n" % args.sprint)
    if not (c["n"] or dl["n"] or p["n"]):
        print("  Nothing references this sprint yet - no row names it as planned, "
              "added or ended.")
        return 0
    print("  Velocity        %d item(s) delivered, %gh" % (dl["n"], dl["h"]))
    if c["n"]:
        print("  Completion      %s%% of items (%d of %d), %s%% of hours (%gh of %gh)"
              % (pct(dl["n"], c["n"]), dl["n"], c["n"],
                 pct(dl["h"], c["h"]) if c["h"] else "-", dl["h"], c["h"]))
        print("  Committed/del.  %gh committed, %gh delivered  (%+gh)"
              % (c["h"], dl["h"], round(dl["h"] - c["h"], 2)))
    else:
        # An invented denominator is the same mistake as an invented baseline.
        print("  Completion      no denominator - nothing carries Sprint Planned "
              "= %s, so what\n                  was committed is unrecorded. The "
              "next planning session fixes it." % args.sprint)
    # Only meaningful against a commitment. With Sprint Planned empty the
    # whole sprint looks pulled in, which says nothing about the sprint and
    # everything about the missing field - and it double-counts the
    # delivered rows, which were also added.
    if p["n"] and c["n"]:
        print("  Pulled in       %d item(s) added after planning, %gh - scope beyond "
              "the commitment" % (p["n"], p["h"]))
    elif p["n"]:
        print("  Pulled in       not distinguishable - with nothing committed, all %d "
              "item(s) added" % p["n"])
        print("                  to this sprint look unplanned, including the "
              "delivered ones")
    if co["n"]:
        print("  Carryover       %d item(s), %gh  (IDs %s)"
              % (co["n"], co["h"], ", ".join(str(i) for i in co["ids"])))
    elif c["n"]:
        print("  Carryover       none")
    if ct["measured"]:
        print("  Cycle time      %g days median, over %d of %d delivered item(s)"
              % (ct["median_days"], ct["measured"], ct["of"]))
    elif dl["n"]:
        print("  Cycle time      not measurable - no delivered item carries both "
              "an Actual Start and End")

    # A rate over rows that mostly lack an estimate is a different claim from
    # one where they all have it, and the retro should know which it has.
    gaps = []
    if c["n"] and c["estimated"] < c["n"]:
        gaps.append("%d of %d committed" % (c["n"] - c["estimated"], c["n"]))
    if dl["n"] and dl["estimated"] < dl["n"]:
        gaps.append("%d of %d delivered" % (dl["n"] - dl["estimated"], dl["n"]))
    if gaps:
        print("\n  Coverage        no effort estimate on %s - the hour figures "
              "cover only the rest." % "; ".join(gaps))
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
        for dest, field in DATE_ARGS:
            sub.add_argument("--" + dest.replace("_", "-"), dest=dest,
                             metavar="DATE", help="%s (%s)" % (field, D.FORMS))
        sub.add_argument("--reason", help="why a planned date moved; required "
                                          "when one does")
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

    s = subs.add_parser("rebaseline", help="move a baseline, recording why")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("--reason", required=True,
                   help="why the commitment moved; this is the record")
    for _dest, _field in [(d, f) for d, f in DATE_ARGS if f in C.BASELINE_FIELDS]:
        s.add_argument("--" + _dest.replace("_", "-"), dest=_dest, metavar="DATE")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_rebaseline)

    s = subs.add_parser("metrics", help="what one sprint delivered against what it took on")
    s.add_argument("register")
    s.add_argument("--sprint", required=True, metavar="ID", help='e.g. "S26.Q3.5"')
    s.add_argument("--json", action="store_true",
                   help="emit the same figures as a structure, for a caller to consume")
    s.set_defaults(func=cmd_metrics)

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
