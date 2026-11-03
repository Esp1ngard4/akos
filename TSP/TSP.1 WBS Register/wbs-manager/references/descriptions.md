# Writing a row's description

A row's description says **what the row is today**, in a few lines a reader takes in at a glance. It is not a log: how the row got here (raised, groomed, resized, agreed) goes in Comments as a titled note (`wbs.py note --title`). It doesn't repeat what another field holds: acceptance criteria, effort, sprints, dependencies, dates.

**About 80 words; 100 for a Deliverable or a Feature.** Thinking that needs more belongs in the row's Execution folder (a discovery, a specification), with a pointer to it.

**When scope changes, rewrite the description** so it stays true, and log the change as a note. The description is the current state; Comments is what changed.

**Guidelines, not gates.** The templates below are where to start. A row that needs a different shape takes it. Nothing refuses a description that doesn't follow them.

## The shape

Open with **one sentence: what the row delivers or changes.** A Deliverable or a Feature names a thing (a noun); a Story or a Task names an activity (a verb), as their titles do. Then the labelled parts for the row's type, each starting its own line:

```
<what it delivers or changes, one sentence>
Label: <a sentence or two>
Label: <…>
```

The dashboard shows each label as a small heading. It also renders `**bold**`, `code`, bullet lines (`- `) and blank-line paragraphs, and folds a long description after its first part.

## By row type

| Row | Labels | Based on |
|---|---|---|
| **Deliverable** | **Purpose:** why it exists and whom it serves · **Not:** what it deliberately isn't | PRINCE2's product description; PMBOK's WBS dictionary |
| **Feature** | **Value:** the benefit expected, the outcome it serves and the measure it should move (`moves …`) · **Approach:** the high-level way · **Not:** the no-gos · **PRD:** its capability, where one exists | SAFe's benefit hypothesis; Shape Up's pitch (problem, solution, no-gos); Cagan and Torres: work serves an outcome |
| **Story** (Build, Improve) | **Problem:** what's wrong or missing today · **Approach:** only if it isn't obvious | Problem-first framing |
| **Story or Task, Nature Analyse** | **Question:** what needs finding out · **Decides:** which decision the answer feeds | Spike practice |
| **Story or Task, Nature Fix** | **Symptom:** what goes wrong, and where · **Cause:** if known | Bug-report practice |
| **Task** | None: one line | |

**A Feature's Value names its outcome:** the objective, goal or measure it serves, and the measure it should move. After delivery, a titled note `Outcome check` can record whether it moved (moved, flat or unclear). Read across Features, those checks tell moving the needle from shipping features.

**Scope:** (what's in) may sit beside **Not:** on any row whose boundary is worth saying. A Feature points to its PRD capability rather than restating it: the PRD holds the product, the WBS the work.

## Examples

**Deliverable** — *Team onboarding guide*

```
The guide a new team member follows to set up their tools and pick up their first piece of work.
Purpose: a newcomer contributes in their first week without a person walking them through it.
Not: the HR induction, or the project's own documentation.
```

**Feature** — *Saved searches*

```
Customers save a search and rerun it from their home page.
Value: serves the objective "customers find what they need faster"; moves the share of searches repeated by hand within a week.
Approach: a saved search is a named query on the account, listed on the home page.
Not: alerts when new results appear.
```

**Story** — *Make WBS comments readable*

```
Show each comment as its own block, with its date, label and title, and the closure note's verdicts as badges.
Problem: the card shows Comments as one plain-text block, so entries and verdicts are hard to find.
```

**Analyse** — *Choose the team's status board*

```
Decide where the team keeps its daily status.
Question: which board the team already lives in, and what it must hold for an agent to read it.
Decides: the board, and whether the status-board tool is installed.
```

**Fix** — *Sprint card path runs outside the card*

```
Keep a sprint card's parent path inside the card.
Symptom: on boards with long titles the path overflows to the right of the card.
Cause: the path is one unwrapped line with the full chain.
```
