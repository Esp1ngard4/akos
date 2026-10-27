#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured edits to a WBS register.

    python wbs.py add     <register> "Title" --type Story --parent 37
    python wbs.py set     <register> --id 42 --status Done --nature Improve
    python wbs.py note    <register> --id 42 "what changed and why"
    python wbs.py check   <register>
    python wbs.py rebaseline <register> --id 42 --baseline-end Q2-26 --reason "..."
    python wbs.py metrics <register>... --sprint S26.Q3.5
    python wbs.py pullins [--root <folder>] [--sprint S26.Q3.5] [--records <folder>]
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
import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import dates as D                                               # noqa: E402
import create_wbs as C                                          # noqa: E402

ITEMS = "items"
SPRINTS = "sprints"
SCHEDULE_LOG = "schedule_log"
# Below this many characters a Description cannot state a problem; `refined`
# reports it as thin rather than as present.
THIN_DESCRIPTION = 20
# --flag -> field. The six schedule dates; see dates.py for what a value
# may look like and why precision is derived rather than stored.
DATE_ARGS = [(f.lower().replace(" ", "_"), f) for f in C.DATE_FIELDS]
# Assigning a real sprint, or closing the row, both supersede an intention
# about how soon. Without this the field rots exactly as Next/Future did in
# Sprint Planned - 18 of 45 rows stale and nothing to catch it.
HORIZON_CLEARS_ON = ("Done", "Cancelled")
SPRINT_FIELDS_ON_ITEM = ("Sprint Planned", "Sprint Added", "Sprint Ended")
# --flag -> field, the same shape as DATE_ARGS. The fields were in the schema
# and in every register's field order from the start, but nothing could write
# them, so they stood at 0 of 97 rows while `check` validated them, `metrics`
# read them and the dashboard rendered them.
SPRINT_ARGS = [(f.lower().replace(" ", "_"), f) for f in SPRINT_FIELDS_ON_ITEM]
# The sprints a row was committed to again, after Sprint Planned: spillover,
# or the next slice of a deliverable worked across sprints. A list, and the
# only one in the model, because a row can be recommitted more than once and
# each later sprint has to see it. Re-pointing Sprint Planned instead would
# rewrite the earlier sprint's carryover; Sprint Added would report planned
# work as pulled in.
CARRIED = "Sprint Carried"


def carried(row):
    value = row.get(CARRIED) or []
    return [value] if isinstance(value, str) else list(value)


def sprint_ids(row):
    """Every sprint a row names, across the scalar fields and the list."""
    return [row.get(f) for f in SPRINT_FIELDS_ON_ITEM if row.get(f)] + carried(row)


def committed_to(row, sprint):
    """Planned into it at the start, or committed to it again later."""
    return row.get("Sprint Planned") == sprint or sprint in carried(row)
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


CLOSED = ("Done", "Cancelled")


def has_children(data, item_id):
    return any(str(r.get("Parent")) == str(item_id) for r in R.rows(data, ITEMS))


def subtree_ids(rows, item_id):
    """IDs (as strings) of every row below `item_id`, Cancelled included."""
    kids = {}
    for r in rows:
        kids.setdefault(str(r.get("Parent")), []).append(str(r.get("ID")))
    out, stack = set(), list(kids.get(str(item_id), []))
    while stack:
        rid = stack.pop()
        if rid in out:
            continue                    # a cycle is check's to report
        out.add(rid)
        stack.extend(kids.get(rid, []))
    return out


def leaves_under(data, item_id):
    """The live (not Cancelled) leaves at or below a row."""
    rows = [r for r in R.rows(data, ITEMS) if r.get("Status") != "Cancelled"]
    kids = {}
    for r in rows:
        kids.setdefault(str(r.get("Parent")), []).append(r)
    out, stack, seen = [], list(kids.get(str(item_id), [])), set()
    while stack:
        r = stack.pop()
        if str(r.get("ID")) in seen:
            continue                    # a cycle is check's to report, not ours to loop on
        seen.add(str(r.get("ID")))
        below = kids.get(str(r.get("ID")))
        if below:
            stack.extend(below)
        else:
            out.append(r)
    return out


def estimate_gap(data, row):
    """The 100% rule: a parent's own estimate against its leaves' sum.

    (own, leaves' sum, unestimated leaves) when they disagree, else None. A
    parent's estimate is the top-down figure made before it was broken down,
    so it is compared with the breakdown, never added to it.
    """
    own = row.get("Estimated Effort (h)")
    if not own or not has_children(data, row.get("ID")):
        return None
    leaves = leaves_under(data, row.get("ID"))
    total = round(sum(l.get("Estimated Effort (h)") or 0 for l in leaves), 2)
    unestimated = sum(1 for l in leaves if not l.get("Estimated Effort (h)"))
    return None if total == own and not unestimated else (own, total, unestimated)


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
        # A first plan is not a move: nothing was promised before it, so
        # there is no "why it moved" to log. Asking anyway taught callers to
        # type filler, and refused the whole edit - a planning commit lost
        # its Sprint Planned and baseline with it.
        if field in C.PLANNED_FIELDS and not creating and before not in (None, "")                 and str(before) != str(value):
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


def clear_horizon_on_close(row, args, changed):
    """Closing a row settles how soon it was wanted, so the intention goes.

    `check` has always errored on a closed row that still carries a Horizon,
    and HORIZON_CLEARS_ON has always named the statuses - but nothing acted on
    it, so every close of a row with a Horizon produced an error to be fixed by
    hand afterwards. Three of those in two days is the argument for doing it
    here, beside the actual-date stamp it belongs with.
    """
    if getattr(args, "status", None) not in HORIZON_CLEARS_ON:
        return
    if row.pop("Horizon", None):
        changed.append("Horizon cleared (a %s row supersedes it)" % args.status)


# A closure note is how a closed row says what happened and whether its AC
# held. A task tracker's closure comment disappears from view once the task is
# completed; the row is what gets read afterwards. Without a rule, almost no
# row gets one: in the register this came from, 1 of 33 closed rows had one.
CLOSURE_MARK = re.compile(r"(^|\n)Closure \d{4}-[A-Z][a-z]{2}-\d{1,2} \(")
# A register that adopts the rule part-way can exempt its history: set
# meta.settings.closure_notes_from to an ISO date, and `check` holds only rows
# closed on or after it. Backfilling older rows is then a choice, made by the
# outcome each delivered, not a sweep.


def apply_closure(row, args, changed, was):
    """Closing a row takes a note, the way moving a date takes a reason.

    Only on the transition: correcting a date on a row that is already Done
    does not ask for a second note. Stamped with the date and the status so
    a later close (a reopened row closing again) reads as its own entry.
    """
    note = getattr(args, "closure", None)
    closing = getattr(args, "status", None) in HORIZON_CLEARS_ON \
        and was not in HORIZON_CLEARS_ON
    if note is not None and not note.strip():
        sys.exit("--closure is empty. Say what happened and where each "
                 "acceptance criterion stands.")
    if closing and not note:
        ask = ("what happened, where each acceptance criterion stands (with "
               "the reason for any gap) and any follow-up"
               if args.status == "Done" else
               "why it was dropped and where anything it held went")
        sys.exit("Closing item %s as %s needs --closure. Say %s - the row is "
                 "what gets read afterwards." % (row.get("ID"), args.status, ask))
    if note and not closing:
        sys.exit("--closure goes with moving a row to Done or Cancelled. To "
                 "add to a row that is already closed, use `wbs.py note`.")
    if not note:
        return
    entry = "Closure %s (%s): %s" % (today_text(), args.status, one_paragraph(note))
    # Newest first, the order DF version histories keep: a closed row is read
    # for how it ended, so that is what it opens with.
    row["Comments"] = ("%s\n\n%s" % (entry, row.get("Comments") or "")).strip()
    changed.append("closure note added at the top of Comments")


