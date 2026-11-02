# TD.4 — Tool Installer

## Purpose

Installs a tool from this catalogue into a project, its definition document and
its skills, records where each part came from, and keeps it reconcilable with
upstream afterwards.

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
| `packs/` | owned | repository root | The packs `init` starts from: `project`, and `foundation`, which it includes |
| The tool's folder | owned, per installed tool | the project's TSP folder: `TSP.<n> <Name>/` | The tool in the project: its TD and its lock |
| `tool.lock.json` | owned, per installed tool | the tool's folder, beside its TD | **Source of truth** for that tool in that project: which parts are installed, where, and from which commit |
| `.agents/skills/<name>/` (or `--dest`) | used, per consuming project | the folder it was installed into | The installed skill. Committed, not gitignored — unlike a junction |

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
| `init <folder> --name <project> [--pack project]` | Start a new project from a pack: its tools added and registered, then its structure set up by those tools' own scripts. Refuses a folder that already holds a project |
| `init <folder> --name <project> --pack foundation` | The artifact register and the tool register, in an empty folder or a running project: only what is missing is created, none of the team's folders renamed, and every tool already installed registered |
| `add <skill> --into <project> [--tools <folder>]` | Install the skill, and its tool's folder with its TD and lock; register the tool where the project has a tool register |
| `add TSP.n --into <project>` | A tool with no skill: its folder, TD and lock |
| `status [--check]` | Every tool's lock under the folder given, each part against its lock. Offline; `--check` exits non-zero on any difference |
| `status --upstream [--source <clone>]` | Also say, per part, whether the catalogue has changed it since the commit its lock records: up to date, or how many changes behind and the newest one, with the `update` line for each. A TD counts changes to itself only. Reads a local clone (offline once pulled) or the lock's URL; with `--check`, exits non-zero while any part is behind |
| `diff <part>` | Ours against upstream |
| `update <part>` | Three-way merge. Exits non-zero and leaves the lock at its commit if anything conflicts |
| `accept <part> [-m why] [--path <where>]` | Record the copy on disk as intended, completing any merge; `--path` points the lock at a part that was moved |

A part is named by its skill (`wbs-manager`), or by its tool's catalogue ID for its
TD (`TSP.4`). The commands search down from `--project` (default: the current
folder), never up, so run from the project's root they see every tool it has.

`status` is deliberately offline — it compares against hashes in the lock rather
than fetching. That is also why *clean* means "as installed", not "the latest":
`--upstream` is the question asked separately, of a clone the user has pulled. That makes it cheap enough to run on every pull request, which is
what turns "drift is detectable" into "drift is detected".

## Conventions

- **One lock per tool, in the tool's folder beside its TD** (`tool.lock.json`).
  The tool is the unit, so its record travels with it: renaming or moving its
  folder moves the record too, and nobody browsing the project meets a
  configuration file in a folder they work in. The lock names the catalogue tool
  it came from (`tsp`, `tool`, `source`) and holds one part per installed piece:
  `TD`, each skill, a shared folder. Each part records its own commit and hashes,
  and **its path from the lock**, so skills may sit wherever the project keeps
  them, `.agents` folders side by side included; nothing walks up or guesses.
- **A tool's folder takes the register's number.** Without a tool register it is
  named by the catalogue (`TSP.17 Work Management`). Once the tool is registered,
  by `add`, `init` or the foundation pack, a folder still named by the catalogue
  becomes `TSP.<row ID> <Name>`: the project numbers its own tools. The lock's
  paths survive it, being relative and the depth unchanged.
- **A part moved from under its lock is found again.** Renaming a folder above
  the lock changes nothing; renaming one that holds a skill but not its lock
  leaves the lock pointing at the old name. `status` reports the part missing,
  finds a skill of that name elsewhere in the project, and prints the `accept
  --path` line that points the lock at it.
- **Default destination** is `.agents/skills/`, the folder most agents read:
  GitHub Copilot (in VS Code too), Codex, Cursor and others. **Claude Code reads
  only `.claude/skills/`** (tested 27-Oct-2026 with Claude Code 2.1.311: a skill
  in `.agents/skills/` was neither listed nor invocable, one in `.claude/skills/`
  was both), so a project using it installs with `--dest .claude/skills`.
  `--dest .github/skills` serves Copilot only.
