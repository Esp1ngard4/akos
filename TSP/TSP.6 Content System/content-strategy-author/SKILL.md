---
name: content-strategy-author
description: Interview the author to decide a content strategy for one scope — the position it is built around, the pillars supporting it, what makes them credible, and what is deliberately excluded — and write it as a message house the drafting skill can read. Use when a scope has no strategy file, when an existing one needs rethinking, or when someone asks to set up positioning for a project or area of focus. Asks and records; it never decides positioning, and never derives it from what has already been published.
user-invocable: true
disable-model-invocation: true
---

# Author a content strategy

Interview the author until a scope's **position** is decided, then write it as a message house.

Strategy is a **choice about where they are going** — not a summary of where they have been. You ask, sharpen, and record. You never decide, and you never read their published pieces to work out what their strategy "must be."

## Before starting

**Establish the scope by asking.** Which project, area of focus, or area of interest is this strategy for? Never infer it from what is being discussed.

**Stop if a strategy already exists** for that scope. Report the file and what it contains. Do not overwrite it, do not merge into it, do not "just add the missing sections." If the author wants it rethought, they say so explicitly first.

**No published work is needed.** A scope with nothing written is fully authorable. Nothing in this interview reads the pieces filed under a scope — they are not evidence for positioning.

**This is invoked deliberately** — by the author asking, or by them accepting the offer from the drafting skill. It never runs as a side effect of anything.

## The interview

Top-down, one checkpoint at a time. The order is the message house: the roof holds up everything beneath it, so nothing below is settled before it.

| # | Ask for | Required |
|---|---|---|
| 1 | **Mission** — one sentence. What is this scope *for*? What should the author be known for here? | yes |
| 2 | **Pillars** — 3–4, each a name and a line. The recurring messages the position rests on. | at least one |
| 3 | **Credibility signals** — what makes this believable: work, artifacts, outcomes, failures, constraints. | no |
| 4 | **Topics to avoid** — deliberately excluded subjects. | no |

Do not settle a pillar before the mission exists. Steps 3 and 4 are skippable in one word; offer that plainly rather than pressing.

**Never a blank prompt.** Offer: *"tell me, or I'll draft one from what you say next and you confirm it."*

**What you may draw on when drafting.** Only what the author has said **in this conversation**. Not their published pieces. Not another scope's strategy. Not what sounds plausible for someone in their field. Drafting from published work is derivation wearing a different hat, and it produces a description of the past dressed as a decision about the future.

**How to ask** — the standard this project already holds for interviews: *ethical journalist, not stenographer*. Push on a vague claim. Probe an unexamined assumption. Ask "how would that rule anything out?" when a pillar could cover everything. But that pressure runs **one way only**: toward precision on what the author already believes, never toward a position you supply instead.

### Probes, when an answer is thin

Reach for these when a direct question produces something vague or aspirational. They are **not** a questionnaire and not extra checkpoints — asking all of them every time would make this the heavy interview it is deliberately not. Pick the one that fits what is stuck.

**When the mission is broad enough to cover anything:**
- *"Who else writes about this, and why would someone read you instead of them?"* — asks for differentiation without you supplying any. Their answer, not your research; never look it up.
- *"What would you be annoyed to see someone else get credit for?"*

**When pillars are aspirational rather than real:**
- *"What do people already come to you asking about?"* — grounds a pillar in demand that exists rather than a topic they wish they owned.
- *"Which of these could you write about next month without new research?"*

**When credibility signals come back thin or generic:**
- *"What would make someone doubt you're worth listening to on this?"* — the inverted probe. Far sharper than asking what makes them credible, because the honest answer names the gap, and the credibility signal is usually whatever closes it.
- *"What have you actually done here that most people writing about it haven't?"*

**When topics-to-avoid is empty:**
- *"What are you regularly tempted to write about that would pull this off-course?"* — an empty exclusions list is often an unexamined one rather than a genuinely open field.

Every one of these asks the author to supply something. None offers a candidate answer, and none is a reason to go looking at their published work.

**Before writing, apply the forward-looking test.** Could this strategy rule a future piece in or out? If it only describes what has already been written, it has failed — say so and keep working, rather than writing a summary.

**If there is no position, write nothing.** Where the author cannot yet articulate what the scope is for, stop and say so plainly. No file is an honest outcome and a good one; a plausible file is not, because everything downstream will read it as a decision that was made.

## Writing the file

One write, at the end. Never mid-interview — if the author abandons, nothing exists on disk. No partial file, no draft that could later be mistaken for a decision.

Location and shape are fixed by the format contract at [`_shared/contracts/strategy-file-format.md`](../_shared/contracts/strategy-file-format.md) — the source of truth, and the same file the plan-authoring and review capabilities read. The house shape is repeated inline below because you must never get these four headers wrong; anything beyond the house, in particular the `## Plan:` fields and the commitment table, is read from the contract rather than remembered. **If the contract and this file ever disagree, the contract wins and this file is the defect.**

```
content-system/strategies/<category>/<slug>.md     # projects | areaOfFocus | areaOfInterest
content-system/strategies/default.md               # catch-all, no category subfolder
```

```markdown
---
scope: areaOfFocus/<slug>
created: YYYY-MM-DD
---

## Mission
One sentence.

## Pillars
- Pillar name — one line each

## Credibility signals
- Optional.

## Topics to avoid
- Optional.
```

**You write the headers, exactly, in that order. The author is never asked to type a structural token** — not a header, not a label, not a marker. They supply content; structure is your job.

**Section order is load-bearing, not stylistic.** All four sections precede any `## Plan:` section, because a plan is delimited from `^## Plan: ` to the next `^## `. Reorder them and plans become silently invisible to the drafting skill — no error, just a plan that quietly stops resolving.

**Required for the file to exist at all**: a mission, and at least one pillar. With neither, this is not a strategy but an empty stub, and it should not be created.

**No audience anywhere in the house.** Audience belongs to a plan beneath it. One house per scope; audience varies underneath.

Create `content-system/strategies/` on first real use. Never scaffold it empty.

## Verify your own write

The write is not done until you have read it back.

1. Re-read the file you just wrote.
2. Apply the same literal rule a reader applies: exact headers, fixed order, all four before any `## Plan:` section.
3. On failure, correct it and re-check **once**.
4. On a second failure, report the failure and what you attempted — *"I couldn't write this in a way I can parse back; here's what I tried, please check it."* Never leave an unverified file on disk.

This is not a schema validator, and you must not build one. It is you applying, to your own output, the rule you already apply when reading. You are both writer and reader of the same rule — there is no excuse for the two disagreeing, and catching it now is far cheaper than discovering three sessions later that a strategy silently stopped resolving.

**If an existing file no longer conforms**, report that to the author. Do not silently rewrite it or work around it.

## Plans are a separate flow

This authors the **house only**. `## Plan:` sections — audience, objective, shape, channel, commitments — are authored separately and sequentially, never inside this interview.

A strategy with zero plans is the common and correct end state, not a step to push someone past.

## What this must never become

- A form, a template to fill in, or any structured-input UI. The interview is conversational, like every other checkpoint in this system.
- A schema-validation library. Self-verification above is the whole mechanism.
- A persisted wizard with saved state. The conversation is the state; abandoned means nothing written.
- Anything that auto-infers a structural field. Ask.
- A combined strategy-and-plan interview.
- A reader of published pieces. They are not evidence for where someone is going.
