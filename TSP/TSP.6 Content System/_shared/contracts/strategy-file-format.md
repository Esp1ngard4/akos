# Contract — strategy file format

**Source of truth for the strategy file format.** Where any other document disagrees, this file wins.

**Consumers**: `content-strategy-author`; plan authoring, drafting resolution, review, and the roadmap view; `content-post-writer`'s scope and plan resolution. Several agents must interpret the same file identically without sharing a parser.

**Committing, scheduling and closing a piece happen in the WBS, not here.** This file holds what is editorial: the house, each plan's audience, objective, the goal it serves, its rate, and the arc of pieces a campaign is made of. When a piece is due, how much effort it takes and whether it is done are fields of its WBS row, reached through the WBS Ref ([`posts-format.md`](posts-format.md)). Nothing here copies them.

**Skills embed the four house headers inline** — they are short and must never be wrong. Everything longer, principally the arc table, is read from here rather than copied.

## Location

```
content-system/strategies/<category>/<slug>.md     # category ∈ projects | areaOfFocus | areaOfInterest
content-system/strategies/default.md               # catch-all, no category subfolder
```

Categories are exactly these three. No fourth category. No index file — scopes are enumerated by walking the folder.

## Resolving a scope

**Scope candidates come from walking `content-system/strategies/`.** That is the only source of scope names.

**No external registry is read, required, or degraded around** — not a notebook tree, not a sibling system, not a calendar or task manager. An earlier design treated such a read as a soft dependency with a fallback for when it was absent; the fallback was always going to be the only path that ran, and a dependency whose degradation is its normal case is worse than no dependency.

**Scope identity is always the path form** — `areaOfFocus/product-craft` — in strategy frontmatter, index rows, idea rows, and backbone frontmatter. Display forms like "AF.6 Widgets" belong in prose only, never in a field that has to join.

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
**Serves:** OBJ-3 Grow the audience                <!-- the goal this plan advances; see "Serves" below -->
**Audience:** ...
**Objective (Know/Feel/Do):** ...
**Shape:** campaign | always-on
**Pillars in play:** Pillar name, Pillar name     <!-- matched against house pillar names; never comma-split -->
**Channel:** blog, linkedin                      <!-- one or more; the set this plan draws from -->
**Cadence:** ~1/week                             <!-- always-on only, free text -->
**Monthly target:** blog 2, linkedin 2           <!-- always-on only, optional; <channel> <integer> per channel -->
**Started:** YYYY-MM                             <!-- always-on only; the month the rate begins. Asked, current month offered -->

