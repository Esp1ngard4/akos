# 3. Owned vs. used skills

**Some skills you wrote. Others you merely installed. They need opposite treatment,
and confusing them loses one of them.**

Once you have a handful of skills, they stop being one category. Some you authored
and maintain. Others came from somewhere else — a public repo, a vendor, a
colleague — and update on a schedule that isn't yours.

The distinction looks cosmetic. It isn't: it determines how you get the skill back
after a laptop dies.

## Owned skills: archive them

A skill you wrote is yours to preserve. It lives with its tool, in version control,
with superseded versions kept in a `PreviousV/` folder rather than deleted.

Recovery path: the repository. Nothing else needed.

## Used skills: record where they came from

A skill you merely installed should **not** be archived. Committing a copy of
someone else's skill means:

- It goes stale the moment upstream moves, silently.
- It implies an ownership and a maintenance commitment you don't have.
- You inherit their licence terms into your repository without deciding to.

But *not archiving it* only works if you can get it again. So the rule has a second
half that is easy to forget:

> A used skill must have its origin recorded — repository or URL, licence, and how
> it was installed.

**Neither archived nor traceable means unrecoverable.** That combination is the
actual failure, and it happens by accident: you don't archive it because it isn't
yours, and you don't record it because installing it took ten seconds and felt
self-evident at the time.

Record it in the governance doc:

| Skill | Origin | Licence | How it was installed |
|---|---|---|---|
| `skill-creator` | `github.com/anthropics/skills`, path `skills/skill-creator` | Apache 2.0 | `/install anthropics/skills/skill-creator` |

## Version pinning is a separate question

Recording the origin makes a skill recoverable. It does not tell you *which*
version you have. If that matters — if a used skill's behaviour is load-bearing —
record the version or commit too, and check it during your periodic review.

For most used skills it doesn't matter enough to track, and pretending otherwise
creates maintenance you won't do. Recording the origin is the part that is always
worth it.

## Both kinds belong in the register

Whichever category a skill falls into, it should appear in your
[tool register](05-registering-your-tools.md). Naming a skill there is what makes
the automation discoverable at all — and it lets the register reconcile in both
directions: a skill named but not installed is a broken reference, and a skill
installed but named nowhere is automation nobody has decided to keep.

The two categories differ in *how you preserve them*, not in *whether you know they
exist*.
