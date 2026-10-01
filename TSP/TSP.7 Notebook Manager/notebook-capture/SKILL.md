---
name: notebook-capture
description: Capture, retrieve and index plain-markdown notebooks (a diary, project, area-of-focus and area-of-interest notebooks, and meeting notes) and draft crystallized HTML posts for an eDiary (e-diary) from a raw entry. Use whenever the user asks to jot something down, log a note, capture a thought, decision or task, start a new notebook, prep for or take notes from a meeting, crystallize or draft an eDiary or e-diary post, or asks what is in a notebook, the diary, meetings or the eDiary.
---

# Notebook Capture

## Files

| Path | Role |
|---|---|
| `notebooks/` (see *Base path*) | **Source of truth.** The user's notebooks |
| `assets/notebooks/` | An empty notebooks tree: every `index.md`, and `eDiary/style.css`. Copied only to create a file that is missing (*First use*) |
| `assets/post-template.html` | The shape every eDiary post starts from. Read in place, never copied |

## When to use this skill

- The user asks to capture, log, note, or record something during a conversation ("note that...", "log this", "add to my diary", "capture this decision")
- The user asks to retrieve something from a notebook ("what did I note last week", "what's in the diary index", "what have I captured about project X")
- The user asks to create a new notebook (a named, scoped capture area distinct from diary)
- The user asks to prep for a meeting or capture notes from one ("prep me for the X meeting", "log notes from today's standup with Y")
- The user asks to crystallize, draft, or turn a raw capture into an eDiary post ("crystallize today's diary entry", "draft an eDiary post from the vendor-sync meeting") — see §10
- The user asks to see the list of notebooks
- The user asks to check notebook tags / cross-references (see §5's audit-on-request behavior)

## Philosophy (read before acting)

One convention serves every notebook. **Diary is not special** — it is `notebooks/diary/`, following the same internal shape (entries/, index.md, template) as any project, area-of-focus, or area-of-interest notebook. The only thing that varies is which of the four registry-style top-level categories a notebook lives under: `diary` (always exactly one, flat, no sub-slug), `projects/<slug>` (many, one per project — has an end state), `areaOfFocus/<slug>` (many, one per ongoing area of responsibility), `areaOfInterest/<slug>` (many, one per deep-dive/thematic topic of ongoing interest — no end state, not a responsibility). Never branch behavior on `if notebook == "diary"` for anything other than category placement. If a rule doesn't apply equally to every notebook, it's the wrong rule.

`meetings/` is a separate, fifth top-level category — flat like diary (no per-meeting subfolder), but one file per meeting rather than one file per day, with its own template and an optional cross-reference into one of the three registry categories. See §5 for its distinct behavior; it is one of two places in this skill where a real behavioral difference exists, not a special case of diary.

`eDiary/` is a separate, sixth top-level category — also flat, one file per post rather than one file per day, but the post itself is static HTML (not markdown) and the cross-reference (`related`) is required, not optional, and targets one specific source *entry* rather than a whole notebook. See §10 for its distinct behavior.

This skill is agent-mediated capture/retrieval only. There is no app, no search index, no file watcher, no sync client, and no coupling to any other skill (sprint and ceremony tooling included) — notebooks are plain markdown that any other skill can already read as context on request, nothing more.

**Base path.** Every `notebooks/...` path in this file is relative to this skill's own location: `notebooks/` sits beside the folder that holds the skills folder this skill is installed in (`.claude/skills/`, `.github/skills/` or similar) — the root of the unit. For example, a skill at `<root>/.claude/skills/notebook-capture/` reads and writes `<root>/notebooks/`. This skill and its data are a self-contained, portable unit; resolve paths relative to that unit's root, not any outer folder, regardless of where the current working directory happens to be.

## Folder convention

```
notebooks/
  index.md                          <- static top-level landing page listing the 6 categories
  diary/
    index.md                        <- per-notebook rollup index
    entries/
      YYYY-MM-DD.md                 <- one file per calendar day
  projects/
    index.md                        <- registry of project notebooks
    <project-slug>/
      index.md                      <- per-notebook rollup index
      entries/
        YYYY-MM-DD.md
  areaOfFocus/
    index.md                        <- registry of area-of-focus notebooks
    <area-slug>/
      index.md                      <- per-notebook rollup index
      entries/
        YYYY-MM-DD.md
  areaOfInterest/
    index.md                        <- registry of area-of-interest notebooks
    <topic-slug>/
      index.md                      <- per-notebook rollup index
      entries/
        YYYY-MM-DD.md
  meetings/
    index.md                        <- flat registry of all meetings, chronological, with a Related column
    entries/
      YYYY-MM-DD-<meeting-slug>.md  <- one file per meeting (not per day)
  eDiary/
    index.md                        <- flat registry of all eDiary posts, chronological, with a Related column
    style.css                       <- one shared stylesheet referenced by every post
    entries/
      YYYY-MM-DD-<post-slug>.html   <- one static HTML file per post (not per day, not markdown)
```

## First use — create what is missing

Before reading or writing a notebook file, check that it and its parent folders exist. Copy any missing file from `assets/notebooks/` at the same relative path (`assets/notebooks/diary/index.md` becomes `notebooks/diary/index.md`), and never overwrite a file that exists. `entries/` folders are created by the first capture that needs them. Once copied, a file belongs to the user's notebooks and may change; the asset is only a starting point, never a copy to keep in sync.

## 1. Notebook resolution

When a capture or retrieval request comes in, decide which notebook it belongs to:

1. If the user names a notebook explicitly (by slug or clear description matching an existing row in `notebooks/projects/index.md`, `notebooks/areaOfFocus/index.md`, or `notebooks/areaOfInterest/index.md`), use that one.
2. If the user's phrasing maps clearly to an existing project, area-of-focus, or area-of-interest notebook's stated purpose, use that one (resolve into `notebooks/projects/<slug>/`, `notebooks/areaOfFocus/<slug>/`, or `notebooks/areaOfInterest/<slug>/` respectively).
3. If the request is to **prep for or capture notes from a meeting**, resolve into `meetings/` instead — never into diary or directly into a project/area-of-focus/area-of-interest notebook. See §5 for meeting-specific behavior, including how a meeting can still cross-reference one of those notebooks without living inside it.
4. **Otherwise, default to `diary`.** Diary is the catch-all for anything that doesn't clearly belong to a project, area-of-focus, or area-of-interest notebook, or to a meeting. Do not ask the user to classify every capture — resolving without friction is the point. (Meetings are the one exception to this default — see rule 3: a meeting never falls back to diary, it stays in `meetings/` even if untagged.)
5. If genuinely ambiguous between two or more existing notebooks (not between "some notebook" and diary), ask one focused question. Do not ask for ambiguity between diary and "no notebook at all" — there is always a home (diary).
6. If the request is for a **brand-new** project, area-of-focus, or area-of-interest notebook and it's genuinely ambiguous which of the three categories it belongs to, ask one focused question naming the plausible options — do not guess between categories. If it's clearly not diary-worthy but the category is obvious from context (e.g. explicitly says "project", "area of focus", or "area of interest"), don't ask.

## 2. Entry file naming

One file per calendar day per notebook: `notebooks/diary/entries/YYYY-MM-DD.md` for diary, or `notebooks/<projects|areaOfFocus|areaOfInterest>/<slug>/entries/YYYY-MM-DD.md` for a project/area-of-focus/area-of-interest notebook, dated by the day of capture (not by capture event). Multiple captures on the same day append as a new heading **at the end of that day's existing file** (§4) — never create a second file for the same day, never overwrite prior content in that file.

Meetings and eDiary posts do not follow this rule — see §5 for meeting file naming (one file per meeting, not per day) and §10 for eDiary post naming (one file per post, not per day).

## 3. Frontmatter schema

Every entry file has YAML frontmatter, generated or refreshed by the agent whenever it writes to the file:

```yaml
---
title: <short, agent-generated>
tags: ["#tag1", "#tag2", "#tag3"]   # up to 3, each "#"-prefixed
summary: <one-sentence executive summary, agent-generated>
---
```

Regenerate `title`, `tags`, and `summary` from the full current day's content every time you write the file (not just the newest addition) — they describe the whole entry file, not the latest append.

Meeting files use this same `title`/`tags`/`summary` schema plus one additional optional field (`related`) — see §5.

## 4. Body — one heading per capture

Notebooks hold reflections, memories, ideas, research notes and ad-hoc thoughts, none of which comes in a fixed shape, and one day can hold several unrelated ones. So the body has no fixed sections: after the frontmatter, **each capture is one `## <heading>` with free prose under it**, in the order captured.

```markdown
## <what this capture is about>

<prose>

## <the next capture's subject>

<prose>
```

- **The heading names the capture's subject** ("From registers to ceremonies", "A walk that changed the plan"), never a fixed label such as "Notes" or "Today's update". A capture short enough not to need a heading still gets one.
- **A same-day capture is a new heading at the end of the file.** Never slot it into an earlier capture. If it continues an earlier capture the same day, add to that capture's prose instead.
- **Write the user's words.** Tidy them for reading, but keep the voice and don't add to the substance.
- **Helping draft a reflection.** When the user asks for help writing something up, work through three questions in the prose: *what happened*, *what it changed in how I see it*, *what I take forward*. They guide the draft; they are never headings.
- **An action inside a capture is a `- [ ]` line.** It keeps the action visible to the user's daily in-basket pass, which processes it into their task system. This skill never sends it anywhere.

This body applies to diary, projects, areaOfFocus, and areaOfInterest entries. Meetings use a different, fixed template — see §5. eDiary posts use no fixed section template at all (HTML narrative prose, not markdown) — see §10.

## 5. Meetings — one file per meeting, cross-referencing, and backlinks

Meetings are a flat top-level category (`notebooks/meetings/`), structurally like diary in that there's no per-meeting subfolder, but they diverge from every other notebook in two ways: file granularity (one file per meeting, not per day) and an optional cross-reference into another notebook.

**File naming.** `notebooks/meetings/entries/YYYY-MM-DD-<meeting-slug>.md`, one file per meeting. Multiple unrelated meetings on the same day get separate files (unlike diary/project/area notebooks, which are one file per day regardless of how many captures happen that day). The date reflects the actual/current occurrence — if a meeting is rescheduled, rename the file to match rather than tracking planned-vs-actual separately.

**Disambiguation — check calendar before asking.** If it's unclear which meeting a request refers to (e.g. more than one candidate meeting today, or which occurrence of a recurring meeting), and a calendar tool is available in the current session, check today's/near-term calendar events first — match by time, title, or attendees — before asking the user. A clear calendar match resolves it silently (the event title becomes the slug/title hint, the time picks the right occurrence). Only ask the user one focused question if no calendar tool is available in this session, or the calendar itself doesn't resolve the ambiguity (e.g. two events at the same time, or nothing matching found). Never ask when there's only one plausible candidate — resolving without friction is still the default.

**Frontmatter.** Same `title`/`tags`/`summary` schema as §3, plus one additional optional field:

```yaml
---
title: <short, agent-generated>
tags: ["#tag1", "#tag2", "#tag3"]   # up to 3, each "#"-prefixed
summary: <one-sentence executive summary, agent-generated>
related: <category>/<slug>          # optional — see "Cross-referencing" below
---
```

**Body template (fixed, verbatim section structure)** — designed to support both prep-before and notes-during/after a meeting in the same file:

```markdown
## Prep / Agenda
...

## Attendees
...

## Notes / Discussion
...

## Decisions
...

## Action items
...
```

Prepping for a future meeting fills in `Prep / Agenda` (and `Attendees` if known); capturing during/after fills in the rest. Regenerate frontmatter from the full current file content each time you write it, same discipline as §3.

**Cross-referencing (`related`).** When a meeting is obviously about an existing project, area-of-focus, or area-of-interest notebook, set `related: <category>/<slug>` (e.g. `related: projects/website-redesign`). Rules:

- Only reference a `category/slug` that actually exists as a live row in that category's registry (`notebooks/projects/index.md`, `notebooks/areaOfFocus/index.md`, or `notebooks/areaOfInterest/index.md`) — re-read the registry at write time, never guess or assume a slug exists from memory.
- Never ask the user to categorize a meeting — infer silently from context.
- If it's not obviously about anything, leave `related` empty/omitted. A meeting with no clear match simply stays in `meetings/`, untagged — never force diary as a fallback for a meeting specifically (this is the one exception to diary's normal catch-all role, per §1 rule 4).

