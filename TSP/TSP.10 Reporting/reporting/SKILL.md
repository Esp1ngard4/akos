---
name: reporting
description: Generates reports from the registers - the sprint update (the last sprint's outcome beside the new sprint's commitments, across projects, after sprint planning) and a project status report with the Essential 4 (On Time, On Scope, On Quality, Resources) proposed from the WBS, RAID and sprint record - each as a JSON record plus an HTML view, opening with an executive summary drafted in plain language for the user to confirm. Also generates a one-page project charter from the brief and the registers, and shares a report outside the work as a filtered copy (`export`), at the share level the project's Stakeholder Register gives. Use whenever the user asks for a status report, a project update, a sprint report, an executive summary, a project charter or one-pager, "how is the project doing", the Essential 4 or a RAG status, wants to share a report with a sponsor or client, or wants to confirm or override a report's ratings or summary. Also used by the sprint ceremonies: status reports at the close-out, the sprint update after planning (sprint-facilitator). Not for the WBS or RAID dashboards themselves (wbs-manager, raid-manager).
---

# Reporting (TSP.10)

Reports are generated from the registers, never written from memory. Each report is two files:

| File | Role |
|---|---|
| `<name>.json` | **The record**: what the report found, with the evidence; then the user's confirmations, overrides and summary. The next report reads it. |
| `<name>.html` | **The view**, generated from the record. Never edited by hand. |

## Requirements

Python 3, standard library only. Uses sibling skills, found beside this one in the skills folder: `wbs-manager` (its register and date modules, `wbs.py metrics --json` and `sprint_board()`) and `sprint-facilitator` (`sprint_record.py goals --json` and its table reader). `raid-manager` is optional: without a RAID register the reports run, with no risks, Changes or help to show. `stakeholder-manager` is optional too: without it, or with no register in a project, every project runs on the solo default (the owner, a status report each sprint).

## The reports

| Report | Command | Writes to |
|---|---|---|
| **Sprint update**, after planning: the last sprint (goals and verdicts, what was delivered) beside this sprint (goals, committed items largest first, capacity, confidence); each project's overall status when several; key deliverables by month; goal history and focus; top risks; hours by area; and, on its own **Sprint board** tab, every project's cards by project and deliverable, To do / Doing / Done, as of the run (rerun mid-sprint to refresh it); a parent card reads its children's hours in the sprint, never its own estimate, and totals add leaves only. The overview is the page that opens and prints; the board is the deep dive | `report.py sprint --sprint <the sprint being started> --records "<sprint records>" --project "<project folder>" [--project ...]` | `Reports/Sprint Update/<sprint ID> Sprint Update.*`, beside the records folder (`--out-dir` to choose) |
| **Project status**, at the close-out or on demand: the **Outcome** (what the project is for, its measures scored against their pace, and *On Outcome*), the Essential 4 with evidence and trend, decisions and help required, key deliverables by month (delivered and due), top risks | `report.py status "<project folder>" [--records "<sprint records>"] [--sprint <ID>] [--as-of YYYY-MM-DD]` | `<project folder>/Reports/Status/<date> Status.*` |
| **Project charter**, on demand, for someone who reads none of the registers (a reviewer, a sponsor, a client): the project on one page. The brief's executive statement as its purpose, its outcome and done-when with *Stop if*, measures (baseline to target, no current values), scope, approach and who it is for; on the side the brief's size and what it serves, appetite and budget, key deliverables (open ones by date, delivered ones folded), stakeholders and communications, and the top risks. Each section names its source; a missing one says so (*No Project Brief yet*, *A lean brief*). Nothing is rated, so it can be shared straight away | `report.py charter "<project folder>" [--as-of YYYY-MM-DD]` | `<project folder>/Reports/Charter/<date> Charter.*` |

A project folder is any folder holding the project's WBS register and, optionally, its RAID register; they are found by their `meta.kind`, so their file names do not matter. Pass every project the sprint spans to `sprint`; it refuses a sprint not yet planned, since nothing is committed. Without `--records`, `status` cannot read the sprint's capacity or confidence, and says less about Resources and Mood.

