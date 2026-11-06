---
name: stakeholder-manager
description: Manages a project's Stakeholder Register - its groups, its stakeholders (role, power/interest, current vs desired engagement, engagement action, share level) and its communications plan (what goes to whom, how often, through which channel, when it was last done), plus a contacts CSV beside it kept out of git; resolves a communication's audience to people and addresses at the moment of sending, says which communications are due or overdue, and generates a Stakeholder Dashboard. Use whenever the user mentions stakeholders, a stakeholder register, a communications plan, "who needs to know", "who do I send this to", a contact or mailing list for a project, a sponsor or client to keep informed, power/interest or engagement, or asks which updates are due or overdue; also when a ceremony or the reporting tool needs a project's audiences. Not for what other people owe (action-tracker-manager), risks and decisions (raid-manager), or writing posts for a public audience (the content system).
---

# Stakeholder Manager (TSP.13)

A Stakeholder Register says, for one project, who has a stake in the work, where each stands, and what flows to them: which update, to whom, how often, through which channel, at what share level, and when it last happened. It answers "who needs to know what about this, and did they hear it?". It sends nothing: it hands over the list, and records that the communication went when the user says so.

## Requirements

Python 3, standard library only. Examples write `python`; on macOS/Linux use `python3`. `git` is used, when present, to check that the contacts file is kept out of the repository.

## Files

| File | Role |
|---|---|
| `Stakeholders <scope>.json`, in `Confidential/Stakeholder Mgm` inside the project's planning folder (numbered by its artifact register: `12. Confidential/13. Stakeholder Mgm`) | **Source of truth.** Written only through `stk.py`. Keep the Confidential folder out of git and restrict who can open it. |
| `Contacts <scope>.csv`, beside it | How to reach each stakeholder, keyed by `S.n`. **Outside git.** Written by `stk.py contact` or by hand in a spreadsheet. |
| `Stakeholder Dashboard.html` and `Stakeholder Dashboard (no notes).html`, beside it | Generated, with each row's notes and without them. Never edit by hand; keep them out of git. |
| `scripts/stk.py` | Every read and write: `add-group`, `add`, `add-comm`, `set`, `note`, `contact`, `done`, `audience`, `due`, `gaps`, `check`, `list`, `show`. |
| `scripts/stk_register.py` | What other tools import: `load_or_default`, `audiences_for`, due dates, audience resolution, the audit. |
| `scripts/stk_schema.py` | Fields, vocabularies, the derived quadrant and gap. |
| `scripts/registry.py` | The JSON register format the register tools share. |
| `scripts/refresh_stk.py` | Rebuilds the dashboard. |
| `scripts/create_stk.py` | A new, empty register and contacts file. Never run it on a live one. |
| `examples/Stakeholders Atlas.json` | A made-up register to read or copy from. |

`<reg>` below is the register's JSON, **the folder that holds it, or the project's planning folder**: given the planning folder, the register is found through the artifact register first (the folder this tool manages, else the one named Stakeholder Mgm, matched by ID), then `Confidential/Stakeholder Mgm` by name, then the planning folder itself. `<skill>` is this folder. `<scope>` is the same string as the project's WBS `meta.scope`.

## The register

Four collections. Rows omit empty fields; dates are `YYYY-MM-DD`; nothing is deleted (a row goes `Inactive`).

**`groups`** (`G.n`) — the audiences: `Name`, `Purpose`, `Status`. A group holds no member list.

