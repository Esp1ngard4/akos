---
name: tsp-manager
description: Maintains a TSP Register - the inventory of every Tool, System and Procedure you rely on - plus the recurring control activities that keep each one alive, and regenerates an HTML dashboard from it. Use whenever the user mentions a "tool register", "tool inventory", "process inventory", "TSP", or asks to add, retire or renumber a tool, record that a tool was reviewed, find which tools are obsolete or overdue for review, run a periodic controls check, or refresh the tool dashboard. Also use when a new tool or automation is created and needs registering.
---

# TSP Manager

The TSP Register is the single inventory of every Tool, System and Procedure in your system. Every `FSP.<N>` folder under `<your tools folder>/` should have exactly one row in it, and the row is what makes the FSP number meaningful — the folder is just storage.

## Requirements

Python 3 with `openpyxl`. Install once per machine from this skill's folder:

```
pip install -r requirements.txt
```

Everything else the scripts use is standard library. Examples below write `python`, which is correct on Windows; on macOS/Linux use `python3`.

## Files

| File | Role |
|---|---|
| `<your tools folder>/TSP Register.xlsx` | **Source of truth.** All edits go here. |
| `<your tools folder>/TSP Dashboard.html` | Generated static snapshot. Never edit by hand — it is overwritten on every refresh. |
| `<your tools folder>/PreviousV/` | Superseded register copies and the pre-2026 DF. |
| `scripts/create_tsp.py` | Creates a new, empty register (five sheets, headers, vocabularies, no data). |
| `scripts/refresh_tsp.py` | Rebuilds the dashboard from the register. |
| `scripts/audit_tsp.py` | Read-only health report: register vs. disk, overdue reviews, lookup violations. |
| `templates/dashboard.html` | Dashboard shell with `{{TOOLS}}`, `{{ACTIVITIES}}`, `{{CHANGELOG}}`, `{{GENERATED}}` placeholders. |

Governance, history and the reasoning behind the review cadence live in `<your tools folder>/DF.18 - TSP Register.md`, not here.

## Register schema

`TSP Register.xlsx` has five sheets. Headers are always row 1; data starts row 2. A row with a blank `ID` is not a record.

**Tools Register** — one row per TSP.

| Col | Field | Notes |
|---|---|---|
| A | ID | Integer. **This is the FSP number.** Never reuse or renumber an ID once assigned. |
| B | Tool/System Name | Should match the `FSP.<ID> <Name>` folder name where a folder exists. |
| C | Description | Free text; often a cross-reference to another FSP/DF. |
| D | Type | `Ferramenta` / `Manual` / `Instrução de trabalho` |
| E | Status | `Planeado` / `Em execução` / `Implementado` / `Absoleto` |
| F | Relevancy | `Critical` / `Often` / `Sometimes` / `Specific - relevant` / `Specific - questionable` / `Rarely` / `Not in the last years` |
| G | Primary AF | e.g. `<area>` |
| H | Other AFs | Comma-separated |
| I | Doc Aux | `Yes`/`No` — does a DF document exist |
| J | Links | Cross-references |
| K | Notes | Free text |
| L | Last Reviewed | Date. Set by the annual review, not by ordinary edits. |
| M | Skill | Comma-separated names of the skills that automate this tool; blank means none. Naming a skill here **is** the expectation that it exists — `audit_tsp.py` reconciles the column against what is installed, in both directions. |

**Control Activities** — recurring upkeep each tool needs: `ID`, `Activity Name`, `Frequency`, `Duration (min)`, `Importance`, `Commitment`, `Linked Tool`, `Description`, `Last Done`, `Next Due`. `Linked Tool` matches a Tools Register **name**, not an ID. `Next Due` is `Last Done` plus the Frequency's `Days` value from Lookups.

**Activity Log** — one row per execution: `ID`, `Activity`, `Done On`, `Planned For`, `Notes`, `Review On`, `Times Postponed`.

**Change Log** — `ID`, `Tool`, `Changed On`, `Description`. Append a row for any structural change to a tool (created, retired, superseded, DF rewritten).

**Lookups** — the allowed values for Status, Type, Relevancy, Importance, and Frequency (with a `Days` column). Stacked blocks separated by blank rows. `audit_tsp.py` validates the other sheets against it.