**Backlink.** Whenever a meeting is tagged `related` to a project/areaOfFocus/areaOfInterest notebook, also add a lightweight row/line to that notebook's own `index.md` referencing the meeting (date + title + relative link back to the meeting file), so opening that notebook surfaces its meetings without a separate lookup in `meetings/`.

**Meetings registry.** `notebooks/meetings/index.md` lists all meetings chronologically with a Related column, so meetings can also be scanned as one flat list regardless of what they're tagged to. Update it every time a new meeting file is created (meetings update this registry far more often than the once-per-notebook-creation cadence of §8's category registries, since every meeting is its own row).

**Audit-on-request (not a standing script).** If the user asks to "check notebook tags" or similar, grep all `related:` frontmatter values under `notebooks/meetings/entries/` and cross-check each one against the three live registries (`notebooks/projects/index.md`, `notebooks/areaOfFocus/index.md`, `notebooks/areaOfInterest/index.md`), flagging any `related` value that doesn't match a live row. This is a behavior the agent performs live, on request, using its own file-reading tools — it is not a background job, script, or standing check that runs automatically.

## 6. Write safety — read-modify-write the full file

Always read the current full file content, then write back the **entire** file content (frontmatter + body) in a single write call. Never stream partial appends or write only the new fragment. This matters because the folder may be synced by a background client — a half-written file could sync mid-write. One read, one full-content write, every time.

