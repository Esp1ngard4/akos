---
name: content-review
description: Report how content actually went over a window the author names — pieces started, locked, published and dropped, the monthly rate against target, produced versus published, and how many items sit at each pipeline stage — check that each piece's status agrees with its WBS row and that every plan names the goal it serves, and render a scope's plans as a visual roadmap. Use when someone asks how a sprint or a month went for content, whether they are holding their rhythm, what is in flight, whether content and the WBS agree, or wants to see the plan as a timeline or roadmap. Reads only; it never changes a status, in the content system or the WBS, and it holds no audience-response data.
user-invocable: true
---

# Review and roadmap

Answer *"is this working?"* — as numbers, or as a picture. Same data, two outputs.

**This skill reads. It does not write** — not a piece's status, not a WBS row, not a plan. Where it finds something wrong it says so, and the author or the skill that owns the field settles it.

**Where things live** ([`posts-format.md`](../_shared/contracts/posts-format.md), [`strategy-file-format.md`](../_shared/contracts/strategy-file-format.md)): a piece's status and dates are in its `backbone.md`; artifacts and `Published` dates in `content-system/posts/index.md`; plans, rates and arcs in `content-system/strategies/**`. When a piece is due, its effort and whether its row is done are in its WBS row, reached through the piece's WBS Ref. **The WBS is read through its Ref, never copied.**

## Entry point 1 — review a window

**The author names the window.** *"How did last sprint go?"*, *"score September"*, *"S26.Q4.1"*, *"the last two weeks"*. Ask if it is not given.

**Never infer the window** from a calendar, a task manager or today's date. **A sprint ID is a window the author named**: read its start and end from the `sprints` calendar of a register this scope's pieces live in. If two registers disagree on that sprint's dates, say so and ask which.

### Pieces in the window

Read each piece's status from its `backbone.md`, or from the index when the field is missing (the contract's rule). Report, by the date each state was entered:

| Reported | Meaning |
|---|---|
| Started | `drafting` date in the window |
| Locked | `locked` date in the window |
| Published | `published` date in the window |
| Dropped | `dropped` date in the window, each with its reason |
| In flight | `drafting` or `locked` at the window's end |

