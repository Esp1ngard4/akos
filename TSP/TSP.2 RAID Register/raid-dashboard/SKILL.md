---
name: raid-dashboard
description: Manages a RAID register - Risks, Actions, Issues, Decisions and Ideas - stored as a JSON register, and generates an interactive HTML dashboard with analytics and a risk heat map. Use whenever the user mentions "RAID", "risk register", "issue log", "decision log", or asks to add, edit or close a risk, action, issue or decision, or wants a view of project risks and how the project is tracking.
---

# RAID Dashboard Manager

A RAID register tracks risks, actions, issues, decisions and ideas for one project. The JSON register is the source of truth; the HTML dashboard is the visual analytics layer generated on top of it.

## Requirements

Python 3. **No dependencies** - standard library only.

Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Architecture

```
<Project folder>/
 0. PrjMgm/
 RAID/
 RAID <Project>.json <- source of truth (human + Claude editable)
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

1. Use `Glob` with pattern `**/RAID*.json` across all connected folders.
2. Confirm `meta.kind == "raid-register"` — the same folder may hold a WBS or Artifact register.
2. **Single match** → use it directly.
3. **Multiple matches** → try to narrow down:
 - If the user named a project in their prompt (e.g. "refresh the Atlas RAID"), match against the filename or parent folder name (case-insensitive, fuzzy is fine).
 - If still ambiguous, present the matches using `AskUserQuestion` with the filenames/paths as options.
4. **No matches** → ask if they want to create a new RAID register (operation 3).

This discovery step runs before every operation — don't assume the same file as last time unless the user is clearly continuing on the same project within the conversation.

## Core operations

### 1. Refresh dashboard

When the user says "refresh the RAID dashboard" or similar:

1. Discover the register (see discovery section above).
2. Run `scripts/refresh_raid.py` via bash:
 ```bash
 python <skill-path>/scripts/refresh_raid.py "<register.json>" "<output-html-path>" "<project-name>"
 ```
3. Create or update the Cowork artifact (`raid-<project-slug>`) with the generated HTML.

### 2. Add/edit RAID items

```python
import sys; sys.path.insert(0, "<skill-path>/scripts")
import registry as R

data = R.load(path)
entries = R.rows(data, "entries")
```

1. New items: `R.next_id(data, "entries", "RAID.ID")`, then append the row.
2. Edits: find the row by `RAID.ID` — `R.get(data, "entries", "RAID.ID", 5)` — and update only the fields being changed.
3. Omit fields that have no value rather than writing empty strings.
4. `R.save(path, data)`, then auto-refresh the dashboard (operation 1).

**Priority % and Target Residual Risk are not fields.** They are computed from the scores when the dashboard renders — Priority as `(Urgency * 1.5 + Consequences) / 12.5 * 100`, Target Residual Risk as `Probability * Severity * (1 - Mitigation Target / 100)`. Never store either: a stored copy goes stale the moment a score changes.


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

```bash
python <skill-path>/scripts/create_raid.py "<output-path>.json" "<project-name>"
```

Builds an empty register — schema, field order and vocabularies, zero rows — and creates the `AuxMat/` folder beside it.

## Register schema

One collection, `entries`. `registry.py` owns the `meta` envelope; `create_raid.py` holds the field order and the vocabularies, which are written into `meta.settings`.

| Field | Notes |
|-------|-------|
| RAID.ID | Sequential integer |
| Detail | Short title |
| Type | Risk, Action, Issue, Decision, Idea |
| DRI | Person responsible |
| Urgency (1-5) | General scoring input, drives Priority % |
| Consequences (1-5) | General scoring input, drives Priority % |
| Feasibility | 1-5 |

### Risk-analysis block

Only meaningful for `Type = Risk` rows — a deeper, risk-specific extension of the same Urgency/Consequences/Feasibility triplet. Order follows the analysis workflow: assess, decide, target, then record the real outcome.

| Field | Notes |
|-------|-------|
| Probability of Occurrence (1-5) | Risk-specific, distinct from general Urgency |
| Severity (1-5) | Risk-specific, distinct from general Consequences |
| Response Strategy | Avoid, Transfer, Mitigate, Accept, Exploit, Share, Enhance (PMBOK threat + opportunity responses) |
| Mitigation Target % | 0-100, manual input |
| Residual Risk Score | Actual/manual, filled in once mitigation plays out — compare against the computed Target Residual Risk |

### Core schema, continued

| Field | Notes |
|-------|-------|
| MoSCoW | 1.Must, 2.Should, 3.Could, 4.Won't |
| Status | Open, Closed |
| Last Review | Date |
| Review On | Date |
| Next Review On | Fallback review date if Review On isn't filled |
| Description | |
| Action Plan | |
| Acceptance Criteria | |
| Action Log | Running log / closure notes |
| Category | |
| Tracked Externally | Y/N flag, see operation 2b |
| Opened On | |
| Requested By | |
| Involve | Other stakeholders |
| Has AuxMat | Y/N flag, see AuxMat section above |
| Estimated Effort | |
| ETC | Estimated time to complete |
| ETC Renegotiated | Revised ETC after initial estimate slips |
| Closed On | |
| Closed By | |


## Dashboard features

- **Board tab**: sortable table, filters for Type/Status/MoSCoW/Category/DRI/externally-tracked, a "Clear all" button, and an active-filter count badge. Filter state persists across reloads via localStorage (keyed per project name).
- **Analytics tab**: KPIs, by-type and by-status charts, priority distribution, MoSCoW breakdown, items-over-time timeline, and — when risk items are present — a risk heat map.
- **Risk heat map**: Probability x Severity scatter with a green/amber/red zone background (green <6, amber 6-14, red >=15 on Probability x Severity). Only renders when >=3 open risk items have both fields scored.
- **Reviews tab**: flags items never reviewed or last reviewed >30/>90 days ago.

The dashboard is generated output — overwritten in full on every refresh. Never hand-edit it.