This applies to every file this skill touches: the entry file (including meeting files), the per-notebook `index.md`, and (when applicable) the category registry `index.md` — including the meetings registry and any backlink row added to another notebook's `index.md`.

## 7. Index maintenance — inline, same turn, no periodic rescan

There is no background reindex job. Every time you write an entry file, in the same turn:

1. Update the entry's own per-notebook `index.md` (`notebooks/diary/index.md`, or `notebooks/<projects|areaOfFocus|areaOfInterest>/<slug>/index.md`) — one row per entry (date, title, tags, summary, relative link to the entry file). Add a new row for a new day; update the existing row's title/tags/summary if the day's file already had a row and you appended to it. This always happens.
2. Update the category registry (`notebooks/projects/index.md`, `notebooks/areaOfFocus/index.md`, or `notebooks/areaOfInterest/index.md`) **only if this write created a brand-new notebook** (see §8) — not on ordinary entry writes. Diary has no registry to update (there is only ever one diary).
3. `notebooks/index.md` (the top-level landing page) essentially never changes — it is a static description of the 6 fixed categories, not a per-notebook registry. Do not update it when creating or writing to a notebook.
4. For a meeting write, the equivalents are: update `notebooks/meetings/index.md` (every new meeting file gets a row — see §5), and if `related` is set, update the backlink row in the related notebook's own `index.md` (§5). Meetings have no per-notebook rollup index beyond the flat `notebooks/meetings/index.md` itself, since there is no per-meeting subfolder.
5. For an eDiary post write, the equivalents are: update `notebooks/eDiary/index.md` (every new post gets a row — see §10), and always update the backlink row in the source entry's own home-notebook `index.md` (§10) — unlike meetings, `related` is required for every eDiary post, so this backlink step is never conditional. eDiary has no per-notebook rollup index beyond the flat `notebooks/eDiary/index.md` itself, since there is no per-post subfolder.

