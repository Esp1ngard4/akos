# 5. Registering your tools

**"What do I actually have?" should have an answer you can check.**

Tools accumulate faster than memory. Scripts, skills, spreadsheets, procedures,
half-finished automations. Some are load-bearing, some were replaced two years ago,
and from the outside they look identical — a folder with a plausible name.

A register is one row per tool, recording what it is, whether it's still used, and
when you last looked at it. The `tsp-manager` skill in this repo implements one;
the idea works with any storage you like.

## What a row needs

| Field | Why |
|---|---|
| **ID** | A permanent identifier — see below |
| **Name** | Matching the folder, where there is one |
| **Status** | Planned / In Progress / Implemented / Obsolete |
| **Relevancy** | How much it actually gets used — a *separate axis* from status |
| **Skill** | Which automations serve it, if any |
| **Doc** | Whether a governance doc exists |
| **Last Reviewed** | Blank means never, and that is worth seeing |

**Status and Relevancy must be separate.** A tool can be fully `Implemented` and
used twice a year, or barely finished and central to everything. Collapsing these
into one field is what produces a register full of `Implemented` tools that nobody
has opened since 2019.

## IDs are permanent

Once assigned, an ID is never reused, renumbered, or reclaimed. Gaps in the
sequence are retired tools. A new tool takes `max(ID) + 1`.

This costs nothing and prevents something expensive: identifiers leak out of the
register into folder names, document cross-references, and years of notes. Reusing
`24` because the original tool was retired silently rebinds every one of those
references to something unrelated, and nothing errors.

If IDs also name folders — `<prefix>.<id> <name>/` — then the register row is what
gives the folder meaning, and the folder is just storage.

## Reconcile against reality, in both directions

A register that is only ever written to is a wish list. The value comes from
checking it against the disk:

- **Folders with no row** — undocumented tools, or something someone else added.
- **Rows with no folder** — may be fine (not everything needs storage), or may be a
  tool that was deleted without being retired.
- **Skills named but not installed** — a broken reference.
- **Skills installed but named nowhere** — automation nobody decided to keep.
- **Values outside the controlled vocabulary** — typos, or a vocabulary that has
  drifted from how you actually work.

That last one deserves attention. When the data disagrees with the allowed values,
**the data is usually right.** In the system this method came from, only 3 of 31
recurring activities matched the official frequency list — the list had simply
never been adopted. The fix was to rewrite the list, not the 28 rows.

## Controls: the part that makes it live

Alongside the inventory, record the recurring upkeep each tool needs — and when it
was last done. Then:

- **Periodically**, work the items whose next-due date has passed.
- **Annually**, walk the register and ask per tool: is it still used? If so, do I
  want to improve it? Batch improvements into a project rather than doing them
  inline, or the review becomes an unbounded refactor and you stop doing it.

**Stamp the review date on every row you touch, whatever the answer.** An unstamped
row is indistinguishable from one never looked at — which is precisely how a review
cadence dies without anyone noticing.

## Make the recompute mechanical

If a control activity's next-due date is calculated — last done plus an interval —
make sure something actually calculates it.

A frequency column with a `Days` value looks like a working mechanism. Check that
it *is* one. In the system this came from, every due date had been typed by hand
and nothing consumed the interval at all; the entire schedule was years overdue and
the reason was structural, not negligence. A control nobody can execute is not a
control.
