# Contract — ideas inbox format

**Source of truth for the idea inbox.** Where any other document disagrees, this file wins.

**Consumers**: `content-idea-capture` (writes), `content-post-writer` (reads when drafting from an idea, removes the row), `content-review` (counts waiting ideas as the front pipeline stage).

## File

`content-system/ideas.md`. One file. No folder, no index, no file per idea.

```markdown
# Ideas — inbox

| ID | Captured | Idea | Scope |
|---|---|---|---|
| 2026-08-11-a | 2026-08-11 | Intake automation broke in a way that taught me the process was the problem | areaOfFocus/product-craft |
| 2026-08-11-b | 2026-08-11 | Why "AI strategy" decks keep describing tools instead of work | |

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

**On promotion**: the row moves out of the table, and the new `backbone.md` records `from-idea:` with the ID and the original text. Traceability runs piece → idea; there is no backlink from the inbox into the piece, because the row no longer exists.

**A promoted idea can be abandoned.** Delete the bundle folder, or leave it — an unfinished folder with no locked artifact is a normal, visible state, and it is what the middle pipeline stage counts. Nothing forces it back into the inbox.

**On dropping**: the row moves to `## Dropped` with a date and a one-line reason. That section is prunable at any time and nothing reads it.

**Counting**: waiting ideas is the row count of the main table. Nothing else needs computing.

## Verify on write

**Every write is checked by reading it back.** After appending, moving, or removing a row, re-read the file and confirm the table still parses: header intact, one row per waiting idea, no row left in two places, no orphaned separator.

On failure, correct it and re-check **once**. On a second failure, say so plainly rather than leaving a broken inbox on disk. A malformed table here silently miscounts the pipeline's front stage, which is the one thing this file exists to make countable.

## What must not be built

No file per idea. No status column. No priority, tags, or scoring. No automatic promotion from idea to draft. No dependency on any inbox outside `content-system/` — in particular, not the outer workspace's `_editorial/_ideas/`.

**Growth trigger**: if waiting ideas routinely exceed ~50, the file stops being readable in one pass and wants splitting by scope. Not before.

## Revision history

| Date | Change |
|---|---|
| 2026-08-13 | Batch capture and announced batch scope stated explicitly. First real use captured five ideas into a non-existent inbox and applied one scope across them — all reasonable, none sanctioned, so the next agent had no way to know which of those behaviours was intended. |
| 2026-08-11 | Created by feature 004. No prior art existed — `content-system/` had no inbox, so the pipeline had no front stage and stage counts could not be taken. |
