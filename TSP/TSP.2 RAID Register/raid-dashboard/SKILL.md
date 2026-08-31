---
name: raid-dashboard
description: Manages a RAID register - Risks, Actions, Issues, Decisions and Ideas - stored as an Excel file, and generates an interactive HTML dashboard with analytics and a risk heat map. Use whenever the user mentions "RAID", "risk register", "issue log", "decision log", or asks to add, edit or close a risk, action, issue or decision, or wants a view of project risks and how the project is tracking.
---

# RAID Dashboard Manager

This skill exists because RAID registers are one of the user's most-used project tools, tracking risks, actions, issues, decisions, and ideas across multiple projects. The Excel file is the source of truth (editable by humans and by Claude via openpyxl), and the Cowork artifact provides the rich visual analytics layer on top.

## Requirements

Python 3 with `openpyxl`. Install once per machine from this skill's folder:

```
pip install -r requirements.txt
```

Everything else the scripts use is standard library. Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Architecture

```
<Project folder>/
 0. PrjMgm/
 RAID/
 RAID <Project>.xlsx <- source of truth (human + Claude editable)
 RAID Dashboard.html <- generated dashboard (visual, regenerated on demand)
 AuxMat/ <- per-item supporting documents
 R5-vendor-risk-analysis/ <- subfolder per item needing working docs
 I3-permit-delay/
```

### Folder conventions

- **Location**: the RAID register lives under `0. PrjMgm/RAID/` within the project folder. `0. PrjMgm` is the standard project management subfolder.
- **AuxMat**: created alongside the register when a new RAID is initialised. Contains one subfolder per RAID item that needs supporting documents (design notes, analysis, evidence, correspondence).
- **AuxMat subfolder naming**: `{Type initial}{ID}-{slug}` — e.g. `R5-vendor-risk-analysis`, `I3-permit-delay`, `A12-stakeholder-comms`. The slug is a short kebab-case description.
- **When to create an AuxMat subfolder**: when working on a RAID item requires creating documents beyond what fits in the register's Description, Action Plan, or Action Log fields. Not every item needs one.
- The `create_raid.py` script creates the `AuxMat/` folder automatically when generating a new register.

## RAID file discovery

The user has RAID registers across many projects and areas of focus. Before any operation, locate the right file:

1. Use `Glob` with pattern `**/RAID*.xlsx` across all connected folders.
2. **Single match** → use it directly.
3. **Multiple matches** → try to narrow down:
 - If the user named a project in their prompt (e.g. "refresh the Casa Lx RAID"), match against the filename or parent folder name (case-insensitive, fuzzy is fine).
 - If still ambiguous, present the matches using `AskUserQuestion` with the filenames/paths as options.
4. **No matches** → ask if they want to create a new RAID register (operation 3).

This discovery step runs before every operation — don't assume the same file as last time unless the user is clearly continuing on the same project within the conversation.

## Core operations

### 1. Refresh dashboard

When the user says "refresh the RAID dashboard" or similar:

1. Discover the RAID xlsx (see discovery section above).
2. Run `scripts/refresh_raid.py` via bash:
 ```bash
 python <skill-path>/scripts/refresh_raid.py "<xlsx-path>" "<output-html-path>" "<project-name>"
 ```
3. Create or update the Cowork artifact (`raid-<project-slug>`) with the generated HTML.

### 2. Add/edit RAID items

1. Read the xlsx with openpyxl
2. New items: next ID = max existing + 1, append row with priority formula
3. Edits: find row by RAID ID, update cells
4. Save xlsx, then auto-refresh dashboard (operation 1)

### 2b. External tracking flag

The register carries a simple Y/N `Tracked Externally` flag:

- Set it to "Y" when a RAID item's action plan is being tracked in your task tracker
  (Jira, Azure DevOps, Planner, a to-do app - whichever you use).
- The dashboard shows a checkmark badge on flagged items and offers filter buttons
  for tracked and untracked items.
- **No task IDs or links are stored** - just the flag. Keeping the linkage one-way
  avoids the register going stale every time a task moves.

