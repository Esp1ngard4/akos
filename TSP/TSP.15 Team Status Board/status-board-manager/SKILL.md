---
name: status-board-manager
description: Runs a team's status board (TSP.15 Team Status Board) - one Excel workbook per sprint, beside the WBS, where the team updates the status of its own work itself or through Copilot in Excel - and its consolidation into the WBS by the product manager. Use whenever the user wants the sprint's board set up, asks to consolidate the board or bring the team's status into the WBS, asks what the team has updated, or a commitment changed in the WBS mid-sprint (a pull-in, a carried split, a cancellation) and the board must show it; and when sprint planning, the weekly review or the close-out reach their board step. Not for the WBS itself (wbs-manager), the sprint ceremonies (sprint-facilitator), or a team that works in the WBS only, which has no board.
---

# Status Board Manager (TSP.15)

A team that shares a WBS updates its status on a board it can edit itself; the product manager brings the board into the WBS. **The WBS keeps one writer: the product manager, through the agent.** The board is the team's; the agent writes it only at the three moments below, and never decides a change in the WBS on its own.

## Requirements

Python 3, standard library only. `wbs-manager` installed beside this skill. `<skills>` is the folder this skill is installed in; `<wbs>` is the project's WBS register.

## The board

`Status Board <scope> <sprint>.xlsx`, beside the WBS. **One per sprint**: setting up the next sprint's board moves the closed one to `Archive/` beside it, once it has been consolidated. A board is recognised by its *About* sheet, not its name.

| Sheet | Holds |
|---|---|
| **Board** | A table of the team's **tasks**: *WBS ID* (the WBS row the task helps deliver, from a list of the sprint's IDs), *WBS item* (its title, filled by the agent), *Task*, *Owner*, *Status* (To do · Doing · Done · Blocked · Cancelled), *Notes*, *AC verdict* (met · partly met · not met), *Updated on*, *Updated by*. The sprint's work only: its committed and pulled-in leaves, not the parents they make up |
| **How to update** | For the team and for Copilot in Excel: what each column means, and prompts that work |
| **About** | Scope, sprint, dates, the WBS it came from, *Set up on*, *Consolidated on*. Leave it as it is |

**A WBS row may have several tasks.** Set-up gives each WBS row one task, named after it; the team splits the work by adding rows with the same WBS ID. A board row is never assumed to be a WBS row: the consolidation rolls the tasks up per WBS row.

**Notes is a dated log**, one entry per line, newest on top: `2026-10-28 · Tom Becker: link works; expiry still to do`. The team adds a line and never edits an older one, so the cell shows how the work evolved and several comments on one row stay apart. A line with no date is kept and proposed like any other.

The team may add columns; they are kept. It should not rename or delete ours, change a WBS ID, or add sheets, which a rewrite does not keep. *Cancelled* is set by the product manager, through the WBS.

## The three moments the agent writes the board

Each one re-reads the board immediately before writing, keeps every cell the team entered, changes only the rows it names, and says what it changed. Tell the user before writing; the version history of the drive the board is shared on covers an edit made in the same moment.

### 1. Set up the sprint's board (planning's last step)

```
python <skills>/status-board-manager/scripts/board.py setup "<wbs>" [--sprint <ID>]
```

One task per WBS row planning committed, named after the row, with its owner and its WBS status as a board status; the WBS ID list holds the sprint's IDs. The closed sprint's board moves to `Archive/`; one not consolidated since its sprint ended stops the set-up (consolidate it first; `--force` archives it as it is, said out loud). Then the team is told the board is ready.

### 2. Update the board (whenever the sprint's commitments change in the WBS)

After a pull-in agreed with the product manager, a split's rest carried in, or a row cancelled, the team must see it that day:

```
python <skills>/status-board-manager/scripts/board.py sync "<wbs>" --ids <ID> [<ID> ...]
```

A committed WBS row with no task gets one; every task of a row cancelled in the WBS is marked *Cancelled*, with a dated note on top saying so; a task's blank *WBS item* is filled. Nothing else changes.

