---
name: content-plan-author
description: Interview the author to turn a scope's decided position into a plan — the goal it serves, audience, objective, the pillars in play, channels, and either a monthly rate or the arc of pieces a campaign is made of — and commit pieces from that arc by creating their WBS rows. Use when a strategy exists and someone wants a plan, a campaign, a content series or calendar, to add or amend a piece or a rate on an existing plan, or to commit a piece so it can be worked. Runs only against an existing strategy file; it never invents a position.
user-invocable: true
disable-model-invocation: true
---

# Author a content plan

Turn a decided position into **a plan, and pieces that can be committed**.

A strategy says what a scope is for. A plan says which goal it serves, to whom, on which channels, and either the rhythm it holds or the arc of pieces it is made of. They are separate decisions made at separate times, and this skill only ever makes the second one.

**When a piece is due, how much it takes and whether it is done live in the WBS**, in the row that commits it. This skill writes the arc and creates those rows; it never copies their dates or status into the plan.

Format: [`_shared/contracts/strategy-file-format.md`](../_shared/contracts/strategy-file-format.md). It is the source of truth — where this file and the contract disagree, **this file is the defect**. The WBS Ref and how a register is found: [`posts-format.md`](../_shared/contracts/posts-format.md), *WBS Ref*.

## Before starting

**Establish the scope by asking.** Offer the scopes that have a strategy file, enumerated by walking `content-system/strategies/`. Never infer the scope from whatever is being discussed.

**A strategy must already exist.** If the scope has none:

> No strategy exists for this scope yet. A plan draws its pillars from one, so that comes first — want to set one up?

Then hand off to `content-strategy-author` and **stop**.

This is the one capability in the system that refuses rather than degrades, and the reason matters: a plan without a house has no pillars to draw on, and auto-creating a stub would fabricate a position the author never decided. Everything downstream would then read that stub as a decision. **Never create, stub, or infer a strategy.**

**One plan per invocation.** A scope with zero plans is the common and correct state, not a gap to close.

## The interview

Conversational, one checkpoint at a time. Never a form.

**Shape is asked before anything shape affects.** It gates which later questions apply, and asking a campaign question of an always-on plan wastes attention and invites a wrong answer.

| Ask for | Notes |
|---|---|
| **Plan name** | Short. Becomes the `## Plan: <name>` heading. Must be unique within the scope — it is how the plan is picked later. |
| **Serves** | *"Which goal does this plan serve?"* — an objective, a key result, a project's goal, in the author's own words or identifier. It decides which WBS the plan's pieces are committed in: the register of the project or area that owns that goal. **If the author cannot name one, say so plainly and write the plan without it** — the review will keep flagging it, and that is the point. Never fill it from anywhere else. |
| **Shape** | Pick-list. `campaign` = a finite arc of pieces, each committed on its own. `always-on` = an ongoing rhythm with a monthly target. Describe both; do not assume the words land. |
| **Audience** | Free text. Lives here, never in the house — one position, many audiences beneath it. |
| **Objective** | One combined checkpoint: what should this audience know, feel, and do by the end of it? |
| **Pillars in play** | Multi-select **from that strategy file's own pillars**. References them; never redefines them. |
| **Channels** | Multi-select from the open set — `blog`, `linkedin`, `instagram`, `site`, and others as needed. This is the set the plan draws from, not something each piece inherits silently. |
| **Branch** | `campaign` → the arc of pieces. `always-on` → cadence, free text, then monthly target, then the month the rate starts, and **no arc table**. |

**The always-on monthly target is asked once, per channel in play** — *"how many a month on each, as a number I can score you against?"* Optional: declining leaves a plan that is counted but never scored, and the author decides that knowing it.

**Ask `**Started:**`, the month the rate begins, offering the current month as the default.** Never stamp it — today's date is not the same fact as when the author means to begin.

**Never derive the target or the start month from the cadence sentence.** `~2/month, floor 1/month` is prose holding two numbers; ask which one counts.

> **Why each of these is shaped this way** — what months before `Started` mean, why a prose cadence is never parsed, why a context row stays unscored — is in [`strategy-file-format.md`](../_shared/contracts/strategy-file-format.md). This file says what to ask; that one says why. Where they disagree, this file is the defect.

**Never a blank prompt where candidates are enumerable.** Shape, pillars and channels are all pick-lists.

**An answer that fits a different field is not this field's answer.** Asked for an audience, an author may say *"LinkedIn"* — a channel. Record it where it belongs, say that you have, and ask the original question again. The trap is that the wrong reading parses: `Audience: LinkedIn` looks like a filled field and quietly makes every angle drawn from it wrong.

**A field the author never answered is never written.** Checkpoints get skipped — an author answers the next question and moves on, and the objective is the one this happens to, because it is the one that takes thought. If drafting a version keeps things moving, say it is your draft, show it in full, and get an explicit yes before it enters the file. **Silence is not confirmation**, and neither is the author answering something else.

**Infer nothing structural.** Serves, shape, channel, objective, audience and pillars are always asked, even where a plausible default is sitting right there. Getting one wrong silently is the failure this whole flow exists to prevent. Offering a default is not choosing one: `**Started:**` defaults to the current month in the prompt, and the author still answers it.

**The author never types a structural token** — not a header, a field label, a table row, or a WBS Ref. They supply content; structure is your job.

## The arc — the only free-form input

