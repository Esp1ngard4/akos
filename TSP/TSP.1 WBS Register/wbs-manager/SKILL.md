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

Support material for a WBS item (discovery, specs, plans, notes, inputs) always lives in the project's `1. Execution/` folder. There is no fallback or alternate location. If the project has no `1. Execution/` folder yet, create one as part of setting up its WBS.

**Organise by piece of work, not by document type.** People read later to find out what happened with one piece of work. A `Plan/` or `Discovery/` folder would scatter that story across several places.

- **One folder per Deliverable or Feature:** `WP.<ID> <Brief Title>`, keyed off the stable `ID`, never `Code`. `Code` is renumbered as the WBS evolves, and a name keyed off it goes stale silently.
- **Flat until it isn't.** A Story's documents are loose files in its parent's folder, prefixed `WP<ID>` (e.g. `WP12 Gap Analysis.md` inside `WP.3 Dashboard Enhancement/`). Once a Story or sub-deliverable has about three documents of its own, it gets a nested `WP.<ID> <Title>/` folder.
- **Two folders by kind, both for material that is not ours to edit,** created when there is something to put in them:
  - `Inputs/`: material received from outside (a client, a vendor, an external spec), kept as received;
  - `Deliverables/`: what was handed over, frozen as sent.
- **The document type is the filename's suffix:** `WP<ID> <Title> - <Type>.md`.

| Type | What to expect |
|---|---|
| Discovery | What was found: the current state, the problem, the evidence |
| Assessment | Options weighed against criteria, a recommendation, and the agreed outcome |
| Specification | What will be built: requirements, detailed acceptance criteria, design |
| Plan | Steps, sequence, sizing |
| Notes | Meetings and decisions as they happened, dated |
| Input | External material that informed the work, with a line saying how it was used |

- **A header names the row and the date, never the status:** `**Story:** ID 12 · **Written:** 2026-03-12`. The status lives in the register; a status copied into a document goes stale. `refined` finds a row's spec by the `ID <n>` in its first lines.
- **A replaced document goes to a `PreviousV/` beside it,** never deleted.
- **Existing folders are not retrofitted** to match.

**A project's own layout.** Where a project's folders differ from these names, its register declares the difference once, in `meta.execution`:

```json
"execution": {"folder": "../../01. Work", "inputs": "Client input", "deliverables": "Sent to client"}
```

`folder` is relative to the register's own folder. Declare only what differs; anything left out follows the standard. **Read `meta.execution` before filing anything.** The dashboard header shows the declared differences, and nothing when a project follows the standard. With `folder` declared, `refined` checks specs without being given `--execution`. The project's top level is the Artifact Register's (TSP.5) to record where the project has one, and the register takes precedence there.

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
| Planned Start / End | No | The current expectation. **Derived on any row with children** and refused there. The first value needs no reason; every later change, clearing included, needs `--reason` and appends to `schedule_log`. |
| Actual Start / End | No | What happened. Derived on a parent. `check` holds them against Status. |
| Horizon | No | `Next` / `Future` — how soon this is wanted. Not a status and not a priority: an item can be `Could` and `Next`, or `Must` and `Future`. Cleared by a real sprint or by closure; `check` enforces both. |
| Sprint Planned / Added / Ended | No | Sprint IDs from the register's `sprints` calendar (e.g. `S26.Q3.5`), and nothing else. `check` rejects an ID the calendar does not hold. |
| Sprint Carried | No | A **list** of the sprints the row was committed to again after `Sprint Planned` — spillover, or the next slice of a deliverable worked across sprints. `set --sprint-carried S --reason "…"` adds one and notes `Carried into S: …` in Comments — refused without the reason; `--sprint-carried ""` clears the list. Never repeats `Sprint Planned`. For a row with nothing done; **partly done work is split instead** (operation 4b). |
| Key Dependencies | No | IDs of blocking items |
| Control Approach | No | How the deliverable is verified (review, functional test, ...) |
| Control Tool | No | Where that verification happens |
| Project Phase | No | PMBOK phase |
| Planned Release / Released On | No | Deliverable dates |
| Action Plan | No | Approach description |
| Planning Considerations | No | Assumptions, risks, constraints |
| Validation Approach | No | How the deliverable will be verified. **Optional, and not asked for:** a requirement's acceptance criteria and its closure verdict already say how it is verified and whether it was (see the Verification tab) |
| Comments | No | A log of dated entries, **newest on top**, one paragraph each — written with `wbs.py note`. A **closure note** from `set --closure` stays pinned above them (see operation 3) |

