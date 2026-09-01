# Contract — strategy file format

**Source of truth for the strategy file format.** Where any other document disagrees, this file wins.

**Consumers**: `content-strategy-author`; plan authoring, drafting resolution, review, and the roadmap view; `content-post-writer`'s scope and plan resolution. Several agents must interpret the same file identically without sharing a parser.

**Skills embed the four house headers inline** — they are short and must never be wrong. Everything longer, principally the commitment table, is read from here rather than copied.

## Location

```
content-system/strategies/<category>/<slug>.md     # category ∈ projects | areaOfFocus | areaOfInterest
content-system/strategies/default.md               # catch-all, no category subfolder
```

Categories are exactly these three. No fourth category. No index file — scopes are enumerated by walking the folder.

## Resolving a scope

**Scope candidates come from walking `content-system/strategies/`.** That is the only source of scope names.

**No external registry is read, required, or degraded around** — not a notebook tree, not a sibling system, not a calendar or task manager. An earlier design treated such a read as a soft dependency with a fallback for when it was absent; the fallback was always going to be the only path that ran, and a dependency whose degradation is its normal case is worse than no dependency.

**Scope identity is always the path form** — `areaOfFocus/product-craft` — in strategy frontmatter, index rows, idea rows, and backbone frontmatter. Display forms like "AF.6 Career" belong in prose only, never in a field that has to join.

**When candidates are enumerable, offer them.** A scope question is a pick-list of the scopes that have a strategy file, plus `default` and an escape option — never a blank prompt.

**A scope with no strategy file is normal**, not an error. Every reader degrades to behaviour that works without one.

## Shape

```markdown
---
scope: areaOfFocus/product-craft       # or projects/<slug>, areaOfInterest/<slug>, or "default"
created: YYYY-MM-DD
---

## Mission
One sentence.

## Pillars
- Pillar name — one line each, 3–4 max

## Credibility signals
- Optional. Things the author can actually surface: work, artifacts, outcomes, failures, constraints.

## Topics to avoid
- Optional.

## Plan: <plan name>
**Audience:** ...
**Objective (Know/Feel/Do):** ...
**Shape:** campaign | always-on
**Stage:** refining | active                     <!-- campaign only; refining = a backlog, nothing scored -->
**Pillars in play:** Pillar name, Pillar name     <!-- matched against house pillar names; never comma-split -->
**Channel:** blog, linkedin                      <!-- one or more; the set this plan draws from -->
**End date:** YYYY-MM-DD                         <!-- campaign only; required once active, optional while refining -->
**Cadence:** ~1/week                             <!-- always-on only, free text -->
**Monthly target:** blog 2, linkedin 2           <!-- always-on only, optional; <channel> <integer> per channel -->
**Started:** YYYY-MM                             <!-- always-on only; the month the rate begins. Asked, current month offered -->

| Date | Working title | Type | Channel | Pillar | Bundle | Status | Piece |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | ... | article | blog | Pillar name | | pending | |

...0..n Plan sections, each self-contained, all after the four sections above
```

## Rules

**Frontmatter is machine-generated and not the source of truth.** It makes the file self-describing if opened detached from its path. Regenerate on every write. Parsing never depends on it — the path already encodes scope.

**Required for the file to exist at all**: `## Mission`, and at least one entry under `## Pillars`. A file with neither is an empty stub, not a strategy, and must not be created. `Credibility signals` and `Topics to avoid` are optional.

**Section order is fixed.** All four prose sections precede every `## Plan:` section, because a Plan section runs from `^## Plan: ` to the next `^## `. Reordering makes plans invisible to enumeration, with no error raised.

**Headers are exact literal strings**: `## Mission`, `## Pillars`, `## Credibility signals`, `## Topics to avoid`. Not fuzzy, not positional, not case-insensitive. Writing them correctly is the agent's job, never the author's.

**Nothing parses inside a Mission sentence or a Pillar line.** Only the headers around them matter.

**No audience anywhere in the house.** Audience belongs to a `## Plan:` section. One house per scope; audience varies beneath it.

**Every write is verified by re-reading.** After writing, re-read the file and apply the rules above to your own output. On failure, correct once and re-check. On a second failure, report it to the author. Never leave an unverified file on disk.

