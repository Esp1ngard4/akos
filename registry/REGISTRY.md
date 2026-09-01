# Tool registry

<!-- GENERATED FILE - do not edit.
     Source of truth: registry/TSP Register.json
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
| TSP.1 | **None** | Implemented | `wbs-manager` | [TD.1](../TSP/TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) |
| TSP.2 | **None** | Implemented | `raid-dashboard` | [TD.2](../TSP/TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md) |
| TSP.3 | **None** | Implemented | `tsp-manager` | [TD.3](../TSP/TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md) |
| TSP.4 | **None** | Implemented | _none_ | [TD.4](../TSP/TSP.4%20Tool%20Installer/TD.4%20-%20Tool%20Installer.md) |
| TSP.5 | **None** | Implemented | `artifact-register` | [TD.5](../TSP/TSP.5%20Artifact%20Register/TD.5%20-%20Artifact%20Register.md) |

## What each is for

**TSP.1 None** — Work breakdown / backlog register per project: decomposition, effort, acceptance criteria, sprint allocation, with a generated dashboard.

**TSP.2 None** — Risks, Actions, Issues, Decisions and Ideas per project, with a probability x severity heat map and a generated dashboard.

**TSP.3 None** — The inventory of tools, systems and procedures, plus the recurring controls that keep them alive. The spine of the method - this register is an instance of it.

**TSP.4 None** — Vendors a tool from this catalogue into a project, records where the copy came from, and keeps it reconcilable with upstream: drift detection and three-way updates.

**TSP.5 None** — Inventory of the artifacts belonging to a scope - documents, folders, tools and physical items - recording what each is, where it lives digitally and physically, what contains it, and which tool governs its contents. The register assigns an ID that is written onto the artifact itself, so its claims about the filesystem can be checked.

## Status meanings

| Status | Meaning |
|---|---|
| `Implemented` | Ready to adopt. Works from a clean checkout. |
| `In Progress` | Usable but still changing; expect rough edges. |
| `Planned` | Listed so the number is reserved; not yet built. |
| `Obsolete` | Superseded. Kept for reference, do not adopt. |

---

Generated from `registry/TSP Register.json` on 2026-09-01.
