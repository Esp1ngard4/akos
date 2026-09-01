# TD.6 — Content System

## Purpose

Turns thinking into finished, publish-ready pieces in the author's own voice, through mandatory back-and-forth rather than one-shot generation. It holds the whole chain: a position per scope, plans that commit that position to dated or rate-based work, an inbox for sparks, an interview-led writer that produces the artifact, and a review that reports honestly whether any of it happened.

It is deliberately **not a publisher**. Its responsibility ends at the finished piece; nothing in it posts, schedules, or transmits to any platform. For formats it cannot produce — video, deck, poster — it stores the source artifact that enables the final one (a storyboard, a deck skeleton, poster copy), never the rendered file.

**It holds no audience-response data** — no impressions, reach, followers or engagement, and no proxy invented in their place. Whether the writing is landing is a judgement this tool cannot make and must not pretend to.

## Status: In Progress

This is the honest label, not a modest one. Read [What is not proven](#what-is-not-proven) before adopting it.

## Components

| Component | Location | Purpose |
|---|---|---|
| Five skills | `content-idea-capture`, `content-plan-author`, `content-post-writer`, `content-review`, `content-strategy-author` | The whole chain, one skill per stage. |
| Format contracts | `_shared/contracts/` | `strategy-file-format.md`, `posts-format.md`, `ideas-inbox-format.md`. Each is the **sole owner** of its format; skills embed only what is short enough to never be wrong and read the rest from here. |
| Voice material | `_shared/personas/`, `_shared/writing-principles.md` | Four craft personas and the principles that bind all of them. |

There is no code. This is the only tool in this repository that ships none, which is why the test checks cross-references rather than behaviour.

## The `_shared/` folder, and why installing works

The five skills read the same three contracts. Duplicating a contract into each skill would contradict the rule the contracts exist to enforce — that each format has exactly one owner — so they live once, in `_shared/`, and the skills address them as `../_shared/contracts/<name>.md`.

That path has to resolve **after installation as well as in this repository**, which is why `install.py` copies `_shared/` beside the skill rather than inside it:

```
your-project/.github/skills/
  _shared/                     <- installed once, whichever skill pulled it
    contracts/
    personas/
    writing-principles.md
  content-post-writer/
  content-review/
```

Install any one skill and `_shared/` comes with it. Install a second from the same tool and the existing copy is **reused**, not duplicated — one copy serves them all, as it does here. It is recorded in `tools.lock.json` as an ordinary entry, so `status`, `diff`, `update` and `accept` all work on it with no special case; edit a contract locally and `status` will name the file.

It is never offered by `install.py list`: it has no `SKILL.md`, and installing it alone would install nothing that runs.

## Where your content lives

The skills read and write a **`content-system/` folder at your project root** — separate from the skills themselves, because it is your data and they are the tool:

```
content-system/
  strategies/<category>/<slug>.md     one file per scope, holding its plans
  posts/YYYY-MM-DD-slug/              one folder per bundle
  ideas.md                            the inbox
  sprints.md                          the review's own log
```

None of it is scaffolded ahead of time. Every skill cold-starts: capture an idea with no strategy, no plan and no posts anywhere, and it works. This repository ships no example data, deliberately — the contracts show the shape of every file, and a seeded example is a thing to delete before you can tell what is yours.

## What the skills cover (and this document doesn't repeat)

Each `SKILL.md` is authoritative for its own mechanics; the three contracts are authoritative for the file formats.

- **`content-strategy-author`** — the interview producing a scope's house: mission, pillars, credibility signals, topics to avoid.
- **`content-plan-author`** — plan authoring and amendment, and activation: the row-by-row grooming pass that turns a backlog into promises.
- **`content-idea-capture`** — capture in seconds without interviewing, batch capture, promotion, dropping.
- **`content-post-writer`** — the phased interview (notes, angle, Six Questions, outline, draft, refinement), persona selection, the anti-AI voice standards, and commitment write-back at lock.
- **`content-review`** — delivery against commitments, rate delivery against a monthly target, pipeline stage counts.

Two rules are governance rather than mechanics, and belong here: **the review never writes** (except the sprint row, which is a separate explicit action), and **capture never interviews** — an interview at capture makes the fastest action in the system the slowest, and then it stops being used and the idea is lost, which is the failure that skill exists to prevent.

## The personas are craft, never substance

A persona says *how* a piece is built — structure, rhythm, how the opening earns the next line. It may never originate a claim, a position, a doubt, or a stance. The corollary is the one that actually fires in practice: **a form can demand content the author never supplied.** An argument shape needs an argument; a "what I learned" shape needs a lesson. When the form asks for material the author did not give, the form is wrong for the material — change the form, never manufacture the missing part to complete the shape.

Every principle in `writing-principles.md` carries a `*Source:*` line recording where it came from, so a future revision can tell an **evidenced** rule from an **inherited** one. Several were written the day a real draft failed in a way nothing then present would have caught.

## What is not proven

Adopt it knowing this. None of it is hypothetical; all of it is recorded rather than estimated.

| | |
|---|---|
| Quickstart scenarios | **27 written, 0 run.** The rules are consistent across skill and contract *by inspection only*. |
| Months reviewed against a plan | **0 complete.** `content-review` has never reported on a real delivered month. |
| Posts produced through the plan layer | **0.** Every post in the author's own instance predates plans entirely. |
| Real drafting sessions | **2**, both in August 2026. They changed the design three times and produced eight hardening fixes. |

`content-review` is the sharpest edge: it reports delivery against commitments and rate against a monthly target, and it has never done so for a month that actually ran. The capture, strategy, plan and drafting skills have all been used on real work; the review closes a loop that has not yet closed once.

The voice material is the part least affected by this. `writing-principles.md` and the personas are craft rules with sources, and they do not depend on the pipeline having been exercised.

## How it is tested

`tests/smoke_test.py` covers what can rot in a tool made of cross-references:

- every skill has a `SKILL.md` declaring `name` and `description`;
- every contract in `_shared/contracts/` is referenced by at least one skill — a contract nothing reads is either dead or a reference somebody dropped;
- every relative link resolves **in this repository**;
- every relative link still resolves **after `install.py add`**, which is a different directory layout and the one that breaks silently;
- a second skill from the same tool reuses the shared copy rather than making another;
- and the link checker is handed a deliberately broken link to confirm it can fail.

That last one is not decoration. This repository has already shipped an audit that reported clean because it was looking in the wrong place, and a checker that has never failed is indistinguishable from one that always passes.

What is **not** tested is whether an interview produces a good piece. No test asserts that, and none can.

## Relationship to other tools

- **TSP.4 Tool Installer** — `_shared/` support was added to `install.py` for this tool. Any future tool with several skills and material between them gets it for free.
- **TSP.3 TSP Register** — row 6. Type `Tool`; Status `In Progress`; Doc Aux `Yes`.
- **No coupling to anything else, by design.** `content-review` never infers a sprint window from a sprint system, a calendar or a task manager; the author names the window. This is not an integration gap to close later — the folder has to stay copyable into any context, and a dependency whose degradation is its normal case is worse than no dependency.

## Open items

- **The 27 scenarios need running.** Each needs a real interview or a real draft, so this is author time, not a scripted job. Until then the consistency claim is inspection, not evidence.
- **One month reviewed end to end** would move this to `Implemented` faster than anything else.
- **The skills carry no tool prefix.** They were built as a portable system first. Renaming touches every skill folder, its frontmatter, the contracts that name it, and this document — a deliberate scoped piece of work, not a silent fix.
- **`update` does not cascade.** Updating a skill does not update `_shared/`; run `update` on the shared entry too. Both are named in `status`.

## Version history

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-09-01 | Published as TSP.6. Contracts, personas and writing principles moved to `_shared/`; `install.py` extended to carry it beside the skill; smoke test added for links, contract references, installed layout and shared reuse. Personal strategies, posts, ideas and voice archive not published — the tool ships, the author's data does not. |
