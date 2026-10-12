#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create, append to, and report on a sprint's ceremony record.

    python sprint_record.py plan   <records dir> "S26.Q3.6" [--calendar <file>]
    python sprint_record.py review <records dir> "S26.Q3.6"
    python sprint_record.py retro  <records dir> "S26.Q3.6"
    python sprint_record.py status <records dir> [--calendar <file>]
    python sprint_record.py goals  <records dir> [--json]

One Markdown file per sprint, holding the sprint's whole arc: `plan` creates
it, `review` records what the sprint delivered, and `retro` appends how the
sprint was worked. A sprint is the natural unit, and the three read together.

Review and retro are kept apart deliberately, as the Scrum Guide has them: the
review inspects the *result*, the retro inspects the *process, the tools and
the way of working*. `status` reads the folder back and says what is due or
outstanding, which is what lets a daily routine raise a ceremony without being
asked. `goals` reads the iteration goals back - verdicts, carried goals,
goal-linked hours - and flags a record that breaks the layout.

`--calendar` takes any JSON file with a `sprints` list - the agile-conventions
file `wbs.py sprints seed` writes, or a WBS register that imported it. With
it, a sprint's dates come from the calendar; without it, from the dates in the
record's heading, and failing those from the planning date plus the sprint
length.

Standard library only. Writing a whole file rather than appending to one
removes a class of error: a block written twice, or written to the wrong
record. Here the file either exists or it does not.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

SPRINT_DAYS = 14
DUE_IN_DAYS = 3

PLAN_TEMPLATE = """# Sprint {label}

## Planning — {today}

**Capacity:** _h available_ · _h planned_

### Fist of five

Confidence in the plan, per participant. Solo: one row.

| Participant | Score (1-5) | If low, why |
|---|---|---|
|  |  |  |

### Iteration goals

`ID` is G1, G2... within this sprint. `Bet` names the bet or objective from a
longer planning cycle that the goal serves (a quarter's bet, an OKR), or
nothing. `Carried from` names the earlier goal this one continues
(`S26.Q3.6 G2`), reworded or widened included. The Review answers each goal;
this table is not edited after planning.

| ID | Goal | Done when | Bet | Carried from |
|---|---|---|---|---|
{goals}

### Committed items

One row per WBS row committed, qualified by scope where the sprint spans more
than one register (`Atlas#12`). `Area` is the area of life or work the item
serves, in whatever vocabulary the TSP register uses. `Goal` holds the IDs the
item serves (`G1`, `G1, G3`), or nothing.

| Item | Effort | Area | Goal | Notes |
|---|---|---|---|---|
|  |  |  |  |  |

### Notes

_Pending actions, blockers, anything worth saying at the retro._

## Noticed

Anything worth acting on, written down when it is noticed - at a ceremony or
mid-sprint, either is fine. The row records where it was sent, never the thing
itself: content belongs in the WBS or the RAID register.

| What | Routed to | Landed |
|---|---|---|
|  |  |  |

## Next sprint - draft

The shortlist for the sprint after this one, built up as the sprint runs and
drained at grooming. `Est.` counts only rows marked `ready` - an estimate on an
unrefined item is a guess about work nobody has described yet.

Dropping something from this list is a deliberate act, said out loud and struck
through rather than quietly deleted.

| Candidate | Where it lives | Refinement | Est. | Carried from |
|---|---|---|---|---|
|  |  |  |  |  |

**Grooming completion:** _refined_ / _listed_ · **Sufficiency:** _Xh refined_ (20h minimum, 40h target)

### Draft goals

Goals worth proposing at the next planning, written whenever they occur.
Planning carries them into its goals table marked `draft:`; the session
confirms, rewords or drops each.

-
"""

