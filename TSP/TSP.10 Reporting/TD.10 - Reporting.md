# TD.10 — Reporting

## Purpose

Say how the work is going, to someone who does not read the registers. Reports are generated from the WBS, RAID and the sprint records, never written from memory, and each one opens with a short summary that a stakeholder can follow without any of the codes the registers use.

Three reports ship:

- **The project status report**: what the project is for and whether it is getting there (its outcome and measures, from the project's brief), then the *Essential 4* (On Time, On Scope, On Quality, Resources), each proposed from the registers with its evidence and confirmed by the person who owns the project, plus the decisions and help the project needs, its key deliverables by month and its top risks.
- **The sprint update**, after sprint planning: the last sprint's outcome beside the new sprint's commitments, across every project the sprint touches, with the sprint's cards as a board on a tab of their own.
- **The project charter**, on demand: the project on one page for someone who reads none of the registers, from its brief and its registers, each section naming its source.

Any of them can be shared outside the work as a filtered copy (`export`), as HTML and optionally PDF.

**A report is three layers, and only the last one is built here.** The *data* lives in the registers. The *audience* (who receives which report, how often, through which channel, at what share level) is the project's Stakeholder Register (TSP.13): with none, a report has one reader, the person running the work. The *views* are this tool. Scaling up means adding a view or a reader, not another tool.

## Status: In Progress

| | |
|---|---|
| Both reports | Run every sprint on real work in their original setting, where the status report is generated at the sprint close-out and the sprint update after planning |
| As shipped here | Exercised end to end on a scratch project built with AKOS's own tools (`tests/smoke_test.py`); **not yet used on real work in this form** |
| Sharing and the charter | Audiences, the external copy and the charter run in their original setting since October; here they are exercised by the smoke test only |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.10 Reporting/` | What the reports are for and why they are shaped as they are |
| `reporting` | `reporting/SKILL.md`, `reporting/scripts/report.py` | The reports, the confirm flow and the rules for the executive summary |
| Each report's record | `<project>/Reports/Status/<date> Status.json`; `Reports/Sprint Update/<sprint ID> Sprint Update.json` beside the sprint records | **Source of truth for a report**: what it found, then the confirmations, overrides and summary |
| Each report's view | the same name, `.html` | Generated from the record; never edited by hand |
| A shared copy | `<name> (external).html` (and `.pdf`), beside the record | What goes to someone outside the work, from `export` |

**Dependencies.** `wbs-manager` (TSP.1) and `sprint-facilitator` (TSP.8) are required: the reports read the WBS through the WBS tool's own modules and `metrics`, and the sprint goals through `sprint_record.py goals`. `raid-manager` (TSP.2) is optional; without a RAID register the reports carry no risks, Changes or help. `stakeholder-manager` (TSP.13) is optional; without it every project runs on the solo default.

## What the SKILL.md covers (and this document doesn't repeat)

`reporting/SKILL.md` holds the commands, the run-and-confirm flow, the rules for the executive summary, the Essential 4 as proposed (what makes a signal amber or red), and how a report is added. This document covers why the reports are shaped as they are, how they relate to the other tools, and their history.

## Design decisions

**The record is the report; the page is a view of it.** Each report is a JSON record and an HTML page generated from it. The next status report reads the latest confirmed record for its trend, so the ratings must live in a diffable file rather than only on a page.

**The generator proposes; the owner confirms.** Every Essential 4 rating is computed from the registers with the evidence beside it, and stays *proposed* until confirmed, or overridden **with a reason**. An unexplained override would make the record say something the registers do not, with nothing to say why.

**The executive summary is drafted, never generated.** Two or three sentences in plain language: what was achieved, where the work is heading or what is at risk, what is needed from the reader. No IDs, codes or colour names, because the reader of a summary is exactly the person without the registers. A template could only restate the codes; the narrative needs judgement, so the agent drafts it from the record's facts and the owner confirms it.

**The Essential 4 measure what the registers can show.** *On Time* reads key deliverables against their baselines. *On Scope* reads decided Changes and unplanned pull-ins. *On Quality* reads whether committed work stated what good looks like, and whether its closure says it was met. *Resources* reads delivered hours against committed, pro-rated mid-sprint. Overall is the worst of the four.

**A project can be green on delivery and still not moving what it exists for, so the report says both.** It opens with the project's outcome and its measures, each scored 0-1 like a key result. *On Outcome* is a fifth signal, proposed and confirmed like the four, but kept out of Overall: Overall stays a delivery verdict whose trend is comparable with every earlier report. Pace is judged at the date each value was taken: a measure read once a quarter cannot move between readings, and judging it against the report's date would call it behind pace all quarter; a value overdue for its reading is caught as stale instead.

**The brief carries what the report needs.** There is no portfolio register here, so the outcome, what the project serves and its measures all live in the project's brief, beside its registers, written and read through Project Definition (TSP.14). A small project's brief is lean (no Measures table), and its report simply has no *On Outcome*.

**What leaves the project is opted in, entry by entry.** An external copy holds a RAID entry only when it is marked `Sharable = Y`; one nobody has thought about stays internal. It drops what names who the work waits on, the evidence under each rating, the card-level board and the facts block, and it refuses a report whose ratings or summary are not confirmed: only what was agreed is shared. The share level comes from the communication that sends the report, so the register and the copy cannot disagree.

**The charter is generated, never written.** A brief is where the words are authored; the registers hold the rest. A charter written by hand would be a third copy that drifts. Nothing in it is rated, so it can be shared straight away, and a shared charter shows stakeholders by role and group, never by name.

**One trend convention: up is better.** Every report and the RAID board draw a trend the same way, an arrow in a tinted circle, with a key at the foot of the page. Records store the level, never the arrow, so no reader has to know which way an arrow pointed; records written under the older convention read correctly.

**Explanations stay out of the reader's way.** How to read a section sits behind an info icon beside its title, opened by hover or tap, and printed inline; what the reader acts on stays on the page.

**What waits on the reader is a request, not a record.** *Decisions required* lists Changes awaiting an outcome. A RAID Decision records a choice already made and asks nothing of anyone.

**The sprint update stands on its own, and comes after planning.** A sprint spans projects: its goals, capacity and effort belong to the person, not to a register, so its story is a cross-project report, and a status report covers only its project. The update is an executive overview for people outside the work. Its card-level board is a deep dive, so it sits on its own tab: the overview is what opens and what prints.

**The board and the WBS dashboard are one model.** A dashboard is one project's, so its Current Sprint tab shows one project; the update shows all of them. Both take their cards, and the deliverable each card serves, from `wbs.py`'s `sprint_board()`, so a card sits in the same lane in either. The update's board is a snapshot as of its date; rerunning the update mid-sprint refreshes it and keeps the confirmed summary.

## Relationship to other tools

- **WBS Register (TSP.1)**: the source of deliverables, baselines, closures and sprint membership. The reports never write to it.
- **RAID Register (TSP.2)**: risks, issues, Changes and their outcomes, and each entry's DRI and trend. Read only.
- **Sprint Ceremonies (TSP.8)**: the close-out generates a status report per project, and planning ends with the sprint update. The sprint records supply goals, capacity and the fist of five.
- **Stakeholder Register (TSP.13)**: who receives each report and at what share level, read through its own module; contacts are never read.
- **Project Definition (TSP.14)**: the brief, read through its `brief.py`: the outcome, what the project serves and the measures for the status report, and the charter's purpose, scope and approach. The report's first step, bringing the measures up to date, is its *Keep current*.
- **Nothing is sent anywhere.** A report is two files, and a shared copy a third. Sending it is the owner's act, through whatever channel the audience uses.

## Maintenance

**Regular use**: a status report per project at each sprint close-out, and the sprint update after each planning. Each is confirmed with the owner before it is shared.

**Before structural change** to a record's shape, keep `render` able to rebuild an older record's view: old records are what the next report's trend reads.

## Open items

| Item | Detail |
|---|---|
| A monthly report and the focus index | The original setting has a monthly review whose report counts active projects and a focus index (how thinly the committed hours were spread). AKOS has no monthly review, so neither ships here |
| Reading measured values automatically | Before a status report the due measures are read by hand; reading them from their sources is for later |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.5 | 2026-10-28 | **The brief is read through Project Definition (TSP.14).** The status report and the charter stop parsing the brief: they read it through `brief.py`, the measures' vocabulary and date checks are the brief's own, and only whether a value reads as a number stays here, since scoring needs it. The template moves from `templates/` into TSP.14. A copy without TSP.14 installed says so in the outcome section and on the charter, and runs on. The executive statement is found in the brief's own language. |
| v1.4 | 2026-10-27 | **A project folder can hold more than registers, and number its folders.** Looking for the WBS and RAID, a JSON that is not a register (an installer's lock) is skipped; it used to stop every report. Reports go into the project's reports folder whatever its number (`05. Reports`, or `Reports`), so a project whose artifact register numbers its folders keeps one. Found installing the tools into an existing project's management folder. |
| v1.3 | 2026-10-27 | **Reports can be shared, and a charter says what the project is.** `export` writes a filtered copy for someone outside the work, as HTML and optionally PDF, holding only RAID entries marked `Sharable = Y` and refusing an unconfirmed report; `--comm` takes the share level from the project's Stakeholder Register, and a status report records who receives it. `report.py charter` puts the project on one page from its brief and registers. Trends are drawn one way everywhere, up is better, as chips with a key; explanations sit behind an info icon; the key deliverables map stacks on a phone. *On Time* counts only a rebaseline to a later date. |
