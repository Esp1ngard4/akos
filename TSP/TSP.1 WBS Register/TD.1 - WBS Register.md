# TD.1 — WBS Register

## Purpose

A Work Breakdown Structure register: the full picture of what a project could deliver, what is planned, what is in flight and what is done.

It answers a different question from a task tracker. A tracker holds committed, active work — what someone is doing this sprint. The WBS holds the *thinking* that precedes commitment: the decomposition, the effort estimates, the acceptance criteria, the dependencies, the items deliberately not being done yet. Work flows out of the WBS into a tracker when it is committed, not the other way round.

Each project gets its own register. There is no central one.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.1 WBS Register/` | Governance: purpose, conventions, relationships, history |
| `wbs-manager` skill | owned | `TSP.1 WBS Register/wbs-manager/` | Operating instructions and scripts |
| `references/descriptions.md` | owned | `TSP.1 WBS Register/wbs-manager/references/` | A row's description by its type: the shape, the labels, examples |
| `WBS <Project>.json` | owned, per project | wherever you keep project management artefacts | **Source of truth** — one per project |
| `WBS Dashboard.html` | generated | alongside the register | Derived view; overwritten on refresh, never hand-edited |

## What the skill covers (and this document doesn't repeat)

`wbs-manager/SKILL.md` is authoritative for the schema of both collections, the allowed values, the ID-versus-Code distinction, dashboard features, and the create/refresh commands.

This document covers what the skill doesn't: why the register exists, its naming rules, how it relates to other tools, and version history.

## Naming conventions

- **File**: `WBS <Project>.json`; dashboard `WBS Dashboard.html` in the same folder.
- **`ID` is permanent; `Code` is not.** This distinction is the one thing most worth understanding. `ID` is a stable integer that never changes — it is what other documents, folders and cross-references point at. `Code` is the hierarchical display position (`1`, `1.1`, `1.2`) and is *expected* to be renumbered whenever the breakdown is reorganised. Anything keyed off `Code` breaks the first time you insert a row; key off `ID`.
- **Execution folders follow the work, not the document type.** A folder per Feature, a nested one once a Story or sub-deliverable has about three documents, and the type as a filename suffix. The question asked of these folders later is "what happened with this piece of work", and folders by type would answer it from several places. The only folders by kind are `Inputs/` and `Deliverables/`, for material received or handed over, neither of which is edited. Document headers carry the row ID and date, not a status: a status copied into a document goes stale without anything noticing. A project's own folder names live in its register's `meta.execution`, so the skill stays cross-project.
- **Hierarchy lives in `Parent`**, which holds the parent's stable `ID`. `Code` displays the hierarchy but does not define it; a tree read from `Code` prefixes silently repoints itself the first time the breakdown is renumbered.
- **One collection, three axes.** `Type` is the level (Feature / Enabler / Story / Task), `Delivers` is the artifact a row produces (Tool / System / Process / Document), and `Nature` is what is being done to it (Build / Improve / Analyse / Fix / Maintain). One field carrying all three cannot be queried on any of them.
- **The deliverable is the parent; work on it are children.** A Feature is the thing that exists when the work is done. A tool enhanced three times has one Feature row and three pieces of work beneath it, not three peer Features.
- **Deliverables are a view, not a collection**: a deliverable is a row whose `Key Deliverable` is `Y`, and the dashboard rolls its progress up from descendants through `Parent`. A separate list cannot say which work delivers which deliverable, which is the only reason to draw the distinction at all.
- **Effort comes from leaves.** A parent's own estimate is the top-down figure made before it was broken down, so it is compared with its children's sum, never added to it (PMI's 100% rule). The Breakdown shows it as the original with the difference; a committed parent counts as an item in a sprint, with its children's hours there.
- **Partly done work is split, not carried.** Carrying it whole credits the hours done in one sprint to the sprint where it closes. `split` makes the row the parent of what was delivered (closed in its sprint) and what is left; both keep the commitment history, so every sprint still shows what it committed and delivered hours count once. A piece split again adds the rest beside it: a split cuts by sprint, not by meaning, so it adds no layer.
- **A row owns its sprint, and placing work under a parent asks what it means.** A commitment to a parent doesn't commit what is filed under it: part of a breakdown is often left for later, and a new row under a committed deliverable is as likely to be new work as planned work. So the start gate reads only the row's own sprint fields, the rule the sprint metrics count by, and the tool asks at the moment of breakdown. A row with no sprint, under a parent committed to the running sprint, is part of that commitment, taken on now, or for later. An open row under a closed parent means the parent didn't deliver its outcome, so it is reopened, or the row belongs elsewhere: any row, a deliverable included, is finished when its purpose is met and reopened when it wasn't. Whether a new child widens its parent is the person's judgment. The tool reminds, and the 100% rule measures it afterwards: children's hours above the parent's estimate mean the scope grew or the estimate was optimistic, both worth knowing.

## Relationship to other tools

**Team Status Board (TSP.15)** — where a team updates its status on a sprint board, the register keeps one writer: the board is consolidated into it, and a mid-sprint commitment reaches the board through its update.

**Task tracker** — items move from the WBS into a tracker when committed to a sprint. One-way and manual. The WBS is not a task list and degrades into an unusable one if treated as such.

**[RAID register](../TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md)** — different jobs. WBS is the roadmap of intended work; RAID is the live register of risks, issues, decisions and ideas. A RAID Action may correspond to a WBS item, but they are maintained independently and cross-referenced by ID. A RAID entry can name the row it bears on in its `WBS Ref` (`<scope>#<id>`); `wbs.py refined --raid` shows those open entries next to the candidate at grooming.

