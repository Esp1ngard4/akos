# Tool registry

<!-- GENERATED FILE - do not edit.
     Source of truth: registry/TSP Register.json
     Regenerate with: python registry/build_registry.py -->

What this repository publishes, and how ready each one is.

Every tool below is a folder under [`TSP/`](../TSP) containing a definition
document, and — where one makes sense — the skill or skills that operate it.
A tool with no skill is still a tool, and a tool may have more than one; the
skill is an attribute, not the unit.

Install one with [`install.py`](../install.py), which records where the copy
came from so it stays reconcilable with upstream:

```bash
python install.py add <skill> --into <your-project>
```

| ID | Tool | Status | Skill | Definition doc |
|---|---|---|---|---|
| TSP.1 | **WBS Register** | Implemented | `wbs-manager` | [TD.1](../TSP/TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) |
| TSP.2 | **RAID Register** | Implemented | `raid-manager` | [TD.2](../TSP/TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md) |
| TSP.3 | **TSP Register** | Implemented | `tsp-manager`, `td-author` | [TD.3](../TSP/TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md) |
| TSP.4 | **Tool Installer** | Implemented | _none_ | [TD.4](../TSP/TSP.4%20Tool%20Installer/TD.4%20-%20Tool%20Installer.md) |
| TSP.5 | **Artifact Register** | Implemented | `artifact-register` | [TD.5](../TSP/TSP.5%20Artifact%20Register/TD.5%20-%20Artifact%20Register.md) |
| TSP.6 | **Content System** | Implemented | `content-idea-capture`, `content-plan-author`, `content-post-writer`, `content-review`, `content-strategy-author` | [TD.6](../TSP/TSP.6%20Content%20System/TD.6%20-%20Content%20System.md) |
| TSP.7 | **Notebook Manager** | In Progress | `notebook-capture` | [TD.7](../TSP/TSP.7%20Notebook%20Manager/TD.7%20-%20Notebook%20Manager.md) |
| TSP.8 | **Sprint Ceremonies** | In Progress | `sprint-facilitator`, `sprint-planning-precheck` | [TD.8](../TSP/TSP.8%20Sprint%20Ceremonies/TD.8%20-%20Sprint%20Ceremonies.md) |
| TSP.9 | **Daily Loop** | In Progress | `daily-loop-facilitator` | [TD.9](../TSP/TSP.9%20Daily%20Loop/TD.9%20-%20Daily%20Loop.md) |
| TSP.10 | **Reporting** | In Progress | `reporting` | [TD.10](../TSP/TSP.10%20Reporting/TD.10%20-%20Reporting.md) |
| TSP.11 | **Weekly Review** | In Progress | `weekly-review-facilitator` | [TD.11](../TSP/TSP.11%20Weekly%20Review/TD.11%20-%20Weekly%20Review.md) |
| TSP.12 | **Action Tracker** | In Progress | `action-tracker-manager` | [TD.12](../TSP/TSP.12%20Action%20Tracker/TD.12%20-%20Action%20Tracker.md) |
| TSP.13 | **Stakeholder Register** | In Progress | `stakeholder-manager` | [TD.13](../TSP/TSP.13%20Stakeholder%20Register/TD.13%20-%20Stakeholder%20Register.md) |
| TSP.14 | **Project Definition** | In Progress | `project-definition-manager` | [TD.14](../TSP/TSP.14%20Project%20Definition/TD.14%20-%20Project%20Definition.md) |
| TSP.15 | **Team Status Board** | In Progress | `status-board-manager` | [TD.15](../TSP/TSP.15%20Team%20Status%20Board/TD.15%20-%20Team%20Status%20Board.md) |
| TSP.16 | **Onboarding** | In Progress | `onboarding-guide` | [TD.16](../TSP/TSP.16%20Onboarding/TD.16%20-%20Onboarding.md) |

## What each is for

**TSP.1 WBS Register** — Work breakdown / backlog register per project: decomposition, effort, acceptance criteria, sprint allocation, with a generated dashboard.

**TSP.2 RAID Register** — Risks, Actions, Issues, Decisions and Ideas per project, with a probability x severity heat map and a generated dashboard.

**TSP.3 TSP Register** — The inventory of tools, systems and procedures, plus the recurring controls that keep them alive. The spine of the method - this register is an instance of it. Automated by two skills: one owns the register row, the other owns the tool definition documents.

**TSP.4 Tool Installer** — Vendors a tool from this catalogue into a project, records where the copy came from, and keeps it reconcilable with upstream: drift detection and three-way updates.

**TSP.5 Artifact Register** — Inventory of the artifacts belonging to a scope - documents, folders, tools and physical items - recording what each is, where it lives digitally and physically, what contains it, and which tool governs its contents. The register assigns an ID that is written onto the artifact itself, so its claims about the filesystem can be checked.

