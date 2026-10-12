# <Project name> — Project Brief

> Template. Copy it into the project's folder, beside its WBS register, as
> `Project Brief.md`: that is where the reporting tool (TSP.10) looks. Delete these
> quoted notes as you fill it in.
>
> **Lean or full.** A small project, one that keeps no WBS register and reports to
> nobody but its owner, stops after *Outcome and done-when*: that is the lean brief.
> Once it keeps a WBS or someone else reads its reports, it grows the rest, and the
> Measures table is what puts its outcome in the status report.
>
> **If the brief can't be written, there may be no reason to do the project.**
>
> Fill it in as the project matures: Why at the start, Outcome and Measures before the
> first sprint commits to it, Scope and Approach when the plan settles. Write the
> executive statement last. Each fact lives in one place: deliverables in the WBS, risks
> and decisions in the RAID register, dates and status in the registers. The brief
> points at them.

**Size:** lean | full · **Written:** YYYY-MM-DD · **Last revised:** YYYY-MM-DD · **Serves:** <the objective, bet or goal this project serves, if any>

> **To** <what the project does> **so that** <the outcome it serves>.

## Why

What prompted the project, and what happens if it is not done. The current state in a
few lines, and the state the project moves to.

## Outcome and done-when

The outcome in one sentence. This line is what the status report shows as the project's
outcome, so keep it to one sentence.

Done when (specific and checkable, three to five):

1. …

Key deliverables: the WBS rows tagged Key Deliverable (`wbs.py deliverables`).

**Stop if:** the condition that would make this not worth finishing.

### Measures

> Three to six measures, at least one **lag**: lead measures alone show activity, not
> value. Choose the ones that would change a decision, not one per done-when item. Each
> is defined in full when it is written, target and method included: a measure nobody
> knows how to take is a wish.
>
> - **ID**: M1, M2… assigned once, never reused, so a report's trend can follow it.
> - **Role**: `lag` (the result the project exists for) or `lead` (what should move it).
> - **Kind**: `H` habit (a rate, e.g. `80%` or `4 of 5`), `M` milestone (`done` or
>   `not done`), `N` number (toward a target, e.g. `12`, or `6 of 42`, read as 6).
> - **C/A**: committed (judged against its target) or aspirational (met at 0.7 of it).
> - **Baseline** and **From**: the value at the start and its date, so pace can be judged.
> - **Target** and **By**: what, and by when.
> - **How measured**: concretely enough that someone else could take it.
> - **Every**: how often it is read: `week`, `sprint`, `month`, `quarter` or `year`.
> - **Current** and **As of**: the latest value. Update the ones due before a status
>   report; older than its cadence, a value is reported stale.
> - **Source**: `measured`, `estimated` or `asked`. **WBS**: optional, the row it tracks.
>
> The status report scores each 0-1 like a key result and judges it against its pace
> at the date it was taken. A table that breaks this shape is reported as findings to
> fix, never as a failure.

| ID | Measure | Role | Kind | C/A | Baseline | From | Target | By | How measured | Every | Current | As of | Source | WBS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | … | lag | N | C | … | YYYY-MM-DD | … | YYYY-MM-DD | … | quarter | … | YYYY-MM-DD | measured | |

## Appetite and budget

- **Appetite:** the time this is worth: hours, or sprints at a share of capacity. When
  the work doesn't fit, the scope is cut rather than the cap raised.
- **Budget:** the money, if any, and where it is tracked.

## Scope

- **In:** …
- **Out:** … (what someone could reasonably expect, and won't get)
- **Assumptions and constraints:** time, dependencies on other projects or people.

## Approach

How the work runs: phases, whether it runs in sprints, and which registers it keeps
(WBS, RAID, an action tracker).

## Who it is for

Who benefits and who is affected, in a line or two.
