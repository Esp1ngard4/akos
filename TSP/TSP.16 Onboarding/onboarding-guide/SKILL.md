---
name: onboarding-guide
description: Onboards people to a project run on these tools (TSP.16 Onboarding) - generates the project's guide in two editions from its own files (the team guide for the product team - why the project exists, how people and agents work together, the tools, where things are, who's who, the sprint's rhythm and a step-by-step path per role saying who acts at each step - and the executive overview for people outside the team - the AI-first way of working, the principles, the rhythm, what they will receive, the system at a glance), reads it through with the product manager, and walks a newcomer through their first week in conversation. Use whenever someone joins the team, asks to be onboarded or says "onboard me", asks how the project works, what a tool is for, what they should do in their first week, or what to say to an agent; when the product manager wants the guide generated, refreshed, posted or adapted to the team's roles; or when a tool is installed, the brief changes or the team changes and the guide should follow. Not for status reports (reporting) or the brief itself (project-definition-manager).
---

# Onboarding Guide (TSP.16)

A newcomer to a project run on these tools meets a lot at once: a brief, a backlog, a board, risks, ceremonies, and agents doing work alongside people. This skill turns the project's own files into a guide they can actually take in, and walks them through it.

**The guide is generated, never written.** Everything in it comes from the project as it is set up: its brief, its registers, the tools it has installed, its sprint calendar. Regenerating is how it stays true; nobody edits the page.

## Requirements

Python 3, standard library only. `<skills>` is the folder this skill is installed in. Reads, where installed beside it: `project-definition-manager` (the brief), `status-board-manager` (how its boards are named). Without any of them, that part of the guide is said plainly or left out.

## Files

| File | Role |
|---|---|
| `scripts/onboard.py` | Gathers the record from the project's files and writes both editions |
| `scripts/render.py`, `guide.css`, `guide.js` | The pages: one self-contained HTML file each |
| `assets/fonts/` | The three typefaces, embedded in every page, with their open licences |
| `scripts/smoke_test.py` | Checks the record and both pages on a scratch project |

## The two editions

| | Team guide | Executive overview |
|---|---|---|
| **For** | The product team: product manager, developers, validation and quality | Anyone outside the team: a sponsor, a client, a reviewer, another department |
| **Holds** | Welcome (the brief's statement, the sprint's cycle), why, you and the agents, the tools you'll use and the product manager's, where things are, who's who, the rhythm, how work gets done (the loop and the work's folder), your first week by role, a glossary | The AI-first way of working, six principles with what each means for the reader, the rhythm and what they will receive, how work gets done, the system as one loop of people and agents |
| **Never holds** | | Names, file paths, commands, anything from the RAID |

**People and agents both do the work; people decide.** Agents also keep the records and prepare; people confirm and own the outcome. Every step of every path says who acts.

**Nothing in it changes from one sprint to the next.** It holds what changes when a tool, the brief or the team changes: the sprint's pattern, never the running sprint, its goals, its dates or this sprint's board. It says where the current state is instead: this sprint's board, the sprint record, the latest status report.

**What it teaches follows what is installed.** With the team board (`status-board-manager`), people update the board or ask Copilot in Excel, and the product manager consolidates; without it, people tell the agent. A ceremony that is not installed is not on the rhythm.

## Generate

```
python <skills>/onboarding-guide/scripts/onboard.py guide "<project folder>" [--records "<sprint records>"]
```

Writes into the project's onboarding folder `Guide.json` (the record), `Guide.html` (the team guide, linking to the other) and `Guide (executive).html`, overwriting the last ones. The onboarding folder is the planning folder's `Onboarding`, numbered or not. Where the project keeps an artifact register, register the folder there first and create it as `<ID>. Onboarding`; otherwise `Onboarding/` is created. `show` prints the record without writing anything, to check what it found.

**Then read it through with the product manager** before anyone else sees it. Look for what the files could not say: a project with no brief has no *Why*; a project with no stakeholder register has no *Who's who* and a default *What you'll receive*. Say which file would fill each gap, and offer the tool that writes it. Never fill a gap by editing the page.

## Post it

Where the team will find it: the project's channel or shared drive. The team guide goes to the team; the executive overview goes to people outside it, and only that one. The page opens from a folder in any browser; a shared drive may download it rather than show it, which is fine.

## Regenerate when

- a tool is installed or removed, or its use changes (a team starts using the board), or the sprint's length changes;
- the brief changes;
- the team changes (a stakeholder register entry).

The weekly review is a good moment to ask whether any of these happened.

## Onboard me

When someone asks to be onboarded, walk them through it in conversation; the page is the reference, the conversation is the onboarding.

1. **Ask their role**, then read the guide's record (`Guide.json` in the onboarding folder). If it is older than the last change listed above, generate it first.
2. **The why, in two sentences**: the brief's statement and outcome. With no brief, say so and who to ask.
3. **How we work with agents**: the work agents do here alongside people, what they keep, what they decide (nothing), and what is the person's to decide. Then the loop a piece of work follows: committed, discover, specify, plan and approve, do, verify and close, each stop drafted in the work's folder and reviewed by a person. One example from their role.
4. **This sprint**, from the live records, not the guide: its goals, and what is theirs in it.
5. **Their five steps**, one at a time, from the guide's path for their role. For each: what it is, who acts, and what they would say. Offer to do the first one with them now, for real: open their tasks on the board, or show them this sprint's work.
6. **Where to ask**: the product manager, and you.

Keep it short: one step per message, and wait for them. Never make a change in a register on their behalf during onboarding unless they ask.

## Adapting it to the team

The roles and their five steps are in `render.py` (`paths`): product manager, developer, validation and quality, with the steps written for the board or for the agent. A team with other roles edits them in its copy of the skill; the installer records the change. Keep five steps per role, each saying who acts.

## Relationship to other skills

- **`project-definition-manager`** — the brief: the guide's *Why* and its welcome.
- **`status-board-manager`** — the team board: whether people update a board, and its file.
- **`sprint-facilitator`**, **`weekly-review-facilitator`** — the rhythm: which ceremonies are on it.
- **`stakeholder-manager`** — who's who, and what an outsider will receive.
- **`artifact-register`** — what each folder holds.
- **`reporting`** — the status report the guide points to; the guide is not a report.
