# AKOS — Agentic Knowledge Operating System

A method for building agent skills that are still trustworthy a year later.

Agent skills are easy to create and easy to accumulate. What is hard is everything
after: knowing which ones exist, where the authoritative copy lives, why a rule is
there, whether a skill still works, and what to do when two copies disagree. Those
problems don't show up on day one — they show up once you have a dozen skills and
no memory of building the first three.

AKOS is the set of conventions that answer those questions, plus three working
tools that demonstrate them.

## The method

Five conventions. Each is short, each came from an actual failure, and each is
independent — adopt them in any order.

| | |
|---|---|
| [Skills and governance docs](method/01-skills-and-governance-docs.md) | Every skill needs a second document. What goes in which, and the test for the borderline cases |
| [Source of truth](method/02-source-of-truth.md) | A skill in two places will drift. How to make that structurally impossible instead of merely discouraged |
| [Owned vs. used skills](method/03-owned-vs-used-skills.md) | You wrote some skills and merely installed others. They need opposite treatment, and getting it wrong loses one of them |
| [Versioning discipline](method/04-versioning-discipline.md) | How to keep a document's history without the history swallowing the document |
| [Registering your tools](method/05-registering-your-tools.md) | An inventory that reconciles against reality, so "what do I actually have" has an answer |

## The tools

Three registers, each an `.xlsx` source of truth with a generated HTML dashboard.
They exist to demonstrate the method on something real — but they are ordinary
working tools and useful on their own.

| Skill | What it manages |
|---|---|
| [`wbs-manager`](examples/.github/skills/wbs-manager) | Work breakdown / backlog: items, effort, sprint allocation |
| [`raid-dashboard`](examples/.github/skills/raid-dashboard) | Risks, Actions, Issues, Decisions, Ideas, with a probability × severity heat map |
| [`tsp-manager`](examples/.github/skills/tsp-manager) | The inventory of your tools themselves, and the recurring controls that keep them alive |

`tsp-manager` is the one that closes the loop: it is the register that knows which
skills exist, and it reconciles that list against what is actually installed.

## Try it

Skills are loaded from `.github/skills/`, `.claude/skills/` or `.agents/skills/` by
GitHub Copilot in VS Code, and the same `SKILL.md` format is read by Claude Code,
Cursor, Codex CLI and others. Copy the folder you want into your repo and the agent
picks it up — no registration step.

```bash
cp -r examples/.github/skills/wbs-manager  <your-repo>/.github/skills/
pip install openpyxl
```

Then ask your agent in plain language — *"create a WBS for project Atlas"*, *"add a
risk about the vendor deadline"*, *"what's overdue for review?"* Skills trigger on
their `description`, so nothing needs invoking by name.

Every script also runs standalone, with no agent involved:

```bash
python .github/skills/wbs-manager/scripts/create_wbs.py "WBS Atlas.xlsx" "Atlas"
python .github/skills/wbs-manager/scripts/refresh_wbs.py "WBS Atlas.xlsx" "WBS Dashboard.html" "Atlas"
```

Requires Python 3.9+ and `openpyxl`. Nothing else — every other import is standard
library. The dashboards load Chart.js and Grid.js from a CDN; offline, tables render
and charts don't.

## Templates

[`templates/DF-template.md`](templates/DF-template.md) — the governance document
structure described in the method.
[`templates/SKILL-template.md`](templates/SKILL-template.md) — a skill skeleton with
the frontmatter fields that matter and notes on writing a `description` that
actually triggers.

## Where this came from

These conventions were extracted from a personal knowledge and project management
system, where the tools grew organically over several years and the governance was
reverse-engineered after the drift had already happened. Every rule here has a
specific failure behind it, and the method documents say which — because a rule
whose reason you can't remember is a rule you will eventually undo.

Nothing from that personal system is included here. The tools are generic, the
examples are invented, and the vocabulary has been stripped of anything local.

## License

MIT — see [LICENSE](LICENSE). Use, adapt and redistribute freely.