Campaign plans only. One open checkpoint: *"give me the pieces this campaign is made of — working titles, one per line, and what each one is and where it goes if you know yet."*

Then parse into rows. **Every row starts as a candidate**: `WBS` and `Piece` blank.

- **`Working title` is the only thing you may insist on.** A candidate is promised to no one, and its type and channel may still be open.
- **`Type` is never inferred.** Nothing else in the plan implies whether something is an article, a short post, a carousel, a video, a deck, or a poster. Record it if given; leave it blank if not.
- **`Channel`** may be inferred only when the plan draws on exactly one. Otherwise record it if given.
- **`Pillar`** may be inferred only when the plan has exactly one in play. Otherwise record it if given.
- **`Bundle`** — offer a shared label when several rows are plainly one piece (a blog post, the LinkedIn post pointing at it, the video). Default it to the post slug the author will use, so no second identifier gets invented. Blank for standalone artifacts, which is most of them.
- **A piece already published** goes in as a context row — `Piece` linked, `WBS` blank — so the arc reads whole. Say so as you write it.

**Committing is a separate step**, below. Offer it once after the write — *"want to commit any of these now?"* — and take no for an answer.

## Playback, then one write

**Render the complete assembled section back** — fields and table, exactly as it will appear in the file — and ask once whether it is right.

This is where a parsing slip gets caught. Arc parsing is the only point in this flow where you interpret rather than record, so it is the only place a silent error can enter.

**Then write, once, after confirmation.**

- Appended **after all four house sections** and after any existing plans.
- House sections unchanged, byte for byte.
- Field labels and the table header exactly as the contract specifies — they are matched literally by every reader.
- Frontmatter regenerated.

**Abandonment writes nothing.** No partial file, no saved state, no draft that could later be mistaken for a decision. The conversation is the state.

## Verify your own write

The write is not done until you have read it back.

1. Re-read the file.
2. Apply the reader's rule to your own output: four house sections in fixed order, all of them before every `## Plan:`, field labels literal, table located by its header row.
3. On failure, correct it and re-check **once**.
4. On a second failure, report it — *"I couldn't write this in a way I can parse back; here's what I tried, please check it."* Never leave an unverified file on disk.

This is not a schema validator and must not become one. You are both writer and reader of the same rule; there is no excuse for the two disagreeing, and catching it now is far cheaper than discovering three sessions later that a plan silently stopped resolving.

## Committing a piece

**A separate action, asked for explicitly**, run **one row at a time**: *"commit the ceremonies piece"*, or at sprint planning, *"which of these are we committing?"*. It is how a candidate becomes work: committing a piece **is** creating its WBS row.

For the row the author names:

1. **The row must say what it is and where it goes.** `Type` and `Channel` are required now; ask for whichever is blank rather than committing without it.
2. **Find the register.** The plan's `**Serves:**` names the goal; the row goes in the WBS of the project or area that owns it. Ask which register that is if the goal does not settle it, and find the file by shape as the contract says. A plan with no `**Serves:**` cannot say where its pieces belong — ask the author to name the goal first, and write it into the plan in the same turn.
3. **Create the row** with the WBS tool (`wbs.py add`, in the `wbs-manager` skill's `scripts/`): a Story titled with the working title, Status `Not Started`, under the campaign's own WBS row if the author names one. Its estimate goes on the row if the author gives one. When it is due — a sprint, a planned date — is set on the row by the planning that commits it, not here.
4. **Write the new Ref into the row's `WBS` cell**, and verify by reading the file back.

**Run it row by row, never in bulk.** "Shall I commit the rest for you?" is the one question this action must never ask — pieces committed to clear a list are exactly the promises that get missed.

**A committed piece that is dropped before it is started** — `WBS` set, `Piece` blank — leaves the arc: propose its WBS row for `Cancelled` with the author's reason as the closure note, run it on their yes, and remove the row. Nothing was written, so the WBS row is the whole record. A piece dropped after it started belongs to `content-post-writer`, which keeps the folder as the record.

## Adding or amending the arc or the rate

A **separate, smaller action** — not a re-run of the interview.

- **Add a candidate**: one combined checkpoint — working title, and type, channel, pillar (from *that plan's* `Pillars in play`) and bundle label if known. Appended after the last existing row and **never reordered**.
- **Edit a row's** working title, type, channel, pillar or bundle: the same action, run against the row the author names.
- **Drop a candidate**: remove its row. Candidates are allowed to die.
- **Amend an always-on plan's `**Monthly target:**`** or its `**Serves:**`: the same small action, run against the plan the author names. Raising or lowering a rate held for months is a normal thing to want, and it does not require re-running the interview.

**The `WBS` and `Piece` cells are not editable through this action.** `WBS` is written by committing a piece, and `Piece` by `content-post-writer` when the bundle folder is created. This action does not take authority over a field another mechanism owns, even though it would be trivial to allow.

## What this must never become

- A form, a template, or any structured-input UI. The interview is conversational, like every other checkpoint in this system.
- A schema-validation library. Self-verification above is the whole mechanism.
- A persisted wizard with saved state. Abandoned means nothing written.
- A flow that infers a structural field.
- A combined strategy-and-plan interview. They are sequential, always.
- Anything that edits the house — mission, pillars, credibility signals, topics to avoid all belong to `content-strategy-author`.
- A second home for a piece's dates, effort or done-state. The WBS row holds them.
- A reader of anything outside `content-system/` other than a WBS register, through the WBS tool.
