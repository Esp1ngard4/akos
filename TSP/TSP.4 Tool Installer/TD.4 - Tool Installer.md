# TD.4 — Tool Installer

## Purpose

Vendors a tool from this catalogue into a project, records where the copy came
from, and keeps it reconcilable with upstream afterwards.

It exists because of a constraint that cannot be designed around: **a skill only
loads from the working tree of whoever is running the agent.** There is no
server-side registry an assistant pulls from. So a team shares a tool by
committing it into the project — everyone gets it on clone, nobody runs a setup
step, and a change to it appears in a pull request like any other change.

That is a copy, and [source of truth](../../method/03-source-of-truth.md) says
copies drift. The junction that solves this for one person is local filesystem
state and does not survive a clone. This tool provides the alternative: the copy
stays, but it is recorded, so drift becomes detectable and updates become a
three-way merge instead of a diff someone has to eyeball.

The reasoning is in [6. Sharing with a team](../../method/06-sharing-with-a-team.md).

## Components

| Component | Provenance | Location | Purpose |
|---|---|---|---|
| This document | owned | `TSP.4 Tool Installer/` | Governance: purpose, model, conventions, history |
| `install.py` | owned | repository root | The tool itself |
| `tools.lock.json` | owned, per consuming project | root of the project it was installed into | **Source of truth** for what that project has and where it came from |
| `.agents/skills/<name>/` (or `--dest`) | used, per consuming project | root of the project it was installed into | The vendored copy. Committed, not gitignored — unlike a junction |

**This tool has no skill.** It runs a handful of times in a project's life, at
moments where a human is deciding something, and it is not improved by being
wrapped in natural language. A tool is not obliged to have one — the
[register](../../method/01-registering-your-tools.md) exists to record tools,
and the skill is an optional attribute.

`install.py` lives at the repository root rather than in this folder because it is
the first thing a consumer of the catalogue runs, and a path with spaces in it is
a poor front door.

## The model

Three versions are needed to answer "what do I bring, and what do I keep":

- **base** — upstream at the commit recorded in the lock
- **theirs** — upstream now
- **mine** — what is in the project

With only two, a difference is ambiguous, because it cannot say who moved.

| base → mine | base → theirs | Result |
|---|---|---|
| unchanged | unchanged | skipped |
| unchanged | changed | `updated` — fast-forward |
| changed | unchanged | `kept` |
| changed | changed | `merged`, or `CONFLICT` |

**The lock records a commit, never a version label.** Reconstructing base needs
the exact content the copy was taken from, and a tag can be moved.

## Commands

| Command | Does |
|---|---|
| `list` | What the catalogue publishes |
| `add <skill> --into <project>` | Vendor it and write the lock entry |
| `add <skill> --into <project> --docs <folder>` | Also place the tool's TD in `<folder>/<tool folder>/`, locked as its own entry (`TSP.n docs`) |
| `add TSP.n --into <project> --docs <folder>` | The TD alone, for a tool with no skill (or a TD wanted without its skill) |
| `status [--check]` | Compare copies against the lock. Offline; `--check` exits non-zero on any difference |
| `diff <skill>` | Ours against upstream |
| `update <skill>` | Three-way merge. Exits non-zero and leaves the lock alone if anything conflicts |
| `accept <skill> [-m why]` | Record the copy on disk as intended, completing any merge |

`status` is deliberately offline — it compares against hashes in the lock rather
than fetching. That makes it cheap enough to run on every pull request, which is
what turns "drift is detectable" into "drift is detected".

## Conventions

- **Lock location** is `tools.lock.json` at the project root, next to the other
  lock files a project has.
- **Default destination** is `.agents/skills/`, the folder most agents read:
  GitHub Copilot (in VS Code too), Codex, Cursor and others. **Claude Code reads
  only `.claude/skills/`** (tested 27-Oct-2026 with Claude Code 2.1.311: a skill
  in `.agents/skills/` was neither listed nor invocable, one in `.claude/skills/`
  was both), so a project using it installs with `--dest .claude/skills`.
  `--dest .github/skills` serves Copilot only.