REVIEW_TEMPLATE = """
## Review — {today}

_What the sprint delivered. Not how it was worked — that is the retro._

### Highlights

_One or two sentences: what someone reading nothing else should know._

Run the metrics twice: once to open the session, once after the decisions
below, and record the closing figures. The session changes what it measures.
Pass every register the sprint spanned:

    wbs.py metrics "<register>" ["<register>" ...] --sprint "<sprint ID>"

### Metrics

| | Value |
|---|---|
| Velocity | _n items, _h |
| Completion | _% of items, _% of hours |
| Committed vs delivered | _h committed, _h delivered |
| Carryover | _n items, _h |
| Cycle time | _ days median, over _ of _ |
| Coverage | _ |

### Effort by register

Where the sprint's effort was meant to go, and where the finished work fell,
from the per-register split `metrics` prints. Both columns are estimates, not
time logged. One register: one row, and the table says nothing new - leave it.

| Register | Committed (h) | Share | Delivered (h) | Share |
|---|---|---|---|---|
|  |  |  |  |  |

### Iteration goals

One row per goal in the planning block, by its ID. `Achieved` is Yes, Partial
or No and nothing else; the nuance goes in `Why`, with RAID IDs (`R.7`) where
a risk or issue was the cause. A goal nobody marks achieved is a commitment
nobody checks.

| ID | Goal | Achieved | Why |
|---|---|---|---|
{goals}

### Committed with known gaps

Items taken into the sprint without stating the problem, what good looks like
or an effort guess. Committing anyway is a legitimate call - priority
outranks refinement - but what became of them is the evidence for whether it
keeps working.

| Item | Gap at commitment | Outcome |
|---|---|---|
|  |  |  |

### Carryover and closure

Each committed item that did not finish is spillover, quietly abandoned, or
finished and never closed. Deciding which makes the next planning session
honest about where it starts. For spillover, the reason it did not finish is
settled here and written on its WBS row when planning carries it.

| Item | Spillover / Abandoned / Not closed | Action |
|---|---|---|
|  |  |  |
"""

RETRO_TEMPLATE = """
## Retrospective — {today}

_Assesses how we are working — processes and tools. Not a planning or
refinement session._

Votes are how a team converges on what matters. Record them as a count or as
participant initials, whichever the session used. Running solo, leave the
column empty — that is correct, not missing.

### What went well

| Item | Votes |
|---|---|
|  |  |

### Anything that can be improved

| Item | Votes |
|---|---|
|  |  |

### What to do differently next iteration

The actionable one, drawn from the improvements that carried the most votes —
a retro that lists everything actions nothing. Route each to where it will be
seen: the WBS for work on a deliverable, the RAID register for an action, a
risk, an issue or a decision.

| Improvement | Votes | Routed to |
|---|---|---|
|  |  |  |
"""

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# '## Planning — 2026-09-10' / '## Retrospective — 2026-09-23'. The em dash is
# what the templates write; a hyphen is accepted so a hand-edited file still
# reads.
CEREMONY_RE = re.compile(
    r"^##[ \t]+(Planning|Review|Retrospective)[ \t]*[—-][ \t]*(\d{4}-\d{2}-\d{2})",
    re.M)
DATES_RE = re.compile(r"\((\d{1,2})-([A-Za-z]{3})[^)]*?/[ \t]*(\d{1,2})-([A-Za-z]{3})\)")
YEAR_RE = re.compile(r"\bS(\d{2})\.")


def slug(label):
    """A filename from a sprint label, keeping the ID and dropping the rest.

    'S26.Q3.6 (13-Sep / 26-Sep)' -> 'S26.Q3.6'. A label that is not a sprint
    ID is slugified whole, so this works before a team adopts the convention.
    """
    head = label.split("(")[0].strip() or label
    return re.sub(r"[^A-Za-z0-9._-]+", " ", head).strip().replace(" ", "-")


def path_for(records_dir, label):
    return os.path.join(records_dir, slug(label) + ".md")


def load_calendar(path):
    """{sprint ID: (start, end)} from any JSON file carrying a `sprints` list.

    None when no file is given. A file without the list is refused: a calendar
    the caller named and that holds nothing is a mistake worth hearing about.
    """
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data.get("sprints") if isinstance(data, dict) else None
    if not rows:
        sys.exit("%s holds no `sprints` list. Pass the agile-conventions file "
                 "wbs.py sprints seed wrote, or a register that imported it." % path)
    return {r["Sprint"]: (date.fromisoformat(r["Starts"]), date.fromisoformat(r["Ends"]))
            for r in rows}


def window(heading, fallback):
    """The sprint's declared dates, read from the record's heading.

    '# Sprint S26.Q3.6 (13-Sep / 26-Sep)' -> (2026-09-13, 2026-09-26). The
    heading is what the session agreed; the planning date only records when
    someone sat down, which can fall a day or two either side. The year comes
    from the sprint ID where there is one, otherwise from `fallback`.

    Returns (None, None) when the label carries no dates - valid, not an error.
    """
    m = DATES_RE.search(heading)
    if not m:
        return None, None
    y = YEAR_RE.search(heading)
    year = 2000 + int(y.group(1)) if y else (fallback or date.today()).year
    try:
        start = date(year, MONTHS[m.group(2).title()], int(m.group(1)))
        end = date(year, MONTHS[m.group(4).title()], int(m.group(3)))
    except (KeyError, ValueError):
        return None, None
    if end < start:                       # a sprint running across New Year
        end = date(year + 1, end.month, end.day)
    return start, end


