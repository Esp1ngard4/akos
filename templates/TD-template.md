# TD.`<N>` — `<Tool Name>`

> Template. One of these per tool, kept beside the tool. It holds the *why*;
> the tool's `SKILL.md` holds the *what and how*. Delete these quoted notes.

## Purpose

One or two paragraphs: what the tool is for, and what question it answers that
nothing else does. If the tool has more than one half (e.g. a register plus the
documentation of what it registers), say so here.

## Components

> The most important table in the document, and the easiest to get subtly wrong.
> State the source of truth explicitly and verify it against what is actually on
> disk — do not trust a previous version of this table.

| Component | Location | Purpose |
|---|---|---|
| `<Register>.json` | `<path>` | **Source of truth.** All edits happen here |
| `<Dashboard>.html` | Same folder | Generated static snapshot; overwritten on every refresh, never hand-edited |
| Skill / scripts | `<path>` | Automation: create, refresh, audit |
| `PreviousV/` | `<path>` | Superseded versions, as descriptive subfolders |

## What the SKILL.md covers (and this document doesn't repeat)

Point at the tool's `SKILL.md` for the column schema, allowed values, and the
operational procedures. Say explicitly that this document covers the rest: purpose,
naming, relationships, maintenance, open items, version history. This is what stops
the two documents drifting into duplicates of each other.

## Naming conventions

- Identifier rules — and whether IDs are permanent. If they are, say why: reused
  IDs silently rebind existing cross-references.
- File naming.
- Folder naming, keyed off a **stable** identifier, never a mutable code or
  position that is expected to be renumbered.
- Controlled vocabulary, and whether it may be changed.

## Relationship to other tools

How data flows to and from siblings, and the deliberate boundaries — what is
automated versus what stays manual, and why. Name anything that is *not* synced
automatically; silence there reads as a promise the tool doesn't keep.

## Maintenance

**Regular use** — the routine: edit the register, refresh the dashboard, and how
often each happens.

**Controls** — any recurring check that keeps the tool alive, with its cadence and
where it is executed (inside an existing review, or standalone). A control that
exists only in a document and never runs is worth recording honestly as such.

**Before structural change** — snapshot the register into `PreviousV/`.

## Open items

| Item | Detail |
|---|---|
| | Known gaps, deferred decisions, things deliberately not fixed and why |

> Keeping this honest is what makes the document trustworthy. An open item recorded
> is a decision pending; an open item omitted is a surprise later.

## Version history

> Newest first. **Keep three entries.** Before trimming, copy the whole document to
> `PreviousV/TD.<N> - <Name> v<version> (YYYY-MM-DD).md` — the full history rides
> along inside that snapshot, so there is no separate history file to maintain.
> Then leave a pointer line under the table.

| Version | Date | Changes |
|---|---|---|
| v1.0 | YYYY-MM-DD | Initial version |