The sprint records must carry structured goals (goal IDs, *Done when*, an `Area` and `Goal` column on committed items), which `sprint_record.py plan` writes. A record from before that reads as unstructured, and its goals are left out rather than guessed.

## Running a report

0. **Status only: bring the brief's measures up to date** (`project-definition-manager`, *Keep current*): any measure whose `As of` is older than its `Every` is due, read or asked, and written in the brief. A value left stale is reported as stale, never guessed.
1. Run the command. It prints the proposed ratings (status) and the summary rules.
2. **Status only: go through the Essential 4 with the user.** Show each proposed rating with its evidence (in the record's `signals.<name>.evidence`). The user confirms it, or overrides it **with a reason**, which `confirm` requires:

   ```bash
   python scripts/report.py confirm "<record.json>" --signal all
   python scripts/report.py confirm "<record.json>" --signal scope --rating green --reason "<why>"
   ```

3. **Draft the executive summary** (below) and show it to the user.
4. Write what they agree, then give them the view's path:

   ```bash
   python scripts/report.py confirm "<record.json>" --summary "<the agreed text>" [--focus "..."] [--highlights "..."]
   ```

A same-day status rerun refuses to overwrite confirmed ratings (`--force` overrides). A regenerated sprint update keeps a summary already written, so it can be rerun mid-sprint to bring the board up to date. `report.py render "<record.json>"` rebuilds a view from its record.

**Ratings are the user's.** Never confirm or override one without them: a confirmed rating is what the next report's trend is measured against.

## Sharing a report

A status report, sprint update or charter goes to someone outside the work through `export`, never as the file itself:

```bash
python scripts/report.py export "<record.json>"                    # external: a filtered copy, as HTML
python scripts/report.py export "<record.json>" --pdf              # ... and printed to PDF
python scripts/report.py export "<record.json>" --audience owner --pdf   # the report as it is, as a PDF
python scripts/report.py export "<record.json>" --comm C.2        # the audience a communication in the Stakeholder Register sends it at
```

- **External is opt-in.** A RAID risk, issue or Change reaches the copy only when its entry is marked `Sharable = Y` (`raid-manager`); the command lists what it held back. *Help required* (it names who the work waits on), the evidence under each rating, the sprint board and the `facts` block are left out.
- **Only what was agreed is shared.** An external export refuses a report whose ratings or summary are not confirmed (`--force` overrides).
- **It reads as a page for someone outside:** no instructions to the owner, no empty sections, no WBS row IDs or objective codes, the done-when list open, and the same trend chips as the owner's view.
- **The HTML is what is shared**, as a file or a link opened in a browser: `<name> (external).html`, beside the record. **The PDF is optional** (`--pdf`), printed by the machine's Chrome or Edge, headless: no new dependency; with neither, the command says so and the page is printed by hand.

**The audience comes from the project's Stakeholder Register (TSP.13).** A status report records every communication that carries it (`audiences`: what, cadence, share level, recipients' names) and the owner's view says *Who receives this*; `export --comm C.n` takes the share level from that communication, and refuses one that carries another report, or a `--audience` that disagrees. A project with no register runs on the solo default, so its report reads as before. Contacts are never read. The external copy never says who else receives it, and a shared charter shows stakeholders by role and group, never by name.

## Trends

**One convention in every report and on the RAID board: up is better.** `trend_chip` shows a trend as an arrow in a tinted circle, with no word on the page: diagonal ↗ for a step better (green), ↘ worse (red), → steady, and straight ↑ / ↓ in a solid circle for a fast move. The word (*better*, *much worse*) is the tooltip, and `page` adds a one-line key at the foot of any page that shows a trend. Never draw a trend another way. Records store the level (-2 to +2), never an arrow; arrows in records written before this read with the convention they were written under (`legacy_level`). RAID's `Trend` is read with `raid_level`. On a phone, a table wider than the screen scrolls inside its card, and the key deliverables map stacks its months, one full-width column each.

## The executive summary

**Two or three sentences a stakeholder can follow without the registers.** It is a status update, not a charter: the reader knows what the project is, so do not describe it.