### 3. Consolidate (the weekly review, the close-out, or on request)

1. **Read and propose**, read-only:

   ```
   python <skills>/status-board-manager/scripts/board.py propose "<wbs>" [--json]
   ```

   Per WBS row, from all its tasks:

   | Proposal | What the product manager decides | Through |
   |---|---|---|
   | `start`: a task moving on a row not started | Set it Implementing, with the earliest task date as `--actual-start` where given | `wbs.py set --status Implementing` |
   | `close`: every live task Done | Close it. The closure note is drafted from each task's newest note, with the weakest task verdict as the row's (each task's verdict listed; the earlier entries reach the row as notes): **confirm each acceptance criterion with the product manager**, never take the board's verdict as the note | `wbs.py set --status Done --closure "…"` (`--actual-end` from the board's date) |
   | `blocked`: a task Blocked | A RAID issue, with an owner and a date to look again; Implementing if it had not started | `raid-manager` |
   | `unlinked`: a task with no WBS ID | Which WBS row it serves, linked; or new work: a pull-in (ask what it displaces), work outside the sprint, or not now. A new row's parent is asked, never guessed | `link`; or `wbs.py add`, then `wbs.py set --pulled-in` when it starts, then `link` |
   | `back`: every task To do on an Implementing row; `reopened`: a task open on a Done row | Ask why. Nothing changes unasked | |
   | `notes`: entries dated since the last consolidation, from every task of the row | Each becomes a dated note on the WBS row, oldest first, saying it came from the board, its date, its author and its task. One the row already holds is not proposed again | `wbs.py note` |
   | `missing`: a committed WBS row with no task | Added at step 3 | |
   | `unknown`, `unreadable` | A WBS ID the register lacks, or a status off the list: ask the row's owner | |

   **Batch the decisions**: present them once, apply only the ones confirmed. Every write goes through `wbs.py`, so its gates hold: a pull-in states its effect, a close has its closure note, a moved date has its reason. Dates are never moved as tidying.

2. **Write the IDs back** for unlinked tasks, whether they serve an existing row or became a new one:

   ```
   python <skills>/status-board-manager/scripts/board.py link "<wbs>" --row <Excel row> --id <new ID>
   ```

3. **Bring the board back in line and stamp it:**

   ```
   python <skills>/status-board-manager/scripts/board.py sync "<wbs>" --consolidated
   ```

   Then one line for the sprint record or the weekly record: how many moved, closed, pulled in, blocked.

## Look

```
python <skills>/status-board-manager/scripts/board.py show "<wbs>"     # the board in one line
python <skills>/status-board-manager/scripts/board.py find "<folder>"  # every live board under a folder
```

The reports read `board.last_consolidated()` to say how fresh the WBS is.

## Where the board steps sit

The board is a step only where this skill is installed and a board exists; without it, planning, the weekly review and the close-out have no board step and say nothing about one.

- **Planning**: its last step is *Set up*.
- **The weekly review**: *Consolidate*, in *Beyond the sprint*.
- **The close-out**: *Consolidate* before walking the committed items, so the close-out works from the team's latest.
- **A pull-in, a split's carry or a cancellation through `wbs-manager`**: *Update the board*.

## Another tool instead of Excel

Where the team updates its status in another tool (Planner, Lists, Jira, GitHub Projects), adapt **only the reading**: make `propose` read that tool into the same rows (*WBS ID*, *Status* in this vocabulary, *Note*, *AC verdict*, dates), and replace the three writes with that tool's own way of adding a row. The proposals, the decisions and every write to the WBS stay as they are. The installer records the adaptation as a local change. TD.15 names where each likely tool plugs in.

## Relationship to other skills

- **`wbs-manager`** — the register the board comes from and goes back into; every write to it is a `wbs.py` command.
- **`sprint-facilitator`** — planning sets up the board, the close-out consolidates it.
- **`weekly-review-facilitator`** — consolidates it mid-sprint.
- **`raid-manager`** — a blocked row becomes an issue.
- **`reporting`** — says how fresh the WBS is.
