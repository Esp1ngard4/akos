# TD.8 — Sprint Ceremonies

## Purpose

The four ceremonies that run a sprint: **backlog grooming**, the **sprint close-out**, the **sprint retrospective** and **sprint planning**. Each one commits, refines, closes or improves the sprint and leaves a record. Two skills run them, and one script writes the record.

It is the tool that uses the registers together. `wbs.py metrics`, `deliverables`, `refined` and carried sprints, RAID's `WBS Ref` and `tsp.py due` each answer a question a ceremony asks. Without the ceremonies, nothing asks those questions on a schedule.

**The sprint lives in the registers.** A WBS row is staged by its `Horizon`, committed by its `Sprint Planned`, in flight by its Status and finished by its closure note. As shipped, the ceremonies need nothing else: no task tracker and no calendar. Most teams use both, each in its own way, so this document says where those tools plug in rather than pretending to plug them in for you (*Adapting it to your tools*).

## Status: In Progress

| | |
|---|---|
| The ceremonies | Run fortnightly on real work in their original setting, where sprint state sat in a task tracker and the triggers on a calendar |
| Register-only, as shipped here | **Not yet used on real work.** Walked through once on a scratch workspace: a sprint groomed, closed out, prechecked and reviewed in a retro, then the next one planned with spillover carried in. It found that a first `Planned End` was refused without a `--reason`, and that `refined` never checked the description; both fixed in `wbs.py` (TD.1 v1.5). Estimates still lack a flag (*Open items*) |
| `sprint_record.py` | Ported unchanged in behaviour from the original. Sprint windows now come from the sprint calendar |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.8 Sprint Ceremonies/` | What each ceremony is for, when it runs, what it decides; how to adapt it |
| `sprint-facilitator` | `sprint-facilitator/SKILL.md` | Runs all four ceremonies |
| `sprint_record.py` | `sprint-facilitator/scripts/` | Writes the sprint's record (`plan`, `review`, `retro`) and reads it back (`status`). Standard library only; takes the records folder as an argument |
| Record layout | `sprint-facilitator/references/record-layout.md` | The record's sections and the script's refusals |
| `sprint-planning-precheck` | `sprint-planning-precheck/SKILL.md` | The readiness half of the close-out. It reads and reports, and never writes |
| Your sprint records | wherever you keep them; the skill finds them by shape | **Source of truth for the record**: one Markdown file per sprint |

**Two skills, one tool.** The precheck is the second half of the close-out. It is a separate file because it is asked for at a different moment ("are we ready?"), not because it governs something different. TSP.3 is the precedent for one tool with two skills.

**Dependencies.** `wbs-manager` (TSP.1) is required. `raid-manager` (TSP.2) and `tsp-manager` (TSP.3) are optional, and each ceremony skips the step whose tool is absent. The installer does not resolve dependencies, so install them together:

```bash
python install.py add sprint-facilitator --into <project>
python install.py add sprint-planning-precheck --into <project>
python install.py add wbs-manager --into <project>
```

## What the skills cover (and this document doesn't repeat)

`sprint-facilitator/SKILL.md` owns how each ceremony is run, step by step, and the defaults (grooming thresholds, controls per sprint, effort sizes). `sprint-planning-precheck/SKILL.md` owns what "ready for planning" means in practice. This document covers why the ceremonies are shaped the way they are, the record, the cadence, how to adapt them, relationships and history.

## The ceremonies

Their order is not arbitrary: each hands the next something it needs.

| | When | Produces |
|---|---|---|
| **Backlog grooming** | ~4 days before planning | Ready candidates, and two figures in the record's draft footer |
| **Sprint close-out** | the sprint's last day | The record's `Review` block, then a readiness report |
| **Sprint retrospective** | the sprint's last day, after the close-out | The record's `Retrospective` block |
| **Sprint planning** | the next sprint's first day | The next sprint's record, opening with its `Planning` block |

**The close-out and the retro sit inside the sprint they close, and both come before planning.** The retro decides how the work should change. If planning ran first, it would commit before the retro had decided anything.

### Backlog grooming

**Purpose:** refine enough work that the next sprint can be planned without stopping to define things.

**An item is ready when it states three things:** the problem or opportunity it addresses, what good would look like when it is done, and an educated guess at the effort. Any of the three can be a guess from past sprints, written down as such, and the sprint tests it. **The solution space is worked out during the sprint**: the specs, the design and the breakdown. When the people who refine the work are the ones who do it, there is no handover, so working it out days ahead buys nothing and costs two context switches. A team that does hand work over (refined by one group, built by another) may need more here, and should say so in its copy of the skill.

**Done-ness** is two figures over the record's `Next sprint - draft`:

- **Completion**: refined ÷ listed.
- **Sufficiency**: the estimates on ready items, summed, against a minimum and a target set once for the team. The defaults (20h and 40h) fit one person's evenings over a fortnight. These are absolute figures, not a fraction of each sprint's capacity, because a floor that moves with capacity is not a floor.

**Estimates use the no-AI baseline.** Work is sized as if agent support were not there. The agent is the accelerator on top, so the scale does not drift and the multiplier stays visible sprint over sprint. Delivering well past the estimate is expected.

**Record:** none of its own. A record asserting that a session happened proves nothing. A record of what got refined can be checked against the registers, so grooming writes only to the draft and to `Noticed`.

### Sprint close-out

**Purpose:** establish what the closing sprint actually delivered, before committing to anything new. Its capacity, its carryover and its unmet goals are inputs to the sprint that follows.

**Cadence:** the sprint's last day, before the retro, and not on planning day. Its second half checks readiness, and a check with no gap before planning leaves no time to act on what it finds.

**It answers four questions:**

- **What did we deliver?** Velocity, completion against commitment and cycle time, computed by `wbs.py metrics` rather than recalled, with effort per register.
- **Did we meet the iteration goals?** Each goal is answered. A goal nobody marks is a commitment nobody checks.
- **What carries over, and what is dropped?** Each unfinished row is genuine spillover, quietly abandoned, or finished and never closed.
- **Is it ready to plan?** This is the precheck: the candidate pool against the thresholds, the gaps, the deliverables and the controls. **A gap is a flag, never a veto.**

**What it is not:** it inspects the *result*. How the work was done is the retro's question. *Scrum calls this the Sprint Review. The name is not borrowed because that event is a stakeholder demonstration, and only its inspect-the-outcome half is here. A team that demonstrates to stakeholders adds that to its copy.*

### Sprint retrospective

**Purpose:** take time, at a regular interval, to assess what is working, what is not, and how to improve.

**Three questions:** what went well, what can be improved, and what we will do differently. The third is the one that acts, drawn from the improvements that matter most. A retro that lists everything actions nothing.

**Every improvement worth acting on gets a destination**: the WBS for work on a deliverable, the RAID register for an action, risk, issue or decision. An improvement left only in the record is not looked at again.

### Sprint planning

**Purpose:** focus the next sprint on the work that delivers the most value.

**It decides:**

- **What is committed**, as a prioritised list, top first, from grooming's ready candidates and the previous sprint's spillover.
- **Capacity**: hours available against hours planned, recorded as they are. Going over can be a deliberate stretch on the no-AI baseline.
- **Two or three iteration goals.**
- **Confidence**, as a fist of five per participant.
- **Controls**: the due control activities to commit, when a TSP register is in use.

**The WBS baseline is set at commitment**, because that is when a commitment becomes real, and it is what the close-out measures slip against. A row already committed to an earlier sprint is *carried* into this one, with a reason, rather than re-pointed, so the earlier sprint keeps its carryover.

## The record

One Markdown file per sprint, named for its ID. It holds the sprint as one arc: `Planning`, `Review` and `Retrospective` blocks, each written once, in that order. After them come three sections that stay open all sprint:

- **`Noticed`**: anything worth acting on, written when it is noticed. Each row records *what* and *where it was routed*, never the item itself. A row with an empty `Routed to` is an admission.
- **`Next sprint - draft`**: the shortlist for the sprint after, accumulated as the sprint runs and drained at grooming. It is the **denominator** that makes grooming measurable. Without a named list the pool has no edge, and no figure can come out of it.
- **`Draft goals`**: goals worth proposing, written whenever they occur. Planning carries them in marked `draft:`, and the session decides.

**Records are found by shape, not by a configured path**: a file named for a sprint ID whose first line is `# Sprint `. The folder can move without anything breaking.

