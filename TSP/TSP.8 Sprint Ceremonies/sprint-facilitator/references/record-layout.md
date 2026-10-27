# The sprint record — lookup data

What each ceremony is for is in TD.8. How to run each is in `SKILL.md`. This file holds only what those steps look up.

## The file

`<records>/<sprint ID>.md`: one Markdown file per sprint, named for the ID alone (`S26.Q3.6.md`), with the heading `# Sprint <ID> (<dd-Mon> / <dd-Mon>)`. With `--calendar`, `plan` takes the dates from the sprint calendar. Without it, give them in the label.

Its sections, in order:

| Section | Written | By |
|---|---|---|
| `## Planning — <date>` | once, at planning | `plan` |
| `## Review — <date>` | once, at the close-out | `review` |
| `## Retrospective — <date>` | once, after the close-out | `retro` |
| `## Noticed` | any time during the sprint | by hand, one row per finding |
| `## Next sprint - draft` | any time; drained at grooming | by hand |
| `### Draft goals` | any time; carried into the next planning | by hand |

The first three are **events**: written once, never touched again, and in that order. The last three are **living**: they accumulate from the day the sprint opens. `review` and `retro` insert their block before the living sections, so the arc still reads as a chronology.

## The script

| Command | Does | Refuses |
|---|---|---|
| `plan <records> <label> [--calendar F]` | Creates the record with its Planning block. Carries the previous record's *Draft goals* in, marked `draft:` | A sprint already planned |
| `review <records> <label>` | Adds the Review block | A sprint never planned; a second review; a review after the retro |
| `retro <records> <label>` | Adds the Retrospective block | A sprint never planned; a second retro |
| `status <records> [--calendar F]` | Says what is due or outstanding, in sentences meant to be read out | — |
| `goals <records> [--json]` | Reads every record's goals back: verdicts, bets, carried goals, the share of committed hours that serve a goal. Lists what breaks the layout and exits 1 when anything does. A report consumes `--json` rather than parsing Markdown | — |

`status` takes a sprint's end from the calendar where the calendar holds the sprint, then from the dates in the record's heading, and failing both from the planning date plus `--length` days (default 14). "Due" means within `--due-in` days (default 3).

## The goal tables

The goals are data a report counts, so three tables keep a fixed shape:

| Block | Table | Columns |
|---|---|---|
| Planning | *Iteration goals* | `ID` (`G1`, `G2`…, unique within the sprint) · `Goal` · `Done when` · `Bet` (the longer-cycle bet or objective it serves, or blank) · `Carried from` (`<sprint ID> <goal ID>`, only for a goal continuing an earlier one) |
| Planning | *Committed items* | `Item` · `Effort` (`Xh`) · `Area` · `Goal` (`G1`, `G1, G3`, or blank) · `Notes`. A pull-in's row is added the day it is pulled in, its `Notes` saying `**pulled in <DD-Mon>**` and `effect:` (`SKILL.md`, *A pull-in states its effect on committed work*); `Item` names the row as `<scope> <ID> <title>`, which `wbs.py pullins` reads |
| Review | *Iteration goals* | `ID` · `Goal` · `Achieved` (`Yes` / `Partial` / `No`, nothing else) · `Why` |

The Review also opens with *Highlights*: one paragraph. In *Committed items*, a struck-through row was dropped and an all-bold row is a subtotal heading; `goals` skips both when it sums hours. A record whose goals table has no `ID` column reads as `unstructured`, never guessed at.

## The calendar

Any JSON file with a `sprints` list of `{"Sprint", "Starts", "Ends"}`: the agile-conventions file `wbs.py sprints seed` writes, or a WBS register that imported it. Sprint IDs are `S<YY>.Q<N>.<X>`; `wbs-manager` explains the convention and how to seed it from a real sprint start date.
