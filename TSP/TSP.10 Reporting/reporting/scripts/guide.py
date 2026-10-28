# -*- coding: utf-8 -*-
"""The project guide's pages, from its record (report.py guide).

Two editions from one record: the team guide, for the product team (why the
project exists, what it runs on, how the work runs, a path per role), and the
executive overview, for people outside the team (the principles, the operating
model, the system at a glance), which holds no names, paths or commands.

The record is gathered by report.py from the project's own files; this module
only renders it. Which status tool the team uses (the team board or the WBS
through the agent) changes what the paths tell people to do.
"""
import html
import json
from datetime import date, timedelta


def e(text):
    return html.escape("" if text is None else str(text))


# ─── What each installed tool is, for a newcomer ─────────────────────────────
#
# Headed by the answer, not the name. `changes`: who changes it. `say`: what to
# say, and to whom, to use it. Keyed by skill; a skill not listed here is shown
# by its tool's name only.

TOOLS = {
    "project-definition-manager": ("The brief says why the project exists", "the product manager",
                                   "What is the outcome of this project?"),
    "wbs-manager": ("The WBS is the backlog: every piece of work, and when", "the product manager, through the agent",
                    "What is in this sprint?"),
    "status-board-manager": ("The team board is where you update your own work, each sprint", "everyone on the team",
                             None),
    "raid-manager": ("The RAID holds what could go wrong, and what was decided", "anyone can raise; the product manager reviews",
                     "Raise a risk: the test environment is shared with another team."),
    "sprint-facilitator": ("The sprint records say what was committed, and how it went", "the product manager, at each ceremony",
                           "What are this sprint's goals?"),
    "reporting": ("The status report says how the project is going", "generated each sprint; nobody edits it",
                  "How is the project doing?"),
    "stakeholder-manager": ("The stakeholder register says who hears what, and when", "the product manager",
                            "What updates are due this week?"),
    "weekly-review-facilitator": ("The weekly review keeps the week on track", "the product manager, each week",
                                  "Let's do the weekly review."),
    "action-tracker-manager": ("Action trackers hold the small actions agreed in a working session", "whoever owns the session",
                               "What is still open from the last session?"),
    "artifact-register": ("The artifact register says where every document lives", "the product manager",
                          "Where is the test plan filed?"),
    "tsp-manager": ("The tool register lists the tools this project runs on", "the product manager", None),
}
ORDER = ["project-definition-manager", "wbs-manager", "status-board-manager", "raid-manager", "sprint-facilitator",
         "reporting", "stakeholder-manager", "weekly-review-facilitator", "action-tracker-manager", "artifact-register",
         "tsp-manager"]

PRINCIPLES = [
    ("One source for every fact", "Each fact is kept in one place, and every report is generated from it, never retyped.",
     "Two reports never disagree, because they come from the same records."),
    ("Agents do the clerical work; people decide", "An AI agent updates the records and drafts the reports. Ratings and decisions are confirmed by a person.",
     "Every rating you see was confirmed by someone accountable."),
    ("A fixed rhythm", "Two-week sprints, each ending in a review of what was delivered, with a look at the week in between.",
     "You know when you'll hear, and what about."),
    ("Done means verified", "Work is done when its acceptance criteria are checked, and the verdict is written down.",
     "“Done” in a report has evidence behind it."),
    ("Risks and changes in the open", "Risks, issues and changes are logged with an owner and a date, and decided on the record.",
     "A change that affects you reaches you as a decision to make, not a surprise."),
    ("What leaves the team is chosen", "Nothing is shared by default. Each item in a shared copy was marked for it.",
     "What you receive was meant for you."),
]

GLOSSARY = [
    ("Sprint", "Two weeks of committed work, with goals."),
    ("WBS", "Work breakdown structure: every piece of work, from deliverables down to tasks, with its estimate and sprint."),
    ("Team board", "This sprint's tasks, in Excel. Each task names the WBS row it helps deliver."),
    ("Consolidation", "Bringing the team board into the WBS: the product manager confirms each change."),
    ("Acceptance criteria", "The checks that say a piece of work is done. Each gets a verdict when it closes: met, partly met or not met."),
    ("Pull-in", "Work taken into a running sprint that did not plan it, with what it displaces said out loud."),
    ("RAID", "Risks, actions, issues, decisions, ideas, changes and lessons, in one register."),
    ("Close-out", "The sprint's last day: what was delivered, the status report, and what carries over."),
    ("Retro", "The team looks at how it worked, and picks one thing to change."),
    ("Brief", "The one document that says why the project exists and how we'll know it worked."),
]
TERMS = {"WBS": GLOSSARY[1][1], "team board": GLOSSARY[2][1], "consolidates": GLOSSARY[3][1],
         "acceptance criteria": GLOSSARY[4][1], "pull-in": GLOSSARY[5][1], "RAID": GLOSSARY[6][1]}


def term(word, text=None):
    tip = TERMS.get(word) or TERMS.get(word.lower())
    return '<dfn tabindex="0" data-tip="%s">%s</dfn>' % (e(tip), e(text or word)) if tip else e(text or word)


# ─── The paths, by role ──────────────────────────────────────────────────────

