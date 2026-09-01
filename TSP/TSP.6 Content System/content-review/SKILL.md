---
name: content-review
description: Report how a content sprint actually went — what was committed, delivered, outstanding and missed, plus how many items sit at each pipeline stage — and render a scope's plans as a visual roadmap. Use when someone asks how a sprint went, whether they are hitting their commitments, what is in flight, or wants to see the plan as a timeline or roadmap. Reads only; it never marks anything delivered or missed, and it holds no audience-response data.
user-invocable: true
---

# Review and roadmap

Answer *"is this working?"* — as numbers, or as a picture. Same data, two outputs.

**This skill reads. It does not write.** The one exception is recording a sprint result, which is a separate action the author asks for explicitly, below.

## Entry point 1 — review a window

**The author names the window.** *"How did last sprint go?"*, *"score August"*, *"the last two weeks"*. Ask if it is not given.

**Never infer the window.** Inferring means reading an external sprint system, a calendar, or a task manager — coupling that breaks portability, since a copy of `content-system/` in another context has none of them. The author knows which sprint they mean.

Read commitment rows from `content-system/strategies/**` and artifacts from `content-system/posts/index.md`.

### Delivery

| Reported | Meaning |
|---|---|
| Committed | rows dated inside the window |
| Delivered | `Status: delivered` |
| Outstanding | `pending`, date still ahead |
| **Missed** | `pending`, date passed |
| Delivered fraction | delivered ÷ committed |

### Refining campaigns are reported, never scored

A campaign at `Stage: refining` contributes **nothing** to committed, delivered, outstanding, missed, or any fraction. Report it separately: the plan name and how many candidates are waiting in it.

Say plainly when candidates are piling up — *"that series holds 9 candidates and none has been committed"* — because that is the number this stage exists to make visible, and an unexamined backlog is the failure it was built to prevent. **Report the count, not an age.** Nothing dates a candidate row: `Date` is the commitment date and a candidate has none, so any "waiting since June" would be invented. **Do not editorialise past the count**; whether the thinking is ready is the author's judgement, not a metric.

**Candidates are not a pipeline stage.** An idea sitting in `ideas.md` *and* named as a candidate is one fact in two frames — report both, add them nowhere. See [`strategy-file-format.md`](../_shared/contracts/strategy-file-format.md).

**A row pointing at an already-published piece is never scored**, in either stage. It carries the arc, not a promise.

### Rate delivery — always-on plans

A campaign is scored by dated rows. An always-on plan with a `**Monthly target:**` is scored **by rate, per calendar month, per channel**: published in that month ÷ the target for that channel. Report it month by month, not as one averaged figure — a quarter that reads `2/2, 0/2, 4/2` is a different story from "6/6", and the averaged version hides the month that was missed.

- **Count `Published`, not produced.** A finished artifact with no `Published` date has not met a public cadence. Produced may be reported alongside, never in place of it.
- **Count rows whose `Scope` includes this scope**, and whose `Channel` matches the target's channel.
- **A partial month is reported as partial**, never scored — August on the 12th is not a missed target, and a month in progress carries its count with the month named as incomplete.
- **Months before the plan's `**Started:**` are counted, never scored.** Report them as history, plainly labelled — that baseline is often the most useful number in the report.
- **An always-on plan with no target is counted, never scored.** Report what was published per month and say plainly that no target is set. Never infer one from the prose `**Cadence:**` line — that is the improvised proxy this skill forbids everywhere else, and here it would fabricate the standard the author is judged against.

**Missed is inferred at read time and written nowhere.** No file is modified to say it. If the author wants a row to visibly read `missed`, that is their manual edit — the system never authors it.

### A scope running both shapes reports two figures, never one

An artifact published against an active campaign's commitment is **also** one toward that month's always-on target. Both are true and they answer different questions — *did you ship what you promised* versus *did you hold your rhythm*.

**Report them side by side and never add them.** A combined total answers neither question while looking like progress, and no artifact is ever counted twice inside a single figure.

