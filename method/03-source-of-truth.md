# 3. Source of truth

**Anything that exists in two places will drift. Make that structurally impossible,
not merely discouraged.**

This applies to every component a tool has — its register, its templates, its
documentation, its scripts. The worked example below is a skill, because that is
where the problem bites hardest and has the neatest fix.

Agents load skills from fixed locations — `.github/skills/`, `.claude/skills/`,
`.agents/skills/`. But that is rarely where the skill *belongs*. A skill is part of
a tool, and the tool has a home: its own folder, next to its documentation, its
templates, its version history.

So you end up with two paths, and a decision about which one is real.

## The wrong fix: a copy and a habit

The obvious approach is to keep the authoritative copy where the tool lives, and
copy it into the agent's folder — or the reverse. Either way you now have two real
directories and a rule that says "remember to resync."

That rule fails. Not dramatically — quietly. You edit the wrong copy and the change
appears to work because the agent is reading the other one. Or you edit the right
copy and the agent keeps using a stale version, and you spend twenty minutes
debugging a skill that was fixed an hour ago.

Every "keep these two in sync" convention is a bug with a delay on it.

## The fix: one directory, two paths

Put the skill where it belongs, and make the agent's path a **junction or symlink**
into it.

```
tools/wbs-manager/wbs-manager/     <- the real directory. version-controlled.
.github/skills/wbs-manager         -> junction into it. gitignored.
```

There is now one directory. Writing through either path writes the same files.
Drift is not discouraged; it is impossible.

```bash
# macOS / Linux
ln -s "$PWD/tools/wbs-manager/wbs-manager" ".github/skills/wbs-manager"

# Windows (junction — no admin rights needed, unlike a symlink)
mklink /J ".github\skills\wbs-manager" "%CD%\tools\wbs-manager\wbs-manager"
```

Agents load skills through junctions without complaint — worth verifying once in
your own setup, but it works.

## Two consequences to handle

**Git will double-count it.** Git follows a junction and sees ordinary files, so
without care it commits every file twice. Gitignore the agent-side path; the real
directory is what gets tracked.

```gitignore
# Junction into tools/<name>/ — the tracked source of truth.
# Recreated per machine; see setup docs.
.github/skills/wbs-manager/
```

**The junction won't survive cloning.** It is local filesystem state, not repo
content. That makes it a setup step, so write it down — a fresh clone that silently
has no skills is a bad first five minutes.

## State it explicitly, and verify it

In the governance doc's Components table, say which path is authoritative — in
words, not by implication:

> **`tools/wbs-manager/wbs-manager/` — the source of truth.**
> `.github/skills/wbs-manager` is a junction into it, not a copy.

Then check the claim against the disk. This is the single most common thing to get
subtly wrong, and it is self-propagating: everything built on top inherits the
error, and each new document copies the assertion from the last one without anyone
re-checking. A Components table that has never been verified is a rumour.

## Which direction?

Put the skill with its tool, not the tool with its agent folder.

Agent folders are a runtime detail of whichever assistant you're using this year.
The tool's folder is where its documentation, templates, history and data
conventions already live — and it is what survives if you switch agents, or use two
at once. A skill filed under `.claude/` is a skill that looks orphaned the moment
you open the repo in something else.