def today_text():
    today = date.today()
    return "%d-%s-%d" % (today.year, D.MONTHS[today.month - 1], today.day)


def one_paragraph(text):
    """An entry is one paragraph, so the blank line can separate entries."""
    return re.sub(r"\n\s*\n+", "\n", text.strip())


def add_note(row, text):
    """Newest entry on top - below any closure note, which stays pinned.

    Comments is a log of dated paragraphs. A closed row is read first for
    how it ended, so a note added after the close goes under the closure
    rather than displacing it; everything older sits beneath.
    """
    paras = [p for p in (row.get("Comments") or "").split("\n\n") if p.strip()]
    pinned = 0
    while pinned < len(paras) and CLOSURE_MARK.match(paras[pinned]):
        pinned += 1
    paras.insert(pinned, "%s: %s" % (today_text(), one_paragraph(text)))
    row["Comments"] = "\n\n".join(paras)
    return pinned


def sprint_calendar(data):
    """Sprint ID -> (starts, ends), from the register's imported calendar."""
    return {s.get("Sprint"): (s.get("Starts"), s.get("Ends"))
            for s in data.get(SPRINTS) or [] if s.get("Sprint")}


def sprint_on(data, stamp):
    """The sprint whose window contains an ISO date, or None.

    A date falls in at most one sprint: the calendar is a partition, seeded
    from a single anchor and length. Outside every window this returns None
    rather than the nearest sprint - a row closed outside the cadence is a
    fact worth seeing, not one worth rounding away.
    """
    for sid, (starts, ends) in sprint_calendar(data).items():
        if starts and ends and starts <= stamp <= ends:
            return sid
    return None


def apply_sprints(data, row, args, changed):
    """Write the sprint fields, refusing an ID the calendar never had.

    Refused here rather than left for `check`, because a mistyped sprint ID
    silently drops the row out of the metrics that sprint is measured by -
    the failure is invisible at exactly the moment it counts.
    """
    known = sprint_calendar(data)
    for dest, field in SPRINT_ARGS:
        value = getattr(args, dest, None)
        if value is None:
            continue
        if value == "":                      # explicit clear
            row.pop(field, None)
            changed.append("%s cleared" % field)
            continue
        if known and value not in known:
            sys.exit("%r is not a sprint in this register's calendar.\n"
                     "  known: %s" % (value, ", ".join(sorted(known))))
        if not known:
            sys.exit("This register has no sprint calendar to check %r "
                     "against.\n  run: wbs.py sprints import" % value)
        row[field] = value
        changed.append("%s=%s" % (field, value))
        # A commitment supersedes an intention, and `check` errors when both
        # stand. Clearing it here is what stops the two drifting apart - the
        # drift that left Next/Future stale in Sprint Planned on 18 of 45 rows.
        if field == "Sprint Planned" and row.pop("Horizon", None):
            changed.append("Horizon cleared (a sprint supersedes it)")

    # Carried adds to a list rather than replacing, since each recommitment is
    # its own fact. '' clears the list - the way to undo a mistaken entry.
    value = getattr(args, "sprint_carried", None)
    if value is None:
        return
    if value == "":
        if row.pop(CARRIED, None) is not None:
            changed.append("%s cleared" % CARRIED)
        return
    if not known:
        sys.exit("This register has no sprint calendar to check %r "
                 "against.\n  run: wbs.py sprints import" % value)
    if value not in known:
        sys.exit("%r is not a sprint in this register's calendar.\n"
                 "  known: %s" % (value, ", ".join(sorted(known))))
    if value == row.get("Sprint Planned"):
        sys.exit("%s is this row's Sprint Planned - carried means committed "
                 "again in a later sprint." % value)
    now = carried(row)
    if value in now:
        return
    # Why it did not finish is the part nobody can reconstruct later, and the
    # row is what gets read once the sprint's record is closed - the same
    # bargain as a moved date's --reason and a closure's --closure.
    reason = (getattr(args, "reason", None) or "").strip()
    if not reason:
        sys.exit("Carrying a row into %s needs --reason: why it did not finish "
                 "where it was committed." % value)
    row[CARRIED] = now + [value]
    add_note(row, "Carried into %s: %s" % (value, reason))
    changed.append("%s += %s (reason noted in Comments)" % (CARRIED, value))


# Statuses that mean "not committed yet". Committing a row to a sprint ends
# that, so the row moves to Not Started. Without it, planning sets the sprint
# and nothing moves the Status, and a sprint's committed rows go on reading
# Portfolio Backlog.
UNCOMMITTED = ("Portfolio Backlog", "Funnel")


def commit_status(row, args, changed):
    """A commitment means Not Started - unless a Status was passed with it.

    Only Sprint Planned and Sprint Carried commit; Sprint Added records work
    pulled in, which normally starts at once and is given its Status then.
    """
    if getattr(args, "status", None):
        return                       # an explicit value was passed; leave it
    if not (getattr(args, "sprint_planned", None)
            or getattr(args, "sprint_carried", None)):
        return
    if row.get("Status") not in UNCOMMITTED:
        return
    changed.append("Status=Not Started (was %s: committing to a sprint means "
                   "Not Started; pass --status to correct)" % row["Status"])
    row["Status"] = "Not Started"


def stamp_sprint_ended(data, row, args, changed):
    """Done closes a row into whatever sprint the calendar was on that day.

    The same bargain as the actual dates: derived from a fact already being
    recorded, so the close-out opens with numbers nobody had to remember to
    write down. Only Done - a cancelled row delivered nothing, and delivery
    is what `metrics` counts.
    """
    if getattr(args, "status", None) != "Done" or row.get("Sprint Ended"):
        return
    if getattr(args, "sprint_ended", None):
        return                       # an explicit value was passed; leave it
    if has_children(data, row.get("ID")):
        return                       # a parent's membership is its children's
    ended = D.resolve(row.get("Actual End"))
    if not ended:
        return
    sid = sprint_on(data, ended["start"])
    if not sid:
        return
    row["Sprint Ended"] = sid
    changed.append("Sprint Ended=%s (stamped from Actual End %s; pass "
                   "--sprint-ended to correct)" % (sid, ended["text"]))


# --------------------------------------------------------------------------- #
# Confirming a pull-in. Starting or closing work the sprint never committed to
# is either a pull-in, whose effect on committed work is stated there and then
# (the sprint ceremonies' rule), or work outside the sprint. The tool asks; it
# never decides, and it never marks anything by itself.

STARTS_WORK = ("Implementing", "Done")


def current_sprint(data):
    return sprint_on(data, date.today().isoformat())


def committed_now(data, row, sprint):
    """Committed to the sprint itself, pulled into it already, or under a row
    that is: work on a committed parent's children is the parent's work. Never
    by a committed child: a parent is a commitment of its own, whose AC can stay
    unmet when every child is done, so it counts only when it was itself
    planned, carried or pulled into the sprint."""
    seen, cur = set(), row
    while cur is not None and str(cur.get("ID")) not in seen:
        if committed_to(cur, sprint) or cur.get("Sprint Added") == sprint:
            return True
        seen.add(str(cur.get("ID")))
        cur = find(data, cur.get("Parent")) if cur.get("Parent") is not None else None
    return False


def scope_code(data):
    """How a sprint record names this register: its meta.scope."""
    return (data.get("meta", {}).get("scope") or "").strip()


