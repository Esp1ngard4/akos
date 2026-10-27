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
import io
import json
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
    # A Change is a request that needs a decision, not the decision itself:
    # the answer goes in Outcome, and its date is the log entry that set it.
    # A Lesson is what the work taught, with the evidence and what changes.
    # What puts it into practice is named in Applied By, not in the sentence.
    "Lesson":   (u"We learned that %s, because %s, so next time %s.",
                 ("learned", "because", "next_time"),
                 ("what we learned", "what showed it", "what to do differently")),
    "Change":   (u"Change %s, requested by %s, because %s; impact: %s.",
                 ("change", "requested_by", "because", "impact"),
                 ("what", "who", "why", "on scope, schedule or cost")),
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
    "Change":   re.compile(u"^change .+ requested by .+ because .+ impact: ", re.I | re.S),
    "Lesson":   re.compile(u"^we learned that .+ so next time ", re.I | re.S),
}

# Fields bound to one of the register's vocabularies, by vocabulary name.
VOCAB_FIELDS = {"Type": "type", "Status": "status", "Outcome": "outcome",
                "Trend": "trend", "Sharable": "sharable", "Reusable": "reusable"}

# Trend is stored as the arrow, which is what every reader shows, under the one
# convention every report and the board share: up is better. The
# words are accepted as input because an arrow is awkward to type at a prompt,
# the chip's short words as well as the long ones.
TREND_WORDS = {"improving fast": u"↑", "much better": u"↑",
               "improving": u"↗", "better": u"↗",
               "stable": u"→", "steady": u"→",
               "worsening": u"↘", "worse": u"↘",
               "worsening fast": u"↓", "much worse": u"↓"}


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

# "<project>#<WBS ID>", e.g. "Atlas#24". Scope-qualified always, never a bare
# number: an ID is unique inside a register and not across them.
WBS_REF = re.compile(r"^[^#]+#\d+$")


