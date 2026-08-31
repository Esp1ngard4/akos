# 1. Skills and governance docs

**Every skill needs a second document.**

A `SKILL.md` is loaded into the agent's context every time the skill triggers. That
makes it expensive real estate: every sentence of backstory is a tax paid on every
future invocation, whether or not that invocation needed the history.

But the history matters. Why a rule exists, what was tried and reverted, which
decision is still open — lose that and the rule looks arbitrary, and an arbitrary
rule eventually gets "cleaned up" by someone who can't see the reason.

So split them:

| | **SKILL.md** | **Governance doc** |
|---|---|---|
| Answers | What to do, and how | Why it exists, how it's governed |
| Read by | The agent, every time | A person, occasionally |
| Contains | Operational instructions, schemas, durable rules and their *timeless* rationale | Purpose, components, naming, relationships, maintenance, open items, version history |
| Never contains | Dated narration, changelogs, "we tried X" | Anything the agent needs at runtime |

The governance doc is conventionally named `DF.<n>` here — *Design Foundation* —
but the name matters far less than the separation.

## The test for a borderline sentence

> Would removing it change what the agent does on the next run?

**Yes, and the reasoning is timeless** → SKILL.md.

**No, or it explains how a rule came to be rather than what to do** → governance doc.

Two examples of the same fact, sorted correctly:

- SKILL.md: *"Never write to the `Commitments` project — it is reserved for
  non-negotiable commitments. This is a category rule, not a permissions accident."*
  The agent needs this every run, and the rationale is what stops it being
  rationalised away.
- Governance doc: *"v2.1 — added the Commitments exclusion after a task was
  auto-filed there during the 2026-07 sprint import."*
  Nobody needs the incident at runtime. But without it recorded somewhere, the
  exclusion looks like an oversight and gets removed.

## The failure this prevents

Skills accumulate narration. Something goes wrong, you fix it, and you write the
story of the fix into the skill so it doesn't happen again — reasonably enough. Do
that six times and the skill is half incident report. It still works, but it costs
more context on every run and the actual instructions are buried.

The reverse failure is quieter and worse: you keep the skill lean by deleting the
reasoning entirely. Months later a rule looks pointless, you remove it, and you
rediscover the original problem the hard way.

Watch for changelog-style history creeping into a `SKILL.md` — dated entries, gap
numbers, "as of" framing. That content has a home; it just isn't that one.

## Section order for the governance doc

Not every tool needs every section, but check each one deliberately rather than
skipping silently:

1. **Purpose** — what it's for, in a paragraph.
2. **Components** — a table: component, location, purpose. See
   [source of truth](02-source-of-truth.md); this is where that gets stated, and
   where it is most often stated wrongly.
3. **What the SKILL.md covers** — a pointer, so the two documents don't duplicate
   and drift.
4. **Naming conventions** — identifiers, files, folders.
5. **Relationships** — how data flows to and from sibling tools, and what is
   deliberately *not* automated.
6. **Maintenance** — the routine, and any recurring controls.
7. **Open items** — known gaps and deferred decisions.
8. **Version history** — see [versioning discipline](04-versioning-discipline.md).

**Open items is the section people skip, and it is the one that makes the document
trustworthy.** A gap recorded is a decision pending. A gap omitted is a surprise
later, usually for someone who assumed the document was complete.

## Write it after the design settles

Not before. A governance doc written against a design you haven't exercised is a
document you will rewrite — and rewriting it teaches you to distrust it. Build the
skill, use it on something real, then write down what it turned out to be.