- **Commit the skill folder and the lock together.** Either without the other is
  worse than neither: a lock with no skill is a promise, and a skill with no lock
  is exactly the unrecorded copy this tool exists to prevent.
- **Content is compared with line endings normalized.** Working trees and
  `git archive` disagree the moment `core.autocrlf` is on, which is the Windows
  default. Without normalizing, every text file looks changed on both sides and
  every update is a whole-file conflict.
- **A declared difference is not a finding.** `accept -m "<why>"` is what
  separates a deliberate local change from a mistake, and `--check` cannot tell
  them apart without it.
- **A tool's TD can travel with it** (`--docs`). A project that owns its tools
  keeps their TDs in its own TSP folder and evolves them there, and still sees
  where the catalogue's have moved: a TD entry gets `status`, `diff`, `update`
  and `accept` like a skill. It is placed once per tool, keeps the upstream file
  name (rename it and it no longer matches upstream), and its entry covers the
  TD files only (`"only": "TD"`), so anything else the project keeps in that
  folder is never drift. The installer never writes a TSP register: registering
  the tools in the project's own register is `tsp-manager`'s.
- **The project-management tools can live in the project-management folder.**
  Install them `--into` that folder (`General/0.PrjMgm`, say): the skills land in
  its `.agents/skills/`, the lock beside them, the TDs in `--docs TSP`. An
  editor reads `.agents/skills/` at the root of each workspace folder, so whoever
  adds that folder to their workspace gets the PM tools and someone who opens
  only the repository root does not. A tool for the whole team is installed at
  the repository root with its own lock; both are listed in the one project TSP
  register.

## Relationship to other tools

**[TSP Register](../TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md)** — the
registry says which tools exist and who keeps them alive. The lock says what one
project uses. Registry and manifest are different jobs: a project that grows its
own registry either dies with its tools or becomes an authority nobody
reconciles.

**The smoke test** exercises `add`, `status --check` on a clean and on an edited
copy, and `accept`, so the drift detection is itself under test.

## Maintenance

- **After changing a tool upstream**, consuming projects pick it up with `update`.
  Nothing pushes to them; that is intentional.
- **Run `status --check` in CI** in every consuming project.
- **Review declared local changes periodically.** Each one is either a fork
  waiting to be acknowledged or a contribution waiting to be sent upstream, and
  the answer changes over time.

## Open items

| Item | Detail |
|---|---|
| No return path | Sending an improvement back upstream is a manual pull request. Fine at this size; a `contribute` command would help once there are many consumers |
| Binary conflicts are not merged | Both sides changed an `.xlsx` and ours is kept, with theirs written alongside as `.upstream`. There is no sensible automatic answer, but the reporting could be clearer about what differs |
| Config-driven tools would remove most conflicts | Most divergence is configuration edited in place. Tools reading project config from outside the vendored folder would rarely conflict at all — the largest available improvement, and it belongs in the tools, not here |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.1 | 2026-10-27 | **A tool's TD can be installed and locked too.** `add --docs <folder>` places the tool's TD in the project's TSP folder as its own lock entry, once per tool; `add TSP.n --docs` places a TD alone, for a tool with no skill. The entry covers the TD files only, so a project can keep its own notes beside a TD, evolve the TD, and still `update` from the catalogue with its edits kept. Conventions say where project-management tools go: their own folder, with its own `.github/skills/` and lock. The default destination becomes `.agents/skills/`, read by most agents; Claude Code reads only `.claude/skills/`, so it takes `--dest` (tested). Raised preparing an existing project's install. |
| v1.0 | 2026-08-31 | Initial version. Written to answer how a team shares tools when the junction approach cannot survive a clone |
