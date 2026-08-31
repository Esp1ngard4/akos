---
name: my-skill
description: What this does AND when to use it. Both halves matter - see the notes below. Use whenever the user mentions <the words they will actually type>, or asks to <the concrete things it handles>.
---

# My Skill

> Template. Delete these quoted notes as you fill it in.
>
> This file is loaded into the agent's context **every time the skill triggers**, so
> everything here is paid for on every run. Durable rules and their timeless
> rationale belong here; the story of how a rule came to be belongs in the
> governance doc. See `method/01-skills-and-governance-docs.md`.

One or two sentences: what this skill operates on, and the single most important
thing to understand about it.

## Requirements

Anything that must be installed, and how. Note the invocation difference if it
matters — `python` on Windows, `python3` on macOS/Linux.

## Files

| File | Role |
|---|---|
| `<path>` | **Source of truth.** All edits go here |
| `<path>` | Generated output — overwritten on refresh, never hand-edited |
| `scripts/<name>.py` | What it does |

> Bundled scripts and resources are supported inside a skill folder, but **you must
> reference them here** for the agent to pick them up.

Point at the governance doc for the reasoning, so this file doesn't duplicate it.

## Schema

If the skill operates on structured data, describe it exactly: sheet or table
names, where headers live, what each field means, allowed values, and which fields
are computed. Be specific enough that the agent doesn't guess — guessing is where
data gets corrupted.

## Operations

One subsection per task, in the order they're usually done. For each: the steps, and
any check that must happen first.

State the destructive guardrails plainly — what must never be overwritten, what
must be backed up first, what must be read before it's written. An agent will
follow an explicit prohibition; it cannot infer one.

## Relationship to other skills

Which skills this hands off to, which hand off to it, and where the boundary sits.
If two skills touch the same artefact, say which one owns writing it.

---

## Writing the description

The `description` is the entire triggering mechanism — the agent decides whether to
load this skill based on it alone. Two failure modes:

**Too narrow, and it never fires.** A description written in your own private
vocabulary won't match anything you actually type. Names of internal systems,
project codes and house jargon are invisible to the matching.

**Too vague, and it fires constantly.** "Helps with documents" competes with
everything.

Write it as: *what it does* + *when to use it*, using the words a user would
naturally say. Include the synonyms — if you might say "backlog" or "work
breakdown" or "roadmap items", list all three. Err slightly toward the pushy side;
under-triggering is the more common failure.

## Optional frontmatter

- `argument-hint` — hint text shown in the chat input.
- `user-invocable` — whether it appears as a slash command.
- `disable-model-invocation` — stops automatic loading; the user must invoke it.
- `context: fork` — run in a dedicated subagent.

Support varies by agent; `name` and `description` are the portable core.
