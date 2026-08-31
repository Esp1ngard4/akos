# DF.1 — WBS Register

## Purpose

A Work Breakdown Structure register: the full picture of what a project could deliver, what is planned, what is in flight and what is done.

It answers a different question from a task tracker. A tracker holds committed, active work — what someone is doing this sprint. The WBS holds the *thinking* that precedes commitment: the decomposition, the effort estimates, the acceptance criteria, the dependencies, the items deliberately not being done yet. Work flows out of the WBS into a tracker when it is committed, not the other way round.

Each project gets its own register. There is no central one.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.1 WBS Register/` | Governance: purpose, conventions, relationships, history |
| `wbs-manager` skill | owned | `TSP.1 WBS Register/wbs-manager/` | Operating instructions and scripts |
| `WBS Template.xlsx` | owned | inside the skill folder | Seed for new registers; `create_wbs.py` copies it |
| `WBS <Project>.xlsx` | owned, per project | wherever you keep project management artefacts | **Source of truth** — one per project |
| `WBS Dashboard.html` | generated | alongside the register | Derived view; overwritten on refresh, never hand-edited |

## What the skill covers (and this document doesn't repeat)

`wbs-manager/SKILL.md` is authoritative for the column schema of all three sheets, the allowed values, the ID-versus-Code distinction, dashboard features, and the create/refresh commands.

This document covers what the skill doesn't: why the register exists, its naming rules, how it relates to other tools, and version history.

## Naming conventions

- **File**: `WBS <Project>.xlsx`; dashboard `WBS Dashboard.html` in the same folder.
- **`ID` is permanent; `Code` is not.** This distinction is the one thing most worth understanding. `ID` is a stable integer that never changes — it is what other documents, folders and cross-references point at. `Code` is the hierarchical display position (`1`, `1.1`, `1.2`) and is *expected* to be renumbered whenever the breakdown is reorganised. Anything keyed off `Code` breaks the first time you insert a row; key off `ID`.
- **Two sheets, two levels**: `Key Deliverables` holds the handful of outcomes the project exists to produce; `WBS` holds the items that build them, each pointing at a deliverable.

## Relationship to other tools

**Task tracker** — items move from the WBS into a tracker when committed to a sprint. One-way and manual. The WBS is not a task list and degrades into an unusable one if treated as such.

**[RAID register](../TSP.2%20RAID%20Register/DF.2%20-%20RAID%20Register.md)** — different jobs. WBS is the roadmap of intended work; RAID is the live register of risks, issues, decisions and ideas. A RAID Action may correspond to a WBS item, but they are maintained independently and cross-referenced by ID.

**[TSP register](../TSP.3%20TSP%20Register/DF.3%20-%20TSP%20Register.md)** — this tool is itself a registered tool.

Nothing syncs automatically. The dashboard is a snapshot, not a live view.

## Maintenance

- **Regular use** — edit the register, then regenerate the dashboard. It carries no generation date of its own, so a stale dashboard is indistinguishable from a current one; refresh after every batch of edits rather than trusting memory.
- **Before a schema change or bulk rewrite** — copy the register to a `PreviousV/` folder first.
- **Periodically** — review items sitting in `Not Started` across several sprints. They are either genuinely deferred, in which case say so, or quietly abandoned.

## Open items

| Item | Detail |
|---|---|
| Dashboard has no generation timestamp | Unlike the TSP dashboard, nothing on the page says when it was rendered, so staleness is invisible |
| No bulk import | Items are added one at a time or by editing the xlsx directly; there is no CSV import path |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-08-31 | Initial public version. Generalised from a personal system: local vocabulary removed, template renamed to drop a local prefix, and this governance document written — previously the tool shipped as a bare skill with no definition document, which the method itself identifies as the broken case |