**TSP.6 Content System** — Turns thinking into finished, publish-ready pieces through interview rather than one-shot generation. Holds a position per scope, plans that name the goal they serve and hold a rate or an arc of pieces, an inbox for sparks, an interview-led writer, and a review that reports what was published against the rate and checks content against the WBS. Committed pieces run on the WBS Register (TSP.1). It is deliberately not a publisher: it stops at the finished piece and transmits to no platform.

**TSP.7 Notebook Manager** — Plain-Markdown notebooks the agent keeps: a diary, notebooks scoped to a project, an area of focus or an area of interest, and meeting notes, with an index per notebook. Raw entries worth more than a note can be crystallized into static HTML posts that link back to the entry they came from. No app, no search index, no database - files only.

**TSP.8 Sprint Ceremonies** — The four sprint ceremonies - backlog grooming, the sprint close-out, the retrospective and sprint planning - run on the WBS, RAID and TSP registers alone, with one Markdown record per sprint written by sprint_record.py. Sprint state lives on WBS rows: staged by Horizon, committed by Sprint Planned, closed with a closure note. A task tracker and a calendar are described as adaptations, not configured.

**TSP.9 Daily Loop** — The morning plan and the evening stand-up as one tool, sharing one Markdown record per day. The evening reviews the day from git, the WBS and the day's notes, raises a sprint ceremony that is due, chooses one to three frogs for tomorrow and closes the record; the morning confirms the frogs and opens the next. A calendar, a task tracker and inboxes are described as adaptations, not shipped.

**TSP.10 Reporting** — The project status report and the sprint update, each a JSON record and an HTML view generated from the WBS, RAID and the sprint records. The status report proposes the Essential 4 (On Time, On Scope, On Quality, Resources) with their evidence for the owner to confirm or override with a reason; the sprint update sets the last sprint's outcome beside the new sprint's commitments across projects, with the sprint's cards as a board on its own tab. Both open with an executive summary drafted in plain language and confirmed by the owner.

**TSP.11 Weekly Review** — The weekly level between the daily loop and the sprint, with its own Markdown record per review. It reads the week's day records, goes over the work beyond the sprint in the registers (rows falling due outside it, RAID entries past their review date), checks mid-sprint whether the sprint is on track and scans the open risks, places the week ahead, and routes what it finds rather than acting on it. A task tracker, a calendar, inboxes and a goal tracker are described as adaptations, not shipped.

**TSP.12 Action Tracker** — A team's shared list of the small actions agreed in a piece of work's sessions, one Markdown file per piece of work, below the deliverables the WBS tracks and the governed items RAID holds. Every action whoever owes it, the owner named rather than assumed; filed in the support folder of the WBS row or RAID item it serves and indexed nowhere. No scripts. A personal task manager, a ticketing tool and meeting notes are described as adaptations, not shipped.

**TSP.13 Stakeholder Register** — For one project, who has a stake in it, where each stands and what flows to them: groups, stakeholders with power, interest and current against desired engagement, and a communications plan with each communication's audience, cadence, channel, share level and last sending. Resolves an audience to people and addresses at the moment of sending, says what is due or overdue, and generates a dashboard. Contacts per project in a CSV kept out of git, which the tool checks. Sends nothing.

**TSP.14 Project Definition** — The documents that define a project: above all the Project Brief every project has (why it exists, its outcome and done-when, Stop if, what it serves, and for a full brief its measures, appetite, scope, approach and who it is for), and further definition documents when a project needs one. Writes, grows, keeps current and revisits the brief; brief.py is the one reader of its format, used by the status report, the charter and the weekly review.

**TSP.15 Team Status Board** — Where a team updates the status of its own work, one Excel board per sprint beside the WBS, edited by the team or through Copilot in Excel, and its consolidation into the WBS: set up at planning, updated when a commitment changes, consolidated at the weekly review and the close-out through proposals the product manager confirms. A step in those ceremonies only where it is installed; the WBS keeps one writer.

**TSP.16 Onboarding** — How people come to work in a project run on these tools: the team guide and the executive overview generated from the project's own files, every step saying who acts, people and agents shown as one loop, fonts embedded; and the onboard me conversation that walks a newcomer through their first week.

## Status meanings

| Status | Meaning |
|---|---|
| `Implemented` | Ready to adopt. Works from a clean checkout. |
| `In Progress` | Usable but still changing; expect rough edges. |
| `Planned` | Listed so the number is reserved; not yet built. |
| `Obsolete` | Superseded. Kept for reference, do not adopt. |

---

Generated from `registry/TSP Register.json` on 2026-10-29.
