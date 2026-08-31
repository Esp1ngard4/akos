# Tool registry

<!-- GENERATED FILE - do not edit.
     Source of truth: registry/TSP Register.xlsx
     Regenerate after any change to the register. -->

What this repository publishes, and how ready each one is.

Every tool below is a folder under [`TSP/`](../TSP) containing a definition
document, and — where one makes sense — the skill that operates it. A tool with
no skill is still a tool; the skill is an attribute, not the unit.

Install one with [`install.py`](../install.py), which records where the copy came
from so it stays reconcilable with upstream:

```bash
python install.py add <skill> --into <your-project>
```

| ID | Tool | Status | Skill | Definition doc |
|---|---|---|---|---|
| TSP.1 | **WBS Register** | Implemented | `wbs-manager` | [TD.1](../TSP/TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) |
| TSP.2 | **RAID Register** | Implemented | `raid-dashboard` | [TD.2](../TSP/TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md) |
| TSP.3 | **TSP Register** | Implemented | `tsp-manager` | [TD.3](../TSP/TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md) |
| TSP.4 | **Tool Installer** | Implemented | _none_ | [TD.4](../TSP/TSP.4%20Tool%20Installer/TD.4%20-%20Tool%20Installer.md) |

## What each is for

**TSP.1 WBS Register** — Work breakdown / backlog register per project: decomposition, effort, acceptance criteria, sprint allocation, with a generated dashboard.

**TSP.2 RAID Register** — Risks, Actions, Issues, Decisions and Ideas per project, with a probability x severity heat map and a generated dashboard.

**TSP.3 TSP Register** — The inventory of tools, systems and procedures, plus the recurring controls that keep them alive. The spine of the method - this register is an instance of it.

**TSP.4 Tool Installer** — Vendors a tool from this catalogue into a project, records where the copy came from, and keeps it reconcilable with upstream: drift detection and three-way updates.

## Status meanings

| Status | Meaning |
|---|---|
| `Implemented` | Ready to adopt. Works from a clean checkout. |
| `In Progress` | Usable but still changing; expect rough edges. |
| `Planned` | Listed so the number is reserved; not yet built. |
| `Obsolete` | Superseded. Kept for reference, do not adopt. |

---

Generated from `registry/TSP Register.xlsx` on 2026-08-31.
