# TD.6 — Content System

## Purpose

Turns thinking into finished, publish-ready pieces in the author's own voice, through mandatory back-and-forth rather than one-shot generation. It holds the editorial chain: a position per scope, plans that name the goal they serve and either hold a monthly rate or lay out the arc of pieces a campaign is made of, an inbox for sparks, an interview-led writer that produces the artifact, and a review that reports honestly whether any of it happened.

**Content serves a goal, and the work runs on the WBS.** A piece is committed by a row in the WBS of the project or area that owns the goal its plan serves (TSP.1), and from then on it is planned, carried and closed like any other work. This tool keeps what only it knows — the goal served, channel and type, a piece's own lifecycle (`drafting`, `locked`, `published`, `dropped`), publish dates, candidates and the rate — and the WBS Ref on each piece joins the two. Each fact has one home.

It is deliberately **not a publisher**. Its responsibility ends at the finished piece; nothing in it posts, schedules, or transmits to any platform. For formats it cannot produce — video, deck, poster — it stores the source artifact that enables the final one (a storyboard, a deck skeleton, poster copy), never the rendered file.

**It holds no audience-response data** — no impressions, reach, followers or engagement, and no proxy invented in their place. Whether the writing is landing is a judgement this tool cannot make and must not pretend to.

## Status: Implemented, as a first version

