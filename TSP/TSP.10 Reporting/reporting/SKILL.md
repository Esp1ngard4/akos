---
name: reporting
description: Generates reports from the registers - the sprint update (the last sprint's outcome beside the new sprint's commitments, across projects, after sprint planning) and a project status report with the Essential 4 (On Time, On Scope, On Quality, Resources) proposed from the WBS, RAID and sprint record - each as a JSON record plus an HTML view, opening with an executive summary drafted in plain language for the user to confirm. Use whenever the user asks for a status report, a project update, a sprint report, an executive summary, "how is the project doing", the Essential 4 or a RAG status, or wants to confirm or override a report's ratings or summary. Also used by the sprint ceremonies: status reports at the close-out, the sprint update after planning (sprint-facilitator). Not for the WBS or RAID dashboards themselves (wbs-manager, raid-manager).
---

# Reporting (TSP.10)

Reports are generated from the registers, never written from memory. Each report is two files:

| File | Role |
|---|---|
| `<name>.json` | **The record**: what the report found, with the evidence; then the user's confirmations, overrides and summary. The next report reads it. |
| `<name>.html` | **The view**, generated from the record. Never edited by hand. |

## Requirements

Python 3, standard library only. Uses sibling skills, found beside this one in the skills folder: `wbs-manager` (its register and date modules, `wbs.py metrics --json` and `sprint_board()`) and `sprint-facilitator` (`sprint_record.py goals --json` and its table reader). `raid-manager` is optional: without a RAID register the reports run, with no risks, Changes or help to show.

## The reports

| Report | Command | Writes to |
|---|---|---|
| **Sprint update**, after planning: the last sprint (goals and verdicts, what was delivered) beside this sprint (goals, committed items largest first, capacity, confidence); each project's overall status when several; key deliverables by month; goal history and focus; top risks; hours by area; and, on its own **Sprint board** tab, every project's cards by project and deliverable, To do / Doing / Done, as of the run (rerun mid-sprint to refresh it). The overview is the page that opens and prints; the board is the deep dive | `report.py sprint --sprint <the sprint being started> --records "<sprint records>" --project "<project folder>" [--project ...]` | `Reports/Sprint Update/<sprint ID> Sprint Update.*`, beside the records folder (`--out-dir` to choose) |
| **Project status**, at the close-out or on demand: Essential 4 with evidence and trend, decisions and help required, key deliverables by month (delivered and due), top risks | `report.py status "<project folder>" [--records "<sprint records>"] [--sprint <ID>] [--as-of YYYY-MM-DD]` | `<project folder>/Reports/Status/<date> Status.*` |

A project folder is any folder holding the project's WBS register and, optionally, its RAID register; they are found by their `meta.kind`, so their file names do not matter. Pass every project the sprint spans to `sprint`; it refuses a sprint not yet planned, since nothing is committed. Without `--records`, `status` cannot read the sprint's capacity or confidence, and says less about Resources and Mood.

The sprint records must carry structured goals (goal IDs, *Done when*, an `Area` and `Goal` column on committed items), which `sprint_record.py plan` writes. A record from before that reads as unstructured, and its goals are left out rather than guessed.

## Running a report

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

## The executive summary

**Two or three sentences a stakeholder can follow without the registers.** It is a status update, not a charter: the reader knows what the project is, so do not describe it.

- **Plain language: no IDs, codes or colour names.** "Three tools were finished: a planning assistant, a notebook and a content manager", never "#67, #68 and #103 closed" or "the project is Amber".
- **Three beats:** what was achieved; where the work is heading or what is at risk, with slips as dates ("moved from end of October to early next year") and capacity as a proportion; what is needed from the reader, or that nothing is.
- **Mid-sprint, say so** ("six days into the sprint", "so far"). Read `facts.sprint_progress`; a report before the sprint ends is never worded as its outcome.
- **Draft only from the record's `facts` block**: what finished, what is in progress, the key deliverables that slipped and from when to when, Changes awaiting a decision, the top risks in words, capacity. Nothing from memory.

The script never writes this prose. A template can only restate the codes, which no outside reader can follow; the narrative needs judgement, so it is drafted here and confirmed by the user.

## The Essential 4, as proposed

Overall is the worst of the four; Mood (the fist of five) is shown but not counted. Green: aligned with the plan. Amber: not aligned, in recovery. Red: not aligned, no recovery.

| Signal | Amber | Red |
|---|---|---|
| On Time | a key deliverable planned past its baseline, or rebaselined this sprint | a baseline passed on an open key deliverable, with no plan beyond it |
| On Scope | an approved Change this sprint, or more hours pulled in than committed | a Change undecided past its decision date, or a key deliverable nothing schedules |
| On Quality | a committed row without acceptance criteria, or a closure with an AC partial | a closure with an AC not met and no follow-up |
| Resources | planned over available (a stretch, never red), or 50-80% of committed hours delivered, pro-rated mid-sprint | under 50% delivered |

**Decisions required** lists Changes awaiting an `Outcome` (`raid-manager`), never RAID Decisions: a Decision records a choice already made. **Help required** lists open items whose DRI is not the register's author (`meta.settings.author`).

## Adding a report

The tool is meant to grow. A new report is a new command in `report.py` that:

1. reads the registers it needs, through the same helpers (`discover`, `Wbs`, `raid_entries`, the sibling tools' `--json`);
2. writes a record with a `kind`, a `facts` block in plain words and a `summary` slot, through `write_record`, which also renders the view;
3. renders its view with the shared pieces (`page`, `summary_html`, `roadmap_html`, `risks_html`, `status_chip`), so every report reads as one system;
4. gets checks in the repository's `tests/smoke_test.py`.

Then add it to the table above.
