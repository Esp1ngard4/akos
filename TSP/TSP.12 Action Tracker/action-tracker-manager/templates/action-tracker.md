<!-- action-tracker-meta
scope: <Piece of work, matches the filename>
owner: <Who runs the sessions>
anchor: WBS <ID>
related_wbs: <comma-separated WBS IDs, or "-">
related_raid: <comma-separated RAID IDs, or "-">
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
status: Active
-->

# <Piece of Work> | Action Tracker

**Purpose:** The actions agreed in the working sessions for <piece of work>, with the people involved.

**Tracker owner:** <Name>
**Anchored to:** WBS <ID>: <the row's title>
**Last reviewed:** YYYY-MM-DD

## What this is and is not

- **Not the RAID register.** Governed risks, issues, decisions and actions live there. A row here that acquires a review date and a real consequence is promoted to a RAID Action and left as a pointer.
- **Not the WBS.** Deliverables, roadmap position and schedule live there. A breakdown that is not in the WBS is expected here.
- **Not a personal task list.** This is the shared view of everyone's actions on this piece of work. A row someone also keeps in their own list says so.

## Current position

<Two to four factual sentences on the state of the whole piece of work. This is what gets read first in a session.>

## Sections

| Code | Section | WBS anchor |
|---|---|---|
| XX | <Section name> | WBS <ID>, or none |

Codes are 2 to 5 uppercase letters, assigned once, never reused or renumbered. The code is a local key; the WBS anchor is a separate reference and may be added later.

## Status key

`⬜ Not Started` · `🔄 In Progress` · `⛔ Blocked` · `✅ Done` · `🚫 Cancelled`

> **Date rule:** every open action has a committed due date, or `TBD · checkpoint YYYY-MM-DD`. Every Latest update opens with its date.

---

## Attention required

Commitments or decisions needing near-term follow-up. Keep it short: a rolling top-of-mind list, not a copy of every open row below.

| Action ID | Commitment or decision required | Owner | Due date | Status |
|---|---|---|---|---|
| | | | | |

---

## 1. <Section Name>   ·   `XX`   ·   WBS <ID>

**Objective:** <what this section is trying to achieve>

**Current position:** <one or two factual sentences: narrative, not the WBS row's status>

### Actions

| ID | Commitment | Owner | Due date | Status | Dependency | Latest update |
|---|---|---|---|---|---|---|
| XX-01 | | | TBD · checkpoint YYYY-MM-DD | ⬜ Not Started | | YYYY-MM-DD: |

### Notes

<optional free text: rationale, background, anything that does not belong in a table row>

---

## 2. <Section Name>   ·   `YY`   ·   no WBS anchor

**Objective:**

**Current position:**

### Actions

| ID | Commitment | Owner | Due date | Status | Dependency | Latest update |
|---|---|---|---|---|---|---|
| YY-01 | | | TBD · checkpoint YYYY-MM-DD | ⬜ Not Started | | YYYY-MM-DD: |

---

## Closed actions

| ID | Section | Commitment | Owner | Status | Closed date | Outcome |
|---|---|---|---|---|---|---|
| _None_ | | | | | | |

---

## Update history

| Date | Updated by | Summary |
|---|---|---|
| YYYY-MM-DD | <Name> | Tracker created |
