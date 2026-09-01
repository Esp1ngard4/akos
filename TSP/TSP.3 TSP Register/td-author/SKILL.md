---
name: td-author
description: Authors and audits Tool Definition (TD) documents and the SKILL.md paired with them — keeps the governance and reasoning (TD) separate from the operating instructions (SKILL.md), and enforces the document structure and version-history discipline. Use whenever a new tool is being created, a TD is being written or updated, a skill is being renamed or repackaged, an old tool version is being archived, or someone asks to review a tool's documentation for drift. Also use proactively on noticing a SKILL.md accumulating dated narration or changelog-style history, or a TD whose body has started describing what changed rather than how the tool works — that content belongs in the version history, and catching it early is this skill's job.
---

# Tool Definition Author

Every tool has a **TD** — the document that says why it exists and how it is
governed. Tools that are automated also have a **SKILL.md**. This skill owns the
first and polices the boundary between them.

The reasoning behind these rules is in the method: [governance
docs](../../../method/02-governance-docs.md), [source of
truth](../../../method/03-source-of-truth.md), [versioning
discipline](../../../method/05-versioning-discipline.md). This file is the
procedure.

**The boundary with `tsp-manager`: this skill owns the document, that one owns
the register row.** When a tool gains or loses a TD, write it here and flip
`Doc Aux` there. Neither does the other's write.

## The core split: TD vs SKILL.md

- **TD — the "why".** Purpose, components, governance, conventions,
  relationships to other tools, maintenance, version history. Dates and
  decisions live here.
- **SKILL.md — the "what and how".** Operating instructions, loaded into context
  every time the skill triggers. Durable rules and their *timeless* rationale
  belong here. Dated narration and "as of <date>" framing do not: every sentence
  of backstory is a permanent tax on every future invocation, whether or not
  that invocation needs it.

**The test for a borderline sentence:** would removing it change what the model
does on the next run? If yes, and the reasoning is timeless, it belongs in
SKILL.md. If it explains *how a rule came to be* rather than what to do, it
belongs in the TD.

## History belongs in the version history, not the body

The split above has a second edge inside the TD itself, and it is easier to
cross because the TD *is* where history belongs — just not anywhere in it.

- **Design rationale** — why the tool is shaped the way it is — belongs in the
  body, and is timeless. *"Two parent columns, because an artifact that is both
  scanned and filed has two real locations."*
- **Change narration** — what this version altered, replaced, merged or
  migrated — belongs only in the version history table. *"This document replaces
  the 2020 one and merges in the tool that had been running separately."*

**The test:** would the sentence still be true if the previous version had never
existed? If yes it is rationale and stays. If it only makes sense by reference
to what came before, it is history and moves to the table.

The failure mode is writing the TD in the same session as the change it
documents, when the migration narrative is still front of mind. Before declaring
a TD done, sweep the body for `replaces`, `previously`, `used to`, `earlier`,
`no longer` and bare years. Each hit is either a genuine open item, a provenance
note, or a line that belongs in the version history.

## TD structure

Mirror this order. Not every tool needs every section, but check each one
deliberately rather than skipping silently.

1. **Purpose** — what the tool is for.
2. **Components** — a table: component, provenance, location, purpose. **State
   which copy is the source of truth, in words.** Get this wrong and everything
   built on top inherits the error, because each new document copies the
   assertion from the last without anyone re-checking. A components table that
   has never been verified against the disk is a rumour.
3. **What the skill covers (and this document doesn't repeat)** — a pointer, so
   the TD does not duplicate content that will drift.
4. **Naming conventions** — files, identifiers, folders.
5. **Relationship to other tools** — how data flows to and from siblings,
   including deliberate boundaries and what stays manual.
6. **Maintenance** — regular use, plus periodic tasks.
7. **Open items** — what is known-wrong or undecided. A TD with no open items is
   usually a TD nobody has read critically.
8. **Version history** — the table. All the dated narration that must not live
   in SKILL.md goes here.

## Version history: order and length

**Newest first.** New entries at the top, the original at the bottom. This
sounds too obvious to state, and it isn't: entries get inserted one at a time,
and a table originally written oldest-first ends up sorted in two directions at
once. **Verify the whole column after editing, not just the row you added.**

**Keep the three most recent.** A TD is read to understand the tool as it is
now; an unbounded table buries that under superseded reasoning.

**Trimming never deletes history.** Before trimming, copy the whole TD to
`PreviousV/TD.<n> - <Name> v<version> (YYYY-MM-DD).md`. The full history rides
along inside that snapshot, so there is nothing extra to maintain. Leave a line
under the trimmed table pointing at the most recent snapshot.

Deliberately *not* the approach: a separate curated history document. It is a
second file to keep in sync, the rule is easy to forget, and when it is
forgotten it rots silently — whereas a snapshot is worth taking before a
structural edit anyway.

## Process

### A new tool

1. Claim the ID through `tsp-manager` — do not invent one.
2. Build the tool. Write the TD **after** the design has actually been
   exercised; writing it earlier just means rewriting it once the design shifts.
3. Write the TD from [`templates/TD-template.md`](../../../templates/TD-template.md).
4. Set `Doc Aux` and the `Skill` column through `tsp-manager`.
5. Final pass on SKILL.md for the split above — easy to violate in the
   satisfaction of having just made something work.

### Updating a tool

1. Change the tool first.
2. Add a version-history entry saying what changed **and why**.
3. Sweep SKILL.md for narration describing *this specific change* rather than
   the durable rule it produced. Move it to the TD.
4. Sweep the TD body with the grep list above.

### Auditing a pair

1. Read both documents in full.
2. **Check the components table against what is actually on disk.** Verify;
   do not trust the document's own prior claims.
3. Check SKILL.md for dated or historical language.
4. Check that the "what the skill covers" pointer has not itself drifted into
   duplicating the real SKILL.md.
5. Report findings. Do not silently fix beyond what was asked — a full audit
   turns up more than the request.

## Verification discipline

**Never mark a documentation change done without reopening the file and
confirming the edit landed.** This is not paranoia: a register elsewhere in this
collection logged several schema changes as complete that a later inspection
found had never been written to the live files. The same applies to anything
with a current-versus-stale split — a renamed skill's old package, a generated
view built from data that has since changed.

## Relationship to other skills

- **`tsp-manager`** — the other half of this same tool. It owns the register
  row; this owns the document.
- **A skill scaffolder** (Anthropic's `skill-creator`, or equivalent) covers the
  generic mechanics of building and evaluating a skill. This skill layers the
  governance on top — use both when creating a tool, not one instead of the
  other. It is externally supplied, so it is referenced rather than vendored
  here; see [owned vs. used](../../../method/04-owned-vs-used.md).