def paths(rec):
    """{role: [(title, body, to, say, asks)]}. `to` names who you say it to: the
    agent, Copilot in Excel, or the board itself."""
    board = rec["status_tool"] == "board"
    weekly = rec["ceremonies"].get("weekly")
    pm = []
    pm.append(("Own the brief", "The outcome and the Stop if line are yours. If either is wrong, change the brief first; everything else follows from it.",
               "your agent", "Show me the brief, and what it says the project is for.", "It opens the brief and walks you through each part."
               if rec.get("brief") else "There is no brief yet: it offers to draft one from the project's documents for you to confirm."))
    pm.append(("Plan the sprint", "Capacity first, then goals, then items. The record is written as you go%s." %
               (", and its last step sets up the team board" if board else ""), "your agent", "Let's run sprint planning.",
               "It asks for capacity, then goals, then proposes the items."))
    if board:
        pm.append(("Consolidate the board each week", "The team updates the board; you bring it into the WBS. Every change is proposed, and nothing reaches the WBS until you confirm it.",
                   "your agent", "Let's do the weekly review." if weekly else "Consolidate the team board.",
                   "It proposes, per WBS row, what moved: starts, closes with a drafted note, blocked tasks, new work."))
    else:
        pm.append(("Keep the WBS current", "The team tells you what moved, or tells the agent; you keep the one record.", "your agent",
                   "What changed in the sprint this week?", "It lists the rows that moved and asks what to record."))
    pm.append(("Close out the sprint", "What was delivered, what carries over, the status report and the updates due.", "your agent",
               "Let's close out the sprint.", "It %swalks the committed items one by one, then drafts the status report for you to confirm."
               % ("consolidates the board first, then " if board else "")))
    pm.append(("Keep the RAID honest", "Every open risk has an owner and a date to look again.", "your agent", "What risks need a look?",
               "It lists those past their review date."))
    if board:
        dev = [
            ("Find your tasks", "Open the team board and filter Owner to your name. Each row is a task; its WBS item says what it helps deliver.",
             "the team board", "Filter the Owner column to your name.", ""),
            ("Move a task", "Set Status as the work moves, and add a dated note on top of its Notes.", "Copilot in Excel",
             "Mark the task Login form as Doing, and add a note on top dated today with my name: started.", "It updates the row the way the How to update sheet says."),
            ("Split the work", "A WBS row can have several tasks. Add a row, pick its WBS ID from the list, give it a Task.", "Copilot in Excel",
             "Add a task under WBS 12: write the unit tests, owner me, status Doing.", ""),
            ("Finish a task", "Done, with an AC verdict against the WBS row's acceptance criteria it covers. A partly met says in the notes what is left.",
             "Copilot in Excel", "Mark the task Login form as Done, AC verdict met, and add a dated note on top: released to test.", ""),
            ("Say what's in the way, or what's new", "Blocked with a note when you're stuck. New work goes in as a task with no WBS ID; the product manager decides where it belongs.",
             "Copilot in Excel", "Add a task with no WBS ID: fix the login timeout, status Doing, with a dated note: found in testing.", ""),
        ]
        val = [
            ("Know what done means", "Each WBS row states how it is verified. Challenge weak acceptance criteria before the work starts.",
             "the product manager", "Which rows this sprint have weak acceptance criteria?", "The agent lists rows with none, or vague ones."),
            ("Track your own tasks", "Your test and review work is on the board like anyone's: filter Owner to your name.", "the team board",
             "Filter the Owner column to your name.", ""),
            ("Record verdicts", "On a Done task, the AC verdict: met, partly met or not met. A partly met says in the notes what is left.",
             "Copilot in Excel", "Set the AC verdict of the task Form test scripts to partly met, with a dated note: two edge cases left.", ""),
            ("Follow the verification", "The WBS dashboard's Verification tab shows each requirement and its verdict, once consolidated.",
             "the WBS dashboard", "Open the Verification tab.", ""),
            ("Speak to quality at the review", "Your read feeds the status report's On Quality rating.", "the product manager",
             "How does quality look this sprint?", "The agent drafts the evidence; the product manager confirms the rating."),
        ]
    else:
        dev = [
            ("See what's yours", "The sprint's work is in the WBS; ask for your rows.", "the agent", "What's in this sprint for me?", "It lists your rows and anything due."),
            ("Start a piece of work", "Say when you start, so the board shows it.", "the agent", "I'm starting the login form.", "It moves the row to Implementing."),
            ("Finish it properly", "Done means each acceptance criterion has a verdict.", "the agent", "The login form is done.", "It asks about each criterion, then closes the row."),
            ("Say when something's unplanned", "Unplanned work is fine; its effect is said out loud.", "the agent", "I need to fix the login bug this sprint.", "It asks what it displaces."),
            ("Raise what's in the way", "A risk or an issue goes in the RAID with an owner.", "the agent", "We're blocked on the test environment.", "It asks who owns it and when to look again."),
        ]
        val = [
            ("Know what done means", "Each WBS row states how it is verified. Challenge weak criteria before work starts.", "the agent",
             "Which rows this sprint have weak acceptance criteria?", "It lists rows with none, or vague ones."),
            ("See what's verified", "The verification view shows each requirement and its verdict.", "the agent", "Show me what's been verified.", "It summarises verdicts."),
            ("Follow a partial verdict", "A criterion partly met says where the rest went.", "the agent", "Where did the rest of row 12 go?", "It follows the closure note."),
            ("Check the documents", "What the work must leave behind, and whether it has.", "the agent", "Which deliverables still lack their documents?", "It checks the document rows."),
            ("Speak to quality at the review", "Your read feeds the status report's On Quality rating.", "the agent", "How does quality look this sprint?", "It drafts the evidence."),
        ]
    return {"Product manager": pm, "Developer": dev, "Validation and quality": val}


# ─── The rhythm, drawn ───────────────────────────────────────────────────────

def rhythm_svg(rec):
    s = rec.get("sprint")
    if not s:
        return '<p class="muted">No sprint calendar found, so the rhythm cannot be drawn.</p>'
    start, end = date.fromisoformat(s["starts"]), date.fromisoformat(s["ends"])
    days = [(start + timedelta(days=i)) for i in range((end - start).days + 1)]
    w, x0, y, h = 48, 10, 44, 70
    width = x0 * 2 + w * len(days)
    cer = rec["ceremonies"]
    workdays = [d for d in days if d.weekday() < 5]
    first, last = (workdays[0], workdays[-1]) if workdays else (days[0], days[-1])
    out = ['<svg viewBox="0 0 %d 150" role="img" aria-label="The sprint from %s to %s: planning on its first day, the review and close-out on its last%s.">'
           % (width, s["starts"], s["ends"], ", a weekly review each Friday" if cer.get("weekly") else ""),
           '<text class="rh-tb" x="10" y="20">Sprint %s · %s to %s</text>' % (e(s["id"]), start.strftime("%d %b"), end.strftime("%d %b"))]
    today = date.fromisoformat(rec["as_of"])
    for i, d in enumerate(days):
        x, we = x0 + i * w, d.weekday() >= 5
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="6" class="rh-day%s"/>' % (x + 2, y, w - 4, h, " rh-we" if we else ""))
        out.append('<text x="%d" y="%d" text-anchor="middle" class="rh-m">%s %d</text>' % (x + w / 2, y + h + 16, "MTWTFSS"[d.weekday()], d.day))
        if we:
            continue
        cx = x + w / 2
        if d == first and cer.get("planning"):
            out.append('<path d="M%d,%d l9,9 l-9,9 l-9,-9 z" class="rh-dot"/><text x="%d" y="%d" text-anchor="middle" class="rh-t">Plan</text>' % (cx, y + 14, cx, y + 50))
        elif d == last and cer.get("closeout"):
            out.append('<path d="M%d,%d l9,9 l-9,9 l-9,-9 z" class="rh-dot"/><text x="%d" y="%d" text-anchor="middle" class="rh-t">Review</text>'
                       '<text x="%d" y="%d" text-anchor="middle" class="rh-m">+ retro</text>' % (cx, y + 14, cx, y + 50, cx, y + 63))
        else:
            out.append('<circle cx="%d" cy="%d" r="5" class="rh-dot"/>' % (cx, y + 23))
        if d.weekday() == 4 and cer.get("weekly") and d != last:
            out.append('<path d="M%d,%d l7,12 l-14,0 z" class="rh-dot"/><text x="%d" y="%d" text-anchor="middle" class="rh-m">weekly</text>' % (cx, y + 38, cx, y + 64))
    if start <= today <= end:
        tx = x0 + (today - start).days * w + w / 2
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" class="rh-today"/>' % (tx, y - 8, tx, y + h + 4))
    out.append("</svg>")
    return "".join(out)


