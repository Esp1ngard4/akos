---
name: sprint-facilitator
description: Runs the sprint ceremonies - backlog grooming (refinement), sprint close-out (sprint review), sprint retrospective and sprint planning - on WBS and RAID registers, and keeps one Markdown record per sprint. Use whenever the user says "let's run sprint planning", "groom the backlog", "refinement session", "time for the retro", "close out the sprint", "what did we deliver this sprint", "sprint review", or asks whether a ceremony is due or overdue - even if they just say "let's do the sprint session".
---

# Sprint Facilitator

Runs the four ceremonies of a sprint and leaves a record of each. Run one with this skill so the facts come from the registers, the user's judgment is asked for only where it is needed, and a record is left. This avoids deciding from memory and then forgetting to write anything down.

**The sprint lives in the registers.** A row is committed by its `Sprint Planned`, in flight by its Status, finished by its closure. Nothing here needs a task tracker or a calendar. TD.8 says what each ceremony is for and why, and how to adapt this skill to the tools a team already uses.

## Requirements

Python 3, standard library only. Uses sibling skills, found beside this one in the skills folder:

| Skill | Needed for |
|---|---|
| `wbs-manager` | **Required.** Every ceremony reads or writes WBS rows |
| `raid-manager` | Optional. Grooming's open-item check; the retro's routing |
| `tsp-manager` | Optional. Planning's control activities |

If `wbs-manager` is missing, say so and stop: there is nothing to run the sprint on. If an optional one is missing, skip its step and say which.

## Files

| Path | Role |
|---|---|
| `<records>/<sprint ID>.md` | **The sprint's record.** One per sprint: `Planning`, `Review`, `Retrospective`, then the living `Noticed` and `Next sprint - draft` |
| `scripts/sprint_record.py` | Writes the record and reads it back: `plan`, `review`, `retro`, `status`. Never write those blocks by hand |
| `references/record-layout.md` | The record's sections and the script's refusals |
| The agile-conventions file | The sprint calendar (`meta.kind` `agile-conventions`), written by `wbs.py sprints seed`. Pass it as `--calendar` |
| WBS and RAID registers | Found the way `wbs-manager` and `raid-manager` find them. **A sprint may span several**; pass every one in play |

**Finding the records.** A sprint record is a Markdown file named for a sprint ID whose first line starts `# Sprint `. Glob `**/S*.md` and keep those. Their folder is the records folder. If there are none, ask where to start one. Beside the conventions file is a good default: a project's planning folder for a team, a personal workspace for one person running several projects.

## Defaults

Edit these for your team. They are written here once, not recalculated each sprint.

| | Default | Meaning |
|---|---|---|
| Grooming minimum | **20h** refined | Below it, grooming is not finished, whatever share of the list it covered |
| Grooming target | **40h** refined | Enough that planning has real choices to make |
| Controls per sprint | **3** | Due control activities committed at planning, when a TSP register is in use |
| Effort sizes | 0.5, 1, 2, 3, 5, 8 h | Suggested buckets for `Estimated Effort (h)` |

**Estimates use the no-AI baseline.** Size work as if agent support were not there. The agent is the accelerator on top and is not folded into the number. Because the baseline stays fixed, the thresholds do not drift either. Delivering several times the estimate is the accelerator showing up, not an estimating error.

## Which ceremony, and is it due

If the user does not say, ask the records:

```bash
python <skill-path>/scripts/sprint_record.py status "<records>" --calendar "<conventions file>"
```

It answers what nothing else can: was a ceremony due and never recorded. It reports a close-out or retro that is due or overdue, or a closed sprint with nothing planned after it. Report it plainly. Do not hedge an overdue ceremony. Grooming is invisible to it by design, because grooming writes no ceremony block.

The order is fixed. **On the sprint's last day the close-out runs, then the retro. Planning runs on the next sprint's first day.** Grooming runs about four days before planning. The retro precedes planning so that planning can commit to what the retro decided.

## Anything noticed goes in `Noticed`

When something worth acting on surfaces, at any ceremony or on an ordinary day between them, write a row in the current record's `## Noticed` at that moment. Route the content in the same breath: work on a deliverable goes to the WBS, and an action, risk, issue or decision goes to the RAID register.