def row_ref(data, row_id):
    return "%s %s" % (scope_code(data), row_id)


def record_line(register_path, data, row, effect):
    """The row's line for the sprint record's Committed items, in its shape.
    `Area` is left for the user: the register does not know which area a
    project serves."""
    hours = row.get("Estimated Effort (h)")
    return "| %s %s | %s |  |  | **pulled in %s**; effect: %s |" % (
        row_ref(data, row["ID"]), row.get("Title", ""),
        ("%gh" % hours) if hours is not None else "",
        "%d-%s" % (date.today().day, D.MONTHS[date.today().month - 1]), effect)


def pull_in_gate(data, row, args, changed, was):
    """Refuse to start or close an uncommitted row without an answer. Returns
    the record line for a pull-in, else None."""
    pulled, outside = getattr(args, "pulled_in", None), getattr(args, "outside_sprint", None)
    status = row.get("Status")
    sprint = current_sprint(data)
    if status not in STARTS_WORK or status == was or not sprint:
        if pulled or outside:
            sys.exit("--pulled-in and --outside-sprint answer a move to Implementing "
                     "or Done in the running sprint; this edit is not one.")
        return None
    if committed_now(data, row, sprint):
        if pulled or outside:
            sys.exit("Item %s is committed to %s already: no answer is needed."
                     % (row["ID"], sprint))
        return None
    if pulled and outside:
        sys.exit("One answer: --pulled-in or --outside-sprint, not both.")
    when = "%d-%s" % (date.today().day, D.MONTHS[date.today().month - 1])
    if pulled:
        row["Sprint Added"] = sprint
        add_note(row, "Pulled into %s on %s; effect: %s." % (sprint, when, pulled.strip().rstrip(".")))
        changed.append("Sprint Added=%s (pulled in; effect: %s)" % (sprint, pulled))
        return record_line(args.register, data, row, pulled.strip().rstrip("."))
    if outside:
        add_note(row, "Worked outside the sprint (%s), %s: %s." % (sprint, when, outside.strip().rstrip(".")))
        changed.append("noted as worked outside %s" % sprint)
        return None
    sys.exit("Item %s is not committed to %s, the sprint running today, so this "
             "is a pull-in or work outside the sprint. Answer one:\n"
             "  --pulled-in \"displaces nothing\"   (or \"delays <the committed item>\")\n"
             "  --outside-sprint \"<why: a correction of past work, or work kept out of the sprint>\""
             % (row["ID"], sprint))


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
    apply_closure(row, args, created, None)
    apply_dates(data, row, args, created, creating=True)
    apply_sprints(data, row, args, created)
    commit_status(row, args, created)
    # A row added straight into Implementing or Done takes the same stamps a
    # status change does - adding is just the first write of that status.
    clear_horizon_on_close(row, args, created)
    stamp_actuals(data, row, args, created)
    stamp_sprint_ended(data, row, args, created)
    R.rows(data, ITEMS).append(row)
    line = pull_in_gate(data, row, args, created, None)
    # The 100% rule: work added under a parent that carries its own estimate
    # must fit inside it, or that estimate becomes the original one.
    parent = find(data, args.parent) if args.parent else None
    if parent is not None and parent.get("Estimated Effort (h)"):
        created.append("note: parent %s carries its own estimate (%gh). Its children "
                       "are its estimate now; `check` compares the two"
                       % (parent.get("ID"), parent["Estimated Effort (h)"]))
    # Stamped values are announced, as `set` announces them, so a wrong one
    # can be corrected.
    code = finish(args, data, "Added item %s  %s%s" % (
        row["ID"], args.title, "\n  " + "\n  ".join(created) if created else ""))
    if line:
        print("\n  Add to the sprint record's Committed items, today:\n  " + line)
    return code


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
    was = row.get("Status")
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
    apply_sprints(data, row, args, changed)
    commit_status(row, args, changed)
    apply_closure(row, args, changed, was)
    clear_horizon_on_close(row, args, changed)
    stamp_actuals(data, row, args, changed)
    stamp_sprint_ended(data, row, args, changed)
    line = pull_in_gate(data, row, args, changed, was)
    check_deliverable(row)
    if not changed:
        sys.exit("Nothing to change. Pass at least one field.")
    code = finish(args, data, "Item %s: %s" % (args.id, ", ".join(changed)))
    if line:
        print("\n  Add to the sprint record's Committed items, today:\n  " + line)
    return code


def cmd_note(args):
    data = R.load(args.register)
    row = find(data, args.id)
    if row is None:
        sys.exit("No item with ID %s." % args.id)
    if not args.text.strip():
        sys.exit("The note is empty.")
    pinned = add_note(row, args.text)
    return finish(args, data, "Item %s: note added %s" % (
        args.id, "below the closure note" if pinned else "at the top of Comments"))


# --------------------------------------------------------------------------- #
# Splitting partly done work. Carrying a partly done row whole credits
# the hours done in one sprint to the sprint where it closes. A split closes
# what was delivered in its sprint and keeps the rest open, and every piece
# keeps the commitment history, so each sprint still shows what it committed
# and delivered hours count once.

SPLIT_MARK = re.compile(r"\bSplit from ID (\d+)\b")
SPLIT_COPY = ("Class", "Nature", "Delivers", "Priority", "Owner", "Category",
              "Sprint Planned", "Sprint Added", CARRIED)


def split_piece_of(row):
    """The ID a row was split from, when `split` made it a piece of its parent."""
    hit = SPLIT_MARK.search(row.get("Comments") or "")
    return hit.group(1) if hit and hit.group(1) == str(row.get("Parent")) else None