## Plan sections

Authored by a separate flow from the house, never in the same interview.

- Begin at `^## Plan: `, run to the next `^## `.
- Fields by exact bold label at line start: `**Audience:**`, `**Objective (Know/Feel/Do):**`, `**Shape:**`, `**Stage:**`, `**Pillars in play:**`, `**Channel:**`, `**End date:**`, `**Cadence:**`, `**Monthly target:**`, `**Started:**`.
- `**Stage:**` is campaign only, exactly `refining` or `active`, and **absent means `active`** — every campaign written before this field existed was a commitment, and reading a missing value as a backlog would silently empty the denominator.
- `**Channel:**` at plan level is one or more values — the set the plan draws from, not a constraint each commitment inherits.
- `**Pillars in play:**` is **resolved against the scope's own `## Pillars` names, never by splitting on commas.** Pillar names routinely contain commas — *"The unit of redesign is the team, not the task"* — so a comma split yields fragments that match nothing, and does it silently: the plan still resolves, it just appears to have no valid pillars. Read the house pillar list first, then find which of those names appear in the field, longest name first. The same applies to a commitment row's `Pillar` cell, resolved against that plan's own list.
- A commitment table is present only when `Shape: campaign`, and is located by its literal header row, never by position.
- `**Monthly target:**` is always-on only and optional. Format is `<channel> <integer>`, comma-separated, channels drawn from that plan's own `**Channel:**` set — `site 2, linkedin 2`. It is the denominator that makes a rhythm scoreable: without it an always-on plan can be counted but not scored, and **a target is never parsed out of the prose `**Cadence:**` line**. `~2/month (floor: 1/month)` holds two numbers and a tilde; picking one would be inventing the standard the author is judged against.
- `**Started:**` is always-on only, `YYYY-MM`, and **asked**, with the current month offered as the default. **Months before it are counted, never scored.** Without it, a review reaching back over a scope's history scores every month against a target that did not exist then, manufacturing a run of misses out of work that predates the commitment. It is asked rather than system-chosen because the system knows today's date, which is not the same fact as when the author intends the rhythm to begin — a plan written on the 28th to start next month would otherwise be scored, and missed, for a month it never claimed.
- **A monthly target scores against `Published`, not against artifacts produced.** A finished piece sitting unpublished has not met a public cadence. This is the same produced-vs-published line the review skill holds everywhere else.
- `Status` is exactly `pending` or `delivered`. Nothing else is ever written by the system. `missed` is a read-time inference — date passed, still `pending` — and remains available as a manual edit the system reads but never authors.

### Commitment table

```
| Date | Working title | Type | Channel | Pillar | Bundle | Status | Piece |
```

| Column | Rule |
|---|---|
| `Date` | **Required.** A row without one cannot be scored. |
| `Working title` | **Required.** Surfaced as the default angle when the row comes due. |
| `Type` | **Required.** What the artifact is: `article`, `short-post`, `carousel`, `video`, `deck`, `poster`. Open set. |
| `Channel` | **Required.** Where it goes: `blog`, `linkedin`, `instagram`, `site`. Open set. One value per row — cross-posting is two rows, because each is independently missable. |
| `Pillar` | One of the plan's own `Pillars in play`, not the whole strategy's pillar list. |
| `Bundle` | Optional shared label grouping artifacts delivered together. Blank for standalone artifacts. Set at creation, not inferred at delivery, because a bundle must be groupable while every row is still `pending`. |
| `Status` | `pending` or `delivered`. System-written only. |
| `Piece` | Relative link to the finished source artifact, filled at write-back. Blank until then. |

**Type and channel are independent and neither may be inferred from the other.** A video can go to LinkedIn or Instagram; a carousel and an article are both `linkedin`. Combinations are not validated — they are not enumerable in advance.

**For types this system cannot produce** — video, deck, poster — `Piece` links the **source artifact** that enables the final: a storyboard, a deck skeleton, poster copy. Never a rendered `.mp4`, `.pptx`, or image.

**A row missing any required column must not be written** — *in an `active` plan*. Ask for the missing part instead. A commitment that cannot be scored pass/fail is an intention, not a commitment, and the delivered fraction is only meaningful if every row in the denominator could actually have been missed.