The row records **what** was noticed and **where it was sent**. It never holds the item itself. A row whose `Routed to` is empty is an admission, not an entry. A finding said out loud and left in prose is lost when the sprint closes; a routed row is not.

## A pull-in states its effect on committed work

Work taken into the sprint after planning gets a row in the record's *Committed items* **the day it is pulled in**, at a ceremony or between them, and its WBS row gets `Sprint Added`. The row's `Notes` say `**pulled in <DD-Mon>**`, then `effect:` and one of two answers:

- `displaces nothing`: the sprint has room, or the stretch was declared for it;
- the committed item it delays, by name (`delays Atlas 34`), or, when it only might, the one that slips first if the sprint runs short (`Atlas 3 slips first if needed`).

Ask the user which, in one question; the answer is theirs. Pulling in is fine: the rule exists so the trade-off is made out loud rather than found at the close-out, which reads it at step 4.

The WBS tool asks at the moment work starts: `wbs.py set --status Implementing` on a row the sprint never committed to is refused until it is given `--pulled-in "<effect>"` or `--outside-sprint "<reason>"`, and a pull-in prints its line for *Committed items*, `Area` left for the user. Add that line the same day. `wbs.py pullins` lists any pulled-in row the record does not name yet; a daily routine runs it (`daily-loop-facilitator`, the evening).

## Ready means three things are stated

A candidate is **ready** when it states:

- **the problem or opportunity** it addresses (in `Description`)
- **what good would look like** when it is done (in `Acceptance Criteria`)
- **an educated guess at the effort** (in `Estimated Effort (h)`)

Any of the three can be a guess drawn from past sprints, written down as such. The sprint tests the guess. **The solution space is sprint work**: the specs, the design and the breakdown of how the work will be done. When the people who refine an item are the ones who do it, working all that out days ahead buys nothing and costs two context switches. Refine until the three are stated, and stop there.

## Running backlog grooming

Grooming produces enough refined work to fill a sprint. Choosing among it is planning's job.

0. **Open the current record's `Next sprint - draft`.** It is the shortlist built up while the sprint ran, and the session starts there rather than searching every register for what is in play.
1. **Find what is in play**: rows `Implementing`, and rows committed to the current sprint (`Sprint Planned` or `Sprint Carried`), across every register.
2. **Ask what the next month holds.** Two separate questions: what is coming that needs preparation (and may become a row), and what takes capacity away (absences, other commitments). Do not merge them into one.
3. **Triage** rows with `Horizon` `Next` or `Future`, the in-play rows (do not close something just because it is old; ask), and any new material the user brings. New work becomes a row through `wbs-manager` (`wbs.py add`, under the deliverable it serves). A risk, issue, action or decision becomes a RAID entry through `raid-manager`.
4. **Close what finished.** A row whose work is done is closed now: `wbs.py set --status Done --closure "…"`, which refuses without a closure note and stamps `Actual End`. Correct the stamp if the work finished earlier.
5. **Refine each candidate to ready**, and check it with:

   ```bash
   python <skills>/wbs-manager/scripts/wbs.py refined "<register>" --ids 12,14 [--execution "<folder>"] [--raid "<RAID register>"]
   ```

   Read the output against the ready rule. A missing or thin description, acceptance criterion or estimate is a gap. A missing action plan or spec is solution space, so it is not a gap. An open RAID item against a candidate is context, not a blocker.
6. **Estimate as you refine**, not in a batch at the end, on the no-AI baseline. If the user is unsure, mark it *needs sizing* rather than forcing a number. `Description`, `Acceptance Criteria` and `Estimated Effort (h)` have no `wbs.py` flag; they are plain field edits (`wbs-manager`, *Critical Design Rules*).
7. **Set `Horizon`** the moment a row is ready: `Next` for the coming sprint, `Future` for the one after. Anything further out gets its `Planned End` and no Horizon. A horizon is a claim about the next four weeks.
8. **Close against the draft with two figures**, written into the draft's footer line:
   - **Completion**: refined ÷ listed.
   - **Sufficiency**: the `Est.` hours on rows marked `ready`, summed, against the minimum and target above. Below the minimum, say so and propose another slot rather than declaring grooming done.
