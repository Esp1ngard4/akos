# Building on AKOS

The [README](../README.md) is for a team deciding whether to run on AKOS. This page is for
whoever builds or adapts the tools: the method behind them, how the catalogue is organised,
how an installed copy stays maintainable, and how it is all tested.

A method for structuring the tools and systems you depend on, so that agents can
safely operate them.

Not "how to write agent skills." Skills are the easy part. The hard part is the
estate underneath: knowing what you actually have, which copy is authoritative, why
a rule exists, whether a tool is still used, and where something came from if you
have to reinstall it. Those questions don't matter on day one. They matter at tool
number thirty, when you no longer remember building the first ten.

AKOS is the set of conventions that answer them, plus working tools that
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

Seven short pieces. Each came from an actual failure, and each says which — a rule
whose reason you can't remember is a rule you will eventually undo.

| | |
|---|---|
| [0. The unit is the tool](00-the-unit-is-the-tool.md) | The assumption everything rests on, and what makes a tool agent-operable |
| [1. Registering your tools](01-registering-your-tools.md) | **The spine.** An inventory that reconciles against reality |
| [2. Governance docs](02-governance-docs.md) | Every tool needs a second document. What goes in which, and the test for borderline cases |
| [3. Source of truth](03-source-of-truth.md) | Anything in two places will drift. How to make that impossible rather than discouraged |
| [4. Owned vs. used](04-owned-vs-used.md) | You built some, you installed others. Opposite treatment, and getting it wrong loses one |
| [5. Versioning discipline](05-versioning-discipline.md) | Keeping history without the history swallowing the document |
| [6. Sharing with a team](06-sharing-with-a-team.md) | Everything above assumes one person. What changes when it's a team, and which rule breaks |

Start at [0](00-the-unit-is-the-tool.md) if you want the reasoning, or
[1](01-registering-your-tools.md) if you'd rather see the mechanism first.

## How the catalogue is organised

What this repository publishes is listed in **[the registry](../registry/REGISTRY.md)** —
which is itself generated from a TSP register, built with the tool it catalogues.

Each entry under [`TSP/`](../TSP) is a **tool**, not a skill: a folder containing a
definition document and the skill that operates it. That distinction is the method's
own rule — a skill with no definition document is an interface onto something nobody
has described.


TSP.1–3 and TSP.5 are each a JSON source of truth with a generated HTML dashboard.
They are ordinary working tools, useful on their own — and they are here because a method with
no worked example is just an opinion.

TSP.8 is what uses them together. The sprint lives on the WBS rows, the retro routes to
RAID, planning commits control activities from the TSP register, and nothing else is
needed. Most teams already run a task tracker and a calendar, each in its own way, so
[TD.8](../TSP/TSP.8%20Sprint%20Ceremonies/TD.8%20-%20Sprint%20Ceremonies.md) says where
they plug in and what to watch for, rather than pretending one setting fits all. TSP.9 is
the same idea at the scale of a day, and its evening stand-up is what notices a sprint
ceremony that was due, or a week gone without a review. TSP.11 is that weekly review: what
falls between the day and the sprint, and whether the sprint is still on track.
TSP.12 is the layer below the registers: the small actions a working session agrees,
kept in one Markdown file the whole group can read and edit, filed with the work it serves.
TSP.13 is who hears about the work: a project's stakeholders and its communications plan,
with the contacts kept beside it and out of git.
TSP.14 is what the project is: its brief, written with whoever owns the outcome,
kept current before each status report, and revisited when a month has gone by.
TSP.15 is how a team shares one WBS: each sprint's board in Excel, updated by the team or
through Copilot, consolidated into the WBS by the product manager at the weekly review and the close-out.
TSP.16 is how people come to work in it: a guide generated from the project itself, showing at every step
what people do and what agents do, and an agent that walks a newcomer through their first week.

TSP.3 has **two** skills, which is the same claim from the other direction: one owns
the register row, the other owns the tool definition documents, and neither does the
other's write.

TSP.4 has **no skill**, deliberately. It runs a few times in a project's life, at
moments where a human is deciding something. A tool is not obliged to have a skill;
the register exists to record tools, and the skill is an optional attribute — which
is the method's [first claim](00-the-unit-is-the-tool.md), demonstrated rather
than asserted.

`registry/` is that worked example running: AKOS uses TSP.3 to catalogue what AKOS
ships. The register is the source of truth; `REGISTRY.md` is generated from it, so the
catalogue cannot drift from the thing that defines it.

