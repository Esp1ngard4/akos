# TD.11 — Weekly Review

## Purpose

The weekly level of the loop, between the day and the sprint.

- **The sprint ceremonies** (TSP.8) govern the project work: what the fortnight holds, and whether it was delivered.
- **The daily loop** (TSP.9) runs the day: its frogs, its record.
- **The weekly review** covers what belongs to neither: work beyond the sprint that is falling due, entries waiting on someone, last week's loose ends, the week ahead placed against what is due and what needs preparing, and, mid-sprint, whether the sprint is on track, with the risk scan the stand-up deliberately leaves out.

**It checks priorities; it never sets them.** The sprint sets them. The review asks whether the week makes room for them, and routes what it finds to where a ceremony will look.

## Status: In Progress

| | |
|---|---|
| The review | Runs weekly on real work in its original setting, where the work beyond the sprint lived in a task tracker and the week was placed on a calendar |
| Register-only, as shipped here | **Not yet used on real work.** Walked through once on a scratch workspace: a project six days into its sprint, a week of day records with one evening left open and a Saturday with none, two rows outside the sprint falling due, a risk on a sprint row and an action waiting on someone else. The review found all of them and wrote a thirty-line record. It found three gaps, now fixed in the skill. Nothing said who "the user" is when deciding what waits on someone else: it is the register's author, and the review asks when none is set. A project whose planning never generated a sprint update got one from the refresh, with a summary to write that belongs to planning. And a day off was counted as a missed stand-up |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.11 Weekly Review/` | What the review is for and why; how to adapt it |
| `weekly-review-facilitator` | `weekly-review-facilitator/SKILL.md` | The review's steps. **Owns the week's record template** |
| Your weekly records | wherever you keep them; found by `kind: weekly-record` | **Source of truth**: one Markdown file per review |

**Dependencies, all optional.** `daily-loop-facilitator` (TSP.9) writes the day records the review reads. `sprint-facilitator` (TSP.8) provides the goals and the sprint record's `Noticed`. `wbs-manager` (TSP.1) and `raid-manager` (TSP.2) hold the work and the risks. `action-tracker-manager` (TSP.12) holds the small actions agreed with others. `reporting` (TSP.10) refreshes the sprint update for the sprint check. `notebook-capture` (TSP.7) takes the closing offer. Without any of them, that step is skipped and the record says so.

## What the skill covers (and this document doesn't repeat)

`weekly-review-facilitator/SKILL.md` owns the steps, the record template, and the rules for what the record keeps and what the screen shows. This document covers why the review is shaped this way, how to adapt it, relationships and history.

## Design decisions

- **A level of its own.** The daily stand-up is kept to ten minutes by leaving out anything that needs a table, a scan or a decision about the week. The sprint ceremonies run once a fortnight and look at the sprint. Between them, things go stale: an entry waiting on someone with nothing to bring it back, a date outside the sprint that passes unnoticed, a risk nobody looked at since planning, a deliverable three weeks out that needs preparing now. The weekly review is where those surface.
- **The sprint check runs mid-sprint only.** On a sprint's first day, the close-out and planning covered the sprint the day before; the review reads the new plan instead of checking an old one.
- **Beyond the sprint is read from the registers.** In its original setting this was a task tracker's inbox, overdue list and waiting-fors. Here the same questions are asked of the registers: rows outside the sprint whose planned end has come, RAID entries past their review date or waiting on someone else. The action trackers are read the same way: rows owed by others that are overdue, or `TBD` with no checkpoint or a passed one, three at most. A row falling due is never re-dated as tidying: it is pulled in with its effect, re-planned as a new promise, or left with a reason.
- **The record is the product; the conversation is scaffolding.** The record keeps only what no register already holds. Its date is the evidence the review ran, which the daily loop's evening reads.
- **Findings are routed, not acted on.** A finding goes to the sprint record's `Noticed`, a chase to a RAID log entry, a pull-in through `wbs-manager`, each on a yes. The review never runs a ceremony or edits a register directly.
- **Inboxes and personal trackers are reminded, never read.**

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** The review was built where the work beyond the sprint lived in a task tracker, the week was placed as time blocks on a calendar, and a personal goal tracker was reminded at the end. The version here strips all of that out, because each person and team uses different tools in different ways. **The tools are named here; the instructions for using them belong in your copy of the skill.** Edit it. The installer records the edit (`status --check`, `accept`) and merges upstream changes around it (`update`). See TD.4.