def cmd_split(args):
    """Close what was delivered in a sprint and keep the rest open.

    The first split turns the row into the parent of the two pieces: it keeps
    its ID, its sprint commitment, its baseline and its own estimate, which
    the Breakdown then shows as the original. Splitting a piece again closes
    that piece with what was delivered and adds the rest beside it, under the
    same parent: a split cuts by sprint, not by meaning, so it adds no layer.
    """
    data = R.load(args.register)
    row = find(data, args.id)
    if row is None:
        sys.exit("No item with ID %s." % args.id)
    rid = str(row.get("ID"))
    if has_children(data, rid):
        sys.exit("Item %s has children: its effort is theirs. Close or carry "
                 "them instead of splitting it." % rid)
    if row.get("Status") in CLOSED:
        sys.exit("Item %s is %s: there is nothing left to split."
                 % (rid, row.get("Status")))
    sprint = args.sprint or next(
        (s for s in reversed([row.get("Sprint Planned")] + carried(row)
                             + [row.get("Sprint Added")]) if s), None)
    if not sprint:
        sys.exit("Item %s names no sprint. Pass --sprint: the sprint the "
                 "delivered part closes in." % rid)
    known = sprint_calendar(data)
    if known and sprint not in known:
        sys.exit("%r is not a sprint in this register's calendar." % sprint)
    if sprint not in sprint_ids(row):
        sys.exit("Item %s was never in %s. A split closes the part delivered "
                 "in a sprint the row was in." % (rid, sprint))
    if args.delivered <= 0:
        sys.exit("--delivered is the hours done; with none, carry the row whole.")
    whole = lambda h: int(h) if h is not None and float(h).is_integer() else h
    args.delivered = whole(args.delivered)
    own = row.get("Estimated Effort (h)")
    rest = whole(args.rest_effort if args.rest_effort is not None else (
        round(own - args.delivered, 2) if own else None))
    if rest is None:
        sys.exit("Item %s has no estimate, so the rest cannot be derived. "
                 "Pass --rest-effort." % rid)
    if rest <= 0:
        sys.exit("Nothing is left (%gh estimated, %gh delivered): close the "
                 "row instead, or pass --rest-effort for what remains."
                 % (own or 0, args.delivered))

    piece_of = split_piece_of(row)
    parent = find(data, piece_of) if piece_of else row
    level = row.get("Type") if row.get("Type") in ("Story", "Task") else "Story"
    title = parent.get("Title", "")      # pieces are named from what they split
    changed, made = [], []
    when = today_text()

    def piece(title_text, effort):
        new = {"ID": R.next_id(data, ITEMS) or 1, "Parent": parent["ID"],
               "Title": title_text, "Type": level, "Estimated Effort (h)": effort}
        for field in SPLIT_COPY:
            if row.get(field):
                new[field] = list(row[field]) if field == CARRIED else row[field]
        if row.get("Acceptance Criteria"):
            new["Acceptance Criteria"] = row["Acceptance Criteria"]
        R.rows(data, ITEMS).append(new)
        kids = [r for r in R.rows(data, ITEMS) if str(r.get("Parent")) == str(parent["ID"])]
        if parent.get("Code"):
            new["Code"] = "%s.%d" % (parent["Code"], len(kids))
        return new

    if piece_of:
        # A piece split again: it closes as the delivered part, and the rest
        # goes beside it, under the same parent.
        done = row
        done["Estimated Effort (h)"] = args.delivered
        done["Title"] = args.done_title or "%s - done in %s" % (title, sprint)
        changed.append("item %s: Estimated Effort %gh -> %gh delivered, retitled"
                       % (rid, own or 0, args.delivered))
    else:
        done = piece(args.done_title or "%s - done in %s" % (title, sprint),
                     args.delivered)
        made.append(done)
        # A parent's plan and actuals are its children's span: they move.
        if row.get("Actual Start"):
            done["Actual Start"] = row.pop("Actual Start")
    remainder = piece(args.rest_title or "%s - rest after %s" % (title, sprint), rest)
    made.append(remainder)
    for field in ("Planned Start", "Planned End"):
        if row.get(field):
            remainder[field] = row.pop(field)
    if row.get("Tracked Externally"):
        remainder["Tracked Externally"] = row.pop("Tracked Externally")
    if row.get("Description"):
        remainder["Description"] = row["Description"]
    remainder["Status"] = "Not Started"

    # The delivered part keeps only the commitments up to the sprint it closes
    # in: a later carry on it would count finished work as that sprint's
    # carryover. The rest keeps the full history.
    order = sorted(known, key=lambda k: known[k][0] or "") if known else []
    pos = lambda sp: order.index(sp) if sp in order else sp
    after = lambda sp: sp and (pos(sp) > pos(sprint) if (sp in order and sprint in order) else sp > sprint)
    kept = [c for c in carried(done) if not after(c)]
    if carried(done) != kept:
        changed.append("item %s: Sprint Carried %s -> %s (only up to %s)"
                       % (done["ID"], ", ".join(carried(done)), ", ".join(kept) or "none", sprint))
        if kept:
            done[CARRIED] = kept
        else:
            done.pop(CARRIED, None)
    if after(done.get("Sprint Added")):
        done.pop("Sprint Added")

    # Close the delivered part in the sprint being closed, not in whichever
    # sprint the close-out happens to run in.
    ns = argparse.Namespace(status="Done", closure=args.closure,
                            actual_end=args.actual_end, actual_start=None)
    was = done.get("Status")
    done["Status"] = "Done"
    apply_closure(done, ns, changed, was)
    if args.actual_end:
        check_date("Actual End", args.actual_end)
        done["Actual End"] = args.actual_end
    stamp_actuals(data, done, ns, changed)
    done["Sprint Ended"] = sprint
    done.pop("Horizon", None)

    for new in made:
        add_note(new, "Split from ID %s at the %s close-out: %s." % (
            parent["ID"], sprint, "the part delivered there" if new is done
            else "what was left, %gh" % rest))
    if piece_of:
        add_note(done, "Split again at the %s close-out: %gh delivered here, "
                       "%gh left in ID %s." % (sprint, args.delivered, rest,
                                               remainder["ID"]))
    add_note(parent, "Split at the %s close-out: %s%gh delivered in ID %s, %gh "
                     "left in ID %s." % (
                         sprint, "" if piece_of else "%gh estimated; " % (own or 0),
                         args.delivered, done["ID"], rest, remainder["ID"]))

    lines = ["Split item %s in %s" % (rid, sprint)]
    if not piece_of:
        lines.append("item %s is now the parent: its %gh is the original "
                     "estimate, its sprint commitment and baseline stay"
                     % (rid, own or 0))
    lines.append("item %s: %s, Done in %s, %gh" % (done["ID"], done["Title"],
                                                   sprint, args.delivered))
    lines.append("item %s: %s, Not Started, %gh, committed as %s"
                 % (remainder["ID"], remainder["Title"], rest,
                    ", ".join(sprint_ids(remainder)) or "-"))
    lines += changed
    lines.append("Task tracker: the open task for ID %s now serves ID %s, with %gh "
                 "left; planning carries ID %s on with --sprint-carried"
                 % (rid, remainder["ID"], rest, remainder["ID"]))
    return finish(args, data, "\n  ".join(lines))


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

        # Open parents only: on a closed one the difference is history, which
        # the dashboard shows; a warning there would have nothing left to decide.
        gap = estimate_gap(data, row) if row.get("Status") not in HORIZON_CLEARS_ON else None
        if gap:
            own, total, unest = gap
            why = ("scope grew past the estimate" if total > own else
                   "the breakdown is incomplete" + (" (%d leaf/leaves unestimated)" % unest if unest else ""))
            warnings.append("item %s: its own estimate is %gh, its children sum to %gh - %s. "
                            "The children are the estimate now; the parent's is the original"
                            % (rid, own, total, why))

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
        raw = row.get(CARRIED)
        if raw is not None and not isinstance(raw, list):
            errors.append("item %s: %s must be a list of sprint IDs, not %r"
                          % (rid, CARRIED, raw))
        for value in carried(row):
            if known_sprints and value not in known_sprints:
                errors.append("item %s: %s holds %r, not a sprint in the calendar"
                              % (rid, CARRIED, value))
            if value == row.get("Sprint Planned"):
                errors.append("item %s: %s repeats Sprint Planned %s"
                              % (rid, CARRIED, value))

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
        if status in UNCOMMITTED and (row.get("Sprint Planned") or carried(row)):
            warnings.append("item %s: committed to %s but Status is %r - a "
                            "commitment means Not Started"
                            % (rid, (carried(row) or [row.get("Sprint Planned")])[-1],
                               status))
        # A committed parent counts as an item and takes its hours
        # from its children in the sprint, so with none of them there the
        # work that finishes it is not named - a refinement gap.
        latest = (carried(row) or [row.get("Sprint Planned")])[-1]
        if latest and status not in CLOSED and has_children(data, rid):
            below = [r for r in items if str(r.get("ID")) in subtree_ids(items, rid)
                     and r.get("Status") != "Cancelled"]
            if not any(committed_to(r, latest) or latest in (r.get("Sprint Added"),
                                                             r.get("Sprint Ended"))
                       for r in below):
                warnings.append("item %s: committed to %s with none of its children "
                                "in it - commit the remaining work under it"
                                % (rid, latest))
        # Work that keeps sliding is a planning problem. A split's
        # rest inherits the commitment history, so this catches it too.
        if status not in CLOSED and len(carried(row)) >= 2:
            warnings.append("item %s: carried into %d sprints (%s) - re-scope it, "
                            "break it down, or drop it out loud"
                            % (rid, len(carried(row)), ", ".join(carried(row))))
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

    if not known_sprints and any(sprint_ids(row) for row in items):
        warnings.append("sprint IDs are in use but the register has no "
                        "calendar - run: wbs.py sprints import")

    # And the inverse, which is the quieter failure: a calendar sits imported
    # and nothing points at it, so `metrics` answers every sprint with
    # "nothing references this sprint yet" and reads as a tooling fault
    # rather than an empty field.
    if known_sprints and not any(sprint_ids(row) for row in items):
        warnings.append("the register has a sprint calendar (%d sprints) but "
                        "no row references any of them - sprint metrics stay "
                        "empty until planning stamps Sprint Planned"
                        % len(known_sprints))

    # `set` refuses a close without a note, so one of these means the row was
    # closed by hand-edit - or before the register adopted the rule.
    rule_from = ((data.get("meta") or {}).get("settings") or {}).get("closure_notes_from")
    def closed_since_rule(r):
        ended = D.resolve(r.get("Actual End"))
        return bool(ended) and (not rule_from or ended["start"] >= rule_from)
    unnoted = [str(r.get("ID")) for r in items
               if r.get("Status") in HORIZON_CLEARS_ON and closed_since_rule(r)
               and not CLOSURE_MARK.search(r.get("Comments") or "")]
    if unnoted:
        warnings.append("%d closed row(s)%s have no closure note: %s"
                        % (len(unnoted), " since %s" % rule_from if rule_from else "",
                           ", ".join(unnoted)))

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