**[TSP register](../TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md)** — this tool is itself a registered tool.

Nothing syncs automatically. The dashboard is a snapshot, not a live view.

## Reconciling with a task tracker

Once a sprint's work lives in two places — rows here, tasks in a tracker — they drift: a committed row nobody is doing, a task finished while its row is still open, a task that names no row, estimates that disagree. Checking the two against each other is reconciliation, and it is worth doing at every close-out.

**This tool does not ship it.** What a reconciliation reads is defined by the platform a project uses: how tasks are exported, what marks one as part of a sprint, where its estimate lives. A tracker-neutral version would be a guess at every platform and right for none, so it belongs to the project, built for its own tracker.

**What this tool provides is the hook.** Every row has a stable `ID` that is never reused, and a task can cite it — `WBS: <scope> - ID <n>`, or whatever shape the tracker allows — so a reconciliation can join the two without guessing. Report disagreements; write nothing. A row is a deliverable and its tasks are the operational work under it, one to many, so the question is coverage and status agreement, never field equality. The reverse happens too: one task can serve several rows, and cite each. Then it covers all of them, and no single row's estimate is compared with it.

## Maintenance

### Regular use

1. **Add and edit items** in the register - IDs are assigned by you and never reused.
2. **Regenerate the dashboard** after every batch of edits. It carries no generation
   date, so a stale dashboard is indistinguishable from a current one; refresh rather
   than trusting memory.
3. **Move committed work out** to your task tracker. The WBS is not a task list and
   degrades into an unusable one if treated as such.

### Periodic

- **Review stalled items** - anything sitting in `Not Started` across several sprints
  is either genuinely deferred, in which case say so, or quietly abandoned.
- **Re-check estimates** on items still ahead of you; the ones written at project
  start are the least reliable.
- **Before a schema change or bulk rewrite** - copy the register to `PreviousV/` first.

## Open items

