# TD.12 — Action Tracker

## Purpose

A team's shared list of small actions under one piece of work: what comes out of a working session (a supplier check-in, a cross-team sync, a client review) and someone has to do. One Markdown file per piece of work, walked top to bottom when the group meets, with a few lines of narrative state above tables of actions.

It fills the gap between the two registers. The **WBS** (TSP.1) holds deliverables and schedule; a breakdown into twenty small actions would swamp it without adding anything a plan needs. The **RAID register** (TSP.2) holds governed items, each with a review date and a consequence if missed; most of these actions have neither and will not survive the month. Without a tracker, those actions live in meeting notes nobody re-reads, or in each person's own task list, where nobody else can see them.

**An action tracker is not a task tracker.** Elsewhere in AKOS, "task tracker" means the tool a team runs its committed work in (Jira, Azure DevOps, a board). An action tracker is a document, shared with whoever is in the sessions, including people who have no access to that tool.

## Status: In Progress

| | |
|---|---|
| The tracker's shape | Comes from a team setting with a ticketing tool, through a personal version where it held what other people owed: contractors, family, colleagues on other systems |
| As shipped here | **Not yet used on real work.** Walked through once on a scratch workspace: a project with a Deliverable, a Feature and a RAID Issue; a tracker on the Feature, filed in its execution folder, and one on the Issue, in its `AuxMat/` folder with `Has AuxMat` set; a session's actions added, rows updated, one closed; a session prepared; and the weekly review reading both trackers. It found four gaps, now fixed in the skill. A Latest update had no date, so "gone quiet since the last review" could not be judged. A `TBD`'s checkpoint could sit anywhere, and one sat in a row's update where no scan would find it: it now goes in the Due date cell. The weekly review missed someone else's `TBD` with no checkpoint at all, the most stalled kind of row. And the Closed actions table had no Status, so a dropped action looked like a delivered one |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.12 Action Tracker/` | What the tracker is for and why; how to adapt it |
| `action-tracker-manager` | `action-tracker-manager/SKILL.md` | The operations: create, add, update or close, prepare a session, review |
| Template | `action-tracker-manager/templates/action-tracker.md` | The tracker's skeleton, copied on create |
| Conventions | `action-tracker-manager/references/conventions.md` | The meta block, section codes, action IDs, dates, status, filing |
| Your trackers | in the support folder of the WBS row or RAID item each serves; found by their `action-tracker-meta` block | **Source of truth**: one Markdown file per piece of work |

**No scripts, no register, no dashboard, no index.** Dependencies: `wbs-manager` (TSP.1) and `raid-manager` (TSP.2) for the anchors and their folders, both optional.

## What the skill covers (and this document doesn't repeat)

`action-tracker-manager/SKILL.md` owns the operations, the boundaries as they are applied, the filing table and the discovery steps; `references/conventions.md` owns the rules for codes, IDs, dates and status. This document covers why the tool is shaped this way, how to adapt it, relationships and history.

## Design decisions

- **Markdown, not a JSON register.** Every other register in AKOS is JSON written through a script, because every write goes through a script anyway. A tracker inverts that: it is edited live in a session, sometimes by someone other than its owner, and the document itself is what gets shared. A format only a script can write would remove the property the tool exists for. The costs are real and accepted: no rollup across trackers, no generated view, next-ID allocation is "read the table". All are affordable because a tracker is one small file read end to end every time it is touched.
- **No checker script either.** The rules (an ID never reused, a `TBD` always with its checkpoint) are checked by the agent applying the skill, and by the people reading the tracker. A checker would be the first step back towards a format only a script can trust.
- **Every action agreed in the sessions, whoever owes it.** The personal version split the work: a task manager held what its owner owed, the tracker what others owed. In a team that split fails, because everyone is someone else's other person. The tracker is the shared view; each person's own list is their business, and a copied row says so.
- **The owner is named, never assumed.** The tracker's `owner` runs the sessions; each row's Owner is the person who owes it. Another skill asking what waits on someone else asks it of the `owner`.
- **Filed with its work, so nothing has to say where it is.** A tracker always serves one WBS row or one RAID item, and lives in that row's support folder or that item's `AuxMat/` folder. Anyone looking at the work finds it there. An index of trackers, in the Artifact Register or anywhere else, would be a second answer to a question the anchor already answers, and would drift.
- **Three boundaries, each a promotion path.** A row that acquires a review date and a real consequence becomes a RAID Action, leaving a pointer. A section that starts producing deliverables or acquires a schedule becomes a WBS row, keeping its code. A section anchored to a WBS row never restates its status: two places holding a status is two answers, and the tracker is the one that goes stale.
- **Section codes are independent of anchors.** A code is a local key, assigned once; a WBS anchor is a separate field. That is what lets a section gain an anchor without renumbering its actions.
- **Dates that can be scanned.** Every Latest update opens with its date, and a `TBD` carries its checkpoint in the Due date cell. Both came out of the dry run: without them, the two most common ways an action dies (nobody touches it, or its date is never set) cannot be found by reading the tables.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** The tracker is shipped as a document alone, because each team shares work in its own way. **The tools are named here; the instructions for using them belong in your copy of the skill.** Edit it. The installer records the edit (`status --check`, `accept`) and merges upstream changes around it (`update`). See TD.4.

### A personal task manager

**Where it plugs in:** operation 2, adding an action.

**What it takes over:** a row someone also wants in their own list gets a task carrying `AT: <CODE>-NN` as its back-reference, and the row says it is tracked there.

**What to watch for:** left unchecked, the tracker becomes a second task list for its owner, and the shared view stops being shared. The tracker holds the actions agreed with others; a person's private to-dos stay in their own list.

### A team ticketing tool

**Where it plugs in:** operations 2 and 3, for rows owned by people who work in the tool (Jira, Azure DevOps, a board).

**What it takes over:** those rows are mirrored as tickets, with the ticket key in the row.

**What to watch for:** **name one of the two as the source of truth for status**, in your copy of the skill. Two places holding a status is two answers. Usually the ticket holds the status and the tracker's row holds the key and a dated Latest update.

### Meeting notes

**Where it plugs in:** operation 2. TSP.7 (Notebook Manager) keeps one note per meeting; a meeting's actions are the tracker's natural input.

**What it takes over:** nothing is wired in. After a meeting, its actions are added to the tracker and the meeting is named in Update history. The meeting note is not edited.

### Sharing the file

A tracker is shared wherever the team already works: a repository, a shared folder, a wiki that renders Markdown. Who can edit it is that place's permission, not the tool's.

## How it is tested

`tests/smoke_test.py` installs the skill into an empty project and checks its layout: the template holds every meta key, every section, the five status values and the Status column in Closed actions; the conventions state the ID, date and checkpoint rules; and the weekly review reads the trackers in its waiting-on-someone step.

**Create, update and close are exercised in the walk-through**, recorded under *Status*, since there is no script for a test to run. What is **not** tested is whether the agent applies the rules well: whether a section is the right size, or a row should have been promoted. No test asserts that, and none can.

## Relationship to other tools

- **TSP.1 WBS Register**: the anchor row, its support folder, and where a section goes when it is promoted.
- **TSP.2 RAID Register**: the anchor item and its `AuxMat/` folder, and where a row goes when it acquires a review date and a consequence.
- **TSP.11 Weekly Review**: reads every active tracker for rows owed by others that are overdue or have no checkpoint, three at most, and chases through this skill on a yes.
- **TSP.7 Notebook Manager**: meeting notes, the tracker's natural input. Described, not wired in.
- **TSP.5 Artifact Register**: deliberately not used for trackers; see *Design decisions*.
- **TSP.3 TSP Register**: row 12.

## Maintenance

**In every session:** close on the day. A tracker's usefulness comes from its state being true; finished rows left in the open tables are the fastest way to lose that.

**Periodically:** the skill's review operation. Look specifically for rows a person owns that never reached their own list when they needed to, and for sections that have quietly acquired a schedule. Both are the tool leaking into its neighbours.

**On any change to the tool:** what it is and why changes here; how it runs changes in the skill.

## Open items

| Item | Detail |
|---|---|
| Unused on real work | See *Status*. A month of real sessions run from a tracker is what moves the tool to `Implemented` |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-26 | Published as TSP.12. One skill, a template and its conventions; no scripts. Re-scoped for a team: every action agreed in the sessions whoever owes it, the owner named rather than assumed, filed with its anchor and indexed nowhere. A personal task manager, a ticketing tool and meeting notes are described as adaptations rather than shipped. The dry run added dated updates, the checkpoint in the Due date cell, the weekly review's check for a missing checkpoint, and a Status column for closed actions. |
