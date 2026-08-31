---
name: wbs-manager
description: Manages a work breakdown structure stored as an Excel register and generates an interactive HTML dashboard from it. Use whenever the user mentions "WBS", "work breakdown", "backlog", "roadmap items", or "deliverables", or asks to create or refresh a WBS dashboard, add or edit work items, or wants analytics on deliverables, backlog health, effort estimates or sprint allocation.
---

# WBS Manager 

Manages Work Breakdown Structure registers stored in Excel (.xlsx) files and generates interactive HTML dashboards. This is the AI-first replacement for the legacy WBS template. Formerly named `wbs-ai-first`.

## Requirements

Python 3 with `openpyxl`. Install once per machine from this skill's folder:

```
pip install -r requirements.txt
```

Everything else the scripts use is standard library. Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Architecture

```
WBS/
 WBS Template.xlsx <- Template for new projects (copy this)
 SKILL.md <- This file
 scripts/
 refresh_wbs.py <- Generates HTML dashboard from any WBS xlsx
 create_wbs.py <- Creates a new WBS from the template

Project folder/
 F.XX <ProjectName>.xlsx <- Project WBS (data, source of truth)
 WBS Dashboard.html <- Generated dashboard (visual, regenerated on demand)
 1. Execution/WP.<ID> <Title>/ <- Support material (see "Support Material" below)
```

`WBS/` is a reference archive of the current + previous packaged versions, not where edits happen — the installed skill (wherever this file actually lives, e.g. `.claude/skills/wbs-manager/`) is the source of truth. See TD.37 for the full lifecycle model.

## Support Material — Execution Folder

Support material for a WBS item (design notes, research, mockups) always lives in the project's `1. Execution/` folder. This is the only convention — there is no fallback or alternate location.

- **Granularity:** one subfolder per Feature-level WP, not per Story. A Story that only needs a single supporting file is a loose file inside its parent's Execution subfolder, distinguished by its own sub-item filename prefix (e.g. `WP3.1 WBS Gap Analysis.md` inside `WP.3 WBS Enhancement/`). Only give a Story its own nested subfolder if its material itself grows multi-document.
- **Naming:** `WP.<ID> <Brief Title>` — keyed off the item's stable `ID` column (see Template Schema below), never off `Code`, since `Code` is expected to be renumbered as the WBS evolves and a folder name keyed off it would silently go stale.
- If the project doesn't yet have a `1. Execution/` folder, create one as part of setting up its WBS.

## Template Schema

The template (`WBS Template.xlsx`) has 3 sheets:

### Sheet: WBS (main backlog)
Single header row (row 1), data from row 2. Columns:

| Column | Required | Description |
|--------|----------|-------------|
| ID | Yes | Stable identifier — plain sequential integer, assigned once at creation, **never reused, never changed** even if the item is reparented or `Code` is renumbered. This is what anything external references: Execution-folder names, `Key Dependencies`, cross-links to RAID or your task tracker. Not the same job as `Code`. |
| Code | Yes | Hierarchical/display position (1.1, 1.2,...). Free to renumber whenever the WBS structure changes — reprioritized, inserted, regrouped. Purely navigational; never used as a reference key outside the row itself. |
| Title | Yes | Short descriptive name |
| Description | No | What needs to be done |
| Acceptance Criteria | No | How completion is verified |
| Owner | No | Person responsible |
| Estimated Effort (h) | No | Hours estimate |
| Type | No | Feature / Story / Tool / System / Process / DocSection / Analysis / Improve |
| Category | No | PMBOK area or project-specific grouping |
| Status | Yes | Portfolio Backlog / Funnel / Not Started / Implementing / Done |
| Priority | No | Must / Should / Could |
| Sprint Planned | No | Sprint ID (e.g. S25.15) |
| Sprint Added | No | Sprint where actually pulled in |
| Sprint Ended | No | Sprint where completed |
| Key Dependencies | No | Codes of blocking items |
| Action Plan | No | Approach description |
| Planning Considerations | No | Assumptions, risks, constraints |
| Validation Approach | No | How the deliverable will be verified |
| Comments | No | General notes |

### Sheet: Key Deliverables
High-level deliverable tracking. Columns: KeyDel.ID, Key Deliverable, Description, Acceptance Criteria, Owner, Status, Estimated Effort (h), Control Approach, Control Tool, Project Phase, Priority, Planned Release, Released On, Key Dependencies, Planning Considerations, Comments.