| Working title | Type | Channel | Pillar | Bundle | WBS | Piece |
|---|---|---|---|---|---|---|
| ... | article | blog | Pillar name | | Product craft#3 | |

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
- Fields by exact bold label at line start: `**Serves:**`, `**Audience:**`, `**Objective (Know/Feel/Do):**`, `**Shape:**`, `**Pillars in play:**`, `**Channel:**`, `**Cadence:**`, `**Monthly target:**`, `**Started:**`.
- `**Serves:**` names the goal the plan advances; see [Serves](#serves). Every plan should carry one. A plan without it is read as written and flagged by the review.
- **Labels no longer written, still read:** `**Stage:**` and `**End date:**` belonged to the campaign lifecycle the WBS now carries. A plan that still has them is read without error and the values are ignored. No writer emits them.
- `**Channel:**` at plan level is one or more values — the set the plan draws from, not a constraint each commitment inherits.
- `**Pillars in play:**` is **resolved against the scope's own `## Pillars` names, never by splitting on commas.** Pillar names routinely contain commas — *"The unit of redesign is the team, not the task"* — so a comma split yields fragments that match nothing, and does it silently: the plan still resolves, it just appears to have no valid pillars. Read the house pillar list first, then find which of those names appear in the field, longest name first. The same applies to an arc row's `Pillar` cell, resolved against that plan's own list.
- An arc table is present only when `Shape: campaign`, and is located by its literal header row, never by position.
- `**Monthly target:**` is always-on only and optional. Format is `<channel> <integer>`, comma-separated, channels drawn from that plan's own `**Channel:**` set — `site 2, linkedin 2`. It is the denominator that makes a rhythm scoreable: without it an always-on plan can be counted but not scored, and **a target is never parsed out of the prose `**Cadence:**` line**. `~2/month (floor: 1/month)` holds two numbers and a tilde; picking one would be inventing the standard the author is judged against.
- `**Started:**` is always-on only, `YYYY-MM`, and **asked**, with the current month offered as the default. **Months before it are counted, never scored.** Without it, a review reaching back over a scope's history scores every month against a target that did not exist then, manufacturing a run of misses out of work that predates the commitment. It is asked rather than system-chosen because the system knows today's date, which is not the same fact as when the author intends the rhythm to begin — a plan written on the 28th to start next month would otherwise be scored, and missed, for a month it never claimed.
- **A monthly target scores against `Published`, not against artifacts produced.** A finished piece sitting unpublished has not met a public cadence. This is the same produced-vs-published line the review skill holds everywhere else.

### Serves

**Content serves a goal, and the goal belongs to a project or an area of focus.** `**Serves:**` names that goal in the author's own words or identifier, such as `OBJ-3 Grow the audience`. It decides which WBS a piece's row belongs in: the register of the project or area that owns the goal.

- **Free text, one goal.** A plan serving two goals is two plans, or a goal not yet decided.
- **Asked when the plan is written, never inferred.** The system does not read a goals system to fill it in.
- **A plan that cannot name its goal is the finding**, not a gap to paper over. The review lists plans with no `**Serves:**` and says so in one line.

### Arc table

A campaign's pieces, one row each: the arc read whole, whether a piece is a candidate, committed, or already out.

```
| Working title | Type | Channel | Pillar | Bundle | WBS | Piece |
```

| Column | Rule |
|---|---|
| `Working title` | **Required.** Surfaced as the default angle when the piece is worked. |
| `Type` | What the artifact is: `article`, `short-post`, `carousel`, `video`, `deck`, `poster`. Open set. **Required once committed.** |
| `Channel` | Where it goes: `blog`, `linkedin`, `instagram`, `site`. Open set. One value per row. **Required once committed.** |
| `Pillar` | One of the plan's own `Pillars in play`, not the whole strategy's pillar list. Optional. |
| `Bundle` | Optional shared label grouping artifacts delivered together. Rows sharing a label are one piece and share one WBS Ref. |
| `WBS` | The WBS Ref of the row that commits the piece, or blank. See [`posts-format.md`](posts-format.md). |
| `Piece` | Relative link to the piece's bundle folder, once it exists. Blank until then. |

**Type and channel are independent and neither may be inferred from the other.** A video can go to LinkedIn or Instagram; a carousel and an article are both `linkedin`. Combinations are not validated: they are not enumerable in advance.

**For types this system cannot produce** (video, deck, poster) the piece holds the **source artifact** that enables the final: a storyboard, a deck skeleton, poster copy. Never a rendered `.mp4`, `.pptx`, or image.

## Candidates, commitments and context

A row's state is read from two cells, never stored:

| `WBS` | `Piece` | The row is |
|---|---|---|
| blank | blank | **a candidate**: a piece the arc may hold, promised to no one |
| set | any | **committed**: its WBS row says when, how much, and whether it is done |
| blank | set | **context**: a piece published before the arc existed, there so the arc reads whole |

**Committing a candidate is creating its WBS row** and writing the Ref into the `WBS` cell, in one action, on the author's word. `Type` and `Channel` must be known by then; ask for them rather than commit without them. There is no plan-level activation: each piece is committed on its own, at planning or when pulled in, where the rest of the author's work is committed too.

**Dropping a candidate removes its row.** Candidates are allowed to die. **A committed piece dropped before it is started** (`Piece` blank) also leaves the arc, and its WBS row is `Cancelled` with the reason; nothing was written, so the WBS row is the whole record. **A piece dropped after it started** keeps its row: its `backbone.md` reads `dropped`, and its WBS row is `Cancelled`.

**A candidate does not replace the idea it came from.** The inbox entry stays where it is. An inbox row carries what a plan table cannot: the capture date, the author's unsharpened wording, and, when it dies, the reason. A candidate row carries a working title and a place in an arc. Naming an idea as a candidate is therefore not a fourth exit from the inbox; the idea leaves only by promotion or dropping, exactly as before. **Candidates are not a pipeline stage** and are never added to the stage counts.

**Changing the header row is a migration, not an edit**, once any campaign plan exists on disk. Readers match it literally.

## What must not be built

No parser or schema-validation library — verification is the agent re-applying these rules to its own output. No strategy index. No cross-scope inheritance. No plan-file splitting until a single scope runs more than three concurrent plans. No dates, effort, sprint or done-state in an arc row: the WBS row holds them, and a copy here would drift.

## Revision history

| Date | Change |
|---|---|
| 2026-10-06 | Pieces are committed in the WBS. Plans gained `**Serves:**`, the goal they advance, which decides the WBS a piece's row lives in. The commitment table became the **arc table**: `Date` and `Status` gave way to `WBS`, the Ref of the row that commits the piece. `**Stage:**`, `**End date:**`, activation and the `pending`/`delivered`/`missed` scoring retired: when, whether and done are WBS fields now. A row is a candidate, committed or context by which of `WBS` and `Piece` is set. Old labels are read and ignored, never written. Migration: the one campaign on disk was at `refining` with six undated candidates, so only its header changes. |
| 2026-08-13 | Campaigns gained `**Stage:** refining \| active`. Author's proposal, and it closed two gaps at once: nothing in the system held thinking that spans several pieces, and nothing convened an accumulating inbox. A refining campaign is a backlog; activating it is the grooming pass. Absent means `active`, so plans written before this field keep their denominator. |
| 2026-08-12 | Always-on plans gained `**Started:**`, the month from which a monthly target applies. Found when the first real plan met six posts published across the eighteen months before it existed: without a start, reviewing that history scores it against a target nobody had set. Months before `Started` are counted, never scored. First specified as system-written from today's date; corrected the same day to asked-with-a-default, because today's date is not the same fact as when the author intends to begin. |
| 2026-08-12 | Always-on plans gained an optional `**Monthly target:**`. A cadence in prose could be read but never scored, which left always-on as the shape you pick when you want a rhythm and accept that nobody can tell whether you held it. The target is the denominator; the prose cadence stays for nuance and is never parsed. |
| 2026-08-12 | `Pillars in play` is resolved by matching house pillar names, not by comma-splitting. Found while writing the first plan on disk, whose pillar names contain commas. No separator change and no migration — the values were always correct; only the reading rule was wrong. |
| 2026-08-11 | Moved here from `specs/003-strategy-file-authoring/contracts/`. The format is executed at runtime by the skills beside it, so it ships with them; the spec records decisions, the system carries what it needs to run. Resolved three competing copies — this file, engineering-brief §4.1, and an inline copy in the skill — down to one owner. |
| 2026-08-11 | Feature 004: commitment table gained `Type`, `Channel`, and `Bundle`. Previous header was `\| Date \| Working title \| Pillar \| Status \| Piece \|`. Made while zero plans existed on disk, so no migration was needed. |
| 2026-08-11 | Feature 004: plan-level `**Channel:**` became a multi-value set over an open list, replacing single-valued `blog \| linkedin \| both`. |
| 2026-08-09 | Created for feature 003, restating engineering-brief §4.1. |
