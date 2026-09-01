# Contract — ideas inbox format

**Source of truth for the idea inbox.** Where any other document disagrees, this file wins.

**Consumers**: `content-idea-capture` (writes), `content-post-writer` (reads when drafting from an idea, removes the entry, carries its context into the backbone), `content-review` (counts waiting ideas as the front pipeline stage).

## File

`content-system/ideas.md`. One file. No folder, no index, no file per idea.

```markdown
# Ideas — inbox

### 2026-08-11-a · Intake automation broke in a way that taught me the process was the problem
Captured 2026-08-11 · areaOfFocus/product-craft

The rollback took nine minutes and the postmortem took three weeks. Worth
saying because everyone reaches for a better script first, and the script
was never the problem.

### 2026-08-11-b · Why "AI strategy" decks keep describing tools instead of work
Captured 2026-08-11

## Dropped

| ID | Captured | Idea | Dropped | Why |
|---|---|---|---|---|
```

**One entry per waiting idea: a `###` heading, a meta line, and — only if the author supplied one — context beneath it.** `2026-08-11-b` is the ordinary case: a heading and a meta line, nothing else. That is a complete capture, not an unfinished one.

## Rules

**The file holds waiting ideas only.** An idea leaves when it is **promoted** or dropped. There is no status field, because "what is waiting" must be a read, not a filter — and a stale `done` marker silently inflates the pipeline count.

**Context sits inside its own entry, never in a separate section.** This is the whole reason the inbox is entries rather than a table: an idea and the author's reason for it are one thing, and splitting them across two places needs a consistency check to keep them together, which is the tell that they should not have been split. There is no keying, and therefore no orphan to check for.

**The heading is `### <ID> · <the idea, one line, in the author's words>`.** Capture does not interview, sharpen, or expand — a capture that comes back polished is one the author has to check.

**The meta line is `Captured <YYYY-MM-DD>`**, plus ` · <scope>` when a scope is known. Nothing else goes on it.

**`ID` is `YYYY-MM-DD-<letter>`**, the letter incrementing within a day. It exists so the author can say "the second one" without ambiguity while the idea waits. It is not a permanent identifier and nothing resolves it after the entry leaves.

**Scope is optional** and uses the strategy path form when present. An idea captured with no scope is normal — capture must work when no strategy file exists anywhere. A scope the author has just stated may be applied across a batch **provided the write says so**; applied silently it is an inference, and inference is what every other part of this system refuses.

**A batch is one capture.** Several ideas in one message are appended in one write with letters incrementing across them, and confirmed once. Splitting a batch into an exchange per idea defeats the ten-second promise the format exists to keep.

### Context

**Optional, author-supplied, and offered rather than asked for.** The body of an entry holds whatever the author volunteers about why the idea is worth writing — the number behind it, the failure that prompted it, who it is for. Unbounded, and usually absent.

Three rules make it safe:

- **The skill never asks for it.** No "would you like to add context?", no prompt after a capture, no nudge on the entries that look thin. Asking is the interview this format exists to prevent, and it would cost the ten-second promise on every capture to serve the minority that carry any.
- **The skill never writes it itself.** An inferred reason is a fabricated one, and it is worse than nothing here because it will later be read as the author's own thinking.
- **It arrives with the capture, or later, by the author saying so.** A batch with context on one of five ideas is still one capture and one write.

The reason context belongs here and not in a promoted `backbone.md`: a bundle folder under `posts/` reads as a commitment to write the thing, and recording why an idea matters is not that. It is the capture finishing itself. An idea may carry a full paragraph and still be waiting, untouched, for a year.

**Context is not a triage field.** It holds the author's reason, not a rating of it. See [What must not be built](#what-must-not-be-built).

### Leaving the inbox

**Promotion is the moment an idea starts becoming a piece** — an angle forming, an outline, notes about the writing rather than about the idea. It does not require an angle, a plan, or a commitment to finish. It creates a bundle folder with a `backbone.md` carrying the idea text and whatever context exists — see [`posts-format.md`](posts-format.md). That folder is where refinement lives: notes, the angle once it settles, Six Questions, outline.

This is deliberate: an idea being actively developed is neither "waiting" nor "written", and without promotion it would have to sit in the inbox pretending to be untouched. The three pipeline stages depend on the distinction being real.

**On promotion**: the entry is removed, and the new `backbone.md` records `from-idea:` with the ID and the original text. **Any context becomes the backbone's opening `## Notes`** — it moves with the idea, so there are never two live copies. Traceability runs piece → idea; there is no backlink from the inbox into the piece, because the entry no longer exists.

**A promoted idea can be abandoned.** Delete the bundle folder, or leave it — an unfinished folder with no locked artifact is a normal, visible state, and it is what the middle pipeline stage counts. Nothing forces it back into the inbox.

**On dropping**: the idea moves to the `## Dropped` table with a date and a one-line reason; its context goes with it and may be pruned. That section stays a table because a dropped idea is a one-liner with a reason, it never carries prose, and nothing reads it.

**Counting**: waiting ideas is the number of `###` entries. Nothing else needs computing. **Context is never counted** — an idea with three paragraphs and an idea with none are both one waiting idea, and a count that treated them differently would be scoring, which this file does not do.

## Verify on write

**Every write is checked by reading it back.** After appending, moving, or removing an entry, re-read the file and confirm it still parses: one `###` heading per waiting idea, each with a `Captured` meta line, no idea left in two places, and the `## Dropped` table intact.

On failure, correct it and re-check **once**. On a second failure, say so plainly rather than leaving a broken inbox on disk. A malformed file here silently miscounts the pipeline's front stage, which is the one thing this file exists to make countable.

## What must not be built

No file per idea. No status field. No priority, tags, or scoring. No automatic promotion from idea to draft. No dependency on any inbox outside `content-system/` — in particular, not the outer workspace's `_editorial/_ideas/`.

**No required context, and no prompt for it.** Context is the author volunteering a reason; the moment it is asked for on every capture it has become the interview, whatever it is called. An entry with none is complete, not unfinished, and nothing may render it as missing or list which ideas lack one.

**No stored summary table.** A compact list of waiting ideas is a fine thing to *render* on request, and `content-idea-capture` does. Writing one into the file would be a second representation of the same ideas, and two representations drift.

**Growth trigger**: if waiting ideas routinely exceed ~50, the file stops being readable in one pass and wants splitting by scope. Not before.

## Revision history

| Date | Change |
|---|---|
| 2026-09-01 | Table replaced by one `###` entry per idea, so that context sits with the idea it belongs to. The first attempt kept the table and put context in a separate `## Context` section keyed by ID; it needed a verify rule for orphaned blocks, which was the tell that one thing had been split across two places. Nothing parses this file — the tool ships no code — so the table was a convention, not a schema. |
| 2026-09-01 | Optional context added at capture time. Six ideas captured as one-liners split cleanly on re-reading: the ones carrying a number or a named failure would survive a week, the ones naming a topic and promising a payoff would not, and the payoff was the part being lost. Promotion was the existing answer and is the wrong instrument — a bundle folder under `posts/` reads as a commitment to write the thing, and recording why an idea matters is the capture finishing itself, not the start of work. |
| 2026-08-13 | Batch capture and announced batch scope stated explicitly. First real use captured five ideas into a non-existent inbox and applied one scope across them — all reasonable, none sanctioned, so the next agent had no way to know which of those behaviours was intended. |
| 2026-08-11 | Created by feature 004. No prior art existed — `content-system/` had no inbox, so the pipeline had no front stage and stage counts could not be taken. |