## 8. Creating a new scoped notebook

To create a project, area-of-focus, or area-of-interest notebook (only when the user asks for a new scoped area, not for ordinary captures):

1. Determine the category — `projects`, `areaOfFocus`, or `areaOfInterest` (see §1 rule 6 if ambiguous).
2. Create `notebooks/<category>/<slug>/` with an `entries/` subfolder and an empty-but-headed `index.md` (same header/table shape as `notebooks/diary/index.md`).
3. Add one row to that category's registry (`notebooks/<category>/index.md`): slug, display name, created date (today), one-line purpose.
4. Do not create an entries file until the first actual capture happens.
5. Use the same frontmatter and body (§3, §4) as diary — no per-notebook schema variants unless a real, demonstrated need arises.

This section does not apply to meetings or eDiary — there is no "creating a new meeting notebook" or "creating a new eDiary notebook" step; each meeting or post is just a new entry file under the existing flat `meetings/` (§5) or `eDiary/` (§10) category.

## 9. Commit discipline

When `notebooks/` is in a git repository, commit after every write to a notebook file — small, frequent, per-write commits, not batched at end of session. This is what makes the git-based rollback guarantee real: uncommitted working-tree changes have no git-level history, only whatever file-version history the sync client keeps.

**Personal content stays out of shared history.** Notebooks hold personal reflections. If the repository is shared — a team project, anything others can clone — do not commit notebook files unless the user says so, and suggest keeping `notebooks/` out of version control (for example in `.gitignore`).