There is **no `key_deliverables` collection.** A deliverable is a row whose `Key Deliverable` is `Y`; the deliverables view filters on it and rolls progress up from descendants through `Parent`. A register still carrying that collection has not been migrated — run `wbs.py migrate`.

## Critical Design Rules

1. **The register is the source of truth; the dashboard is generated.** Never hand-edit the HTML — it is overwritten in full on every refresh.
2. **`ID` is never reused and never changed.** Renumber `Code` freely instead.
3. **Use `wbs.py` for the edits with rules attached** — claiming an ID, setting `Parent`, tagging `Key Deliverable`, anything vocabulary-bound. Reaching for `registry.py` to do those by hand bypasses the rules rather than following them. Everything else is a plain field edit: `R.load`, change the row, `R.save`, which keeps `updated` and `values_hash` correct.
4. **`Parent` holds a stable `ID`, never a `Code`.** The hierarchy has to survive renumbering, and `Code` is renumbered by exactly the restructuring the parenting rule invites.
5. **Deliverables are a view, not a collection.** Never reintroduce a parallel list — the link between a deliverable and the work that delivers it is `Parent`, and a second collection cannot express it.
6. **No derived values in the register** — effort rollups, counts and percentages are computed by the dashboard generator, not stored.
7. **Field order doesn't matter** in a row; `meta.settings.fields` defines display order.
8. **A refused save means someone else wrote first.** `registry.save` refuses when the register changed on disk after it was loaded (another session or a sync saved in between), and writes nothing. Reload, make the change again, and save. `force=True` is only for an overwrite the user has asked for, never a way past the refusal.

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

**Closing a row takes a closure note.** Moving a row to `Done` or `Cancelled` is refused without `--closure`, the way moving a planned date is refused without `--reason`:

```bash
python <skill-path>/scripts/wbs.py set "<register>" --id 42 --status Done \
  --closure "What happened: <what was delivered>. AC: (1) <criterion> - met. (2) <criterion> - partial: <why>, <where the rest went>. Follow-up: <task or row, or none>."
```

It goes at the **top** of `Comments` as `Closure 2026-Sep-26 (Done): …` — newest first, the order a TD's version history keeps, because a closed row is read for how it ended. The convention:

- **What happened** — what was actually delivered, in a sentence or two. Evidence where there is some: a commit, a record, a TD version.
- **AC** — each acceptance criterion by number: met, partial or not met. **Any gap says why**, and where the missing part went.
- **Follow-up** — the task or row that picks up anything left over, by stable `ID`. `none` is an answer.
- For `Cancelled`: why it was dropped, and where anything it held went.

If the work was also tracked as a task, its closure comment can say the same — but a task's comment goes out of view once the task is completed, and the row is what gets read afterwards. Only the transition asks: correcting a date on a row that is already closed needs no new note, and `--closure` on a row that is not closing is refused.

**Every other entry in `Comments` goes through `note`:**

```bash
python <skill-path>/scripts/wbs.py note "<register>" --id 42 "Scope revised: was X (3h), now Y - because Z."
```

It stamps the date and puts the entry on top, **below any closure note** — a closed row is read first for how it ended, so the closure stays pinned however much is added after it. One paragraph per entry, because the blank line is what separates them. Rows written before this convention hold their entries run together in one paragraph, oldest first; they are re-cut by reading them, not by script, since the entries are woven into prose.

**Starting work the sprint never committed to asks first.** Moving a row to `Implementing` or `Done` (through `set` or `add`) is refused when the sprint running today has not committed to it: not planned or carried into it, not pulled in already, and not under a parent that is. **A parent counts only when it is committed itself:** a committed child does not make it so, since a parent's own acceptance criteria can stay unmet when every child is done. When a sprint means to close a parent (a goal naming a key deliverable), commit the parent at planning too; otherwise its close is asked like any other row. Ask the user which of two it is, then pass the answer:

