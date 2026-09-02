---
name: raid-manager
description: Manages a RAID register - Risks, Actions, Issues, Decisions and Ideas - stored as a JSON register, and generates an interactive HTML dashboard with analytics and a risk heat map. Use whenever the user mentions "RAID", "risk register", "issue log", "decision log", or asks to add, edit or close a risk, action, issue or decision, to log an update or progress note against one, or wants a view of project risks and how the project is tracking.
---

# RAID Manager

A RAID register tracks risks, actions, issues, decisions and ideas for one project. The JSON register is the source of truth; the HTML dashboard is the visual analytics layer generated on top of it.

## Requirements

Python 3. **No dependencies** - standard library only.

Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Architecture

```
<Project folder>/
  0. PrjMgm/
    RAID/
      RAID <Project>.json        <- source of truth (human + Claude editable)
      RAID Dashboard.html        <- generated dashboard (visual, regenerated on demand)
      AuxMat/                    <- per-item supporting documents
        R5-vendor-risk-analysis/ <- subfolder per item needing working docs
        I3-permit-delay/

<skill-path>/scripts/
  registry.py     <- the shared JSON register format (load/save/hash)
  raid.py         <- the operations with rules attached (add/log/update/close/review/check)
  create_raid.py  <- builds an empty register
  refresh_raid.py <- generates the dashboard
```

### Folder conventions

- **Location**: the RAID register lives under `0. PrjMgm/RAID/` within the project folder. `0. PrjMgm` is the standard project management subfolder.
- **AuxMat**: created alongside the register when a new RAID is initialised. Contains one subfolder per RAID item that needs supporting documents (design notes, analysis, evidence, correspondence).
- **AuxMat subfolder naming**: `{Type initial}{ID}-{slug}` — e.g. `R5-vendor-risk-analysis`, `I3-permit-delay`, `A12-stakeholder-comms`. The slug is a short kebab-case description.
- **When to create an AuxMat subfolder**: when working on a RAID item requires creating documents beyond what fits in the register's Description, Action Plan, or Action Log fields. Not every item needs one.
- The `create_raid.py` script creates the `AuxMat/` folder automatically when generating a new register.

## RAID file discovery

A user may have RAID registers across several projects. Before any operation, locate the right file:

1. Use `Glob` with pattern `**/RAID*.json` across all connected folders.
2. Confirm `meta.kind == "raid-register"` — the same folder may hold a WBS or Artifact register.
3. **Single match** → use it directly.
4. **Multiple matches** → try to narrow down:
   - If the user named a project in their prompt (e.g. "refresh the Atlas RAID"), match against the filename or parent folder name (case-insensitive, fuzzy is fine).
   - If still ambiguous, present the matches using `AskUserQuestion` with the filenames/paths as options.
5. **No matches** → ask if they want to create a new RAID register (operation 6).

This discovery step runs before every operation — don't assume the same file as last time unless the user is clearly continuing on the same project within the conversation.

## How an entry is written

Every entry's `Description` follows one sentence shape, fixed per type. The shape is the point: a reader meets the same slots in the same order every time, so a register can be skimmed without re-reading each entry to work out which part is the cause and which is the consequence.

| Type | Shape |
|------|-------|
| **Risk** | Because of `<cause>`, there is a risk that `<uncertain event>`, which may result in `<impact if it happens>`. |
| **Issue** | Because of `<cause>`, `<what has gone wrong>`, which is resulting in `<impact being felt>`. |
| **Action** | Do `<the work>`, by `<when>`, so that `<outcome it buys>`. |
| **Decision** | Chose `<option taken>`, over `<alternatives rejected>`, because `<reason>`. |
| **Idea** | If `<the change>`, then `<expected benefit>`. |

Risk and Issue deliberately share their slots. An issue is a risk that already happened, so promoting one is a change of tense rather than a rewrite.

Two rules that make the shapes work:

- **A cause is not a restatement of the event.** "Because of the risk of delay, there is a risk that we are delayed" is the failure mode. The cause is the condition that already exists and is true today; the event is what it might produce.
- **`Detail` is a handle, not a sentence.** It is what shows in the board's row and every filter — keep it to a few words ("Junction breaks on clone"). The full shaped sentence goes in `Description`.