- **`add` names what the skill works with.** The catalogue's other skills that the
  installed skill's SKILL.md names in backticks, and that the project does not have
  yet, are listed after the install, one line. The skill's own text is the list, so
  nothing beside it has to be kept in step; whether to add them is the user's call.
- **The project pack puts the product manager's skills in the project-management folder** (`00. PrjMgm/.agents/skills/`) and the team's at the root, every tool's folder, with its TD and lock, in the tool register's folder. An agent loads the skills of the folder it opens, and not of folders nested inside it, so `init` writes a workspace per profile: the team's opens the project, the product manager's adds the project-management folder as a folder of its own, where the skills load. It registers every tool in the project's own tool register, numbered by the project with its catalogue tool in `Upstream`; and files the stakeholder register under a Confidential folder it keeps out of git, access set where the files are shared.
- **The foundation pack is what every project's tools rest on:** the artifact register, which says what each folder is and which tool manages it, and the tool register, which keeps the tools up to date, running and fit. It is the one pack that adopts a running project: it creates only what is missing, numbers only the folders it creates (before installing anything into them, so no lock loses a part), renames none of the team's own, and registers every tool it finds a lock for. The project pack includes it. `add` into a project without a tool register says so, and points here.
- **The basic convention a project is expected to follow:** a project-management folder named `PrjMgm` (numbered or not) holding the registers, and an `Execution` folder beside it. The project pack lays a project out this way, and a project already running can be moved to it. **A project that departs from it says so in its own records**: the WBS declares its Execution folder (`meta.execution`), the artifact register says which tool governs which folder (*Managed By*), and each lock records where its skills are. Tools look in that order of cost: the convention first, then those records, then a search by name; never by assuming how deep a folder sits.
- **A pack is a new project's starting point** (`packs/<name>.json`): the skills to add, the planning and execution folders (00 and 01: the artifact register describes the whole project), the planning folder's contents (the register's own folder first, as 02), the steps that create each register through the installed tool's own script, the documents to number once they exist, the lines `.gitignore` needs, and what to say first. `init` holds no knowledge of any tool: a step is a skill, a script and its arguments, so the structure is the tools' own and a change to a tool reaches new projects through the pack untouched. It runs on an empty folder or a fresh repository only, the foundation excepted; a running project adds tools one at a time, because its structure is already its own. Like everything else here it is a person's decision, so no skill runs it.
- **Commit the skill folder and the tool's folder together.** Either without the
  other is worse than neither: a lock with no skill is a promise, and a skill with
  no lock is exactly the unrecorded copy this tool exists to prevent.
- **Content is compared with line endings normalized.** Working trees and
  `git archive` disagree the moment `core.autocrlf` is on, which is the Windows
  default. Without normalizing, every text file looks changed on both sides and
  every update is a whole-file conflict.
- **A declared difference is not a finding.** `accept -m "<why>"` is what
  separates a deliberate local change from a mistake, and `--check` cannot tell
  them apart without it.
- **A tool's TD always travels with it.** A tool without its definition document
  is not installed whole. The project evolves the TD in the tool's folder and
  still sees where the catalogue's has moved: the `TD` part gets `status`, `diff`,
  `update` and `accept` like a skill. It is placed once per tool, keeps the
  upstream file name (rename it and it no longer matches upstream), and covers the
  TD files only (`"only": "TD"`), so the lock and anything else the project keeps
  in that folder is never drift. The tool's row is written through `tsp-manager`'s
  own script, the project's copy where it has one: the register stays that tool's.
- **The tool folder goes where the registers point.** `add` uses `--tools` when
  given; else the folder holding the project's tool register; else a folder named
  `TSP`, numbered or not; else a new `TSP/`. The skill goes into `--into`'s
  `.agents/skills/`: the project-management folder for the product manager's
  tools (whoever adds that folder to their workspace gets them), the repository
  root for the team's, each tool's folder in the one TSP folder either way.

## Relationship to other tools

**[TSP Register](../TSP.3%20TSP%20Register/TD.3%20-%20TSP%20Register.md)** — the
registry says which tools exist and who keeps them alive. The lock says what one
project uses. Registry and manifest are different jobs, and a project keeps both:
installing a tool takes on its upkeep (up to date, running, fit for how the team
works), which the catalogue cannot do for it. The pack's tool register is that
registry, each row naming its catalogue tool in `Upstream`. Only a portfolio team
that manages the tools for its projects keeps the registry instead, the projects
keeping the lock alone. When the project closes, what it improved goes back
upstream, and each tool moves on or retires with it ([sharing with a team](../../method/06-sharing-with-a-team.md)).

**The smoke test** exercises `add`, `status --check` on a clean and on an edited
copy, and `accept`, so the drift detection is itself under test; and `update` on a
skill and on a TD, cleanly and with a conflict: the conflicting update exits
non-zero, keeps the lock at its commit, refuses a second `update` and an `accept`
while conflict markers remain, and completes with `accept` once they are resolved.
It installs into `.agents` folders side by side, moves a skill from under its lock
and re-points it, has an old lock refused, and runs the foundation pack on a
running project and on an empty folder.

## Maintenance

- **After changing a tool upstream**, consuming projects pick it up with `update`.
  Nothing pushes to them; that is intentional.
- **Run `status --check` in CI** in every consuming project.
- **Review declared local changes periodically.** Each one is either a fork
  waiting to be acknowledged or a contribution waiting to be sent upstream, and
  the answer changes over time.

## Moving from the old lock

Before v1.11 a project had one `tools.lock.json` per folder it installed into,
its entries keyed by skill and by `TSP.<n> docs`. Every command refuses one, so it
is never misread. To move a project over, once:

1. For each tool in the old locks, find its folder: the `path` of its `TSP.<n>
   docs` entry. A tool installed without its TD has none: place the TD in a folder
   named by the tool's row in the project's tool register, found by `Upstream`.
2. Write that folder's `tool.lock.json`: the old entries become its parts (`TD`,
   each skill, `_shared`), each `path` rewritten relative to the new lock, the
   commits and hashes kept as they were, so nothing reads as changed.
