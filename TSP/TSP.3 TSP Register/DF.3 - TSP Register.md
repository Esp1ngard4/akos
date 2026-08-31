# DF.3 — TSP Register

## Purpose

The inventory of every **Tool, System and Procedure** you depend on — and the recurring controls that keep each one alive.

This is the spine of the method. Every tool is a row; the row is what makes the tool findable, reviewable and, when the time comes, automatable. A tool with no row is a tool you will rediscover by accident, usually while looking for something else.

Alongside the inventory it holds the **control activities**: the recurring upkeep each tool needs, and the log of when each was actually performed. Without that, tools rot invisibly — they stay listed as implemented long after anyone last opened them.

Unlike the WBS and RAID registers, which are per-project, there is normally **one TSP register per estate**.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.3 TSP Register/` | Governance: purpose, conventions, relationships, history |
| `tsp-manager` skill | owned | `TSP.3 TSP Register/tsp-manager/` | Operating instructions and scripts |
| `templates/dashboard.html` | owned | inside the skill folder | Shell the dashboard renders into. **Shipped asset, not generated output** |
| `TSP Register.xlsx` | owned | wherever you keep it | **Source of truth.** Five sheets: Tools Register, Control Activities, Activity Log, Change Log, Lookups |
| `TSP Dashboard.html` | generated | alongside the register | Derived view, carrying its generation date; overwritten on refresh |

## What the skill covers (and this document doesn't repeat)

`tsp-manager/SKILL.md` is authoritative for the schema of all five sheets, the controlled vocabularies and their `Days` values, ID assignment rules, the register/retire/review procedures, and the create, refresh and audit commands.

This document covers the rest: why the register exists, its conventions, the two controls, and version history.

## Naming conventions

- **The register ID *is* the tool's number.** They are one identifier. If tools also get folders, name them `TSP.<id> <Name>/` so the folder and the row cannot diverge.
- **IDs are permanent.** Never reused, renumbered or reclaimed. Gaps are retired tools; a new tool takes `max(id) + 1`. Identifiers leak out into folder names, cross-references and years of notes — reusing one silently rebinds every one of them, and nothing errors.
- **Status and Relevancy are separate axes.** Status is lifecycle; Relevancy is how much the tool actually gets used. A tool can be fully implemented and touched twice a year. Collapsing them produces a register full of "implemented" tools nobody has opened in years.
- **Naming a skill in the `Skill` column is the expectation that it exists.** There is no separate "should be automated" flag: a skill named but not installed is a broken reference; a skill installed but named nowhere is automation nobody decided to keep. `audit_tsp.py` reports both.
- **The schema is yours to adapt.** The shipped columns reflect one estate. `Primary Area` may want to be team, service or value stream; you may not need `Relevancy` at all. Change it in `create_tsp.py` before creating the register, not after.

## The two controls

The register exists to be *worked*, not just held. Two controls do that:

1. **Periodic — planned controls.** Work the control activities whose next-due date has passed. Record what you did, and recompute the next due date from the frequency's `Days` value.

2. **Annual — the tool review.** Walk the register and ask, per tool: is it still used? If so, do I want to improve it? Batch improvements into a project rather than doing them inline, or the review becomes an unbounded refactor and you stop running it.

   **Stamp the review date on every row you touch, whatever the answer.** An unstamped row is indistinguishable from one never looked at — which is exactly how a review cadence dies unnoticed.

If the next-due dates are calculated, make sure something actually calculates them. A frequency column with a `Days` value *looks* like a working mechanism; confirm it is one, or every date will have been typed by hand and the whole schedule will drift.

## Relationship to other tools

**Every other tool** is a row in this register — including the [WBS](../TSP.1%20WBS%20Register/DF.1%20-%20WBS%20Register.md) and [RAID](../TSP.2%20RAID%20Register/DF.2%20-%20RAID%20Register.md) registers, and this tool itself. Building a tool is not finished until its row exists.

**Governance documents** — the `Doc Aux` flag records whether a tool has one. Whatever authors the document owns the document; this register owns the row. Neither does the other's write.

**Nothing syncs automatically.** Rows change because someone changed them. `audit_tsp.py` is the compensating control: it compares the register against what is actually on disk and reports the drift in both directions.

## Open items

| Item | Detail |
|---|---|
| `Primary AF` / `Other AFs` | Still carries "Areas of Focus" — vocabulary from the originating estate. Should be a neutral ownership field. Rename in `create_tsp.py` before it spreads into real registers |
| Folder reconciliation is convention-bound | `audit_tsp.py` matches folders named `<prefix>.<number> <name>`. Estates using a different scheme get no value from that check, though the other reports are layout-independent |
| `Next Due` is not computed | The `Days` value exists but nothing applies it; dates are entered manually. Automating it would make the periodic control self-sustaining |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.1 | 2026-08-31 | Fixed packaging: `templates/dashboard.html` was excluded by a `*.html` ignore rule intended for generated dashboards, so every clone got a tool that failed on first run. `refresh_tsp.py` now fails with an explanation rather than a traceback, and `create_tsp.py` prints the refresh command as an explicit next step |
| v1.0 | 2026-08-31 | Initial public version. Generalised from a personal system, and given `create_tsp.py` — the originating register was migrated out of a database rather than created by a script, so until now there was no way to stand up a fresh one. This governance document written; previously the tool shipped as a bare skill with no definition document |
