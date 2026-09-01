# Contract — ideas inbox format

**Source of truth for the idea inbox.** Where any other document disagrees, this file wins.

**Consumers**: `content-idea-capture` (writes), `content-post-writer` (reads when drafting from an idea, removes the row, carries its context into the backbone), `content-review` (counts waiting ideas as the front pipeline stage).

## File

`content-system/ideas.md`. One file. No folder, no index, no file per idea.

```markdown
# Ideas — inbox

| ID | Captured | Idea | Scope |
|---|---|---|---|
| 2026-08-11-a | 2026-08-11 | Intake automation broke in a way that taught me the process was the problem | areaOfFocus/product-craft |
| 2026-08-11-b | 2026-08-11 | Why "AI strategy" decks keep describing tools instead of work | |

## Context

### 2026-08-11-a
The rollback took nine minutes and the postmortem took three weeks. Worth
saying because everyone reaches for a better script first, and the script
was never the problem.

## Dropped

| ID | Captured | Idea | Dropped | Why |
|---|---|---|---|---|
```

## Rules

**The table holds waiting ideas only.** An idea leaves the table when it is **promoted** or dropped. There is no status column, because "what is waiting" must be a read, not a filter — and a stale `done` row silently inflates the pipeline count.

**Promotion is the moment an idea starts being worked**, and it does not require an angle, a plan, or a commitment to finish. It creates a bundle folder with a `backbone.md` carrying the idea text and whatever notes exist — see [`posts-format.md`](posts-format.md). That folder is where refinement lives: notes, the angle once it settles, Six Questions, outline.

This is deliberate: an idea being actively developed is neither "waiting" nor "written", and without promotion it would have to sit in the inbox pretending to be untouched. The three pipeline stages depend on the distinction being real.

**`ID` is `YYYY-MM-DD-<letter>`**, the letter incrementing within a day. It exists so the author can say "the second one" without ambiguity while the idea waits. It is not a permanent identifier and nothing resolves it after the row leaves.

**`Scope` is optional** and uses the strategy path form when present. An idea captured with no scope is normal — capture must work when no strategy file exists anywhere. A scope the author has just stated may be applied across a batch **provided the write says so**; applied silently it is an inference, and inference is what every other part of this system refuses.

**A batch is one capture.** Several ideas in one message are appended in one write with letters incrementing across them, and confirmed once. Splitting a batch into an exchange per idea defeats the ten-second promise the format exists to keep.

**`Idea` is one line, in the author's words.** Capture does not interview, sharpen, or expand. That work belongs to drafting, and doing it here would turn a ten-second action into a conversation.

**`## Context` is optional, author-supplied, and offered rather than asked for.** A `### <ID>` block holds whatever the author volunteers about why an idea is worth writing — the number behind it, the failure that prompted it, who it is for. Unbounded, and usually absent.

Three rules make it safe:

- **The skill never asks for it.** No "would you like to add context?", no prompt after a capture. Asking is the interview this format exists to prevent, and it would cost the ten-second promise on every capture to serve the minority that carry a block.
- **The skill never writes one itself.** An inferred reason is a fabricated one. If the author did not say it, there is no block.
- **It arrives in the same turn as the row, or later, by the author saying so.** A batch with context on one of five ideas is still one capture and one write.

The reason it lives here and not in a promoted `backbone.md`: a bundle folder under `posts/` reads as a commitment to write the thing, and recording why an idea matters is not that. It is the capture finishing itself. An idea may carry a full paragraph of context and still be waiting, untouched, for a year.

**Context is not a triage field.** It holds the author's reason, not a rating of it. See [What must not be built](#what-must-not-be-built).

**On promotion**: the row moves out of the table, and the new `backbone.md` records `from-idea:` with the ID and the original text. Traceability runs piece → idea; there is no backlink from the inbox into the piece, because the row no longer exists.

**A `### <ID>` block moves with its row.** On promotion its text becomes the backbone's opening `## Notes`; on dropping it goes with the row and may be pruned. It is never left behind, and there are never two live copies — the inbox block is the seed, `## Notes` is where it grows once the idea is being worked.

**A promoted idea can be abandoned.** Delete the bundle folder, or leave it — an unfinished folder with no locked artifact is a normal, visible state, and it is what the middle pipeline stage counts. Nothing forces it back into the inbox.

**On dropping**: the row moves to `## Dropped` with a date and a one-line reason. That section is prunable at any time and nothing reads it.

**Counting**: waiting ideas is the row count of the main table. Nothing else needs computing. **`## Context` blocks are never counted** — an idea with a block and an idea without one are both one waiting idea, and a count that treated them differently would be scoring, which this file does not do.

## Verify on write

**Every write is checked by reading it back.** After appending, moving, or removing a row, re-read the file and confirm the table still parses: header intact, one row per waiting idea, no row left in two places, no orphaned separator, and **every `### <ID>` block matching a row that is still in the table** — a block whose row was promoted or dropped is context that was supposed to travel and did not.

On failure, correct it and re-check **once**. On a second failure, say so plainly rather than leaving a broken inbox on disk. A malformed table here silently miscounts the pipeline's front stage, which is the one thing this file exists to make countable.

## What must not be built

No file per idea. No status column. No priority, tags, or scoring. No automatic promotion from idea to draft. No dependency on any inbox outside `content-system/` — in particular, not the outer workspace's `_editorial/_ideas/`.

**No required context, and no prompt for it.** `## Context` is the author volunteering a reason; the moment it is asked for on every capture it has become the interview, whatever it is called. A capture with no block is complete, not unfinished, and nothing may render it as missing.

**Growth trigger**: if waiting ideas routinely exceed ~50, the file stops being readable in one pass and wants splitting by scope. Not before.

## Revision history

| Date | Change |
|---|---|
| 2026-09-01 | Optional `## Context` blocks added. Six ideas captured as one-liners on 2026-09-01 split cleanly on re-reading: the ones carrying a number or a named failure would survive a week, the ones naming a topic and promising a payoff would not, and the payoff was the part being lost. Promotion was the existing answer and is the wrong instrument — a bundle folder under `posts/` reads as a commitment to write the thing, and recording why an idea matters is the capture finishing itself, not the start of work. |
| 2026-08-13 | Batch capture and announced batch scope stated explicitly. First real use captured five ideas into a non-existent inbox and applied one scope across them — all reasonable, none sanctioned, so the next agent had no way to know which of those behaviours was intended. |
| 2026-08-11 | Created by feature 004. No prior art existed — `content-system/` had no inbox, so the pipeline had no front stage and stage counts could not be taken. |
