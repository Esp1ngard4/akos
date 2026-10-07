# Contract — posts format

**Source of truth for how a piece is stored, tracked and indexed.** Where any other document disagrees, this file wins.

**Consumers**: `content-post-writer` (writes all of it), `content-plan-author` (writes the WBS Ref it creates into the plan, read here), `content-review` (reads piece status and the index for delivery, rate, pipeline counts and the mismatch check).

## Folder layout

One folder per **bundle**. A bundle is a set of artifacts that share one piece of thinking. **A bundle is a piece**: it is the unit that is committed, tracked and closed.

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

**`backbone.md` is never duplicated per artifact.** Angle, Six Questions, outline, claims, scope, status and the WBS Ref are properties of the thinking, not of a rendering.

## Source artifacts, never finals

For types this system cannot produce — `video`, `deck`, `poster` — the stored file is the **source that enables the final**: a storyboard, a deck skeleton, poster copy. Never a rendered `.mp4`, `.pptx`, or image. Production happens in external tools, and those formats are gitignored repo-wide in any case.

## `backbone.md`

Thin YAML frontmatter, then phase-ordered body sections.

```markdown
---
scope: areaOfFocus/product-craft    # optional until known
from-idea: 2026-08-11-a          # optional; the inbox entry this came from, with its text
wbs: Product craft#3             # required from promotion; see "WBS Ref"
status: drafting                 # drafting | locked | published | dropped
drafting: 2026-10-07             # the date each state was entered; only states reached
locked: 2026-10-12
published: 2026-10-14
dropped:
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

**Sections accrue in order as work progresses; absent sections are omitted, never left empty.** A backbone with only `## Idea` and `## Notes` is a valid, expected state — it is a piece in its first session.

**A bundle folder exists from promotion**, which is the moment a committed piece starts being worked. Promotion creates it, using the idea's own slug; drafting fills the rest in.

> **Not the assessment pipeline.** `.specify/assessments/` is a build/don't-build gate for capabilities, ending in a handoff to `/speckit-specify`. Content ideas are written, not built, and `content-system/` must stay self-contained. An idea *for this system* goes to assess; an idea *for a piece* stays here.

**Frontmatter date fields hold only the states reached.** A field for a state not reached is omitted, never left empty — the example shows them all only to name them.

## Piece status

Every piece carries one status, in its `backbone.md`, with the date it entered each state.

| Status | Entered when | Date field | The piece's WBS row |
|---|---|---|---|
| `drafting` | **Promotion**: the bundle folder is created. The WBS Ref is required from here | `drafting` | `Implementing` |
| `locked` | Every artifact named in `## Artifacts` is locked — its index row is written | `locked` | stays `Implementing` |
| `published` | Every artifact named in `## Artifacts` has a `Published` date in the index | `published` | `Done` |
| `dropped` | The author drops the piece. The reason is one line in `## Notes` | `dropped` | `Cancelled`, the reason as its closure note |

**`published` and `dropped` are final.** Once a piece reaches either, nothing about it needs keeping in line again.

**The WBS row moves with the piece, at the transition, and on the author's word.** Only three transitions touch the WBS — into `drafting`, `published` and `dropped`. The skill that makes the transition proposes the matching WBS change in one line and runs it when the author agrees. The WBS rule it serves is the same as this file's: a status never moves without its date. `locked` changes nothing in the WBS, because a finished piece that has not gone live is still work in progress there.

**A piece is not `published` until all its artifacts are.** The index keeps each artifact's own `Published` date; the piece's `published` date is the last of them.

**A missing `status` is read, never written back.** Bundles that predate this field carry none, and are not backfilled. Read it from the index: `published` when every artifact of the bundle has a `Published` date, `locked` when every artifact has an index row, `drafting` otherwise. A bundle with no `## Artifacts` and no index row reads as `drafting`.

**There is no `scheduled` state.** This system is not a publisher. Publishing is the author's own act, recorded after it happens.

## WBS Ref

The pointer from a piece to the WBS row that commits it, written `<scope>#<ID>` — `Product craft#3`, `P12 Website#42`. The same form a RAID entry uses for its `WBS Ref`.