def read_record(path, calendar=None):
    text = open(path, encoding="utf-8").read()
    rec = {"sprint": os.path.splitext(os.path.basename(path))[0],
           "planned": None, "review": None, "retro": None}
    keys = {"Planning": "planned", "Review": "review", "Retrospective": "retro"}
    for kind, iso in CEREMONY_RE.findall(text):
        key = keys[kind]
        if rec[key] is None:              # first of each wins; there is one
            rec[key] = date.fromisoformat(iso)
    # The calendar is the authority where it holds the sprint; the heading is
    # what the session wrote down when it did not.
    if calendar and rec["sprint"] in calendar:
        rec["starts"], rec["ends"] = calendar[rec["sprint"]]
    else:
        rec["starts"], rec["ends"] = window(text.split("\n", 1)[0], rec["planned"])
    return rec


def read_records(records_dir, calendar=None):
    """Every record in the folder, oldest planning session first.

    Sorted by the planning date rather than by filename: sprint IDs sort
    correctly only by luck, and a record whose label predates the convention
    does not sort against one that follows it at all.
    """
    if not os.path.isdir(records_dir):
        return []
    found = [read_record(os.path.join(records_dir, n), calendar)
             for n in sorted(os.listdir(records_dir)) if n.endswith(".md")]
    return sorted(found, key=lambda r: (r["planned"] or date.min, r["sprint"]))


def draft_goals(path):
    """The '- ' lines under '### Draft goals' in a record's draft section.

    Only that subsection is read, and only non-empty bullets: the template's
    empty '- ' is a prompt, not a goal.
    """
    text = open(path, encoding="utf-8").read()
    at = text.find("### Draft goals")
    if at < 0:
        return []
    goals = []
    for line in text[at:].split("\n")[1:]:
        if line.startswith("#"):
            break
        if line.startswith("- ") and line[2:].strip():
            goals.append(line[2:].strip())
    return goals


# --- Reading the goals back ------------------------------------------------
#
# The goals are recorded as tables so that a report can count them: hit rate,
# goals carried from sprint to sprint, and the share of committed hours that
# serve a goal. This is the one reader, so a report consumes `goals --json`
# rather than parsing Markdown of its own.

VERDICTS = ("Yes", "Partial", "No")
GOAL_ID_RE = re.compile(r"^G\d+$")
EFFORT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*h\b")


def block(text, name):
    """The text of one '## <name>' block, up to the next '## ' heading."""
    m = re.search(r"^##[ \t]+%s\b.*$" % name, text, re.M)
    if not m:
        return None
    nxt = re.search(r"^##[ \t]", text[m.end():], re.M)
    return text[m.end():m.end() + nxt.start()] if nxt else text[m.end():]