def rhythm_legend(rec):
    cer, board = rec["ceremonies"], rec["status_tool"] == "board"
    items = ["● %s" % ("Each working day: the team updates its tasks on the board" if board else "Each working day: the work moves, and the WBS is told")]
    if cer.get("planning"):
        items.append("◆ Planning on day 1%s; review, close-out and retro on the last day" % (", which sets up the board" if board else ""))
    if cer.get("weekly"):
        items.append("▲ Friday: the product manager's weekly review%s" % (", which consolidates the board" if board else ""))
    items.append('<span class="today-key">┆ today</span>')
    return '<div class="legend">%s</div>' % "".join("<span>%s</span>" % i for i in items)


# ─── The pages ───────────────────────────────────────────────────────────────

CSS = """
:root {
  --page:#f6f6f4; --surface:#fcfcfb; --raised:#ffffff; --border:rgba(11,11,11,0.10); --ink:#0b0b0b; --ink2:#52514e;
  --muted:#77756f; --grid:#e1e0d9; --s1:#2a78d6; --s1bg:#e3edfa; --s1ink:#1d5aa6;
  --good:#0ca30c; --goodbg:#e8f5e8; --crit:#d03b3b;
  --font:system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; --mono:ui-monospace, "Cascadia Mono", Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --page:#0d0d0d; --surface:#1a1a19; --raised:#222220; --border:rgba(255,255,255,0.10); --ink:#ffffff; --ink2:#c3c2b7;
  --muted:#9a988f; --grid:#2c2c2a; --s1:#3987e5; --s1bg:#17263a; --s1ink:#8dbaf2; --goodbg:#16301a; color-scheme: dark; } }
:root[data-theme="dark"] {
  --page:#0d0d0d; --surface:#1a1a19; --raised:#222220; --border:rgba(255,255,255,0.10); --ink:#ffffff; --ink2:#c3c2b7;
  --muted:#9a988f; --grid:#2c2c2a; --s1:#3987e5; --s1bg:#17263a; --s1ink:#8dbaf2; --goodbg:#16301a; color-scheme: dark; }
* { box-sizing:border-box; }
body { margin:0; background:var(--page); color:var(--ink); font-family:var(--font); font-size:15px; line-height:1.55; }
.wrap { max-width:1120px; margin:0 auto; padding-inline:16px; padding-block:0 48px; }
h1, h2, h3 { text-wrap:balance; margin:0; } p { margin:0; } a { color:var(--s1ink); }
:focus-visible { outline:2px solid var(--s1); outline-offset:2px; border-radius:4px; }
.top { position:sticky; top:0; z-index:5; background:var(--page); border-bottom:1px solid var(--border); }
.top .wrap { display:flex; flex-wrap:wrap; align-items:center; gap:10px 16px; padding-block:10px; }
.brand { display:flex; flex-direction:column; min-width:0; margin-right:auto; }
.brand b { font-size:16px; } .brand span { font-size:12px; color:var(--muted); }
.search { position:relative; flex:1 1 200px; max-width:280px; }
.search input { width:100%; font:inherit; font-size:13.5px; padding:7px 10px; border:1px solid var(--border); border-radius:8px; background:var(--surface); color:var(--ink); }
.results { position:absolute; left:0; right:0; top:calc(100% + 4px); background:var(--raised); border:1px solid var(--border); border-radius:8px; box-shadow:0 6px 24px rgba(0,0,0,.12); max-height:320px; overflow:auto; }
.results a { display:block; padding:8px 10px; text-decoration:none; color:var(--ink); font-size:13.5px; border-bottom:1px solid var(--border); }
.results a small { display:block; color:var(--muted); font-size:12px; } .results a:last-child { border-bottom:0; }
.layout { display:grid; grid-template-columns:220px minmax(0,1fr); gap:32px; padding-top:24px; }
nav.map { position:sticky; top:76px; align-self:start; }
nav.map ol { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; }
nav.map li.group { font-size:11px; letter-spacing:.8px; text-transform:uppercase; color:var(--muted); margin:14px 0 4px 10px; }
nav.map a { display:block; text-decoration:none; color:var(--ink2); font-size:14px; padding:6px 10px; border-radius:6px; }
nav.map a:hover { background:var(--surface); }
nav.map a[aria-current="true"] { background:var(--s1bg); color:var(--s1ink); font-weight:600; }
@media (max-width:860px) { .layout { grid-template-columns:minmax(0,1fr); gap:16px; padding-top:12px; }
  nav.map { position:static; overflow-x:auto; } nav.map ol { flex-direction:row; gap:6px; padding-bottom:4px; }
  nav.map li.group { display:none; } nav.map a { white-space:nowrap; border:1px solid var(--border); background:var(--surface); font-size:13px; } }
main { min-width:0; display:flex; flex-direction:column; gap:40px; }
section.part { display:flex; flex-direction:column; gap:16px; scroll-margin-top:90px; }
.eyebrow { font-size:12px; letter-spacing:.8px; text-transform:uppercase; color:var(--s1ink); font-weight:600; }
.part > header { display:flex; flex-direction:column; gap:6px; max-width:62ch; }
.part > header h2 { font-size:24px; line-height:1.25; } .part > header p { color:var(--ink2); }
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px 18px; display:flex; flex-direction:column; gap:8px; min-width:0; }
.card h3 { font-size:16px; line-height:1.35; } .card p { color:var(--ink2); font-size:14.5px; }
.facts { display:grid; grid-template-columns:auto 1fr; gap:4px 12px; font-size:13.5px; margin:4px 0 0; }
.facts dt { color:var(--muted); } .facts dd { margin:0; min-width:0; overflow-wrap:anywhere; } .facts code { font-family:var(--mono); font-size:12.5px; }
.say { margin-top:auto; border-top:1px dashed var(--grid); padding-top:10px; font-size:13.5px; display:flex; flex-direction:column; gap:4px; }
.say b { font-size:11px; letter-spacing:.6px; text-transform:uppercase; color:var(--muted); font-weight:600; }
.say q { quotes:"\\201C" "\\201D"; color:var(--ink); font-weight:600; } .say span { color:var(--muted); font-size:13px; }
.src { font-size:12px; color:var(--muted); } .muted { color:var(--muted); }
.next { align-self:flex-start; font-size:14px; text-decoration:none; font-weight:600; }
.hero { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:24px; display:flex; flex-direction:column; gap:14px; }
.hero .statement { font-size:22px; line-height:1.35; max-width:48ch; text-wrap:balance; }
.hero .lede { color:var(--ink2); max-width:62ch; }
.now { display:flex; flex-wrap:wrap; gap:8px; }
.chip { display:inline-flex; align-items:center; gap:6px; font-size:13px; padding:4px 10px; border-radius:16px; background:var(--page); border:1px solid var(--border); color:var(--ink2); }
.chip .dot { width:8px; height:8px; border-radius:50%; background:var(--good); }
.doors { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px; }
@media (max-width:700px) { .doors { grid-template-columns:minmax(0,1fr); } }
.door { text-decoration:none; color:var(--ink); background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px 18px; display:flex; flex-direction:column; gap:6px; }
.door:hover { border-color:var(--s1); }
.door .k { font-size:12px; letter-spacing:.8px; text-transform:uppercase; color:var(--s1ink); font-weight:700; }
.door b { font-size:16px; line-height:1.35; } .door span { font-size:13px; color:var(--muted); }
.tree { font-family:var(--mono); font-size:13px; line-height:1.8; background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 18px; overflow-x:auto; }
.tree ul { list-style:none; margin:0; padding-left:18px; border-left:1px solid var(--grid); }
.tree > ul { padding-left:0; border-left:0; }
.tree li span { font-family:var(--font); color:var(--muted); font-size:13px; margin-left:8px; }
.figure { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; overflow-x:auto; }
.figure svg { display:block; min-width:640px; width:100%; height:auto; }
.rh-day { fill:var(--page); stroke:var(--grid); } .rh-we { fill:var(--grid); opacity:.45; } .rh-dot { fill:var(--s1); }
.rh-today { stroke:var(--crit); stroke-width:2; stroke-dasharray:4 3; }
.rh-t { fill:var(--ink2); font:12px var(--font); } .rh-tb { fill:var(--ink); font:600 12px var(--font); } .rh-m { fill:var(--muted); font:11px var(--font); }
.legend { display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--ink2); margin-top:10px; } .today-key { color:var(--crit); }
.roles { display:flex; flex-wrap:wrap; gap:8px; }
.roles button { font:inherit; font-size:14px; padding:8px 14px; border-radius:20px; border:1px solid var(--border); background:var(--surface); color:var(--ink); cursor:pointer; }
.roles button[aria-pressed="true"] { border-color:var(--s1); background:var(--s1bg); color:var(--s1ink); font-weight:600; }
.path { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px; display:grid; grid-template-columns:220px minmax(0,1fr); gap:20px; }
@media (max-width:700px) { .path { grid-template-columns:minmax(0,1fr); } }
.steps { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; }
.steps button { width:100%; text-align:left; font:inherit; font-size:14px; padding:7px 10px; border:0; border-radius:6px; background:transparent; color:var(--ink2); cursor:pointer; display:flex; gap:10px; align-items:baseline; }
.steps button .n { font-variant-numeric:tabular-nums; font-size:12px; color:var(--muted); min-width:1.2em; }
.steps button[aria-current="true"] { background:var(--s1bg); color:var(--s1ink); font-weight:600; } .steps button.done .n { color:var(--good); }
.stepbody { display:flex; flex-direction:column; gap:10px; min-width:0; }
.progress { font-size:12px; color:var(--muted); letter-spacing:.4px; }
.bar { height:4px; background:var(--grid); border-radius:2px; overflow:hidden; } .bar i { display:block; height:100%; background:var(--s1); width:20%; transition:width .25s; }
.stepbody h3 { font-size:19px; } .stepbody p { color:var(--ink2); max-width:62ch; }
.stepnav { display:flex; gap:8px; margin-top:6px; }
.btn { font:inherit; font-size:14px; padding:7px 14px; border-radius:8px; border:1px solid var(--border); background:var(--raised); color:var(--ink); cursor:pointer; }
.btn.primary { background:var(--s1); border-color:var(--s1); color:#fff; } .btn[disabled] { opacity:.45; cursor:default; }
dfn { font-style:normal; border-bottom:1px dotted var(--muted); cursor:help; position:relative; }
dfn[data-tip]:hover::after, dfn[data-tip]:focus::after, dfn.open::after { content:attr(data-tip); position:absolute; left:0; top:calc(100% + 6px); z-index:4; width:min(280px, 70vw);
  background:var(--raised); color:var(--ink); border:1px solid var(--border); border-radius:8px; padding:8px 10px; font-size:13px; line-height:1.45; box-shadow:0 6px 24px rgba(0,0,0,.14); font-weight:400; }
.gloss { display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:10px 24px; }
.gloss div { border-top:1px solid var(--grid); padding-top:8px; } .gloss b { display:block; font-size:14px; } .gloss span { font-size:13.5px; color:var(--ink2); }
.means { font-size:13.5px; color:var(--ink); background:var(--page); border-radius:6px; padding:8px 10px; }
.means b { font-size:11px; letter-spacing:.6px; text-transform:uppercase; color:var(--muted); display:block; font-weight:600; }
.table { overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface); }
.table table { border-collapse:collapse; width:100%; font-size:14px; min-width:480px; }
.table th, .table td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--grid); vertical-align:top; }
.table th { font-size:12px; letter-spacing:.6px; text-transform:uppercase; color:var(--muted); font-weight:600; } .table tr:last-child td { border-bottom:0; }
.sys .reg { fill:var(--s1bg); stroke:var(--s1); } .sys .rep { fill:var(--goodbg); stroke:var(--good); }
.sys .arrow { stroke:var(--muted); stroke-width:1.4; fill:none; } .sys .ah { fill:var(--muted); }
.cards.pairs { grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }
.pmtools { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 18px; display:flex; flex-direction:column; gap:6px; }
.pmtools h3 { font-size:15px; } .pmtools p { color:var(--muted); font-size:13px; }
.pmtools ul { list-style:none; margin:4px 0 0; padding:0; display:flex; flex-direction:column; }
.pmtools li { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; padding:7px 0; border-top:1px solid var(--grid); font-size:14px; }
.pmtools li b { font-weight:500; } .pmtools li span { color:var(--muted); font-family:var(--mono); font-size:12.5px; overflow-wrap:anywhere; }
@media (max-width:700px) { .pmtools li { grid-template-columns:minmax(0,1fr); gap:2px; } }
.print-only { display:none; }
footer { margin-top:40px; font-size:12px; color:var(--muted); }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; scroll-behavior:auto !important; } }
@media print {
  .top .search, nav.map, .roles, .path, .next, .doors { display:none !important; }
  .top { position:static; } .layout { display:block; } .print-only { display:block; }
  section.part { break-inside:avoid-page; } .card { break-inside:avoid; }
  body { font-size:12.5px; } .figure svg { min-width:0; }
}
"""

