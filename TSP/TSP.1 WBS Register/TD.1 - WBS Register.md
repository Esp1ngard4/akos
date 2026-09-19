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
- **Hierarchy lives in `Parent`**, which holds the parent's stable `ID`. `Code` displays the hierarchy but does not define it; a tree read from `Code` prefixes silently repoints itself the first time the breakdown is renumbered.
- **One collection, three axes.** `Type` is the level (Feature / Enabler / Story / Task), `Delivers` is the artifact a row produces (Tool / System / Process / Document), and `Nature` is what is being done to it (Build / Improve / Analyse / Fix / Maintain). One field carrying all three cannot be queried on any of them.
- **The deliverable is the parent; work on it are children.** A Feature is the thing that exists when the work is done. A tool enhanced three times has one Feature row and three pieces of work beneath it, not three peer Features.
- **Deliverables are a view, not a collection**: a deliverable is a row whose `Key Deliverable` is `Y`, and the dashboard rolls its progress up from descendants through `Parent`. A separate list cannot say which work delivers which deliverable, which is the only reason to draw the distinction at all.

## Relationship to other tools

**Task tracker** — items move from the WBS into a tracker when committed to a sprint. One-way and manual. The WBS is not a task list and degrades into an unusable one if treated as such.

**[RAID register](../TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md)** — different jobs. WBS is the roadmap of intended work; RAID is the live register of risks, issues, decisions and ideas. A RAID Action may correspond to a WBS item, but they are maintained independently and cross-referenced by ID.

**[TSP register](../TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md)** — this tool is itself a registered tool.

Nothing syncs automatically. The dashboard is a snapshot, not a live view.

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
| v1.3 | 2026-09-19 | **Deliverables became a view of the register rather than a second collection, and `Type` stopped doing three jobs at once.** `Type` had mixed decomposition level, artifact kind and nature of effort into one column that nothing validated - it was absent from the register's vocabularies entirely - so two registers could and did read it incompatibly, one as level and one as artifact kind. It is now level alone (`Feature / Enabler / Story / Task`), with `Delivers` and `Nature` carrying the other two; all three are registered vocabularies that `wbs.py check` enforces. **`Parent` added**, holding the parent's stable `ID`: the hierarchy had existed only as a string prefix in `Code`, the one field this document says is renumbered, so nothing recorded which work delivered what - the gap that made a separate deliverables list look necessary. **`key_deliverables` retired** in favour of a `Key Deliverable` Y/N column valid only on Feature and Enabler rows; the collection could not express the link between a deliverable and the work delivering it, and in practice held the same items the backlog already had, recorded twice and unlinked. **`wbs.py` added** - the tool had no operations script, so every write was a hand edit with nothing enforcing ID reuse, parent existence, cycles or vocabularies; it carries `add`, `set`, `check` and a dry-run-by-default `migrate`. Dashboard gained a Deliverables tab rolling progress up through `Parent` |
| v1.2 | 2026-09-01 | Documentation caught up with the register format. The body still described the spreadsheet two sections above the entry announcing it was gone — a template file that no longer ships, an `.xlsx` source of truth, and sheets rather than collections. `Cancelled` added to the Status vocabulary: there was no state for work abandoned rather than delivered, so a dropped item either lost the record of why or held a status the schema did not recognise, which the dashboard then counted as no status at all. `Key Dependencies` documented as `ID` references — the skill had described them as `Code` references, which is the field explicitly expected to be renumbered. Two defects fixed: `create_wbs.py` wrote the Status vocabulary as `Backlog` where the documentation and the dashboard both say `Portfolio Backlog`, and `refresh_wbs.py` still carried the spreadsheet readers it stopped calling when `main()` moved to JSON |
| v1.1 | 2026-09-01 | **The register is JSON.** Every write went through a script anyway, and a spreadsheet cost a subprocess to read, a dependency to install, and a file lock whenever the application or a sync client held it. The dropdowns a spreadsheet gave back are enforced more strictly by the commands - argparse refuses an invalid value where a dropdown only warns and paste bypasses entirely. The `.xlsx` template the skill used to ship is gone: `create_wbs.py` builds the register programmatically, so there is no asset left that a copy of the skill can be missing. The tool now has **no runtime dependencies at all** |
| v1.0 | 2026-08-31 | Initial public version. Generalised from a personal system: local vocabulary removed, template renamed to drop a local prefix, and this governance document written — previously the tool shipped as a bare skill with no definition document, which the method itself identifies as the broken case |
