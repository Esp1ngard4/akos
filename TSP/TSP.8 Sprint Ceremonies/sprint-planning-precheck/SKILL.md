---
name: sprint-planning-precheck
description: Checks whether the next sprint is ready to plan - at the sprint close-out, the day before planning - and produces a readiness report from the WBS, RAID and tool registers. Use whenever the user asks "am I ready for planning", "are we ready for sprint planning", "pre-check before planning", "how's the next sprint looking", "is the backlog refined enough", or "do we need another grooming session". Also run it first when the user asks to start sprint planning and no close-out has been recorded for the sprint that is ending.
---

# Sprint Planning Pre-Check

Planning goes badly when it discovers gaps that could have been caught a day earlier: rows with no estimate, unfinished work nobody triaged, a candidate pool too thin to fill the sprint. This check surfaces them at the close-out, on the sprint's last day, so there is still time to act. That action might be a short grooming top-up, sizing three rows, or deciding consciously to carry something over.

**It reads and reports; it changes nothing.** The output is one structured report. The user decides what to act on, through `sprint-facilitator`, `wbs-manager` or `raid-manager`.

## Requirements

Python 3. Uses sibling skills from the skills folder: `sprint-facilitator` (its `sprint_record.py`) and `wbs-manager` are required. `raid-manager` and `tsp-manager` are optional. A check whose tool is missing is reported as **not assessed**, never as passed.

## Running the pre-check

### 1. Did the close-out happen?

```bash
python <skills>/sprint-facilitator/scripts/sprint_record.py status "<records>" --calendar "<conventions file>"
```

The pre-check is the second half of the close-out session. If the close-out has not been recorded, **lead the report with that and carry on**. Readiness judged without knowing what closed is guesswork, but whether to plan anyway is the user's decision. Nothing here blocks.

From the calendar, give planning's date, which is the next sprint's first day, and how far away it is.

### 2. What closed, and what follows from it

For each row **closed this sprint** (`Sprint Ended` is this sprint), reconstruct its context before recommending anything. Do not ask the user to recall it:

- **Its parent** (`Parent`): what outcome the row contributed to, and that outcome's acceptance criteria.
- **Its siblings** under the same parent. Classify each as closed, `Horizon` `Next`, `Horizon` `Future`, committed to a sprint, unscheduled, or missing an estimate.

Then recommend one action per closed row:

- **Stage the next sibling.** It is defined, not yet scheduled and not blocked, so set it to `Horizon Next`.
- **Check whether the parent is done.** Every child is closed; are the parent's acceptance criteria met?
- **No action; the dependency is tracked.** The next sibling waits on something recorded in `Key Dependencies` or RAID.
- **Create a follow-up row.** The closure note names follow-up work that no row holds.
- **Clean close.** The row is self-contained.

Each recommendation should leave the user a yes or no on a concrete proposal, with the lookup already done.

For each committed row **still open**, offer a lean and ask the user to classify it:
- **Spillover**: it is `Implementing`, or was updated recently.
- **Abandoned**: still `Not Started` with no `Actual Start` all sprint.
- **Finished but not closed**: the user says it is done; close it with a note.

### 3. Is the next sprint ready?

**Start from the grooming draft.** The current record's `Next sprint - draft` is the bounded list grooming took on, with each row's refinement state. That list is the denominator. Then list every row with `Horizon` `Next` as a check: if the pool is much larger than the draft, grooming shortlisted only a fraction of what was ripe, and the report should say so.

- **Capacity.** Sum the `Est.` hours on draft rows marked `ready`, and only those; an estimate on an unrefined item is a guess about work nobody has described. Compare the sum with the thresholds in `sprint-facilitator` (*Defaults*):
  - **Below the minimum:** not enough plannable work. Recommend another grooming slot.
  - **Between minimum and target:** enough to plan; planning will prioritise and cut.
  - **Above the target:** healthy, and planning will have real cuts to make.

  The thresholds are on the no-AI baseline. A sprint that delivers well past its refined hours is expected; do not suggest re-basing them.
- **Estimation gaps.** `Horizon Next` rows with no `Estimated Effort (h)`. If there are more than a couple, recommend sizing them before planning.
- **Refinement gaps**, computed rather than eyeballed:

  ```bash
  python <skills>/wbs-manager/scripts/wbs.py refined "<register>" --ids 21,83,99 [--execution "<folder>"] [--raid "<RAID register>"]
  ```

  A missing or thin description, a missing acceptance criterion or a missing estimate is a gap. Whether what is written names something concrete is still read, not computed. A missing action plan or spec is solution space, which is sprint work, so it is **not** a gap. A missing parent or Type is register hygiene: worth a line, not a readiness finding. An open RAID item against a candidate is context, not a blocker; surface it so the commitment is made knowing about it.

Refinement lives in three places: the row itself, any spec in the execution folder that names it, and the RAID entries that point at it (`WBS Ref`). A candidate can look complete in one and be bare in the others. If the team also tracks work in a task tracker, that is a fourth place, and TD.8 explains how to add it.

### 4. Planning's standing items

- **Key Deliverables**, across every register in play:

  ```bash
  python <skills>/wbs-manager/scripts/wbs.py deliverables "<register>" ["<register>" ...] --by <end of the incoming sprint> --sprint <incoming sprint ID>
  ```

  For each open Key Deliverable it reports a baseline already passed (or passing before `--by`), nothing scheduling it, or nothing committed or staged for the incoming sprint. Planning takes each one to commit, rebaseline or accept; running it today leaves time to act.
- **Control activities**, if a TSP register is in use: `tsp.py due "<TSP register>"`. Show the list and say plainly how stale it is. **Which ones to commit is the user's call.** Retiring dead ones, or routing the whole list to the retro, is as legitimate as committing three.

### 5. The report

One report, not a series of questions. Everything above the last section is evidence; the last section is what to do.

```
## Sprint Planning Readiness — <date>

**Planning:** <date> (<N> days away) · **Close-out:** recorded / NOT recorded

### What closed
<per closed row: the recommendation>
<per open committed row: spillover / abandoned / not closed, with the lean>

### Next sprint candidate pool
- Grooming draft: N listed, M ready (completion M/N)
- Ready hours: X h (minimum / target per sprint-facilitator)
- Wider Horizon Next pool: P rows [if much larger than the draft, say so]
- Missing estimates: [rows, or none]
- Refinement gaps: [rows and what each lacks, or none]

### Standing items
- Key Deliverables: [findings, or none]
- Controls: N due, K overdue by more than a year — which to commit is yours to say

### Recommended actions before planning
1. <the most important gap>
2. ...
```

Keep the recommendations concrete: "size rows 21, 83 and 99", "book a one-hour grooming top-up", "decide whether row 44 carries or is cancelled".

## A gap is a flag, never a veto

If an item is to be prioritised, it is prioritised, refined or not. What matters is that the choice is recorded: planning notes a row committed with a known gap, and the next close-out says what became of it. One sprint of that is a note; several sprints of it is evidence for the retro.

## What this skill does not do

- It does not write to any register or record. It recommends, and the user acts through the owning skill.
- It does not run planning (`sprint-facilitator` does).
- It does not groom. If the pool is too thin, the recommendation is another grooming session, not grooming on the spot.