def parent_ids(rows):
    """IDs (as strings) of the rows with a live child among `rows`."""
    return {str(r.get("Parent")) for r in rows
            if r.get("Parent") not in (None, "") and r.get("Status") != "Cancelled"}


def hours(rows, parents=frozenset()):
    """Effort over the leaves among `rows`.

    A parent's own estimate is the top-down figure its children replaced (the
    100% rule), so a committed parent adds no hours: its hours in a sprint are
    its children's there, already counted as leaves. It still counts as an
    item - committing it is the promise that the deliverable lands.
    """
    return round(sum(r.get("Estimated Effort (h)") or 0 for r in rows
                     if str(r.get("ID")) not in parents), 2)


def estimated(rows, parents=frozenset()):
    """The leaves among `rows` that carry an estimate; a parent needs none."""
    return [r for r in rows
            if str(r.get("ID")) not in parents and r.get("Estimated Effort (h)")]


def leaf_count(rows, parents):
    return sum(1 for r in rows if str(r.get("ID")) not in parents)


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


def sprint_populations(rows, sprint):
    """Committed, pulled in and delivered: which rows a sprint holds.

    The one definition of sprint membership. `metrics` counts these and the
    dashboard's Current Sprint board draws them, so the board and the retro
    cannot disagree about what was in the sprint. The caller chooses the rows:
    `metrics` leaves Cancelled out, the board keeps them for its toggle.
    """
    committed = [r for r in rows if committed_to(r, sprint)]
    pulled = [r for r in rows if r.get("Sprint Added") == sprint
              and not committed_to(r, sprint)]
    delivered = [r for r in rows if r.get("Sprint Ended") == sprint
                 and r.get("Status") == "Done"]
    return committed, pulled, delivered


def sprint_board(rows, sprint):
    """The sprint's cards, each with how it is in the sprint and what it is for.

    One card per row the sprint holds (`sprint_populations`), with:
    - `role`: Committed, Carried in, Pulled in, or Closed here (delivered in
      the sprint without having been committed or pulled into it);
    - `lane`: the ID of the nearest Deliverable at or above the row, else its
      root ancestor, else None - a row with no parent has nothing to serve;
    - `path`: the titles between the lane and the row, top first;
    - `hours`: a leaf's own estimate; a parent's is its leaves' among the
      sprint's cards, since its own estimate covers the whole deliverable.
      `parent` says which it is.

    The WBS dashboard's Current Sprint tab draws from this, and so should any
    report that shows the sprint as a board, so a card sits in the same lane,
    with the same hours, wherever it is shown.
    """
    by_id = {r.get("ID"): r for r in rows}
    committed, pulled, delivered = sprint_populations(rows, sprint)
    role = {}
    for r in delivered:
        role[r.get("ID")] = "Closed here"
    for r in pulled:
        role[r.get("ID")] = "Pulled in"
    for r in committed:
        role[r.get("ID")] = "Carried in" if sprint in carried(r) else "Committed"

    kids = {}
    for r in rows:
        if r.get("Status") != "Cancelled" and r.get("Parent") not in (None, ""):
            kids.setdefault(str(r.get("Parent")), []).append(r)

    def card_hours(rid):
        if str(rid) not in kids:
            return by_id[rid].get("Estimated Effort (h)")
        total, stack, seen = 0, list(kids[str(rid)]), set()
        while stack:
            r = stack.pop()
            if str(r.get("ID")) in seen:
                continue
            seen.add(str(r.get("ID")))
            if str(r.get("ID")) in kids:
                stack.extend(kids[str(r.get("ID"))])
            elif r.get("ID") in role:
                total += r.get("Estimated Effort (h)") or 0
        return round(total, 2)

    kids = {}
    for r in rows:
        if r.get("Status") != "Cancelled" and r.get("Parent") not in (None, ""):
            kids.setdefault(str(r.get("Parent")), []).append(r)

    def card_hours(rid):
        if str(rid) not in kids:
            return by_id[rid].get("Estimated Effort (h)")
        total, stack, seen = 0, list(kids[str(rid)]), set()
        while stack:
            r = stack.pop()
            if str(r.get("ID")) in seen:
                continue
            seen.add(str(r.get("ID")))
            if str(r.get("ID")) in kids:
                stack.extend(kids[str(r.get("ID"))])
            elif r.get("ID") in role:
                total += r.get("Estimated Effort (h)") or 0
        return round(total, 2)

    cards = []
    for rid, how in role.items():
        row, chain = by_id[rid], []
        cur, seen = row, {rid}
        while cur.get("Parent") in by_id and cur.get("Parent") not in seen:
            cur = by_id[cur.get("Parent")]
            seen.add(cur.get("ID"))
            chain.append(cur)                # nearest first
        if row.get("Type") == "Deliverable":
            lane, path = rid, []
        else:
            hit = next((n for n, a in enumerate(chain) if a.get("Type") == "Deliverable"), None)
            if hit is None and chain:
                hit = len(chain) - 1         # no Deliverable above: the root
            lane = chain[hit].get("ID") if hit is not None else None
            path = [a.get("Title", "") for a in reversed(chain[:hit])] if hit else []
        cards.append({"id": rid, "role": how, "lane": lane, "path": path,
                      "hours": card_hours(rid), "parent": str(rid) in kids})
    return cards


