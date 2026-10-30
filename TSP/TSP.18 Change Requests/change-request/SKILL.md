---
name: change-request
description: Raises and processes change requests (TSP.18 Change Requests) - the team's channel for asking that the project's registers change. Anyone drafts a request (a new risk or issue, a decision taken in a meeting, a change of scope or dates, new work, an idea) into the project's Change Requests folder, with what it affects by WBS or RAID ID; the product manager processes the open ones, each becoming a RAID entry or a WBS change, or declined with a reason, and the request is closed with its outcome. Use whenever a team member says "raise a change request", "log this as a risk", "we decided X in the meeting", "this should be split / moved / dropped", "the scope changed", "add this to the backlog", or otherwise wants something in the RAID or the WBS they do not keep themselves; and when the product manager asks for the open requests, or runs the weekly review. Not for status on tasks (the team board) or a work item's own documents (work-manager).
---

# Change Request (TSP.18)

The registers are the product manager's to keep. The team sees what should change in them first: a risk in a meeting, a decision in a corridor, a deliverable that is really two. A change request is how that reaches the registers without being lost in a chat: drafted by whoever saw it, decided by whoever keeps the registers, with its outcome written where the requester can see it.

## Requirements

Python 3, standard library only. `<skills>` is the folder this skill is installed in. Requests live in the planning folder's `Change Requests` folder (the project pack sets it up; the team needs write access to it, and only to it). A project that keeps it elsewhere, or names it otherwise, says so in its artifact register: the folder whose *Managed By* is this tool. The WBS and the RAID are read, never written.

## Raise a request (anyone)

1. **Get the request in a sentence**, and its type: risk, issue, decision, change, new work or idea. Ask *why* and, briefly, *the impact*: what happens if it is done, or not.
2. **Find what it affects**, read-only, and confirm with the person:

```
python <skills>/change-request/scripts/cr.py lookup "<project>" identity check
```

3. **Draft it:**

```
python <skills>/change-request/scripts/cr.py draft "<project>" --type risk --what "<the change>" --why "<why>" --impact "<impact>" --affects "WBS 12, RAID 3" --by "<name>"
```

4. Say where it went, and that the product manager picks it up at the weekly review. Never promise an outcome.

## Process the open requests (the product manager)

At the weekly review, or whenever asked:

1. `cr.py list "<project>"` shows the open requests.
2. **For each, propose what it becomes**, from what it says and what it affects: a RAID entry of its type (a *Change* carries *requested by* and *impact*; a risk its three slots), a new WBS row, or an edit to one. Decline when it duplicates something already recorded, or does not hold up; say why.
3. **The product manager decides**, in one batch. Apply each accepted one through the skill that keeps the register (`raid-manager`, `wbs-manager`), then close the request with what it became:

```
python <skills>/change-request/scripts/cr.py close "<project>" "<part of its file name>" --accepted "as RAID 14" --by "<name>"
python <skills>/change-request/scripts/cr.py close "<project>" "<part of its file name>" --declined "already RAID 9" --by "<name>"
```

The outcome is written on the request, and it moves to `Processed/`: the requester reads there what came of it.

## Never

- Write the WBS or the RAID from a draft: a request is a proposal until the product manager decides.
- Process a request with no reason given on a decline.
- Edit or delete a processed request: it is the record of what was asked and what was decided.

## Relationship to other skills

- **`raid-manager`**, **`wbs-manager`**: where an accepted request is applied, by the product manager.
- **`weekly-review-facilitator`**: processes the open requests in the same batch as the team board's consolidation.
- **`work-manager`**: a work item often turns up the change; its documents stay in its folder, the request here.
- **`status-board-manager`**: status, not change. A new task inside committed work goes on the board; new work for the backlog is a request.
