# Phased Workflow with Interview Checkpoints

Use this when guiding the user through creating a post from notes or a draft. Ask **one concise question** at each checkpoint. For quick tasks (e.g. "cut fluff"), jump to Phase 5.

**Bar**: You are a talented blogger writing the best content for the medium. Interview until you have a story **worth telling**. Nothing less than great should pass. If the story isn’t there yet, don’t lock the outline or the draft—keep refining until it is.

**Save location**: Each post folder is a **bundle** — one `backbone.md` plus one file per artifact, named `<channel>-<type>.md` (`blog-article.md`, `linkedin-short-post.md`, `instagram-video.md`). Format is owned by [`_shared/contracts/posts-format.md`](../../_shared/contracts/posts-format.md). Create the folder after Phase 1 when the angle is set, or earlier if an idea was promoted from `content-system/ideas.md`; derive or ask for the slug (kebab-case). If the promoted idea had a `### <ID>` context block, it becomes the opening `## Notes` and is removed from `ideas.md`.

**Backbone format**: thin YAML frontmatter (`scope`, optional `from-idea`, optional `commitments`), then sections in this order, each added as its phase completes and omitted entirely when empty: `## Idea`, `## Notes`, `## Angle`, `## Audience`, `## Artifacts` (type, channel and target length per artifact), `## Persona`, `## Six Questions`, `## Outline`, `## Claims`.

---

## Phase 0: Notes as atoms

- Ask the user to paste notes, fragments, quotes, examples, or bullets.
- Help atomize notes into: key claims, supporting evidence, mini-stories, tensions/contrasts, surprising bits, phrases worth keeping.
- **Interview checkpoint**: One concise question—identify what feels most important or most true.
- **No search**: do not look anything up in this phase, for any reason. See "Web search" in SKILL.md — search here would hand the user an atom they didn't originate.

---

## Phase 1: Resolve scope, pick an angle from notes, and a persona

- **First, resolve scope by asking.** Walk `content-system/strategies/` and list what is there, by path form (`areaOfFocus/product-craft`), plus `default`. Take the answer as given. If the source idea already carries a scope, use it silently and ask nothing. **No external registry is read** — the strategies folder is the only source of scope names.
  - **Never infer scope from what the piece is about.** Do not suggest a scope because the material mentions a product, project or client; do not filter the list to what looks topically relevant; do not pre-select. Scope is the positioning goal the piece serves — a judgement only the author can make. Six posts were once scoped by topic-matching against project names and all six were wrong.
  - If the author is unsure, proceed as `default` and revisit at lock time rather than resolving it for them.
  - Record the answer in `backbone.md` under a `**Scope:**` line.
  - **If that scope has no strategy file**, offer once — *"No strategy file exists for this scope yet — want to set one up now, or continue without one for this piece?"* Declined or unanswered: continue exactly as today, and do not ask again this session. Accepted: pause here keeping the angle work already done, hand off to `content-strategy-author`, and resume afterwards. Never blocking; never offered where a strategy already exists. **You detect and offer; you do not author** — the strategy interview belongs to that skill, not this one.
- **Then resolve the plan**, if the scope has a strategy file. Enumerate its `## Plan:` sections. **Zero** → proceed on the strategy's own pillars, and offer once, declinably, to set one up with `content-plan-author`. **Exactly one** → adopt it silently, asking nothing about which plan; take its `Audience`, `Objective`, `Pillars in play`, `Shape` and `Channel`. **Two or more** → ask once, as a pick-list naming each plan with its shape, its audience, and — for a campaign — its stage. **A refining plan is offered like any other and labelled as refining**: drafting a candidate before it is committed is legitimate and often the point, but the author must see that nothing in it is promised before choosing it, not find out when no angle is surfaced. This can only ever be the second question in a resolution pass, never asked at the same time as the scope question.
- **Then resolve the angle.**
  - **Only an `active` campaign carries commitments.** A campaign at `Stage: refining` holds candidates, not promises — surface nothing from it and write no pointer against it. A missing `**Stage:**` reads as `active`. See [`strategy-file-format.md`](../../_shared/contracts/strategy-file-format.md).
  - Active campaign plan with a `pending` row dated **today or earlier** → surface that row's `Working title` as the **default** angle, explicitly labelled as coming from an existing commitment, and fully overridable. If the user accepts it, write `commitments: <scope>/<plan>/<date>` into `backbone.md` frontmatter **now**, at acceptance — not at lock time. This pointer is the only thing write-back will ever match on.
  - Active campaign with nothing due, a refining campaign, an always-on plan, or no plan → the normal 2–3 angle proposal below, constrained to the plan's `Pillars in play` (or the strategy's own pillars where there is no plan) and avoiding its `Topics to avoid`. An always-on plan additionally defaults the audience rather than asking fresh.
  - **If the user overrides the surfaced angle, rejects it, or nothing was due, no pointer is written — ever.** Not even if the finished piece plainly fits a pillar. A false negative costs one manual cell edit later; a false positive silently credits the wrong commitment and corrupts the record the author uses to hold themselves accountable.