def sprint_metrics(data, sprint):
    """The four populations, and what each one is worth.

    Committed and pulled-in are kept apart because the difference is where
    over-commitment shows: a sprint that delivered its plan and absorbed
    more is not the same as one that merely hit its number.
    """
    live = [r for r in R.rows(data, ITEMS) if r.get("Status") != "Cancelled"]
    committed, pulled, delivered = sprint_populations(live, sprint)
    carried = [r for r in committed if r not in delivered]
    spans = sorted(d for d in (cycle_days(r) for r in delivered) if d is not None)
    scope = data.get("meta", {}).get("scope", "?")
    # Hours come from leaves only: a parent counts as an item.
    parents = parent_ids(live)

    return {
        "sprint": sprint,
        "scope": scope,
        "committed": {"n": len(committed), "h": hours(committed, parents),
                      "leaves": leaf_count(committed, parents),
                      "estimated": len(estimated(committed, parents))},
        "pulled_in": {"n": len(pulled), "h": hours(pulled, parents)},
        "delivered": {"n": len(delivered), "h": hours(delivered, parents),
                      "leaves": leaf_count(delivered, parents),
                      "estimated": len(estimated(delivered, parents))},
        # IDs are unique within a register, not across them, so a combined
        # report has to say which project each one belongs to.
        "carryover": {"n": len(carried), "h": hours(carried, parents),
                      "ids": ["%s#%s" % (scope, r.get("ID")) for r in carried]},
        "cycle_time": {"median_days": median_of(spans), "measured": len(spans),
                       "of": len(delivered), "days": spans},
    }


def median_of(spans):
    if not spans:
        return None
    ordered = sorted(spans)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def combine(parts):
    """One sprint's figures across several registers.

    A sprint is planned across whatever projects are in play, and capacity is
    the person's, not the project's - so the totals are the meaningful
    numbers and the per-project split is the detail. Cycle time is combined
    from the raw spans: the median of two medians is not a median.
    """
    total = {"sprint": parts[0]["sprint"], "scope": "combined",
             "parts": [p["scope"] for p in parts]}
    for group in ("committed", "pulled_in", "delivered"):
        total[group] = {k: round(sum(p[group].get(k, 0) for p in parts), 2)
                        for k in parts[0][group]}
    total["carryover"] = {
        "n": sum(p["carryover"]["n"] for p in parts),
        "h": round(sum(p["carryover"]["h"] for p in parts), 2),
        "ids": [i for p in parts for i in p["carryover"]["ids"]]}
    days = [d for p in parts for d in p["cycle_time"]["days"]]
    total["cycle_time"] = {"median_days": median_of(days), "measured": len(days),
                           "of": sum(p["cycle_time"]["of"] for p in parts),
                           "days": sorted(days)}
    return total


def pct(part, whole):
    return None if not whole else round(part / whole * 100)


def cmd_metrics(args):
    """One sprint, across however many projects it spanned.

    Planning is often cross-project, and capacity belongs to the person
    rather than to any one register - so the totals are what a close-out
    actually needs, with the per-project split kept visible underneath.
    """
    parts, windows = [], {}
    for path in args.register:
        data = R.load(path)
        known = {s.get("Sprint"): (s.get("Starts"), s.get("Ends"))
                 for s in data.get(SPRINTS) or []}
        scope = data.get("meta", {}).get("scope", path)
        if known and args.sprint not in known:
            sys.exit("%r is not a sprint in %s's calendar.\n  known: %s"
                     % (args.sprint, scope, ", ".join(sorted(known)) or "(none)"))
        if args.sprint in known:
            windows[scope] = known[args.sprint]
        parts.append(sprint_metrics(data, args.sprint))

    # Two registers can hold the same sprint ID over different dates if their
    # calendars were seeded from different anchors. Adding those together
    # would report one sprint that never happened.
    if len(set(windows.values())) > 1:
        sys.exit("%s means different dates in different registers, so they "
                 "cannot be added together:\n%s\n  Reseed from one anchor, or "
                 "report them separately."
                 % (args.sprint, "\n".join("    %-22s %s -> %s" % (k, v[0], v[1])
                                           for k, v in sorted(windows.items()))))

    m = combine(parts) if len(parts) > 1 else parts[0]

    if args.json:
        import json
        print(json.dumps({"total": m, "by_project": parts}
                         if len(parts) > 1 else m, indent=2))
        return 0

    c, p, dl, co, ct = (m["committed"], m["pulled_in"], m["delivered"],
                        m["carryover"], m["cycle_time"])
    if len(parts) > 1:
        print("Sprint %s across %d projects: %s\n"
              % (args.sprint, len(parts), ", ".join(m["parts"])))
    else:
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
    # Parents are counted as items but carry no hours, so coverage is over
    # leaves: a parent is never "unestimated".
    gaps = []
    c_leaves, dl_leaves = c.get("leaves", c["n"]), dl.get("leaves", dl["n"])
    if c_leaves and c["estimated"] < c_leaves:
        gaps.append("%d of %d committed" % (c_leaves - c["estimated"], c_leaves))
    if dl_leaves and dl["estimated"] < dl_leaves:
        gaps.append("%d of %d delivered" % (dl_leaves - dl["estimated"], dl_leaves))
    if c["n"] > c_leaves or dl["n"] > dl_leaves:
        print("\n  Parents         %d committed, %d delivered: counted as items, "
              "with their children's hours"
              % (c["n"] - c_leaves, dl["n"] - dl_leaves))
    if gaps:
        print("\n  Coverage        no effort estimate on %s - the hour figures "
              "cover only the rest." % "; ".join(gaps))

    if len(parts) > 1:
        print("\n  By project")
        for part in parts:
            print("    %-22s %d delivered (%gh)  |  %d committed (%gh)  |  "
                  "%d carried"
                  % (part["scope"], part["delivered"]["n"], part["delivered"]["h"],
                     part["committed"]["n"], part["committed"]["h"],
                     part["carryover"]["n"]))
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


# --------------------------------------------------------------------------- #
# Planning readiness: read-only questions a grooming or planning session asks
# before it commits. Each reports what is absent; none of them decides.

def cmd_deliverables(args):
    """The open Key Deliverables, and which of them planning has to talk about.

    Read-only, across every register given, because deliverables span
    projects the way sprints do. Three questions, each a finding rather than
    a verdict: is the baseline already lost (or lost before --by), is anything
    scheduling the row at all, and - with --sprint - does anything under it
    sit in that sprint or the one being groomed. A deliverable nothing touches
    is a question for planning, not a surprise for the next close-out.
    """
    today = date.today().isoformat()
    by = D.resolve(args.by) if args.by else None
    if args.by and not by:
        sys.exit("--by %r is not a readable date (%s)" % (args.by, D.FORMS))
    horizon_end = by["end"] if by else today

    total = flagged = 0
    for path in args.registers:
        data = R.load(path)
        scope = data.get("meta", {}).get("scope", "?")
        items = R.rows(data, ITEMS)
        kids = {}
        for r in items:
            kids.setdefault(r.get("Parent"), []).append(r)

        def subtree(row):
            out, todo = [], list(kids.get(row.get("ID"), []))
            while todo:
                r = todo.pop()
                out.append(r)
                todo.extend(kids.get(r.get("ID"), []))
            return out

        open_kd = [r for r in items if str(r.get("Key Deliverable") or "").upper() == "Y"
                   and r.get("Status") not in ("Done", "Cancelled")]
        if not open_kd:
            continue
        print("%s - %d open Key Deliverable(s)" % (scope, len(open_kd)))
        for row in open_kd:
            total += 1
            notes = []
            base = D.resolve(row.get("Baseline End"))
            if not base:
                notes.append("no baseline")
            elif base["end"] < today:
                notes.append("baseline %s already passed" % base["text"])
            elif base["end"] < horizon_end:
                notes.append("baseline %s falls before %s" % (base["text"], by["text"]))
            tree = [row] + subtree(row)
            scheduled = any(r.get("Planned End") or r.get("Horizon") or sprint_ids(r)
                            for r in tree)
            if not scheduled:
                notes.append("nothing schedules it - no Planned End, Horizon or sprint "
                             "on it or below it")
            if args.sprint:
                touched = any(committed_to(r, args.sprint) or r.get("Horizon") == "Next"
                              for r in tree)
                if not touched:
                    notes.append("nothing in it is committed to %s or staged Next"
                                 % args.sprint)
            if notes:
                flagged += 1
            print("  %s#%-4s %-44s %s" % (scope, row.get("ID"), str(row.get("Title"))[:44],
                                         "; ".join(notes) if notes else "ok"))
        print("")
    if not total:
        print("No open Key Deliverables in the register(s) given.")
        return 0
    print("%d of %d need a word at planning. Nothing was changed: commit, rebaseline "
          "with a reason, or accept - each is the session's call." % (flagged, total))
    return 0


