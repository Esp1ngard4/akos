# 6. Sharing with a team

**A skill only exists where the agent is looking. For a team that means committed
into the project — a copy, made deliberate.**

Everything up to here assumes one person and one machine. Most of it survives
contact with a team unchanged. One rule does not: [source of
truth](03-source-of-truth.md) says put the skill in one directory and point the
agent's path at it with a junction. A junction is local filesystem state. Your
teammate clones the repo and gets nothing.

There is no server-side registry that Copilot or Claude Code pull skills from.
They read `.github/skills/`, `.claude/skills/`, `.agents/skills/` in whatever
working tree the person has open. So for the team to have the tool, the tool has
to be in the repository.

## Two different things

The confusion that makes this feel hard is that "the register" is doing two jobs.

A **registry** is a catalogue: what tools exist, who keeps each one alive, whether
it is still fit for purpose. It carries [control
activities](01-registering-your-tools.md) — a standing commitment to review.

A **manifest** is a much smaller thing: which tools *this project* uses, from
where, at which version.

Projects need a manifest. They do not need a registry, and giving them one is a
mistake with a delay on it: projects end, tools outlive them, and a register that
lives inside a project either dies with it or quietly becomes a fourth authority
nobody reconciles.

**Scope the registry to the smallest group that will actually run the control
activities.** Not the organisation, not the project — whoever is accountable for
the quarterly review. An org-wide register that nobody grooms is a stale
spreadsheet with governance theatre attached.

## The copy is not the problem

Copies were never the enemy. **Unrecorded** copies were. A vendored skill whose
origin and commit are written down is a *used* component with provenance, which
[owned vs. used](04-owned-vs-used.md) already licenses. There were only ever two
ways to guarantee no drift:

| | Enforcement | Survives a clone |
|---|---|---|
| Junction | structural — one directory | no |
| Vendored + locked | recorded, and checked by a test | yes |

Teams only get the second. The guarantee is the same; what changes is that drift
becomes *detectable* rather than *impossible*, so something has to do the
detecting.

## Not "whoever needs it"

The tempting middle path is to let each person install the skills they personally
use. Reject it. The failure mode is not an error, it is **silence** — someone
without the skill gets no warning, just an agent that never offers to do the
thing, and does something worse by hand instead. Two people run the same request,
get different results, and nothing on screen explains why.

A committed skill also shows up in a pull request. A copy on someone's laptop
cannot be reviewed, and its behaviour is not part of any record.

The line: **a skill that touches a shared artifact must be shared.** Personal
scratch helpers can stay local.

## The register survives without the tool

Worth checking deliberately: someone without `wbs-manager` can still open
`WBS Atlas.json`, read it, and edit a row. They lose consistent creation and the
generated dashboard, not access.

Never build a tool whose artifact is unreadable without the tool. Graceful
degradation is what stops a shared register becoming a hostage.

## Bring vs. keep

Once a project has its own copy, the copy will change — and eventually so will
upstream. You cannot decide what to take with two versions in hand: a difference
between yours and theirs is ambiguous, because you cannot tell who moved.

You need three. **Base** is upstream at the commit in the lock, **theirs** is
upstream now, **mine** is what is in the project.

| base → mine | base → theirs | Verdict |
|---|---|---|
| unchanged | unchanged | nothing to do |
| unchanged | **changed** | fast-forward — take theirs |
| **changed** | unchanged | keep ours |
| **changed** | **changed** | conflict — a human decides |

Only the last row needs judgment, and it is usually a small minority of files.

**This is why the lock records a commit rather than a version number.** A version
is a label and labels get moved; reconstructing base needs the exact content the
copy was taken from. Without base there is no merge, only a diff someone has to
eyeball — which is how a team ends up never updating anything.

## When you do conflict

Three outcomes, and which one it is should be written down rather than left in
the diff:

1. **Generally useful** → send it upstream. The next update fast-forwards and the
   divergence disappears. This is the outcome to design for.
2. **Genuinely local** → it is permanent. The component has just moved from *used*
   to *forked*, and that belongs in the [governance doc](02-governance-docs.md),
   not in someone's memory.
3. **A workaround for a bug now fixed upstream** → drop yours.

Recording the reason is what makes an automated check usable: a copy that differs
*and says why* is fine, and everything else is a finding.

## Most divergence is configuration

The conflicts that hurt are rarely logic. They are a hardcoded sprint length, a
status vocabulary, a column name — configuration wearing code's clothes. If the
tool reads those from a project file *outside* the vendored folder, the merge
never touches them and the conflict never happens.

In a one-person estate this looks like over-engineering, because editing the
script directly costs nothing. At team scale it is the difference between updates
that fast-forward and updates that need a meeting.

## One column the solo register does not need

Add an **owner** to the registry. Solo, the owner is always you, so the column is
noise. Shared, an unowned tool rots and nobody notices, because "someone should
update that" is not addressed to anyone.

The second thing to write down is the **return path**: how an improvement made
inside a project gets back upstream. Without one, every project's copy silently
becomes owned by that project, and you have as many forks as you have teams.

---

The [installer](../install.py) in this repository implements all of the above:
`add` vendors a skill and records where it came from, `status --check` fails a
build when a copy has drifted without explanation, `update` does the three-way
merge, and `accept` records a resolution or a declared local change.