- **`<scope>` is the register's own `meta.scope`**, exactly as written there. `<ID>` is the row's stable ID.
- **The row lives in the WBS of the project or area of focus that owns the goal the content serves** — the goal its plan names in `**Serves:**` ([`strategy-file-format.md`](strategy-file-format.md)).
- **A register is found by its shape, never by a configured path.** Search the workspace that holds `content-system/` — the enclosing repository, not `content-system/` itself, since registers live with the projects and areas that own them. Look for JSON files outside any `PreviousV/` folder whose `meta.kind` is `wbs-register`, and take the one whose `meta.scope` equals the Ref's scope. No match, or more than one, is reported to the author, never guessed.
- **One row per piece.** Cross-posting the same piece is not a row of its own. An artifact that takes effort of its own — a video made from its storyboard — may have a child row under the piece's row; the piece still carries the parent's Ref.

## Index

`content-system/posts/index.md`, one row per **artifact**, newest first.

```
| Date | Title | Type | Channel | Scope | Published | Link |
```

| Column | Rule |
|---|---|
| `Date` | The artifact's own date, not the bundle's. |
| `Title` | The artifact's title. Artifacts in a bundle usually differ. |
| `Type` | `article`, `short-post`, `carousel`, `video`, `deck`, `poster`. Open set. |
| `Channel` | `blog`, `linkedin`, `instagram`, `site`. Open set. One value per row. |
| `Scope` | Strategy path form — `areaOfFocus/product-craft`, not `AF.6 Widgets`. This is what joins a post to its strategy. A comma-separated list is permitted; a piece may serve more than one scope. |
| `Published` | Date the author recorded publication, or blank. **Never inferred, never derived from the lock signal.** Written by the record-publication action when the author says the artifact is live. |
| `Link` | Relative link to the artifact file. |

**The index is a cache for retrieval, not a browsing UI.** Each bundle's `backbone.md` is the source of truth. Rows are written in the same turn an artifact is locked, never deferred.

**Produced is not published.** A row with a `Link` and no `Published` date means the source artifact is finished and has not gone live. That state is normal, expected, and must never be reported as delivered-to-audience.

## Why posts stay flat rather than foldered by scope

Decided 2026-08-08, unchanged by bundling. A post can serve more than one scope; scope can be assigned wrongly and a cell is cheaper to fix than a move; chronology is the primary access pattern; volume does not justify a tree; and a scope tree would be a second index that drifts from this one. Portability also argues for flat — `posts/` copies cleanly, whereas a scope tree bakes one instance's taxonomy into the directory structure.

**Trigger to revisit**: several hundred posts, or a single scope operating as its own publication with a separate audience and cadence.

## Verify on write

**Every write is checked by reading it back.** After writing a `backbone.md` or an index row, re-read the file and apply the rules above to your own output — frontmatter fields, a date for the current status, section order, the index's seven columns, the artifact filename pattern.

On failure, correct it and re-check **once**. On a second failure, report it plainly — *"I couldn't write this in a way I can read back; here's what I tried, please check it"* — and never leave an unverified file on disk.

This is not a schema validator and must not become one. It is the writer applying, to its own output, the rule it already applies when reading.

## What must not be built

No parser or schema-validation library. No per-scope folder tree. No second index. No detection of publication — the `Published` column is author-recorded, and automating it would require the analytics integration that is permanently out of scope. No copy of the WBS row's dates, effort or sprint in this system — they are read through the WBS Ref when a view needs them.

## Revision history

| Date | Change |
|---|---|
| 2026-10-06 | Pieces run on the WBS. A bundle is a piece; its `backbone.md` carries `status` (`drafting`, `locked`, `published`, `dropped`), a date per state reached, and the WBS Ref of the row that commits it. The WBS row moves at three transitions, on the author's word. A missing status is read from the index, so older bundles need no backfill. The `commitments:` pointer and the index's `Commitment` column are retired: a commitment was a plan row identified by its date, and the WBS row now carries both; the column was blank on all seven rows. |
| 2026-08-11 | Created by feature 004. Bundle layout replaces one `draft.md` per folder, resolving the long-standing defect where the index permitted `Format: both` but only one artifact could be stored. Index columns `Format` → `Type` + `Channel`, `Scope` moved to path form, `Commitment` and `Published` added. Seven existing posts migrated. |
