# TD.5 — Artifact Register

## Purpose

An inventory of the artifacts belonging to a scope — documents, folders, tools and
physical items — recording what each one is, where it lives digitally and
physically, what contains it, and whether anything else governs its contents.

It answers two questions that a folder tree alone cannot:

- **Where is it?** Especially for physical things. "Where is the signed lease" has
  no other source of truth once the answer is a filing cabinet.
- **What is inside this container, and who governs it?** The register records a
  container and then either owns its contents or hands them to another tool.

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.5 Artifact Register/` | Governance: purpose, mechanism, conventions, history |
| `artifact-register` skill | owned | `TSP.5 Artifact Register/artifact-register/` | Operating instructions and scripts |
| `<ID>. Artifact Register, <Scope>.xlsx` | owned, per scope | with the artifacts it describes | **Source of truth** — one per scope |
| `Artifact Dashboard.html` | generated | alongside each register | Derived view; overwritten on refresh, never hand-edited |

There is no template file — `create_artifact_register.py` builds the register
programmatically, so the schema has exactly one definition.

**There is no master register.** Each register is independently authoritative for
its own scope; none contains or supersedes another. A register lives with the
artifacts it describes and holds an ID in its own scope, because it is itself an
artifact of that scope.

## What the skill covers (and this document doesn't repeat)

`artifact-register/SKILL.md` is authoritative for the column schema, every command
and its arguments, what each audit check does, and which edits belong to
`artifact.py` rather than to the spreadsheet.

This document covers the rest: the mechanism the tool rests on, how scopes divide,
the delegation rule, and the reasoning behind both.

## The mechanism: the ID is written onto the artifact

This is the whole idea, and it is easy to skim past.

1. The register assigns an **ID**, unique within that register and never reused.
2. The ID is written onto the artifact itself — a filename prefix for digital
   things, a label for physical ones: `<ID>. <Name>`.
3. Position follows ID. Inside a folder or a physical binder, artifacts sit in ID
   order.

```
0.Admin/                            artifact 0
  7. Artifact Register, Atlas.xlsx  artifact 7 - the register, listing itself
4.Reference/                        artifact 4
  8. Site Survey.pdf                artifact 8,  Parent Digital = 4
  15. Floor Plan.pdf                artifact 15, Parent Digital = 4
```

Two things follow, and they are why this is worth the discipline.

**The filesystem becomes readable as the register**, without opening it. A file
with no prefix is visibly unregistered — the convention announces its own
breaches rather than letting them accumulate quietly.

**The register's claims become falsifiable.** Most registers can only be checked
against themselves: are the IDs unique, do the fields have legal values. This one
makes an assertion about the world that a script can go and test. That is the
difference between a document that is internally consistent and one that is
actually true, and it is the reason this tool can catch a filing error that a
person would find years later, if ever.

## Scopes

One tool, one register per scope — the same shape as
[WBS](../TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md) and
[RAID](../TSP.2%20RAID%20Register/TD.2%20-%20RAID%20Register.md).

A scope gets its own register when it has enough artifacts to be worth navigating
— roughly a dozen. Below that, a general register with an `Area of Focus` value is
enough. A scoped register lives **with the artifacts it describes**, not with the
tool.

## The delegation rule

**The register records a container, then stops if something else governs the
inside.**

- A folder of project management documents → `Managed By` the tool that governs
  them. The register records the folder and does not inventory its contents.
- A folder of assorted certificates → **blank**. Nothing else governs it, so this
  register owns the contents and each one gets an ID.

Without this rule the register has to inventory everything and collapses under its
own weight. With it, the register is a map of boundaries rather than a list of
files.

**Every `Managed By` value must name a live tool in the tool register.** A
delegation to a tool that no longer exists is an artifact nobody governs, and it
looks identical to one that is properly handled — the most dangerous state
available, because it reads as safe.

### The rule applies to the disk scan too

This is the part that took a rewrite to get right. The audit walks the folder the
register describes, and its first version reported **218 findings on a 23-row
register** — every file inside every subfolder, including folders that belonged to
other tools entirely.

The fix was not a filter. It was recognising that **the scan has to stop exactly
where the register stops**. Three boundaries:

| Boundary | Why |
|---|---|
| `Managed By` is set | Another tool owns those contents |
| `Type = Tool` | A tool manages its own internals |
| Nothing in the register names this artifact as its parent | The register treats it as one artifact; its contents are out of scope |

The third is the one that matters, and it is **read off the register rather than
guessed**: a container the register inventories is one that something claims as a
parent. With it, 218 findings became 7 — all genuine.

That generalises past this tool. A check that reports everything technically
wrong is not a strict check, it is an unusable one, and the cure is usually to
find the boundary the system already declares rather than to invent a threshold.

## Filing category is derived, not declared

Whether an artifact is grouped, stored away from its usual place, or governed by
its own rule follows from `Parent`, `Location` and `Managed By`. There is no
category name to assign or remember, and no way for a category to disagree with
the facts it summarises.

## An artifact can be in two places at once

`Parent Digital` and `Parent Physical` are separate columns because a contract
that is both scanned and filed has two real locations. A single parent column
forces a choice between them and loses half the answer.

## Which edits need a command

**Automate the operations that must keep two things in step; leave the rest to the
spreadsheet.**

`Name` and the parent columns are encoded into filenames, so changing either in
the register alone leaves it disagreeing with the disk in a way nothing detects —
the audit matches on ID, not on name. Those get commands: `add`, `rename`, `move`,
`retire`.

Everything else is a field edit, and a command that writes a single cell is a
worse spreadsheet than the spreadsheet.

`retire` disposes of the artifact and keeps the row with its ID spent forever, so
an old reference still resolves to what it was. It archives if given somewhere to
archive to and deletes otherwise, and it refuses to retire a container still
holding active artifacts — disposing of it would take registered children with it
and leave rows pointing at nothing.

## Relationship to other tools

- **[TSP Register](../TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md)** —
  `Managed By` points into it, and this tool is registered there. The two are
  reciprocal: the tool register says what governs things, this register says what
  is governed.
- **[WBS](../TSP.1%20WBS%20Register/TD.1%20-%20WBS%20Register.md)** — a register
  whose rows carry acceptance criteria and sprints is a WBS, not this. If you find
  yourself adding a status workflow to an artifact register, you have the wrong
  tool open.

## Maintenance

1. **Assign the ID before filing anything.** The prefix goes on at the same moment
   as the row, or it never goes on. `artifact.py add` does both.
2. **Stamp `Last Reviewed`** whenever an entry is touched.
3. **Run `audit --root` periodically.** It is the only check in this collection
   that compares a register against reality rather than against itself.
4. **Review physical artifacts annually** — confirm each is still worth keeping,
   and retire what is not.

## Open items

| Item | Detail |
|---|---|
| Header row is detected, not fixed | Registers this tool creates put headers on a known row, but the reader scans for them so a spreadsheet adapted from elsewhere still works. Slight complexity for real adoption benefit |
| `retire` deletes by default | `--archive` is available and safer. The default is deletion because an artifact register that quietly keeps everything stops being true about the shelf — but it is the sharpest edge in this collection |
| Physical artifacts cannot be reconciled | The disk check only reaches digital ones. A physical artifact's location is an assertion no script can test, which is exactly why the annual walk-through exists |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-08-31 | Initial public version. Generalised from a personal reference-material system dating to 2016 and a separately-built per-project document control list, which turned out to be the same tool at two scopes using the same mechanism |