3. Delete the old locks, and run `status --check` from the project's root: every
   tool listed, every part clean.
4. Run `init --pack foundation` on the project. It keeps both registers and
   brings each tool's row in line with its lock (Skill, Links); regenerate the
   tool register's dashboard after it.

## Open items

| Item | Detail |
|---|---|
| Several parts moved at once | `status` finds a moved skill by name and prints the `accept --path` line for it, one part at a time. A folder of many skills renamed would want one command for them all |
| No return path | Sending an improvement back upstream is a manual pull request. Fine at this size; a `contribute` command would help once there are many consumers |
| Binary conflicts are not merged | Both sides changed an `.xlsx` and ours is kept, with theirs written alongside as `.upstream`. There is no sensible automatic answer, but the reporting could be clearer about what differs |
| Config-driven tools would remove most conflicts | Most divergence is configuration edited in place. Tools reading project config from outside the vendored folder would rarely conflict at all — the largest available improvement, and it belongs in the tools, not here |

## Version history

| Version | Date | Changes |
|---|---|---|
| v1.11 | 2026-11-02 | **A lock per tool, beside its TD; the foundation pack.** The single `tools.lock.json` in the folder installed into put a configuration file where a whole team browses, and a pack project had two. Each tool now keeps `tool.lock.json` in its own folder, its parts recorded by their path from the lock, so the record travels with the tool and needs no register to be found. The TD is always placed (`--docs` gone); a tool folder takes the register's number once registered (`init` had named them by the catalogue while numbering rows by the project). The foundation pack sets up the two registers in a running project. Considered and rejected: the lock in `.agents/` (still visible, and tied to one skills folder), one lock per project in the register's folder (a dependency on the register, two folders' skills in one file). Renaming a folder that holds a skill but not its lock was found to break its path; the foundation numbers its folders before installing into them, and `status` finds a moved skill by name. |
| v1.10 | 2026-11-01 | **A project that installs tools keeps their registry.** This document and method 06 said a project needs the lock and never a registry, while the pack gives every project a tool register. Installing a tool takes on its upkeep, which the catalogue cannot run, so the project keeps the registry, adapted tools or not; only a portfolio team managing its projects' tools takes it over. A first draft made the registry depend on adapting a tool; rejected by the user, since the upkeep comes with installing. `update` tested on a skill and through a conflict that stays retryable. |
| v1.9 | 2026-10-29 | **The basic convention, stated, and how tools find what departs from it.** A project is expected to keep `PrjMgm` and `Execution`; one that departs says so in its records (the WBS's `meta.execution`, the artifact register's *Managed By*, the locks), and tools look at the convention first, then the records, then by name. Raised aligning a running project whose folders sat a level deeper. |

Earlier versions are in this file's git history.
