# TD.13 — Stakeholder Register

## Purpose

Who has a stake in a project, where each stands, and what flows to them. One register per project holds its groups, its stakeholders with their power, interest and engagement, and its communications plan: which update goes to whom, how often, through which channel, at what share level, and when it last happened. It answers what no other tool here can: who needs to know what about this work, and did they hear it?

It is an outflow of governance, not a publisher and not a CRM. It hands over the list of people and addresses at the moment of sending, and records that a communication went when the user says so. Judgment stays with the person: how engaged someone is, and how engaged they need to be, is the user's read, never the tool's guess.

## Status: In Progress

| | |
|---|---|
| The design | Comes from a personal setting, where it ran a house project's contractors, architect and family alongside projects with the owner as their only stakeholder |
| As shipped here | **Not yet used on real work.** Exercised by the smoke test on a scratch project, and by the example register. The close-out sends what is due, the weekly review names what is overdue, and the reporting tool reads audiences from it; all three exercised by the smoke test only |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.13 Stakeholder Register/` | What the register is for and why; how to adapt it |
| `stakeholder-manager` | `stakeholder-manager/SKILL.md` and `scripts/` | Every read and write of a register, the contacts file, audience resolution, due dates, the audit, the dashboard, and `stk_register.py`, the reader other tools import |
| Dashboard template | `stakeholder-manager/templates/dashboard.html` | The page `refresh_stk.py` fills |
| Example | `stakeholder-manager/examples/Stakeholders Atlas.json` | A made-up register: a sponsor, a client, a delivery team and a steering group |
| `Stakeholders <scope>.json` | `Confidential/Stakeholder Mgm` in your project's planning folder, numbered by its artifact register (the starter pack makes `12. Confidential/13. Stakeholder Mgm`) | **Source of truth** for that project: groups, stakeholders, communications, change log. Out of git with the whole Confidential folder |
| `Contacts <scope>.csv` | Beside the register | How to reach each stakeholder. **Outside git** |
| `Stakeholder Dashboard.html`, `Stakeholder Dashboard (no notes).html` | Beside the register | Generated views, with each row's notes and without them; never hand-edited, outside git |

Standard library only. Dependencies, all optional: `wbs-manager` (TSP.1) or an agile conventions file for the sprint calendar, and the content system (TSP.6) for public audiences.

## What the skill covers (and this document doesn't repeat)

`stakeholder-manager/SKILL.md` is the authoritative reference for the fields and vocabularies, every operation (set up, change, contacts, sending, due, check, refresh), the reader API and the ceremony hooks. This document covers why the tool is shaped as it is, its conventions, how to adapt it, its boundaries and its history.

## Design decisions

- **Two lists, joined by audience.** Who the people are, and what flows to them, are kept apart: every framework and tool that does this well does so. A communication names its audience by group or person; who that is gets resolved when it is sent.
- **Groups are memberships, not a category.** Communications go to groups, and a person belongs to several (the client lead is in the steering group and on the weekly update). A category allows one value. Membership is held on the stakeholder and nowhere else, so there is no second list to drift.
- **The gap drives the action.** Current against desired engagement, on PMBOK's five levels, is the part of stakeholder analysis that leads somewhere: a stakeholder below where they are needed wants one engagement action, and a gap without one is an audit finding. Power and interest place them on the grid and say how they are managed. The heavier salience model (power, legitimacy, urgency) is left out: it earns its cost only where a group's claim is contested.
- **Contacts per project, out of git.** Not everyone who works on a project can see every project: a contractor or a client given one project's folder needs its contacts and nothing else. A list per project travels with the folder and exposes only that project's people; one shared list would hand every contact to whoever got a copy. Duplication across projects is accepted, kept in step by offering to copy a row when a stakeholder is added and by `check --all`, which names any that disagree. The file is CSV so someone without the tool can edit it in a spreadsheet, and so it imports into an address book. Git is not its home because git keeps every version of other people's personal data for good, so the tool checks: `create_stk.py` prints the `.gitignore` line a repository needs, and `check` reports a contacts file git tracks or would take.
- **Evidence is one date.** Specialist stakeholder software is built around an interaction log; this tool keeps `Last Done` per communication, which is enough to say what is overdue. Conversations are recorded as meeting notes. A full log is worth its cost only when a project has more than a handful of external stakeholders.
- **It rides the ceremonies.** Communication tied to the work's rhythm gets done; a separate communications calendar does not. The close-out sends what is due per sprint and the weekly review names what is overdue.
- **What is learned about a person accumulates.** A stakeholder's notes are a dated log, newest first, the convention the WBS keeps for a row's comments: a note is read later for how understanding of someone changed, which an overwritten field loses. The change log records that a note was added and never its text, so a page built without notes leaves nothing behind.
- **A note is written to be read in a list.** What was learned in a sentence, what it means in one or two more, a title for what will be looked for, the detail in the meeting notes. A log that grows by paragraphs stops being read, and a note is read most when preparing to meet someone. What they said or did is recorded, not a judgement of them, and no contact detail, because the page with notes can still travel. Notes belong to stakeholders and communications; a group is an audience, and what is learned about it is learned about its members.
- **Active management, history on request.** A stakeholder who has gone `Inactive` is history, not someone to manage: the audit raises nothing about them beyond broken data, the grid and the counts leave them out, and the tables show them only when asked. Their rows stay, since nothing is deleted.
- **Two dashboards, because notes are the most personal part.** The page with notes is for you; the one without is the copy that can travel further. Choosing between them is a decision you make each time, not one the tool makes.
- **Solo is the default.** A project with no register has its owner as its one stakeholder and a status report per sprint as its one communication. Consumers read through `load_or_default`, so nothing breaks, and a register is created only when someone besides the owner needs to hear.
- **Found by shape, not by a path.** A register is a JSON file whose `meta.kind` is `stakeholder-register`. `--all` walks a root folder you name for that shape; there is no configured list of projects.
- **Confidential, and found through the artifact register.** A register says what each person's stake is and how engaged they are: material about people the team need not read. It sits in a Confidential folder of the planning folder, so access is set on that folder alone and the registers beside it stay open to the team. Given the planning folder, a tool finds it where the artifact register says first, matching folders by ID because names drift, then by name. The sprint calendar sits elsewhere in the planning folder, so it is searched upward from the register.
- **Communications and content meet at one point.** A communication is owed to named people with a stake in one project; content is written for a public audience against a strategy. Where a project's audience is the public, its communication points to a content plan and holds nothing else. The pointer runs one way, so the content system stays unaware of this register and portable without it.

## Naming conventions

- **IDs**: `G.n` groups, `S.n` stakeholders, `C.n` communications, assigned once within a register and never reused: a reused ID would silently rebind the audiences and contacts rows that name it. A stakeholder's `S.n` is also the key of its row in the contacts file.
- **Scope**: the register's `meta.scope` is the same string as the project's WBS `meta.scope`, so a ref reads the same in both.
- **Files**: `Stakeholders <scope>.json` and `Contacts <scope>.csv` in `<planning folder>/Confidential/Stakeholder Mgm`; `Stakeholder Dashboard.html` and `Stakeholder Dashboard (no notes).html` beside them.
- **Vocabularies**: engagement on PMBOK's five levels, share level `owner` or `external` as the reporting tool and RAID's `Sharable` use them, mode on PRINCE2's channel types. A register may override a vocabulary in `meta.settings.vocabularies`.
- **Content pointer**: `content: <strategy scope> › <plan name>`, as the content system names them.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.** The register is shipped on its own files alone, because each team keeps its people and its channels in its own way. **The tools are named here; the instructions for using them belong in your copy of the skill.** Edit it. The installer records the edit (`status --check`, `accept`) and merges upstream changes around it (`update`). See TD.4.

### A CRM or a shared address book

**Where it plugs in:** the contacts file, and operation *Send a communication*.

**What it takes over:** where a team already keeps contacts (a CRM, a company directory, a shared address book), the contacts CSV can hold only the `S.n` and a key into that system, and `audience` names the key instead of an address.

**What to watch for:** the register's rule still holds. No address enters the register, its log or the dashboard, whichever system holds them.

### A mail tool's lists

**Where it plugs in:** *Send a communication*, step 1.

**What it takes over:** a group that maps to a distribution list in the mail tool can name the list in its `Purpose`, and the user sends to the list.

**What to watch for:** the list's members then live in two places. Name which one is the source of truth in your copy of the skill, and let `check` keep comparing the register's members with the people actually reached.

### A shared drive for the contacts file

The contacts file is shared, if at all, wherever the project's folder is shared: a team drive or a synced folder, never the repository. Who can read it is that place's permission, not the tool's.

## How it is tested

`tests/smoke_test.py` installs the skill into an empty project and runs it: a register created with its contacts file; a group, stakeholders and communications added; contacts written; an audience resolved, whole and split; a communication done; `due` per sprint against a scratch WBS calendar and with no calendar; `check` finding a missing contact, a gap with no action and a contacts file git would take; the dashboard generated with no address in it; the solo default on a project with no register; on a project set up from the starter pack, the planning folder reaching the register in Confidential and the register reading the WBS's sprint calendar; and the example register passing `check` with the findings it is built to show: a gap with no engagement action, and no contacts file, since none is shipped.

What is **not** tested is whether the analysis is right: whether a stakeholder's power or engagement was read well. No test asserts that, and none can.

## Relationship to other tools

- **TSP.10 Reporting**: the audience layer, who receives which report and at what share level. A status report records its audiences, `export --comm C.n` takes the share level from a communication, and the charter shows the stakeholders, by role and group in a shared copy.
- **TSP.8 Sprint Ceremonies**: the close-out sends the communications due per sprint and records them.
- **TSP.11 Weekly Review**: names overdue communications and gaps with no action, read only.
- **TSP.2 RAID Register**: an engagement action may be a RAID Action; RAID's `Sharable` decides what an external copy holds.
- **TSP.12 Action Tracker**: holds what other people owe; this register holds who they are and what they hear.
- **TSP.7 Notebook Manager**: meeting notes are where an interactive communication is recorded.
- **TSP.6 Content System**: a public audience's communication points to one of its plans; never written from here.
- **TSP.3 TSP Register**: row 13.

Nothing is sent by this tool, and no external service is read: addresses come from the project's own contacts file.

## Maintenance

**Each sprint close-out:** the communications due are sent and stamped.

**Weekly review:** overdue communications and unaddressed gaps are named.

**When contacts change across projects:** `check --all`, and settle the ones that disagree.

**When a project gains someone to keep informed:** a register is created through the skill, with the user.

**When a consumer is added:** it reads `stk_register.py`; it keeps no audience list of its own.

**Before structural change:** snapshot the register into `PreviousV/`.

## Open items

| Item | Detail |
|---|---|
| Unused on real work | See *Status*. A project run with a sponsor or client through a few sprints is what moves the tool to `Implemented` |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.4 | 2026-11-04 | **Notes are written and shown to be read in a list.** SKILL.md says how to write a note, and `note` says when one runs past 400 characters. The panel had listed entries as small undivided text; each is now a block with its date and title, a long one folded, the newest open, and an `S.n` or `C.n` in it linked. A communication opens the same detail as a stakeholder, since its notes had reached the page unshown. `note` had accepted a group, which has no notes field; it now refuses one. `check` warns on a note holding what looks like an email address or phone number. The panel's changes leave out `Note added`. |
| v1.3 | 2026-11-04 | **Notes became a dated log, a stakeholder's detail opens from the dashboard, and the views are active by default.** `stk.py note` adds an entry on top and the change log records only that one was added; `set --notes` is refused, since it overwrote the field each time. The dashboard had passed notes to the page and never shown them; it now opens a person's detail from any name, and refresh writes a second page without notes. Engagement, communications and groups had listed inactive rows greyed; they now need the *Show inactive* switch, and `list` needs `--inactive`. `check --all` stopped comparing the contacts of stakeholders inactive in their project. |
| v1.2 | 2026-11-03 | The register in `Confidential/Stakeholder Mgm`, where the starter pack puts it: given the planning folder it is found through the artifact register first, then by name, so the status report reads it instead of the solo default; the sprint calendar is searched upward from it, so `per sprint` follows the sprints instead of every 14 days. `check` reports a register outside Confidential and a `per sprint` communication with no calendar. |

Earlier versions are in this file's git history.