Suggested commit message shape: `notebook: <slug> <YYYY-MM-DD> — <short description>` (e.g. `notebook: diary 2026-08-06 — capture standup update`, or `notebook: meetings 2026-08-06-vendor-sync — capture meeting notes`, or `notebook: eDiary 2026-08-06-a-post-title — crystallize post`).

## 10. eDiary — AI-drafted HTML posts, required single-entry `related`, and head-plus-body metadata

`eDiary/` is a flat top-level category, structurally like meetings in that there's no per-post subfolder, but it diverges further than meetings does: the post file itself is **static HTML, not markdown**, and its `related` cross-reference targets **exactly one specific source entry** (not an entire notebook) and is **required**, not optional, because every post is drafted *from* something.

**When to invoke.** The user asks to crystallize, draft, or turn a raw capture into an eDiary post ("crystallize today's diary entry," "draft an eDiary post from the vendor-sync meeting," "make a post out of this"). This is agent-mediated, single-invocation drafting — there is no slash-command or wizard; a direct request in conversation is sufficient.

**Resolving the source entry.** Identify exactly one existing entry file to crystallize from — a diary day, a project/areaOfFocus/areaOfInterest day, or a meeting. Use the same resolution discipline as §1: if the user names or clearly implies the entry, use it; if genuinely ambiguous between two or more candidates, ask one focused question; never fabricate a source. An eDiary post is never drafted from nothing — if there's no identifiable source entry, this isn't an eDiary request (it's probably a fresh diary capture instead, per §1).

**File naming.** `notebooks/eDiary/entries/YYYY-MM-DD-<post-slug>.html`, one file per post, dated by the crystallization date (the post's own date, not necessarily the source entry's date). The slug is agent-generated from the post title, same convention as meeting slugs.

**AI-assisted drafting.** Read the full source entry, then produce a first-pass crystallized draft: narrative prose (not a restructured copy of the source's raw captures or sections), light prompting from the user is enough to steer tone/focus — this is meant to be a fast first pass, not a multi-turn wizard. The title must read as materially more considered than the source entry's filename or heading; do not just retitle the source. Only include an image block or video block if the user actually supplies image content/alt-text-worthy detail or a real video link — never fabricate placeholder media into a real post. `assets/post-template.html` carries both blocks commented out for that reason.

**Body structure (not a fixed-section template, unlike §4/§5).** Top to bottom: header block (`<h1>` title, date, 0–3 tags — same tag convention as §3), then narrative prose paragraphs optionally interspersed with full-width image blocks (`<figure class="post-image">`, real `alt` text required, optional `<figcaption>`) and at most one video block (`<div class="post-video">` with a label and a real `<a href>`, never a bare inline-text link), then a low-emphasis related citation. No enforced sub-headings — imposing the meetings-style fixed sections here would recreate the "still looks like raw notes" failure mode this feature exists to solve.

**Head-plus-body metadata (HTML has no frontmatter).** Every post carries the same four fields (`date`, `title`, `tags`, `related`) in **two places that must be kept in sync by hand**:

```html
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="date" content="{YYYY-MM-DD}">
  <meta name="tags" content="{#tag1, #tag2, #tag3}">
  <meta name="related" content="{category}/{...path — see below}">
  <link rel="stylesheet" href="../style.css">
</head>
```

...plus the visible `<header class="post-header">` block (title/date/tags) and `<footer class="post-related">` block (related citation) in the body — start every post from this skill's `assets/post-template.html`, which has the exact shape. **Note:** unlike markdown frontmatter (which is at least visible when the file is opened in any text editor), an HTML `<head>` is invisible when the file is opened in a browser — the normal way these posts get read. There is no mechanical link between the two copies; whichever regenerates a post (agent or human edit) must update both the `<head>` meta and the visible header/footer together, or they will silently drift with no in-browser signal that they've gone out of sync. Treat this as a manual discipline, same spirit as §3/§7's "regenerate from full current content every write," applied twice per file instead of once.

**Shared stylesheet.** All posts reference the single shared file at `notebooks/eDiary/style.css` via `<link rel="stylesheet" href="../style.css">` — never an inline per-file `<style>` block. One stylesheet lets the look change across every past post at once; the cost is that a post copied out on its own loses its styling. Keep it that way: no inline styles in a post, and ask the user before changing the approach.

**`related` — required, single-target, entry-level (not notebook-level).** This is the one place eDiary's cross-reference mechanic genuinely diverges from meetings' (§5), not just a syntax translation:

- Meetings' `related` points at an entire notebook (`<category>/<slug>`, e.g. `projects/website-redesign`) and is optional.
- eDiary's `related` points at **one specific dated entry inside a notebook** and is **required** — every post exists because it was crystallized from exactly one entry. Value format: `diary/<YYYY-MM-DD>` for a diary day, `meetings/<YYYY-MM-DD>-<meeting-slug>` for a meeting, or `<category>/<notebook-slug>/<YYYY-MM-DD>` for a project/areaOfFocus/areaOfInterest entry.
- **Validate against the live source, same discipline as §5:** before setting `related`, re-read the source notebook's own `index.md` (or the entries file directly) at write time to confirm that specific dated entry actually exists — never guess a date or slug from memory.
- The rendered `<a href>` in the visible `<footer class="post-related">` must resolve as a real relative path from `eDiary/entries/` back to the source file (e.g. `../../diary/entries/2026-08-06.md`), not just display the `category/date` label as inert text.

**Backlink.** Same mechanic as §5's meetings backlink, reused as-is: add a lightweight row to the source entry's own home-notebook `index.md` (e.g. `diary/index.md`, `meetings/index.md`, or the relevant project/area's per-notebook `index.md`) noting the eDiary post that crystallized it — date, a `↳ Crystallized: <post title> (eDiary)` label, and a relative link to the post file. Because `related` is always set for eDiary (unlike meetings), this backlink step is never conditional — it happens on every post write.

**eDiary registry.** `notebooks/eDiary/index.md` lists all posts chronologically with a Related column, same shape as `notebooks/meetings/index.md` (§5) — Date, Title, Related, Link. Update it every time a new post file is created.

**Explicitly out of scope for this category (do not build or reach for these):**
- No gallery, feed, or browsing UI — the index is a flat lookup list, not a designed browsing surface.
- No auto-publish, share button, or export-to-platform action of any kind.
- No JS, modal, wizard, or in-page interaction anywhere in a post — static single-file HTML only.
- No per-platform image/format tuning (e.g. no Instagram caption-length or LinkedIn aspect-ratio logic) — stay generic; the human reformats per platform manually if they choose to share.
- No multi-target `related` — one source entry per post, matching meetings' single-target shape, never a list.

## Explicitly out of scope (do not build or reach for these)

- No read/write coupling to sprint or ceremony tooling. Notebooks are plain markdown; other skills may be asked to read one as context, but no integration code exists or should be added.
- No search index, database, or embedding store. Retrieval is: read the top-level landing page or relevant category registry, read the relevant per-notebook index, read the entry file(s) if needed.
- No NL tag-based routing. §1's resolution rules are the entire routing mechanism.
- No purpose-built editor, file watcher, or sync client. Files are opened directly in any existing editor; whatever sync the folder already has is sufficient.
- No diary special-casing anywhere in behavior, folder shape, or template.
- No standing/background script to validate meeting `related` tags against the registries. The audit described in §5 is performed live, on request, by the agent's own file-reading tools — never automate it into a periodic job.
