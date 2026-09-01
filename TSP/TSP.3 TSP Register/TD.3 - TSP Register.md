# TD.3 — TSP Register

## Purpose

The inventory of every **Tool, System and Procedure** you depend on — and the recurring controls that keep each one alive.

This is the spine of the method. Every tool is a row; the row is what makes the tool findable, reviewable and, when the time comes, automatable. A tool with no row is a tool you will rediscover by accident, usually while looking for something else.

Alongside the inventory it holds the **control activities**: the recurring upkeep each tool needs, and the log of when each was actually performed. Without that, tools rot invisibly — they stay listed as implemented long after anyone last opened them.

Unlike the WBS and RAID registers, which are per-project, there is normally **one TSP register per estate**.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.3 TSP Register/` | Governance: purpose, conventions, relationships, history |
| `tsp-manager` skill | owned | `TSP.3 TSP Register/tsp-manager/` | The register half: the row, the dashboard, the audit |
| `td-author` skill | owned | `TSP.3 TSP Register/td-author/` | The documentation half: authoring and auditing TDs and their paired SKILL.md |
| `templates/dashboard.html` | owned | inside the skill folder | Shell the dashboard renders into. **Shipped asset, not generated output** |
| `TSP Register.json` | owned | wherever you keep it | **Source of truth.** Four collections — Tools Register, Control Activities, Activity Log, Change Log — plus the controlled vocabularies, which live in the `meta` envelope rather than as a collection of their own |
| `TSP Dashboard.html` | generated | alongside the register | Derived view, carrying its generation date; overwritten on refresh |

**This tool has two skills, and the boundary between them is the point.**
`tsp-manager` owns the register row; `td-author` owns the tool definition
document. When a tool gains or loses a TD, one writes the document and the other
flips the `Doc Aux` flag - neither does the other's write. A tool is not properly
in the system until it has both a row and a TD, which is why the tool that
manages tools needs both halves.

## Shared code is copied, not imported

`registry.py` — the JSON register format — is identical in all four tools that
use it. It is **copied into each skill folder rather than imported from one
place**, because a skill has to be self-contained: the installer vendors a single
skill folder, and a shared library sitting outside it would not come along.

That is the same trade as vendoring a tool into a project: one directory would be
cleaner, and it would not survive being installed. So the guard is a test rather
than a structure — the smoke test asserts every copy is byte-identical, because
an edit applied to three of four copies leaves one tool quietly behaving
differently, and nothing else would say so.

## What the skills cover (and this document doesn't repeat)

`tsp-manager/SKILL.md` is authoritative for the schema of all four collections, the controlled vocabularies and their `Days` values, ID assignment rules, the register/retire/review procedures, and the create, refresh and audit commands.

This document covers the rest: why the register exists, its conventions, the two controls, and version history.

## Naming conventions

- **The register ID *is* the tool's number.** They are one identifier. If tools also get folders, name them `TSP.<id> <Name>/` so the folder and the row cannot diverge.
- **IDs are permanent.** Never reused, renumbered or reclaimed. Gaps are retired tools; a new tool takes `max(id) + 1`. Identifiers leak out into folder names, cross-references and years of notes — reusing one silently rebinds every one of them, and nothing errors.
- **Status and Relevancy are separate axes.** Status is lifecycle; Relevancy is how much the tool actually gets used. A tool can be fully implemented and touched twice a year. Collapsing them produces a register full of "implemented" tools nobody has opened in years.
- **Naming a skill in the `Skill` column is the expectation that it exists.** There is no separate "should be automated" flag: a skill named but not installed is a broken reference; a skill installed but named nowhere is automation nobody decided to keep. `audit_tsp.py` reports both.
- **The schema is yours to adapt.** The shipped columns reflect one estate. `Primary Area` may want to be team, service or value stream; you may not need `Relevancy` at all. Change it in `create_tsp.py` before creating the register, not after.

## TSP types

| Type | Meaning |
|---|---|
| `Tool` | Something used to get work done - a register, a script, a configured application |
| `Manual` | A playbook describing a whole system, rather than a single tool |
| `Work Instruction` | A defined procedure with steps - a routine, a checklist, a process someone follows |

Most estates are overwhelmingly `Tool`. The other two matter because they stop the
register becoming software-only: a morning routine and a documented handover process
are things you depend on and would have to rebuild, which is the test.

Status runs `Planned` -> `In Progress` -> `Implemented` -> `Obsolete`. Relevancy is
the separate axis recording how much the tool is actually used, from `Critical` down
to `Not in the last years`. **The two together are what the annual review acts on** -
status alone cannot tell you whether something is worth keeping.

## Relationship to other tools

**Every other tool** is a row in this register — including the [WBS](../TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) and [RAID](../TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md) registers, and this tool itself. Building a tool is not finished until its row exists.

**Governance documents** — the `Doc Aux` flag records whether a tool has one. Whatever authors the document owns the document; this register owns the row. Neither does the other's write.

**Nothing syncs automatically.** Rows change because someone changed them. `audit_tsp.py` is the compensating control: it compares the register against what is actually on disk and reports the drift in both directions.

## Maintenance

### The two controls

The register exists to be *worked*, not just held. Two controls do that:

1. **Periodic — planned controls.** Work the control activities whose next-due date has passed. Record what you did, and recompute the next due date from the frequency's `Days` value.

2. **Annual — the tool review.** Walk the register and ask, per tool: is it still used? If so, do I want to improve it? Batch improvements into a project rather than doing them inline, or the review becomes an unbounded refactor and you stop running it.

   **Stamp the review date on every row you touch, whatever the answer.** An unstamped row is indistinguishable from one never looked at — which is exactly how a review cadence dies unnoticed.

If the next-due dates are calculated, make sure something actually calculates them. A frequency column with a `Days` value *looks* like a working mechanism; confirm it is one, or every date will have been typed by hand and the whole schedule will drift.

### Routine

1. **Register new tools** as they are built - a tool is not finished until its row exists.
2. **Regenerate the dashboard** after a batch of edits. Its subtitle carries the
   generation date, so staleness is at least visible.
3. **Log structural changes** in the Change Log sheet: created, retired, superseded,
   governance document rewritten.
4. **Run the audit** before the annual review, and whenever folders have been
   reorganised. It reports drift in both directions.
5. **Before a schema change or bulk rewrite** - copy the register to `PreviousV/` first.

## Open items

| Item | Detail |
|---|---|
| Folder reconciliation is convention-bound | `audit_tsp.py` matches folders named `<prefix>.<number> <name>`. Estates using a different scheme get no value from that check, though the other reports are layout-independent |
| `Next Due` is not computed | The `Days` value exists but nothing applies it; dates are entered manually. Automating it would make the periodic control self-sustaining |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.5 | 2026-09-01 | Body caught up with the register format: the Components table still said `TSP Register.xlsx` and "Five sheets", two sections above the entry explaining the Lookups sheet had become a dict. `tsp-manager`'s SKILL.md carried a find-replace artefact - "Edit the workbook with `the register` (`data_only=True` ...)", a line naming a library that had been substituted out of it - and now points at `tsp.py` for the operations with rules attached. Version numbering repaired: the two 2026-09-01 entries had reused numbers already spent on 2026-08-31, leaving the table with two v1.1s and two v1.2s; they are now v1.3 and v1.4 |
| v1.4 | 2026-09-01 | Gained a second skill, `td-author`, which owns the tool definition documents while `tsp-manager` owns the register row. The catalogue already published the TD template and the reasoning behind it, but nothing applied either - the boundary between a TD and a SKILL.md, and where history goes inside a TD, were stated as method and enforced nowhere. Skill discovery also learned the catalogue layout: skills here sit beside their tool rather than in a skills directory, so the reconciliation had been finding nothing and reporting clean |
| v1.3 | 2026-09-01 | **The register is JSON.** Every write went through a script anyway, and a spreadsheet cost a subprocess to read, a dependency to install, and a file lock whenever the application or a sync client held it. The dropdowns a spreadsheet gave back are enforced more strictly by the commands - argparse refuses an invalid value where a dropdown only warns and paste bypasses entirely. The Lookups sheet - five stacked blocks separated by blank rows, a workaround for spreadsheets having no nested structure - is now an ordinary dict, which is what makes the new check that Next Due equals Last Done plus the Frequency's Days possible at all. The tool now has **no runtime dependencies at all** |

Earlier entries are not kept here. This repository is version-controlled, so the full history of this document is in its git log; a copy of the system kept outside version control should snapshot to `PreviousV/` instead, per `method/05-versioning-discipline.md`.