JS = """
(function () {
  "use strict";
  var PATHS = %s, role = Object.keys(PATHS)[0] || null, step = 0;
  var map = document.getElementById("map");
  function parts() { return Array.prototype.slice.call(document.querySelectorAll("section.part")); }
  (function buildMap() { var last = null;
    parts().forEach(function (s) { var g = s.getAttribute("data-group");
      if (g && g !== last) { var gl = document.createElement("li"); gl.className = "group"; gl.textContent = g; map.appendChild(gl); }
      last = g; var li = document.createElement("li"), a = document.createElement("a");
      a.href = "#" + s.id; a.textContent = s.getAttribute("data-title"); li.appendChild(a); map.appendChild(li); }); })();
  function track() { var cur = null, ps = parts();
    ps.forEach(function (s) { if (s.getBoundingClientRect().top < 140) cur = s.id; });
    if (!cur && ps.length) cur = ps[0].id;
    map.querySelectorAll("a").forEach(function (a) { a.setAttribute("aria-current", a.getAttribute("href") === "#" + cur ? "true" : "false"); }); }
  window.addEventListener("scroll", track, { passive: true }); track();
  var rolesEl = document.getElementById("roles"), stepsEl = document.getElementById("steps");
  function renderPath() {
    if (!rolesEl || !role) return;
    Array.prototype.forEach.call(rolesEl.children, function (b) { b.setAttribute("aria-pressed", b.textContent === role ? "true" : "false"); });
    var p = PATHS[role]; stepsEl.innerHTML = "";
    p.forEach(function (s, i) { var li = document.createElement("li"), b = document.createElement("button"); b.type = "button";
      b.innerHTML = '<span class="n">' + (i < step ? "\\u2713" : i + 1) + "</span><span></span>"; b.lastChild.textContent = s[0];
      if (i === step) b.setAttribute("aria-current", "true"); if (i < step) b.className = "done";
      b.addEventListener("click", function () { step = i; renderPath(); }); li.appendChild(b); stepsEl.appendChild(li); });
    var s = p[step];
    document.getElementById("progress").textContent = role + " \\u00b7 step " + (step + 1) + " of " + p.length;
    document.getElementById("bar").style.width = ((step + 1) / p.length * 100) + "%%";
    document.getElementById("stitle").textContent = s[0]; document.getElementById("sbody").textContent = s[1];
    document.getElementById("sto").textContent = "Say this to " + s[2];
    document.getElementById("ssay").textContent = s[3]; document.getElementById("sask").textContent = s[4] || "";
    document.getElementById("prev").disabled = step === 0;
    document.getElementById("nextstep").textContent = step === p.length - 1 ? "Done" : "Next step"; }
  if (rolesEl) { Object.keys(PATHS).forEach(function (r) { var b = document.createElement("button"); b.type = "button"; b.textContent = r;
      b.addEventListener("click", function () { role = r; step = 0; renderPath(); }); rolesEl.appendChild(b); });
    document.getElementById("prev").addEventListener("click", function () { if (step > 0) { step--; renderPath(); } });
    document.getElementById("nextstep").addEventListener("click", function () { if (step < PATHS[role].length - 1) { step++; renderPath(); } });
    renderPath(); }
  document.addEventListener("click", function (ev) {
    document.querySelectorAll("dfn.open").forEach(function (d) { if (d !== ev.target) d.classList.remove("open"); });
    if (ev.target.tagName === "DFN") ev.target.classList.toggle("open"); });
  var q = document.getElementById("q"), res = document.getElementById("results");
  q.addEventListener("input", function () { var t = q.value.trim().toLowerCase(); res.innerHTML = "";
    if (t.length < 2) { res.hidden = true; return; } var hits = [];
    document.querySelectorAll("section.part [data-search]").forEach(function (c) {
      var text = (c.getAttribute("data-search") + " " + c.textContent).toLowerCase();
      if (text.indexOf(t) >= 0) hits.push({ c: c, sec: c.closest("section.part") }); });
    hits.slice(0, 8).forEach(function (h) { var a = document.createElement("a"), title = (h.c.querySelector("h3") || h.c).textContent.trim().slice(0, 70);
      a.href = "#" + h.sec.id; a.textContent = title; var sm = document.createElement("small"); sm.textContent = h.sec.getAttribute("data-title");
      a.appendChild(sm); a.addEventListener("click", function () { res.hidden = true; q.value = ""; }); res.appendChild(a); });
    if (!hits.length) { var n = document.createElement("a"); n.textContent = "Nothing found. Try sprint, board or risk."; res.appendChild(n); }
    res.hidden = false; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") res.hidden = true; });
})();
"""


