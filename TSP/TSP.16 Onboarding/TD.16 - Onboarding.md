# TD.16 — Onboarding

## Purpose

How someone comes to work in a project run on these tools. The tool generates the project's guide from its own files, in two editions: the team guide, for the product team, and the executive overview, for people outside it. It then walks a newcomer through their first week in conversation. It answers what no register does: how does this project work, and what do I do in it?

It is also where the way of working is made visible. A project run on these tools is AI-first: people and agents do the work together; agents also keep the records, propose and draft; people decide, confirm and own the outcome. The guide shows that loop at every step, so a newcomer learns to work with the agents from their first day, and an outsider sees why the team can be small and still current.

## Status: In Progress

| | |
|---|---|
| The design | Written for a product team adopting these tools in a running project, and generated there on its first day of use |
| As shipped here | **Not yet read by a newcomer.** Exercised by its smoke test on a scratch project, with and without a team board |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.16 Onboarding/` | What the tool is for and why; how to adapt it |
| `onboarding-guide` | `onboarding-guide/SKILL.md` and `scripts/` | Generating, reading through, posting, regenerating, and the *onboard me* conversation; `onboard.py` gathers, `render.py` with `guide.css` and `guide.js` draws |
| Fonts | `onboarding-guide/assets/fonts/` | Three open-licensed typefaces, embedded in every page, with their licences |
| `Guide.json` | The project's onboarding folder | The record a guide is drawn from |
| `Guide.html`, `Guide (executive).html` | Beside it | The two editions. Generated, never edited; overwritten when regenerated |

Standard library only, no dependencies. It reads the brief (TSP.14) and how team boards are named (TSP.15) where they are installed.

## What the skill covers (and this document doesn't repeat)

`onboarding-guide/SKILL.md` holds what each edition contains, the commands, when to regenerate, where to post it, the *onboard me* conversation, and where the role paths live. This document covers why the tool is shaped as it is, how to adapt it, and its history.

## Design decisions

**A tool of its own, not a report.** A report answers how a project is going, each sprint, for its stakeholders. The guide answers how the project works, changes when the team or its tools change, and is for newcomers and outsiders. It carries a procedure a report does not: reading it through, posting it, the conversation. So it has a folder of its own beside the reports, and one current copy rather than a dated series.

**Only what changes slowly.** The guide holds what changes when a tool, the brief or the team changes, and nothing that changes each sprint: the rhythm is the sprint's pattern, not this sprint's dates; the board is how boards are named, not this sprint's file. What is current it points to: this sprint's board, the sprint record, the latest status report. A guide carrying the running sprint is wrong two weeks after it is posted, and a guide found wrong once is not trusted again.

**Generated from the project, never written.** Everything comes from the project as it is set up: the brief's statement and outcome, the tools in the project's lock, the folders the artifact register describes, the stakeholder register, the sprint calendar. What it teaches follows what is installed: a team on the board is told to update the board, a team without one to tell the agent; a ceremony not installed is not on the rhythm. A guide written by hand would describe the project as someone remembered it.

**People and agents, shown at every step.** Both do the work; what separates them is that a person decides and owns the outcome. The collaboration is the point of the way of working, so it is not a paragraph: every step of every path says who acts (*You*, *Agent does it with you*, *You decide, agent prepares*) and who you say it to; the rhythm marks people and agents in their own colours; the executive overview draws people and agents as one loop between the records and what the reader receives.

**How a piece of work gets done is its own section.** Committed work gets a folder in the Execution folder; an agent researches, specifies and plans there, a person reviews each stop and approves the plan before anything is built, and the agent then carries out the steps it can. This is where AI-first is most concrete, and a newcomer who misses it treats the agent as a chat window rather than a colleague with a method. The folder layout is the backlog's (TSP.1, *Support Material*), read from the project.

**Two editions, and the outside one holds nothing internal.** A team member needs the how; an outsider needs the principles, the rhythm and what they will receive. The executive overview carries no names, paths, commands or RAID content, so it can be passed on without a second look.

**Built not to overwhelm.** One screen first, with three doors; one idea per card; the four tools a team member uses before the product manager's, which are a line each; five steps per role; a glossary for the words. A guide that shows everything at once is not read.

**Made to feel worth reading.** It is a welcome, so it is designed like one: its own typefaces, a hero that states what the project is for, considered light and dark themes. The fonts are embedded so the page looks the same opened from a shared drive, offline or behind a network that blocks font services. It is a page, not a print: nothing in its layout is designed around paper.

**The page is the reference; the conversation is the onboarding.** *Onboard me* walks a newcomer through their path one step at a time, and offers to do the first one with them for real. A tool for an AI-first team onboards with an agent.

## Naming conventions

- **Files:** `Guide.json`, `Guide.html`, `Guide (executive).html`, in the project's onboarding folder: `Onboarding`, numbered by the artifact register where there is one.
- **Roles:** product manager, developer, validation and quality, by default.
- **Who acts:** *You* (amber), *Agent* (indigo).

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.**

### The team's own roles

**Where it plugs in:** `render.py`, `paths`.

**What it takes over:** a team with other roles (a designer, a data engineer, a business analyst) writes their five steps in its copy of the skill, each saying who acts and who you say it to.

**What to watch for:** keep five steps, in the order the person meets them; more is a manual, not a path.

### Another agent

**Where it plugs in:** the steps' *say this to* lines.

**What it takes over:** where the team works with a named assistant (Copilot, an in-house agent), the paths name it.

**What to watch for:** the split stays the same whatever the agent: it proposes and drafts, a person decides.

### Where the guide is posted

**Where it plugs in:** the skill's *Post it*.

**What it takes over:** the team's channel, wiki or intranet. A wiki that cannot hold an HTML file can link to it on a shared drive.

## How it is tested

`onboarding-guide/scripts/smoke_test.py` builds a scratch project and checks: the record finds the brief, the sprint, the board and the installed tools; the team guide carries every section, the board's file, three role paths each step saying who acts, and the fonts; the executive overview holds the principles and the collaboration loop and no file, path or command; without a board, the paths say to tell the agent. `tests/smoke_test.py` runs it and installs the skill into an empty project.

What is **not** tested is whether a newcomer understands it. That is the first person onboarded's to say.

## Relationship to other tools

- **TSP.14 Project Definition**: the brief, which the guide opens with.
- **TSP.15 Team Status Board**: whether the team updates a board, and where it is.
- **TSP.8 Sprint Ceremonies**, **TSP.11 Weekly Review**: the rhythm, and the sprint record the guide points to; the weekly review asks whether the guide needs regenerating.
- **TSP.13 Stakeholder Register**: who's who, and what an outsider receives.
- **TSP.1 WBS Register**: the work loop's folder layout, and where the Execution folder is (`meta.execution`).
- **TSP.5 Artifact Register**: what each folder holds, and the onboarding folder's number.
- **TSP.10 Reporting**: the status report the guide points to.
- **TSP.3 TSP Register**: row 16.

## Maintenance

**When someone joins:** *onboard me*, from the latest guide.

**When a tool, the brief, the team or the sprint's length changes:** regenerate, read it through, post it. A new sprint is not a reason.

**When the team's roles differ:** adapt the paths in the skill copy.

## Open items

| Item | Detail |
|---|---|
| Unread by a newcomer | See *Status*. The first person onboarded with it says what was missing |
| The catalogue's guide | The same page builder over the AKOS catalogue, published as a site, is still to be built |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.2 | 2026-10-29 | **Work Management found wherever it is installed:** the default places, then the lock files, which record where each skill is, then beside the skill. |
| v1.1 | 2026-10-29 | **The guide shows how much of the loop a piece of work needs.** Where Work Management (TSP.17) is installed, its size table is read from the project's own guidelines and shown under *How work gets done*; the developer's path starts a work item with it. |
| v1.0 | 2026-10-28 | Published as TSP.16: the team guide and the executive overview generated from a project's own files into an onboarding folder, every step saying who acts, people and agents drawn as one loop doing the work, how a piece of work gets done (discover, specify, plan and approve, do, close), nothing that changes each sprint, fonts embedded; the *onboard me* conversation. First built inside Reporting the same day, showing the running sprint, and moved out before it was published. |
