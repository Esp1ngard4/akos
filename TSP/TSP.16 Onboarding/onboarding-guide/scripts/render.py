# -*- coding: utf-8 -*-
"""The onboarding guide's pages, from its record (TSP.16 Onboarding).

Two editions from one record. The team guide, for the product team: why the
project exists, how people and agents work together, the tools, where things
are, who's who, the rhythm, and a path per role in which every step says who
acts. The executive overview, for people outside the team: the AI-first way of
working, the principles, the rhythm and what they will receive, the system as
one loop of people and agents; no names, paths or commands.

Each page is one self-contained HTML file with its fonts embedded, so it looks
the same opened from a shared drive, offline or behind a corporate network.
Nothing on either page changes from one sprint to the next: the rhythm is the
sprint's pattern, and the pages say where the current state is.
"""
import base64
import html
import io
import json
import os

HERE = os.path.dirname(os.path.realpath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")


def e(text):
    return html.escape("" if text is None else str(text))


# ─── Content that does not come from the project ─────────────────────────────

TOOLS = {
    "status-board-manager": ("board", "The team board is where you update your own work", "everyone on the team"),
    "project-definition-manager": ("doc", "The brief says why the project exists", "the product manager"),
    "raid-manager": ("shield", "The RAID holds what could go wrong, and what was decided", "anyone raises; the product manager reviews"),
    "reporting": ("chart", "The status report says how the project is going", "generated each sprint; nobody edits it"),
    "wbs-manager": ("flow", "The backlog (WBS): every piece of work, and when", "the product manager, with the agents"),
    "sprint-facilitator": ("cal", "The sprint records: what was committed, and how it went", "the product manager, at each ceremony"),
    "weekly-review-facilitator": ("cal", "The weekly review: the week kept on track", "the product manager"),
    "stakeholder-manager": ("person", "The stakeholder register: who hears what, and when", "the product manager"),
    "action-tracker-manager": ("check", "Action trackers: the small actions a session agrees", "whoever owns the session"),
    "artifact-register": ("doc", "The artifact register: where every document lives", "the product manager"),
    "tsp-manager": ("flow", "The tool register: the tools this project runs on", "the product manager"),
    "project-guide": ("doc", "This guide", "generated; nobody edits it"),
}
ASK = {
    "status-board-manager": ("agent", "Copilot in Excel", "Mark the task Login form as Doing, with a note on top dated today: started."),
    "project-definition-manager": ("agent", "Your agent", "What is this project for, and how will we know it worked?"),
    "raid-manager": ("person", "The product manager", "The test environment is shared with another team."),
    "reporting": ("agent", "Your agent", "How is the project doing?"),
    "wbs-manager": ("agent", "Your agent", "What is in this sprint for me?"),
}

PRINCIPLES = [
    ("One source for every fact", "Each fact is kept once; every report is generated from it, never retyped.", "Two reports never disagree."),
    ("Agents prepare; people decide", "Agents update the records and draft the reports; a person confirms each change and each rating.", "Every rating has someone accountable behind it."),
    ("A fixed rhythm", "Sprints of a fixed length, a review at the end of each, a look at the week in between.", "You know when you'll hear, and about what."),
    ("Done means verified", "Work is done when its acceptance criteria are checked and the verdict written down.", "“Done” has evidence behind it."),
    ("Risks and changes in the open", "Logged with an owner and a date; decided on the record.", "A change reaches you as a decision, not a surprise."),
    ("What leaves the team is chosen", "Nothing is shared by default; each shared item was marked for it.", "What you receive was meant for you."),
]

GLOSSARY = [
    ("Agent", "An AI assistant that works alongside the team: it does work, keeps the records and prepares. It proposes; a person decides."),
    ("Sprint", "A fixed stretch of committed work, with goals; the same length every time."),
    ("Team board", "This sprint's tasks, in Excel; each names the WBS row it helps deliver."),
    ("Consolidation", "The agent proposes, the product manager confirms: the board reaches the backlog."),
    ("WBS", "The backlog: every piece of work, from deliverables down to tasks, with its estimate and sprint."),
    ("Acceptance criteria", "The checks that say work is done, each with a verdict: met, partly met or not met."),
    ("Pull-in", "Work added to a running sprint, with what it displaces said out loud."),
    ("RAID", "Risks, actions, issues, decisions, ideas, changes and lessons, in one register."),
    ("Close-out", "The sprint's last day: what was delivered, the status report, what carries over."),
    ("Brief", "The one document that says why the project exists and how we'll know it worked."),
    ("Execution folder", "Where each piece of work keeps its trail: one folder per backlog row, with its discovery, spec, plan and notes."),
    ("Spec and plan", "What will be built and how it will be checked, then the steps. An agent drafts them; a person approves the plan before work starts."),
]

ICONS = {
    "spark": '<path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    "person": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    "doc": '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "board": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16M3 9h18"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "flow": '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M7.4 11l9.2-4M7.4 13l9.2 4"/>',
    "cal": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "loop": '<path d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3"/><path d="M18 3v4h-4M6 21v-4h4"/>',
}
SPRITE = '<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>' % "".join(
    '<symbol id="i-%s" viewBox="0 0 24 24">%s</symbol>' % (k, v) for k, v in ICONS.items())


def icon(name):
    return '<svg><use href="#i-%s"/></svg>' % name


def who(kind, text):
    return '<span class="who %s">%s%s</span>' % (kind, icon("spark" if kind == "agent" else "person"), e(text))


# ─── The paths, by role ──────────────────────────────────────────────────────
#
# Each step: (title, body, actors, say-to kind, say-to, phrase, what follows).
# actors: "person" (you), "agent" (an agent does it with you), "both" (you
# decide, the agent prepares).

def paths(rec):
    board = rec["status_tool"] == "board"
    weekly = rec["ceremonies"].get("weekly")
    ex = (rec.get("execution") or {}).get("folder") or "the Execution folder"
    brief = rec.get("brief")
    pm = [
        ("Own the brief", "The outcome and the Stop if line are yours. If either is wrong, change the brief first; everything else follows from it.",
         "both", "agent", "Your agent", "Show me the brief, and what it says the project is for.",
         "It walks you through each part." if brief else "There is no brief yet: it drafts one from the project's documents for you to confirm."),
        ("Plan the sprint", "Capacity first, then goals, then items. The agent writes the record as you go%s." % (", and sets up the team board at the end" if board else ""),
         "both", "agent", "Your agent", "Let's run sprint planning.", "It asks for capacity and proposes the items; you decide."),
        (("Consolidate on Friday", "The team updates the board; the agent proposes, row by row, what moved. Nothing reaches the backlog until you confirm it.",
          "both", "agent", "Your agent", "Let's do the weekly review." if weekly else "Consolidate the team board.",
          "Starts, closes with drafted notes, blocked tasks, new work: you confirm them in one batch.") if board else
         ("Keep the backlog current", "The team tells the agent what moved; you keep the one record honest.", "both", "agent", "Your agent",
          "What changed in the sprint this week?", "It lists the rows that moved and asks what to record.")),
        ("Close out and report", "What was delivered, what carries over, and the status report, drafted for you to confirm.", "both", "agent", "Your agent",
         "Let's close out the sprint.", "It %swalks the committed items, then drafts the report." % ("consolidates the board first, then " if board else "")),
        ("Keep the RAID honest", "Every open risk has an owner and a date to look again.", "both", "agent", "Your agent", "What risks need a look?",
         "It lists those past their review date."),
    ]
    if board:
        dev = [
            ("Find your tasks", "Open the team board and filter Owner to your name. Each row is a task, and names the backlog row it helps deliver.",
             "person", "person", "The team board", "Filter the Owner column to your name.", ""),
            ("Start from its folder", "Each backlog row has a folder in %s with its discovery, spec and plan. The agent drafts what is missing; once you approve the plan, it takes the steps it can." % ex,
             "both", "agent", "Your agent", "Open the folder for WBS 12 and draft the plan.", "It drafts it there for you to approve, and starts on its steps only once you have."),
            ("Move a task", "Set its status as the work moves, with a dated note on top. A backlog row can carry several tasks, each naming its WBS ID.",
             "agent", "agent", "Copilot in Excel", "Mark the task Login form as Doing, with a note on top dated today: started.",
             "It updates the row the way the board's How to update sheet says."),
            ("Finish it properly", "Done, with an AC verdict against the row's acceptance criteria. A partly met says what's left.", "agent", "agent",
             "Copilot in Excel", "Mark the task Login form as Done, AC verdict met, note: released to test.",
             "On Friday the agent proposes the close; the product manager confirms."),
            ("Say what's in the way", "Blocked, with what you're waiting for. New work goes in as a task with no WBS ID.", "agent", "agent",
             "Copilot in Excel", "Set the task Password reset to Blocked, note: waiting for the security policy.",
             "The agent offers it as a risk with an owner."),
        ]
        val = [
            ("Know what done means", "Each backlog row states how it is verified, from its spec. Challenge weak criteria before the plan is approved.", "both", "agent",
             "The product manager's agent", "Which rows this sprint have weak acceptance criteria?", "It lists rows with none, or vague ones."),
            ("Track your own tasks", "Your test and review work is on the board like anyone's.", "person", "person", "The team board",
             "Filter the Owner column to your name.", ""),
            ("Record verdicts", "On a Done task: met, partly met or not met, with a note on what's left.", "agent", "agent", "Copilot in Excel",
             "Set the AC verdict of Form test scripts to partly met, note: two edge cases left.", ""),
            ("Follow the verification", "The backlog dashboard's Verification tab shows each requirement and its verdict.", "person", "person",
             "The WBS dashboard", "Open the Verification tab.", ""),
            ("Speak to quality at the review", "Your read feeds the status report's On Quality rating.", "both", "agent", "The product manager's agent",
             "How does quality look this sprint?", "It drafts the evidence; the product manager confirms the rating."),
        ]
    else:
        dev = [
            ("See what's yours", "The sprint's work is in the backlog; the agent finds yours.", "agent", "agent", "Your agent", "What's in this sprint for me?", "It lists your rows and anything due."),
            ("Start a piece of work", "Say when you start. The work's folder in %s holds its discovery, spec and plan; the agent drafts what is missing, and takes the plan's steps it can once you approve it." % ex,
             "both", "agent", "Your agent", "I'm starting the login form.", "It moves the row to Implementing and asks which stop to start at."),
            ("Finish it properly", "Done means each acceptance criterion has a verdict.", "both", "agent", "Your agent", "The login form is done.", "It asks about each criterion, then proposes the close."),
            ("Say when something's unplanned", "Unplanned work is fine; its effect is said out loud.", "both", "agent", "Your agent", "I need to fix the login bug this sprint.", "It asks what it displaces."),
            ("Raise what's in the way", "A risk or an issue goes in the RAID with an owner.", "both", "agent", "Your agent", "We're blocked on the test environment.", "It asks who owns it and when to look again."),
        ]
        val = [
            ("Know what done means", "Each backlog row states how it is verified. Challenge weak criteria before work starts.", "both", "agent", "Your agent",
             "Which rows this sprint have weak acceptance criteria?", "It lists rows with none, or vague ones."),
            ("See what's verified", "The verification view shows each requirement and its verdict.", "agent", "agent", "Your agent", "Show me what's been verified.", "It summarises verdicts."),
            ("Follow a partial verdict", "A criterion partly met says where the rest went.", "agent", "agent", "Your agent", "Where did the rest of row 12 go?", "It follows the closure note."),
            ("Check the documents", "What the work must leave behind, and whether it has.", "agent", "agent", "Your agent", "Which deliverables still lack their documents?", "It checks the document rows."),
            ("Speak to quality at the review", "Your read feeds the status report's On Quality rating.", "both", "agent", "Your agent", "How does quality look this sprint?", "It drafts the evidence; a person confirms."),
        ]
    return {
        "Product manager": ("Owns the brief, the backlog and the ceremonies", "flow", pm),
        "Developer": ("Builds the product%s" % (", updates the board" if board else ""), "board", dev),
        "Validation and quality": ("Verifies the work meets its criteria", "check", val),
    }


# ─── Drawings ────────────────────────────────────────────────────────────────

def length(rec):
    """The sprint's length in words: 'two-week', or 'ten-day'."""
    days = (rec.get("cadence") or {}).get("days") or 14
    words = {7: "one-week", 14: "two-week", 21: "three-week", 28: "four-week"}
    return words.get(days, "%d-day" % days)


def ring(rec):
    """The sprint as a cycle: its length and its ceremonies, the same every sprint."""
    c = rec.get("cadence")
    if not c:
        return ""
    cer = rec["ceremonies"]
    weeks = c["days"] % 7 == 0
    seg = 314.16 / (c["days"] // 7 if weeks else 1)
    marks = [m for m, have in (("planned on its first day", cer.get("planning")), ("reviewed each Friday", cer.get("weekly")),
                               ("closed on its last", cer.get("closeout"))) if have]
    note = ", ".join(marks[:-1]) + " and " + marks[-1] if len(marks) > 1 else (marks[0] if marks else "")
    note = note[:1].upper() + note[1:]
    return ('<div class="ring"><svg viewBox="0 0 120 120" aria-hidden="true"><defs><linearGradient id="rg" x1="0" x2="1"><stop offset="0" stop-color="#8ea0ff"/><stop offset="1" stop-color="#c3b5ff"/></linearGradient></defs>'
            '<circle class="pr" cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round" stroke-dasharray="%.2f 6.5" transform="rotate(-90 60 60)"/>'
            '<text x="60" y="64" text-anchor="middle" class="rn">%d</text><text x="60" y="82" text-anchor="middle" class="rs">%s</text></svg>'
            '<div><b>Every sprint</b><small>%s</small></div></div>'
            % (seg - 6.5, c["days"] // 7 if weeks else c["days"], "weeks" if weeks else "days", e(note)))


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def rhythm_svg(rec):
    """The sprint's pattern, by weekday and day number: no dates, no 'today'."""
    c = rec.get("cadence")
    if not c:
        return '<p class="src">No sprint calendar found, so the rhythm cannot be drawn.</p>'
    wd0 = WEEKDAYS.index(c["starts"]) if c["starts"] in WEEKDAYS else 0
    days = [(i, (wd0 + i) % 7) for i in range(c["days"])]
    cer, board = rec["ceremonies"], rec["status_tool"] == "board"
    w, x0, y = 50, 10, 46
    work = [d for d in days if d[1] < 5]
    first, last = (work[0], work[-1]) if work else (days[0], days[-1])
    out = ['<svg viewBox="0 0 %d 170" role="img" aria-label="Every sprint: %d days from a %s, planning on its first working day, review and retro on its last%s.">'
           % (x0 * 2 + w * len(days), c["days"], c["starts"], ", a weekly review each Friday" if cer.get("weekly") else ""),
           '<text class="rh" x="10" y="22">Every sprint · %d days, starting on a %s</text>' % (c["days"], e(c["starts"]))]
    for d in days:
        i, wd = d
        x, cx, we = x0 + i * w, x0 + i * w + w / 2, wd >= 5
        out.append('<rect x="%d" y="%d" width="%d" height="82" rx="10" class="%s"/>' % (x + 3, y, w - 6, "rw" if we else "rd"))
        out.append('<text x="%d" y="%d" text-anchor="middle" class="rm">%s %d</text>' % (cx, y + 100, "MTWTFSS"[wd], i + 1))
        if we:
            continue
        out.append('<circle cx="%d" cy="%d" r="4" class="rp"/>' % (cx, y + 16))
        label = None
        if d == first and cer.get("planning"):
            label = "Plan"
        elif d == last and cer.get("closeout"):
            label = "Review"
        elif wd == 4 and cer.get("weekly"):
            label = "Weekly"
        if label:
            out.append('<rect x="%d" y="%d" width="16" height="16" rx="4" class="rk"/><text x="%d" y="%d" text-anchor="middle" class="rt">%s</text>'
                       % (cx - 8, y + 30, cx, y + 62, label))
            if board or label != "Plan":
                out.append('<path d="M%d,%d l4,6 l-4,6 l-4,-6 z" class="ra"/>' % (cx, y + 68))
    out.append("</svg>")
    legend = ['<span><i style="background:var(--person)"></i>%s</span>' % ("The team updates the board, every day" if board else "The work moves; the team tells the agent"),
              '<span><i style="background:var(--agent)"></i>%s</span>' % ("The agent sets up and consolidates the board" if board else "The agent prepares each ceremony"),
              '<span><i style="background:var(--accent)"></i>Ceremonies: planning%s, close-out and retro</span>' % (", the Friday review" if cer.get("weekly") else "")]
    return "".join(out) + '<div class="legend">%s</div>' % "".join(legend)


def system_svg(rec):
    """The records on the left, people and agents as one loop in the middle,
    what the reader receives on the right."""
    notes = {"Brief": "why it exists, how it's measured", "Backlog": "every piece of work, and when", "Team board": "the team's tasks, each sprint",
             "Risks and decisions": "what could go wrong, what was decided", "Sprint records": "what was committed and delivered"}
    regs = [r for r in ("Brief", "Backlog", "Team board", "Risks and decisions", "Sprint records") if r in rec["registers"]] or ["Backlog"]
    gap = 58
    hgt = max(280, 30 + len(regs) * gap)
    mid = hgt / 2.0
    zt = mid - 123                       # the zone's top
    ay, py = zt + 36, zt + 156           # the agents' and people's boxes
    parts = ['<svg viewBox="0 0 760 %d" role="img" aria-label="The records feed a loop where people and agents do the work, agents propose and people decide; what is confirmed goes into the status report and your shared copy.">' % hgt,
             '<defs>%s</defs>' % "".join('<marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="%s" d="M0,0 L10,5 L0,10 z"/></marker>' % (m, c)
                                          for m, c in (("ah", "ah"), ("aha", "ahA"), ("ahp", "ahP")))]
    top = mid - (len(regs) * gap - 12) / 2.0
    for i, r in enumerate(regs):
        y = top + i * gap
        parts.append('<rect class="rg" x="10" y="%d" width="220" height="46" rx="10"/><text class="rh" x="26" y="%d">%s</text><text class="rm" x="26" y="%d">%s</text>'
                     % (y, y + 20, e(r), y + 36, e(notes[r])))
        target = ay + 31 if y + 23 < mid else py + 31
        parts.append('<path class="ln" d="M230,%d C252,%d 252,%d 274,%d" marker-end="url(#ah)"/>' % (y + 23, y + 23, target, target))
    parts.append('<rect class="zone" x="262" y="%d" width="262" height="246" rx="18"/><text class="rz" x="393" y="%d" text-anchor="middle">WORKING TOGETHER</text>' % (zt, zt + 22))
    parts.append('<rect class="ag" x="276" y="%d" width="234" height="62" rx="12"/><text class="rh" x="292" y="%d">Agents</text><text class="rm" x="292" y="%d">do the work · keep records · propose</text>' % (ay, ay + 24, ay + 42))
    parts.append('<rect class="pp" x="276" y="%d" width="234" height="62" rx="12"/><text class="rh" x="292" y="%d">People</text><text class="rm" x="292" y="%d">do the work · decide · own the outcome</text>' % (py, py + 24, py + 42))
    parts.append('<path class="la" d="M458,%d C474,%d 474,%d 458,%d" marker-end="url(#aha)"/><text class="rla" x="478" y="%d">proposes</text>' % (ay + 62, ay + 80, py - 20, py - 2, mid + 4))
    parts.append('<path class="lp" d="M328,%d C312,%d 312,%d 328,%d" marker-end="url(#ahp)"/><text class="rlp" x="338" y="%d">decides,</text><text class="rlp" x="338" y="%d">corrects</text>' % (py, py - 18, ay + 80, ay + 64, mid - 2, mid + 11))
    for y, title, note in ((mid - 76, "Status report", "drafted by agents, rated by people"), (mid + 16, "Your copy", "only what someone chose to share")):
        parts.append('<rect class="op" x="556" y="%d" width="196" height="52" rx="12"/><text class="rh" x="572" y="%d">%s</text><text class="rm" x="572" y="%d">%s</text>' % (y, y + 22, title, y + 38, note))
        parts.append('<path class="ln" d="M524,%d C542,%d 538,%d 554,%d" marker-end="url(#ah)"/>' % (mid + (-12 if y < mid else 18), mid + (-12 if y < mid else 18), y + 26, y + 26))
    parts.append("</svg>")
    return "".join(parts)


STAGES = [
    # (title, body, [(kind, team label, outside label)], document, a gate)
    ("Committed", "Planning puts the backlog row in the sprint. It gets a folder of its own, named for the row, and everything about the work goes there.",
     [("person", "You commit", "A person commits"), ("agent", "Agent opens the folder", "An agent opens the folder")], "/", False),
    ("Discover", "The current state, the problem, the evidence, and the options where there are several. The agent researches; you correct what it got wrong.",
     [("agent", "Agent researches", "An agent researches"), ("person", "You review", "A person reviews")], " - Discovery.md", False),
    ("Specify", "What will be built, and the acceptance criteria that will say it is done. The criteria go onto the backlog row.",
     [("agent", "Agent drafts", "An agent drafts"), ("person", "You review", "A person reviews")], " - Specification.md", False),
    ("Plan and approve", "The steps, in order, sized. Nothing is built until the plan is approved.",
     [("agent", "Agent drafts", "An agent drafts"), ("person", "You approve", "A person approves")], " - Plan.md", True),
    ("Do", "The agent carries out the steps it can, following the approved plan; you do the rest and review what it produced. Each step is noted as it happens.",
     [("agent", "Agent does its steps", "Agents do their steps"), ("person", "You do yours, and review", "People do theirs, and review")], " - Notes.md", False),
    ("Verify and close", "Each criterion gets a verdict, and the row closes with a note on what was delivered. What was handed over is kept as sent.",
     [("agent", "Agent checks, drafts the close", "An agent checks"), ("person", "You confirm", "A person confirms")], "deliverables", False),
]


def work_loop(rec, exec_=False):
    """How a piece of work gets done: six stops, each drafted by an agent and
    reviewed or approved by a person, leaving its document in the work's folder."""
    ex = rec.get("execution") or {}
    item, short = "WP.12 Login form", "WP12 Login form"
    cards = []
    for i, (title, body, acts, doc, gate) in enumerate(STAGES):
        chips = "".join(who(k, outside if exec_ else team) for k, team, outside in acts)
        path = ""
        if not exec_:
            path = (item + "/" if doc == "/" else ("%s/%s/" % (item, ex.get("deliverables") or "Deliverables") if doc == "deliverables" else short + doc))
            path = '<code class="doc">%s</code>' % e(path)
        cards.append('<li class="stage%s" data-search="%s"><span class="n">%02d</span><h3>%s</h3><div class="acts">%s</div><p>%s</p>%s</li>'
                     % (" gate" if gate else "", e(title.lower()), i + 1, e(title), chips, e(body if not exec_ else body.replace("you correct", "a person corrects").replace("; you do the rest", "; people do the rest")), path))
    note = ('<div class="loopnote">%s<p><b>Back a stop when the work shows the spec or the plan was wrong:</b> the agent revises, %s approve%s again. '
            'A small fix goes straight from committed to done; the bigger or less certain the work, the more stops it makes.</p></div>'
            % (icon("loop"), "a person" if exec_ else "you", "s" if exec_ else ""))
    return '<ol class="loop">%s</ol>%s' % ("".join(cards), note)


def work_tree(rec):
    ex = rec.get("execution") or {}
    rows = [("WP12 Login form - Discovery.md", "what was found"), ("WP12 Login form - Specification.md", "what will be built, and its criteria"),
            ("WP12 Login form - Plan.md", "the steps, approved before work starts"), ("WP12 Login form - Notes.md", "decisions as they happened, dated"),
            ((ex.get("inputs") or "Inputs") + "/", "what came from outside, kept as received"), ((ex.get("deliverables") or "Deliverables") + "/", "what was handed over, frozen as sent")]
    src = ("Declared in the backlog register" if ex.get("declared") else ("The project's own folder" if ex.get("found") else "The standard layout; the folder is created with the first piece of work"))
    return ('<div class="panel tree" data-search="execution folder spec plan discovery"><ul><li>%s<span>one folder per backlog row, named by its ID</span><ul><li>WP.12 Login form/<span>an example</span><ul>%s</ul></li></ul></li></ul></div><p class="src">%s.</p>'
            % (e(ex.get("folder") or "1. Execution"), "".join("<li>%s<span>%s</span></li>" % (e(n), e(a)) for n, a in rows), src))


# ─── The page frame ──────────────────────────────────────────────────────────

def font_faces():
    out = []
    for fam, f, wght in (("Bricolage Grotesque", "BricolageGrotesque-latin.woff2", "200 800"), ("Geist", "Geist-latin.woff2", "100 900"),
                         ("Geist Mono", "GeistMono-latin.woff2", "100 900")):
        path = os.path.join(FONTS, f)
        if os.path.exists(path):
            data = base64.b64encode(io.open(path, "rb").read()).decode("ascii")
            out.append("@font-face { font-family:'%s'; font-style:normal; font-weight:%s; font-display:swap; src:url(data:font/woff2;base64,%s) format('woff2'); }"
                       % (fam, wght, data))
    return "\n".join(out)


CSS = io.open(os.path.join(HERE, "guide.css"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "guide.css")) else ""


def frame(rec, title, sub, mark, body, paths_json="{}", top_extra=""):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, viewport-fit=cover\">\n"
            "<meta name=\"generator\" content=\"onboarding-guide\">\n<title>%s</title>\n<style>\n%s\n%s\n</style>\n</head>\n<body>\n%s\n"
            '<div class="top"><div class="wrap"><div class="mark"><i>%s</i><div><b>%s</b><span>%s</span></div></div>%s'
            '<div class="search">%s<input id="q" type="search" placeholder="Search the guide" aria-label="Search the guide" autocomplete="off"><div class="results" id="results" hidden></div></div></div></div>\n'
            '<div class="wrap"><div class="layout"><nav class="map" aria-label="Guide map"><ol id="map"></ol></nav><main>%s'
            '<footer>Generated from the project\'s own files on %s; never edited by hand.</footer></main></div></div>\n<script>%s</script>\n</body></html>\n'
            % (e(title), font_faces(), CSS, SPRITE, e(mark[:1].upper()), e(rec["scope"]), sub, top_extra, icon("search"), body, e(rec["as_of"]),
               JS.replace("__PATHS__", paths_json)))


JS = io.open(os.path.join(HERE, "guide.js"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "guide.js")) else ""


def section(sid, title, group, body, eyebrow="", heading="", lede=""):
    head = ""
    if heading:
        head = "<header>%s<h2>%s</h2>%s</header>" % ('<span class="eyebrow">%s</span>' % e(eyebrow) if eyebrow else "", e(heading),
                                                    "<p>%s</p>" % e(lede) if lede else "")
    return '<section class="part" id="%s" data-title="%s" data-group="%s">%s%s</section>' % (sid, e(title), e(group), head, body)


def headline(rec):
    """The brief's executive statement as a sentence, its 'so that' half set off."""
    st = (rec.get("brief") or {}).get("statement") or ""
    for sep in (" so that ", " para que "):
        if sep in st:
            a, b = st.split(sep, 1)
            if a.lower().startswith("to "):
                a = "We " + a[3:]
            elif a.lower().startswith("para "):
                a = a[5:].capitalize()
            return "%s <em>so that %s</em>" % (e(a), e(b.rstrip(".") + ".")) if sep == " so that " else "%s <em>para que %s</em>" % (e(a), e(b))
    return None


def duo(rec, exec_=False):
    board = rec["status_tool"] == "board"
    if exec_:
        a = ["Work alongside the team: drafts, analysis, code", "Keep the backlog, risks and decisions current", "Draft every report from the same records"]
        p = ["Confirm every change before it is recorded", "Confirm every rating before it is shared", "Own the outcome, the priorities and the trade-offs"]
        u = ("For you", "Faster, and traceable", ["Status the same day, not the next meeting", "Every figure traceable to its source", "A decision reaches you with its options"])
    else:
        a = ["Work with you: drafts, analysis, code and tests, for you to review",
             ("Bring the team board into the backlog, row by row, as proposals" if board else "Keep the backlog current as the team reports what moved"),
             "Draft closure notes, status reports and each ceremony's record",
             "Answer “what's in the sprint?” and “what's at risk?” at any time"]
        p = [("Do the work with the agents, and update their own tasks, or ask Copilot in Excel to" if board else "Do the work with the agents, and tell them what moved"),
             "Confirm every change before it reaches the backlog", "Judge: is it done, is it at risk, what comes next", "Own the outcome, and say so when it changes"]
        u = ("What it unlocks", "Less admin, more signal", ["Records that are current without anyone chasing", "Reports in minutes, each traceable to its source",
                                                            "Anyone can ask the system, not wait for a meeting", "A newcomer is productive in their first week"])
    li = lambda xs: "<ul>%s</ul>" % "".join("<li>%s</li>" % e(x) for x in xs)
    return ('<div class="duo"><div class="card agentcard" data-search="agents">%s<h3>%s</h3>%s</div>'
            '<div class="card personcard" data-search="people decide">%s<h3>%s</h3>%s</div>'
            '<div class="card unlock" data-search="unlocks"><span class="eyebrow">%s</span><h3>%s</h3>%s</div></div>'
            % (who("agent", "Agents"), "Work, keep and prepare" if exec_ else "Work with you, keep the records, propose", li(a),
               who("person", "People"), "Decide and confirm" if exec_ else "Work, decide, own the outcome", li(p), e(u[0]), e(u[1]), li(u[2])))


def week_flow(rec):
    board = rec["status_tool"] == "board"
    steps = [("p", "board" if board else "person", "The team updates the board" if board else "The team says what moved",
              "Status and a dated note, by hand or through Copilot in Excel" if board else "In a sentence, to the agent"),
             ("a", "spark", "The agent reads it", "Rolls each backlog row's tasks up into proposals" if board else "Turns it into proposed changes"),
             ("p", "person", "The product manager confirms", "Each change, in one batch%s" % (", on Friday" if rec["ceremonies"].get("weekly") else "")),
             ("a", "flow", "The agent writes it", "Backlog, risks and notes, each with its reason"),
             ("a", "chart", "Reports follow", "Generated from the same records, never retyped")]
    return '<div class="flow" data-search="week flow consolidation"><ol>%s</ol></div>' % "".join(
        '<li class="%s"><div class="dot">%s</div><b>%s</b><span>%s</span></li>' % (k, icon(i), e(t), e(s)) for k, i, t, s in steps)


# ─── The team guide ──────────────────────────────────────────────────────────

def render_team(rec, exec_name=None):
    board = rec["status_tool"] == "board"
    out = []
    h = headline(rec)
    hero = ('<div class="hero"><div><span class="kicker">Welcome to %s</span><h1>%s</h1>'
            '<p class="lede">This guide shows why the project exists, what it runs on, and how a week works here, for your role. People and agents do the work together; agents keep the records and prepare, people decide and own the outcome.</p>'
            '<div class="thesis"><span><i class="tg"></i>You and the agents do the work</span><span><i class="tp"></i>You decide</span><span><i class="ta"></i>Agents keep the records</span></div></div>%s</div>'
            % (e(rec["scope"]), h or "Welcome to %s. <em>Here's how we work.</em>" % e(rec["scope"]), ring(rec)))
    doors = ('<div class="doors"><a class="door" href="#why"><span class="k">Why <span>2 min</span></span><b>Why this project exists, and what done looks like</b></a>'
             '<a class="door" href="#agents"><span class="k">What <span>5 min</span></span><b>How we work with agents, the tools, who’s who</b></a>'
             '<a class="door" href="#first-week"><span class="k">How <span>5 min</span></span><b>Your first week, step by step, for your role</b></a></div>')
    out.append(section("welcome", "Welcome", "Start", hero + doors))

    b = rec.get("brief")
    if b:
        ul = lambda xs: '<ul class="points">%s</ul>' % "".join("<li>%s</li>" % e(x.rstrip(".")) for x in xs)
        done = b.get("done_when") or []
        cards = [("check", "Done when", ul(done[:5]) if done else "<p>Not written yet: ask the product manager.</p>", "Brief · Outcome and done-when")]
        if b.get("measures"):
            cards.append(("chart", "How we'll know", ul(b["measures"][:4]) + "<p>The status report scores these each sprint.</p>", "Brief · Measures"))
        if b.get("stop_if"):
            cards.append(("shield", "We stop if", "<p>%s</p><p>The one condition that would make finishing not worth it.</p>" % e(b["stop_if"][:1].upper() + b["stop_if"][1:]), "Brief · Stop if"))
        body = '<div class="grid">%s</div>' % "".join(
            '<div class="card" data-search="%s %s"><div class="cardhead"><div class="ico">%s</div><h3>%s</h3></div>%s<p class="src">%s</p></div>'
            % (e(t), e(s), icon(i), e(t), h, e(s)) for i, t, h, s in cards)
        heading, lede = b.get("outcome") or "Why this project exists", "Everything the team does traces back to this outcome. If a task doesn't move it, ask why it's in the sprint."
    else:
        body = ('<div class="card" data-search="brief why"><div class="cardhead"><div class="ico">%s</div><h3>No brief yet</h3></div>'
                '<p>Why the project exists and what done looks like are not written down yet. Ask the product manager; the brief is where they will be.</p></div>' % icon("doc"))
        heading, lede = "Why this project exists", ""
    out.append(section("why", "Why we're doing this", "Why", body, "Why", heading, lede))

    out.append(section("agents", "You and the agents", "What", duo(rec) + week_flow(rec), "What · 1 of 4",
                       "An AI-first team: people and agents do the work, people make the calls",
                       "Agents work alongside you, and every record here is kept by an agent and confirmed by a person. That's what lets a small team stay current without status meetings or spreadsheets nobody trusts."))

    team_tools = ["status-board-manager" if board else "wbs-manager", "project-definition-manager", "raid-manager", "reporting"]
    cards, rows = [], []
    for t in rec["tools"]:
        info = TOOLS.get(t["skill"])
        if not info:
            continue
        if t["skill"] in team_tools:
            kind, to, phrase = ASK.get(t["skill"], ("agent", "Your agent", ""))
            cards.append((team_tools.index(t["skill"]),
                          '<div class="card" data-search="%s"><div class="cardhead"><div class="ico">%s</div><h3>%s</h3></div>'
                          '<dl class="facts"><dt>Where</dt><dd><code>%s</code></dd><dt>Changes it</dt><dd>%s</dd></dl>'
                          '<div class="say"><div class="row">%s%s</div><q>%s</q></div></div>'
                          % (e(t["skill"]), icon(info[0]), e(info[1]), e(t.get("where") or "-"), e(info[2][:1].upper() + info[2][1:]),
                             who(kind, to), " say this" if kind == "agent" else " tell", e(phrase))))
        else:
            rows.append('<li data-search="%s">%s<span>%s</span></li>' % (e(t["skill"]), e(info[1]), e(t.get("where") or "")))
    cards.sort()
    pm_panel = ('<div class="panel" data-search="product manager tools"><h3>Run by the product manager, with the agents</h3><p>You won\'t need these to start; they keep the project\'s records.</p><ul class="list">%s</ul></div>'
                % "".join(rows)) if rows else ""
    out.append(section("toolkit", "The toolkit", "What", '<div class="grid two">%s</div>%s' % ("".join(c for _, c in cards), pm_panel),
                       "What · 2 of 4", "The %d tools you'll use" % len(cards),
                       "You rarely open these files yourself. The agents keep them; you update your tasks and ask questions."))

    tree = "".join("<li>%s<span>%s</span></li>" % (e(f["name"]), e(f.get("about") or "")) for f in rec["folders"])
    out.append(section("where", "Where things are", "What", '<div class="panel tree" data-search="folder"><ul><li>%s<span>planning and tracking</span><ul>%s</ul></li></ul></div><p class="src">%s</p>'
                       % (e(rec["folder_name"]), tree, "From the artifact register" if rec.get("folders_from") == "artifact-register" else "From the planning folder"),
                       "What · 3 of 4", "Everything about running the project lives in one folder"))

    groups = (rec.get("people") or {}).get("groups") or []
    if groups:
        body = '<div class="grid">%s</div><p class="src">From the stakeholder register. Names appear only in this team copy.</p>' % "".join(
            '<div class="card" data-search="who %s"><h3>%s</h3><p>%s</p></div>' % (e(g["name"]), e(g["name"]),
            e(" · ".join("%s, %s" % (m["name"], m["role"].lower()) if m.get("name") else m["role"] for m in g["members"]))) for g in groups)
        heading = "Who's who"
    else:
        body = ('<div class="card" data-search="who product manager"><div class="cardhead"><div class="ico">%s</div><h3>Ask the product manager%s</h3></div>'
                '<p>The project keeps no stakeholder register yet, so who’s who is not written down here. The product manager runs the ceremonies and keeps the backlog, with the agents.</p></div>'
                % (icon("person"), ", " + e(rec["pm"]) if rec.get("pm") else ""))
        heading = "Who's who"
    out.append(section("who", "Who's who", "What", body, "What · 4 of 4", heading))

    now = rec.get("now") or []
    current = ('<div class="card" data-search="this sprint now current goals"><div class="cardhead"><div class="ico">%s</div><h3>What this sprint is about</h3></div>'
               '<p>This guide changes only when the project’s tools, brief or team do, so it never shows the sprint running now. For that, open %s, or ask your agent: <q>What is this sprint about?</q></p></div>'
               % (icon("cal"), e(", ".join(now[:-1]) + " or " + now[-1] if len(now) > 1 else (now[0] if now else "the backlog"))))
    out.append(section("rhythm", "The rhythm", "How", '<div class="figure" data-search="rhythm sprint ceremonies">%s</div>%s' % (rhythm_svg(rec), current),
                       "How · 1 of 3", "%s sprints, the same shape every time" % length(rec).capitalize(), "Who acts at each moment is marked: people in amber, agents in indigo."))

    out.append(section("work", "How work gets done", "How", work_loop(rec) + work_tree(rec), "How · 2 of 3",
                       "From committed to done: researched, specified and planned, then built",
                       "Every piece of work the sprint commits to gets a folder of its own. Agents draft what it needs at each stop and do the steps they can; you review, and nothing is built before you approve the plan."))

    ps = paths(rec)
    out.append(section("first-week", "Your first week", "How",
                       '<div class="roles" id="roles" role="group" aria-label="Your role"></div><div class="path"><ol class="steps" id="steps"></ol>'
                       '<div class="stepbody" aria-live="polite"><div class="progress"><span id="progress"></span><span id="pct"></span></div><div class="bar"><i id="bar"></i></div>'
                       '<div class="actors" id="actors"></div><h3 id="stitle"></h3><p id="sbody"></p>'
                       '<div class="say"><div class="row" id="sto"></div><q id="ssay"></q><span class="sask" id="sask"></span></div>'
                       '<div class="stepnav"><button class="btn" type="button" id="prev">Back</button><button class="btn primary" type="button" id="nextstep">Next step</button></div></div></div>',
                       "How · 3 of 3", "Your first week, for your role", "Five stops, in the order you'll meet them. Each says who acts: you, or an agent with you."))

    gl = "".join("<div><b>%s</b><span>%s</span></div>" % (e(w), e(d)) for w, d in GLOSSARY if board or w not in ("Team board", "Consolidation"))
    ask = ('<div class="card" data-search="help ask"><h3>Stuck? Ask the product manager%s</h3><p>Or ask your agent first: it can explain any tool in this guide, and walk you through your first week. Say “onboard me”.</p></div>'
           % (", " + e(rec["pm"]) if rec.get("pm") else ""))
    out.append(section("glossary", "Glossary", "Help", '<div class="gloss" data-search="glossary">%s</div>%s' % (gl, ask), "Help", "Words you'll hear"))

    extra = ('<a class="toplink" href="%s">Executive overview →</a>' % e(exec_name)) if exec_name else ""
    data = {k: [v[0], v[1], [list(s) for s in v[2]]] for k, v in ps.items()}
    return frame(rec, "%s guide" % rec["scope"], "Guide for the product team", rec["scope"], "".join(out), json.dumps(data, ensure_ascii=False), extra)


# ─── The executive overview ──────────────────────────────────────────────────

def render_exec(rec):
    out = []
    h = headline(rec)
    hero = ('<div class="hero"><div><span class="kicker">How the %s team works</span><h1>A small team, <em>run AI‑first</em>, with people accountable for every call.</h1>'
            '<p class="lede">%s People and agents do the work together, in %s sprints; agents keep one record of it and prepare every report from it; people confirm each change and each rating.</p>'
            '<div class="thesis"><span><i class="ta"></i>Agents keep the records</span><span><i class="tp"></i>People decide</span><span><i class="tg"></i>You see what the team sees</span></div></div>%s</div>'
            % (e(rec["scope"]), (h.replace("<em>", "").replace("</em>", "") if h else e(rec["scope"]) + " is run on a small set of tools and a fixed rhythm."), length(rec), ring(rec)))
    doors = ('<div class="doors"><a class="door" href="#ai-first"><span class="k">AI-first <span>2 min</span></span><b>What agents do, and what people keep</b></a>'
             '<a class="door" href="#principles"><span class="k">Principles <span>2 min</span></span><b>Six rules the team holds itself to</b></a>'
             '<a class="door" href="#operates"><span class="k">Operating model <span>2 min</span></span><b>The rhythm, and what you’ll receive</b></a></div>')
    out.append(section("overview", "In one screen", "Start", hero + doors))
    out.append(section("ai-first", "An AI-first team", "Why", duo(rec, exec_=True), "AI-first", "Agents work alongside the team. People stay accountable.",
                       "Agents take part in the work itself, and take on the overhead of keeping records current and turning them into reports. People make the calls, and answer for them."))
    pc = "".join('<div class="card principle" data-search="%s"><span class="pnum">%02d</span><h3>%s</h3><p>%s</p><div class="means"><b>For you</b>%s</div></div>'
                 % (e(t), i + 1, e(t), e(p), e(f)) for i, (t, p, f) in enumerate(PRINCIPLES))
    out.append(section("principles", "The principles", "Why", '<div class="grid">%s</div>' % pc, "Principles", "Six rules the team holds itself to"))
    rows = rec.get("comms") or []
    if rows:
        trs = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(c["what"]), e(c["cadence"]), e(c["audience"])) for c in rows)
        src = "From the communications plan, at the external level."
    else:
        trs = ("<tr><td>Status report: delivery, outcome, risks</td><td>Every sprint, at its close-out</td><td>The sponsor, and anyone the product manager names</td></tr>"
               "<tr><td>Sprint review</td><td>Every sprint, its last day</td><td>Anyone invited</td></tr>"
               "<tr><td>A decision that needs you</td><td>When it arises</td><td>Whoever owns it</td></tr>")
        src = "The default until the project keeps a communications plan; the product manager sets who receives what."
    out.append(section("operates", "How the team operates", "How", '<div class="figure">%s</div><div class="table"><table><thead><tr><th>What</th><th>How often</th><th>For</th></tr></thead><tbody>%s</tbody></table></div><p class="src">%s</p>'
                       % (rhythm_svg(rec), trs, src), "Operating model", "The rhythm, and what you'll receive"))
    out.append(section("work", "How work gets done", "How", work_loop(rec, exec_=True), "How work gets done",
                       "Researched, specified and planned before it is built",
                       "An agent drafts each stop and carries out the steps it can; a person reviews each one and approves the plan before anything is built. Every piece of work keeps its own trail, so how a result was reached can always be shown."))
    out.append(section("system", "The system at a glance", "What", '<div class="figure sys">%s</div>' % system_svg(rec), "System",
                       "Records on the left, people and agents working them in the middle, what you read on the right",
                       "Nothing reaches a record, or you, without both: the agent prepares it, a person decides it."))
    return frame(rec, "%s: how the team works" % rec["scope"], "Executive overview", rec["scope"], "".join(out))
