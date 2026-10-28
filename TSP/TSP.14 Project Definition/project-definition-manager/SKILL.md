---
name: project-definition-manager
description: Writes, grows, checks and revisits the documents that define a project (TSP.14 Project Definition) - above all the Project Brief, the one document every project has (why it exists, its outcome and done-when, Stop if, what it serves, and for a full brief its measures, appetite, scope, approach and who it is for). Use whenever the user wants a Project Brief written, started, updated, grown from lean to full, checked or revisited; asks what a project's outcome is, what it serves, or what its done-when or Stop if says; is starting a project, or installing these tools into a project already running; or when a brief's measures are due before a status report. Also used by reporting (the status report and the charter read the brief) and weekly-review-facilitator (a brief due a revisit). Not for how a project is going (reporting), or its deliverables and risks (wbs-manager, raid-manager).
---

# Project Definition Manager (TSP.14)

The documents that say what a project *is*: why it exists, what it promises, for whom, and how its outcome is measured. **The Project Brief** is the one every project has. Further definition documents join only when a project needs one (below).

What a project *does* lives elsewhere: deliverables in the WBS, risks and decisions in the RAID, status in the registers, people in the Stakeholder Register. The brief points at them and never copies them, because a second list drifts from the first.

## Requirements

Python 3, standard library only. Examples write `python`; on macOS/Linux use `python3`. `<skills>` is the folder this skill is installed in.

## Files

| File | Role |
|---|---|
| `templates/Project Brief.md` | The template, both sizes in one file. |
| `scripts/brief.py` | The one reader of the format: `show`, `check`, `new`, and the module the other tools import. |
| `scripts/smoke_test.py` | Checks `brief.py` on briefs it builds itself. Run it after any change to `brief.py`. |

A project's brief is `Project Brief.md` beside its registers, in its project-management folder (`0. PrjMgm/`, or numbered by its artifact register, `04. Project Brief.md`). `brief.py` accepts the file, that folder, or the project folder above it.

## The brief

**Lean or full.** **Full** when the project runs a WBS register or someone other than its owner reads its reports; **lean** otherwise. The `**Size:**` header line says which. A lean brief holds the executive statement, *Why*, *Outcome and done-when* and *Stop if*. The full one adds *Measures*, *Appetite and budget*, *Scope*, *Approach* and *Who it is for*. Growing edits the same file: add the sections, change Size.

**The header line:** `**Size:** · **Written:** · **Last revised:** · **Serves:**`. `Last revised` moves whenever the brief is revisited, even when nothing changes, because it is the revisit clock. `Serves` names the goal the project moves, in whatever form the team keeps goals (an objective, an OKR, a bet), by its ID.

**The executive statement opens it:** *To <what the project does> so that <the outcome it serves>*, in the brief's own language, written last because only then is it easy.

**The brief owns the outcome and what the project serves.** Every reader takes them from here: the status report, the charter. Where some other list also records them (a portfolio, a programme plan), that list is checked against the brief, never the other way round, and a change of outcome is made here first.

**Measures (full brief).** Three to six, at least one lag, each defined in full when written: role, kind, committed or aspirational, baseline and its date, target and by when, how measured, how often, current value and its date, source. The template's comment carries the rules. The brief holds only the current value; the status reports keep the history.

**If a brief can't be written, there may be no reason to do the project.** Say so out loud to whoever owns it.

## The four moments

Each is started by whoever owns the moment: a ceremony, another tool, or the user.

### 1. Write

*A new project:*

```
python <skills>/project-definition-manager/scripts/brief.py new "<project>/0. PrjMgm" --title "<Project name>" --size lean|full [--serves <goal ID>]
```

Then fill it **with the owner, in this order:** *Why*, then the outcome sentence and the done-when (three to five, specific and checkable), then *Stop if*, and the executive statement last. In a full brief the measures come before the first sprint commits to the project; *Scope* and *Approach* wait until the plan settles, and keep their prompts until then.

*An adoption*, a project already running when these tools are installed into it: **draft from what the project already has** (its charter or business case, its plan, its WBS, its status reports), point at those documents instead of copying them, and leave the outcome to whoever owns it: the sponsor or the PM, not the agent. A drafted outcome is a proposal until they confirm it.

Where the organisation requires its own document (a business case, a charter format), follow its template and point at it from *Approach* rather than repeating it in the brief.

### 2. Grow

When `check` says *lean, but the project runs a WBS - grow it to full*: add the full sections from the template, the Measures first, and set Size to full.

### 3. Keep current

Before a status report (`reporting`), the measures due by their `Every` are updated: read the *measured* ones from the source their `How measured` names, ask for the *asked* ones, and write `Current` and `As of`. Edit the table by hand; git keeps every revision. A value older than its cadence is reported stale.

### 4. Revisit

`check` reports *revisit due* when `Last revised` is more than a month old, and the weekly review (`weekly-review-facilitator`) shows it. Ask, project by project:

- Is the outcome still the right one?
- Has *Stop if* tripped?
- Is what it serves still right, and still a current goal?
- Is the size still right?

Change what needs changing, and set `Last revised` to today either way. The sprint close-out is not a revisit point: it is about delivery.

## Check and show

```
python <skills>/project-definition-manager/scripts/brief.py check <brief or folder> [--wbs]   # findings; exit 1 when there are any
python <skills>/project-definition-manager/scripts/brief.py show  <brief or folder> [--json]  # what every reader takes from it
```

`check` reports: no Size line; lean on a project with a WBS (`--wbs`); no executive statement, outcome sentence, done-when or Stop if; full with no Measures table; the table's columns, vocabularies and dates; no lag measure; no `Last revised`, or a revisit due. Template prompts left as written (`<…>`, `…`) count as missing. Whether a measure's values read as numbers is checked by the status report, which scores them.

**Other tools import `brief.py`; they never parse a brief themselves:** `B.find`, `B.resolve`, `B.read` / `B.parse`, `B.check`, `B.measure_findings`, `B.serves_list`, `B.revisit_due`. A change to the template's shape is made in `brief.py` and its smoke test in the same edit.

## Further definition documents

Only when a project needs one, each pointing at the brief instead of repeating it, and linked from the brief's *Approach*: a **PRD** for a product (users, problems, requirements), or a **business case** when a funder requires one, on the funder's template where it has one.

## Relationship to other skills

- **`reporting` (TSP.10)** — the status report and the charter read the brief through `brief.py`; the report's step that updates the measures is *Keep current* here. Without this skill installed, the report says so and runs without the outcome section.
- **`weekly-review-facilitator` (TSP.11)** — shows a brief due a revisit.
- **`wbs-manager`, `raid-manager`, `stakeholder-manager`** — what the brief points at.
