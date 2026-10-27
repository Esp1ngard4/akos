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

## Relationship to other tools

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
| v1.12 | 2026-10-27 | **From any card to its parent and its children.** A card's details show the path from the top row down to its parent above the title, each level a link, and list its children with status and hours; a sprint card's path is links. Opening a card puts `#item=<ID>` in the address: a link opens the dashboard at that card (Copy link), and the browser's Back returns to the card before. Chosen from three previews, at desktop and phone width. |
| v1.11 | 2026-10-27 | **`migrate` keeps a register's own vocabulary.** It replaced any vocabulary that differed from the standard, so a project that had added a value of its own (a `Delivers` its work needed) lost it, and every row using it became an error. It now adds the standard values the register lacks, renames a renamed one in place, and keeps the rest. Found adapting an existing project's register to AKOS. |
| v1.10 | 2026-10-27 | **Work the sprint never committed to asks first.** `set` or `add` to `Implementing` or `Done` on a row the running sprint has not committed to is refused until it is answered: `--pulled-in "<effect>"` (sets `Sprint Added`, notes the effect, prints the line for the sprint record) or `--outside-sprint "<why>"` (notes it, marks nothing). A parent counts only when it is committed itself, never through a committed child. `pullins` lists rows pulled into the running sprint that its record does not name, across every register under a root. A split into an earlier sprint keeps later commitments off the delivered part. *Reconciling with a task tracker* adds that one task may serve several rows. The convention reads one folder per Deliverable or Feature. |

Earlier entries are not kept here. This repository is version-controlled, so the full history of this document is in its git log; a copy of the system kept outside version control should snapshot to `PreviousV/` instead, per `method/05-versioning-discipline.md`.