def section(sid, title, group, body, eyebrow="", heading="", lede=""):
    head = ""
    if heading:
        head = '<header>%s<h2>%s</h2>%s</header>' % ('<span class="eyebrow">%s</span>' % e(eyebrow) if eyebrow else "",
                                                     e(heading), "<p>%s</p>" % lede if lede else "")
    return '<section class="part" id="%s" data-title="%s" data-group="%s">%s%s</section>' % (sid, e(title), e(group), head, body)


def card(h, body, extra="", search=""):
    return '<div class="card" data-search="%s"><h3>%s</h3>%s%s</div>' % (e(search), h, body, extra)


def say(to, phrase, asks=""):
    return ('<div class="say"><b>Say this to %s</b><q>%s</q>%s</div>' % (e(to), e(phrase), "<span>%s</span>" % e(asks) if asks else ""))


def frame(title, subtitle, sections_html, paths_json="{}", footer=""):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n<meta name=\"generator\" content=\"reporting guide\">\n"
            "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n"
            '<div class="top"><div class="wrap"><div class="brand"><b>%s</b><span>%s</span></div>'
            '<div class="search"><input id="q" type="search" placeholder="Search the guide" aria-label="Search the guide" autocomplete="off">'
            '<div class="results" id="results" hidden></div></div></div></div>\n'
            '<div class="wrap"><div class="layout"><nav class="map" aria-label="Guide map"><ol id="map"></ol></nav><main>%s'
            '<footer>%s</footer></main></div></div>\n<script>%s</script>\n</body></html>\n'
            % (e(title), CSS, e(title), subtitle, sections_html, footer, JS % paths_json))


