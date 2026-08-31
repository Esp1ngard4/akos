# DF.2 — RAID Register

## Purpose

A single register for the five things that need tracking alongside a project's planned work but don't belong in its plan: **R**isks, **A**ctions, **I**ssues, **D**ecisions and **I**deas.

They live together because they convert into each other. A risk that materialises becomes an issue. An issue that needs work spawns an action. An idea deferred often resurfaces as a decision. Splitting them across separate trackers means losing that lineage and maintaining five things that each go stale independently.

Each project gets its own register.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.2 RAID Register/` | Governance: purpose, conventions, relationships, history |
| `raid-dashboard` skill | owned | `TSP.2 RAID Register/raid-dashboard/` | Operating instructions and scripts |
| `RAID <Project>.xlsx` | owned, per project | wherever you keep project management artefacts | **Source of truth** — one per project |
| `RAID Dashboard.html` | generated | alongside the register | Derived view; overwritten on refresh, never hand-edited |
| `AuxMat/` | owned, per project | alongside the register | Working documents for individual entries; created automatically |

There is no separate template file — `create_raid.py` builds the register programmatically, so the schema has exactly one definition.

## What the skill covers (and this document doesn't repeat)

`raid-dashboard/SKILL.md` is authoritative for the full column schema, the risk-analysis block (probability, severity, response strategy, residual risk), the priority formula, dashboard features including the heat map, and the create/refresh commands.

This document covers the rest: why the register exists, its types, naming, relationships and version history.

## The five types

| Type | When to use |
|---|---|
| **Risk** | Something that *might* happen and would affect the project, positively or negatively |
| **Action** | A concrete follow-up needing tracking beyond a simple task — multi-step, cross-party, or requiring formal acceptance |
| **Issue** | Something that *has* happened and needs resolving |
| **Decision** | A decision made, with its rationale — recorded for traceability |
| **Idea** | Captured for future consideration; the someday/maybe of project management |

**Decisions are the type most often skipped and the most valuable in hindsight.** A decision recorded with what it replaced and why is what stops the same question being reopened a year later by someone — possibly you — who cannot see the reasoning.

## Naming conventions

- **File**: `RAID <Project>.xlsx`; dashboard `RAID Dashboard.html` alongside.
- **Entry IDs** are sequential integers within a register, referenced externally as `{type initial}.{id}` — `R.5` for risk 5, `I.3` for issue 3, `A.12` for action 12.
- **Headers are on row 6**, not row 1 — rows 2 and 3 carry the register title and creation date. Anything reading the sheet must account for this.

## Relationship to other tools

**Task tracker** — the register carries a `Tracked Externally` Y/N flag, and nothing more. No task IDs, no links, no sync. Keeping the linkage one-way avoids the register going stale every time a task moves. For traceability in the useful direction, put the RAID ID in the tracker item's description (`RAID: R.5`).

If you want real task creation, delegate it to a skill that owns your tracker's conventions rather than building tracker-specific logic in here.

**[WBS register](../TSP.1%20WBS%20Register/DF.1%20-%20WBS%20Register.md)** — the roadmap of intended work. A RAID Action may correspond to a WBS item; they are maintained independently and cross-referenced by ID.

**Calendar** — review dates are managed manually. The dashboard's review view flags overdue entries; nothing schedules them for you.

## Maintenance

- **Regular use** — add and edit entries, then regenerate the dashboard.
- **Review cycle** — use the dashboard to find entries not reviewed recently; update the review dates when you touch them. An unstamped entry is indistinguishable from one never looked at.
- **Closing** — set status to Resolved or Closed and fill the closure fields. Closed entries drop out of the active counts but stay in the register permanently.
- **Before a schema change** — copy the register to a `PreviousV/` folder first.

## Open items

| Item | Detail |
|---|---|
| `Tracked Externally` is a bare flag | Deliberate, but it means the register cannot tell you *which* tracker item corresponds to an entry. Revisit only if the one-way convention proves insufficient |
| Header row at 6 is unusual | It exists to carry a title block. Anything parsing the sheet must know; a reader who assumes row 1 gets nothing |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-08-31 | Initial public version. Generalised from a personal system: a vendor-specific tracking column renamed to `Tracked Externally` across schema, dashboard and documentation, and this governance document written — previously the tool shipped as a bare skill with no definition document |
