---
name: artifact-register
description: Manages Artifact Registers — the inventory of documents, folders, tools and physical items belonging to a scope, recording what each is, where it lives digitally and physically, what contains it, and which tool governs its contents. Use whenever the user mentions "artifact register", "document control list", "reference material", or asks where something is filed, what is in a folder, how to file a new document, what ID something should get, which artifacts are overdue for review, or to create a register for a project or area. Also use when the user asks whether the filing matches the register, since this tool reconciles a register against the actual folder on disk. Trigger too on "add this to the register", "is this filed correctly", "retire this document", or when a project accumulates enough documents to need its own register.
---

# Artifact Register

Inventories the artifacts of a scope and where they live. One register per scope:
a global one for general reference material, and one per project or area that has
enough artifacts to be worth navigating.

Governance and rationale are in `TD.5 - Artifact Register.md`. This file covers
operation.

## Requirements

`openpyxl`. Everything else is standard library. Commands below write `python`,
correct on Windows; use `python3` on macOS/Linux.

## The rule that makes this tool work

**The register assigns an ID; the ID is written onto the artifact; position
follows ID.**

```
00.Admin/                            artifact 0
  07. Artifact Register, Atlas.xlsx  artifact 7 - the register, listing itself
04.Reference/                        artifact 4
  08. Site Survey.pdf                artifact 8,  Parent Digital = 4
  15. Floor Plan.pdf                artifact 15, Parent Digital = 4
```

Filename prefixes are `<ID>. <Name>` or `<ID>.<Name>`, with the ID **zero-padded**
to the register's width — `07.` not `7.`. Padding matters because sorting differs
by platform: Windows Explorer sorts naturally (1, 2, 10) while web clients, macOS
and `ls` sort lexicographically (1, 10, 2). Padded, the folder reads the same
everywhere.

The width lives on the register's `Settings` sheet as `ID width`, default 2.
Registers over 99 artifacts need 3. It is stored rather than derived, so adding
artifact 100 never silently re-pads everything beneath it.

Because the ID is on the artifact, the register makes a falsifiable claim about
the disk — which is what `audit` checks. A file with no prefix is visibly
unregistered, and one padded to the wrong width is a warning.

**Never reuse an ID**, including a retired one. A prefix on an old file or an old
email would then point at the wrong row.

## The delegation rule

Each row either owns its contents or hands them over:

- **`Managed By` set** — the register records the container and stops. Its
  contents belong to that tool.
- **`Managed By` blank** — this register owns the contents, and each gets an ID.

Values are written `TSP.n` and must name a live tool in your tool register.
`audit` checks this. (The prefix is `TOOL_PREFIX` in `schema.py` if your register
numbers things differently.)

## Schema

`Artifacts` sheet. The header row is detected rather than assumed, so a register
adapted from an existing spreadsheet works even if its headers are not on the row
this tool would have chosen.

| Column | Notes |
|---|---|
| `ID` | Unique, never reused, written onto the artifact |
| `Name` | As it appears after the ID prefix |
| `Description` | What it is and why it is kept |
| `Type` | `Folder`, `Document`, `Tool`, `Item` |
| `Location` | From the `Locations` sheet |
| `Parent Digital` | Containing artifact's ID, `Main` for a root, `N/A` if not digital |
| `Parent Physical` | Same, physically. **Both may be set** — a scanned and filed contract has two homes |
| `Managed By` | `TSP.n` of the governing tool, or blank |
| `Area of Focus` | Blank means general reference |
| `Owner`, `Created On`, `Status`, `Last Reviewed`, `Comments` | `Status` is `Active` or `Retired` |

Lookup sheets: `Locations` (ID, Location, Active, Kind) and `Areas of Focus`.

## Creating a register

The filename should carry the ID the register holds in its own scope; it seeds
itself as that artifact.

```
python create_artifact_register.py "7. Artifact Register, Atlas.xlsx" "Atlas" \
    --location "Physical:Office" --location "Digital:Cloud drive" \
    --area "5:Operations"
```

## Editing artifacts

`artifact.py` handles the operations where the register and the disk must
change together, because `Name` and the parent columns are encoded into the
filesystem. Editing those in the spreadsheet alone leaves the two disagreeing in
a way nothing detects — the audit matches on ID, not on name.