- Propose **2–3 plausible angles/threads** that connect the atoms.
- **Agree the artifacts.** Ask which artifacts this bundle produces — type and channel for each. One is the normal case. Record them under `## Artifacts` in the backbone; each becomes its own file, its own index row and its own lock.
- **Interview checkpoint**: Ask the user to choose one angle (or rank them), state the **intended audience**, and **format** (blog or LinkedIn). If blog, ask for **target word count** (e.g. 800–1000) or suggest a range; record it in the backbone.
- **Persona selection**: Read `content-system/personas/README.md` and propose **exactly one** persona with a one-line reason, for the user to confirm or override. Choose on **what the material already is**, never on what would be most impressive. Two rules that do the real work:
  - **Argument Builder requires a genuinely open question.** If the user could state the conclusion in one sentence right now, the decision is settled and this is the wrong persona — its shape would have to be filled with manufactured doubt.
  - **Reflective Narrator is the default when unsure**, because it demands the least material the user didn't already supply.
  - If a chosen persona's length or shape conflicts with the target word count agreed above, say so now rather than padding later. The material sets the length.
- **Save**: Create `content-system/posts/YYYY-MM-DD-slug/` (today's date + slug from angle or user), unless promotion already created it. Write `backbone.md` — frontmatter (`scope` in path form, `from-idea` if promoted, `commitments` if one was accepted) and the sections settled so far: `## Angle`, `## Audience`, `## Artifacts`, `## Persona` with the reason. Artifact files are created in Phase 4, not here.
- **No search**: angle selection is where the user's own thinking has to do the work; no lookups here either.

---

## Phase 2: Six Questions clarity gate (time-boxed feel)

Use these to clarify the post quickly. Ask **only the single most blocking** at a time.

1. **Most important point** – What is the one thing this post must get across?
2. **Why it matters** – What does it enable or change?
3. **Why readers should care** – What benefit do they get?
4. **Easiest way to understand** – Analogy, example, or structure?
5. **Desired reader feeling** – How should they feel when done?
6. **Reader's next action** – What do you want them to do after reading?

- **Interview checkpoint**: Ask only the single most blocking of these at a time.
- **Don’t leave until the story is worth telling**: If answers are thin or the story isn’t there yet, keep asking (one question at a time) or recommend reshaping the angle or choosing a different one. Do not move to outline until you believe the post has a story worth telling.
- **Save**: Append Six Questions answers to `backbone.md`.
- **No search** in this phase either — see Phase 0.

---

## Phase 3: Outline (bullets, fast, linear)

- Produce a **bullet outline in final order** (no prose).
- Optionally offer alternative structures: story-first vs framework-first.
- **Don’t lock a weak outline**: If the outline doesn’t yet support a story worth telling, refine it—ask what’s missing, suggest a stronger sequence or a clearer turn, and update the outline. Only move to draft when the outline is strong enough.
- **Save**: Append the bullet outline to `backbone.md`. Optionally use Canvas for in-session editing.
- **Interview checkpoint**: One question to confirm sequence and any missing proof/examples.
- **No search** in this phase either — see Phase 0. This is the last phase where search is banned outright; from Phase 4 on, search is still restricted to verifying a claim the user already made (see SKILL.md).

---

## Phase 4: Draft (outline → prose)

- **Load the selected persona's own file** from `content-system/personas/` before writing a word, and follow its build, opening, closing, rhythm and — most importantly — its "What it must not do" section. Where it collides with `content-system/writing-principles.md`, the principle wins.
- **If drafting requires material the user never supplied** — a lesson, a doubt, a cause, a counter-argument, a number — stop and ask. Do not write the missing part to complete the persona's shape. Repeated need to invent means the persona is wrong for the material: say so and propose a different one, back at Phase 1.
- Convert outline into prose.
- **Blog**: Write the first draft at **target length** (from backbone). A blog post tells a story and takes the reader on a journey; it needs a narrative arc (before, build/tension, turn, after) and enough length to feel like a read, not a list of bullets. Do not produce a short summary with the idea of expanding later. Include scene, reflection, and concrete detail so the draft is already blog-length.
- **LinkedIn**: Move fast; tight lines, natural pacing.
- **Save**: Write the draft to its artifact file — `<channel>-<type>.md` in the bundle folder. Optionally use Canvas for in-session editing.
- **One artifact at a time.** Where the bundle has several, draft, refine and lock each in turn. They share the angle, the Six Questions, the outline and the claims record; they do not share prose, and each passes the voice check and the claim check on its own.
- **For a type this skill cannot render directly** — video, deck, poster — load its module from `references/types/` and write the **source artifact** it specifies: a storyboard, a deck skeleton, poster copy. Never a rendered `.mp4`, `.pptx` or image. If a requested type has no module, say so rather than silently writing an article.
- **Don’t lock a weak draft**: If the draft doesn’t meet the bar (story not worth telling, execution thin), say so in one sentence and propose what’s missing—then refine the outline or the draft. Keep refining until the post is great. Only then offer it as final.
- **Interview checkpoint**: One question to confirm voice/tone and any sensitive details to avoid.

---

## Phase 5: Review (polish by cutting)

- Before proposing a draft as final, run the **anti-AI self-check** (see anti-ai-standards.md) **and the persona's own "What it must not do" list** as a second checklist — that list is where a persona's characteristic failure is written down in advance. **Then run the claim check** (below), before "remove templated phrases": extract and resolve any outside claims in the current artifact file. Once both checks are done: remove templated phrases, formulaic contrasts, and stock transitions; prefer expanding with concrete story over adding filler.
- **Default editing philosophy**: Cut repetition and fluff, tighten to target length, then style cleanup.
- Offer revision options: cut 20%, add one concrete example, make it more personal/reflective, make it more tactical.
- **Save**: Overwrite the artifact file with the final post text when the user approves.
- **Interview checkpoint**: Ask what to emphasize or de-emphasize.

### Claim check (part of the Phase 5 self-check, not a separate phase)

No research phase is added anywhere in this workflow. Phase 0 remains the right evidence phase for this content — the user is the source, not a reporter. This check closes one specific hole: nothing above asks "how do you know that?" of a claim the *user* asserts (the fabrication ban above only stops the *agent* inventing something).

**Extraction rule.** Scan the current artifact file sentence by sentence. A sentence is in scope only if it asserts something as fact about the world *beyond the user's own direct experience*: numbers, industry generalities, "most/usually/the standard is"-shaped claims, or anything about a named third party (a company, a specific person, a competitor). Out of scope: opinions marked as opinion, predictions tensed as predictions (not smuggled in as present-tense fact), and anything the user is stating about what they personally did, observed, or decided. Two categories only — about the world, or about the user's own experience — nothing larger. Expected yield is **0–5 sentences, often zero**. When the extraction is empty, state "No outside claims found" in one line and move on — do not turn this into a line-by-line review of the whole draft.

**One question per extracted sentence** — "How do you know this?" — resolved to exactly one of three dispositions:

| Disposition | What happens |
|---|---|
| **Sourced** | The user names a source, or confirms one the agent found under the search rule below. The sentence stands in the artifact file unchanged; the source is recorded in `backbone.md`'s `## Claims` section. |
| **On author** | The user confirms it's really their own experience. Rewrite the sentence in the artifact file to say so out loud — e.g. "Most migrations fail" → "Every migration I've run has slipped." A real rewrite, not a tag or footnote. **Only valid if the claim affects no one else** — any sentence naming a third party (a company, a specific person, a competitor) does not qualify for this disposition regardless of how personally the user experienced it; resolve it as sourced or cut instead. |
| **Can't back it** | Cut from the artifact file entirely, or explicitly rewritten as the user's own read/impression (e.g. "My read is that most migrations fail, though I haven't checked the numbers"). Never left as a bare, unhedged "experts say"-style claim — that phrasing is banned regardless of disposition. |

**Recording — `## Claims` in `backbone.md`.** Append a `## Claims` section to `backbone.md`, last, in file order, one row per extracted claim: the sentence (or its rewritten form), its disposition, and the source if sourced. Write this section **only when the extraction is non-empty** — omit it entirely (not an empty heading) when there are no outside claims.

**Search — direction-of-flow rule, MUST / MUST NOT.** See "Web search" in SKILL.md for the full rule; restated here because this is where it's exercised:
- **MUST** allow search only to verify a claim the user already made, including contradiction-hunting against that specific claim.
- **MUST NOT** search for any reason in Phases 0–3, ever, regardless of tool availability.
- **Exception**: the user explicitly asks the agent to look something up.
- If this check ever proposes a fact the user didn't first assert, it has crossed into content supply — the differentiator is void, not just weakened.

---

## Phase 6: Publish cadence (optional)

- If the user wants consistency, help pick a **realistic cadence** and a **time-box plan**.
- Otherwise skip.

---

## Refinement loop (iterating on the draft)

Use this when the user already has a draft and wants to refine it until they have a final version (e.g. “refine this,” “make it plainer,” “cut the second paragraph,” “add an example here”). Multiple rounds are normal.

**Bar in refinement**: Don’t propose the draft as final until it’s great. If the story or execution isn’t there yet, suggest what’s missing and refine (outline or draft) until it is.

**Each round:**

1. **Read the current draft** – From `content-system/posts/YYYY-MM-DD-slug/draft.md` if that post folder exists, or from the text the user pasted or pointed to. If unsure which post, ask once (“Which post folder, or paste the draft?”).
2. **Apply the requested change** – Do exactly what they asked (cut fluff, plainer language, add example, tighten, change tone, etc.). Apply the anti-AI writing standard and self-check before responding.
3. **Write back to the artifact file** – Overwrite the artifact file with the updated text so the next round starts from this version.
4. **One concise question** – Ask the diagnosis question first: **"Is the problem the shape — order, what the turn is, what's missing — or the sentences?"** Route on the answer: *shape* → back to Phase 3 (outline), not forward into cutting; *sentences* → proceed to cutting and the Phase 5 voice self-check. Cutting cannot fix a shape problem — if the diagnosis routes to shape, don't offer "cut 20%" as a revision option. Once shape vs. sentences is resolved (or on a later round, once that's already settled), the usual follow-ups apply — e.g. “Anything else to change?”, “More personal or more tactical?”, or “Ready to lock this as final?”.
5. **Repeat** until the user says they’re done (e.g. “That’s final,” “Lock it,” “Good to go”). Then, in that same turn, do all three and stop:

   **a. Confirm** the final version is saved in the artifact file.

   **b. Add the artifact's row** to `content-system/posts/index.md` — `| Date | Title | Type | Channel | Scope | Commitment | Published | Link |`, `Scope` in path form, `Published` **left blank**. Written at lock time, never deferred.

   **c. Write back the commitment, if and only if one was accepted at Phase 1.** Read `commitments:` from `backbone.md`, find exactly that row in the plan's table, set its `Status` to `delivered` and fill its `Piece` cell with a relative link to the artifact. Change nothing else in the file.

   **Write-back matches on the recorded pointer and nothing else.** No title similarity, no topic matching, no pillar fit. If no pointer exists, no row is credited — a commitment fulfilled without automatic credit costs one manual cell edit, while crediting the wrong row silently corrupts the record the author uses to hold themselves accountable.

   **`Published` is not written here.** The lock means the source artifact is finished, not that it went live. The author records publication separately.

   **Abandonment before this signal writes nothing** — the commitment row stays `pending`, and no intermediate status exists. An always-on plan has no table and gets no write-back at all; that absence is correct behaviour, not an oversight. **Neither does a campaign at `Stage: refining`** — its rows are candidates, so no row in it is ever credited, whatever a backbone happens to point at.

   **Then verify**: re-read the strategy file and the index row you just wrote. If either no longer parses, correct once and re-check; on a second failure say so plainly rather than leaving them broken.

**If the request is vague** (“make it better,” “polish it”): Offer one or two concrete options (e.g. “Cut ~20% or add one concrete example?”) and apply the one they choose, then ask the one follow-up question.

**Revision options you can offer**: cut 20%, add one concrete example, make it more personal/reflective, make it more tactical, plainer language, shorter/longer.

**Before proposing a draft as final**: Run the anti-AI self-check. **Then run the claim check** (see Phase 5 above) against the current artifact file, before applying any rewrite for AI writing patterns. If the user has said the draft has lots of AI writing patterns or similar, rewrite with the anti-AI standard applied (cut templated phrases, formulaic contrasts, stock transitions) and expand with concrete story rather than filler.
