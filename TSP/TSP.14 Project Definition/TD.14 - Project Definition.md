# TD.14 — Project Definition

## Purpose

The documents that say what a project is: why it exists, what it promises, for whom, and how its outcome is measured. Above all the **Project Brief**, which every project has, and beside it, only when a project needs one, a further definition document such as a PRD or a funder's business case. The tool writes them with whoever owns the project, keeps the brief's measures current, revisits it on a clock, and is the one reader every other tool uses.

It defines; it does not report. How a project is going is the status report's (TSP.10); what it delivers and what threatens it are the WBS's and the RAID's. Whether a project should exist at all is its owner's call, and the brief is where that call is tested: if one can't be written, there may be no reason to do the project.

## Status: In Progress

| | |
|---|---|
| The design | Comes from a personal setting, where every open project keeps a brief, a portfolio checks them, and the status report reads its outcome and measures from it |
| As shipped here | **Not yet used on real work.** Exercised by its own smoke test and by the repository's, through the status report and the charter reading a brief, and the weekly review's revisit check |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.14 Project Definition/` | What the tool is for and why; how to adapt it |
| `project-definition-manager` | `project-definition-manager/SKILL.md` and `scripts/` | How a brief is written, grown, kept current and revisited; `brief.py`, the reader other tools import; its smoke test |
| Template | `project-definition-manager/templates/Project Brief.md` | Both sizes in one file |
| `Project Brief.md` | Your project's planning folder, beside its registers | **Source of truth** for that project's definition: its outcome, what it serves, its measures |

Standard library only, and no dependencies. The tools that read the brief (TSP.10, TSP.11) find it when it is installed beside them, and say so when it is not.

## What the skill covers (and this document doesn't repeat)

`project-definition-manager/SKILL.md` holds the brief's sizes and sections, the four moments and how each runs, the `brief.py` commands and what `check` reports, and which functions other tools import. This document covers why the tool is shaped as it is, how to adapt it, and its history.

## Design decisions

**One project document, grown over time.** A case, a charter, an initiation document and a management plan often describe the same project four times. The brief has their sections, filled in as the project matures: lean while a project is small and only its owner reads about it, full once it runs a WBS or reports to someone else. One file with both sizes, so growing it edits the document instead of copying it over.

**A project's definition belongs to the project.** The brief describes one project, so it is a tool of its own rather than a part of whatever ranks projects. A project with no portfolio around it still gets a brief and everything needed to write one.

**The brief owns the outcome and what the project serves.** Every reader takes them from it. Where some other list also records them, a portfolio or a programme plan, that list is checked against the brief, never the other way round: a change of outcome is a change to what the project promises, so it is made in the document that holds the promise.

**The brief points; it does not copy.** Key deliverables are the WBS's, risks and decisions the RAID's, dates and status the registers', stakeholders the Stakeholder Register's. A second list drifts from the first, and the registers are what reports read. Bringing them together for someone who reads none of them is a generated view's job, the charter (TSP.10), not the brief's.

**Measures make the outcome checkable.** A full brief carries three to six measures, at least one of them lag (the result the project exists for, not the activity meant to move it), each defined with its baseline, target, method and cadence when it is written. The brief holds only the current value; the status reports keep the history.

**Four moments, each started by whoever owns it.** *Write* when a project starts or adopts these tools, *grow* when the size rule says so, *keep current* before a status report, *revisit* on the clock. The tool owns what happens in each; the ceremonies that already run decide when. A moment with its own schedule would be one more ceremony to skip.

**An adoption is drafted, not interviewed.** A project already running has a charter, a plan, a backlog. Its brief is drafted from them and points at them, and the outcome stays a proposal until whoever owns it confirms it: the sponsor or the PM, not the agent.

**The brief carries its own revisit clock.** `Last revised` moves whenever the brief is revisited, and a month without one makes it due. The weekly review shows it. The sprint close-out is not a revisit point: it is about delivery, and a definition questioned every two weeks stops meaning anything.

**One reader of the format.** The file name, the header line, the sections and the Measures table are read by `brief.py` and nowhere else; the other tools import it. A format read in several places drifts in several directions.

## Naming conventions

- **The brief:** `Project Brief.md` in the project's planning folder; a project laid out by its artifact register may number it (`04. Project Brief.md`). Title line `<Project name> — Project Brief`.
- **Header line:** `**Size:** lean|full · **Written:** YYYY-MM-DD · **Last revised:** YYYY-MM-DD · **Serves:** <goal IDs>`.
- **Measures:** `M1`, `M2`… assigned once and never reused, so a report's trend can follow a measure across edits.
- **Further documents:** `<Project> - <Type>.md` beside the brief (`Atlas Website - PRD.md`), linked from *Approach*.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** The brief is shipped as one Markdown file beside the registers; where your organisation already keeps project definitions, the skill is edited to fit, and the edit is yours to keep.

### An organisation's own definition document

**Where it plugs in:** *Write*.

**What it takes over:** where a business case, a charter or a project initiation document is required on the organisation's template, that document is written there, and the brief is drafted from it and points at it from *Approach*.

**What to watch for:** the outcome and the measures still live in the brief, because that is where the status report reads them. Say in your copy of the skill which document wins when they disagree.

### A portfolio or programme list

**Where it plugs in:** the outcome and *Serves*.

**What it takes over:** a portfolio that records each project's outcome and the goal it serves keeps them as copies, checked against the brief.

**What to watch for:** the check runs from the portfolio's side. Add it there, reading the brief through `brief.py`, rather than copying the outcome into a second place by hand.

### The goals a project serves

**Where it plugs in:** the `**Serves:**` header line.

**What it takes over:** whatever the team uses for goals, OKRs, objectives, bets, names them by ID here. A revisit asks whether that goal is still current.

## How it is tested

`project-definition-manager/scripts/smoke_test.py` builds briefs in a scratch folder and checks the reader: a brief started from the template, refusing a second; the header, statement (in more than one language), outcome, done-when, Stop if and Serves; the size rule against a WBS; the revisit clock; the Measures table's columns, vocabularies and dates; template prompts read as missing; and the command line. `tests/smoke_test.py` runs it, installs the skill into an empty project, and checks that the status report and the charter read a brief through it and say so when it is not installed.

What is **not** tested is whether a brief is any good: whether its outcome is the right one, or its measures would change a decision. No test can say that.

## Relationship to other tools

- **TSP.10 Reporting**: the status report and the charter read the brief through `brief.py`; the report's first step, bringing the measures up to date, is *Keep current* here.
- **TSP.11 Weekly Review**: shows a brief due a revisit.
- **TSP.1 WBS Register, TSP.2 RAID Register, TSP.13 Stakeholder Register**: what the brief points at for deliverables, risks and decisions, and people.
- **TSP.3 TSP Register**: row 14.

## Maintenance

**When a project starts, or adopts these tools:** *Write*, with whoever owns the outcome.

**Before each status report:** *Keep current*, the measures due by their cadence.

**Weekly review:** a brief due a revisit is named, and revisited.

**After a change to the template's shape:** `brief.py` and its smoke test in the same edit.

## Open items

| Item | Detail |
|---|---|
| Unused on real work | See *Status*. A project run through a few status reports on its brief is what moves the tool to `Implemented` |
| Adopting an existing project | The adoption form of *Write* is described here; the method chapter on adopting these tools into a project already running is still to be written |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-28 | Published as TSP.14. One skill with the brief template, both sizes in one file, and `brief.py`, the reader the status report, the charter and the weekly review use. The brief owns the outcome and what the project serves; it carries its own revisit clock. Replaces the template that sat in `templates/` with no tool to write it. |
