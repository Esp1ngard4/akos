# TD.9 — Daily Loop

## Purpose

The two daily routines, morning and evening, and the one record they share.

- **In the evening**, the stand-up reviews the day while it is fresh: what was worked on, which of the day's frogs were not done, what might block tomorrow. It then chooses tomorrow's frogs and closes the day's record.
- **In the morning**, the planner confirms those frogs with a clear head, names what needs attention, and opens the new day's record with what it decided.

A **frog** is the most important thing to complete that day, one to three of them (after Brian Tracy's *Eat That Frog*). It belongs to its day. Every evening the frogs are put down, done or not, and tomorrow's are chosen fresh. A frog that is never cleared becomes a label nobody believes.

**The pairing is the point.** The evening chooses while the day's context is still loaded, and the morning confirms after a night's distance. Each half catches what the other cannot. One is a tool with two skills, not two tools, because the record is what joins them. The morning's decision is the one thing the evening cannot otherwise see: a frog swapped in the morning looks, by evening, exactly like a frog not done.

**The evening is also a watchdog.** A routine that runs every day is where a missed fortnightly ceremony surfaces by itself. Each evening the stand-up asks the sprint records whether a ceremony is due, and raises one before proposing frogs. It reports and hands over; it never runs the ceremony.

## Status: In Progress

| | |
|---|---|
| The loop | Runs daily on real work in its original setting, where frogs were task-tracker labels and the evening read a calendar |
| Register-only, as shipped here | **Not yet used on real work.** Walked through once on a scratch workspace: a first morning, a day's work committed, and an evening that closed the record and chose the next frogs. It found three gaps, now fixed in the skills. The first morning was treated as a missed evening. The evening had nothing to propose once the sprint's committed work was done. And the register's date form, `2026-Oct-2`, has to be matched as written |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.9 Daily Loop/` | What the loop is for and why; how to adapt it |
| `standup-facilitator` | `standup-facilitator/SKILL.md` | The evening. **Owns the record's template** and closes the record; also takes notes during the day |
| `morning-planner` | `morning-planner/SKILL.md` | The morning. Opens the record and writes only its `### Morning` |
| Your day records | wherever you keep them; found by `kind: day-record` | **Source of truth**: one Markdown file per day |

**Dependencies, all optional.** `wbs-manager` (TSP.1) lets both halves read the work in flight. `sprint-facilitator` (TSP.8) provides the ceremony check. `notebook-capture` (TSP.7) takes the diary offer. Without any of them, the loop still runs on git and the user's own account of the day.

## What the skills cover (and this document doesn't repeat)

`standup-facilitator/SKILL.md` owns the evening's steps, the record template, and the rules for what the record keeps. `morning-planner/SKILL.md` owns the morning's steps and the day's shape. This document covers why the loop is shaped this way, how to adapt it, relationships and history.

## Design decisions

- **The record is the product; the conversation is scaffolding.** The screen shows only what must be decided now. The record keeps only what no register already holds. Git holds what changed, the WBS holds status, effort and dates, and RAID holds the risk. A record that restates them writes the day out twice and is read once. What is left is what was believed and turned out wrong, and why a premise was rejected. A stand-up record that ran to ninety lines by restating commit messages is where this rule came from.
- **`status: closed`, not the file's existence, is the evidence the stand-up ran.** The morning opens the record, so a file can exist for a day whose evening never ran.
- **"What did I do today" is read from where the work leaves a trace.** A task tracker sees only work tracked as tasks. Building a tool or writing a document leaves no trace there. One day that took a governance document through four revisions and published a tool showed zero events in the tracker's activity log, so a stand-up reading only the tracker reports an empty day and is confidently wrong. Git, the registers and the day's own notes are read first.
- **Risks are a plain question, not a scan.** Reading every RAID register each evening turns a ten-minute routine into an assessment. The scan belongs to a weekly review; the stand-up just asks.
- **Inboxes are reminded, never read.** Automating triage is a bigger and riskier problem than the rest of the routine put together.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** The loop was built where frogs were labels in a task tracker, the evening read three calendars and blocked time on one of them, and personal trackers were reminded at the end. The version here strips all of that out, because each person and team uses different tools in different ways. **The tools are named here; the instructions for using them belong in your copy of the skills.** Edit them. The installer records the edit (`status --check`, `accept`) and merges upstream changes around it (`update`). See TD.4.

### A calendar

**Where it plugs in:** the day's shape (morning step 1, evening step 5), and time for each frog.

**What it takes over:** the one question about what is already fixed, which becomes a read. It also adds a step: for each frog with no time on the calendar, propose a block, and create it only once the user approves it. A plan becomes real by being blocked, not by being decided.

**What to watch for:**

- **Read every calendar where events actually live.** The first version read one account that turned out to be empty, while the real events sat elsewhere. Resolve calendars by listing them, not by assumption.
- **Write to one calendar only**: the one that holds the person's own planned time. **Never write to a calendar of commitments with other people**, even with permission. That is a category rule, not a permissions accident.
- **Find a recurring event by ID, not by weekday**, because an occurrence can be moved.
- **The event that triggers the routine carries the trigger and the agenda, never the procedure.** Keep its text under version control and publish it to the calendar. A step copied into an event description drifts silently.

### A task tracker

**Where it plugs in:** the frogs (as a label), what is in flight, what must be done today, and what finished today.

**What to watch for:**

- **Clear every frog label every evening, done or not.** A label nothing removes decays silently; one setup found four of five frog labels stale.
- **"Finished today" is a question about when, not about state.** A label meaning "finished, awaiting review" can sit on a task for a whole sprint, so pulling everything with that label reports a fortnight as a day. Read the tracker's activity log for today's events.
- **Filter queries fail silently.** A label misspelt matches nothing and returns an empty list that looks like a quiet day. In many query languages `&` binds tighter than `|`, so `p1 | p2 & tomorrow` means something other than it reads. Run a filter before relying on it.
- **Query by label, never by a saved filter whose name carries a date.** The name rolls over every sprint and the query breaks quietly.
- **Keep out-of-scope work out of every pull, not just most.** If work for an employer shares an account with personal work, each pull must exclude it. An activity event carries the project but not the labels, so a label filter alone lets it through.

### Inboxes

The reminder can name them: "email, chat, the paper notebook". Keep it a reminder.

### Anything before the morning plan

A routine that comes first (exercise, priming, reading) belongs before `morning-planner` and outside it. If you want it in the record, add a line to your copy of the morning skill, not a step.

### A weekly review

Not shipped in AKOS yet. Where one exists, the evening checks its records the same way it checks the sprint's, and says in one line when none has been recorded for a week.

## How it is tested

`tests/smoke_test.py` installs both skills into an empty project and checks the record contract the two share. The morning creates the record from the template the stand-up owns, so both must name the same `kind`, the same `status` values and the same four sections. It also checks the ceremony command the stand-up names exists in TSP.8.

What is **not** tested is whether the agent drafts a good day or chooses good frogs. No test asserts that, and none can.

## Relationship to other tools

- **TSP.8 Sprint Ceremonies**: the evening runs `sprint_record.py status` and raises a ceremony that is due. The sprint decides what the fortnight holds; the loop decides what each day holds.
- **TSP.1 WBS Register**: the work in flight, and the rows a frog cites.
- **TSP.7 Notebook Manager**: takes the evening's diary offer. The diary is for reflections and memories, not for the stand-up.
- **TSP.3 TSP Register**: row 9.

## Maintenance

**Daily:** the routines themselves.

**On any change to the routine:** what it is and why changes here; how it runs changes in the skill that owns the step. The record template changes only in `standup-facilitator`.

## Open items

| Item | Detail |
|---|---|
| Register-only mode unexercised on real work | See *Status*. A real week run this way is what moves the tool to `Implemented` |
| No weekly review in AKOS | The risk scan the stand-up deliberately leaves out has no home here yet |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-02 | Published as TSP.9. The morning and evening routines as one tool with two skills and a shared day record, run on git and the registers alone. Calendar time blocks, tracker labels and inbox reads are described as adaptations rather than shipped. |