**`stakeholders`** (`S.n`) — `Name`, `Role` (in this project), `Organisation`, `Groups` (any number), `Power` and `Interest` (`High`/`Low`), `Current` and `Desired` (`Unaware`, `Resistant`, `Neutral`, `Supportive`, `Leading`), `Stake` (what's in it for them, what worries them, one line), `Engagement Action` (what closes the gap, or a RAID ref `<scope>#A.n`), `Share Level` (`owner` sees reports as they are; `external` gets the external copy), `Status`, `Notes` (a dated log, newest first, written with `note`). A row can be a body with no particular person behind it ("the steering committee", "the regulator").

**`communications`** (`C.n`) — `What`, `Report` (`status-report`, `sprint-update`, `closure`, when it carries one), `Mode` (`push` is sent, `pull` is a view they open, `interactive` is a conversation), `Audience` (group and stakeholder IDs), `Cadence` (`per sprint`, `weekly`, `monthly`, `quarterly`, `on event: <what>`), `Channel` (`email`, `chat`, `meeting`, `letter`, or `content: <scope> › <plan>`), `Owner`, `Last Done`, `Status`, `Notes`.

**`change_log`** — one row per write, with its reason.

**Derived, never stored:** the quadrant (High/High manage closely, High/Low keep satisfied, Low/High keep informed, Low/Low monitor), the engagement gap, when a communication is next due, and who an audience is.

## Rules

- **Write only through `stk.py`.** It validates every value, refuses a group or audience ID that does not exist, and logs each write.
- **Contact details never enter the register, its log, the dashboard or a report.** They live in the project's contacts CSV, outside git, so a project folder can be shared whole and a copy exposes only its own people. `stk.py contact` never echoes the values; do not repeat them in a commit message or a record either. `check` reports a contacts file git tracks (an error) or would take (a warning).
- **There is no shared contact list across projects.** Someone in two projects has a row in each. When adding a stakeholder, look in the other projects' contacts files for the same name or email and offer to copy the row rather than have it retyped; `check --all` reports any that disagree.
- **Never invent an analysis value.** Power, interest and engagement come from the user. Leave them blank and let the audit list them, rather than fill them with a guess.
- **Membership is on the stakeholder** (`--groups`). Adding someone to a group puts them in every communication to that group from the next send.
- **Nothing is sent.** `audience` hands over the list; `done` records that it went, on the user's word. A skipped communication is said, not recorded.
- **A communication to a public audience points to a content plan** (`content: <scope> › <plan>`) and holds nothing else; cadence and delivery stay in the plan. The content system is never written from here.

## Reading the register from another tool

A tool that needs a project's audiences reads them here and keeps no list of its own. Find this skill as a sibling of the calling skill (beside it in the skills folder), then:

```python
sys.path.insert(0, os.path.join(stakeholder_manager_folder, "scripts"))
import stk_register as STK
data = STK.load_or_default("<project planning folder>", scope="Atlas")   # never None
for comm, level in STK.audiences_for(data, "status-report"):           # level: owner | external
    ...
```

**The solo default:** a project with no register gets one stakeholder (the owner, `owner` share level) and one communication (the status report, per sprint, to the owner). `data["meta"]["default"]` is `True` then. Consumers call `load_or_default` and never test for the file themselves.

## Operations

### Look

```
python <skill>/scripts/stk.py list <reg> [--what stakeholders|groups|communications] [--inactive]
python <skill>/scripts/stk.py show <reg> --id S.4
```

### Set up a register for a project

When a project has someone besides its owner to keep informed: a sponsor, a client, a steering group, a supplier.

1. `python <skill>/scripts/create_stk.py "<project planning folder>/Confidential/Stakeholder Mgm" --scope "<the WBS's meta.scope>"`. A project set up from the starter pack has the folder already; otherwise create it, registered in the artifact register if the project keeps one. If it prints a `.gitignore` line, add it before anything else.
2. Groups first: who is addressed together (`add-group <reg> "Steering group" --purpose "..."`).
3. Stakeholders: `add <reg> "Name" --role "..." --groups G.1 --share external`. Ask the user for power, interest, current and desired engagement, and the stake; leave blank what they don't answer.
4. Communications: what the user actually keeps up, not an ideal plan. `add-comm <reg> "Monthly steering update" --mode push --audience G.1 --cadence monthly --channel email`.
5. Contacts: `contact <reg> --id S.4 --email ... --phone ... --preferred Email`, or the user fills the CSV in a spreadsheet.
6. `check`, then `refresh_stk.py`.

### Change

```
python <skill>/scripts/stk.py set <reg> --id S.4 --current Supportive --reason "..."
python <skill>/scripts/stk.py set <reg> --id S.4 --groups G.1,G.3          # replaces the list
python <skill>/scripts/stk.py set <reg> --id C.2 --cadence monthly --reason "..."
python <skill>/scripts/stk.py set <reg> --id S.6 --status Inactive --reason "work finished"
```

A gap between `Current` and `Desired` wants an `--action`: the one thing that closes it.

**Notes are a log.** What is learned about a stakeholder or a communication goes in a dated entry on top, never over the last one (a group has no notes; what is learned belongs to its members or its communications):

```
python <skill>/scripts/stk.py note <reg> --id S.4 --title "Budget" "wants a monthly figure, not a quarterly one"
```

It is stored as `2026-11-04 · Budget: …`, or `2026-11-04: …` without a title; a title is a few words with no colon. The change log records `Note added`, never the text. `add --notes` writes the first entry. `set --notes` is refused, since it would overwrite the history; `set --notes "" --reason "..."` clears the whole log, for a note that should never have been written.

**Write a note to be read in a list**, since the dashboard shows the log as one:

- Write what changes how they are engaged: a position, a concern, a preference, something they committed to. What happened in a conversation is its meeting notes (notebook-capture); the note can point to them.
- One sentence on what was learned, then at most one or two on what it means for engaging them. Past 400 characters `note` says so; the detail belongs in the meeting notes.
- A title for anything that will be looked for later.
- What they said or did, not a judgement of their character, written as something they would not mind reading: the page with notes can still travel.
- No contact details (`check` warns on what looks like an email address or a phone number), and no health, family or money matters unless engaging them depends on it.
- `S.n` and `C.n` in the text link to that row on the dashboard.

### What a communication's report tells: its focus

A communication carrying a report may be given a **focus**: the WBS rows (any level) and milestones its readers should hear about now, because they care about them or because they tell the story at this point.

```bash
python <skill>/scripts/stk.py focus <reg> --id C.2 --items "201,M1,M2"   # set, dated (Focus Set) and logged
python <skill>/scripts/stk.py focus <reg> --id C.2                       # print it
python <skill>/scripts/stk.py focus <reg> --id C.2 --items ""            # clear: the report tells the key deliverables
```

- **Another project's row or milestone is named by its register's scope**: `P12#77`, `Atlas#M1` (the scope as the register gives it, or its leading code, in any case). A bare `201` or `M1` is the communication's own project. A project without a portfolio number is named the same way, by its register's scope.
- Its report (`report.py export --comm C.2`) tells the focus under *Roadmap · in focus*, with each focused row's delivery journey, in place of the key deliverables. A **status report** tells the items in its own project and notes the rest as told elsewhere; a **sprint update** tells them across all the projects it spans, each in a lane of its own. **With no focus, the report tells the key deliverables**, as it always has.
- **The focus is not `Key Deliverable`.** A key deliverable is a lasting fact the planning checks rely on; a focus changes from report to report and differs by audience, so it belongs to the communication, not the row.
- **It is dated, so it is revisited:** the owner's status report lists each communication's focus with its date and asks whether it is still the story. Change it when the story moves; clear it when the key deliverables say enough.

### Send a communication

1. `python <skill>/scripts/stk.py audience <reg> --id C.2 [--split]` — the people, each once, with the address for the channel (falling back to the person's preferred channel), anyone with no address, and the share level. `external` means anyone in the audience is external: the external copy goes to all of them, or `--split` gives the two lists for two sends.
2. A report: generate it with the reporting tool, then `report.py export "<record>" --comm C.n`, which takes the share level from this communication and writes the copy into the communication's folder as a **sending** (below).
3. The user sends it.
4. `python <skill>/scripts/stk.py done <reg> --id C.2 [--file <path> ...] [--link URL] [--sending "<name>"] [--on YYYY-MM-DD] [--note "..."]`. Content: `--piece <post bundle>` with the link where it was published.

### Where what was sent is kept

- **Each communication has a folder, and each sending a subfolder** holding everything that went out together: the report, the email that carried it, an attachment, a dashboard image, a video. `PrjMgm/Comms/C.2 <name>/<sending>/`, or under `Confidential/Comms/` for a communication marked **`Confidential: Y`** (`stk.py set --id C.2 --confidential Y`; default N; a public, content communication can never be Y). The planning folder may be numbered (`0. PrjMgm`, `03. PrjMgm`); so may the folders in it.
- **The two Comms folders are created when first needed**, recorded in the project's artifact register where it has one, governed by this tool. Everything inside them is this tool's and is never registered one by one. The folder is found by the communication's ID, so a renamed communication keeps it.
- **A sending is named by what it carries**: the report record's name (`2026-11-06 Status`), a content piece's date and title, or the name given with `--sending` (a date, by default, when `done` brings files and no export made one).
- **Exporting the same sending again moves the earlier copy into its `PreviousV/`**, stamped with when it was written; nothing that may have gone out is overwritten.
- **`done` marks a sending as gone**: it archives into the latest sending not yet sent (what the last export wrote) unless `--sending` names one, copies the `--file`s in (refusing a name already there), writes `Sent.md` (when, to whom by name, the files, where it went, the focus at the time) and logs the same on the communication. Done with no files and no export stamps *Last Done* as before. A register outside a PrjMgm folder has nowhere to keep them, and `done` says so.
- **Content**: `--piece` copies the published post's artifacts (not its backbone) from `content-system/posts/<date-slug>/`, reading it and writing nothing there.
- **`Reports/` and `Comms/` keep different things**: `Reports/<type>/` holds a report's record (its data, the ratings and summary confirmed, the trends read from it) and the owner's working view, never sent; `Comms/` holds what was sent, the only place a reader's copy lives.
- The dashboard's communication detail lists its sendings, newest first, linked; `check` flags a public communication marked confidential and a folder whose communication is gone.

### What is due

```
python <skill>/scripts/stk.py due <reg>... | --all [--root DIR]  [--as-of DATE] [--within DAYS] [--overdue] [--events]
```

- **Calendar cadences** fall due that long after `Last Done`; overdue once passed. `--within 7` also lists those falling due in the coming week.
- **`per sprint`** is due during each sprint: done since the current sprint started is on track; last done in the previous sprint (or never) is due; a whole sprint missed is overdue. The sprint calendar is the project's agile conventions file, else its WBS register, searched from the register's folder upward to the planning folder. With neither, `per sprint` reads as every 14 days, and `due` says so.
- **`on event`** is never due; `--events` lists them so they are not forgotten.
- Never done is due.

`--all` reads every register under `--root` (default: the current folder), found by `meta.kind`.

### Check

```
python <skill>/scripts/stk.py check <reg>
python <skill>/scripts/stk.py check --all [--root DIR]   # every project, plus contacts that disagree across projects
```

Within a project: a register outside a Confidential folder, a `per sprint` communication with no sprint calendar found, unknown or inactive IDs in groups and audiences, a group with no active members, missing analysis fields, a gap with no engagement action, a note holding what looks like an email address or phone number (on any row, active or not), a stakeholder with no contacts row (and the reverse), a recipient with no address for the channel, a contacts file git tracks or would take, a `content:` channel whose plan cannot be found (checked against the nearest `content-system/strategies/` at or above the register; with none, a note says the pointers were not checked). Across projects: the same name or email with different details, among the stakeholders active in each, named without the values. Each finding is a decision for the user; nothing is fixed silently.

### Refresh the dashboard

```
python <skill>/scripts/refresh_stk.py <reg> [--as-of DATE]
```

After any batch of writes; `stk.py` says when it has gone stale. It writes two pages: `Stakeholder Dashboard.html` with each row's notes, for your own use, and `Stakeholder Dashboard (no notes).html` without them, in rows or in the change log. The second still holds engagement and stakes, so who it goes to is still your call.

Tabs: the power/interest grid, engagement (gaps first), communications (overdue first), groups, findings, change log. **Active rows by default:** the grid shows active stakeholders only and counts the rest; engagement, communications and groups add the inactive rows with the *Show inactive* switch. **A name opens its detail.** A stakeholder's: who they are, where they stand, the communications that reach them and when each is due. A communication's: what it is, when it is due, who it reaches. Both end with findings, notes and changes. Notes show one block per entry, dated and titled, a long one folded and the newest open. It shows a count of recipients, never an address.

## In the ceremonies

- **Sprint close-out** (`sprint-facilitator`): after the status reports, `due` for each project the sprint spanned; for each communication due, `audience`, the report at its share level, sent or skipped, `done`.
- **Weekly review** (`weekly-review-facilitator`): read only. `due --all --overdue` and `gaps --all` (stakeholders below the engagement wanted, with no action); three lines at most.
- **On demand:** `check --all`, for the contacts that disagree across projects.

## Relationship to other tools

- **`reporting` (TSP.10)** — reads a project's audiences and share levels through `audiences_for`; its external copy is what an `external` audience receives.
- **`raid-manager` (TSP.2)** — an engagement action may be a RAID Action, referenced `<scope>#A.n`; RAID's `Sharable` decides what reaches the external copy.
- **The Project Brief** — says what the project is for; the people and what they hear are here.
- **`action-tracker-manager` (TSP.12)** — holds what other people owe; this register holds who they are and what they hear.
- **`notebook-capture` (TSP.7)** — notes of an interactive communication (a meeting) are its meeting notes.
- **The content system (TSP.6)** — a public audience's communication points to one of its plans; a published piece is copied into the communication's folder with `done --piece`. It is never written from here.
