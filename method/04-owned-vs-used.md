# 4. Owned vs. used

**Some tools you built. Others you merely installed. They need opposite treatment,
and confusing them loses one of them.**

Once an estate has any size, its tools stop being one category. Some you authored
and maintain: scripts, spreadsheets with logic in them, documented procedures.
Others came from outside and update on a schedule that isn't yours: a to-do app, a
password manager, a clipboard utility, a skill from a public repository.

The distinction looks like bookkeeping. It isn't — it determines how you get the
tool back after a laptop dies.

## Owned tools: archive them

A tool you built is yours to preserve. It lives in version control, with superseded
versions kept in a `PreviousV/` folder rather than deleted.

Recovery path: the repository. Nothing else needed.

Keep the old versions. When a tool is replaced, archive the previous generation with
a descriptive folder name — `PreviousV/WBS v1.0 (Visio)/` — rather than deleting it.
Old formats occasionally still hold data worth recovering, and the archive is the
cheapest possible insurance.

## Used tools: record where they came from

A tool you merely installed should **not** be archived. Committing a copy of
someone else's tool means:

- It goes stale the moment upstream moves, silently.
- It implies an ownership and a maintenance commitment you don't have.
- You inherit their licence terms into your repository without deciding to.

But *not archiving it* only works if you can get it again. So the rule has a second
half, and this is the half that gets forgotten:

> A used tool must have its origin recorded — vendor or repository, licence or
> account, version if it matters, and how it was installed.

**Neither archived nor traceable means unrecoverable.** That combination happens by
accident, not negligence: you don't archive it because it isn't yours, and you don't
record it because installing it took ten seconds and felt self-evident at the time.
Two years later it is a name in a register and nothing else.

Record it in the tool's governance doc:

| Tool | Origin | Licence | How it was installed |
|---|---|---|---|
| `<agent skill>` | `github.com/<org>/<repo>`, path `skills/<name>` | Apache 2.0 | `/install <org>/<repo>/<name>` |
| `<password manager>` | vendor, account under `<which email>` | commercial, annual | vendor installer; config exported to `PreviousV/` |

## This is older than skills

Agent skills are the newest thing this rule applies to, not the reason for it.

In the estate this method came from, the register already contained a to-do app, a
password manager and a clipboard tool — all used, none authored, all needing exactly
this treatment years before any skill existed. The rule was rediscovered rather than
invented when the first externally-supplied skill arrived, because nobody had
written it down as a *tool* rule.

If you find yourself writing a convention that applies to skills, check whether it
is really a tool convention with a skill-shaped example. Usually it is.

## Configuration is the grey area

Many used tools are only valuable because of how *you* configured them — the
filters, the labels, the templates, the keyboard shortcuts. The application is
theirs; the configuration is yours.

Treat them separately. Record the application's origin as above, and **archive the
configuration as an owned artefact**: an export, a settings file, a documented list
of the conventions you rely on. Reinstalling the app is easy. Reconstructing three
years of accumulated setup from memory is not.

## Both kinds belong in the register

Whichever category a tool falls into, it gets a row. The categories differ in *how
you preserve them*, not in *whether you know they exist*.

For tools with an agent skill, naming the skill in the register is what makes the
automation discoverable — and lets the register reconcile in both directions: a
skill named but not installed is a broken reference, and a skill installed but named
nowhere is automation nobody has decided to keep. See
[registering your tools](01-registering-your-tools.md).
