# <Project name> — Project Brief

<!--
Project Brief (TSP.14 Project Definition). Copy to the project's PrjMgm folder as `Project Brief.md`
(`brief.py new` does it), and delete these comments as the brief is written.

Lean or full. A project with no WBS register that reports to nobody but its owner keeps
the lean brief: the executive statement, Why, Outcome and done-when, and Stop if. Delete
everything from Measures down and set Size to lean. Once it runs a WBS or someone else reads
its reports, it grows the rest here, in this same file, and Size becomes full.

If the brief can't be written, there may be no reason to do the project.

Fill it in as the project matures: Why at the start, Outcome and Measures before the first
sprint commits to it, Scope and Approach when the plan settles. A section with nothing to say
yet stays as its prompt. Write the executive statement last.

The brief holds the outcome and what the project serves; reports and the Project Register
read them from here. Every other fact lives in one place: deliverables in the WBS, risks and
decisions in the RAID, dates and status in the registers, stakeholders in the Stakeholder
Register once the project has one. The brief points at them.

Last revised moves whenever the brief is revisited, even when nothing changes: a brief not
revised for a month is due a revisit.
-->

**Size:** full · **Written:** YYYY-MM-DD · **Last revised:** YYYY-MM-DD · **Serves:** <the objective or bet this project moves, if any>

> **To** <what the project does> **so that** <the outcome it serves>.

## Why

What prompted the project, and what happens if it is not done. The current state in a few
lines, and the state the project moves to.

## Outcome and done-when

<The outcome in one sentence. This line is the project's outcome wherever it is shown.>

Done when (specific and checkable, three to five):

1. …

Key deliverables: the WBS's Key Deliverable rows (`wbs.py deliverables`).

**Stop if:** <the condition that would make this not worth finishing>

### Measures

<!--
Three to six measures, at least one lag: lead measures alone show activity, not value.
Choose the ones that would change a decision, not one per done-when item. Each is defined in
full when written, target and method included: a measure nobody knows how to take is a wish.

- ID: M1, M2... assigned once, never reused, so a report's trend can follow a measure.
- Role: lag (the result the project exists for) or lead (what should move it).
- Kind: H habit (a rate, e.g. 80% or 4 of 5), M milestone (done or not done),
  N number (toward a target, e.g. 12, or 6 of 42, read as 6).
- C/A: committed (judged against its target) or aspirational (met at 0.7 of it).
- Baseline and From: the value at the start and its date, so pace can be judged.
- Target and By: what, and by when.
- How measured: concretely enough that someone else could take it.
- Every: how often it is read: week, sprint, month, quarter or year.
- Current and As of: the latest value. Updated before a status report when due;
  older than its cadence, it is stale.
- Source: measured, estimated or asked. WBS: optional, the row it tracks.
-->

| ID | Measure | Role | Kind | C/A | Baseline | From | Target | By | How measured | Every | Current | As of | Source | WBS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | … | lag | N | C | … | YYYY-MM-DD | … | YYYY-MM-DD | … | quarter | … | YYYY-MM-DD | measured | |

## Appetite and budget

- **Appetite:** the time this is worth: hours, or sprints at a share of capacity. When the
  work doesn't fit, the scope is cut rather than the cap raised.
- **Budget:** the money, if any, and where it is tracked.

## Scope

- **In:** …
- **Out:** … (what someone could reasonably expect, and won't get)
- **Assumptions and constraints:** time, dependencies on other projects or people.

## Approach

How the work runs: phases, whether it runs in sprints, and which registers it keeps (WBS,
RAID, Action Tracker, Stakeholder Register). Further definition documents, a PRD for a
product or a funder's business case, are linked here.

## Who it is for

Who benefits and who is affected, in a line or two. With a Stakeholder Register, point to it.