- **Plain language: no IDs, codes or colour names.** "Three tools were finished: a planning assistant, a notebook and a content manager", never "#67, #68 and #103 closed" or "the project is Amber".
- **Three beats:** what was achieved; where the work is heading or what is at risk, with slips as dates ("moved from end of October to early next year") and capacity as a proportion; what is needed from the reader, or that nothing is.
- **Mid-sprint, say so** ("six days into the sprint", "so far"). Read `facts.sprint_progress`; a report before the sprint ends is never worded as its outcome.
- **Draft only from the record's `facts` block**: what finished, what is in progress, the key deliverables that slipped and from when to when, Changes awaiting a decision, the top risks in words, capacity. Nothing from memory.

The script never writes this prose. A template can only restate the codes, which no outside reader can follow; the narrative needs judgement, so it is drafted here and confirmed by the user.

## The Essential 4, as proposed

Overall is the worst of the four; Mood (the fist of five) and On Outcome are shown but not counted. Green: aligned with the plan. Amber: not aligned, in recovery. Red: not aligned, no recovery.

| Signal | Amber | Red |
|---|---|---|
| On Time | a key deliverable planned past its baseline, or rebaselined to a later date this sprint (a move earlier is noted in the evidence, not counted) | a baseline passed on an open key deliverable, with no plan beyond it |
| On Scope | an approved Change this sprint, or more hours pulled in than committed | a Change undecided past its decision date, or a key deliverable nothing schedules |
| On Quality | a committed row without acceptance criteria, or a closure with an AC partial | a closure with an AC not met and no follow-up |
| Resources | planned over available (a stretch, never red), or 50-80% of committed hours delivered, pro-rated mid-sprint | under 50% delivered |

## Outcome and measures

The status report opens, after the summary, with what the project is for and whether it is getting there. Everything comes from the project's brief, `Project Brief.md` beside its registers, read through `project-definition-manager` (TSP.14), which owns it and writes it: the outcome sentence, the done-when list, the `**Serves:**` in its header line, and the Measures table. Without that skill installed, the section says so and the report runs on.

- **Each measure is scored 0-1 like a key result:** a number by its progress from baseline to target, a habit by its rate against the target rate, a milestone done or not. An aspirational (`A`) measure is met at 0.7 of its target.
- **Pace is judged at the date the value was taken:** on pace when the score is at least the share of the time from `From` to `By` that had passed by its `As of`. A value not read within its `Every` is **stale**; a measure past its `By` below target is **past due**.
- **Trend** compares each score with the last confirmed status report's.
- **On Outcome** is proposed like the Essential 4 and confirmed or overridden the same way (`confirm --signal outcome`), but **is not counted in Overall**:

| | Rule |
|---|---|
| Green | every measure on pace and current |
| Amber | a measure behind pace, stale, or with no value yet; an aspirational one past due |
| Red | a lag measure with no value, or a committed measure past its date below target |

With no brief, or a lean brief with no Measures table, the section says so and *On Outcome* is not proposed; the report runs as before. A table that breaks the layout (a value outside a vocabulary, a number that isn't one, a date that isn't one, no lag measure) gives **findings** on the page and in the run, never a failure: fix them in the brief.

**Decisions required** lists Changes awaiting an `Outcome` (`raid-manager`), never RAID Decisions: a Decision records a choice already made. **Help required** lists open items whose DRI is not the register's author (`meta.settings.author`).

## Adding a report

The tool is meant to grow. A new report is a new command in `report.py` that:

1. reads the registers it needs, through the same helpers (`discover`, `Wbs`, `raid_entries`, the sibling tools' `--json`);
2. writes a record with a `kind`, a `facts` block in plain words and a `summary` slot, through `write_record`, which also renders the view;
3. renders its view with the shared pieces (`page`, `summary_html`, `roadmap_html`, `risks_html`, `status_chip`, `trend_chip`, `info_tip`), so every report reads as one system. Text that explains how to read a section (how a score is computed, what a threshold means) goes behind `info_tip` beside the section title, never as a caption under it; content the reader acts on stays on the page;
4. gets checks in the repository's `tests/smoke_test.py`.

Then add it to the table above.