# --------------------------------------------------------------------------- #
# The project's Execution folder. The standard layout needs no declaration; a
# project whose folders differ declares the difference in meta.execution, so
# the skill stays cross-project and the deviation is written down once, where
# the convention is read.
#   folder        the Execution folder, relative to the register's own folder
#   inputs        the folder for material received from outside
#   deliverables  the folder for what was handed over, as sent

EXECUTION_STANDARD = {"folder": "1. Execution", "inputs": "Inputs",
                      "deliverables": "Deliverables"}


def execution_layout(data, register_path=None):
    """The register's Execution layout: names, resolved path, and deviations.

    `path` is None when no folder is declared - guessing where a project keeps
    its work would be worse than asking. `deviations` lists only the names that
    differ from the standard, which is what the dashboard shows.
    """
    declared = data.get("meta", {}).get("execution") or {}
    layout = dict(EXECUTION_STANDARD)
    for key in EXECUTION_STANDARD:
        if str(declared.get(key) or "").strip():
            layout[key] = str(declared[key]).strip()
    layout["path"] = None
    if declared.get("folder") and register_path:
        base = os.path.dirname(os.path.abspath(register_path))
        layout["path"] = os.path.normpath(os.path.join(base, layout["folder"]))
    shown = dict(layout, folder=os.path.basename(os.path.normpath(layout["folder"])))
    layout["deviations"] = [(key, shown[key]) for key in EXECUTION_STANDARD
                            if shown[key] != EXECUTION_STANDARD[key]]
    return layout


def cmd_refined(args):
    """Is a candidate refined enough to commit to?

    A different question from whether a row and its tasks agree, which is
    reconciliation and belongs to the project's own tracker. This asks whether
    the row itself is ready: it states the problem (Description), what good
    looks like (Acceptance Criteria) and an effort guess, and a candidate
    missing any of them will be refined during planning instead of before it,
    which is what grooming exists to prevent.

    Deliberately not a verdict. A Task may reasonably have no spec and a small
    Story no action plan; what counts as ready is the session's call. This
    reports what is absent.
    """
    data = R.load(args.register)
    rows = {str(r.get("ID")): r for r in R.rows(data, ITEMS)}
    wanted = [i.strip() for i in args.ids.split(",") if i.strip()]

    # Open RAID items bearing on a candidate. The reference lives on the RAID
    # entry and points here - one direction is enough, unlike a task tracker, because
    # both registers are local and a scan costs nothing. Most entries carry no
    # reference and should: a capacity risk is not about a deliverable.
    threats = {}
    if args.raid:
        raid = R.load(args.raid)
        scope = str(data.get("meta", {}).get("scope") or "")
        for entry in R.rows(raid, "entries"):
            ref = str(entry.get("WBS Ref") or "").strip()
            if "#" not in ref:
                continue
            where, _, rid = ref.rpartition("#")
            if where.strip() != scope or str(entry.get("Status")) == "Closed":
                continue
            threats.setdefault(rid, []).append(
                "%s R.%s %s" % (entry.get("Type"), entry.get("RAID.ID"),
                                str(entry.get("Detail"))[:40]))

    specs = {}
    execution = args.execution or execution_layout(data, args.register)["path"]
    if execution and not os.path.isdir(execution):
        sys.exit("No Execution folder at %s - check meta.execution.folder or "
                 "--execution." % execution)
    if execution:
        for base, _dirs, files in os.walk(execution):
            for name in files:
                if not name.lower().endswith(".md"):
                    continue
                path = os.path.join(base, name)
                try:
                    text = open(path, encoding="utf-8", errors="ignore").read(4000)
                except IOError:
                    continue
                for found in re.findall(r"\bID\s*(\d+)", text, re.I):
                    specs.setdefault(found, set()).add(name)

    print("Refinement of %d candidate(s) in %s\n"
          % (len(wanted), data.get("meta", {}).get("scope", "?")))
    missing_any = 0
    for rid in wanted:
        row = rows.get(rid)
        if row is None:
            print("  ID %-4s [%-13s] %-38s | %s"
                  % (rid, "-", "-", "no such row in this register"))
            missing_any += 1
            continue
        gaps = []
        # The ready rule's first half: the problem the row addresses. A
        # description too short to say one has not stated it.
        description = str(row.get("Description") or "").strip()
        if not description:
            gaps.append("no description (no problem stated)")
        elif len(description) < THIN_DESCRIPTION:
            gaps.append("description too thin to state a problem")
        if not str(row.get("Acceptance Criteria") or "").strip():
            gaps.append("no acceptance criteria")
        below = subtree_ids(list(rows.values()), rid)
        if below:
            # A parent takes its hours from its children in the
            # sprint, so it needs no estimate of its own - it needs the work
            # that finishes it among the candidates.
            open_below = {i for i in below if rows[i].get("Status") not in CLOSED}
            if not open_below:
                gaps.append("no open work under it (close it, or add what finishes it)")
            elif not open_below & set(wanted):
                gaps.append("none of its open work is a candidate (name what finishes it)")
        elif not row.get("Estimated Effort (h)"):
            gaps.append("no estimate")
        if row.get("Parent") in (None, ""):
            gaps.append("no parent")
        if not str(row.get("Type") or "").strip():
            gaps.append("no Type")
        if not str(row.get("Action Plan") or "").strip():
            gaps.append("no action plan")
        if execution and rid not in specs:
            gaps.append("no spec naming it")
        for threat in threats.get(rid, []):
            gaps.append("open " + threat)
        state = ", ".join(gaps) if gaps else "ready"
        if gaps:
            missing_any += 1
        print("  ID %-4s [%-13s] %-38s | %s"
              % (rid, str(row.get("Status"))[:13], str(row.get("Title"))[:38], state))

    print("")
    if not missing_any:
        print("  Every candidate carries what planning needs.")
    else:
        print("  %d of %d have a gap. A gap is a flag, not a veto - if an item is\n"
              "  to be prioritised it is to be prioritised, and the close-out records\n"
              "  what it was committed without." % (missing_any, len(wanted)))
    print("  Whether rows and their tasks agree is reconciliation, which depends on\n"
          "  the project's tracker and is deliberately not part of this tool.")
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

    in_use = {sid for row in R.rows(data, ITEMS) for sid in sprint_ids(row)}
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
# The daily check: rows pulled into the sprint that its record does not name
# yet. Every WBS register under a root, found by meta.kind, so one created
# mid-sprint is included.

SKIP_DIRS = ("PreviousV", "Reports", "AuxMat", ".git", "__pycache__", "node_modules")
IDS = re.compile(r"^\s*#?\s*((?:\d+\s*(?:,|and|&|-|–)?\s*)*)(.*)$")
PAREN_IDS = re.compile(r"\(\s*(\d+(?:\s*(?:,|and|&)\s*\d+)*)\s*\)")