def run_checks(data):
    """Read-only. Errors are things that will misrender or mislead; warnings are
    conventions worth following that no one should be blocked on."""
    errors, warnings = [], []
    known = set(fields_of(data))

    for row in R.rows(data, ENTRIES):
        rid = R.clean(row.get(ID)) or "?"
        typ, status = R.clean(row.get("Type")), R.clean(row.get("Status"))

        for field, vocab in sorted(VOCAB_FIELDS.items()):
            allowed, value = vocabulary(data, vocab), R.clean(row.get(field))
            if allowed and value and value not in allowed:
                errors.append("R.%s %s %r is not in the vocabulary" % (rid, field, value))
            elif value and not allowed and field in ("Outcome", "Trend"):
                errors.append("R.%s has %s, but the register has no %s vocabulary "
                              "- run `raid.py migrate`" % (rid, field, vocab))
        # The On Scope signal counts approved Changes; an Outcome anywhere else
        # would be counted as one, or silently mean nothing.
        if R.clean(row.get("Outcome")) and typ != "Change":
            errors.append("R.%s has an Outcome but is a %s - Outcome is for "
                          "Change entries" % (rid, typ or "row with no Type"))
        if typ == "Change" and status == "Closed" and not R.clean(row.get("Outcome")):
            warnings.append("R.%s is a Closed Change with no Outcome" % rid)
        for name in row:
            if known and name not in known:
                errors.append("R.%s has field %r, which the schema does not "
                              "define" % (rid, name))

        # A reference to a WBS row, when the item is about one. Shape only:
        # this register does not know where any WBS register lives, and a
        # stored path would rot the first time a folder moved. Resolution
        # happens in `wbs.py refined --raid`, which is handed both registers.
        #
        # Always scope-qualified, because a WBS ID is unique within a register
        # and not across them. Most entries carry nothing here and should: a
        # capacity risk or a systemic decision is not about a deliverable, and
        # there is no "n/a" to write because nothing asks the reverse question.
        ref = R.clean(row.get("WBS Ref"))
        if ref and not WBS_REF.match(ref):
            errors.append("R.%s WBS Ref %r is not project#id - e.g. "
                          "Atlas#24" % (rid, ref))

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
    if args.type != "Lesson" and (args.reusable or args.applied_by):
        sys.exit("--reusable and --applied-by belong to a Lesson.")
    for key, value in (("MoSCoW", args.moscow), ("Category", args.category),
                       ("Reusable", args.reusable), ("Applied By", args.applied_by),
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
            hint = ("\n  It is in the current schema: run `raid.py migrate --apply` first."
                    if name in ("Outcome", "Trend", "Sharable") else "")
            sys.exit("%r is not a field in this register.\n  fields: %s%s"
                     % (name, ", ".join(known), hint))
        if name == LOG:
            sys.exit("The Action Log is append-only. Use `raid.py log` instead.")
        if name == "Trend":
            value = TREND_WORDS.get(value.lower(), value)
        if name in VOCAB_FIELDS:
            if value and name in ("Outcome", "Trend", "Sharable") and not vocabulary(data, VOCAB_FIELDS[name]):
                sys.exit("This register has no %s vocabulary yet. Run `raid.py "
                         "migrate --apply` first." % VOCAB_FIELDS[name])
            check_vocab(data, VOCAB_FIELDS[name], value)
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
    if R.clean(row.get("Outcome")) and R.clean(row.get("Type")) != "Change":
        sys.exit("Outcome is for Change entries; R.%s is a %s. Nothing written."
                 % (args.id, R.clean(row.get("Type"))))

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
    if R.clean(row.get("Type")) == "Change" and not R.clean(row.get("Outcome")):
        sys.exit("R.%s is a Change with no Outcome. Decide it first:\n  raid.py "
                 "update ... --id %s --set Outcome=Approved -m \"<why>\"" % (args.id, args.id))
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


# --------------------------------------------------------------------------- #
# The cross-project Lessons page. Every RAID register under a root folder,
# found by meta.kind, archived projects included: a register under a folder
# whose name starts "Archive" (any case) is shown as archived. A lesson is worth
# most on the next project, so the page reads across projects, not one.

SKIP_DIRS = ("PreviousV", "Reports", "AuxMat", ".git", "__pycache__", "node_modules")


def raid_registers(root):
    found = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        rel = os.path.relpath(here, root).split(os.sep)
        where = "archived" if any(part.lower().startswith("archive") for part in rel) else "active"
        for name in sorted(files):
            path = os.path.join(here, name)
            if name.endswith(".json"):
                try:
                    with io.open(path, encoding="utf-8") as fh:
                        if json.load(fh).get("meta", {}).get("kind") == "raid-register":
                            found.append((path, where))
                except (IOError, OSError, ValueError):
                    pass
    return found


def cmd_lessons(args):
    root = os.path.abspath(args.root or os.getcwd())
    out = args.out or os.path.join(root, "Lessons Dashboard.html")
    regs = raid_registers(root)
    lessons = []
    for path, where in regs:
        data = R.load(path)
        scope = data.get("meta", {}).get("scope") or os.path.basename(path)
        for row in R.rows(data, ENTRIES):
            if R.clean(row.get("Type")) != "Lesson":
                continue
            lessons.append({"scope": scope, "archived": where == "archived", "ref": "R.%s" % row.get(ID),
                            "detail": row.get("Detail") or "", "description": row.get("Description") or "",
                            "status": R.clean(row.get("Status")) or "Open",
                            "category": R.clean(row.get("Category")) or "Uncategorised",
                            "reusable": R.clean(row.get("Reusable")) == "Y",
                            "applied": R.clean(row.get("Applied By")) or "", "learned": row.get("Opened On") or "",
                            "dri": row.get("DRI") or ""})
    lessons.sort(key=lambda x: (not x["reusable"], x["category"].lower(), x["learned"]))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(LESSONS_PAGE.replace("__DATA__", json.dumps(
            {"lessons": lessons, "registers": [{"scope": R.load(p).get("meta", {}).get("scope") or os.path.basename(p),
                                                "archived": w == "archived"} for p, w in regs],
             "generated": dt.date.today().isoformat()}, ensure_ascii=False).replace("</", "<\\/")))
    print("Lessons page: %d lesson(s) from %d RAID register(s) (%d archived)\n  %s"
          % (len(lessons), len(regs), sum(1 for _p, w in regs if w == "archived"), out))
    return 0


LESSONS_PAGE = u"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lessons Learned</title>
<style>
:root { --page:#f6f6f4; --surface:#fcfcfb; --border:rgba(11,11,11,0.10); --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --good:#0ca30c; --goodbg:#e8f5e8; --s1:#2a78d6; --donebg:#e3edfa; --nonebg:#efeee9; }
@media (prefers-color-scheme: dark) { :root { --page:#0d0d0d; --surface:#1a1a19; --border:rgba(255,255,255,0.10);
  --ink:#fff; --ink2:#c3c2b7; --goodbg:#16301a; --donebg:#17263a; --nonebg:#262624; } }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--page); color:var(--ink); font-size:13px; line-height:1.5; padding:20px 16px; }
.page { max-width:1100px; margin:0 auto; }
h1 { font-size:20px; } .meta { color:var(--ink2); font-size:12px; margin:2px 0 14px; }
.filters { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; }
select { font:inherit; padding:4px 8px; border:1px solid var(--border); border-radius:8px; background:var(--surface); color:var(--ink); }
h2 { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.8px; color:var(--ink2); margin:16px 0 8px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin-bottom:10px; }
.head { display:flex; flex-wrap:wrap; align-items:center; gap:6px 10px; margin-bottom:4px; }
.ref { font-weight:700; color:var(--ink2); } .title { font-weight:650; }
.chip { font-size:11px; border-radius:10px; padding:0 8px; background:var(--nonebg); color:var(--ink2); white-space:nowrap; }
.chip.reuse { background:var(--goodbg); color:var(--good); font-weight:600; } .chip.closed { background:var(--donebg); color:var(--s1); }
.small { font-size:11.5px; color:var(--ink2); margin-top:4px; } .muted { color:var(--muted); }
</style></head><body><div class="page">
<h1>Lessons learned</h1><div class="meta" id="meta"></div>
<div class="filters">
  <select id="fScope"><option value="">All projects</option></select>
  <select id="fCat"><option value="">All categories</option></select>
  <select id="fReuse"><option value="">Reusable or not</option><option value="Y">Reusable</option><option value="N">This project only</option></select>
  <select id="fStatus"><option value="">Open or closed</option><option value="Open">Open: not yet applied</option><option value="Closed">Closed: applied</option></select>
</div>
<div id="list"></div>
</div>
<script>
const D = __DATA__;
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const regs = D.registers.map(r => esc(r.scope) + (r.archived ? ' (archived)' : '')).join(', ');
document.getElementById('meta').innerHTML = D.lessons.length + ' lesson(s) from ' + D.registers.length +
  ' RAID register(s): ' + (regs || 'none') + ' · generated ' + D.generated + ' by raid-manager, never edited by hand';
const fill = (id, vals) => { const s = document.getElementById(id); [...new Set(vals)].sort().forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; s.appendChild(o); }); };
fill('fScope', D.lessons.map(l => l.scope)); fill('fCat', D.lessons.map(l => l.category));
function render() {
  const f = id => document.getElementById(id).value;
  const shown = D.lessons.filter(l => (!f('fScope') || l.scope === f('fScope')) && (!f('fCat') || l.category === f('fCat'))
    && (!f('fReuse') || (l.reusable ? 'Y' : 'N') === f('fReuse')) && (!f('fStatus') || l.status === f('fStatus')));
  if (!shown.length) { document.getElementById('list').innerHTML = '<p class="muted">' + (D.lessons.length ? 'No lesson matches these filters.' : 'No lesson recorded yet. Add one with raid.py add --type Lesson.') + '</p>'; return; }
  let html = '', group = null;
  shown.forEach(l => {
    const g = (l.reusable ? 'Reusable' : 'This project only') + ' · ' + l.category;
    if (g !== group) { html += '<h2>' + esc(g) + '</h2>'; group = g; }
    html += '<div class="card"><div class="head"><span class="ref">' + esc(l.scope) + ' ' + esc(l.ref) + '</span><span class="title">' + esc(l.detail) + '</span>' +
      (l.reusable ? '<span class="chip reuse">reusable</span>' : '') + '<span class="chip' + (l.status === 'Closed' ? ' closed' : '') + '">' + (l.status === 'Closed' ? 'applied' : 'not yet applied') + '</span>' +
      (l.archived ? '<span class="chip">archived project</span>' : '') + '</div><div>' + esc(l.description) + '</div>' +
      '<div class="small">Applied by: ' + (l.applied ? esc(l.applied) : '<span class="muted">nothing yet</span>') + ' · learned ' + esc(l.learned) + (l.dri ? ' · ' + esc(l.dri) : '') + '</div></div>';
  });
  document.getElementById('list').innerHTML = html;
}
['fScope','fCat','fReuse','fStatus'].forEach(id => document.getElementById(id).addEventListener('change', render));
render();
</script></body></html>
"""


def schema_gaps(data):
    """What the register's schema lacks against create_raid's: missing fields,
    and missing values in each vocabulary. Rows are never touched - a new type
    or field is something a row may use, not something every row must hold."""
    import create_raid as C
    fields = fields_of(data)
    missing_fields = [f for f in C.FIELDS if f not in fields]
    vocabs = R.setting(data, "vocabularies", {}) or {}
    missing_values = {}
    for name, values in C.VOCABULARIES.items():
        have = vocabs.get(name) or []
        lack = [v for v in values if v not in have]
        if lack:
            missing_values[name] = lack
    return missing_fields, missing_values


def apply_schema(data, missing_fields, missing_values):
    import create_raid as C
    settings = data["meta"].setdefault("settings", {})
    fields = settings.setdefault("fields", {}).setdefault(ENTRIES, [])
    for f in missing_fields:
        # Keep create_raid's order: insert after the field that precedes it there.
        at = C.FIELDS.index(f)
        before = next((p for p in reversed(C.FIELDS[:at]) if p in fields), None)
        fields.insert(fields.index(before) + 1 if before else len(fields), f)
    vocabs = settings.setdefault("vocabularies", {})
    for name, lack in missing_values.items():
        vocabs.setdefault(name, []).extend(lack)


def cmd_migrate(args):
    """Bring a register up to the current schema, and turn free-text Action Logs
    into dated entries.

    Dry by default. The schema half adds fields and vocabulary values and never
    touches a row. In the log half the date is only ever taken from the text
    itself and the author only from the row's DRI - neither is invented, so an
    entry that carried neither stays undated rather than being given a
    plausible date.
    """
    data = R.load(args.register)
    missing_fields, missing_values = schema_gaps(data)
    if missing_fields or missing_values:
        print("Schema:")
        for f in missing_fields:
            print("   + field       %s" % f)
        for name, lack in sorted(missing_values.items()):
            print("   + vocabulary  %s: %s" % (name, ", ".join(lack)))
        print()
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

    if not plan and not (missing_fields or missing_values):
        print("Nothing to migrate - the schema is current and every Action Log "
              "is already structured.")
        return 0
    for row, entry in plan:
        print("R.%s  %s" % (R.clean(row.get(ID)), R.clean(row.get("Detail"))))
        print("   from  %r" % R.clean(row.get(LOG))[:100])
        print("   to    on=%s by=%s\n         note=%r"
              % (entry.get("on") or "(none in the text)",
                 entry.get("by") or "(no DRI)", entry["note"][:100]))
    if plan:
        print("\n%d log entr%s to convert." % (len(plan), "y" if len(plan) == 1 else "ies"))
    trended = [r for r in R.rows(data, ENTRIES) if R.clean(r.get("Trend"))]
    if trended:
        print("\n%d entr%s a Trend. Up is better: \u2191 improving fast to \u2193 worsening fast."
              " A Trend set under the opposite reading now says the reverse; check each, nothing"
              " is converted:" % (len(trended), "y carries" if len(trended) == 1 else "ies carry"))
        for r in trended:
            print("   R.%s  %s  %s" % (R.clean(r.get(ID)), R.clean(r.get("Trend")), R.clean(r.get("Detail"))[:60]))
    if not args.apply:
        print("Dry run. Re-run with --apply to write.")
        return 0
    apply_schema(data, missing_fields, missing_values)
    for row, entry in plan:
        row[LOG] = [entry]
    if args.author and not R.setting(data, "author"):
        data["meta"].setdefault("settings", {})["author"] = args.author
    R.save(args.register, data)
    print("Written.")
    return 0


def main():
    # A console that cannot print a character (Windows' code page, a Trend arrow
    # in the change summary) gets a substitute, never a crash before the save.
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
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
    # A slot shared by two types (Decision's and Change's --because) is one
    # flag; Change's --requested-by is also the Requested By field.
    helps = {}
    for typ in sorted(SKELETONS):
        shape, slots, labels = SKELETONS[typ]
        for slot, label in zip(slots, labels):
            helps.setdefault("--" + slot.replace("_", "-"), []).append("%s: %s" % (typ, label))
    helps.setdefault("--requested-by", []).append("also fills Requested By")
    for flag, texts in helps.items():
        s.add_argument(flag, help="; ".join(texts))
    s.add_argument("--description", help="freehand, bypassing the type's shape")
    s.add_argument("--dri")
    s.add_argument("--moscow")
    s.add_argument("--category", help="for a Lesson: Planning, Estimation, Tooling, Process, "
                                       "Quality, People, Communication, or your own")
    s.add_argument("--reusable", choices=["Y", "N"], help="a Lesson: does it apply beyond this project")
    s.add_argument("--applied-by", help="a Lesson: the record that puts it into practice "
                                        "(R.12, a WBS row, a tool's change)")
    s.add_argument("--action-plan")
    s.add_argument("--acceptance", help="Acceptance Criteria")
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

    s = subs.add_parser("lessons", help="the cross-project Lessons page, from every RAID register")
    s.add_argument("--root", help="the folder whose RAID registers are read (default: the current one)")
    s.add_argument("--out", help="the page (default: Lessons Dashboard.html under --root)")
    s.set_defaults(func=cmd_lessons)

    s = subs.add_parser("migrate", help="bring the schema up to date; free-text "
                                        "Action Logs -> dated entries")
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