def _now_chips(rec, board_word=True):
    s = rec.get("sprint")
    chips = []
    if s:
        chips.append('<span class="chip"><span class="dot"></span>Sprint %s · day %d of %d</span>' % (e(s["id"]), s["day"], s["days"]))
        for g in s.get("goals", [])[:2]:
            chips.append('<span class="chip">%s: %s</span>' % (e(g["id"]), e(g["goal"][:80])))
    if rec.get("board") and board_word:
        chips.append('<span class="chip">Team board consolidated %s</span>' % e(rec["board"].get("consolidated") or "not yet"))
    return '<div class="now">%s</div>' % "".join(chips)


def statement(rec):
    b = rec.get("brief") or {}
    return b.get("statement")


def render_team(rec):
    board = rec["status_tool"] == "board"
    b, out = rec.get("brief"), []
    stmt = statement(rec)
    hero = ('<div class="hero"><span class="eyebrow">Welcome to %s</span>' % e(rec["scope"])
            + ('<p class="statement">%s</p>' % e(stmt) if stmt else
               '<p class="statement">%s runs on a small set of tools, a fixed rhythm, and one record of the work.</p>' % e(rec["scope"]))
            + _now_chips(rec) + '<p class="src">%s</p></div>' % e("From the Project Brief and the sprint calendar" if stmt else
                                                                  "This project has no brief yet, so its purpose is not written down: ask the product manager."))
    doors = ('<div class="doors"><a class="door" href="#why"><span class="k">Why</span><b>Why this project exists, and what done looks like</b><span>2 min</span></a>'
             '<a class="door" href="#toolkit"><span class="k">What</span><b>The tools it runs on, where things live, who’s who</b><span>4 min</span></a>'
             '<a class="door" href="#first-week"><span class="k">How</span><b>Your first week, step by step, for your role</b><span>5 min</span></a></div>')
    out.append(section("welcome", "Welcome", "", hero + doors))

    if b:
        cards = [card("The outcome: %s" % e(b.get("outcome") or "not written yet"),
                      "<p>Done when: %s</p>" % e("; ".join(b.get("done_when", [])) or "not written yet"), '<p class="src">Brief · Outcome and done-when</p>', "outcome done")]
        if b.get("why"):
            cards.append(card("Why it matters", "<p>%s</p>" % e(b["why"][:600]), '<p class="src">Brief · Why</p>', "why"))
        if b.get("stop_if"):
            cards.append(card("We stop if %s" % e(b["stop_if"].rstrip(".")), "<p>The one condition that would make finishing not worth it.</p>", '<p class="src">Brief · Stop if</p>', "stop"))
        if b.get("measures"):
            cards.append(card("We measure it by %s" % e(", ".join(m for m in b["measures"][:3])), "<p>The status report scores these each sprint.</p>",
                              '<p class="src">Brief · Measures</p>', "measures"))
        body = '<div class="cards">%s</div>' % "".join(cards)
        heading = b.get("outcome") or "Why this project exists"
    else:
        body = '<div class="card" data-search="brief why"><h3>No brief yet</h3><p>Why the project exists and what done looks like are not written down yet. Ask the product manager; the brief is where they will be.</p></div>'
        heading = "Why this project exists"
    out.append(section("why", "Why we're doing this", "Why", body + '<a class="next" href="#toolkit">Next: the tools →</a>', "Why", heading,
                       "Everything the team does traces back to this. If a task doesn't move it, ask why it's in the sprint."))

    # The tools a team member uses come first, as cards; the product manager's
    # run beneath as one line each, so a first look is four cards, not eleven.
    team_tools = ("project-definition-manager", "status-board-manager" if board else "wbs-manager", "raid-manager", "reporting")
    tcards, pm_rows = [], []
    for t in rec["tools"]:
        info = TOOLS.get(t["skill"])
        if not info:
            continue
        if t["skill"] not in team_tools:
            pm_rows.append('<li data-search="%s"><b>%s</b><span>%s</span></li>' % (e(t["skill"]), e(info[0]), e(t.get("where") or "")))
            continue
        heading, changes, phrase = info
        heading = heading.replace("WBS", term("WBS"), 1).replace("RAID", term("RAID"), 1)
        facts = '<dl class="facts"><dt>Where</dt><dd><code>%s</code></dd><dt>Changes it</dt><dd>%s</dd></dl>' % (e(t.get("where") or "-"), e(changes))
        if t["skill"] == "status-board-manager":
            extra = say("Copilot in Excel", "Mark the task Login form as Doing, and add a note on top dated today with my name: started.",
                        "Or edit the row yourself. The How to update sheet inside the board says how.")
        elif phrase:
            extra = say("your agent" if t["skill"] in ("wbs-manager", "sprint-facilitator", "weekly-review-facilitator", "stakeholder-manager", "tsp-manager", "artifact-register") else "the agent, or the product manager", phrase)
        else:
            extra = ""
        tcards.append(card(heading, facts, extra, t["skill"] + " " + t.get("name", "")))
    lede = ("You rarely open these files yourself. You update your tasks on the team board; the product manager %s it into the WBS. Never edit a generated page by hand."
            % term("consolidates")) if board else "You rarely open these files yourself: you ask the agent, and it reads or updates them. Never edit a generated page by hand."
    pm_list = ('<div class="pmtools"><h3>Run by the product manager</h3><p>You won\'t need these to start; they keep the project\'s records.</p><ul>%s</ul></div>'
               % "".join(pm_rows)) if pm_rows else ""
    out.append(section("toolkit", "The toolkit", "What", '<div class="cards pairs">%s</div>%s<p class="src">From the project\'s tool register and its installed tools</p>'
                       '<a class="next" href="#where">Next: where things are →</a>' % ("".join(tcards), pm_list),
                       "What · 1 of 3", "The %d tools you'll use" % len(tcards), lede))

    tree = "".join('<li>%s<span>%s</span></li>' % (e(f["name"]), e(f.get("about") or "")) for f in rec["folders"])
    out.append(section("where", "Where things are", "What", '<div class="tree" data-search="folder where"><ul><li>%s<span>planning and tracking</span><ul>%s</ul></li></ul></div>'
                       '<p class="src">%s</p><a class="next" href="#who">Next: who’s who →</a>' % (e(rec["folder_name"]), tree,
                       "From the artifact register" if rec.get("folders_from") == "artifact-register" else "From the planning folder"),
                       "What · 2 of 3", "Everything about running the project lives in one folder",
                       "Work products live where the team already keeps them. This folder is for planning and tracking."))

    people = rec.get("people") or {}
    if people.get("groups"):
        pc = "".join(card(e(g["name"]), "<p>%s</p>" % e(" · ".join("%s, %s" % (m["name"], m["role"]) if m.get("name") else m["role"] for m in g["members"])),
                          "", "who " + g["name"]) for g in people["groups"])
        body = '<div class="cards">%s</div><p class="src">From the stakeholder register. Names appear only in the team\'s copy.</p>' % pc
    else:
        body = ('<div class="card" data-search="who people"><h3>Ask the product manager, %s</h3><p>The project keeps no stakeholder register yet, so who’s who is not written down here. '
                'The product manager runs the ceremonies and keeps the WBS.</p></div>' % e(rec.get("pm") or ""))
    out.append(section("who", "Who's who", "What", body, "What · 3 of 3", "Who's who"))

    out.append(section("rhythm", "The rhythm", "How", '<div class="figure" data-search="rhythm sprint ceremonies">%s%s</div>'
                       '<a class="next" href="#first-week">Next: your first week →</a>' % (rhythm_svg(rec), rhythm_legend(rec)),
                       "How · 1 of 3", "Two-week sprints, the same shape each time", "Dates come from the project's sprint calendar."))

    ps = paths(rec)
    printed = "".join('<div class="card"><h3>%s</h3><ol>%s</ol></div>' % (e(r), "".join("<li><b>%s.</b> %s <i>Say this to %s:</i> “%s”</li>" % (e(s[0]), e(s[1]), e(s[2]), e(s[3])) for s in st))
                      for r, st in ps.items())
    widget = ('<div class="roles" role="group" aria-label="Your role" id="roles"></div><div class="path"><ol class="steps" id="steps"></ol>'
              '<div class="stepbody" aria-live="polite"><div class="progress" id="progress"></div><div class="bar"><i id="bar"></i></div>'
              '<h3 id="stitle"></h3><p id="sbody"></p><div class="say"><b id="sto"></b><q id="ssay"></q><span id="sask"></span></div>'
              '<div class="stepnav"><button class="btn" type="button" id="prev">Back</button><button class="btn primary" type="button" id="nextstep">Next step</button></div></div></div>'
              '<div class="print-only">%s</div>' % printed)
    out.append(section("first-week", "Your first week", "How", widget, "How · 2 of 3", "Your first week, for your role",
                       "Pick your role. Five stops, in the order you'll meet them."))

    if board:
        common = [("Update a task", "Status as it moves, and a dated note on top.", "Copilot in Excel", "Mark the task Login form as Doing, and add a dated note on top: started."),
                  ("Add a task under a WBS row", "Pick its WBS ID from the list; the work splits as it needs to.", "Copilot in Excel", "Add a task under WBS 12: write the unit tests, owner me."),
                  ("Finish a task", "Done, with its AC verdict.", "Copilot in Excel", "Mark the task Login form as Done, AC verdict met, with a dated note: released to test."),
                  ("Say you're blocked", "Blocked, with what you're waiting for.", "Copilot in Excel", "Set the task Password reset to Blocked, with a dated note: waiting for the security policy.")]
    else:
        common = [("Pick up a piece of work", "The agent moves it to Implementing.", "the agent", "I'm starting the login form."),
                  ("Finish it", "It asks how each criterion went.", "the agent", "The login form is done."),
                  ("Take on unplanned work", "Fine; say what it displaces.", "the agent", "I need to fix the login bug this sprint."),
                  ("Say you're blocked", "It goes in the RAID with an owner.", "the agent", "We're blocked on the test environment.")]
    out.append(section("common", "Common things", "How", '<div class="cards pairs">%s</div>' % "".join(card(e(h), "<p>%s</p>" % e(p), say(to, s), h) for h, p, to, s in common),
                       "How · 3 of 3", "The things you'll do every week"))

    gl = "".join('<div><b>%s</b><span>%s</span></div>' % (e(w), e(d)) for w, d in GLOSSARY if board or w not in ("Team board", "Consolidation"))
    ask = card("Stuck? Ask the product manager%s" % (", " + e(rec["pm"]) if rec.get("pm") else ""),
               "<p>Or ask the agent first: it can explain any tool in this guide.</p>", "", "ask help")
    out.append(section("glossary", "Glossary", "Help", '<div class="gloss" data-search="glossary words">%s</div>%s' % (gl, ask), "Help", "Words you'll hear"))

    sub = "Project guide for the product team · as of %s" % e(rec["as_of"])
    return frame("%s guide" % rec["scope"], sub, "".join(out), json.dumps(ps, ensure_ascii=False),
                 "Generated from the project's own files; never edited by hand. Regenerate it with report.py guide.")


