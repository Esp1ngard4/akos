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
      dates.py                <- Variable-precision schedule dates; the only place
                                 precision and variance are decided
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
  "items": [ {...} ],
  "sprints": [ {"Sprint": "S26.Q3.5", "Starts": "2026-08-30", "Ends": "2026-09-12"} ],
  "schedule_log": [ {"ID": 1, "Changed On": "2026-09-20", "Item": 42,
                     "Field": "Planned End", "From": "Mar-26", "To": "May-26",
                     "Reason": "vendor delay"} ]
}
```

- **`values_hash`** fingerprints the rows, not the file — it excludes `meta`, so reindenting is not a data change. A generated dashboard stamps the hash it was built from, which is how `registry.stale_views()` can tell you a dashboard has gone stale rather than quietly showing old numbers.
- **Rows omit their empty fields.** Do not write `null` or `""` to mean "no value"; leave the key out. `meta.settings.fields` carries the canonical field order for rendering a rectangular table.
- **`schedule_log` is why a date moved**, one row per change. Structured rather than free text, because the slip count has to be countable.
- **`sprints` is the imported calendar**, not a locally-authored one — see "Sprints" below. Absent, or empty, means the project is not run in sprints, and sprint IDs then go unvalidated rather than being rejected.
- **A register may carry extra collections** beyond `items` and `sprints` when a project has structured data that belongs with its WBS. The dashboard reads `items` only.

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

The noun/verb column is the quickest test in practice: deliverables and features name *things*, stories and tasks name *activity*. "Renovated kitchen" against "install the cabinets"; "Calendar integration" against "enhance the sync script".

**The deliverable is the parent; work on it are children.** A Deliverable is never finished — it accumulates features for as long as it exists. A tool enhanced three times has one Deliverable row and three Features beneath it, not three peer rows.

`Class` is the distinction between what the project exists to produce and what it needs in order to run. A business case or a project management plan is a real, tracked deliverable that no stakeholder wants the project *for* — PRINCE2 calls these management products, PMBOK separates product scope from project scope. `Enabler` is the third case: work that serves the product without being visible in it, such as a migration or an architectural spike.

### Collection: `items`

| Field | Required | Description |
|--------|----------|-------------|
| ID | Yes | Stable identifier — plain sequential integer, assigned once, **never reused, never changed** even if the item is reparented or `Code` is renumbered. This is what anything external references: Execution-folder names, `Parent`, `Key Dependencies`, cross-links to other registers. |
| Parent | No | The parent item's **stable `ID`**, never its `Code`. Absent on a root. This is the only place the hierarchy is stored — `Code` merely displays it. |
| Code | Yes | Hierarchical/display position (1.1, 1.2, ...). Free to renumber whenever the structure changes; **never a reference key**. |
| Title | Yes | Short descriptive name. **On a Feature, name the thing, not the work that produced it** — `Artifact Register (TSP.5)`, not `Artifact Register rebuilt AI-first as JSON, replacing the DCL`. A deliverable's title is read in a list of deliverables, where a sentence is unreadable; the detail belongs in `Description`, which is where it stays current anyway. |
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
| Baseline Start / End | No | The original commitment. **Write-once** — `set` refuses to overwrite one; `rebaseline` is the verb. A parent may carry its own. |
| Planned Start / End | No | The current expectation. **Derived on any row with children** and refused there. Every change needs `--reason` and appends to `schedule_log`. |
| Actual Start / End | No | What happened. Derived on a parent. `check` holds them against Status. |
| Horizon | No | `Next` / `Future` — how soon this is wanted. Not a status and not a priority: an item can be `Could` and `Next`, or `Must` and `Future`. Cleared by a real sprint or by closure; `check` enforces both. |
| Sprint Planned / Added / Ended | No | Sprint IDs from the register's `sprints` calendar (e.g. `S26.Q3.5`), and nothing else. `check` rejects an ID the calendar does not hold. |
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

Reports duplicate IDs, parents that do not exist or close cycles, vocabulary violations, `Key Deliverable` on rows that cannot carry it, and rows with no Type.

It also holds the two time fields apart, which is what stops `Horizon` rotting into noise:

- **`Horizon` on a `Done` or `Cancelled` row** — closing the row settles how soon it was wanted.
- **`Horizon` alongside a `Sprint Planned`** — a commitment supersedes an intention.
- **A sprint ID the calendar does not hold**, in any of the three sprint fields. Silent when the register has no calendar: with nothing to check against, guessing would be worse than saying nothing.

And it holds the schedule dates against reality:

- **`Actual End` set but Status is not `Done` or `Cancelled`** — two answers to whether something finished is one too many.
- **`Actual Start` set on a `Not Started`, `Portfolio Backlog` or `Funnel` row.**
- **An End before its Start**, within each of the three pairs.
- **A plan or actual stored on a parent** — a warning: it is derived at render time, so the stored value is silently ignored.
- **`Sprint Planned` and `Planned End` in different periods** — also a warning. The calendar makes them comparable, and disagreement is usually a stale field rather than a mistake.

Run it before a planning ceremony and after any hand-edit.

### 4. Sprint planning
Grooming sets the horizon; planning turns it into a commitment.

- **Grooming** — `--horizon Next` for the upcoming sprint, `Future` for the one after.
- **Planning** — set `Sprint Planned` to a sprint ID the calendar holds, and **clear `Horizon` in the same edit** (`--horizon ""`). `check` will otherwise flag the row.
- When an item starts: Status → `Implementing`, `Sprint Added` → current sprint.
- When an item completes: Status → `Done`, `Sprint Ended` → current sprint, and `Horizon` must be gone.
- Multiple items can share a sprint. After changes, **refresh the dashboard** (operation 5).

### 5. Generate dashboard
```bash
python <skill-path>/scripts/refresh_wbs.py "<register.json>" "<output-html-path>" "<project-name>"
```
Generates a self-contained HTML file with:
- **KPI strip** — total items, implementing, done, not started, total effort, planned sprints
- **Sprint Board tab** — items grouped by sprint with status badges, filterable by status/priority/type
- **Analytics tab** — status distribution, priority breakdown, sprint effort allocation
- **Roadmap tab** — baseline, plan and actual as three bars per row, with a **zoom control** (day / month / quarter / sprint). **Slip is drawn, not listed** — a hatched band runs from where a row was promised to where it now lands, red when late and green when early, dashed at the promise and arrowed at the landing. It reads as the distance it is, costs no column, and appears on no row that never had a baseline to miss. A row that moved more than once carries the count; the full phrase is on hover.

  Two things make a wide chart readable rather than just correct: **rows alternate in tone**, because the eye travels a long way from a name to its bars and a hairline rule does not survive that trip; and a dashed **Today** line marks where now falls, which is the reference every other bar is read against. That line is computed when the page opens, not when it is generated, so it stays right without a refresh.

  **A row assigned to a sprint is dated, not undated.** Where a row has no `Planned` dates of its own but names a sprint the calendar holds, the roadmap draws it across that sprint's window and marks the bar as sprint-sourced; `Sprint Added` and `Sprint Ended` do the same for actuals. An explicit date always wins. This is the one-timeline idea taken literally — without it such a row falls into the undated list while the calendar knows exactly when it runs. Zoom changes the tick density, not the geometry: once a sprint has dates, the sprint view *is* the date view at sprint granularity, which is why there is one timeline here and not two roadmap models. Dates alone do not say what is finished, so each row also carries a **status stripe** and a **progress cell**, and the view opens with one line saying how much of the planned work is done.

  **Progress is measured over leaves, by effort where there is any and by count where there is not.** Only leaves carry effort that is really theirs — adding a parent's own estimate to its children's would count the same work twice. Saying "3 of 7 items" on a row whose hours are unknown is honest; inventing hours to produce a percentage is not. **Cancelled work is excluded from both halves** — it is not work that will be done, so leaving it in the denominator would understate real progress, and the figure does not move when the cancelled toggle does.

Two conventions that run across every view:

- **Derived values look derived** — a rolled-up bar is dashed and paler than a stored one, so a parent's span is never mistaken for a commitment someone made.
- **Rows with no dates are listed, not hidden.** An undated row in a roadmap is a gap to fix, and hiding it hides the gap — the same reason an untyped row shows a red em dash rather than a blank.
- **Cancelled rows are hidden by default, with a toggle.** The status exists so a dropped item keeps the record of why, but it is noise in the common case and on a roadmap it draws bars for work that will never happen. The toggle matters as much as the default.

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

| Horizon (how soon) |
|---|
| Next · Future |

Definitions for each level are in "The four axes" above. All six vocabularies live in the register's `meta.settings.vocabularies` and are enforced by `wbs.py check`.

### Migrating an older register

```bash
python <skill-path>/scripts/wbs.py migrate "<register>" [--apply]
```

Dry run unless `--apply`. Maps the old single-axis `Type` onto the three axes (`Tool` → Feature + Delivers Tool, `Improve` → Story + Nature Improve, and so on), fills `Parent` from the `Code` strings, registers the vocabularies, and drops `key_deliverables` **only if it is empty** — populated rows are flagged instead, since folding them into `items` as Feature rows is a judgment call. Snapshot the register first.

The mapping is a sensible default, not an oracle: `DocSection` becomes a Story, which is right for a leaf section and wrong for a top-level deliverable that happens to produce documents. Read what it did before accepting it.

## Schedule dates

Six fields — `Baseline`, `Planned` and `Actual`, each a Start and an End. They replace `Planned Release` and `Released On`, which folded into `Planned End` and `Actual End`: eight overlapping date fields would let a row hold two answers to when it shipped.

### Three forms, and precision is never invented

| You write | It means | Precision |
|---|---|---|
| `2026-Mar-12` | that day | day |
| `Mar-26` | 1–31 March 2026 | month |
| `Q1-26` | 1 Jan – 31 Mar 2026 | quarter |

**The register stores the string you typed.** Precision is derived at read time and never written back — rewriting `Q1-26` as `2026-03-31` would invent a confidence nobody has. Anything unparseable is **rejected, not coerced**: a date nobody can read is worse than a blank one, because blank is honestly unknown.

**Variance is computed at the coarser of the two precisions compared.** Baseline `Q1-26` against a plan of `2026-Mar-12` is *on plan*, not "19 days early" — the commitment was only ever quarter-accurate. Variance is then reported in that precision's own unit, never converted into a false one.

All of this lives in `scripts/dates.py`, and **only there**. The dashboard receives instants already resolved by `refresh_wbs.py`, so there is one implementation rather than a Python one and a JavaScript one drifting apart.

### The baseline is write-once

```bash
python <skill-path>/scripts/wbs.py rebaseline "<register>" --id 42     --baseline-end Q2-26 --reason "scope grew after discovery"
```

`set` refuses to overwrite a baseline date. A baseline that can be quietly edited is not a baseline, it is just another plan — so moving one is its own verb, it requires a reason, and it records what the value was.

### Every planned move is logged

`set --planned-end` requires `--reason` and appends to `schedule_log`. This is the point of the whole feature: today's variance says a deliverable is late, but the log says it has moved right three times, and the second is the more useful signal. The **slip count** is how many log entries moved `Planned End` later.

### Parents derive, leaves carry

`Planned` and `Actual` on a row with children are the span of its descendants, computed at render time and never stored; `wbs.py` refuses to set them there. A **baseline** is different — committing to a deliverable is a real commitment made at that level, so it is stored, and comparing it against derived actuals is exactly the insight worth having.

## Sprints

**The WBS does not define the cadence.** The sprint ceremonies own it, each project records its own instance in a planning folder, and the register imports a copy. A project with no conventions file is not run in sprints — a valid and common state, and the roadmap then falls back to dates alone.

**`S<YY>.Q<N>.<X>`** — `S26.Q3.5` is the fifth sprint of Q3 2026. A sprint belongs to the quarter it *starts* in and keeps its length at the boundary, so quarters hold uneven counts and the year's last sprint runs into the next one. This beats a running count: a project starting mid-year joins the rhythm already running instead of opening its own count at 1.

### Seed a project's calendar

```bash
python <skill-path>/scripts/wbs.py sprints seed "<project>/<planning folder>/agile-conventions.json" \
    --scope "Project name" --year 2026 --anchor 2026-07-19
```

`--anchor` is **a real sprint start date taken from a ceremony record, never 1 January.** The derived grid and the actual cadence are not the same thing, and where they disagree the record is right.

This is a seed. Once a ceremony moves, edit the row — the stored date is the record, and reseeding would discard it. `seed` refuses to overwrite without `--force` for that reason.

### Import it into the register

```bash
python <skill-path>/scripts/wbs.py sprints import "<register>" --from "<conventions file>"
```

Prints a diff rather than overwriting silently, and **refuses to drop a sprint that items still reference** unless forced. The register keeps its own copy so it stays self-contained — no register reads another file at runtime — which is the same relationship the dashboard has with the register: generated, explicit, detectably stale.

## Relationship to Other Tools

- **Task tracker** = committed/active work (what is being done this sprint)
- **RAID** = risks, actions, issues, decisions
- **WBS** = full roadmap/backlog (what could be done, what's planned, what's done)

Items flow from the WBS into your task tracker when committed to a sprint. The WBS captures the thinking and planning before commitment.