### Produced and published are two numbers

- **Produced** — artifacts locked in the window.
- **Published** — artifacts with a date in the index's `Published` column.

**Never present these as one figure.** Write-back marks a commitment `delivered` when the *source artifact* is finished. For a blog post that is nearly the same moment as publishing; for a video, the storyboard exists and the video does not. Reporting produced as published overstates precisely the number this system exists to be honest about.

If produced consistently exceeds published, say so plainly — finished work piling up unpublished means the bottleneck moved, and that is worth naming rather than averaging away.

### Pipeline stages

Three, mutually exclusive, every item in exactly one:

| Stage | Counted from |
|---|---|
| Captured, not started | `###` entries in `content-system/ideas.md` - the entry count, never adjusted for whether an entry carries context |
| Started, not locked | bundle folders in `content-system/posts/` with no index row |
| Locked | rows in `content-system/posts/index.md` |

### The analytics boundary

**Hold no audience-response data and never estimate any.** No impressions, followers, reach, engagement, or click-through.

When asked how a channel or cadence is performing, say so plainly: the system holds no such data, and that judgement is qualitative. **Do not improvise a proxy** — post counts per channel are not performance, and offering them as if they were is worse than admitting the gap, because the author would act on a number that measures nothing.

### Absence is a result

No plans, no commitments, an empty window: report it and stop. *"Nothing to score — this scope has no plans."* Not an error, not a failure.

## Entry point 2 — record a sprint result

**Separate, and only when asked.** Appends one row to `content-system/sprints.md`.

It is separate precisely because review may not write. A review that quietly logged its own output would break its own guarantee while looking helpful — and the author would lose the ability to look at a sprint without changing the record of it.

Only mark a sprint content-focused if the author says it was. Sprints where content was not the focus **do not get a row at all** — absent, not zero.

## Entry point 3 — render the roadmap

Generate `content-system/roadmaps/<category>-<slug>.html` for one scope, covering every plan in its strategy file.

### Form

- Commitments grouped by month, down the page.
- **A refining campaign renders as a block, off the month spine** — its candidates listed together, undated, visibly a backlog rather than a schedule. Placing an undated candidate on a month would draw a promise nobody made.
- **Always-on plans render as months too** — one row per month per channel, showing published ÷ target where a `**Monthly target:**` exists, and the bare count where it does not. Dated commitments and monthly rates share the same month spine, so a scope running both reads as one timeline.
- **Each `Bundle` is one bordered group** — a multi-channel deliverable reads as one thing, not three unrelated dots.
- Standalone artifacts are single rows.
- Type and channel as small labels.
- Status by **colour and by text**. Never colour alone — "overdue" must be readable without seeing red.
- Overdue derived from the same read-time inference used above.

### Hard constraints

- **No JavaScript. None.** This is a document, not an application. That is the line between the static snapshot this system permits and the dashboard it deliberately defers.
- **No external assets.** Inline CSS only — no stylesheet, font, script or image fetched from anywhere. It must render with networking disabled.
- **Read-only.** Generating it modifies no source file.
- **Regenerated, never updated.** A second run replaces the file. No accumulated copies, no stale variants, no partial updates.
- **Derived, therefore gitignored.** It is never a source of truth; deleting `content-system/roadmaps/` loses nothing.
- **A what-if never lands at the canonical path.** A render using any value the files do not hold — an assumed start month, a target being considered, a date not yet committed — is written outside `roadmaps/` and carries a banner naming the assumption and the real value. A derived file that disagrees with its source is indistinguishable from the real one once it is on disk, and the author will not be the one who confuses them — the next agent will.
- **Nothing to plot is stated plainly**, not rendered as an empty frame. A plan with no commitments and no published artifacts in range has nothing to draw, and says so.

## What this must never become

- An analytics surface.
- A dashboard with state, filters, or input.
- A scheduled job, or anything that runs unasked.
- A writer of `missed`, or of any status.
- A reader of any system outside `content-system/`.
- A second place where commitment state lives.