### Sheet: _Schema
Machine-readable column definitions. The skill reads this to validate and map columns dynamically.

## Critical Design Rules

These rules exist because the old WBS template (735 columns, merged cells, inline Gantt) was impossible for agents to read/write reliably:

1. **NO merged cells** — ever, in any sheet
2. **NO inline Gantt charts** — visual timelines are generated as HTML dashboards
3. **Single header row** (row 1) — data starts at row 2
4. **No conditional formatting** — the dashboard handles all visuals
5. **No formulas** — keep data flat; calculations happen in the dashboard generator
6. **Column order doesn't matter** — the skill discovers columns by header name

## WBS File Discovery

Before any operation, locate the right WBS file:

1. Use `Glob` with patterns `**/F.* WBS*.xlsx` and `**/F.* *.xlsx` across connected folders
2. Filter out the template (`WBS Template.xlsx`)
3. Single match → use directly
4. Multiple matches → narrow by project name from user's prompt, or ask
5. No matches → offer to create a new WBS using `create_wbs.py`

## Operations

### 1. Read / overview
```python
import openpyxl
wb = openpyxl.load_workbook(path, data_only=True)
# Find the main data sheet: named 'WBS', or containing 'Implement', or first sheet
# Build column map from row 1 headers
# Extract items from row 2 onwards
```

### 2. Add items
- Next ID = max existing ID + 1 (never reuse a retired ID)
- Next Code = max existing code + 1, or the appropriate hierarchical position (e.g. "3.6") if it's a sub-item — Code can be freely chosen/renumbered, ID cannot
- Default Status = "Portfolio Backlog" (the default funnel entry point)
- Default Type = "Story" unless user specifies otherwise; use "Feature" for larger epic-level deliverables
- Priority: ask the user or leave blank
- Append row after last data row
- Save xlsx, then **auto-refresh the dashboard** (operation 5)

### 3. Edit items
- Find row by ID column (stable), not Code (may have been renumbered since last touched)
- Update only specified cells
- Save xlsx, then **auto-refresh the dashboard** (operation 5)

### 4. Sprint planning
- Set `Sprint Planned` to sprint ID (e.g. S25.16)
- Multiple items can be allocated to the same sprint
- When item starts: Status → "Implementing", Sprint Added → current sprint
- When item completes: Status → "Done", Sprint Ended → current sprint
- After changes, **auto-refresh the dashboard** (operation 5)

### 5. Generate dashboard
```bash
python <skill-path>/scripts/refresh_wbs.py "<xlsx-path>" "<output-html-path>" "<project-name>"
```
The script reads the xlsx and generates a self-contained HTML file with:
- **KPI strip** — total items, implementing, done, not started, total effort, planned sprints
- **Sprint Board tab** — items grouped by sprint with status badges, filterable by status/priority/type
- **Analytics tab** — status distribution, priority breakdown, sprint effort allocation
- **Gantt tab** — timeline view of sprint-planned items

Save the HTML alongside the xlsx (same folder) as `WBS Dashboard.html`.

**Always regenerate the dashboard after any data change** — the HTML is a snapshot, not a live view.

### 6. Create new WBS for a project
```bash
python <skill-path>/scripts/create_wbs.py "<output-path>" "<project-name>"
```
Copies the template. User removes example rows and starts adding items.

## Status Values

| Status | Meaning |
|--------|---------|
| Portfolio Backlog | Item captured but not yet committed |
| Funnel | Being considered/evaluated — under active triage |
| Not Started | Committed but work hasn't begun |
| Implementing | Actively being worked on |
| Done | Completed |

## Type Values

| Type | Meaning |
|------|---------|
| Feature | Larger deliverable / epic-level work package |
| Story | Discrete work item within a feature |
| Tool | A reusable tool or template |
| System | A system or framework |
| Process | A process or procedure |
| DocSection | A section within a larger document |
| Analysis | Research or assessment work |
| Improve | Enhancement to an existing tool |

## Sprint ID Convention

Format: `S{YY}.{NN}` — e.g. S25.15 means year 2025, sprint 15.

## Relationship to Other Tools

- **Task tracker** = committed/active work (what is being done this sprint)
- **RAID** = risks, actions, issues, decisions
- **WBS** = full roadmap/backlog (what could be done, what's planned, what's done)

Items flow from the WBS into your task tracker when committed to a sprint. The WBS captures the thinking and planning before commitment.
