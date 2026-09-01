# Contract — posts format

**Source of truth for how a finished piece is stored and indexed.** Where any other document disagrees, this file wins.

**Consumers**: `content-post-writer` (writes both), `content-review` (reads the index for delivery and pipeline counts).

## Folder layout

One folder per **bundle**. A bundle is a set of artifacts that share one piece of thinking.

```
content-system/posts/YYYY-MM-DD-slug/
  backbone.md              <- one per bundle, always
  blog-article.md
  linkedin-short-post.md
  instagram-video.md
```

- The folder date is the bundle's first artifact date. Individual artifacts carry their own dates in the index.
- Artifacts are named `<channel>-<type>.md`. Both dimensions are required, including when a bundle has one artifact — two LinkedIn artifacts of different types, or one type across two channels, are ordinary cases that either half alone cannot distinguish.
- A bundle with one artifact is the normal case. Nothing about the layout changes.

**`backbone.md` is never duplicated per artifact.** Angle, Six Questions, outline, claims, scope and commitment pointers are properties of the thinking, not of a rendering.

## Source artifacts, never finals

For types this system cannot produce — `video`, `deck`, `poster` — the stored file is the **source that enables the final**: a storyboard, a deck skeleton, poster copy. Never a rendered `.mp4`, `.pptx`, or image. Production happens in external tools, and those formats are gitignored repo-wide in any case.

## `backbone.md`

Thin YAML frontmatter, then phase-ordered body sections.

```markdown
---
scope: areaOfFocus/product-craft    # optional until known
from-idea: 2026-08-11-a          # optional; the inbox entry this came from, with its text
commitments:                      # optional; one line per artifact credited to a plan row
  - areaOfFocus/product-craft/Lab in the open/2026-09-02
---

## Idea               <- the original capture, verbatim, when promoted from the inbox
## Notes              <- raw material; exists from promotion onward, before any angle
## Angle
## Audience
## Artifacts          <- type, channel, and target length per artifact in this bundle
## Persona
## Six Questions
## Outline
## Claims            <- only when the Phase 5 extraction is non-empty; omitted, never empty
```

**Sections accrue in order as work progresses; absent sections are omitted, never left empty.** A backbone with only `## Idea` and `## Notes` is a valid, expected state — it is an idea being developed, and it is what the middle pipeline stage counts.

**A bundle folder may exist before an angle is settled.** Promotion from the inbox creates it, using the idea's own slug; drafting fills the rest in. This is the home for refining an idea that is more than a one-liner and not yet a piece.

> **Not the assessment pipeline.** `.specify/assessments/` is a build/don't-build gate for capabilities, ending in a handoff to `/speckit-specify`. Content ideas are written, not built, and `content-system/` must stay self-contained. An idea *for this system* goes to assess; an idea *for a piece* stays here.

`commitments` is written at the moment a surfaced commitment is **accepted**, not at lock time. It is the direct pointer write-back reads later.

## Index

`content-system/posts/index.md`, one row per **artifact**, newest first.

```
| Date | Title | Type | Channel | Scope | Commitment | Published | Link |
```

| Column | Rule |
|---|---|
| `Date` | The artifact's own date, not the bundle's. |
| `Title` | The artifact's title. Artifacts in a bundle usually differ. |
| `Type` | `article`, `short-post`, `carousel`, `video`, `deck`, `poster`. Open set. |
| `Channel` | `blog`, `linkedin`, `instagram`, `site`. Open set. One value per row. |
| `Scope` | Strategy path form — `areaOfFocus/product-craft`, not `AF.6 Career`. This is what joins a post to its strategy. A comma-separated list is permitted; a piece may serve more than one scope. |
| `Commitment` | The plan commitment satisfied, as `<plan name>/<date>`, or blank. Blank is normal. |
| `Published` | Date the author recorded publication, or blank. **Never inferred, never derived from the lock signal.** |
| `Link` | Relative link to the artifact file. |

**The index is a cache for retrieval, not a browsing UI.** Each bundle's `backbone.md` is the source of truth. Rows are written in the same turn an artifact is locked, never deferred.

**Produced is not published.** A row with a `Link` and no `Published` date means the source artifact is finished and has not gone live. That state is normal, expected, and must never be reported as delivered-to-audience.

## Why posts stay flat rather than foldered by scope

Decided 2026-08-08, unchanged by bundling. A post can serve more than one scope; scope can be assigned wrongly and a cell is cheaper to fix than a move; chronology is the primary access pattern; volume does not justify a tree; and a scope tree would be a second index that drifts from this one. Portability also argues for flat — `posts/` copies cleanly, whereas a scope tree bakes one instance's taxonomy into the directory structure.

**Trigger to revisit**: several hundred posts, or a single scope operating as its own publication with a separate audience and cadence.

## Verify on write

**Every write is checked by reading it back.** After writing a `backbone.md` or an index row, re-read the file and apply the rules above to your own output — frontmatter fields, section order, the index's eight columns, the artifact filename pattern.

On failure, correct it and re-check **once**. On a second failure, report it plainly — *"I couldn't write this in a way I can read back; here's what I tried, please check it"* — and never leave an unverified file on disk.

This is not a schema validator and must not become one. It is the writer applying, to its own output, the rule it already applies when reading.

## What must not be built

No parser or schema-validation library. No per-scope folder tree. No second index. No detection of publication — the `Published` column is author-recorded, and automating it would require the analytics integration that is permanently out of scope.

## Revision history

| Date | Change |
|---|---|
| 2026-08-11 | Created by feature 004. Bundle layout replaces one `draft.md` per folder, resolving the long-standing defect where the index permitted `Format: both` but only one artifact could be stored. Index columns `Format` → `Type` + `Channel`, `Scope` moved to path form, `Commitment` and `Published` added. Seven existing posts migrated. |