```bash
python <skill-path>/scripts/wbs.py set "<register>" --id 58 --status Implementing --pulled-in "displaces nothing"   # or "delays <scope> 61"
python <skill-path>/scripts/wbs.py set "<register>" --id 58 --status Done --closure "..." --outside-sprint "a correction of past work"
```

`--pulled-in` sets `Sprint Added`, notes the effect on the row and prints the line for the sprint record's *Committed items*, with `Area` left for the user to fill: add it the same day (sprint-facilitator, *A pull-in states its effect*). `--outside-sprint` notes why and marks nothing. Never pick the answer: it is the user's. Other edits to an uncommitted row are not asked about.

**The daily check** lists rows pulled into the running sprint that its record does not name yet, across every WBS register under a root folder (found by `meta.kind`, so a register created mid-sprint is included). The record is found as the sprint ceremonies find theirs (`<sprint>.md`, first line `# Sprint `), or named with `--records`. It reads an item as `<scope> <ID> <title>`, `<scope> 3, 4 <title>` for several rows, or the IDs in brackets after the title. The daily loop's evening runs it:

```bash
python <skill-path>/scripts/wbs.py pullins [--root <folder>] [--sprint <ID>] [--records <folder>]
```


### 3b. Validate

```bash
python <skill-path>/scripts/wbs.py check "<register>"
```

Reports duplicate IDs, parents that do not exist or close cycles, vocabulary violations, `Key Deliverable` on rows that cannot carry it, and rows with no Type.

It also holds the two time fields apart, which is what stops `Horizon` rotting into noise:

- **`Horizon` on a `Done` or `Cancelled` row** — closing the row settles how soon it was wanted.
- **`Horizon` alongside a `Sprint Planned`** — a commitment supersedes an intention.
- **A sprint ID the calendar does not hold**, in any of the three sprint fields. Silent when the register has no calendar: with nothing to check against, guessing would be worse than saying nothing.
- **A committed row still in `Portfolio Backlog` or `Funnel`** — a warning. A commitment means `Not Started`.
- **An open parent whose own estimate differs from its leaves' sum** — a warning, under the 100% rule: a parent's children make up 100% of its work, so its own estimate (made before it was broken down) is compared with theirs, never added to it. Below it, the breakdown is incomplete or leaves are unestimated; above it, scope grew. Closed parents are not checked: their difference is history, shown on the Breakdown. `add --parent` reminds you when the parent carries an estimate.

And it holds the schedule dates against reality:

- **`Actual End` set but Status is not `Done` or `Cancelled`** — two answers to whether something finished is one too many.
- **`Actual Start` set on a `Not Started`, `Portfolio Backlog` or `Funnel` row.**
- **An End before its Start**, within each of the three pairs.
- **A plan or actual stored on a parent** — a warning: it is derived at render time, so the stored value is silently ignored.
- **A `Done` row with no `Actual End`, or an `Implementing` row with no `Actual Start`** — warnings. The roadmap cannot place such a row, and this is the direction of the implication that actually rots.
- **`Sprint Planned` and `Planned End` in different periods** — also a warning. The calendar makes them comparable, and disagreement is usually a stale field rather than a mistake.
- **A closed row with no closure note** — a warning. `set` refuses that close, so one of these was closed by hand-edit. A register adopting the rule part-way sets `meta.settings.closure_notes_from` to an ISO date, and only rows closed on or after it are checked; older notes are a backfill chosen by the outcome each delivered, not a sweep.

And it holds commitments to the work they name:

- **An open parent committed to a sprint with none of its children in it** — a warning. A committed parent takes its hours from its children in the sprint, so with none there the work that finishes it is not named: a refinement gap. `refined` reports the same before planning.
- **An open row carried into two or more sprints** — a warning: re-scope it, break it down, or drop it out loud. A split's rest inherits the commitment history, so a remainder pushed again is caught too.

Run it before a planning ceremony and after any hand-edit.

### 4. Sprint planning
Grooming sets the horizon; planning turns it into a commitment.

