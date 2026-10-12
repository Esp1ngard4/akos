# TD.10 — Reporting

## Purpose

Say how the work is going, to someone who does not read the registers. Reports are generated from the WBS, RAID and the sprint records, never written from memory, and each one opens with a short summary that a stakeholder can follow without any of the codes the registers use.

Two reports ship:

- **The project status report**: the *Essential 4* (On Time, On Scope, On Quality, Resources), each proposed from the registers with its evidence and confirmed by the person who owns the project, plus the decisions and help the project needs, its key deliverables by month and its top risks.
- **The sprint update**, after sprint planning: the last sprint's outcome beside the new sprint's commitments, across every project the sprint touches, with the sprint's cards as a board on a tab of their own.

**A report is three layers, and only the last one is built here.** The *data* lives in the registers. The *audience* (who receives which report, how often, through which channel) is a communications plan, not built here: until there is one, every report has one reader, the person running the work. The *views* are this tool. Scaling up means adding a view or a reader, not another tool.

## Status: In Progress

| | |
|---|---|
| Both reports | Run every sprint on real work in their original setting, where the status report is generated at the sprint close-out and the sprint update after planning |
| As shipped here | Exercised end to end on a scratch project built with AKOS's own tools (`tests/smoke_test.py`); **not yet used on real work in this form** |
| Not here yet | Audience filtering (what an external reader may see), export to Word or PowerPoint, and a project's outcome and measures beside the Essential 4. Each is being built in the original setting and will follow |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.10 Reporting/` | What the reports are for and why they are shaped as they are |
| `reporting` | `reporting/SKILL.md`, `reporting/scripts/report.py` | The reports, the confirm flow and the rules for the executive summary |
| Each report's record | `<project>/Reports/Status/<date> Status.json`; `Reports/Sprint Update/<sprint ID> Sprint Update.json` beside the sprint records | **Source of truth for a report**: what it found, then the confirmations, overrides and summary |
| Each report's view | the same name, `.html` | Generated from the record; never edited by hand |

**Dependencies.** `wbs-manager` (TSP.1) and `sprint-facilitator` (TSP.8) are required: the reports read the WBS through the WBS tool's own modules and `metrics`, and the sprint goals through `sprint_record.py goals`. `raid-manager` (TSP.2) is optional; without a RAID register the reports carry no risks, Changes or help.

## What the SKILL.md covers (and this document doesn't repeat)

`reporting/SKILL.md` holds the commands, the run-and-confirm flow, the rules for the executive summary, the Essential 4 as proposed (what makes a signal amber or red), and how a report is added. This document covers why the reports are shaped as they are, how they relate to the other tools, and their history.

## Design decisions

**The record is the report; the page is a view of it.** Each report is a JSON record and an HTML page generated from it. The next status report reads the latest confirmed record for its trend, so the ratings must live in a diffable file rather than only on a page.

**The generator proposes; the owner confirms.** Every Essential 4 rating is computed from the registers with the evidence beside it, and stays *proposed* until confirmed, or overridden **with a reason**. An unexplained override would make the record say something the registers do not, with nothing to say why.

**The executive summary is drafted, never generated.** Two or three sentences in plain language: what was achieved, where the work is heading or what is at risk, what is needed from the reader. No IDs, codes or colour names, because the reader of a summary is exactly the person without the registers. A template could only restate the codes; the narrative needs judgement, so the agent drafts it from the record's facts and the owner confirms it.

**The Essential 4 measure what the registers can show.** *On Time* reads key deliverables against their baselines. *On Scope* reads decided Changes and unplanned pull-ins. *On Quality* reads whether committed work stated what good looks like, and whether its closure says it was met. *Resources* reads delivered hours against committed, pro-rated mid-sprint. Overall is the worst of the four.

**What waits on the reader is a request, not a record.** *Decisions required* lists Changes awaiting an outcome. A RAID Decision records a choice already made and asks nothing of anyone.

**The sprint update stands on its own, and comes after planning.** A sprint spans projects: its goals, capacity and effort belong to the person, not to a register, so its story is a cross-project report, and a status report covers only its project. The update is an executive overview for people outside the work. Its card-level board is a deep dive, so it sits on its own tab: the overview is what opens and what prints.

**The board and the WBS dashboard are one model.** A dashboard is one project's, so its Current Sprint tab shows one project; the update shows all of them. Both take their cards, and the deliverable each card serves, from `wbs.py`'s `sprint_board()`, so a card sits in the same lane in either. The update's board is a snapshot as of its date; rerunning the update mid-sprint refreshes it and keeps the confirmed summary.

## Relationship to other tools

- **WBS Register (TSP.1)**: the source of deliverables, baselines, closures and sprint membership. The reports never write to it.
- **RAID Register (TSP.2)**: risks, issues, Changes and their outcomes, and each entry's DRI and trend. Read only.
- **Sprint Ceremonies (TSP.8)**: the close-out generates a status report per project, and planning ends with the sprint update. The sprint records supply goals, capacity and the fist of five.
- **Nothing is sent anywhere.** A report is two files. Sharing one is the owner's act, through whatever channel the audience uses.

## Maintenance

**Regular use**: a status report per project at each sprint close-out, and the sprint update after each planning. Each is confirmed with the owner before it is shared.

**Before structural change** to a record's shape, keep `render` able to rebuild an older record's view: old records are what the next report's trend reads.

## Open items

| Item | Detail |
|---|---|
| Audience filtering and export | Filter RAID rows by whether they are sharable for each audience a communications plan names; export to Word or PowerPoint for an external reader. Nothing marked not sharable may reach an external export |
| Outcome and measures | What the project is for and whether it is getting there, from a project brief, beside the Essential 4 as a fifth signal kept out of Overall |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-12 | Published as TSP.10: the project status report and the sprint update, each a JSON record and an HTML view, with the Essential 4 proposed and confirmed, the executive summary drafted and confirmed, and the sprint board on its own tab. Runs on AKOS's own registers and sprint records; needs structured sprint goals (TD.8 v1.2) and the RAID register's Changes and Trend (TD.2 v1.5). |
