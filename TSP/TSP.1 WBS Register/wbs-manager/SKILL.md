---
name: wbs-manager
description: Manages a work breakdown structure stored as a JSON register and generates an interactive HTML dashboard from it. Use whenever the user mentions "WBS", "work breakdown", "backlog", "roadmap items", or "deliverables", or asks to create or refresh a WBS dashboard, add or edit work items, or wants analytics on deliverables, backlog health, effort estimates or sprint allocation.
---

# WBS Manager

Manages Work Breakdown Structure registers — one JSON file per project, holding the full roadmap/backlog — and generates interactive HTML dashboards on top of them.

## Requirements

Python 3. **No dependencies** — standard library only.

Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Architecture

```
TSP.1 WBS Register/
  TD.1 - WBS Register.md      <- Governance: purpose, conventions, history
  wbs-manager/                <- The skill. Source of truth for all edits
    SKILL.md                  <- This file
    requirements.txt
    scripts/
      registry.py             <- The shared JSON register format (load/save/hash)
      refresh_wbs.py          <- Generates the HTML dashboard from a register
      create_wbs.py           <- Builds an empty register for a new project

Project folder/
  WBS <Project>.json                <- The register (data, source of truth)
  WBS Dashboard.html                <- Generated view, regenerated on demand
  1. Execution/WP.<ID> <Title>/     <- Support material (see below)
```

The skill lives with its tool, at `TSP.1 WBS Register/wbs-manager/` — that is the source of truth, and all edits happen there. Wherever your agent loads skills from, that location is a link into this folder, not a copy, so the two cannot drift. See TD.1 for the full lifecycle model.

## Support Material — Execution Folder

Support material for a WBS item (design notes, research, mockups) always lives in the project's `1. Execution/` folder. This is the only convention — there is no fallback or alternate location.

- **Granularity:** one subfolder per Feature-level WP, not per Story. A Story that only needs a single supporting file is a loose file inside its parent's Execution subfolder, distinguished by its own sub-item filename prefix (e.g. `WP3.1 Gap Analysis.md` inside `WP.3 Dashboard Enhancement/`). Only give a Story its own nested subfolder if its material itself grows multi-document.
- **Naming:** `WP.<ID> <Brief Title>` — keyed off the item's stable `ID` field (see Register Schema below), never off `Code`, since `Code` is expected to be renumbered as the WBS evolves and a folder name keyed off it would silently go stale.
- If the project doesn't yet have a `1. Execution/` folder, create one as part of setting up its WBS.

## Register Schema

A register is one JSON file: a `meta` envelope plus named collections of rows. `registry.py` owns the envelope and is shared with the other register tools here.

```json
{
  "meta": {
    "kind": "wbs-register",
    "version": 1,
    "scope": "Atlas",
    "updated": "2026-09-01T15:16:36",
    "values_hash": "sha256:ad2e...",
    "settings": {"fields": {...}, "vocabularies": {...}}
  },
  "items": [ {...} ],
  "key_deliverables": [ {...} ]
}
```

- **`values_hash`** fingerprints the rows, not the file — it excludes `meta`, so reindenting is not a data change. A generated dashboard stamps the hash it was built from, which is how `registry.stale_views()` can tell you a dashboard has gone stale rather than quietly showing old numbers.
- **Rows omit their empty fields.** Do not write `null` or `""` to mean "no value"; leave the key out. `meta.settings.fields` carries the canonical field order for rendering a rectangular table.
- **A register may carry extra collections** beyond `items` and `key_deliverables` when a project has structured data that belongs with its WBS. The dashboard reads `items` only.

### Collection: `items` (main backlog)

| Field | Required | Description |
|--------|----------|-------------|
| ID | Yes | Stable identifier — plain sequential integer, assigned once at creation, **never reused, never changed** even if the item is reparented or `Code` is renumbered. This is what anything external references: Execution-folder names, `Key Dependencies`, cross-links to other registers or a task tracker. Not the same job as `Code`. |
| Code | Yes | Hierarchical/display position (1.1, 1.2, ...). Free to renumber whenever the WBS structure changes — reprioritized, inserted, regrouped. Purely navigational; never used as a reference key outside the row itself. |
| Title | Yes | Short descriptive name |
| Description | No | What needs to be done |
| Acceptance Criteria | No | How completion is verified |
| Owner | No | Person responsible |
| Estimated Effort (h) | No | Hours estimate |
| Type | No | Feature / Story / Tool / System / Process / DocSection / Analysis / Improve |
| Category | No | Knowledge area or project-specific grouping |
| Status | Yes | Portfolio Backlog / Funnel / Not Started / Implementing / Done / Cancelled |
| Priority | No | Must / Should / Could / Won't (MoSCoW) |
| Sprint Planned | No | Sprint ID (e.g. S25.15) |
| Sprint Added | No | Sprint where actually pulled in |
| Sprint Ended | No | Sprint where completed |
| Key Dependencies | No | IDs of blocking items |
| Action Plan | No | Approach description |
| Planning Considerations | No | Assumptions, risks, constraints |
| Validation Approach | No | How the deliverable will be verified |
| Comments | No | General notes |