**Committed and delivered are the WBS's figures, not this skill's.** For a sprint window, run `wbs.py metrics` (the `wbs-manager` skill's `scripts/`) over the registers this scope's pieces live in, and report its committed, pulled-in and delivered counts for the content rows, labelled as coming from the WBS. Never recompute them here — two counts of one thing drift.

### Campaign arcs

Per campaign: how many **candidates** (no `WBS`), how many **committed but not started** (`WBS` set, `Piece` blank), and how many under way or done. **Candidates are not a pipeline stage** and are never scored — say plainly when they are piling up (*"that series holds 9 candidates and none is committed"*), because that is the number an arc exists to make visible. **Report the count, not an age**: nothing dates a candidate row, so any "waiting since June" would be invented. Do not editorialise past the count.

**A context row** (`Piece` linked, `WBS` blank) is never scored. It carries the arc, not a promise.

### Rate delivery — always-on plans

An always-on plan with a `**Monthly target:**` is scored **by rate, per calendar month, per channel**: published in that month ÷ the target for that channel. Report it month by month, not as one averaged figure — a quarter that reads `2/2, 0/2, 4/2` is a different story from "6/6", and the averaged version hides the month that was missed.

- **Count `Published`, not produced.** A finished artifact with no `Published` date has not met a public cadence. Produced may be reported alongside, never in place of it.
- **Count index rows whose `Scope` includes this scope**, and whose `Channel` matches the target's channel.
- **A partial month is reported as partial**, never scored — September on the 12th is not a missed target, and a month in progress carries its count with the month named as incomplete.
- **Months before the plan's `**Started:**` are counted, never scored.** Report them as history, plainly labelled — that baseline is often the most useful number in the report.
- **An always-on plan with no target is counted, never scored.** Report what was published per month and say plainly that no target is set. Never infer one from the prose `**Cadence:**` line — that is the improvised proxy this skill forbids everywhere else, and here it would fabricate the standard the author is judged against.

### Produced and published are two numbers

- **Produced** — artifacts locked in the window (index rows dated in it).
- **Published** — artifacts with a `Published` date in the window.

**Never present these as one figure.** A locked artifact is a finished *source*: for a blog post that is nearly the moment of publishing; for a video, the storyboard exists and the video does not. Reporting produced as published overstates precisely the number this system exists to be honest about.

If produced consistently exceeds published — pieces sitting at `locked` — say so plainly: finished work piling up unpublished means the bottleneck moved, and that is worth naming rather than averaging away.

### Pipeline stages

Three, mutually exclusive, every item in exactly one:

| Stage | Counted from |
|---|---|
| Captured, not started | `###` entries in `content-system/ideas.md` — the entry count, never adjusted for whether an entry carries context |
| Drafting | pieces whose status is `drafting` |
| Locked, not published | pieces whose status is `locked` |

Published and dropped pieces have left the pipeline and are reported above, not here.

### Checks — reported, never fixed

**Content and the WBS disagree.** For every piece with a WBS Ref, resolve the Ref by shape and read the row's `Status`. Report each piece where the pair is not one of these:

| Piece | WBS row |
|---|---|
| `drafting` or `locked` | `Implementing` |
| `published` | `Done` |
| `dropped` | `Cancelled` |
| an arc row committed, not started (`Piece` blank) | `Not Started` or `Portfolio Backlog` |

Also report: **a Ref that resolves to no register or no row**, and **a piece with no Ref** that started after its plan gained one. Name the piece, both statuses and which side looks behind. The fix belongs to `content-post-writer`'s transitions or to the WBS tool, on the author's word; this skill never runs it.

**A plan that names no goal.** Every `## Plan:` with no `**Serves:**`, one line each: *"'Lab in the open' doesn't say which goal it serves, so its pieces have no WBS to live in."* That is the finding; do not suggest a goal.

### The analytics boundary

**Hold no audience-response data and never estimate any.** No impressions, followers, reach, engagement, or click-through.

When asked how a channel or cadence is performing, say so plainly: the system holds no such data, and that judgement is qualitative. **Do not improvise a proxy** — post counts per channel are not performance, and offering them as if they were is worse than admitting the gap, because the author would act on a number that measures nothing.

### Absence is a result

No plans, no pieces, an empty window: report it and stop. *"Nothing to report — this scope has no pieces in that window."* Not an error, not a failure.

## Entry point 2 — render the roadmap

Generate `content-system/roadmaps/<category>-<slug>.html` for one scope, covering every plan in its strategy file.

### Where a piece sits

- **Published** → its `published` date.
- **Otherwise, committed** → its WBS row's `Planned End`; failing that, the window of the sprint the row names (`Sprint Planned`, else `Sprint Added`) from that register's calendar. **Read at render time, through the Ref; never stored here.**
- **Neither** → undated: listed in its campaign's block, never placed on a month.

### Form

- Pieces grouped by month, down the page.
- **Each campaign's candidates and undated pieces render as a block, off the month spine** — listed together, visibly a backlog rather than a schedule. Placing an undated piece on a month would draw a promise nobody made.
- **Always-on plans render as months too** — one row per month per channel, showing published ÷ target where a `**Monthly target:**` exists, and the bare count where it does not. Dated pieces and monthly rates share the same month spine, so a scope running both reads as one timeline.
- **Each `Bundle` is one bordered group** — a multi-channel piece reads as one thing, not three unrelated dots.
- Type and channel as small labels.
- Status (`committed`, `drafting`, `locked`, `published`, `dropped`) by **colour and by text**. Never colour alone — "overdue" must be readable without seeing red.
- **Overdue** is inferred at render time: a planned date passed and the piece not `published`. Written nowhere.

### Hard constraints

- **No JavaScript. None.** This is a document, not an application. That is the line between the static snapshot this system permits and the dashboard it deliberately defers.
- **No external assets.** Inline CSS only — no stylesheet, font, script or image fetched from anywhere. It must render with networking disabled.
- **Read-only.** Generating it modifies no source file and no WBS register.
- **Regenerated, never updated.** A second run replaces the file. No accumulated copies, no stale variants, no partial updates.
- **Derived, therefore gitignored.** It is never a source of truth; deleting `content-system/roadmaps/` loses nothing.
- **A what-if never lands at the canonical path.** A render using any value the files do not hold — an assumed start month, a target being considered, a date not yet planned — is written outside `roadmaps/` and carries a banner naming the assumption and the real value. A derived file that disagrees with its source is indistinguishable from the real one once it is on disk, and the author will not be the one who confuses them — the next agent will.
- **Nothing to plot is stated plainly**, not rendered as an empty frame. A plan with no pieces and no published artifacts in range has nothing to draw, and says so.
- **A Ref that does not resolve** places its piece in the undated block, marked as such — never dropped silently and never given a guessed date.

## What this must never become

- An analytics surface.
- A dashboard with state, filters, or input.
- A scheduled job, or anything that runs unasked.
- A writer of any status, in the content system or the WBS.
- A second count of what the WBS already counts.
- A reader of any system outside `content-system/` other than a WBS register, through its Ref.