9. **Dropping a candidate is a deliberate act.** Strike it through with a word on why. An item carried for several sprints without being committed either goes out loud or keeps its `Carried from`, which makes the rot visible.
10. **Grooming writes only to the draft and `Noticed`.** It leaves no ceremony block. A record that a meeting happened proves nothing; a record of what got refined can be checked against the registers.

## Running the sprint close-out

On the sprint's last day, before the retro. **It inspects the result**: what the sprint delivered against what it took on. How the work went is the retro's question, and a close-out that drifts into "we should estimate differently" has taken the retro's job.

1. **Open with the numbers**, across every register the sprint spanned:

   ```bash
   python <skills>/wbs-manager/scripts/wbs.py metrics "<register>" ["<register>" ...] --sprint <sprint ID>
   ```

   Totals first, with the per-register split underneath. Where a figure cannot be produced, say why. A gap in what the sprint recorded is a close-out topic, and usually a more useful one than a number.
2. **Answer the iteration goals.** `review` pre-fills them by ID from the planning block. Mark each `Yes`, `Partial` or `No` and nothing else; the nuance goes in `Why`, with RAID IDs where a risk or issue was the cause. Write the *Highlights*: one or two sentences for someone who reads nothing else. A partly met goal is still answered here: it belonged to this sprint, and whatever continues becomes a new commitment at planning, *Carried from* this one.
3. **Account for what was committed with known gaps**, using the planning block's notes. Committing unready work is legitimate, but what became of it is the evidence for whether that keeps working.
4. **Decide the carryover.** **Read the pull-ins' `effect:` lines first.** A committed item a pull-in said it would delay, or would slip first, did not slip on its own: its why names that pull-in. A pull-in with no `effect:`, or one only written into the record at this close-out, is recorded as `effect not stated`: a gap in how the sprint was run, and the retro's to look at. Each committed row that did not finish is one of three things: genuine spillover, quietly abandoned, or finished and never closed. Close the third kind now with a closure note. For spillover, settle in a sentence why it did not finish; planning writes that sentence onto the row when it carries it. **Then ask of each unfinished leaf: was any of it delivered?** Nothing: it is carried whole at planning. Something: split it now (`wbs.py split --id <n> --delivered <h> --sprint <closing sprint> --closure "..."`, `wbs-manager` operation 4b), so what was delivered closes in this sprint with its hours and the rest stays open, and point the open task in the tracker at the rest. A parent is not split: its children are closed or carried. `check` flags a row carried into two or more sprints: re-scope it, break it down, or drop it out loud.
5. **Re-run the metrics, then write the record.** The session changes what it measures, so record the closing figures:

   ```bash
   python <skill-path>/scripts/sprint_record.py review "<records>" "<sprint ID>"
   ```

   Fill the metrics, *Effort by register* from the per-register split (skip it if there is only one register), the goals, the known gaps and the carryover. Then run `sprint_record.py goals <records>`: it reads the goals back and names anything that breaks the layout.
6. **Then the readiness half**: `sprint-planning-precheck`, in the same session. You cannot judge readiness to commit without first knowing what closed.
7. **The communications due**, where a project keeps a stakeholder register (`stakeholder-manager`; a project without one has only its owner, whom the close-out already reached):

   ```bash
   python <skills>/stakeholder-manager/scripts/stk.py due --all --root "<the folder holding the projects>"
   ```

   For each one listed: `stk.py audience <register> --id C.n` gives who it goes to, their addresses and the share level. A report going to an `external` audience goes through `reporting`'s `report.py export --comm C.n`, which takes the share level from the register. The user sends it; on their word, `stk.py done <register> --id C.n`. A skipped one is said, not recorded. The `stakeholder-manager` skill holds the rules; never repeat a contact's details in the record.

## Running the sprint retrospective

On the sprint's last day, straight after the close-out. **It assesses how the work was done**: the processes and the tools, not the work itself. Scoping, estimating and prioritising belong to grooming and planning.

1. Run `wbs.py check` on each register. A row closed without a closure note, or a status without its date, is a process finding in its own right.
2. Append the block:

   ```bash
   python <skill-path>/scripts/sprint_record.py retro "<records>" "<sprint ID>"
   ```