`raid.py add` builds the sentence from its slots, so use it rather than writing the Description by hand. `raid.py check` reports entries whose Description does not match its type's shape, as a warning: it is a drafting aid, not a gate, and a legitimately odd entry can stay odd.

## The Action Log

`Action Log` is a **list of dated, attributed entries**, not free text — it is what makes a register readable months later, when what changed matters less than why.

```json
"Action Log": [
  {"on": "2026-09-02", "by": "avm", "note": "Opened."},
  {"on": "2026-09-14", "by": "avm",
   "changed": {"Status": ["Open", "Closed"]},
   "note": "install.py shipped; drift check in the smoke test."}
]
```

- `on` and `by` are stamped automatically. Author resolution: `--by`, else `meta.settings.author`, else `RAID_AUTHOR`, else the OS account.
- `changed` maps a field to `[was, now]`. Every `raid.py update`, `close` and `review` writes one, so **the register can never say what changed without saying why**.
- The log is **append-only**. `raid.py update` refuses to set it; there is no edit or delete verb by design.
- Newest last in the file, newest first in the dashboard.

**Never write a field change straight to the JSON.** Doing so loses the reason, which is the only part that cannot be reconstructed later.

## Core operations

### 1. Log an update

The most common operation. A plain progress note:

```bash
python <skill-path>/scripts/raid.py log "<register.json>" --id 5 -m "Vendor confirmed the lead time; no change to the score."
```

### 2. Change fields, with the reason attached

```bash
python <skill-path>/scripts/raid.py update "<register.json>" --id 5 \
  --set "Severity (1-5)=4" --set "Response Strategy=Mitigate" \
  -m "Reassessed after the site visit."
```

`--set` is repeatable and takes `Field=Value`; an empty value clears the field. It rejects a field the schema does not define, so a typo cannot silently create a phantom column, and it validates `Type` and `Status` against the register's vocabularies.

Related verbs, each of which also writes a log entry:

```bash
python .../raid.py close  "<register.json>" --id 5 -m "<the outcome>"
python .../raid.py review "<register.json>" --id 5 --next 2026-12-01
python .../raid.py review "<register.json>"           # every open entry
```

`close` sets Status, Closed On and Closed By together. `review` stamps Last Review and optionally Next Review On.

### 3. Add an entry

```bash
python <skill-path>/scripts/raid.py add "<register.json>" "Junction breaks on clone" --type Risk \
  --because-of "a junction is local filesystem state that no clone reproduces" \
  --risk-that "a fresh machine loads no skills at all" \
  --may-result-in "silent no-ops that look like the agent ignoring the request"
```

Claims the next ID, writes the shaped Description, sets Status to Open and Opened On to today, and logs the opening. Each type takes its own slot flags (`--do/--by-when/--so-that`, `--chose/--over/--because`, `--if-we/--then`, `--because-of/--happened/--resulting-in`); `raid.py add --help` lists them. `--description` writes one freehand when an entry genuinely does not fit its shape.

**Priority % and Target Residual Risk are not fields.** They are computed from the scores when the dashboard renders — Priority as `(Urgency * 1.5 + Consequences) / 12.5 * 100`, Target Residual Risk as `Probability * Severity * (1 - Mitigation Target / 100)`. Never store either: a stored copy goes stale the moment a score changes.

For anything the verbs do not cover, the register is JSON:

```python
import sys; sys.path.insert(0, "<skill-path>/scripts")
import registry as R

data = R.load(path)
row = R.get(data, "entries", "RAID.ID", 5)
```

Omit fields that have no value rather than writing empty strings, and `R.save(path, data)` when done.

### 4. Refresh dashboard

When the user says "refresh the RAID dashboard" or similar:

1. Discover the register (see discovery section above).
2. Run `scripts/refresh_raid.py` via bash:
   ```bash
   python <skill-path>/scripts/refresh_raid.py "<register.json>" "<output-html-path>" "<project-name>"
   ```

