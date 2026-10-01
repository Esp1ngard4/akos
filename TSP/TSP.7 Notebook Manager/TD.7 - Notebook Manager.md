# TD.7 — Notebook Manager

## Purpose

A place to write things down that is plain files and nothing else: a diary, notebooks scoped to a project, an area of focus or an area of interest, and meeting notes, all in Markdown under one `notebooks/` folder. The agent captures, files, indexes and retrieves; there is no app, no search index, no database and no sync client.

It has a second half: the **eDiary**. When a raw entry is worth more than a note, the agent drafts a crystallized post from it, a static HTML page that links back to the exact entry it came from. Capture stays fast and unpolished; crystallization is a separate, deliberate step.

**One convention serves every notebook.** The diary is not special: it has the same shape as any project or area notebook, and only its place in the folder tree differs. Meetings (one file per meeting) and eDiary posts (one HTML file per post) are the two real exceptions, and the skill says why for each.

## Status: In Progress

The capture and crystallization paths are used on real work. Parts of the convention have never been exercised, and that is the honest label.

| | |
|---|---|
| Diary captures | Used since August 2026, in the current one-heading-per-capture shape since late September |
| eDiary posts | One real crystallization, drafted from a diary entry, with its link and backlink |
| Fresh install | Tested: an empty project, installed under `.github/skills/`, builds its notebooks tree on first use (see *How it is tested*) |
| Meetings | **Never used.** The template, `related` link and backlink are specified, not exercised |
| Project, area-of-focus and area-of-interest notebooks | **Never created.** The registries ship empty and have not had a first row |

## Components

| Component | Location | Purpose |
|---|---|---|
| `notebook-capture` | `notebook-capture/SKILL.md` | The skill: resolution, file naming, entry shape, indexes, meetings, eDiary drafting, write safety |
| First-use assets | `notebook-capture/assets/notebooks/` | An empty notebooks tree: every `index.md`, and `eDiary/style.css`. The skill copies from it only to create a file that is missing, never over one that exists |
| Post template | `notebook-capture/assets/post-template.html` | The shape every eDiary post starts from. Read in place, never copied |
| Your notebooks | `notebooks/` at the root of the project the skill is installed in | **Source of truth.** Your data, not part of the tool; nothing here ships it |

There is no code. Like TSP.6, the tool is a skill and the files it reads, so the test checks layout and links rather than behaviour.

## Where your notebooks live, and who can read them

The skill finds `notebooks/` beside the folder that holds its skills folder. Installed under `your-project/.github/skills/`, that is `your-project/notebooks/`. It resolves this from its own location, not the working directory, so it works wherever the agent was started.

**A notebook is personal.** The installer (TSP.4) is built for sharing — commit the skill and everyone who clones the repo has it — and that is the wrong default for a diary. Two ways to use it safely:

- **Install it in a personal workspace**, a repository only you use. This is the intended setup.
- **In a shared repository, keep `notebooks/` out of version control** (`.gitignore`). The skill's own guardrail backs this up: it commits after every write only where the repository is yours, and in a shared one asks before committing anything.

Nothing in the tool sends content anywhere. An eDiary post is a file; sharing it is something you do by hand.

## First use

None of the tree exists until the skill needs it. On the first read or write it creates each missing file from `assets/notebooks/`, at the same relative path; `entries/` folders appear with the first capture that needs one. Once created, a file belongs to your notebooks and may change; the asset is a starting point, not a copy kept in sync. This repository ships no example entries or posts, deliberately: a seeded example is a thing to delete before you can tell what is yours.

## What the SKILL.md covers (and this document doesn't repeat)

`notebook-capture/SKILL.md` is authoritative for the folder convention, how a request is routed to a notebook (the diary is the catch-all), entry naming and frontmatter, the entry body (one heading per capture), the meetings template and its optional `related` link, the eDiary's head-plus-body metadata and required `related` link, index maintenance, write safety, and commit discipline. This document covers the rest: purpose, status, where the data lives and who can read it, naming, testing, relationships, maintenance and open items.

## Naming conventions

- **Entries:** `notebooks/<category>/[<slug>/]entries/YYYY-MM-DD.md`, one per day per notebook, dated by the day of capture. A second capture the same day is a new heading in the same file.
- **Meetings:** `notebooks/meetings/entries/YYYY-MM-DD-<meeting-slug>.md`, one per meeting.
- **eDiary posts:** `notebooks/eDiary/entries/YYYY-MM-DD-<post-slug>.html`, one per post, dated by when it was crystallized.
- **Notebook slugs** are chosen when a scoped notebook is created and recorded in its category's registry. The categories themselves are fixed: `diary`, `projects`, `areaOfFocus`, `areaOfInterest`, `meetings`, `eDiary`.

## How it is tested

`tests/smoke_test.py` installs the skill into an empty project with `install.py add` and checks what a new user would hit first:

- the skill and its `assets/` arrive, and no notebooks data comes with them;
- first use, done the way the skill describes, builds the whole tree, and every link on the landing page resolves;
- a second first-use run copies nothing, so it can never overwrite your notes;
- a post placed in `eDiary/entries/` finds the stylesheet, and every `assets/` path the skill names exists.

What is **not** tested is whether the agent routes a capture to the right notebook or drafts a good post. No test asserts that, and none can.

## Relationship to other tools

- **TSP.4 Tool Installer** — installs the skill with its `assets/`. Your `notebooks/` folder is never touched by `install.py`, so `update` and `diff` see only the tool.
- **TSP.3 TSP Register** — row 7. Type `Tool`; Status `In Progress`; Doc Aux `Yes`.
- **TSP.6 Content System** — no coupling. Both start from your own writing, and an eDiary post can become raw material for a piece, but nothing passes between them automatically.
- **No coupling to anything else, by design.** Other skills may read a notebook as context when asked; no integration code exists. A calendar, when the agent has one, is read only to tell two meetings apart.

## Maintenance

**Regular use** — capture and retrieval happen through the skill; the files are plain Markdown and open in any editor.

**Controls** — none run automatically. Checking meeting `related` links against the registries is a request ("check notebook tags"), performed live by the agent, never a background job.

**Before structural change** — the convention is the skill's contract with every file you have written; change it only with a migration of existing entries in the same step.

## Open items

| Item | Detail |
|---|---|
| Meetings and scoped notebooks unexercised | See *Status*. The first real meeting and the first project notebook are what would move this tool to `Implemented` |
| eDiary metadata is kept in sync by hand | A post carries its date, title, tags and `related` link twice — in `<head>` and in the visible header and footer — and nothing links the two. The template marks both; drift is still possible |
| The commit guardrail relies on the agent | Whether a repository is "shared" is the agent's judgement. `.gitignore` is the dependable control; the guardrail is the backstop |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-10-01 | Published as TSP.7. The skill ships an empty notebooks tree and the eDiary post template as `assets/`, so a fresh install builds what it needs on first use; smoke test added for the installed layout, first use and links. No entries or posts published — the tool ships, the author's notebooks do not. |
