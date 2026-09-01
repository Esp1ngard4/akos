---
name: content-plan-author
description: Interview the author to turn a scope's decided position into dated, trackable work — audience, objective, the pillars in play, channels, and either a cadence or a set of commitments that can actually be missed. Use when a strategy exists and someone wants a plan, a campaign, a content calendar, or a commitment they can be held to, and when adding or amending a commitment on an existing plan. Runs only against an existing strategy file; it never invents a position.
user-invocable: true
disable-model-invocation: true
---

# Author a content plan

Turn a decided position into **dated work that can be missed**.

A strategy says what a scope is for. A plan says what will be published, when, to whom, and on which channel. They are separate decisions made at separate times, and this skill only ever makes the second one.

Format: [`_shared/contracts/strategy-file-format.md`](../_shared/contracts/strategy-file-format.md). It is the source of truth — where this file and the contract disagree, **this file is the defect**.

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
| **Shape** | Pick-list. `campaign` = a finite push with dated commitments. `always-on` = an ongoing rhythm with a cadence and no dates. Describe both; do not assume the words land. |
| **Stage** | Campaign only, asked immediately after shape. `refining` = a backlog: candidates, no dates required, nothing scored. `active` = promises: every row scoreable, the fraction is real. |
| **Audience** | Free text. Lives here, never in the house — one position, many audiences beneath it. |
| **Objective** | One combined checkpoint: what should this audience know, feel, and do by the end of it? |
| **Pillars in play** | Multi-select **from that strategy file's own pillars**. References them; never redefines them. |
| **Channels** | Multi-select from the open set — `blog`, `linkedin`, `instagram`, `site`, and others as needed. This is the set the plan draws from, not something each commitment inherits silently. |
| **Branch** | `campaign, active` → end date, then commitments. `campaign, refining` → candidates, end date optional. `always-on` → cadence, free text, then monthly target, then the month the rate starts, and **no commitment table**. |

**Refining collects candidates, not commitments.** One open checkpoint, and **`Working title` is the only thing you may insist on**. A row may point at an already-published piece — `Date` blank, `Piece` linked — which is never scored; say so as you write it.

**The scoreability gate does not apply while refining**, and applies in full the moment the plan activates.

**The always-on monthly target is asked once, per channel in play** — *"how many a month on each, as a number I can score you against?"* Optional: declining leaves a plan that is counted but never scored, and the author decides that knowing it.

**Ask `**Started:**`, the month the rate begins, offering the current month as the default.** Never stamp it — today's date is not the same fact as when the author means to begin.

**Never derive the target or the start month from the cadence sentence.** `~2/month, floor 1/month` is prose holding two numbers; ask which one counts.

> **Why each of these is shaped this way** — what months before `Started` mean, why a candidate cannot be missed, why a prose cadence is never parsed, why an already-published row stays unscored — is in [`strategy-file-format.md`](../_shared/contracts/strategy-file-format.md). This file says what to ask; that one says why. Where they disagree, this file is the defect.

**Never a blank prompt where candidates are enumerable.** Shape, pillars and channels are all pick-lists.

**An answer that fits a different field is not this field's answer.** Asked for an audience, an author may say *"LinkedIn"* — a channel. Record it where it belongs, say that you have, and ask the original question again. The trap is that the wrong reading parses: `Audience: LinkedIn` looks like a filled field and quietly makes every angle drawn from it wrong.

**A field the author never answered is never written.** Checkpoints get skipped — an author answers the next question and moves on, and the objective is the one this happens to, because it is the one that takes thought. If drafting a version keeps things moving, say it is your draft, show it in full, and get an explicit yes before it enters the file. **Silence is not confirmation**, and neither is the author answering something else.

**Infer nothing structural.** Shape, channel, objective, audience and pillars are always asked, even where a plausible default is sitting right there. Getting one wrong silently is the failure this whole flow exists to prevent. The single system-chosen value anywhere is `Status: pending` at row creation, and that is an initialisation value write-back already expects. Offering a default is not choosing one: `**Started:**` defaults to the current month in the prompt, and the author still answers it.