def render_exec(rec):
    out, stmt = [], statement(rec)
    hero = ('<div class="hero"><span class="eyebrow">How this team works</span>'
            + ('<p class="statement">%s</p>' % e(stmt) if stmt else '<p class="statement">%s</p>' % e(rec["scope"]))
            + '<p class="lede">The team works in two-week sprints, keeps one record of every piece of work, and reports from those records, so what you read is what the team itself works from.</p>'
            + _now_chips(rec, board_word=False) + "</div>")
    doors = ('<div class="doors"><a class="door" href="#principles"><span class="k">Principles</span><b>Six rules the team holds itself to</b><span>2 min</span></a>'
             '<a class="door" href="#operates"><span class="k">Operating model</span><b>The rhythm, and what you’ll receive</b><span>2 min</span></a>'
             '<a class="door" href="#system"><span class="k">System</span><b>The tools, at a glance</b><span>1 min</span></a></div>')
    out.append(section("overview", "In one screen", "", hero + doors))
    pc = "".join(card(e(h), "<p>%s</p>" % e(p), '<div class="means"><b>For you</b>%s</div>' % e(f), h) for h, p, f in PRINCIPLES)
    out.append(section("principles", "The principles", "Why", '<div class="cards">%s</div>' % pc, "Principles", "Six rules the team holds itself to"))

    rows = rec.get("comms") or []
    if rows:
        trs = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(c["what"]), e(c["cadence"]), e(c["audience"])) for c in rows)
        src = "From the communications plan, shared at the external level"
    else:
        trs = ("<tr><td>Status report: delivery, outcome, risks</td><td>Every sprint, at its close-out</td><td>The sponsor and anyone the product manager names</td></tr>"
               "<tr><td>Sprint review</td><td>Every sprint, its last day</td><td>Anyone invited</td></tr>"
               "<tr><td>A decision that needs you</td><td>When it arises</td><td>Whoever owns it</td></tr>")
        src = "The default for a project with no communications plan yet; the product manager sets who receives what"
    table = '<div class="table" data-search="receive status report"><table><thead><tr><th>What</th><th>How often</th><th>For</th></tr></thead><tbody>%s</tbody></table></div><p class="src">%s</p>' % (trs, src)
    out.append(section("operates", "How the team operates", "How", '<div class="figure">%s%s</div>%s' % (rhythm_svg(rec), rhythm_legend(rec), table),
                       "Operating model", "The rhythm, and what you'll receive"))

    regs = [r for r in ("Brief", "Backlog", "Team board", "Risks and decisions", "Sprint records") if r in rec["registers"]]
    notes = {"Brief": "why it exists, how it's measured", "Backlog": "every piece of work, and when", "Team board": "the team's tasks, each sprint",
             "Risks and decisions": "what could go wrong, what was decided", "Sprint records": "what was committed, what was delivered"}
    hgt = max(200, 30 + 56 * len(regs))
    boxes, arrows = [], []
    for i, r in enumerate(regs):
        yy = 16 + i * 56
        boxes.append('<rect class="reg" x="20" y="%d" width="240" height="44" rx="8"/><text class="rh-tb" x="36" y="%d">%s</text><text class="rh-m" x="36" y="%d">%s</text>'
                     % (yy, yy + 20, e(r), yy + 35, e(notes[r])))
        arrows.append('<path class="arrow" d="M260,%d C350,%d 360,%d 446,%d" marker-end="url(#ah)"/>' % (yy + 22, yy + 22, hgt / 2 - 16, hgt / 2 - 16))
    mid = hgt / 2
    svg = ('<svg viewBox="0 0 700 %d" role="img" aria-label="The records on the left feed what you read on the right."><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           '<path class="ah" d="M0,0 L10,5 L0,10 z"/></marker></defs>%s%s'
           '<rect class="rep" x="450" y="%d" width="230" height="52" rx="8"/><text class="rh-tb" x="466" y="%d">Status report</text><text class="rh-m" x="466" y="%d">on time, on scope, quality, resources</text>'
           '<rect class="rep" x="450" y="%d" width="230" height="52" rx="8"/><text class="rh-tb" x="466" y="%d">Your copy</text><text class="rh-m" x="466" y="%d">only what was marked to share</text>'
           '<path class="arrow" d="M565,%d L565,%d" marker-end="url(#ah)"/></svg>'
           % (hgt, "".join(boxes), "".join(arrows), mid - 42, mid - 20, mid - 4, mid + 34, mid + 56, mid + 72, mid + 10, mid + 32))
    out.append(section("system", "The system at a glance", "What", '<div class="figure sys" data-search="system tools">%s</div><a class="next" href="#next-exec">Next: where to go from here →</a>' % svg,
                       "System", "Records on the left, what you read on the right", "The team keeps its records once. Everything you receive is generated from them."))
    out.append(section("next-exec", "Where to go next", "Help", '<div class="cards">%s%s</div>' % (
        card("The project charter", "<p>The project on one page: purpose, scope, approach, key deliverables.</p>", "", "charter"),
        card("The latest status report", "<p>Shared at the end of each sprint, the copy marked for you.</p>", "", "status")),
        "Next", "Two documents, if you want more"))
    sub = "Executive overview, for people outside the team · as of %s" % e(rec["as_of"])
    return frame("%s: how the team works" % rec["scope"], sub, "".join(out), "{}",
                 "Shared from the project's records; generated, never edited by hand.")
