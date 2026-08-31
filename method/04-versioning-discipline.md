# 4. Versioning discipline

**Keep the history without letting the history swallow the document.**

A governance document accumulates version entries. Each one is worth writing — the
reasoning behind a change is exactly what stops it being undone later. But after a
couple of years the version table is longer than the document, and the thing people
actually came to read is below the fold.

Three rules handle it.

## Newest first

New entries at the top; the original `v1.0` at the bottom. A reader wants the
current state, and the most recent changes are the ones most likely to explain what
they're looking at.

This sounds too obvious to state. It isn't, because of *how* entries get added: you
insert each new row above the previous one, and if the table was originally written
oldest-first, you end up with a table sorted in two directions at once — a
descending block sitting on top of an ascending tail. It reads as fine until
someone tries to find the oldest entry.

**Verify the whole column after editing, not just the row you added.**

## Keep three

Three entries is enough to see the recent trajectory. Beyond that you are reading
archaeology.

Pick a number and hold to it; the specific number matters less than having one, because
"trim it when it gets long" is not a rule anyone executes.

## Snapshot the whole document before trimming

This is the part that makes the other two safe.

Before removing entries, copy the entire document:

```
PreviousV/DF.37 - WBS Register v2.1 (2026-08-31).md
```

The full history rides along **inside the snapshot**. Nothing is lost, and there is
no separate history file to maintain.

Then leave a pointer under the trimmed table:

> Earlier entries are not kept here. The full history lives inside the DF snapshots
> in `PreviousV/` — most recently `PreviousV/DF.37 - WBS Register v2.1 (2026-08-31).md`.

## What was rejected, and why

**A dedicated version-history document.** The obvious alternative: move old entries
into `HISTORY.md` and keep the DF lean. It fails on discipline — it is a second file
to keep in sync, and the rule ("every trim, append to the archive") is exactly the
kind of thing that gets skipped once and then rots silently. A snapshot has no such
failure mode, because it is a whole-file copy you would want before a structural
edit anyway.

**Relying on git or cloud file history alone.** Tempting, and it costs nothing —
but it assumes the document is committed (folders sit untracked for longer than
anyone expects), that retention outlives your interest in it, and that whoever
wants the history knows to go looking in a tool rather than the folder. Version
control is the safety net, not the record.

## What belongs in an entry

Not just what changed — **what it replaced and why**. An entry that says *"added
the Skill column"* tells a future reader nothing they can't see. An entry that says
*"added the Skill column; it was argued against on the grounds that skills all live
in one directory and could be derived from disk, which turned out to be false —
they are scattered across three locations"* prevents the column being removed on
the same wrong reasoning.

Record reversals explicitly. A decision that was made, unmade, and remade is the
most valuable thing in the table, because it is the one most likely to be attempted
a third time.