**Registers are JSON.** Every write went through a script anyway, and a spreadsheet
cost a subprocess to read, a dependency to install, and a file lock whenever the
application or a sync client held it. What a spreadsheet gave back — validated
dropdowns while typing — the commands enforce more strictly, since argparse refuses
an invalid value where a dropdown only warns and paste bypasses entirely.

The tools themselves, one line each, are in the [README](../README.md#the-tools) and the
[registry](../registry/REGISTRY.md).

## Installing, and keeping the copy maintainable

Skills load from `.github/skills/`, `.claude/skills/` or `.agents/skills/` in GitHub
Copilot for VS Code, and the same `SKILL.md` format is read by Claude Code, Cursor,
Codex CLI and others. **This repository is a catalogue, not a working environment** —
the skills are not installed here. Put one in your own repo and your agent picks it
up with no registration step.

```bash
git clone https://github.com/Esp1ngard4/akos.git
python akos/install.py list
python akos/install.py add wbs-manager --into <your-repo>
```

That copies the skill into `<your-repo>/.agents/skills/` and writes
`tools.lock.json` recording where it came from and at which commit. **Commit both.**
`.agents/skills/` is read by GitHub Copilot, Codex, Cursor and others; Claude Code
reads only `.claude/skills/`, so for Claude Code add `--dest .claude/skills`.
Everyone who clones your repo then has the tool — no setup step, and a later change
to it shows up in a pull request like any other.

The lock is what makes the copy maintainable rather than a fork by accident:

```bash
python akos/install.py status --check   # has our copy drifted? (offline; good for CI)
python akos/install.py update wbs-manager   # three-way merge upstream changes in
```

`update` applies upstream changes, keeps yours, and asks about the overlap only.

A project that will own and evolve its tools can take their definition documents
too, into its own TSP folder, locked the same way:

```bash
python akos/install.py add wbs-manager --into <your-repo> --docs TSP
python akos/install.py add TSP.4 --into <your-repo> --docs TSP   # a tool with no skill: its TD alone
```
[6. Sharing with a team](06-sharing-with-a-team.md) explains why it works this
way; [TD.4](../TSP/TSP.4%20Tool%20Installer/TD.4%20-%20Tool%20Installer.md) is the
reference. A plain `cp -r` of the skill folder also works — you just lose the ability
to answer "what did we change?" later.

Then ask in plain language — *"create a WBS for project Atlas"*, *"add a risk about
the vendor deadline"*, *"what's overdue for review?"* Skills trigger on their
`description`, so nothing needs invoking by name.

Every script also runs standalone, with no agent involved:

```bash
python "TSP/TSP.1 WBS Register/wbs-manager/scripts/create_wbs.py"  "WBS Atlas.json" "Atlas"
python "TSP/TSP.1 WBS Register/wbs-manager/scripts/refresh_wbs.py" "WBS Atlas.json" "WBS Dashboard.html" "Atlas"
```

**Python 3.9+ and nothing else.** No dependencies, so there is no install step —
registers are JSON and every import is standard library. Dashboards pull Chart.js
and Grid.js from a CDN; offline, tables render and charts don't.

## Verifying it works

```bash
python tests/smoke_test.py              # the working tree
python tests/smoke_test.py --packaged   # what git actually ships
```

Every tool is exercised the way a new user would: create a register, render its
dashboard, check the output is real rather than merely present. The installer gets
the same treatment — vendor a tool into a throwaway project, confirm `status --check`
passes clean, edit a file, confirm it now fails, then declare the change and confirm
it passes again. Runs in seconds and needs nothing installed at all.

TSP.5 gets an extra case of its own. It is the only tool here that asserts something
about the world rather than about itself — the ID it assigns is written onto the file,
so the register can be wrong in a way a script can detect. The test breaks the filing
on purpose and confirms the audit notices, because a check that cannot fail is not a
check.

`--packaged` is the one that matters. It exports `git archive HEAD` and runs from
there, so a file sitting untracked on disk is simply absent. That gap once shipped a
tool whose dashboard template had never been committed, and every clone failed on
first use while the working tree looked perfectly healthy. CI runs `--packaged` on
every push, against Python 3.9 and 3.13.

## Templates

- [`templates/TD-template.md`](../templates/TD-template.md) — the governance document structure. `td-author` (TSP.3's second skill) is what applies and audits it.
- [`templates/SKILL-template.md`](../templates/SKILL-template.md) — a skill skeleton, with notes on writing a `description` that actually triggers. Under-triggering is the common failure: a skill described in your own private vocabulary never matches anything you type.
