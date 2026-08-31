# AKOS — Agentic Knowledge Operating System

A method for structuring the tools and systems you depend on, so that agents can
safely operate them.

Not "how to write agent skills." Skills are the easy part. The hard part is the
estate underneath: knowing what you actually have, which copy is authoritative, why
a rule exists, whether a tool is still used, and where something came from if you
have to reinstall it. Those questions don't matter on day one. They matter at tool
number thirty, when you no longer remember building the first ten.

AKOS is the set of conventions that answer them, plus three working tools that
demonstrate the conventions on something real.

## The idea in one paragraph

**The unit is the tool, not the skill.** A tool is anything you depend on and would
have to rebuild — a spreadsheet with logic in it, a script, a documented procedure,
a configured third-party app. A skill is one thing a tool can *have*: the interface
that lets an agent operate it. In the estate this came from, 91 tools are registered
and **8 have a skill**. Organise around skills and you have a method that describes
eight things. Organise around tools and the skills fall out as an attribute — a
column on a row.

"Agentic" then means something precise: a tool becomes agent-operable when it has an
explicit source of truth, a documented schema, stated guardrails, and a registry
entry. Three of those four are worth having with no agent involved at all. **The
work of making a tool agent-ready is mostly the work of making it well-governed.**

## The method

Six short pieces. Each came from an actual failure, and each says which — a rule
whose reason you can't remember is a rule you will eventually undo.

| | |
|---|---|
| [0. The unit is the tool](method/00-the-unit-is-the-tool.md) | The assumption everything rests on, and what makes a tool agent-operable |
| [1. Registering your tools](method/01-registering-your-tools.md) | **The spine.** An inventory that reconciles against reality |
| [2. Governance docs](method/02-governance-docs.md) | Every tool needs a second document. What goes in which, and the test for borderline cases |
| [3. Source of truth](method/03-source-of-truth.md) | Anything in two places will drift. How to make that impossible rather than discouraged |
| [4. Owned vs. used](method/04-owned-vs-used.md) | You built some, you installed others. Opposite treatment, and getting it wrong loses one |
| [5. Versioning discipline](method/05-versioning-discipline.md) | Keeping history without the history swallowing the document |

Start at [0](method/00-the-unit-is-the-tool.md) if you want the reasoning, or
[1](method/01-registering-your-tools.md) if you'd rather see the mechanism first.

## The tools

What this repository publishes is listed in **[the registry](registry/REGISTRY.md)** —
which is itself generated from a TSP register, built with the tool it catalogues.

Each entry under [`TSP/`](TSP) is a **tool**, not a skill: a folder containing a
definition document and the skill that operates it. That distinction is the method's
own rule — a skill with no definition document is an interface onto something nobody
has described.

| | Tool | Skill |
|---|---|---|
| TSP.1 | [WBS Register](TSP/TSP.1%20WBS%20Register/) — work breakdown / backlog | `wbs-manager` |
| TSP.2 | [RAID Register](TSP/TSP.2%20RAID%20Register/) — risks, actions, issues, decisions, ideas | `raid-dashboard` |
| TSP.3 | [TSP Register](TSP/TSP.3%20TSP%20Register/) — the inventory of tools itself | `tsp-manager` |

Each is an `.xlsx` source of truth with a generated HTML dashboard. They are ordinary
working tools, useful on their own — and they are here because a method with no worked
example is just an opinion.

`registry/` is that worked example running: AKOS uses TSP.3 to catalogue what AKOS
ships. The register is the source of truth; `REGISTRY.md` is generated from it, so the
catalogue cannot drift from the thing that defines it.

## Try it

Skills load from `.github/skills/`, `.claude/skills/` or `.agents/skills/` in GitHub
Copilot for VS Code, and the same `SKILL.md` format is read by Claude Code, Cursor,
Codex CLI and others. **This repository is a catalogue, not a working environment** —
the skills are not installed here. Copy the one you want into your own repo and your
agent picks it up with no registration step.

```bash
cp -r "TSP/TSP.1 WBS Register/wbs-manager"  <your-repo>/.github/skills/
pip install openpyxl
```

Then ask in plain language — *"create a WBS for project Atlas"*, *"add a risk about
the vendor deadline"*, *"what's overdue for review?"* Skills trigger on their
`description`, so nothing needs invoking by name.

Every script also runs standalone, with no agent involved:

```bash
python "TSP/TSP.1 WBS Register/wbs-manager/scripts/create_wbs.py"  "WBS Atlas.xlsx" "Atlas"
python "TSP/TSP.1 WBS Register/wbs-manager/scripts/refresh_wbs.py" "WBS Atlas.xlsx" "WBS Dashboard.html" "Atlas"
```

Python 3.9+ and `openpyxl`; every other import is standard library. Dashboards pull
Chart.js and Grid.js from a CDN — offline, tables render and charts don't.

## Templates

- [`templates/DF-template.md`](templates/DF-template.md) — the governance document structure.
- [`templates/SKILL-template.md`](templates/SKILL-template.md) — a skill skeleton, with notes on writing a `description` that actually triggers. Under-triggering is the common failure: a skill described in your own private vocabulary never matches anything you type.

## Where this came from

These conventions were extracted from a personal knowledge and project management
system built up over several years, where the tools grew organically and the
governance was reverse-engineered after the drift had already happened. That's why
every rule has a specific failure attached — they were all paid for.

Nothing from that system is included here. The tools are generic, the examples
invented, and the vocabulary stripped of anything local.

## License

MIT — see [LICENSE](LICENSE). Use, adapt and redistribute freely.