def table(text, heading):
    """The first pipe table under '### <heading>', as (header, rows).

    Rows that are empty in every cell are the template's prompt, not data.
    """
    if text is None:
        return None, []
    at = text.find("### " + heading)
    if at < 0:
        return None, []
    lines = []
    for line in text[at:].split("\n")[1:]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            lines.append(line)
        elif lines:
            break
    if len(lines) < 2:
        return None, []

    def cells(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = cells(lines[0])
    rows = []
    for line in lines[2:]:
        values = cells(line)
        if not any(values):
            continue
        rows.append({h: (values[i] if i < len(values) else "") for i, h in enumerate(header)})
    return header, rows


def unbold(cell):
    return cell[2:-2].strip() if cell.startswith("**") and cell.endswith("**") else cell


def read_goals(path):
    """One record's goals, verdicts and goal-linked hours, plus what breaks the
    layout. A record written before goals had IDs is reported as unstructured,
    never guessed at: a hit rate built on guesses is worse than a gap."""
    text = open(path, encoding="utf-8").read()
    sprint = os.path.splitext(os.path.basename(path))[0]
    out = {"sprint": sprint, "structured": False, "goals": [], "highlights": None,
           "hours": None, "findings": []}
    planning, review = block(text, "Planning"), block(text, "Review")
    header, rows = table(planning, "Iteration goals")
    if not header or "ID" not in header:
        return out
    out["structured"] = True
    find = out["findings"]

    goals = {}
    for r in rows:
        gid = r.get("ID", "")
        if not GOAL_ID_RE.match(gid):
            find.append("planning: goal ID %r is not G1, G2..." % gid)
            continue
        if r.get("Goal", "").lower().startswith("draft:"):
            find.append("%s is still marked draft:" % gid)
        goals[gid] = {"id": gid, "goal": r.get("Goal", ""),
                      "done_when": r.get("Done when", ""),
                      "bet": r.get("Bet", ""),
                      "carried_from": r.get("Carried from", ""),
                      "achieved": None, "why": None}

    if review is not None:
        _, answers = table(review, "Iteration goals")
        answered = set()
        for r in answers:
            gid = r.get("ID", "")
            if gid not in goals:
                find.append("review answers %r, which planning does not hold" % gid)
                continue
            answered.add(gid)
            verdict = unbold(r.get("Achieved", ""))
            goals[gid]["achieved"] = verdict or None
            goals[gid]["why"] = r.get("Why", "")
            if not verdict:
                find.append("%s is unanswered" % gid)
            elif verdict not in VERDICTS:
                find.append("%s: %r is not Yes / Partial / No" % (gid, verdict))
        for gid in goals:
            if gid not in answered:
                find.append("%s has no row in the review" % gid)
        hl = review.split("### Highlights", 1)
        if len(hl) == 2:
            # One paragraph: the metrics' instructions follow it in the template.
            body = hl[1].split("###", 1)[0].strip().split("\n\n", 1)[0].strip()
            out["highlights"] = body if body and not body.startswith("_") else None
    out["goals"] = list(goals.values())

    cheader, committed = table(planning, "Committed items")
    if cheader and "Goal" in cheader:
        total = linked = 0.0
        unestimated = 0
        for r in committed:
            item = r.get("Item", "")
            # A struck-through row was dropped; an all-bold row is a subtotal
            # heading over the rows beneath it, and counting it double-counts.
            if item.startswith("~~") or (item.startswith("**") and item.endswith("**")):
                continue
            serves = [g.strip() for g in r.get("Goal", "").split(",") if g.strip()]
            for g in serves:
                if g not in goals:
                    find.append("committed item names %s, which planning does not hold" % g)
            m = EFFORT_RE.search(r.get("Effort", ""))
            if not m:
                unestimated += 1
                continue
            hours = float(m.group(1))
            total += hours
            if serves:
                linked += hours
        out["hours"] = {"committed": total, "goal_linked": linked,
                        "unestimated_rows": unestimated}
    else:
        find.append("committed items have no Goal column")
    return out


def cmd_goals(records_dir, as_json):
    if not os.path.isdir(records_dir):
        sys.exit("%s is not a folder." % records_dir)
    records = read_records(records_dir)
    results = [read_goals(path_for(records_dir, r["sprint"])) for r in records]
    known = {(r["sprint"], g["id"]) for r in results for g in r["goals"]}
    for r in results:
        for g in r["goals"]:
            ref = g["carried_from"].split()
            if ref and (len(ref) != 2 or tuple(ref) not in known):
                r["findings"].append("%s carried from %r, which no record holds"
                                     % (g["id"], g["carried_from"]))
    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 1 if any(r["findings"] for r in results) else 0

    for r in results:
        if not r["structured"]:
            print("%s  unstructured - written before goals had IDs" % r["sprint"])
            continue
        verdicts = ", ".join("%s %s" % (g["id"], g["achieved"] or "open") for g in r["goals"])
        line = "%s  %s" % (r["sprint"], verdicts or "no goals")
        bets = ["%s %s" % (g["id"], g["bet"]) for g in r["goals"] if g["bet"]]
        if bets:
            line += "  | bets: %s" % ", ".join(bets)
        carried = [g["id"] for g in r["goals"] if g["carried_from"]]
        if carried:
            line += "  | carried: %s" % ", ".join(carried)
        h = r["hours"]
        if h and h["committed"]:
            line += "  | goal focus %g of %gh (%d%%)" % (
                h["goal_linked"], h["committed"], round(100 * h["goal_linked"] / h["committed"]))
            if h["unestimated_rows"]:
                line += ", %d row(s) unestimated" % h["unestimated_rows"]
        print(line)
        for f in r["findings"]:
            print("    ! %s" % f)
    return 1 if any(r["findings"] for r in results) else 0


def dated(label, calendar):
    """The label with the sprint's dates appended, when the calendar has them
    and the label does not already carry its own."""
    if not calendar or DATES_RE.search(label) or slug(label) not in calendar:
        return label
    start, end = calendar[slug(label)]
    return "%s (%d-%s / %d-%s)" % (label.strip(), start.day, start.strftime("%b"),
                                   end.day, end.strftime("%b"))


def cmd_plan(records_dir, label, calendar):
    path = path_for(records_dir, label)
    if os.path.exists(path):
        sys.exit("%s already exists. A sprint gets one record; append the retro "
                 "to it with the retro command rather than planning twice." % path)
    # Draft goals are written into the sprint that is ending, so they come from
    # the latest record, read before this one exists.
    previous = read_records(records_dir)
    carried = draft_goals(path_for(records_dir, previous[-1]["sprint"])) if previous else []
    rows = "\n".join("| G%d | draft: %s |  |  |  |" % (i, g.replace("|", "/"))
                     for i, g in enumerate(carried, 1)) or "|  |  |  |  |  |"
    os.makedirs(records_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(PLAN_TEMPLATE.format(label=dated(label, calendar),
                                      today=date.today().isoformat(), goals=rows))
    print("Created %s" % path)
    if carried:
        print("  %d draft goal(s) carried from %s - confirm, reword or drop each."
              % (len(carried), previous[-1]["sprint"]))
    print("  Fill capacity, goals and committed items live with the user.")
    return 0


# The record has two kinds of section. Planning, Review and Retrospective are
# events, written once and never touched again, and their order is the sprint's
# arc. Noticed and the draft are living: they accumulate from the day the sprint
# opens until grooming drains them. So a block cannot simply be appended - it
# has to land before the living sections, or the arc reads Planning, Noticed,
# draft, Review, which is not a chronology of anything.
LIVING_SECTIONS = ("## Noticed", "## Next sprint - draft")


def add_block(path, block):
    """Insert a ceremony block after the arc and before the living sections."""
    text = open(path, encoding="utf-8").read()
    cuts = [text.index(h) for h in LIVING_SECTIONS if h in text]
    if not cuts:                              # a record without the sections
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(block)
        return
    at = min(cuts)
    merged = text[:at].rstrip("\n") + "\n" + block.rstrip("\n") + "\n\n" + text[at:]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(merged)


def cmd_review(records_dir, label):
    path = path_for(records_dir, label)
    if not os.path.exists(path):
        sys.exit("%s does not exist. The sprint was never planned, or the label "
                 "does not match the one planning used." % path)
    text = open(path, encoding="utf-8").read()
    if "## Review" in text:
        sys.exit("%s already has a review. Edit it rather than appending a "
                 "second one." % path)
    if "## Retrospective" in text:
        # Chronology is the file's whole value: planning, review, retro.
        sys.exit("%s already has a retrospective, so a review appended now would "
                 "read out of order. Add the review above it by hand." % path)
    # The goals are pre-filled by ID from planning, so the session answers
    # them rather than copying a table by hand.
    _, planned = table(block(text, "Planning"), "Iteration goals")
    rows = "\n".join("| %s | %s |  |  |" % (g.get("ID", ""), g.get("Goal", ""))
                     for g in planned if g.get("ID")) or "|  |  |  |  |"
    add_block(path, REVIEW_TEMPLATE.format(today=date.today().isoformat(), goals=rows))
    print("Added the review to %s" % path)
    print("  Fill the highlights, metrics, goals and carryover decisions live,")
    print("  then run the goals command to check the record reads.")
    return 0


def cmd_retro(records_dir, label):
    path = path_for(records_dir, label)
    if not os.path.exists(path):
        sys.exit("%s does not exist. The sprint was never planned, or the label "
                 "does not match the one planning used." % path)
    text = open(path, encoding="utf-8").read()
    if "## Retrospective" in text:
        sys.exit("%s already has a retrospective. Edit it rather than appending "
                 "a second one." % path)
    add_block(path, RETRO_TEMPLATE.format(today=date.today().isoformat()))
    print("Added the retrospective to %s" % path)
    print("  Fill the three questions live with the user.")
    return 0


def cmd_status(records_dir, as_of, length, due_in, calendar):
    """Say what is due or outstanding, in sentences a daily routine can read out.

    Deliberately narrow: this answers "was a ceremony due and never recorded",
    which nothing else can see. Whether one is *scheduled* is a calendar
    question, for whoever has wired one in.
    """
    records = read_records(records_dir, calendar)
    if not records:
        print("No sprint has ever been recorded in %s." % records_dir)
        print("Nothing is overdue, because nothing has been planned - but that "
              "also means no sprint is currently open.")
        return 0

    r = records[-1]
    end = r["ends"]
    if end is None and r["planned"] is not None:
        end = r["planned"] + timedelta(days=length)

    if end is None:
        print("%s is the latest record and carries no dates, so whether a "
              "ceremony is due cannot be told from it." % r["sprint"])
        return 0

    over = (as_of - end).days             # negative while the sprint is open
    # The close-out comes first in the cycle, so it is reported first. Both it
    # and the retro close the same sprint; neither substitutes for the other.
    if r["review"] is None and (over > 0 or -over <= due_in):
        if over > 0:
            finding = ("%s ended %s and has no close-out - %d day%s overdue. "
                       "Planning the next sprint without it is planning blind."
                       % (r["sprint"], end, over, "" if over == 1 else "s"))
        else:
            finding = ("%s ends %s. The close-out is due that day, then the "
                       "retro." % (r["sprint"], end))
    elif r["retro"] is None:
        if over > 0:
            finding = ("%s ended %s and has no retrospective - %d day%s overdue."
                       % (r["sprint"], end, over, "" if over == 1 else "s"))
        elif -over <= due_in:
            finding = "%s ends %s. The retrospective is due." % (r["sprint"], end)
        else:
            finding = None
    elif over > 0:
        finding = ("%s closed on %s. No sprint has been planned since - %d day%s "
                   "without one." % (r["sprint"], r["retro"], over,
                                     "" if over == 1 else "s"))
    elif -over <= due_in:
        finding = "%s ends %s. The next sprint needs planning." % (r["sprint"], end)
    else:
        finding = None

    if finding is None:
        print("No ceremony is due or outstanding. %s runs to %s."
              % (r["sprint"], end))
        return 0
    print(finding)

    # The close-out and the readiness check share one session on the sprint's
    # last day, followed by the retro; planning is the next day, the new
    # sprint's first. Grooming leaves no record of its own - its evidence is the
    # refined state of the candidates - so the precheck is the only thing that
    # can say whether planning has anything ready to work from.
    print("The close-out shares its session with sprint-planning-precheck: "
          "close the sprint first, then check readiness. Grooming leaves no "
          "record, so the state of the candidates is the only evidence it "
          "happened.")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command")
    s = sub.add_parser("plan", help="create the sprint's record")
    s.add_argument("records_dir")
    s.add_argument("label", help='a sprint ID, e.g. "S26.Q3.6", or a label '
                                 'with dates, e.g. "S26.Q3.6 (13-Sep / 26-Sep)"')
    s.add_argument("--calendar", metavar="FILE",
                   help="JSON with a `sprints` list; dates the heading from it")
    for name, helptext in (("review", "append what the sprint delivered"),
                           ("retro", "append how the sprint was worked")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("records_dir")
        s.add_argument("label", help='the sprint ID planning used, e.g. "S26.Q3.6"')
    s = sub.add_parser("goals", help="read every record's goals back, and check the layout")
    s.add_argument("records_dir")
    s.add_argument("--json", action="store_true", help="emit JSON for a report to consume")
    s = sub.add_parser("status", help="say what is due or outstanding")
    s.add_argument("records_dir")
    s.add_argument("--calendar", metavar="FILE",
                   help="JSON with a `sprints` list; the authority for dates")
    s.add_argument("--as-of", default=None, metavar="YYYY-MM-DD",
                   help="treat this as today, for testing")
    s.add_argument("--length", type=int, default=SPRINT_DAYS, metavar="DAYS",
                   help="sprint length, used only when neither the calendar nor "
                        "the record gives dates (default: %d)" % SPRINT_DAYS)
    s.add_argument("--due-in", type=int, default=DUE_IN_DAYS, metavar="DAYS",
                   help="how far ahead counts as due (default: %d)" % DUE_IN_DAYS)
    args = p.parse_args()

    if args.command == "plan":
        return cmd_plan(args.records_dir, args.label, load_calendar(args.calendar))
    if args.command == "review":
        return cmd_review(args.records_dir, args.label)
    if args.command == "retro":
        return cmd_retro(args.records_dir, args.label)
    if args.command == "goals":
        return cmd_goals(args.records_dir, args.json)
    if args.command == "status":
        as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
        return cmd_status(args.records_dir, as_of, args.length, args.due_in,
                          load_calendar(args.calendar))
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