```
python artifact.py add    <register> <path> --name "Site Survey" --type Document \
                          --parent-digital 4 --root <folder>
python artifact.py add    <register> <path> --id 22 --root <folder>
python artifact.py rename <register> --id 22 --name "New Name" --root <folder>
python artifact.py move   <register> --id 22 --parent-digital 12 --root <folder>
python artifact.py retire <register> --id 22 --root <folder> --archive ./Archive --yes
python artifact.py repad  <register> --root <folder> [--width 3]
```

- **`add`** takes the next unused ID — never a gap left by a retirement — writes
  the row, and renames the file to `<ID>. <Name>` in one operation. With `--id`
  it instead re-prefixes the file of a row that already exists, which is the fix
  for an artifact whose prefix was lost.
- **`rename`** and **`move`** change the register and the file together. `move`
  acts on the disk only for `Parent Digital`; the physical parent has no
  filesystem meaning.
- **`retire`** disposes of the artifact and sets `Status = Retired`. It moves the
  artifact to `--archive` if you give one and **deletes it otherwise**. The row
  stays and the ID stays spent forever, so an old reference still resolves.

- **`repad`** brings every filename up to the register's ID width. Needed once
  when a register adopts padding, and again if the width is raised. **Only the
  number changes** — name, separator and extension are left exactly as they are,
  because rebuilding names from the register would quietly rewrite filenames that
  have legitimately drifted from it, which is a different decision.

`add`, `rename`, `move` and `repad` accept `--dry-run`. `retire` does nothing without
`--yes`, and **refuses to retire a container that still holds active artifacts** —
disposing of it would take registered children with it and leave rows pointing at
nothing. Retire the contents first.

Every operation re-runs the checks afterwards, so a half-completed edit reports
itself immediately instead of surfacing months later.

**Everything else is a plain field edit** — `Last Reviewed`, `Description`,
`Comments`, `Owner`, `Managed By`, `Area of Focus`, `Type`. Do those in the
spreadsheet. A command that writes one cell is a worse spreadsheet.

## Dashboard

Derived output — overwritten in full, never edited by hand. Tabs: overview,
artifacts (filterable), containment trees, review queue, findings.

```
python refresh_artifact_register.py "<register>.xlsx" "Artifact Dashboard.html" \
    --scope "Atlas" --root "<folder it describes>" --tsp-register "<tool register>.xlsx"
```

`--root` and `--tsp-register` are optional and take the same values as `audit`.
Pass them and the Findings tab carries the full audit; omit them and it says which
checks were skipped rather than implying a clean bill. The tab label shows a
count, so a register with problems announces them on open.

The Artifacts tab filters on Status, Type, Location, Area of Focus and Managed By.
Filters combine, each option shows its row count, and `(blank)` selects rows where
the field is empty — which is how you find artifacts still missing a `Type`.

## Audit

```
python audit_artifact_register.py "<register>.xlsx" \
    --root "<folder it describes>" --tsp-register "<tool register>.xlsx"
```

Exits non-zero on errors. Every finding is listed; `--summary` gives class names
and counts only.

Errors: duplicate IDs, invalid `Type`/`Status`, parents pointing at IDs that do
not exist or at themselves, `Managed By` naming a tool not in the tool register,
files on disk with no ID prefix, disk prefixes with no register row, one ID on two
unrelated entries.

Warnings, grouped by class: missing `Type` or `Status`, reviews older than two
years, rows claiming a digital home with nothing on disk, an ID carried by both a
folder and its own contents.

**The disk scan stops where the register stops** — at anything delegated, at
anything of `Type = Tool`, and at any container the register names no children
inside. That last boundary is read off the register rather than guessed: a folder
nothing claims as a parent is one artifact, and its contents are out of scope.
Without it the audit reports every file in every subfolder; on a real 23-row
register that was the difference between 218 findings and 7.

An unprefixed *directory* is reported once and not descended into, so one
unregistered folder is one finding rather than one per file within it.

The checks live in `checks.py` and are called by both `audit` and `refresh`, so
the terminal and the dashboard cannot report different findings.
