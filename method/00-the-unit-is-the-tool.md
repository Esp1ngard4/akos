# 0. The unit is the tool

**Not the skill. The tool.**

This is the assumption everything else rests on, and it is easy to get backwards —
especially now, when agent skills are the interesting new thing and it feels natural
to organise around them.

A **tool** is anything you depend on and would have to rebuild if it vanished: a
spreadsheet with rules baked into it, a script, a documented procedure, a checklist,
a third-party app you have configured to your own conventions, a manual describing
how a whole subsystem works. Some are software. Many aren't.

A **skill** is one thing a tool can have. It is the interface that lets an agent
operate the tool. It is not the tool.

## What a tool is made of

One component is mandatory. The rest are optional and vary by tool.

| Component | | |
|---|---|---|
| **Definition document** | **required** | What the tool is, why it exists, what it's made of, how it's governed. See [governance docs](02-governance-docs.md) |
| Data | common | A register, a spreadsheet, a folder of files - whatever the tool actually operates on |
| Scripts / templates | common | The mechanics |
| Generated output | common | Dashboards, reports - derived, never authoritative |
| **Agent skill** | **optional** | The interface that lets an agent operate the tool |
| Third-party application | sometimes | Where the tool is really "how I use X" |

A tool with a definition document and nothing else is a legitimate tool - a
documented procedure is exactly that. A tool with a skill but no definition document
is the broken case: an interface onto something nobody has described, which is how
an agent ends up confidently doing the wrong thing.

Write the definition first. Add a skill when the tool has earned one.

Components also differ in where they came from - some you authored, some you
installed - and that determines how each is preserved. See
[owned vs. used](04-owned-vs-used.md).

## Why the distinction matters

In the estate this method came from, the register holds **91 tools. Eight have a
skill.** Seventy-one active tools have none at all, and most of them never will —
a bedtime routine and a password manager do not need an agent interface.

Organise around skills and you build a system that describes 8 things and has
nothing to say about the other 71. Organise around tools and the eight skills fall
out naturally as an attribute: a column on a row, alongside status, owner and last
review date.

The same inversion shows up in provenance. "Some skills you wrote, others you merely
installed" is a real and useful rule — but it is just the newest instance of
something much older. You also *use* a to-do app, a password manager, a clipboard
utility. You did not write them, you cannot archive them meaningfully, and if you
lose them you need to know where they came from. That is a **tool** rule. Skills
inherited it.

Getting this backwards is not fatal, but it produces a method that dates badly: tied
to one generation of agent tooling rather than to the thing that persists.

## What makes a tool agent-operable

"Agentic" is not a synonym for "has a skill attached." A skill pointed at an
undocumented, ambiguous tool produces confident wrong actions faster than you could
produce them by hand.

Four properties make a tool safe for an agent to act on:

1. **An explicit source of truth.** Exactly one place is authoritative, it is stated
   in writing, and it has been checked against reality. See
   [source of truth](03-source-of-truth.md).
2. **A documented schema.** Field names, allowed values, what is computed, where
   headers live. An agent that has to infer structure will infer it wrong on the
   edge cases, silently.
3. **Stated guardrails.** What must never be overwritten, what must be read before
   it is written, what must be backed up first. An agent will follow an explicit
   prohibition and cannot infer an implicit one.
4. **A registry entry.** Something that knows the tool exists, so the automation is
   discoverable and can be reconciled against reality. See
   [registering your tools](01-registering-your-tools.md).

Notice that three of the four are worth having whether or not an agent is ever
involved. That is the point: **the work of making a tool agent-ready is mostly the
work of making it well-governed.** The skill is the last step and the smallest one.

Which is also why 71 unautomated tools are not a backlog of failures. They are tools
that have not needed an interface yet. When one does, the governance is what makes
adding it a day's work instead of a rewrite.

## How to read the rest

The register is the spine — every tool is a row, and the other conventions describe
what a good row points at.

| | |
|---|---|
| [1. Registering your tools](01-registering-your-tools.md) | The inventory, and reconciling it against reality |
| [2. Governance docs](02-governance-docs.md) | Every tool gets a second document; what goes in which |
| [3. Source of truth](03-source-of-truth.md) | Where a tool's components live, and how to make drift impossible |
| [4. Owned vs. used](04-owned-vs-used.md) | You built some, you installed others; they need opposite treatment |
| [5. Versioning discipline](05-versioning-discipline.md) | Keeping history without the history swallowing the document |