The dashboard is a snapshot, not a live view — regenerate it after any change. The `raid.py` verbs do not regenerate it; they warn when it has gone stale, via `registry.stale_views(path)`.

### 5. Check a register

```bash
python <skill-path>/scripts/raid.py check "<register.json>"
```

Read-only. Reports vocabulary violations, fields the schema does not define, malformed or unattributed log entries, Descriptions that do not follow their type's shape, closed entries with no Closed On, risks with no Probability/Severity, and stale dashboards. Run it before a review ceremony, and after any hand-edit of the JSON.

### 6. Create new RAID register

```bash
python <skill-path>/scripts/create_raid.py "<output-path>.json" "<project-name>"
```

Builds an empty register — schema, field order and vocabularies, zero rows — and creates the `AuxMat/` folder beside it. Set `meta.settings.author` so log entries are attributed consistently.

A register whose Action Log is still free text converts with:

```bash
python <skill-path>/scripts/raid.py migrate "<register.json>" [--apply]
```

Dry by default. It takes the date only from the text itself and the author only from the row's DRI — an entry carrying neither stays undated rather than being given a plausible date.

### 7. External tracking flag

The register carries a simple Y/N `Tracked Externally` flag:

- Set it to "Y" when a RAID item's action plan is being tracked in your task tracker (Jira, Azure DevOps, Planner, a to-do app - whichever you use).
- The dashboard shows a checkmark badge on flagged items and offers filter buttons for tracked and untracked items.
- **No task IDs or links are stored** - just the flag. Keeping the linkage one-way avoids the register going stale every time a task moves.

Set it through `raid.py`, so the reason lands in the log with it:

```bash
python .../raid.py update "<register.json>" --id 5 --set "Tracked Externally=Y" -m "Raised as a ticket."
```

For traceability in the other direction, put the RAID ID in the tracker item's description (e.g. `RAID: R.5`). That direction is the useful one, and it costs nothing to maintain.

If your tracker has an API and you want real task creation, delegate it to a separate skill that owns those conventions rather than building tracker-specific logic into this one.

## Register schema

One collection, `entries`. `registry.py` owns the `meta` envelope; `create_raid.py` holds the field order and the vocabularies, which are written into `meta.settings`.

| Field | Notes |
|-------|-------|
| RAID.ID | Sequential integer |
| Detail | Short handle — a few words, not the full sentence |
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
| Response Strategy | Avoid, Transfer, Mitigate, Accept, Exploit, Share, Enhance (PMI PMBOK threat + opportunity responses) |
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
| Description | The type's sentence shape — see "How an entry is written" |
| Action Plan | |
| Acceptance Criteria | |
| Action Log | List of `{on, by, note, changed}` entries — see "The Action Log" |
| Category | |
| Tracked Externally | Y/N flag, see operation 7 |
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

- **Board tab**: sortable table, filters for Type/Status/MoSCoW/Category/DRI/tracked, a "Clear all" button, and an active-filter count badge. The **Updated** column is the newest Action Log date, derived at render time — sort on it to find items that have gone quiet. Filter state persists across reloads via localStorage (keyed per project name).
- **Closed entries are hidden from the board by default.** They stay in the register permanently and stay in the KPI counts — they are history, and history should not compete with open work for attention. A `Show closed (N)` button brings them back, and the choice persists like any other filter. Filtering explicitly for `Status = Closed` overrides the hide, so that combination shows the closed entries rather than an empty board. When a filter matches nothing, the empty state says how many closed entries are hidden.
- **Item detail**: the Action Log renders as a timeline, newest first, each entry showing its date, author, field changes and note.
- **Analytics tab**: KPIs, by-type and by-status charts, priority distribution, MoSCoW breakdown, items-over-time timeline, and — when risk items are present — a risk heat map.
- **Risk heat map**: Probability x Severity scatter with a green/amber/red zone background (green <6, amber 6-14, red >=15 on Probability x Severity). Only renders when >=3 open risk items have both fields scored.
- **Reviews tab**: flags items never reviewed or last reviewed >30/>90 days ago.

The dashboard is generated output — overwritten in full on every refresh. Never hand-edit it.
