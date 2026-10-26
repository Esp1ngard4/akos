# Action Tracker Conventions

## Filing

- **With the work, never centralised.** A tracker lives in the support folder of its anchor: the WBS row's `WP.<ID> <Title>/` folder under the project's execution folder (read the register's `meta.execution` first), or the RAID item's `AuxMat/{Type initial}{ID}-{slug}/` folder. The anchor is what says where a tracker is; there is no index of trackers.
- **Filename:** `Action Tracker <Scope Name>.md`, named for the piece of work. The meta block's `scope` matches the filename.
- If the anchor has no obvious home yet, ask where the tracker should live rather than inventing a folder structure.

## Meta block (required, first thing in the file)

Every tracker opens with an HTML comment block, before the `# Title`:

```
<!-- action-tracker-meta
scope: <the piece of work, matching the filename>
owner: <who runs the sessions the tracker is walked in>
anchor: <a WBS row by ID, e.g. "WBS 12", or a RAID item, e.g. "RAID 5">
related_wbs: <comma-separated WBS IDs that sections anchor to, or "-">
related_raid: <comma-separated RAID IDs, or "-">
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
status: Active | Archived
-->
```

`anchor` is what the tracker hangs from; `related_wbs` lists the rows individual sections point at. Both hold WBS **`ID`** values, never `Code` values.

Update `last_reviewed` every time the tracker is edited. Set `status: Archived` rather than deleting a tracker whose piece of work has finished. It stays where it is filed, because it belongs to its anchor.

## Owners

- **The tracker's `owner`** runs the sessions. It is asked for on create, never assumed.
- **A row's Owner** is one person, by the name the team uses for them, written the same way throughout the tracker. A row owed by two people is two rows, or one owner with the other named in Dependency.

## Section codes

- Short, uppercase, 2 to 5 letters, taken from the section name (`PROC` for Procurement, `COMMS` for Communications).
- Assigned once, recorded in the tracker's Sections legend, and **never reused**: when a section closes, its code retires with it.
- **The code is a local key, not a reference.** A section's optional WBS anchor is a separate field on its header. The two are independent, which is what lets a section gain a WBS anchor later without renumbering anything.
- One section, one ID sequence. Do not run one flat sequence across the whole tracker: scanning by section is the point.

## Action IDs

`<CODE>-NN`, zero-padded to two digits: `PROC-01`, `COMMS-02`. If a section ever needs three digits, extend the padding rather than breaking the pattern.

- Sequential within a section, allocated once, **never reused or renumbered**.
- An ID's code never changes, even if the action is later judged to belong in another section. Move the row and say so in Update history; do not renumber.

## Dates

`YYYY-MM-DD` everywhere, without exception.

- **Due date** is a real date or `TBD`. Never blank.
- **A `TBD` carries its checkpoint in the same cell:** `TBD · checkpoint YYYY-MM-DD`, the date by which the real due date is confirmed. A `TBD` with no checkpoint is a stalled action wearing a status that looks active: flag it rather than leave it. A checkpoint kept anywhere else (the Latest update, the section's narrative) cannot be scanned for, so it is missed.
- **A passed checkpoint is met or re-set, never just moved.** The real due date replaces `TBD`, or a new checkpoint goes in with the reason in Latest update.
- **Latest update opens with its date:** `2026-03-12: quote received`. That date is how a row gone quiet is found.

## Status vocabulary

- `⬜ Not Started`
- `🔄 In Progress`
- `⛔ Blocked`
- `✅ Done`
- `🚫 Cancelled`

No other values. `Cancelled` covers work deliberately dropped rather than delivered. Without it, an abandoned row either disappears or sits open forever, and the reason it was dropped survives nowhere.

## Closing an action

- Set Status to `✅ Done` or `🚫 Cancelled`, and move the row to **Closed actions** with its **Status**, a **Closed date** and a one-line factual **Outcome**. The Status column is what tells a delivered action from a dropped one.
- Keep the same ID. Never delete a row or reuse a closed ID.
- Do it the day the action is done. A tracker whose state is true stays useful; one that piles up finished rows in its open tables does not.

## Narrative blocks

The tracker's **Current position**, and each section's **Objective** and **Current position**, are what get read aloud in a session; the tables are walked after. Keep them factual and current: a Current position older than the last review is a defect, not background.

A section's Current position is **narrative, not status**. Where the section anchors to a WBS row, that row's status and dates belong to the WBS and are not restated here.

## Update history

Every session that touches a tracker appends one row: the date, who updated it, a one-line summary. Actions taken from a meeting name the meeting here. This is the tracker's own change log; action detail belongs in the action's row.

## Relationship to the registers

- **Not the RAID register.** RAID holds governed items, with scoring and review dates. A row that acquires a review date and a consequence becomes a RAID Action through `raid-manager`, leaving a one-line pointer here. Never two sources of truth.
- **Not the WBS.** The WBS holds deliverables, roadmap position and schedule. A breakdown deliberately kept out of the WBS is the normal case for this tool, not an omission.
- **Not a personal task list.** A row copied into someone's own task list says so on the row, and the copy carries `AT: <CODE>-NN` back. The tracker stays the shared view.

The tracker is disposable next to the registers: it holds the operational detail of a piece of work, before that detail needs a formal home or without it ever needing one.
