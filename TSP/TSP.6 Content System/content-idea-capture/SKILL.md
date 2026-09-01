---
name: content-idea-capture
description: Park a content idea in seconds before it evaporates, and manage the inbox of ideas waiting to be written. Use when someone says they have an idea for a post, wants to jot something down for later, asks what ideas are waiting, wants to start working one up, or wants to drop one. Captures in the author's own words without interviewing, sharpening, or asking for an angle — developing the idea is the writer's job, not this one's.
user-invocable: true
---

# Capture a content idea

Catch a spark before it evaporates. **Seconds, not a conversation.**

Format: [`_shared/contracts/ideas-inbox-format.md`](../_shared/contracts/ideas-inbox-format.md). It is the source of truth — where this file and the contract disagree, **this file is the defect**.

## Capture

One exchange. Take the author's words, append a row to `content-system/ideas.md`, confirm in one line, stop.

- **Record the idea in the author's own words.** Do not sharpen it, expand it, retitle it, or make it sound better. A capture that comes back polished is a capture the author has to check.
- **Scope is optional.** Offer the scopes that have a strategy file — walk `content-system/strategies/` — and accept "none" instantly. Never block on it. Most sparks arrive before anyone knows where they belong.
- **ID is `YYYY-MM-DD-<letter>`**, the letter incrementing within the day. It exists so the author can say "the second one" while the idea waits.
- **Several ideas in one message is one capture, not several.** Append them all in one write, letters incrementing across the batch, and confirm in one line. Turning a batch into five exchanges is the same failure as interviewing — it makes the fastest action in the system the slowest.
- **A scope the author has just named may be applied to the whole batch, provided you say so.** *"All five under `areaOfFocus/product-craft` — tell me if any of those belong elsewhere."* An announced scope is corrected in seconds; a scope question per row is the interview this skill exists to avoid. Say nothing and it is an inference, which is a different thing entirely.

### The one hard rule

**Capture never interviews.**

The refinement gates protect the moment an idea becomes a *piece*. They do not belong at the moment it becomes a *row*. An interview here makes the fastest action in the system the slowest — and then the author stops using it and the idea is lost entirely, which is the failure this skill exists to prevent.

No angle. No "what's the most important point?". No audience. No persona. Those are Phase 1 of `content-post-writer`, and they are that skill's job.

## What's waiting

Read `content-system/ideas.md` and show the table as it stands. **The count is the row count** — no filtering, no status to interpret. That is the whole reason the file holds waiting items only.

## Promotion — start working an idea

Move the row out of the inbox and create a bundle folder:

```
content-system/posts/YYYY-MM-DD-slug/backbone.md
```

with frontmatter carrying `from-idea:` (the ID and the original text) and `scope:` if known, then `## Idea` — the capture, verbatim — and an empty `## Notes`.

**No angle is required. No plan. No commitment to finish.** This is the point of promotion: an idea being actively worked is neither waiting nor written, and without a place to sit it would have to stay in the inbox pretending to be untouched. The bundle folder is where refinement happens — notes now, angle when it settles, and the rest as `content-post-writer` fills it in.

**A promoted idea may be abandoned.** The folder stays where it is, counted as in-progress. Nothing drags it back to the inbox, and nothing needs cleaning up.

**Drafting straight from an inbox idea is a promotion** — it creates the folder and removes the row in one step. Hand off to `content-post-writer` from there.

### Never route to the assessment pipeline

`.specify/assessments/` is a **build/don't-build gate** for capabilities. It asks for goals, non-goals, success metrics, appetite and solution options, and its verdict hands off to `/speckit-specify`. Those are questions about shipping software, not writing a piece — and it sits outside `content-system/`, so anything routed there breaks the moment this folder is copied to another context.

**An idea *for this system* belongs in assess. An idea *for a piece* belongs here.** A content idea that needs real work gets promoted and refined in its own backbone; it does not need a heavier gate.

## Dropping

Move the row to `## Dropped` with the date and a one-line reason. Ideas are allowed to die — an inbox that only accumulates stops being an inbox and becomes a guilt pile.

That section is prunable at any time and nothing reads it.

## Degradation and cold start

Works with **nothing else present** — no strategy, no plan, no posts, no prior ideas. A missing `content-system/ideas.md` is created on first capture, never scaffolded ahead of time — header, table header and an empty `## Dropped` section, written in the same turn as the first row. The cold start is not a special case and needs no announcement beyond the usual one-line confirmation.

## Verify

After appending, moving, or removing a row, re-read the file and confirm the table still parses — header intact, one row per waiting idea, nothing left in two places. Correct once; on a second failure say so plainly. A malformed table silently miscounts the pipeline's front stage, which is the one thing this file exists to make countable.

## What this must never become

- An interview.
- A tagging, priority, or scoring system.
- A place where ideas get developed rather than parked.
- A second inbox alongside the outer workspace's `_editorial/_ideas/` — this one reads nothing outside `content-system/`.
- A router into `.specify/assessments/`.