- **Grooming** — `--horizon Next` for the upcoming sprint, `Future` for the one after.
- **Planning** — set `Sprint Planned` to a sprint ID the calendar holds, and **clear `Horizon` in the same edit** (`--horizon ""`). `check` will otherwise flag the row. **A commitment means `Not Started`:** committing a `Portfolio Backlog` or `Funnel` row (`--sprint-planned` or `--sprint-carried`) moves it to `Not Started` and says so, unless `--status` is passed with it. **A row already planned into an earlier sprint and not Done** keeps its `Sprint Planned`; add the new sprint with `--sprint-carried` and a `--reason` saying why it did not finish. Work committed at a planning counts to that sprint from that moment, even if it finishes before the sprint's start date.
- When an item starts: Status → `Implementing`, and `Actual Start` is stamped with it. A row the sprint did not commit to asks first: a pull-in (`Sprint Added` → current sprint) or work outside the sprint (see operation 3).
- When an item completes: Status → `Done`, `Sprint Ended` → current sprint, `Horizon` must be gone, and `Actual End` is stamped.
- Multiple items can share a sprint. After changes, **refresh the dashboard** (operation 5).

**A committed parent is legitimate** — it is the promise that the deliverable lands this sprint. It counts as an item; its hours are its children's in the sprint (see Sprint metrics), so commit the work that finishes it alongside it.

### 4b. Split partly done work

At the close-out, a committed leaf that did not finish is asked one question: was any of it delivered? **Nothing** → carry it whole (`--sprint-carried`). **Something** → split it:

```bash
python <skill-path>/scripts/wbs.py split "<register>" --id 42 --delivered 6 --sprint S26.Q4.1 \
  --closure "What happened: … AC: (1) met. (2) partial: rest in the new row." [--rest-effort 4]
```

