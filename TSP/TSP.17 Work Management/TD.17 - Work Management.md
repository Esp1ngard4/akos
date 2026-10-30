# TD.17 — Work Management

## Purpose

How a piece of work is carried out, once a project has committed to it: where its documents live, what they are called, and what each stage of the work usually needs. It answers the question a team member has on picking up a WBS row — *what do I write, where, and how much?* — with guidelines scaled to the work's size, so a small fix is not made to carry a specification and a new capability is not built without one.

It is a team tool. The WBS says what the work is and where it stands; this tool keeps the work's own trail, and every team member uses it.

## Status: In Progress

| | |
|---|---|
| The design | The Execution folder's conventions, moved here from the WBS skill, which only the product manager loads; four stages as guidelines, scaled small, medium and large |
| As shipped here | **Not yet used by a team on real work.** Exercised by its smoke test on a scratch project |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.17 Work Management/` | What the tool is for and why; how to adapt it |
| `work-manager` | `work-manager/SKILL.md`, `scripts/work.py` | Starting a work item, filing, what's next, the conventions |
| The guidelines | `work-manager/references/sizes.md`, `references/stages/` | Which stages each size needs; one guideline per stage. **The files a project adapts** |
| The templates | `work-manager/templates/` | One per document type |

## What the skill covers (and this document doesn't repeat)

`work-manager/SKILL.md` holds the commands, the conventions (folder, names, header, `Inputs/`, `Deliverables/`), how the agent proposes a size, and what it never does. This document covers why the tool is shaped as it is, and how to adapt it.

## Design decisions

**Guidelines, not gates.** A rule that makes everyone write a specification gets specifications nobody reads; no guidance at all gets work built from a chat message. The guidelines say what usually helps and how much of it, and each stage ends on a question (*could someone else build this from the spec?*) rather than a checklist. The agent proposes; the person decides; nothing is blocked.

**Scaled by size, decided by a person.** Small, medium and large say how much of the four stages a piece of work needs. Size is a judgement, so the agent proposes one with its reason and the person decides. Work that turns out bigger moves up a size and keeps everything done so far.

**A stage, as many documents as it needs.** Stages are separate kinds of work, each with its own guideline and its own documents. A size says which stages a piece of work needs, never how many documents a stage may hold: large research may take a vendor survey, interviews and a look at the current system, each a document named by its subject, kept in a stage subfolder once there are many. A cap would push the work into one long document nobody reads.

**Taught in the onboarding, not left in the folder.** A newcomer meets the conventions once, in the onboarding guide's *How work gets done*, and asks the agent after that. A page left in the Execution folder would be a second copy, read once and never kept current.

**One owner for the conventions.** They lived in the WBS skill, but the WBS does not own the Execution folder, and the team, who work in it, did not load that skill. Here they have one owner, used by the people who apply them; the WBS keeps only what it reads.

**Grown by adapting the skill.** A project wanting more of a stage tightens that stage's file in its copy, the installer records it as the project's own (`accept -m`), and `update` still brings the catalogue's changes. No configuration file.

**Never writes the registers.** It reads the WBS row; changes to the WBS or the RAID that a work item turns up go through whoever keeps them.

## Naming conventions

- **Folders:** `WP.<ID> <Title>` in the Execution folder, one per Deliverable or Feature; a colon in a title becomes a dash. A Story's or a Task's documents sit flat in its parent's folder until it has about three of its own (`start --own-folder`).
- **Documents:** `WP<ID> <Title> - <Type>.md`, further ones in a stage `WP<ID> <Title> - <Type> - <Subject>.md`, a stage with many in its own subfolder; the header `**<Type>:** ID <n> · **Written:** <date> · **Size:** <size>`.
- **Sizes:** small, medium, large.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.**

### More structure, or less

**Where it plugs in:** `references/stages/<stage>.md`, and `references/sizes.md`.

**What it takes over:** a team that wants a stage to hold more (a design section, a security review, kinds of research) adds it to that stage's file; one that wants less removes it. Each stage grows on its own.

**What to watch for:** keep each stage a few prompts and a question. A long checklist turns a guideline into a form.

### Documents in Word

**Where it plugs in:** the templates and `doc_name` in `work.py`.

**What it takes over:** a team writing in Word keeps `.docx` templates; the names and the folder stay the same.

## How it is tested

`work-manager/scripts/smoke_test.py` builds a scratch project and checks: *start* makes the folder and the size's documents, header filled, and never overwrites; *add* gives a stage further documents by subject, in a stage subfolder too; *next* takes an untouched document as not started and follows the size; moving up a size adds the missing documents; *file* copies into `Inputs/` or `Deliverables/`. `tests/smoke_test.py` runs it and has `init` install it at the project root.

What is **not** tested is whether the guidelines help: that is the first team's to say.

## Relationship to other tools

- **TSP.1 WBS Register:** the rows read here, and `meta.execution`, the project's own layout.
- **TSP.18 Change Requests:** where a change a work item turned up is proposed.
- **TSP.16 Onboarding:** the guide's *How work gets done* shows the stages and the sizes.
- **TSP.15 Team Status Board:** the status of a work item's tasks.
- **TSP.4 Tool Installer:** `init` installs it at the project root, with the team's tools.

## Maintenance

**When a stage keeps being skipped, or keeps being too heavy:** adapt the guidelines in the project's copy, and say why (`accept -m`).

## Open items

| Item | Detail |
|---|---|
| Unused by a team | See *Status* |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.1 | 2026-10-29 | **The Execution folder found by what the project records.** What the WBS declares; else the default convention; else the folder the artifact register says this tool governs (*Managed By*); else one named Execution anywhere in the project. |
| v1.0 | 2026-10-29 | Published as TSP.17: the Execution folder's conventions, moved from the WBS skill; four stages, each its own guideline and as many documents as the work needs, scaled small, medium and large; *start*, *add*, *file*, *next*, *where*. A newcomer learns the conventions from the onboarding guide, not from a page in the folder. Raised trying the starter pack as a team member. |