The skills are in real use, and the tool is improved as it is used rather than held back until every path has been exercised. That is a choice, not a claim that it is proven: [What is not proven](#what-is-not-proven) lists what has not yet run, and is worth reading before adopting it.

## Components

| Component | Location | Purpose |
|---|---|---|
| Five skills | `content-idea-capture`, `content-plan-author`, `content-post-writer`, `content-review`, `content-strategy-author` | The whole chain, one skill per stage. |
| Format contracts | `_shared/contracts/` | `strategy-file-format.md`, `posts-format.md`, `ideas-inbox-format.md`. Each is the **sole owner** of its format; skills embed only what is short enough to never be wrong and read the rest from here. |
| Voice material | `_shared/personas/`, `_shared/writing-principles.md` | Four craft personas and the principles that bind all of them. |
| **WBS Register (TSP.1)** | `wbs-manager`, installed beside these skills | **Required to commit and track pieces.** Committing a piece creates its row; starting, publishing and dropping a piece propose the matching `wbs.py set`; the review reads rows and runs `wbs.py metrics`. Without it, ideas, strategies and plans still work, but no piece can be committed, so none is started. |

There is no code, which is why the test checks cross-references rather than behaviour.

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
```

**Committed pieces also have a row in a WBS register** — the register of the project or area that owns the goal a plan serves, wherever your WBS registers already live. The skills find a register by its shape (`meta.kind: wbs-register` and its `meta.scope`), searching from the project root, never from a configured path.

None of it is scaffolded ahead of time. Every skill cold-starts: capture an idea with no strategy, no plan and no posts anywhere, and it works. This repository ships no example data, deliberately — the contracts show the shape of every file, and a seeded example is a thing to delete before you can tell what is yours.

## What the skills cover (and this document doesn't repeat)

Each `SKILL.md` is authoritative for its own mechanics; the three contracts are authoritative for the file formats.

- **`content-strategy-author`** — the interview producing a scope's house: mission, pillars, credibility signals, topics to avoid.
- **`content-plan-author`** — plan authoring and amendment (the goal served, audience, objective, pillars, channels, rate or arc), and **committing a piece**, row by row, which creates its WBS row.
- **`content-idea-capture`** — capture in seconds without interviewing, batch capture, dropping; promotion hands off to the writer.
- **`content-post-writer`** — the phased interview (notes, angle, Six Questions, outline, draft, refinement), persona selection, the anti-AI voice standards, and a piece's four transitions — start, lock, publish, drop — each proposing the matching WBS change. Recording publication lives here.
- **`content-review`** — pieces by status over a window the author names (a sprint ID included), the WBS's own committed/delivered figures, rate against a monthly target, pipeline stages, the content-vs-WBS mismatch check, plans that name no goal, and the static roadmap.

Three rules are governance rather than mechanics, and belong here: **the review never writes**, in the content system or the WBS; **the WBS never changes without the author's yes**, and a declined change leaves the content status moved and the mismatch visible rather than silently skipped; and **capture never interviews** — an interview at capture makes the fastest action in the system the slowest, and then it stops being used and the idea is lost, which is the failure that skill exists to prevent.

## The personas are craft, never substance

A persona says *how* a piece is built — structure, rhythm, how the opening earns the next line. It may never originate a claim, a position, a doubt, or a stance. The corollary is the one that actually fires in practice: **a form can demand content the author never supplied.** An argument shape needs an argument; a "what I learned" shape needs a lesson. When the form asks for material the author did not give, the form is wrong for the material — change the form, never manufacture the missing part to complete the shape.

Every principle in `writing-principles.md` carries a `*Source:*` line recording where it came from, so a future revision can tell an **evidenced** rule from an **inherited** one. Several were written the day a real draft failed in a way nothing then present would have caught.

## What is not proven

Adopt it knowing this. None of it is hypothetical; all of it is recorded rather than estimated.

| | |
|---|---|
| Quickstart scenarios | **27 written, 0 run, and written before the WBS design.** Those exercising campaign activation, commitment scoring and the sprint log test parts that no longer exist. The rules are consistent across skill and contract *by inspection only*. |
| Months reviewed against a plan | **0 complete.** `content-review` has never reported on a real delivered month. |
| Pieces taken through the WBS lifecycle | **0.** No piece has yet gone from commitment through `locked` and `published` with both sides written at each transition. |
| Real drafting sessions | **2**, both in August 2026. They changed the design three times and produced eight hardening fixes. |

`content-review` and the WBS transitions are the sharpest edge: the review reports rate against a monthly target and checks content against the WBS, and neither has run on a month or a piece that actually happened. The capture, strategy, plan and drafting skills have all been used on real work; the review closes a loop that has not yet closed once.

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
- **TSP.3 TSP Register** — row 6. Type `Tool`; Status `Implemented`; Doc Aux `Yes`.
- **TSP.1 WBS Register — the one dependency, by design.** A piece's commitment, effort, sprint, planned dates and done-state are its WBS row's fields, so the content system copies none of them. The same dependency TSP.8 Sprint Ceremonies has, and for the same reason: the work is planned in one place.
- **TSP.8 Sprint Ceremonies** — content needs no ceremony of its own. Grooming refines candidates, planning commits pieces and sets their sprint, the close-out counts them with everything else.
- **No calendar or task manager.** `content-review` never infers a window from either; the author names it, or names a sprint ID read from a WBS register's own calendar.

## Open items

- **The 27 scenarios need running.** Each needs a real interview or a real draft, so this is author time, not a scripted job. Until then the consistency claim is inspection, not evidence.
- **One month reviewed end to end** is the evidence most worth having: `content-review` has not yet scored a month that actually ran.
- **The scenarios need re-cutting against the current contracts** before any are run, so the evidence tests the tool as it is.
- **Installing a content skill does not install `wbs-manager`.** Add it too (`install.py add wbs-manager`); the writer and the plan author say plainly when no register can be found, and commit nothing.
- **`update` does not cascade.** Updating a skill does not update `_shared/`; run `update` on the shared entry too. Both are named in `status`.

## Version history

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-10-07 | **Content runs on the WBS.** Plans name the goal they serve (`Serves`); a committed piece has a row in the WBS of that goal's owner. A piece carries a dated status (`drafting`, `locked`, `published`, `dropped`) and a WBS Ref; start, publish and drop propose the matching WBS change on the author's yes. The commitment table became the arc table; `Stage`, `End date`, activation, commitment write-back, campaign scoring, the index's `Commitment` column and `sprints.md` retired, their jobs taken by the WBS. The review gained the content-vs-WBS and no-goal checks, and the roadmap reads planned dates through the Ref. One dependency, TSP.1. The open item on a tool prefix is dropped: the names are intended. |
| 1.1 | 2026-10-02 | **Implemented, as a first version.** The skills are in real use and improve as they are used; *What is not proven* stays, unchanged, so the label does not claim more than has run. No change to any skill or contract. |
| 1.0 | 2026-09-01 | Published as TSP.6. Contracts, personas and writing principles moved to `_shared/`; `install.py` extended to carry it beside the skill; smoke test added for links, contract references, installed layout and shared reuse. Personal strategies, posts, ideas and voice archive not published — the tool ships, the author's data does not. |