## The cadence

The sprint ID is `S<YY>.Q<N>.<X>`. A sprint belongs to the quarter it starts in, and the calendar is seeded from a real sprint start date, not from 1 January. `wbs-manager` (TSP.1, *Sprints*) defines the convention and seeds the calendar. **The ceremonies own the cadence; the registers import it.**

**One project or several, the same mechanism.** A team usually runs one project, so its sprint spans one register. A person often runs several projects, and the sprint spans all of them, because capacity belongs to the person, not to any one project. Every command takes one register or several. Totals come first and the per-register split sits underneath. Registers whose calendars disagree about a sprint are refused, which is what a shared cadence buys.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** These ceremonies were built where sprint state sat in a task tracker and the triggers on a calendar. The version here strips both out, because each team uses different ones, and uses them differently enough that no setting could cover it. **The tools are named here; the instructions for using them belong in your copy of the skill.** Edit it. The installer is built for this: `install.py status --check` flags the edit, `accept` records it, and `update` three-way merges upstream changes around it (TD.4). An adaptation is then a recorded divergence, not a fork by accident.

### A task tracker

**Where it plugs in:** grooming (where new work is created and staged), planning (where commitments are made), the close-out (what finished) and the precheck (a fourth place refinement can live).

**What it takes over:** usually the in-sprint state, meaning who is doing what today and what is finished. Rows stay the deliverables, and tasks become the operational work under them, one row to many tasks.

