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

`status` takes a sprint's end from the calendar where the calendar holds the sprint, then from the dates in the record's heading, and failing both from the planning date plus `--length` days (default 14). "Due" means within `--due-in` days (default 3).

## The calendar

Any JSON file with a `sprints` list of `{"Sprint", "Starts", "Ends"}`: the agile-conventions file `wbs.py sprints seed` writes, or a WBS register that imported it. Sprint IDs are `S<YY>.Q<N>.<X>`; `wbs-manager` explains the convention and how to seed it from a real sprint start date.