## Refining — a campaign that is still a backlog

`Stage: refining` exists because the thinking that connects several pieces has to live somewhere before any of them is promised. Without it, the only home for an arc is a plan full of dates the author does not believe, and the fiction spreads into everything that reads it.

In a refining plan:

- **`Working title` is the only required cell.** Date, type, channel and pillar may all be blank — they are what refinement is *for*.
- **`End date` is optional.** A backlog has no deadline.
- **Nothing is scored.** No delivered fraction, no missed rows, no contribution to any denominator. A candidate cannot be missed, because nothing was promised.
- **A row may point at an already-published piece** via `Piece`, with `Date` blank, so the arc reads whole. **Such a row is never scored, in either stage** — counting work that predates the promise would inflate the fraction with credit for something that could not have failed.

**A candidate does not replace the idea it came from.** The inbox row stays where it is. An inbox row carries what a plan table cannot: the capture date, the author's unsharpened wording, and — when it dies — the reason. A candidate row carries a working title and a place in an arc. Naming an idea as a candidate is therefore not a fourth exit from the inbox; the idea leaves only by promotion or dropping, exactly as before. **Candidates are not a pipeline stage** and are never added to the stage counts.

**Activation is a deliberate act, and it is the grooming pass.** Moving `refining` → `active` requires, for every row: either it becomes fully scoreable — date, working title, type, channel — or it leaves the table, or it is explicitly kept as an already-published context row. `End date` becomes required. A plan cannot activate with a half-specified row in it, because the moment it activates the denominator is real.

**Activation is one-way in normal use.** A plan that has started making promises does not quietly become a backlog again; the author is free to hand-edit it back, and the system will read that, but no action offers it — reverting would erase the missed rows that are the whole point of having committed.

**Changing the header row is a migration, not an edit**, once any campaign plan exists on disk. Readers match it literally.

## What must not be built

No parser or schema-validation library — verification is the agent re-applying these rules to its own output. No strategy index. No cross-scope inheritance. No plan-file splitting until a single scope runs more than three concurrent plans.

## Revision history

| Date | Change |
|---|---|
| 2026-08-13 | Campaigns gained `**Stage:** refining \| active`. Author's proposal, and it closed two gaps at once: nothing in the system held thinking that spans several pieces, and nothing convened an accumulating inbox. A refining campaign is a backlog; activating it is the grooming pass. Absent means `active`, so plans written before this field keep their denominator. |
| 2026-08-12 | Always-on plans gained `**Started:**`, the month from which a monthly target applies. Found when the first real plan met six posts published across the eighteen months before it existed: without a start, reviewing that history scores it against a target nobody had set. Months before `Started` are counted, never scored. First specified as system-written from today's date; corrected the same day to asked-with-a-default, because today's date is not the same fact as when the author intends to begin. |
| 2026-08-12 | Always-on plans gained an optional `**Monthly target:**`. A cadence in prose could be read but never scored, which left always-on as the shape you pick when you want a rhythm and accept that nobody can tell whether you held it. The target is the denominator; the prose cadence stays for nuance and is never parsed. |
| 2026-08-12 | `Pillars in play` is resolved by matching house pillar names, not by comma-splitting. Found while writing the first plan on disk, whose pillar names contain commas. No separator change and no migration — the values were always correct; only the reading rule was wrong. |
| 2026-08-11 | Moved here from `specs/003-strategy-file-authoring/contracts/`. The format is executed at runtime by the skills beside it, so it ships with them; the spec records decisions, the system carries what it needs to run. Resolved three competing copies — this file, engineering-brief §4.1, and an inline copy in the skill — down to one owner. |
| 2026-08-11 | Feature 004: commitment table gained `Type`, `Channel`, and `Bundle`. Previous header was `\| Date \| Working title \| Pillar \| Status \| Piece \|`. Made while zero plans existed on disk, so no migration was needed. |
| 2026-08-11 | Feature 004: plan-level `**Channel:**` became a multi-value set over an open list, replacing single-valued `blog \| linkedin \| both`. |
| 2026-08-09 | Created for feature 003, restating engineering-brief §4.1. |
