# Tool registry

<!-- GENERATED FILE - do not edit.
     Source of truth: registry/TSP Register.xlsx
     Regenerate after any change to the register. -->

What this repository publishes, and how ready each one is.

Every tool below is a folder under [`TSP/`](../TSP) containing a definition
document and the skill that operates it. Copy the skill folder into your own
`.github/skills/`, `.claude/skills/` or `.agents/skills/` to use it.

| ID | Tool | Status | Skill | Definition doc |
|---|---|---|---|---|
| TSP.1 | **WBS Register** | Implemented | `wbs-manager` | [TD.1](../TSP/TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) |
| TSP.2 | **RAID Register** | Implemented | `raid-dashboard` | [TD.2](../TSP/TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md) |
| TSP.3 | **TSP Register** | Implemented | `tsp-manager` | [TD.3](../TSP/TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md) |

## What each is for

**TSP.1 WBS Register** — Work breakdown / backlog register per project: decomposition, effort, acceptance criteria, sprint allocation, with a generated dashboard.

**TSP.2 RAID Register** — Risks, Actions, Issues, Decisions and Ideas per project, with a probability x severity heat map and a generated dashboard.

**TSP.3 TSP Register** — The inventory of tools, systems and procedures, plus the recurring controls that keep them alive. The spine of the method - this register is an instance of it.

## Status meanings

| Status | Meaning |
|---|---|
| `Implemented` | Ready to adopt. Works from a clean checkout. |
| `In Progress` | Usable but still changing; expect rough edges. |
| `Planned` | Listed so the number is reserved; not yet built. |
| `Obsolete` | Superseded. Kept for reference, do not adopt. |

---

Generated from `registry/TSP Register.xlsx` on 2026-08-31.