For traceability in the other direction, put the RAID ID in the tracker item's
description (e.g. `RAID: R.5`). That direction is the useful one, and it costs
nothing to maintain.

If your tracker has an API and you want real task creation, delegate it to a
separate skill that owns those conventions rather than building tracker-specific
logic into this one.

### 3. Create new RAID register

Run `scripts/create_raid.py "<output-path>" "<project-name>"` to generate a fresh xlsx with the standard schema, then create the artifact.

## Excel schema

Row 6 = headers, data starts row 7. Full column list (v2.3 — see `RAID/TF.103 - RAID Register.md` version history):

| Col | Field | Notes |
|-----|-------|-------|
| B | RAID.ID | Sequential integer |
| C | Detail | Short title |
| D | Type | Risk, Action, Issue, Decision, Idea |
| E | DRI | Person responsible |
| F | Priority % | Formula: `=(Urgency*1.5 + Consequences)/12.5*100` |
| G | Urgency (1-5) | General scoring input, drives Priority % |
| H | Consequences (1-5) | General scoring input, drives Priority % |
| I | Feasibility | 1-5 |

### Risk-analysis block (J-O)

Inserted right after Feasibility because it's a deeper, risk-specific extension of the same G/H/I scoring triplet — only meaningful for `Type = Risk` rows, but kept adjacent rather than tacked on at the end. Order follows the actual analysis workflow: assess, decide, target, calculate, then record the real outcome.

| Col | Field | Notes |
|-----|-------|-------|
| J | Probability of Occurrence (1-5) | Risk-specific, distinct from general Urgency (G) |
| K | Severity (1-5) | Risk-specific, distinct from general Consequences (H) |
| L | Response Strategy | Dropdown: Avoid, Transfer, Mitigate, Accept, Exploit, Share, Enhance (PMI PMBOK threat + opportunity responses) |
| M | Mitigation Target % | 0-100, manual input |
| N | Target Residual Risk | Formula: `=IF(M{r}="","",ROUND(J{r}*K{r}*(1-M{r}/100),1))` — Probability x Severity reduced by the mitigation target |
| O | Residual Risk Score | Actual/manual, filled in once mitigation plays out — compare against Target Residual Risk (N) |

### Core schema, continued (P-AI)

| Col | Field | Notes |
|-----|-------|-------|
| P | MoSCoW | 1.Must, 2.Should, 3.Could, 4.Won't |
| Q | Status | Open, In Progress, Resolved, Closed, On Hold |
| R | Last Review | Date |
| S | Review On | Date |
| T | Next Review On | Fallback review date if Review On isn't filled |
| U | Description | |
| V | Action Plan | |
| W | Acceptance Criteria | |
| X | Action Log | Running log / closure notes |
| Y | Category | |
| Z | Tracked Externally | Y/N flag, see operation 2b below |
| AA | Opened On | |
| AB | Requested By | |
| AC | Involve | Other stakeholders |
| AD | Has AuxMat | Y/N flag, see AuxMat section above |
| AE | Estimated Effort | |
| AF | ETC | Estimated time to complete |
| AG | ETC Renegotiated | Revised ETC after initial estimate slips |
| AH | Closed On | |
| AI | Closed By | |

## Dashboard features

- **Board tab**: sortable table, filters for Type/Status/MoSCoW/Category/DRI/externally-tracked, a "Clear all" button, and an active-filter count badge. Filter state persists across reloads via localStorage (keyed per project name).
- **Analytics tab**: KPIs, by-type and by-status charts, priority distribution, MoSCoW breakdown, items-over-time timeline, and — when risk items are present — a risk heat map.
- **Risk heat map**: Probability x Severity scatter with a green/amber/red zone background (green <6, amber 6-14, red >=15 on Probability x Severity). Only renders when >=3 open risk items have both fields scored.
- **Reviews tab**: flags items never reviewed or last reviewed >30/>90 days ago.

## openpyxl preservation note

openpyxl strips conditional formatting and images on save. This is fine -- the xlsx is the data store, the artifact is the visual layer. Don't try to preserve Excel formatting; invest that energy in the artifact instead.