def wbs_registers(root):
    found = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            path = os.path.join(here, name)
            try:
                if json.load(open(path, encoding="utf-8")).get("meta", {}).get("kind") == "wbs-register":
                    found.append(path)
            except (IOError, ValueError):
                pass
    return found


def find_record(root, sprint):
    """The sprint's record under root: `<sprint>.md` whose first line starts
    `# Sprint `, as the sprint ceremonies find their records. None if absent."""
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if sprint + ".md" in files:
            path = os.path.join(here, sprint + ".md")
            with open(path, encoding="utf-8") as fh:
                if fh.readline().startswith("# Sprint "):
                    return path
    return None


def record_refs(path, scopes):
    """{(scope, id)} for every row the record's Committed items names. An item
    names a row as `<scope> <ID> <title>`, or `<scope> 3, 4 <title>` for
    several, or with the IDs in brackets after the title."""
    if not path or not os.path.exists(path):
        return None
    scopes = sorted(scopes, key=len, reverse=True)
    out, inside = set(), False
    for line in open(path, encoding="utf-8").read().split("\n"):
        if line.startswith("#"):
            inside = line.strip().lstrip("#").strip().lower() == "committed items"
            continue
        if not inside or not line.startswith("|"):
            continue
        item = line.strip().strip("|").split("|")[0].strip().replace("**", "")
        if item.startswith("~~"):
            continue
        code = next((sc for sc in scopes if sc and item.lower().startswith(sc.lower())), None)
        if code is None:
            continue
        m = IDS.match(item[len(code):])
        ids = m.group(1) or ""
        if not ids.strip():
            paren = PAREN_IDS.search(m.group(2) or "")
            ids = paren.group(1) if paren else ""
        for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", ids):
            lo, hi = int(a), int(b) if b else int(a)
            for n in (range(lo, hi + 1) if 0 <= hi - lo <= 50 else (lo, hi)):
                out.add((code, n))
    return out


def cmd_pullins(args):
    root = os.path.abspath(args.root or os.getcwd())
    regs = [(p, R.load(p)) for p in wbs_registers(root)]
    if not regs:
        print("No WBS register under %s." % root)
        return 0
    sprint = args.sprint or next((current_sprint(d) for _p, d in regs if current_sprint(d)), None)
    if not sprint:
        print("No sprint runs today in any register's calendar: nothing to check.")
        return 0
    record = (os.path.join(args.records, sprint + ".md") if args.records
              else find_record(root, sprint))
    named = record_refs(record, [scope_code(d) for _p, d in regs])
    missing = []
    for path, data in regs:
        code = scope_code(data)
        for row in R.rows(data, ITEMS):
            if row.get("Sprint Added") != sprint or row.get("Status") == "Cancelled":
                continue
            cur, seen, hit = row, set(), False
            while cur is not None and str(cur.get("ID")) not in seen:
                if named and (code, int(cur["ID"])) in named:
                    hit = True
                    break
                seen.add(str(cur.get("ID")))
                cur = find(data, cur.get("Parent")) if cur.get("Parent") is not None else None
            if not hit:
                effect = re.search(r"effect:\s*([^.\n]+)", row.get("Comments") or "")
                missing.append(record_line(path, data, row, effect.group(1).strip() if effect else "?"))
    if named is None:
        print("%s has no sprint record yet: %d pulled-in row(s) to add once it exists." % (sprint, len(missing)))
    if not missing:
        print("No pull-in into %s is missing from its record." % sprint)
        return 0
    print("%d row(s) pulled into %s that the record does not name. Add to Committed items:" % (len(missing), sprint))
    for line in missing:
        print("  " + line)
    return 0


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
        for dest, field in SPRINT_ARGS:
            sub.add_argument("--" + dest.replace("_", "-"), dest=dest,
                             metavar="SPRINT",
                             help="%s - a sprint ID from the register's "
                                  "calendar, or '' to clear" % field)
        sub.add_argument("--sprint-carried", dest="sprint_carried", metavar="SPRINT",
                         help="add a sprint this row is committed to again, after "
                              "Sprint Planned (spillover or the next slice), or '' "
                              "to clear the list")
        for dest, field in DATE_ARGS:
            sub.add_argument("--" + dest.replace("_", "-"), dest=dest,
                             metavar="DATE", help="%s (%s)" % (field, D.FORMS))
        sub.add_argument("--reason", help="why a planned date moved; required "
                                          "when one does")
        sub.add_argument("--closure", metavar="NOTE",
                         help="what happened and where each AC stands; "
                              "required when a row moves to Done or Cancelled")
        sub.add_argument("--pulled-in", metavar="EFFECT",
                         help="starting or closing a row the running sprint never committed "
                              "to: it is pulled in, with its effect ('displaces nothing', "
                              "'delays <item>'). Sets Sprint Added and prints the record line")
        sub.add_argument("--outside-sprint", metavar="REASON",
                         help="...or it is work outside the sprint, with why. Noted, nothing marked")
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

    s = subs.add_parser("note", help="add a dated entry to Comments, newest on "
                                     "top (below any closure note)")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("text")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_note)

    s = subs.add_parser("split", help="close the part of a row delivered in a "
                                      "sprint and keep the rest open")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("--delivered", type=float, required=True,
                   help="hours delivered in the sprint")
    s.add_argument("--rest-effort", type=float,
                   help="hours left (default: the estimate less --delivered)")
    s.add_argument("--sprint", metavar="SPRINT",
                   help="the sprint the delivered part closes in (default: the "
                        "row's latest)")
    s.add_argument("--done-title")
    s.add_argument("--rest-title")
    s.add_argument("--closure", required=True, metavar="NOTE",
                   help="the delivered part's closure note: what happened, AC")
    s.add_argument("--actual-end", metavar="DATE",
                   help="when the delivered part finished (default: today)")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_split)

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
    s.add_argument("register", nargs="+",
                   help="one or more; a cross-project sprint takes all of them")
    s.add_argument("--sprint", required=True, metavar="ID", help='e.g. "S26.Q3.5"')
    s.add_argument("--json", action="store_true",
                   help="emit the same figures as a structure, for a caller to consume")
    s.set_defaults(func=cmd_metrics)

    s = subs.add_parser("pullins", help="rows pulled into the running sprint that its record does not name yet")
    s.add_argument("--sprint", help="default: the sprint running today")
    s.add_argument("--root", help="the folder whose WBS registers and sprint record are read (default: the current one)")
    s.add_argument("--records", help="the sprint records folder (default: the record found under --root)")
    s.set_defaults(func=cmd_pullins)

    s = subs.add_parser("refined",
                        help="whether candidates carry what planning needs")
    s.add_argument("register")
    s.add_argument("--ids", required=True, metavar="N,N,N",
                   help="the candidates, as the grooming draft names them")
    s.add_argument("--execution", metavar="DIR",
                   help="also check whether a spec in this folder names each one "
                        "(default: the register's meta.execution.folder)")
    s.add_argument("--raid", metavar="REGISTER",
                   help="also name open RAID items whose WBS Ref points at each one")
    s.set_defaults(func=cmd_refined)

    s = subs.add_parser("deliverables",
                        help="open Key Deliverables: lost baselines, unscheduled, uncovered")
    s.add_argument("registers", nargs="+")
    s.add_argument("--by", metavar="DATE",
                   help="also flag baselines falling before this date - usually the "
                        "end of the sprint being planned (%s)" % D.FORMS)
    s.add_argument("--sprint", metavar="ID",
                   help="flag deliverables with nothing committed to this sprint "
                        "or staged Next")
    s.set_defaults(func=cmd_deliverables)

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