### Collection: `key_deliverables`

High-level deliverable tracking. Fields: KeyDel.ID, Key Deliverable, Description, Acceptance Criteria, Owner, Status, Estimated Effort (h), Control Approach, Control Tool, Project Phase, Priority, Planned Release, Released On, Key Dependencies, Planning Considerations, Comments.

## Critical Design Rules

1. **The register is the source of truth; the dashboard is generated.** Never hand-edit the HTML — it is overwritten in full on every refresh.
2. **`ID` is never reused and never changed.** Renumber `Code` freely instead.
3. **Write through `registry.py`,** so `updated` and `values_hash` stay correct. Hand-editing the JSON is possible but leaves the hash stale.
4. **No derived values in the register** — effort rollups, counts and percentages are computed by the dashboard generator, not stored.
5. **Field order doesn't matter** in a row; `meta.settings.fields` defines display order.

## WBS File Discovery

Before any operation, locate the right register:

1. Use `Glob` with patterns `**/*WBS*.json` and `**/WBS *.json` across connected folders
2. Confirm `meta.kind == "wbs-register"` — the same folder may hold a RAID or Artifact register
3. Single match → use directly
4. Multiple matches → narrow by project name from the user's prompt, or ask
5. No matches → offer to create one with `create_wbs.py`

## Operations

### 1. Read / overview
```python
import sys; sys.path.insert(0, "<skill-path>/scripts")
import registry as R

data = R.load(path)
items = R.rows(data, "items")
```

### 2. Add items
- Next ID = `R.next_id(data, "items")` (never reuse a retired ID)
- Next Code = max existing code + 1, or the appropriate hierarchical position (e.g. "3.6") if it's a sub-item — Code can be freely chosen/renumbered, ID cannot
- Default Status = "Portfolio Backlog" (the default funnel entry point)
- Default Type = "Story" unless the user specifies otherwise; use "Feature" for larger epic-level deliverables
- Priority: ask the user or leave blank
- Omit fields that have no value rather than writing empty strings
- Append to `items`, `R.save(path, data)`, then **auto-refresh the dashboard** (operation 5)

### 3. Edit items
- Find the row by `ID` (stable), not `Code` (may have been renumbered since last touched) — `R.get(data, "items", "ID", 12)`
- Update only the specified fields
- `R.save(path, data)`, then **auto-refresh the dashboard** (operation 5)

### 4. Sprint planning
- Set `Sprint Planned` to sprint ID (e.g. S25.16)
- Multiple items can be allocated to the same sprint
- When an item starts: Status → "Implementing", Sprint Added → current sprint
- When an item completes: Status → "Done", Sprint Ended → current sprint
- After changes, **auto-refresh the dashboard** (operation 5)

### 5. Generate dashboard
```bash
python <skill-path>/scripts/refresh_wbs.py "<register.json>" "<output-html-path>" "<project-name>"
```
Generates a self-contained HTML file with:
- **KPI strip** — total items, implementing, done, not started, total effort, planned sprints
- **Sprint Board tab** — items grouped by sprint with status badges, filterable by status/priority/type
- **Analytics tab** — status distribution, priority breakdown, sprint effort allocation
- **Gantt tab** — timeline view of sprint-planned items

Save the HTML alongside the register (same folder) as `WBS Dashboard.html`.

**Always regenerate the dashboard after any data change** — the HTML is a snapshot, not a live view. `R.stale_views(path)` reports any dashboard beside the register that was built from different data; it is cheap enough to check after every edit.

### 6. Create a new WBS for a project
```bash
python <skill-path>/scripts/create_wbs.py "<output-path>.json" "<project-name>"
```
Builds an empty register — schema, field order and vocabularies, zero rows. It refuses to overwrite an existing file without `--force`.

## Status Values

| Status | Meaning |
|--------|---------|
| Portfolio Backlog | Item captured but not yet committed |
| Funnel | Being considered/evaluated — under active triage |
| Not Started | Committed but work hasn't begun |
| Implementing | Actively being worked on |
| Done | Completed |
| Cancelled | Dropped without being delivered — keep the row and say why in Comments |

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