Frequency values and their `Days`: `Daily` 1, `Weekly` 7, `Monthly` 31, `6 weeks` 42, `2 months` 60, `Quarterly` 90, `4 months` 120, `Semi-annual` 180, `Annual` 365, `2-2 Years` 730, `5-5 Years` 1825.

Field values are a mix of Portuguese and English — this is historical and deliberate. Match the existing vocabulary in the column you are writing; do not translate or normalise values as a side effect of an unrelated edit.

## Operations

Edit the workbook with `openpyxl` (`data_only=True` for reads; plain `load_workbook` when writing so formulas survive). Always **read the sheet first** to find the real last row and the current max ID — never assume.

### Register a new tool

1. Check it isn't already there — search Tools Register column B *and* column C for the name and any alias. Duplicate registration is the most common error.
2. Assign `ID = max(existing IDs) + 1`. Gaps in the sequence are retired IDs; never fill them.
3. Append the row with at minimum ID, Name, Description, Type, Status, Relevancy, Primary AF, Doc Aux — plus `Skill` if the tool is automated.
4. Create `<your tools folder>/FSP.<ID> <Name>/` if the tool needs a folder.
5. Append a Change Log row.
6. Refresh the dashboard.

### Retire a tool

Set Status to `Absoleto` and append a Change Log row naming what replaced it. **Do not delete the row and do not move the FSP folder unless the user asks** — a tool's number and history stay in the register permanently, and old file formats sometimes still hold data worth recovering.

### Record a review

Set `Last Reviewed` on the Tools Register row. For a control activity: append to Activity Log, set `Last Done`, and set `Next Due = Last Done + Frequency days` using the Lookups `Days` column.

### Create a new register

```
python scripts/create_tsp.py "<path>/TSP Register.xlsx" [--vocabulary en|pt]
```

For standing up a register somewhere other than the personal the system. `--vocabulary pt` reproduces the personal register's historical Portuguese Status/Type/Importance terms; `en` (the default) is the English equivalent for a register starting clean. It refuses to overwrite an existing file unless `--force` is passed.

**Never use this to "reset" the live register** — that would destroy the inventory. The live register is only ever edited in place.

### Refresh the dashboard

```
python scripts/refresh_tsp.py "<your tools folder>/TSP Register.xlsx"
```

The dashboard is a static snapshot with the generation date in its subtitle — **rerun it after every batch of register edits**, or the user reads stale numbers.

### Audit

```
python scripts/audit_tsp.py "<your tools folder>/TSP Register.xlsx"
```

Read-only. Run it before the annual review, and whenever the register and the FSP folders may have drifted.

Skill roots are auto-discovered: the repo-root `.claude/skills` plus any `.claude/skills` inside an FSP folder (and ship their own). Project-scoped skills under `<your tools folder>/` are deliberately not scanned — they belong to projects, not TSPs. Pass `--skills DIR` (repeatable) to override.

### Back up before a structural change

Before changing the schema or doing a bulk rewrite, copy the register to `PreviousV/TSP Register (<what changed> YYYY-MM-DD).xlsx`.

## The two controls

These are the reason the register exists rather than being a static list:

1. **Monthly** — during the monthly review, check the Control Activities whose `Next Due` has passed. The dashboard's Overview tab lists them.
2. **Annual (TSP review)** — walk the register and, per tool, ask: is it still being used? If yes, do I want to improve it? Improvements are batched into a `the system TSP Lean<YY>` project rather than done inline. Stamp `Last Reviewed` on every row you touch, whatever the answer.

## Relationship to other tools

- **A skill-authoring skill** - if you use one to scaffold and package skills, it is
  externally supplied: name it in the register but do not archive a copy of it. See
  the method note on owned vs. used tools.
- **A governance-doc skill** - if you separate the "why" document from the skill
  itself, that skill owns the document and this one owns the register row. **The
  boundary: it owns the document, this owns the row.** When a tool gains or loses a
  governance doc, it writes the doc and this one flips the `Doc Aux` flag and
  appends the Change Log entry - neither does the other's write.
- **Every other skill you install** is itself a registered tool. Building a new
  skill is not finished until its row exists here.
- Nothing syncs automatically. The register is updated deliberately, by this skill.