| Item | Detail |
|---|---|
| Dashboard has no generation timestamp | Unlike the TSP dashboard, nothing on the page says when it was rendered, so staleness is invisible |
| No bulk import | Items are added one at a time or by editing the JSON directly; there is no CSV import path |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.25 | 2026-11-06 | **A project's categories group its work.** `Category` was in every register's field order but nothing used it: no flag, no list, only a chip in a row's detail, so its values drifted and nothing could group by it, while the calendar view in the reports needs a grouping inside each project. Each register now keeps its own ordered list (`wbs.py categories`, the `category` vocabulary), held by `add`, `set` and `check`, free text without one; `--category` sets it; a row inherits its nearest categorised ancestor's, computed and never stored, so categorising the deliverables is enough. The dashboard filters by category and shows the inherited value. Projects keep their own lists: a view across projects groups by project first. Register change: none. |
| v1.24 | 2026-11-06 | **Milestones and the delivery journey.** A row has one end date, so a deliverable reached in stages (proven in a PoC, then in production a year later) told only its last. Milestones now sit beside the rows, as PMBOK's milestone list does: a `milestones` collection (M1…, title, optional stage, write-once baseline, notes, dropped with a closure), a per-register ordered `stage` vocabulary the project sets, and a `Milestone` field on the rows that reach one. A milestone is derived, never marked: reached when its rows are done, else planned from them, on plan or late against its baseline. `journey()` reads a row's children by stage, once, for the dashboard and the status report. The roadmap gains a milestone lane and date guides, the card a delivery journey, the Deliverables tab the next milestone. Register change: one collection, one row field, one vocabulary, added by `migrate`. |
| v1.23 | 2026-11-05 | **The close-out's decision lives on the row.** `closeout` records, for a row a sprint held and did not finish, an outcome (carry to the next sprint, land on a named later one, park in Portfolio Backlog, drop as Cancelled), its target and why, in a new list field, `Sprint Closeouts`, with a *Closed out* note; the sprint fields are never rewritten. Before, planning gathered every unfinished row as carryover, so a row meant to be parked came back, and nothing told a decided row from one nobody looked at. A closed-out row is no longer live in that sprint, so `check` stops reading it as a commitment and warns instead on an open row in an ended sprint with no closeout. `metrics` breaks carryover and unfinished pull-ins down by outcome and keeps a row dropped at a close-out in that sprint's figures. `closeouts --sprint` gives the record's carryover lines, `--target` planning's candidates, and a carry with no `--reason` takes the closeout's. A close-out may start early. **The sprint board places a card where it stood in that sprint**, not by today's status: a *Closed out* column with each card's outcome, the close-out's progress from its first decision or the sprint's last day, *to decide* and *no decision* flags, and the card's journey across sprints. Register change: one optional field, added to the field order by `migrate`. |
| v1.22 | 2026-11-04 | **Reopening a closed row by hand asks why and undoes its finish.** `set --status` from Done or Cancelled to an open status needs `--reopen "<why>"`, clears Actual End and Sprint Ended and notes Reopened, the same reopen `--reopen-parent` does. Before, a row reopened by hand kept both, so the roadmap and the metrics went on counting it finished. |
| v1.21 | 2026-11-03 | **A row owns its sprint; work under a parent is asked about.** The start gate no longer inherits a parent's commitment: a new row under a committed deliverable went in as planned work, and one under a closed feature went in with nothing asked. `add` and `set --parent` now ask. Under a closed parent the choice is `--reopen-parent` (it and every closed row above it reopen, with `Actual End` and `Sprint Ended` cleared) or filing elsewhere. Under a committed parent, a row with no sprint takes `--in-sprint`, `--pulled-in` or `--later`. Otherwise a reminder to update the parent if the row widens it. `check` warns on an open row under a closed parent, and the over-estimate warning names an optimistic estimate as well as grown scope. A Deliverable is finished when its purpose is met. |
| v1.20 | 2026-11-03 | **A description template per row type.** `references/descriptions.md` sets each type's shape from best practice: one sentence on what the row delivers or changes, then labelled parts. Deliverable: Purpose, Not. Feature: Value (naming the outcome it serves and the measure it should move), Approach, Not, PRD. Story: Problem, Approach. Analyse: Question, Decides. Fix: Symptom, Cause. Task: one line. The description is the current state, about 80 words (100 for a Deliverable or Feature); history goes to a titled note. `wbs.py add` prints the shape when a row has no description. The card shows the labels as sections, renders bold, paragraphs, bullet lines and code, and folds a long description after its first paragraph. |
| v1.19 | 2026-11-03 | **Comments and criteria read as entries.** The card shows each Comments entry as its own block, with its date, a label (Closure, Note, Carried, Pulled in, Split, Outside sprint) and its title. A long entry folds to its first line, the newest open. The closure note is pinned, with *What happened*, *AC* and *Follow-up* as sections and a verdict badge per criterion. `ID n` in the text links to the card. The acceptance criteria show one per line, numbered, each with its closure verdict on a closed row. A number starts a criterion only when it continues the sequence; the Verification tab counts criteria the same way. `wbs.py note --title` gives an entry a heading, and SKILL.md asks for notes written to be read in a list. |
| v1.18 | 2026-10-29 | **The Execution folder's conventions move to Work Management (TSP.17).** The team, who work in that folder, did not load this skill; the conventions now have one owner, used by the people who apply them. This skill keeps what it reads: a row's specification by its `ID <n>` (`refined`), and `meta.execution`. |
| v1.17 | 2026-10-28 | **A new register can declare its Execution folder.** `create_wbs.py --execution <folder>` writes `meta.execution.folder` at creation, so a project set up by `install.py init`, whose folders the artifact register numbers (`01. Execution`), needs no hand edit. |
| v1.16 | 2026-10-28 | **A team updates its status on a board, and the WBS keeps one writer** (TSP.15): a pull-in, a carried split or a cancellation is followed by the board's update, where a board exists. `wbs.py` itself knows nothing of boards. |
| v1.15 | 2026-10-27 | **Sprints: one set of sprint figures, and the trend in Analytics.** The Sprint Board tab becomes Sprints: every sprint with work, newest first, the running one open and the older ones folded to their figures; each header is the Current Sprint strip, from `wbs.py metrics`; rows grouped Committed, Carried in, Pulled in and Closed here, each with a link to its parent. Analytics opens with committed against delivered hours per sprint and the velocity (average delivered over the last three ended sprints). The tab's own sprint sum, which disagreed with the metrics (Synaptica Q4.1: 200h against 76h committed and 176h delivered), goes, with the Unplanned list and the filters only it used. |
| v1.14 | 2026-10-27 | **The Breakdown reads at any depth.** A level-1 row is a section band; below it a thin guide line per level shows which rows are siblings; a wrapped title stays under its own level; parent rows are semibold. Before, 18px a level, wrapped titles back at the left edge and parents looking like leaves lost the hierarchy below level 2. Chosen from three previews. |
| v1.13 | 2026-10-27 | **A sprint card names its direct parent only.** On one line, cut with an ellipsis, the full chain in its tooltip; in a lane, a parent that is the lane's head is not repeated. The full path stays in the card's details. The full path ran outside the card on a board with long titles. |
| v1.12 | 2026-10-27 | **From any card to its parent and its children.** A card's details show the path from the top row down to its parent above the title, each level a link, and list its children with status and hours; a sprint card's path is links. Opening a card puts `#item=<ID>` in the address: a link opens the dashboard at that card (Copy link), and the browser's Back returns to the card before. Chosen from three previews, at desktop and phone width. |
| v1.11 | 2026-10-27 | **`migrate` keeps a register's own vocabulary.** It replaced any vocabulary that differed from the standard, so a project that had added a value of its own (a `Delivers` its work needed) lost it, and every row using it became an error. It now adds the standard values the register lacks, renames a renamed one in place, and keeps the rest. Found adapting an existing project's register to AKOS. |
| v1.10 | 2026-10-27 | **Work the sprint never committed to asks first.** `set` or `add` to `Implementing` or `Done` on a row the running sprint has not committed to is refused until it is answered: `--pulled-in "<effect>"` (sets `Sprint Added`, notes the effect, prints the line for the sprint record) or `--outside-sprint "<why>"` (notes it, marks nothing). A parent counts only when it is committed itself, never through a committed child. `pullins` lists rows pulled into the running sprint that its record does not name, across every register under a root. A split into an earlier sprint keeps later commitments off the delivered part. *Reconciling with a task tracker* adds that one task may serve several rows. The convention reads one folder per Deliverable or Feature. |

Earlier entries are not kept here. This repository is version-controlled, so the full history of this document is in its git log; a copy of the system kept outside version control should snapshot to `PreviousV/` instead, per `method/05-versioning-discipline.md`.
