# TD.18 — Change Requests

## Purpose

The team's channel for asking that the project's registers change. The WBS and the RAID are kept by the product manager, but the team sees what should change in them first. A change request carries that from whoever saw it to whoever keeps the registers, and back: the outcome is written on the request, where the requester can see it.

## Status: In Progress

| | |
|---|---|
| The design | A request a file, drafted by anyone with their agent; processed by the product manager at the weekly review, in the same batch as the team board's consolidation |
| As shipped here | **Not yet used by a team.** Exercised by its smoke test on a scratch project |

## Components

| Component | Location | Purpose |
|---|---|---|
| This document | `TSP.18 Change Requests/` | What the tool is for and why; how to adapt it |
| `change-request` | `change-request/SKILL.md`, `scripts/cr.py` | Drafting, looking up what a request affects, listing, closing |
| The requests | The planning folder's `Change Requests/`, processed ones in `Processed/` | One Markdown file each |

## What the skill covers (and this document doesn't repeat)

`change-request/SKILL.md` holds the commands, how a request is drafted and processed, and what is never done. This document covers why the tool is shaped as it is.

## Design decisions

**A proposal until decided.** A request never writes a register. The person who keeps the WBS and the RAID decides, and applies it through the skills that keep them; a register written from a draft would be a register nobody keeps.

**One file per request, its outcome on it.** A request is read later for what was asked and what came of it. A file holds both, and a processed one moved to `Processed/` leaves the folder showing only what is still open. Nothing in the file says *open* or *closed*: where it sits says it.

**Decided at the weekly review.** The board's consolidation already brings the team's status into the registers once a week; requests join that batch, so the product manager decides them together and the team knows when to expect an answer.

**What it affects, by ID.** A request naming `WBS 12` or `RAID 3` is processed in a minute; one naming "the login thing" starts a conversation. The agent looks the IDs up, read-only, so the team member need not know them.

**Status is not change.** A task inside committed work goes on the board; a change to what is committed, or to the risks, is a request.

## Naming conventions

- **Files:** `CR <date> <first words of the request>.md`.
- **Types:** risk, issue, decision, change, new work, idea.
- **Outcome:** `Accepted as RAID 14` or `Declined: <why>`, dated, with who decided.

## Adapting it to your tools

**Every real implementation will need its own changes to work properly.**

### Requests in a ticketing tool

**Where it plugs in:** `cr.py draft` and `list`.

**What it takes over:** a team already raising requests in a tracker drafts them there; the processing stays the same.

**What to watch for:** the outcome must still reach the requester.

## How it is tested

`change-request/scripts/smoke_test.py` builds a scratch project with a WBS and a RAID and checks: a draft lands in the folder with its type, requester and what it affects; *lookup* finds rows and entries by words; *list* shows the open ones; *close* writes the outcome and moves the request to `Processed/`, accepted or declined, and a decline needs its reason. `tests/smoke_test.py` runs it and has `init` install it at the project root.

## Relationship to other tools

- **TSP.1 WBS Register**, **TSP.2 RAID Register**: where accepted requests are applied.
- **TSP.11 Weekly Review**: where the open requests are processed.
- **TSP.15 Team Status Board**: status, beside this tool's change.
- **TSP.17 Work Management**: work items turn up the changes requested here.
- **TSP.4 Tool Installer**: `init` installs it at the project root and sets up the folder.

## Maintenance

**At the weekly review:** the open requests are processed.

## Open items

| Item | Detail |
|---|---|
| Unused by a team | See *Status* |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-29 | Published as TSP.18: drafting with what a request affects by ID, listing, closing with the outcome; processed at the weekly review. Raised trying the starter pack as a team member. |
