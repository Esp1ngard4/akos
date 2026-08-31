# 4. Owned vs. used

**Provenance is a property of a component, not of a tool.**

A tool is the unit of the register, but a tool is made of parts. At minimum it has a
**definition document** — the governance doc that says what it is and how it is run.
That part is always yours, always authored, always worth preserving.

Everything else varies. A tool may also have data files, scripts, templates, a
dashboard, and — optionally — an agent skill. Some of those you wrote. Some arrived
from outside and update on a schedule that isn't yours.

So the question is never "is this tool owned or used?" It is **"for each component,
did I author it or install it?"** — because the answer determines how you get that
component back after a laptop dies.

## Owned components: archive them

Anything you authored is yours to preserve. It lives in version control, with
superseded versions kept in a `PreviousV/` folder rather than deleted.

Recovery path: the repository. Nothing else needed.

Keep the old versions. When a component is replaced, archive the previous generation
under a descriptive name — `PreviousV/WBS v1.0 (Visio)/` — rather than deleting it.
Old formats occasionally still hold data worth recovering, and the archive is the
cheapest insurance available.

The definition document is always in this category. If nothing else about a tool
survives, that document is what lets you rebuild or replace it deliberately instead
of from memory.

## Used components: record where they came from

Anything you merely installed should **not** be archived. Committing a copy of
someone else's work means:

- It goes stale the moment upstream moves, silently.
- It implies an ownership and a maintenance commitment you don't have.
- You inherit their licence terms into your repository without deciding to.

But *not archiving it* only works if you can get it again. So the rule has a second
half, and this is the half that gets forgotten:

> A used component must have its origin recorded — vendor or repository, licence or
> account, version if it matters, and how it was installed.

**Neither archived nor traceable means unrecoverable.** That combination happens by
accident, not negligence: you don't archive it because it isn't yours, and you don't
record it because installing it took ten seconds and felt self-evident at the time.
Two years later it is a name in a document and nothing else.

Record it in the tool's governance doc, in the Components table where the rest of
the tool's parts are already listed:

| Component | Provenance | Origin | Licence | Recovery |
|---|---|---|---|---|
| Definition doc | **owned** | — | — | this repository |
| `<register>.xlsx` | **owned** | — | — | this repository + `PreviousV/` |
| `<authored skill>` | **owned** | — | — | this repository |
| `<installed skill>` | **used** | `github.com/<org>/<repo>`, path `skills/<name>` | Apache 2.0 | `/install <org>/<repo>/<name>` |
| `<third-party app>` | **used** | vendor, account under `<which email>` | commercial, annual | vendor installer |
| `<its configuration>` | **owned** | — | — | export in `PreviousV/` |

## A tool can be mixed, and usually is

This is the case the simpler framing misses.

In the estate this method came from, one tool — the register manager itself — has
three skills: two written in-house and one installed from a public repository. One
row in the register, one governance doc, three skill components, **two different
provenance treatments.** The two authored skills are archived; the installed one is
recorded and deliberately not archived.

A tool built entirely around a third-party application is mixed too. The application
is used; the governance doc describing how you run it is owned; and the
configuration sitting inside it is owned as well, even though it lives in someone
else's software.

If a tool's Components table has a single provenance for every row, that is worth a
second look. It's possible — but more often it means a component hasn't been thought
about yet.

## This is older than skills

Agent skills are the newest thing this rule applies to, not the reason for it.

The register this came from already contained a to-do app, a password manager and a
clipboard utility — all installed, none authored, all needing exactly this treatment
years before any skill existed. The rule was rediscovered rather than invented when
the first externally-supplied skill arrived, because nobody had written it down as a
*component* rule.

If you find yourself writing a convention that applies to skills, check whether it's
really a component convention with a skill-shaped example. Usually it is.

## Configuration is the grey area

Many used components are only valuable because of how *you* configured them — the
filters, the labels, the templates, the keyboard shortcuts. The application is
theirs; the configuration is yours, and it is the part that actually took time.

Treat them as two components with different provenance, exactly as in the table
above. Record the application's origin; **archive the configuration as an owned
artefact** — an export, a settings file, or a documented list of the conventions you
depend on. Reinstalling an app is easy. Reconstructing three years of accumulated
setup from memory is not.

## The register records the tool; the doc records the parts

One row per tool, not per component. The register answers *what exists and is it
still used*; the governance doc's Components table answers *what it's made of and
where each part came from*.

For components that are agent skills, naming them in the register as well is worth
it — that's what makes the automation discoverable, and lets the register reconcile
in both directions: a skill named but not installed is a broken reference, and a
skill installed but named nowhere is automation nobody has decided to keep. See
[registering your tools](01-registering-your-tools.md).