### A task tracker

**Where it plugs in:** step 2b, beyond the sprint.

**What it takes over:** the tracker's inbox (each item needs a home), its overdue list (each item done, re-dated as a new promise, or dropped with a comment), and its waiting-fors (name the ones with no date, which nothing will bring back, and those due in the coming week).

**What to watch for:**

- **An overdue date changes only through a decision about the commitment.** Clearing or pushing a date to tidy the list hides a broken promise.
- **Keep out-of-scope work out of every count.** If work for an employer shares the tracker with personal work, every pull must exclude it.
- **Filter queries fail silently.** Run a filter before relying on it; an empty result looks like a quiet week.

### A calendar

**Where it plugs in:** step 2a (last week's one-off events, and whether any left an action not yet captured) and step 4 (the free time on each day ahead, what collides, and events up to three weeks out that need preparing).

**What it takes over:** step 4's plan becomes time blocks, each with a day, a time, a length and the work it is for, created only once the user approves that block.

**What to watch for:**

- **Read every calendar where events actually live**, and resolve them by listing them, not by assumption.
- **Write to one calendar only**: the one that holds the person's own planned time. **Never write to a calendar of commitments with other people**, even with permission. That is a category rule, not a permissions accident.
- **Don't fill the week.** Blocks are for the work that must happen this week; the evening still chooses each day's frogs.

### Inboxes

The reminder can name them: "email, chat, the paper notebook". Keep it a reminder.

### A goal tracker

If goals are kept outside the registers, step 5 reminds the user to update it. Keep it a reminder.

## How it is tested

`tests/smoke_test.py` installs the skill into an empty project and checks its layout: the record template holds every section and `kind: weekly-record`; each `sprint_record.py` and `report.py` command the skill names exists in TSP.8 and TSP.10; and the daily loop's evening names the weekly check.

**The walk-through on a scratch workspace** is recorded under *Status*. What is **not** tested is whether the agent judges a goal's state well or plans a good week. No test asserts that, and none can.

## Relationship to other tools

- **TSP.9 Daily Loop**: writes the day records the review reads, and its evening says when no weekly record is newer than a week. The risk scan the stand-up leaves out happens here.
- **TSP.8 Sprint Ceremonies**: the goals, and the `Noticed` table where findings go. The review never runs a ceremony.
- **TSP.1 WBS Register** and **TSP.2 RAID Register**: the work beyond the sprint, the committed work, and the risks.
- **TSP.12 Action Tracker**: the actions owed by others, read in *Waiting on someone*; a chase goes through its skill.
- **TSP.10 Reporting**: the sprint update, refreshed for the sprint check.
- **TSP.13 Stakeholder Register**: the communications overdue and the engagement gaps with no action, read in the sprint check, three lines at most.
- **TSP.7 Notebook Manager**: takes the closing offer.
- **TSP.3 TSP Register**: row 11.

## Maintenance

**Weekly:** the review itself.

**On any change to the review:** what it is and why changes here; how it runs changes in the skill.

## Open items

| Item | Detail |
|---|---|
| Register-only mode unexercised on real work | See *Status*. A real month of weekly reviews run this way is what moves the tool to `Implemented` |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.2 | 2026-10-27 | **The sprint check reads the stakeholder registers** (TSP.13): communications overdue and stakeholders below the engagement wanted with no action, three lines at most, silent when there are none. Read only; sending stays with the close-out. It replaces the *A stakeholder register* adaptation, now that one ships. |
| v1.1 | 2026-10-26 | *Waiting on someone* also reads the action trackers (TSP.12): rows owed by someone other than the tracker's owner that are past their due date, or `TBD` with no checkpoint or a passed one, three at most, the missing checkpoints first. A chase is the row's Latest update, through `action-tracker-manager`. |
| v1.0 | 2026-10-26 | Published as TSP.11. The weekly review as one skill with its own record, run on the day records, the sprint records and the registers alone: beyond the sprint read from the registers, the sprint check mid-sprint only, findings routed rather than acted on. A task tracker, a calendar, inboxes and a goal tracker are described as adaptations rather than shipped. |