**What to watch for:**

- **State in two places drifts.** Decide which is the source for each fact, and check the other against it at every close-out (TD.1, *Reconciling with a task tracker*). Report disagreements; never sync silently.
- **A task cites its row**, by the row's stable `ID`, never its `Code`. A task that should not be on the roadmap says so (`WBS: n/a — <reason>`), or the same question comes back every sprint.
- **Don't close finished tasks immediately.** Mark them finished, and keep them visible until the close-out has reviewed them and written the closure. Most trackers hide a completed task, and work that cannot be seen cannot be reviewed.
- **Mirror the vocabulary, not the data.** If the tracker has labels for "next sprint" and "sprint after", give them the meaning the WBS `Horizon` already has, so the two systems speak one language.
- **Goals can live in the tracker** as tasks titled with the sprint ID, so the close-out can find and close them.

### A calendar

**Where it plugs in:** knowing when each ceremony is scheduled, and finding capacity at grooming and planning.

**What it takes over:** the trigger. A recurring event is what reminds people a ceremony is on.

**What to watch for:**

- **An event carries the trigger and the agenda, never the procedure.** A calendar event is the one artifact nothing can check: it is not in version control and no validator reads it, so a stale step there fails silently at the moment someone relies on it. Keep the event's text in a file under version control, and treat the calendar as where it is published.
- **Find events by ID, not by weekday.** An occurrence can be moved.
- **The calendar says what was scheduled; the record says what happened.** Keep `sprint_record.py status` as the check that something was missed. A recurring event announces nothing once it has passed.
- **Never write to a calendar that holds other people's commitments.**
- **Check any date written through a natural-language parser**, because some shift dates silently.

### A daily routine

A daily routine that runs `sprint_record.py status` makes a missed ceremony surface without anyone asking for it. That is the second control after the calendar. TSP.9 does this.

## Naming conventions

- **Records:** `<sprint ID>.md`, ID alone. The heading carries the dates as a visual aid.
- **Items in a record** are qualified by scope when a sprint spans several registers (`Atlas#12`). An ID is unique within a register, not across them.

## How it is tested

`tests/smoke_test.py` exercises `sprint_record.py` the way a new user would. It seeds a calendar, plans a sprint with the heading dated from the calendar, then runs `status` before, at and after the sprint's end. It appends the review and retro, checks that ceremony blocks land ahead of the living sections, carries a draft goal into the next sprint, and confirms every refusal: planning twice, a review after a retro, a ceremony on a sprint never planned, and a calendar with no sprints.

It also checks that every `wbs.py` and `tsp.py` command the two skills name actually exists, so a command renamed in another tool fails here rather than halfway through a ceremony. It installs both skills and `wbs-manager` into an empty project, the way *Components* says to.

What is **not** tested is whether the agent runs a ceremony well. No test asserts that, and none can. One full cycle was walked through on a scratch workspace before release (*Status*).

## Relationship to other tools

- **TSP.1 WBS Register**: the source of the sprint's state and figures.
- **TSP.2 RAID Register**: where the retro routes actions, risks, issues and decisions, and what grooming's `refined --raid` reads.
- **TSP.3 TSP Register**: planning commits due controls from it; row 8 registers this tool.
- **TSP.4 Tool Installer**: installs the skills and keeps an adapted copy reconcilable with upstream.
- **TSP.9 Daily Loop**: runs `status` each evening and raises a ceremony that is due. It reports and hands over; it never runs one.

## Maintenance

**Each sprint:** the ceremonies themselves.

**On any change to a ceremony:** what it is and why changes here; how it is run changes in the skill.

## Open items

| Item | Detail |
|---|---|
| Register-only mode unexercised on real work | See *Status*. The first real sprint run this way is what moves the tool to `Implemented` |
| Estimates and acceptance criteria have no `wbs.py` flag | Grooming sets them as plain field edits. A flag would let the register's rules apply to them as well |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.1 | 2026-10-02 | The two `wbs.py` gaps the dry run found are fixed at the source (TD.1 v1.5): a first `Planned End` needs no reason, and `refined` checks the description. The workarounds the skills carried for both are gone. |
| v1.0 | 2026-10-02 | Published as TSP.8. The four ceremonies run on the WBS, RAID and TSP registers alone; a task tracker and a calendar are described as adaptations rather than configured. `sprint_record.py` reads sprint windows from the sprint calendar. |