3. **Walk the three questions in order**, one table row per point: what went well, what can be improved, what to do differently next iteration. Fill them in live with the user; never pre-fill guesses.
4. **Vote to converge where there is a team**, as a count or as initials. When working solo, leave the column empty; that is correct.
5. **The third question is the one that acts.** Draw it from the improvements with the most votes. A retro that lists everything actions nothing.
6. **Route each improvement**: work on a deliverable goes to the WBS, and an action, risk, issue or decision goes to the RAID register. Write the destination in `Routed to`.

## Running sprint planning

On the next sprint's first day. The close-out and the retro ran the day before.

0. **Check the last sprint's goals were answered.** If the previous record's review left `Achieved` empty, answer it now before setting new goals beside it.
1. **Gather the candidates**: rows with `Horizon` `Next`, committed rows from the sprint that closed that are not `Done`, and the due controls (step 2b).
2. **Build the capacity table**, one row per candidate: its `Estimated Effort (h)` and its register. Skip a child whose parent is also in the set, because the parent's estimate covers it. Size anything with no estimate now. Sum it against the hours the user says are available and record both as they are. Going over capacity can be a deliberate stretch on the no-AI baseline; say so in the record when it is. **This table becomes the record's committed items**, written once.
   - 2a. **Key Deliverables**: take each finding from the precheck's `wbs.py deliverables` to a decision: commit something under it, `rebaseline` it with a reason, or accept the gap and say so. If the precheck did not run, run it now.
   - 2b. **Controls**, if a TSP register is in use: show `tsp.py due` and ask which to commit. The default is three, but the user decides, and retiring dead ones (`tsp.py retire`) is a legitimate answer. A committed control goes into the committed-items table as `control <ID>`. When it is done, it is recorded with `tsp.py done`.
   - 2c. **A `Planned End` already passed on a candidate is a decision, not clean-up**: re-plan it with a `--reason`, or cancel the row with a closure note.
3. **Confirm each committed row is ready**, top priority first. A row committed with a gap is still committed; note the gap so the close-out can say what became of it.
4. **Record the commitment on each row.** For a new commitment: `--sprint-planned <sprint ID> --horizon ""`. For a row carried from an earlier sprint and not Done: `--sprint-carried <sprint ID> --reason "<why it did not finish>"`, so the earlier sprint keeps its carryover. A split's rest is carried the same way; carry its parent too only when the deliverable is promised again this sprint, since a committed parent counts as an item with its children's hours. **A commitment means `Not Started`:** `wbs.py` moves a committed `Portfolio Backlog` or `Funnel` row there itself and says so. **Set the baseline if the row has none**: commitment is the moment it becomes real, it is written once, and `rebaseline` moves it afterwards. Set `Planned End` at the precision the commitment actually has.
5. **Decide two or three iteration goals**, starting from any `draft:` goals the record carries in as `G1`, `G2`…. Each keeps its ID, gets a one-line *Done when* (the test the close-out will judge it against), a *Bet* when it serves a bet or objective from a longer planning cycle (blank otherwise, which is legitimate), and *Carried from* `<sprint ID> <goal ID>` when it continues an earlier goal, reworded or widened included. Mark each committed item's `Goal` with the IDs it serves, and its `Area`. **A goal that closes a parent commits the parent:** when a *Done when* names a WBS parent or key deliverable to close this sprint, commit that row too (step 4), on its own line at `0h`, since its hours are its children's. A parent counts as committed only when it is itself, so otherwise its close is asked as a pull-in. The goals are data a report counts, so keep the ID, the test and the carry out of the goal sentence. Record confidence as a fist of five, per participant.
6. **Write the record**:

   ```bash
   python <skill-path>/scripts/sprint_record.py plan "<records>" "<sprint ID>" --calendar "<conventions file>"
   ```

   Fill in the capacity line, the committed items, the goals (replace each `draft:` with the decided wording or drop it) and the fist of five. Pre-fill nothing the session has not decided.

## Relationship to other skills

- **`sprint-planning-precheck`** is the second half of the close-out. It reads and reports; this skill decides and writes.
- **`wbs-manager`** owns every write to a WBS row. This skill tells it what to write and when.
- **`raid-manager`** owns RAID entries. This skill routes to it.
- **`tsp-manager`** owns control activities. Planning reads `due` and records `done`.
- **A daily routine** can run `sprint_record.py status` each day so a missed ceremony surfaces without being asked for. It reports; it never runs a ceremony.
