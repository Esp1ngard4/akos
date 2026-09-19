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
      wbs.py                  <- The operations with rules attached
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
  "items": [ {...} ]
}
```

- **`values_hash`** fingerprints the rows, not the file — it excludes `meta`, so reindenting is not a data change. A generated dashboard stamps the hash it was built from, which is how `registry.stale_views()` can tell you a dashboard has gone stale rather than quietly showing old numbers.
- **Rows omit their empty fields.** Do not write `null` or `""` to mean "no value"; leave the key out. `meta.settings.fields` carries the canonical field order for rendering a rectangular table.
- **A register may carry extra collections** beyond `items` when a project has structured data that belongs with its WBS. The dashboard reads `items` only.

### The four axes

A row says four independent things, and keeping them apart is what lets deliverables be a view over the register rather than a second collection:

| Field | Question it answers | Values |
|---|---|---|
| `Type` | What **level** is this? | Deliverable / Feature / Story / Task |
| `Class` | What **kind of value** does it serve? | Product / Management / Enabler |
| `Delivers` | What **artifact** does it produce? | Tool / System / Process / Document |
| `Nature` | What is being **done**? | Build / Improve / Analyse / Fix / Maintain |

**No level is defined by duration.** Size lives in `Estimated Effort (h)`, which states it better than a level name ever could — and once tooling compresses a week of work into an afternoon, any definition resting on "fits in a sprint" stops discriminating anything.

| Type | Test | Names a |
|---|---|---|
| **Deliverable** | A verifiable product, result or capability that persists after the project | noun |
| **Feature** | A named increment of a deliverable that a stakeholder would recognise and ask for | noun |
| **Story** | The smallest slice that is independently valuable **and** independently verifiable | verb |
| **Task** | A step that is not independently valuable; it only makes sense inside its story | verb |

The noun/verb column is the quickest test in practice: deliverables and features name *things*, stories and tasks name *activity*. "Renovated kitchen" against "install the cabinets"; "Todoist integration" against "enhance the sync script".

**The deliverable is the parent; work on it are children.** A Deliverable is never finished — it accumulates features for as long as it exists. A tool enhanced three times has one Deliverable row and three Features beneath it, not three peer rows.

`Class` is the distinction between what the project exists to produce and what it needs in order to run. A business case or a project management plan is a real, tracked deliverable that no stakeholder wants the project *for* — PRINCE2 calls these management products, PMBOK separates product scope from project scope. `Enabler` is the third case: work that serves the product without being visible in it, such as a migration or an architectural spike.

### Collection: `items`

| Field | Required | Description |
|--------|----------|-------------|
| ID | Yes | Stable identifier — plain sequential integer, assigned once, **never reused, never changed** even if the item is reparented or `Code` is renumbered. This is what anything external references: Execution-folder names, `Parent`, `Key Dependencies`, cross-links to other registers. |
| Parent | No | The parent item's **stable `ID`**, never its `Code`. Absent on a root. This is the only place the hierarchy is stored — `Code` merely displays it. |
| Code | Yes | Hierarchical/display position (1.1, 1.2, ...). Free to renumber whenever the structure changes; **never a reference key**. |
| Title | Yes | Short descriptive name. **On a Feature, name the thing, not the work that produced it** — `Artifact Register (FSP.23)`, not `Artifact Register rebuilt AI-first as JSON, replacing the DCL`. A deliverable's title is read in a list of deliverables, where a sentence is unreadable; the detail belongs in `Description`, which is where it stays current anyway. |
| Type | Yes | Level — see the four axes above |
| Class | No | What kind of value the row serves. Defaults to `Product`. |
| Nature | No | What is being done to the thing. Defaults to `Build`. |
| Delivers | No | Artifact kind, on rows that produce one |
| Key Deliverable | No | `Y`/`N`. **Curation, not classification** — it marks what earns a line in an executive report, which is a smaller set than everything with `Class: Product`. Valid only on `Deliverable` and `Feature` rows, since a Story or Task names activity and activity cannot be reported as a deliverable. |
| Description | No | What needs to be done |
| Acceptance Criteria | No | How completion is verified |
| Owner | No | Person responsible |
| Estimated Effort (h) | No | Hours estimate |
| Category | No | PMBOK area or project-specific grouping |
| Status | Yes | Portfolio Backlog / Funnel / Not Started / Implementing / Done / Cancelled |
| Priority | No | Must / Should / Could / Won't (MoSCoW) |
| Sprint Planned / Added / Ended | No | Sprint IDs (e.g. S25.15) |
| Key Dependencies | No | IDs of blocking items |
| Control Approach | No | How the deliverable is verified (review, functional test, ...) |
| Control Tool | No | Where that verification happens |
| Project Phase | No | PMBOK phase |
| Planned Release / Released On | No | Deliverable dates |
| Action Plan | No | Approach description |
| Planning Considerations | No | Assumptions, risks, constraints |
| Validation Approach | No | How the deliverable will be verified |
| Comments | No | General notes |

There is **no `key_deliverables` collection.** A deliverable is a row whose `Key Deliverable` is `Y`; the deliverables view filters on it and rolls progress up from descendants through `Parent`. A register still carrying that collection has not been migrated — run `wbs.py migrate`.

## Critical Design Rules

1. **The register is the source of truth; the dashboard is generated.** Never hand-edit the HTML — it is overwritten in full on every refresh.
2. **`ID` is never reused and never changed.** Renumber `Code` freely instead.
3. **Use `wbs.py` for the edits with rules attached** — claiming an ID, setting `Parent`, tagging `Key Deliverable`, anything vocabulary-bound. Reaching for `registry.py` to do those by hand bypasses the rules rather than following them. Everything else is a plain field edit: `R.load`, change the row, `R.save`, which keeps `updated` and `values_hash` correct.
4. **`Parent` holds a stable `ID`, never a `Code`.** The hierarchy has to survive renumbering, and `Code` is renumbered by exactly the restructuring the parenting rule invites.
5. **Deliverables are a view, not a collection.** Never reintroduce a parallel list — the link between a deliverable and the work that delivers it is `Parent`, and a second collection cannot express it.
6. **No derived values in the register** — effort rollups, counts and percentages are computed by the dashboard generator, not stored.
7. **Field order doesn't matter** in a row; `meta.settings.fields` defines display order.

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

```bash
python <skill-path>/scripts/wbs.py add "<register>" "Title" --type Story --parent 37 --code 3.4
```

Claims the next ID, refuses a `Parent` that does not exist or would close a cycle, holds every vocabulary field to the register's own vocabulary, and keeps `Key Deliverable` off rows that cannot carry it. Defaults: Status `Portfolio Backlog`, Type `Story`, Nature `Build`. Choose `Code` as the hierarchical position; it is display only. Omit fields that have no value rather than writing empty strings. Then **refresh the dashboard** (operation 5).

### 3. Edit items

```bash
python <skill-path>/scripts/wbs.py set "<register>" --id 42 --status Done --nature Improve
```

Find rows by `ID`, never `Code`. Pass `--field ""` to clear a field. Then **refresh the dashboard** (operation 5).

### 3b. Validate

```bash
python <skill-path>/scripts/wbs.py check "<register>"
```

Reports duplicate IDs, parents that do not exist or close cycles, vocabulary violations, `Key Deliverable` on rows that cannot carry it, and rows with no Type. Run it before a planning ceremony and after any hand-edit.

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

## Vocabularies

| Type (level) | Class (kind of value) |
|---|---|
| Deliverable · Feature · Story · Task | Product · Management · Enabler |

| Delivers (artifact) | Nature (what is being done) |
|---|---|
| Tool · System · Process · Document | Build · Improve · Analyse · Fix · Maintain |

Definitions for each level are in "The four axes" above. All five vocabularies live in the register's `meta.settings.vocabularies` and are enforced by `wbs.py check`.

### Migrating an older register

```bash
python <skill-path>/scripts/wbs.py migrate "<register>" [--apply]
```

Dry run unless `--apply`. Maps the old single-axis `Type` onto the three axes (`Tool` → Feature + Delivers Tool, `Improve` → Story + Nature Improve, and so on), fills `Parent` from the `Code` strings, registers the vocabularies, and drops `key_deliverables` **only if it is empty** — populated rows are flagged instead, since folding them into `items` as Feature rows is a judgment call. Snapshot the register first.

The mapping is a sensible default, not an oracle: `DocSection` becomes a Story, which is right for a leaf section and wrong for a top-level deliverable that happens to produce documents. Read what it did before accepting it.

## Sprint ID Convention

Format: `S{YY}.{NN}` — e.g. S25.15 means year 2025, sprint 15.

## Relationship to Other Tools

- **Task tracker** = committed/active work (what is being done this sprint)
- **RAID** = risks, actions, issues, decisions
- **WBS** = full roadmap/backlog (what could be done, what's planned, what's done)

Items flow from the WBS into your task tracker when committed to a sprint. The WBS captures the thinking and planning before commitment.
