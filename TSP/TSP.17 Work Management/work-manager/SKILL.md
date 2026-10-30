---
name: work-manager
description: Manages a project's work items (TSP.17 Work Management) - the Execution folder where each piece of work keeps its documents, and the stages a piece of work goes through (discovery, specification, plan, implement), scaled to its size. Starts a work item from its WBS row (its folder, and the documents its size calls for, from templates), files what was received or delivered, says what is next on a work item and what that stage asks for, and names and files support documents by the project's conventions. Use whenever someone starts work on a WBS row or a piece of work ("start work on WBS 12", "I'm picking up the login form"), asks where a document goes or what to call it, wants to file an email, an attachment or an external spec, asks what's next on a work item, how much discovery or specification it needs, or what a specification or plan should contain. Not for the WBS row itself (wbs-manager), risks and decisions (raid-manager), or status (the team board).
---

# Work Manager (TSP.17)

Every piece of work a project commits to keeps its own trail: a folder for it, its documents, what came in and what went out. This skill keeps that trail in the same shape for everyone, and says what a piece of work usually needs at each stage, scaled to its size, so nobody is left guessing and nobody writes documents nobody reads.

**Guidelines, not gates.** `references/sizes.md` says which stages each size of work needs; `references/stages/` holds one guideline per stage: what to expect, a few prompts, and the question that says it is done enough. Propose; never block. A project that wants more of a stage tightens that stage's file in its copy.

**A stage holds as many documents as the work needs.** Research that takes three documents gets three. A size says which stages, never how many documents.

## Requirements

Python 3, standard library only. `<skills>` is the folder this skill is installed in. The WBS is read, never written: the row's title and type name the folder and the documents.

## Files

| File | Role |
|---|---|
| `scripts/work.py` | `start`, `add`, `file`, `next`, `where` |
| `references/sizes.md` | Which stages each size of work needs |
| `references/stages/` | One guideline per stage: discovery, specification, plan, implement. The files a project adapts |
| `templates/` | One per document type |
| `scripts/smoke_test.py` | Checks the commands on a scratch project |

## Start a work item

1. **Find the row** in the WBS by its ID, or by its title if the person names the work.
2. **Propose a size**, from the row: its estimate, its description, whether it has children, how much is still unknown. Say why in one line (*"medium: a clear problem, two unknowns about the identity provider"*). **The person decides.**
3. Run it:

```
python <skills>/work-manager/scripts/work.py start "<project>" --id 12 --size medium
```

It creates the documents the size calls for, from the templates, header filled: in the row's own folder (`WP.<ID> <Title>/`, created if there is none), or, for a Story or a Task, in its parent's folder while that has one. It never overwrites a document. Then say which stage comes next and what it asks for, from the guidelines.

**Work turns out bigger.** Start it again at the larger size: the missing documents are added, nothing is lost.

## Along the way

- **Another document for a stage:** `work.py add "<project>" --id 12 --stage discovery --subject "Vendor survey"` adds one from the stage's template, named by its subject. With `--subfolder` the stage keeps its documents in a subfolder of its own (`Discovery/`); once it has one, its next documents go there.
- **What's next:** `work.py next "<project>" --id 12` lists the documents by stage, takes one still identical to its template as not started, counts a stage as begun once any of its documents is written, and prints the next stage with its guideline. Read it out in your own words; offer to draft that stage's document with the person, from what is already known (the row, the inputs, the earlier documents).
- **Filing:** `work.py file "<project>" --id 12 "<file>"` copies a received file into `Inputs/`; `--deliverable` into `Deliverables/`, frozen as sent. Say in a line, in Notes, how an input was used.
- **Drafting a stage's document:** follow its prompts in the guidelines; ask for what only the person knows; keep it as short as the work allows. The specification's acceptance criteria also go on the WBS row: offer it, through whoever keeps the WBS.
- **Closing:** before the row closes, each acceptance criterion gets a verdict in Notes. The closure note on the WBS row is the product manager's.

## The conventions

Support material for a piece of work always lives in the project's Execution folder, organised **by piece of work, not by document type**: people read later to find out what happened with one piece of work, and a `Plan/` or `Discovery/` folder would scatter that story.

- **One folder per Deliverable or Feature:** `WP.<ID> <Title>`, keyed off the WBS row's stable `ID`, never its `Code` (renumbered as the WBS evolves).
- **Flat until it isn't.** A Story's or a Task's documents are loose files in its parent's folder, prefixed `WP<ID>`; once it has about three documents of its own, it gets a folder of its own (`start --own-folder`). A row whose parent has no folder gets its own from the start.
- **The document type is the file name's suffix:** `WP<ID> <Title> - <Type>.md`. A stage's further documents add their subject: `WP<ID> <Title> - <Type> - <Subject>.md`. A stage with many may keep them in a subfolder named for it (`Discovery/`), flat until it isn't.

| Type | What to expect |
|---|---|
| Discovery | What was found: the current state, the problem, the evidence |
| Assessment | Options weighed against criteria, a recommendation, and the agreed outcome |
| Specification | What will be built: requirements, acceptance criteria, design |
| Plan | Steps, sequence, sizing |
| Notes | Work and decisions as they happened, dated |
| Input | External material that informed the work, with a line saying how it was used |

- **`Inputs/`**: material received from outside, kept as received. **`Deliverables/`**: what was handed over, frozen as sent. Created when there is something to put in them.
- **A header names the row, the date and the size, never the status:** `**Feature:** ID 12 · **Written:** 2026-10-29 · **Size:** medium`. The status lives in the WBS; a status copied into a document goes stale. The WBS skill finds a row's specification by the `ID <n>` in its first lines.
- **A replaced document goes to a `PreviousV/` beside it,** never deleted. **Existing folders are not retrofitted.**
- **A project's own layout** is declared once, in the WBS register's `meta.execution` (`folder`, relative to the register's folder; `inputs`; `deliverables`), and read here. Without it, the Execution folder is the one beside the planning folder, else the one the artifact register says this tool governs (*Managed By*), else one named Execution anywhere in the project.

## Never

- Block work for a missing document: say what the guideline expects, and leave the call to the person.
- Write the WBS or the RAID: offer the change, through whoever keeps them (a change request, where the team has one).
- Overwrite a document, or move one out of its work item's folder.

## Relationship to other skills

- **`wbs-manager`**: the rows this skill reads; `refined` checks a row has a specification; `meta.execution` declares the folder.
- **`change-request`**: where a team member proposes a change to the WBS or the RAID that a work item turned up.
- **`onboarding-guide`**: *How a piece of work gets done* shows the stages and the sizes from this skill's guidelines.
- **`status-board-manager`**: the status of a work item's tasks; this skill keeps its documents.