- **The row becomes the parent of two pieces**, and keeps its ID, sprint commitment, baseline and own estimate, which the Breakdown then shows as the original (*10h → 6h + 4h*). It stays open until the rest closes.
- **The done piece** closes `Done` in `--sprint` (default: the row's latest) with the delivered hours, the closure note and the row's `Actual Start`.
- **The rest piece** is `Not Started`, with the remaining hours (default: the estimate less `--delivered`), the `Planned` dates and `Tracked Externally`.
- **Both carry the row's commitment history** (`Sprint Planned`, `Sprint Added`, `Sprint Carried`), so every sprint that committed to the work still counts it, and the delivered hours land where they were done.
- **Splitting a piece again** closes that piece with what was delivered and adds the rest beside it, under the same parent: a split cuts by sprint, not by meaning, so it adds no layer. Add layers yourself wherever they represent the work.
- Refused on a row with children (close or carry them instead), a closed row, and a row never in the sprint.
- It says what to change in the task tracker: the open task now serves the rest piece, with the hours left. Planning then carries the rest piece with `--sprint-carried`, and the parent only when the deliverable is promised again.

The schedule dates hang off these same moments rather than forming a separate routine — see **When each date is written** below for which field belongs to which. Committing to a sprint is also when a story's **baseline** is set, and it is set once.

### 5. Generate dashboard
```bash
python <skill-path>/scripts/refresh_wbs.py "<register.json>" "<output-html-path>" "<project-name>"
```
Generates a self-contained HTML file with:
- **KPI strip** — total items, implementing, done, not started, total effort (leaves only), planned sprints
- **Current Sprint tab** — one sprint as a board: **lanes by the deliverable each card serves**, columns To do / Doing / Done. The lane is the card's nearest `Deliverable` ancestor, else its root; a card with no parent goes in a final *No deliverable* lane, so the gap shows. Each card shows the levels between it and its lane, and a tag when it was **carried in** or **pulled in**; a committed card still in `Portfolio Backlog` or `Funnel` is flagged. A parent card shows its hours *in sprint*, its children's on the board, and the column and lane totals add leaves only. The lane header carries the deliverable's overall progress and the sprint's hours in it. A switch drops the lanes for a plain board.
  - **Which rows are in the sprint, and the header's figures, come from `wbs.py`** (`sprint_board`, `sprint_metrics`), embedded per sprint at generation. `sprint_board()` decides each card's role, lane and path once; a report that shows the sprint as a board should use it too, so a card sits in the same lane everywhere. The header therefore reads the same as `wbs.py metrics --sprint` for that sprint; never recompute them in the page.
  - **Which sprint is current is decided when the page opens**, from the calendar, like the Roadmap's Today line, so it stays right between refreshes. A picker shows any other sprint. While today's sprint has cards, the dashboard opens on this tab.
  - **Read-only**, like the rest of the dashboard: a card moves through `wbs.py set`. One project per dashboard: a sprint that spans several projects is a cross-project report's job, not the dashboard's.
- **Sprint Board tab** — every sprint's items as a table, with status badges, filterable by status/priority/type: the history view
- **Breakdown tab: effort rolls up bottom-up.** A parent's effort is its leaves' sum and its progress is over its leaves - never its own estimate added on top. Where a parent carries its own estimate it shows as the original one, with the difference (*est. 10h → 27h (+17h)*); unestimated leaves are counted (*2 of 7 unestimated*), never filled in.
- **Verification tab** — every requirement (Feature and Story) with the deliverable and parent it traces to, how many acceptance criteria it states, and its verification read from its closure note: *verified*, *partly met*, *not met*, *no verdict*, *open*, or *referred* (a row split from another keeps its verdict there). A gap shows where its follow-up went. Flags: committed or staged with no AC; closed with no AC verdict (since the register's `meta.settings.closure_notes_from` date, where set); partly or not met with no follow-up. This is a traceability matrix's verified column, read from the closure notes rather than kept by hand, and the drill-down behind the status report's *On Quality*.
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
| Cancelled | Dropped without being delivered — keep the row; `--closure` records why |

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

### When each date is written

The dates are only as good as the moment they are captured, and a field nobody is prompted for is a field nobody fills. **Status is the trigger:** an actual date and a status change are two halves of one fact, so `wbs.py set --status` stamps the matching date itself and says it did — and so does `add --status`, since adding a row is the first write of its status.

| Field | Written | At |
|---|---|---|
| `Baseline Start` / `End` | **once**, when the commitment is made | Sprint planning for a story; roadmap agreement for a deliverable. Never edited afterwards — `rebaseline` moves it and records why. |
| `Planned Start` / `End` | at refinement, and again whenever the expectation changes | Backlog grooming and sprint planning. Every later move needs `--reason` and lands in `schedule_log`. |
| `Actual Start` | when work actually begins | Status → `Implementing`. Stamped automatically. |
| `Actual End` | when the row closes | Status → `Done` or `Cancelled`, at the grooming or retro that reviews it. Stamped automatically. |

**Never move a Status without its date.** That is the whole convention, and it is enforced from both sides: `check` rejects an `Actual End` on a row that is not closed, and warns about a closed row that has no `Actual End`. The second half is the one that matters — the first stops a wrong date, the second stops a missing one, and it was a missing one that let `Next`/`Future` rot unnoticed across 18 rows.

A stamped date is today's date, which is right when you close a row as you finish it and wrong when you are recording something from last week. It is announced on every write for exactly that reason; pass `--actual-end` to correct it.

**Parents are never stamped** — their actuals are the span of their children.

### The baseline is write-once

```bash
python <skill-path>/scripts/wbs.py rebaseline "<register>" --id 42     --baseline-end Q2-26 --reason "scope grew after discovery"
```

`set` refuses to overwrite a baseline date. A baseline that can be quietly edited is not a baseline, it is just another plan — so moving one is its own verb, it requires a reason, and it records what the value was.

### Every planned move is logged

Moving or clearing a planned date requires `--reason` and appends to `schedule_log`. Setting one for the first time does not: nothing was promised before it, so there is nothing to explain, and a log of filler reasons would bury the real ones. This is the point of the whole feature: today's variance says a deliverable is late, but the log says it has moved right three times, and the second is the more useful signal. The **slip count** is how many log entries moved `Planned End` later.

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

## Sprint metrics

```bash
python <skill-path>/scripts/wbs.py metrics "<register>" --sprint S26.Q3.5 [--json]
```

What one sprint delivered against what it took on. The retro runs this **before discussion opens**, so the session is insight-led rather than summarised afterwards.

Four populations, and the first two are kept apart deliberately — the gap between them is where over-commitment shows:

| | |
|---|---|
| **Committed** | `Sprint Planned` = the sprint, or the sprint is in `Sprint Carried`. What planning agreed to. |
| **Pulled in** | `Sprint Added` = the sprint but the row is not committed to it. Scope that arrived mid-sprint. |
| **Delivered** | `Sprint Ended` = the sprint and `Status` is `Done`. |
| **Carried over** | Committed, not delivered. Listed by ID, so the retro can discuss items rather than a number. |

These definitions live in `sprint_populations()`, and the dashboard's Current Sprint board draws from the same function.

**Hours come from leaves.** A committed or delivered parent counts as an item, and adds no hours of its own: its own estimate is the top-down figure its children replaced, so its hours in a sprint are its children's there, already counted. A 20h document committed with its 2h last piece is 2 items and 2h. Board cards follow the same rule (`sprint_board` gives each card its hours, a parent's as its children's on the board), and the dashboard's effort totals count leaves only.

**Hours count as committed in every sprint a row was planned into, and as delivered only in the sprint where it closes.** For a row with nothing done that is right: no work happened in the earlier sprint. Partly done work is split (operation 4b), so what was delivered lands in its sprint and only the rest moves on, while each sprint still shows what it committed.

Reported: **velocity** (count *and* hours — eight one-hour jobs is not two four-hour ones), **completion rate** by both count and hours, **carryover**, **committed against delivered hours**, and **median cycle time** from `Actual Start` to `Actual End`.

**A sprint spans whatever projects were in play**, so pass every register it touched:

```bash
python <skill-path>/scripts/wbs.py metrics "<register A>" "<register B>" --sprint S26.Q3.5
```

Totals come first, with a per-project split underneath — capacity belongs to the person, not to any one register. Three details make that safe: **item IDs are qualified by scope** (`Atlas#4`), since an ID is unique within a register and not across them; **a combined median is computed from the raw spans**, never by averaging medians; and **registers whose calendars disagree about the sprint are refused**, because the same ID over different dates describes a sprint that never happened. That last check is only possible — and only necessary — because projects share one cadence.

**Cancelled rows are excluded throughout.** Work that will not happen should neither flatter a sprint nor punish it.

**There is no effort-variance metric, deliberately.** It would need hours *spent*, and nothing records those — not the register, not the task tracker. Committed-against-delivered compares two numbers that exist and measures the thing a retro can act on.

**Every figure states its coverage, and a missing one says so.** A completion rate over rows that mostly lack an estimate is a different claim from one where they all have it. Where nothing carries `Sprint Planned`, there is no denominator and the command says that rather than reporting zero — inventing one is the same mistake as inventing a baseline.

`--json` emits the same structure for a caller to consume rather than re-parse.

### Key Deliverables before planning

```bash
python <skill-path>/scripts/wbs.py deliverables "<register A>" "<register B>" --by 2026-Oct-24 --sprint S26.Q4.1
```

Read-only. Per open row with `Key Deliverable = Y`, across every register given: a **baseline already passed**, or passing before `--by`; **nothing scheduling it** (no `Planned End`, `Horizon` or sprint on it or below it); and, with `--sprint`, **nothing committed to that sprint or staged `Next`** on it or below it. It lists findings, not verdicts — commit, rebaseline with a reason, or accept is the planning session's call. Run it the day before planning, while there is still time to act on what it finds.

### Is a candidate ready to commit to?

```bash
python <skill-path>/scripts/wbs.py refined "<register>" --ids 12,14,15 [--execution "<project>/1. Execution"] [--raid "<RAID register>"]
```

Read-only. For each candidate a grooming draft names, it reports what is absent: a description stating the problem (or one too thin to, under 20 characters), acceptance criteria, an action plan, an estimate, a parent, a Type. With `--execution`, also whether any Markdown file in that folder names the row (`ID <n>`); with `--raid`, the open RAID entries whose `WBS Ref` points at it (`<scope>#<id>`, matched against this register's `meta.scope`). A gap is a flag, not a veto: a Task may reasonably have no spec, and what counts as ready is the session's call. Run it at grooming, so planning starts from rows that are ready rather than refining them on the spot.

Whether rows and their tasks agree is **reconciliation**, and it is deliberately not here: it depends on the task tracker a project uses. TD.1 says what it checks and where to build it.

## Relationship to Other Tools

- **Task tracker** = committed/active work (what is being done this sprint)
- **RAID** = risks, actions, issues, decisions
- **WBS** = full roadmap/backlog (what could be done, what's planned, what's done)

Items flow from the WBS into your task tracker when committed to a sprint. The WBS captures the thinking and planning before commitment.
