# Type module — video storyboard

**Renders**: `<channel>-video.md` — a storyboard. **Never** an `.mp4`.

This module governs **rendering only**. The angle, Six Questions, outline and claims come from the shared `backbone.md`, and the claim check, anti-AI voice check, refinement loop and `writing-principles.md` all still apply unchanged. Nothing here overrides them.

## What you produce

A shot list the author can film from. One row per beat:

```markdown
## Storyboard — <working title>

**Length**: ~60s
**Hook (first 3 seconds)**: <the line or image that stops the scroll>

| # | Seconds | On screen | Spoken | On-screen text |
|---|---|---|---|---|
| 1 | 0–5 | The failing dashboard | "This ran fine for six months." | — |
```

Then:

```markdown
**Close**: <what the viewer should be left with>
**What I need to film**: <props, screens, locations the author must have>
```

## Rules

**The spoken column is the writing.** It carries the voice, and it gets the same anti-AI treatment as prose — no templated openers, no "in this video I'll show you", no stock transitions between beats.

**Say it once.** A beat where the spoken line and the on-screen text repeat each other wastes both. On-screen text either names something the voice does not, or stays empty.

**The hook is a real constraint, not a label.** If the first beat needs context before it makes sense, the storyboard is starting in the wrong place — go back to the outline rather than writing a slower opening.

**Name what must be filmed.** A storyboard that assumes footage the author does not have is a script for a video that will not get made. If a beat needs a screen recording, a whiteboard, or a specific location, say so in "What I need to film".

**Length is a budget.** Beats have seconds; they must add up. Cutting a beat is a decision to surface, not something to absorb by talking faster.

## What this must never do

- Write, generate, or reference a rendered video file.
- Invent footage, statistics, or a demo the author has not said exists.
- Add a call to action the author did not ask for.
- Pad to reach a length. A 40-second video that works beats a 60-second one that was stretched.