**The author never types a structural token** — not a header, a field label, a table row, or a status value. They supply content; structure is your job.

## Commitments — the only free-form input

Campaign plans only. One open checkpoint: *"give me the dates and working titles you want to commit to, one per line — and what each one is and where it goes."*

Then parse into rows:

- **`Type` is always asked**, never inferred. Nothing else in the plan implies whether something is an article, a short post, a carousel, a video, a deck, or a poster.
- **`Channel`** may be inferred only when the plan draws on exactly one. Otherwise ask, per row.
- **`Pillar`** may be inferred only when the plan has exactly one in play. Otherwise ask, per row.
- **`Bundle`** — offer a shared label when several rows are plainly one deliverable (a blog post, the LinkedIn post pointing at it, the video). Default it to the post slug the author will use, so no second identifier gets invented. Blank for standalone artifacts, which is most of them.

### The scoreability gate

**Reject a row missing a date, working title, type, or channel.** Ask for the missing part rather than writing it.

This is the standard the whole feature rests on. *"Post regularly on LinkedIn"* cannot be missed, so it cannot be scored, so it is an intention — not a commitment. The delivered fraction only means something if every row in the denominator could genuinely have failed.

## Playback, then one write

**Render the complete assembled section back** — fields and table, exactly as it will appear in the file — and ask once whether it is right.

This is where a parsing slip gets caught. Commitment parsing is the only point in this flow where you interpret rather than record, so it is the only place a silent error can enter.

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

## Adding or amending a commitment

A **separate, smaller action** — not a re-run of the interview.

One combined checkpoint: date, working title, type, channel, pillar (from *that plan's* `Pillars in play`, not the whole strategy's list), and an optional bundle label. `Status: pending`, `Piece` blank. Rows are appended after the last existing row and **never reordered by date**.

Editing an existing row's date, title, type, channel, pillar or bundle is the same action, run against the row the author names.

Amending an always-on plan's `**Monthly target:**` is the same small action, run against the plan the author names. Raising or lowering a rate you have been holding for months is a normal thing to want, and it does not require re-running the interview.

**`Status` is not editable through this action, in either direction.** `pending` → `delivered` belongs to write-back alone, and a `missed` the author wants visible stays a manual markdown edit. This action does not take authority over a field another mechanism owns, even though it would be trivial to allow.

## Activation — the grooming pass

**A separate action, asked for explicitly**, that moves a campaign from `refining` to `active` — where accumulated thinking gets resolved instead of accumulating further.

Walk the table row by row. Each one takes exactly one of three exits:

1. **Committed** — supply date, working title, type and channel.
2. **Dropped** — removed from the table. Candidates are allowed to die.
3. **Kept as context** — an already-published piece, `Date` blank and `Piece` linked. Never scored.

Then ask for the `End date`, required from here on, and rewrite `**Stage:**` to `active`.

**A plan cannot activate with a half-specified row left in it.**

**Run it row by row, never in bulk.** "Shall I date the rest for you?" is the one question this action must never ask — dates chosen to clear a list are exactly the promises that get missed.

**Nothing offers the reverse.** An active plan hand-edited back to `refining` is read as written, but no action performs it: reverting would erase the missed rows that are the entire value of having committed.

## What this must never become

- A form, a template, or any structured-input UI. The interview is conversational, like every other checkpoint in this system.
- A schema-validation library. Self-verification above is the whole mechanism.
- A persisted wizard with saved state. Abandoned means nothing written.
- A flow that infers a structural field.
- A combined strategy-and-plan interview. They are sequential, always.
- Anything that edits the house — mission, pillars, credibility signals, topics to avoid all belong to `content-strategy-author`.
- A reader of anything outside `content-system/`.
