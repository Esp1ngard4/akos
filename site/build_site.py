#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the AKOS site into docs/, for GitHub Pages.

    python site/build_site.py           # build and write docs/
    python site/build_site.py --check   # exit 1 if docs/ is behind the sources (CI)

What it writes, and from what:

    docs/index.html           the front page: the README's opening
    docs/tools/index.html     every tool, by what the agent does with it (the README's table)
    docs/tools/<tool>.html    one page per tool, from its TD
    docs/first-hour.html      your first hour on Atlas: what you say, what the agent does
    docs/atlas/               Atlas's guides, from TSP.16 Onboarding

Atlas is a made-up project. The first hour is not a description of setting it
up: it is the list of steps this script runs to set it up, so every command on
that page has run before the page was written. The pages use TSP.16's look,
and the as-of date is fixed, so the same sources give the same site.

Rebuild after changing a TD, the README's opening or tools table, TSP.16, or
anything Atlas is built with.
"""
import argparse
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSP = os.path.join(ROOT, "TSP")
FIXTURES = os.path.join(ROOT, "site", "atlas")
DOCS = os.path.join(ROOT, "docs")
AS_OF = date(2026, 10, 28)
REPO = "https://github.com/Esp1ngard4/akos"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

sys.path.insert(0, os.path.join(TSP, "TSP.16 Onboarding", "onboarding-guide", "scripts"))
import onboard as O                                             # noqa: E402
G = O.G


def e(text):
    return html.escape("" if text is None else str(text))


# ─── Atlas, and the first hour that sets it up ───────────────────────────────

PACK = json.load(io.open(os.path.join(ROOT, "packs", "project.json"), encoding="utf-8"))
INIT = ["init", "Atlas", "--pack", "project", "--name", "Atlas", "--first-day", "2026-07-06"]
WBS, RAID, STK = "0. PrjMgm/01. WBS/WBS Atlas.json", "0. PrjMgm/02. RAID/RAID Atlas.json", "0. PrjMgm/04. Comms/Stakeholders Atlas.json"

# Each step: what you say, what the agent does, what you get, and the commands
# that run, from the Atlas folder: (skill, script, args). The first step is the
# installer's, run by a person; the rest run through the skills it installed.
FIRST_HOUR = [
    {"title": "Start the project",
     "run_by": "you",
     "agent": "Run the installer once, with the project pack. It installs the pack's %d tools and sets the project up the way the conventions say: "
              "the planning folder with its numbered folders, each register created empty by its own tool, a sprint calendar, the brief's template, "
              "and a first onboarding guide. Starting a project is a person's decision, so no agent does it." % len(PACK["skills"]),
     "get": "A project an agent can work in from the first message. Commit it.",
     "run": [("install", "install.py", INIT)]},
    {"title": "Write the brief",
     "say": "Let's write the project brief for Atlas.",
     "agent": "Asks you why the project exists, what done looks like and what would make you stop, and writes each part into the brief for you to confirm.",
     "get": "The statement the whole team reads first.",
     "link": ("Atlas's brief", REPO + "/blob/main/site/atlas/Project%20Brief.md"),
     "fixture": ("Project Brief.md", "0. PrjMgm/07. Project Brief.md"),
     "run": [("project-definition-manager", "brief.py", ["check", "0. PrjMgm"])]},
    {"title": "Break the work down",
     "say": "Add the self-service sign-up as a key deliverable, with four features: the form, email verification, the identity check and the welcome.",
     "agent": "Adds each row under its parent with a stable ID, holding every field to the register's own vocabulary.",
     "get": "Five rows, ready for acceptance criteria and estimates at grooming.",
     "run": [("wbs-manager", "wbs.py", ["add", WBS, "Self-service sign-up", "--type", "Deliverable", "--key-deliverable", "Y"])]
            + [("wbs-manager", "wbs.py", ["add", WBS, t, "--type", "Feature", "--parent", "1"])
               for t in ("Sign-up form", "Email verification", "Identity check", "Welcome to the dashboard")]},
    {"title": "Log what could go wrong, and what was decided",
     "say": "Log a risk: the provider's identity check may not be in its sandbox by sprint two. Maya owns it. And record that we chose one responsive flow over a separate mobile one.",
     "agent": "Writes each entry in its type's own sentence (because of, there is a risk that, which may result in), with an owner, and refuses one with a slot missing.",
     "get": "A risk and a decision, each traceable.",
     "run": [("raid-manager", "raid.py", ["add", RAID, "Identity check in the sandbox", "--type", "Risk",
                                          "--because-of", "a provider release we do not control",
                                          "--risk-that", "the payments provider's identity check is not in its sandbox by sprint two",
                                          "--may-result-in", "the identity step slipping a sprint", "--dri", "Maya Torres"]),
             ("raid-manager", "raid.py", ["add", RAID, "One flow for web and mobile", "--type", "Decision",
                                          "--chose", "one responsive flow", "--over", "a separate mobile flow", "--because", "the same steps, half the testing"])]},
    {"title": "Say who's who",
     "say": "Set up who's who: the product team, and the steering group with Ruth as sponsor. Steering gets the status report every sprint.",
     "agent": "Adds the groups and the people, and a communications plan saying who receives what, and when.",
     "get": "Who's who in the guide, and what each audience receives. Contacts stay in a file beside it, out of git.",
     "run": [("stakeholder-manager", "stk.py", ["add-group", STK, "Product team", "--purpose", "Builds and verifies the product"]),
             ("stakeholder-manager", "stk.py", ["add-group", STK, "Steering", "--purpose", "Owns the outcome and the budget"])]
            + [("stakeholder-manager", "stk.py", ["add", STK, n, "--role", r, "--groups", g])
               for n, r, g in (("Maya Torres", "Product manager", "G.1"), ("Leo Brandt", "Developer", "G.1"), ("Sara Lind", "Developer", "G.1"),
                               ("Ines Okafor", "Validation and quality", "G.1"), ("Ruth Calder", "Sponsor", "G.2"), ("Tom Reyes", "Head of support", "G.2"))]
            + [("stakeholder-manager", "stk.py", ["add-comm", STK, "Status report", "--mode", "push", "--audience", "G.2", "--cadence", "per sprint", "--channel", "email"]),
               ("stakeholder-manager", "stk.py", ["add-comm", STK, "Sprint review", "--mode", "push", "--audience", "G.1,G.2", "--cadence", "per sprint", "--channel", "meeting"])]},
    {"title": "Bring the team in",
     "say": "Regenerate the onboarding guide.",
     "agent": "Reads the brief, the registers and the tools installed, and writes the team guide and the executive overview from them. Nothing in either is typed by hand.",
     "get": "Two pages to share: one for the team, one for everyone else.",
     "link": ("Atlas's team guide", "atlas/"),
     "run": [("onboarding-guide", "onboard.py", ["guide", "0. PrjMgm", "--as-of", AS_OF.isoformat()])]},
]
NEXT = ("Let's run sprint planning.", "Capacity first, then the sprint's goals, then the work: the agent proposes, you decide, and it writes the record. "
        "From then on, the rhythm in Atlas's guide takes over.")


def build_atlas(where):
    """Set Atlas up under `where` by running the first hour; return its planning folder."""
    atlas = os.path.join(where, "Atlas")
    skills = os.path.join(atlas, PACK.get("dest", ".agents/skills").replace("/", os.sep))
    for step in FIRST_HOUR:
        if step.get("fixture"):
            # The conversation writes the brief; here, Atlas's finished brief stands in for it.
            shutil.copy(os.path.join(FIXTURES, step["fixture"][0]), os.path.join(atlas, step["fixture"][1]))
        for skill, name, args in step["run"]:
            if skill == "install":
                cmd = [os.path.join(ROOT, "install.py")] + args + ["--source", REPO + ".git"]
                cwd = where
            else:
                cmd, cwd = [os.path.join(skills, skill, "scripts", name)] + args, atlas
            p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=cwd)
            if p.returncode != 0:
                sys.exit("First hour, %s: %s failed\n%s" % (step["title"], name, (p.stdout + p.stderr)[-1500:]))
    return os.path.join(atlas, PACK["planning"])


# ─── Reading the sources ─────────────────────────────────────────────────────

def readme():
    """The README's opening, its four areas and its tools table."""
    text = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    title = re.search(r"^# AKOS — (.+)$", text, re.M).group(1)
    opening = text.split("*Agentic Knowledge Operating System*", 1)[1].split("\n## ", 1)[0]
    intro = [" ".join(p.split()) for p in opening.strip().split("\n\n")]
    areas_text = text.split("## What the agent does on the team", 1)[1].split("\n## ", 1)[0]
    areas = [(m.group(1).rstrip("."), " ".join(m.group(2).split())) for m in re.finditer(r"\*\*(.+?)\*\*\s+(.+?)(?=\n\n|\Z)", areas_text.strip(), re.S)]
    people = " ".join(text.split("## What stays with people", 1)[1].split("\n## ", 1)[0].split())
    tools = []
    for m in re.finditer(r"^\| (TSP\.\d+) \| \[(.+?)\]\((.+?)\) \| (.+?) \| (.+?) \|$", text, re.M):
        tools.append({"id": m.group(1), "name": m.group(2), "does": m.group(4), "skills": re.findall(r"`([^`]+)`", m.group(5)), "skill_note": m.group(5)})
    return title, intro, areas, people, tools


def tool_folder(tid):
    return next(n for n in os.listdir(TSP) if n.startswith(tid + " "))


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def td(tid):
    folder = tool_folder(tid)
    path = next(os.path.join(TSP, folder, n) for n in os.listdir(os.path.join(TSP, folder)) if n.startswith("TD.") and n.endswith(".md"))
    text = io.open(path, encoding="utf-8").read()
    secs, cur = {}, None
    for line in text.split("\n"):
        if line.startswith("## "):
            cur = line[3:].strip()
            secs[cur] = []
        elif cur:
            secs[cur].append(line)
    return folder, os.path.basename(path), {k: "\n".join(v).strip() for k, v in secs.items()}


# ─── A small Markdown renderer, for the TDs' sections ───────────────────────

def linker(folder, depth, pages):
    """A TD's relative link: another tool's page where it points at a tool, else the file on GitHub."""
    def fix(url):
        if re.match(r"^[a-z]+:", url) or url.startswith("#"):
            return url
        path, _, anchor = url.partition("#")
        full = os.path.normpath(os.path.join("TSP", folder, unquote(path))).replace(os.sep, "/")
        m = re.match(r"^TSP/(TSP\.\d+) [^/]+(/TD\.[^/]+\.md)?/?$", full)
        if m and m.group(1) in pages:
            return "../" * depth + "tools/" + pages[m.group(1)]
        kind = "tree" if os.path.isdir(os.path.join(ROOT, full)) else "blob"
        return "%s/%s/main/%s%s" % (REPO, kind, quote(full), "#" + anchor if anchor else "")
    return fix


def inline(text, fix):
    codes = []
    text = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or "\x00%d\x00" % (len(codes) - 1), text)
    text = e(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: '<a href="%s">%s</a>' % (e(fix(html.unescape(m.group(2)))), m.group(1)), text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % e(codes[int(m.group(1))]), text)


def markdown(text, fix):
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>%s</code></pre>" % e("\n".join(lines[i + 1:j])))
            i = j + 1
        elif line.startswith("#"):
            out.append("<h4>%s</h4>" % inline(line.lstrip("#").strip(), fix))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s|:-]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[1:]
            th = "" if not any(head) else "<thead><tr>%s</tr></thead>" % "".join("<th>%s</th>" % inline(c, fix) for c in head)
            if not any(head):
                body = rows[1:]
            out.append('<div class="table"><table>%s<tbody>%s</tbody></table></div>'
                       % (th, "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c, fix) for c in r) for r in body)))
        elif re.match(r"^(\s*)([-*]|\d+\.) ", line):
            ordered = bool(re.match(r"^\s*\d+\. ", line))
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.) ", lines[i]) or (lines[i].startswith("  ") and items)):
                if re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(t, fix) for t in items), tag))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(\||#|```|\s*([-*]|\d+\.) )", lines[i]):
                para.append(lines[i].lstrip("> ").strip())
                i += 1
            out.append("<p>%s</p>" % inline(" ".join(para), fix))
    return "".join(out)


# ─── The pages ───────────────────────────────────────────────────────────────

GROUPS = [("Running the project", ["TSP.14", "TSP.1", "TSP.8", "TSP.15", "TSP.11", "TSP.10", "TSP.2", "TSP.13", "TSP.12", "TSP.16"]),
          ("Your own day", ["TSP.9", "TSP.7", "TSP.6"]),
          ("Keeping the system", ["TSP.3", "TSP.5", "TSP.4"])]

EXTRA_CSS = """<style>
.prose { display:flex; flex-direction:column; gap:12px; font-size:15.5px; color:var(--ink2); max-width:72ch; }
.prose h4 { font:600 16px var(--display); color:var(--ink); margin-top:8px; }
.prose ul, .prose ol { margin:0; padding-left:20px; display:flex; flex-direction:column; gap:6px; }
.prose code, .cmd code { font:500 13px var(--mono); background:var(--tint); padding:1px 6px; border-radius:6px; }
.prose a { color:var(--accent); }
.prose .table table { min-width:0; }
.cmd pre { margin:0; background:var(--tint); border-radius:12px; padding:12px 14px; overflow-x:auto; font:500 12.5px/1.6 var(--mono); color:var(--ink2); }
.toolcard { display:flex; flex-direction:column; gap:8px; text-decoration:none; color:inherit; }
.toolcard:hover { border-color:color-mix(in srgb, var(--accent) 40%, var(--line)); }
.toolcard .k { font:600 12px var(--mono); color:var(--muted); }
.toolcard p { font-size:14.5px; }
.toplink.cta { background:var(--accent); color:var(--bg); }
.toplink.cta:hover { color:var(--bg); filter:brightness(1.08); }
.start p { margin-top:12px; font-size:15px; color:var(--ink2); }
.actions { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.actions .btn { text-decoration:none; }
.chips { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
.chip { font:600 11.5px var(--body); letter-spacing:.04em; text-transform:uppercase; padding:4px 10px; border-radius:999px; background:var(--tint); color:var(--ink2); }
.hour { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:14px; counter-reset:hour; }
.hour > li { background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:18px 20px; box-shadow:var(--shadow); display:grid; grid-template-columns:44px minmax(0,1fr); gap:6px 14px; }
.hour .num { grid-row:span 6; width:36px; height:36px; border-radius:11px; display:grid; place-items:center; font:700 15px var(--display); background:var(--agentSoft); color:var(--agent); }
.hour h3 { font-size:17px; }
.hour .line { display:flex; gap:10px; align-items:flex-start; flex-wrap:wrap; font-size:14.5px; color:var(--ink2); }
.hour .line .who { flex:none; }
.hour .line > span:last-child { flex:1 1 260px; min-width:0; }
.hour details summary { cursor:pointer; font-size:13px; color:var(--muted); }
.hour details pre { margin-top:8px; }
@media (max-width:560px) { .hour > li { grid-template-columns:minmax(0,1fr); } .hour .num { grid-row:auto; } }
</style>"""


def nav(depth, here):
    up = "../" * depth
    links = [("index.html", "Home"), ("tools/index.html", "The tools"), ("atlas/", "Atlas")]
    return ("".join('<a class="toplink" href="%s%s"%s>%s</a>' % (up, h, ' aria-current="page"' if h == here else "", t) for h, t in links)
            + '<a class="toplink" href="%s">GitHub</a>' % REPO
            + '<a class="toplink cta" href="%sfirst-hour.html"%s>Start a project</a>' % (up, ' aria-current="page"' if here == "first-hour.html" else ""))


def start(depth):
    """Where every page ends up: the one command, and where to go from it."""
    up = "../" * depth
    cmd = ("git clone %s.git\npython akos/install.py init my-project --name \"My project\"" % REPO)
    return G.section("start", "Start yours", "Start",
                     '<div class="card cmd start"><pre>%s</pre><p>That is the whole setup: the pack\'s tools, the folders, the registers, the brief\'s template and a first guide. '
                     'Then open the project with your agent and say <q>Let\'s write the project brief.</q></p>'
                     '<div class="actions"><a class="btn primary" href="%sfirst-hour.html">Walk through the first hour</a>'
                     '<a class="btn" href="%s">AKOS on GitHub</a><a class="btn" href="%s#start">Already running a project?</a></div></div>'
                     % (e(cmd), up, REPO, REPO), "Start", "Start yours",
                     "A new project, set up the way the conventions say, in one command. A project already running adds the tools it needs one at a time.")


def page(title, sub, body, depth, here):
    rec = {"scope": "AKOS", "as_of": AS_OF.isoformat()}
    out = G.frame(rec, title, sub, "AKOS", EXTRA_CSS + body, "{}", nav(depth, here))
    return out.replace("Generated from the project's own files on", "Generated from the AKOS repository on")


def front(title, intro, areas, people):
    hero = ('<div class="hero"><div><span class="kicker">AKOS · Agentic Knowledge Operating System</span><h1>%s</h1>%s'
            '<div class="thesis"><span><i class="tg"></i>Agents do the work they can</span><span><i class="tp"></i>People decide</span>'
            '<span><i class="ta"></i>Everything on record</span></div></div></div>'
            % (e(title).replace("AI", "<em>AI</em>", 1), "".join('<p class="lede">%s</p>' % e(p) for p in intro)))
    doors = ('<div class="doors"><a class="door" href="atlas/"><span class="k">See it <span>5 min</span></span><b>Atlas, a made-up project run on AKOS: its team guide</b></a>'
             '<a class="door" href="first-hour.html"><span class="k">Try it <span>1 hour</span></span><b>Your first hour: what you say, and what the agent does</b></a>'
             '<a class="door" href="tools/index.html"><span class="k">The tools <span>16</span></span><b>Every tool, by what the agent does with it</b></a></div>')
    out = [G.section("welcome", "AKOS", "Start", hero + doors)]
    cards = "".join('<div class="card" data-search="%s"><h3>%s</h3><p>%s</p></div>' % (e(t), e(t), e(b)) for t, b in areas)
    out.append(G.section("agent", "What the agent does", "What", '<div class="grid two">%s</div>' % cards, "On the team", "What the agent does",
                         ""))
    out.append(G.section("people", "What stays with people", "What", '<div class="card personcard"><p>%s</p></div>' % e(people), "People", "What stays with people"))
    out.append(G.section("loop", "How work gets done", "How", G.work_loop({"execution": {}}, exec_=True), "How",
                         "How a piece of work gets done", "Researched, specified and planned before it is built: the agent drafts each stop, a person approves the plan."))
    out.append(start(0))
    return page("AKOS: AI as a member of the team", "AI as a member of the team", "".join(out), 0, "index.html")


def tools_index(tools, pages):
    by = {t["id"]: t for t in tools}
    out = []
    for g, ids in GROUPS:
        cards = "".join('<a class="card toolcard" href="%s" data-search="%s %s"><span class="k">%s</span><h3>%s</h3><p>%s</p></a>'
                        % (pages[i], e(by[i]["name"]), e(" ".join(by[i]["skills"])), e(i), e(by[i]["name"]), e(by[i]["does"])) for i in ids if i in by)
        out.append(G.section(slug(g), g, "Tools", '<div class="grid">%s</div>' % cards, "The tools", g))
    lede = ("Each tool is a folder: a design document saying what it is and why, and the skill an agent uses to operate it. "
            "Install the ones your team needs; each works on its own, and they work better together.")
    out[0] = out[0].replace("</header>", "<p>%s</p></header>" % e(lede), 1)
    return page("AKOS: the tools", "The tools", "".join(out), 1, "tools/index.html")


def tool_page(t, pages):
    folder, td_name, secs = td(t["id"])
    fix = linker(folder, 1, pages)
    status_key = next((k for k in secs if k.startswith("Status")), None)
    status = status_key.split(":", 1)[1].strip() if status_key and ":" in status_key else None
    chips = "".join('<span class="chip">%s</span>' % e(x) for x in (["Status: " + status] if status else []) + ["Skill: " + s for s in t["skills"]])
    does = t["does"]
    lede = ("The agent does nothing here:" + does.split(":", 1)[1] if does.startswith("Nothing:") else "The agent " + does[:1].lower() + does[1:]) + "."
    out = [G.section("about", t["name"], "Start", '<div class="chips">%s</div>' % chips, t["id"], t["name"], lede)]
    out.append(G.section("purpose", "What it's for", "Why", '<div class="prose">%s</div>' % markdown(secs.get("Purpose", ""), fix), "Why", "What it's for"))
    if status_key and secs.get(status_key):
        out.append(G.section("status", "Status", "Why", '<div class="prose">%s</div>' % markdown(secs[status_key], fix), "Status", status or "Status"))
    if secs.get("Adapting it to your tools"):
        out.append(G.section("adapting", "Adapting it", "How", '<div class="prose">%s</div>' % markdown(secs["Adapting it to your tools"], fix),
                             "How", "Adapting it to your tools"))
    out.append(G.section("works-with", "Works with", "How", '<div class="prose">%s</div>' % markdown(secs.get("Relationship to other tools", ""), fix),
                         "How", "Works with"))
    if t["skills"]:
        cmds = "\n".join("python akos/install.py add %s --into <your-repo>" % s for s in t["skills"])
    else:
        cmds = "python akos/install.py add %s --into <your-repo> --docs TSP   # no skill: its design document alone" % t["id"]
    links = ('<p class="src"><a href="%s/blob/main/%s">The full design document</a> · <a href="%s/tree/main/%s">The tool\'s folder</a></p>'
             % (REPO, quote("TSP/%s/%s" % (folder, td_name)), REPO, quote("TSP/" + folder)))
    out.append(G.section("install", "Install it", "How", '<div class="card cmd"><pre>git clone %s.git\n%s</pre></div>%s' % (REPO, e(cmds), links),
                         "Start", "Install it", "Into a project already running. A new project gets this tool with the rest of the pack, in one command: "
                         "see Start yours, below."))
    out.append(start(1))
    return page("AKOS: %s" % t["name"], t["id"] + " · " + t["name"], "".join(out), 1, "")


def first_hour():
    def show(arg):
        return '"%s"' % arg if (" " in arg or "'" in arg) else arg
    steps = []
    for s in FIRST_HOUR:
        cmds = "\n".join(("python akos/install.py " if sk == "install" else "python <skills>/%s/scripts/%s " % (sk, name)) + " ".join(show(a) for a in args)
                         for sk, name, args in s["run"])
        if s.get("fixture"):
            cmds = "# the agent edits %s with you, then checks it\n%s" % (s["fixture"][1], cmds)
        steps.append((s["title"], s.get("say"), s["agent"], s["get"], s.get("link"), cmds))
    items = []
    for n, (title, say, agent, get, link, cmds) in enumerate(steps, 1):
        lines = []
        if say:
            lines.append('<div class="line">%s<span><q>%s</q></span></div>' % (G.who("person", "You say"), e(say)))
        lines.append('<div class="line">%s<span>%s</span></div>' % (G.who("agent", "The agent") if say is not None else G.who("person", "You run"), e(agent)))
        lines.append('<div class="line"><span class="chip">You get</span><span>%s%s</span></div>'
                     % (e(get), (' <a href="%s">%s →</a>' % (e(link[1]), e(link[0]))) if link else ""))
        lines.append('<details class="cmd"><summary>What runs underneath</summary><pre>%s</pre></details>' % e(cmds))
        items.append('<li data-search="%s"><span class="num">%d</span><h3>%s</h3>%s</li>' % (e(title.lower()), n, e(title), "".join(lines)))
    items.append('<li data-search="next sprint planning"><span class="num">→</span><h3>Then</h3><div class="line">%s<span><q>%s</q></span></div>'
                 '<div class="line">%s<span>%s</span></div></li>' % (G.who("person", "You say"), e(NEXT[0]), G.who("agent", "The agent"), e(NEXT[1])))
    body = G.section("first-hour", "Your first hour", "Start", '<ol class="hour">%s</ol>' % "".join(items), "Try it", "Your first hour, on Atlas",
                     "Atlas is a made-up project. These are the steps that set it up, in the order a team would take them: what you say, what the agent does, "
                     "and what runs underneath. They are not illustrations: the site is built by running them.")
    return page("AKOS: your first hour", "Your first hour", body + start(0), 0, "first-hour.html")


def build():
    """{path under docs/: text} for the whole site."""
    title, intro, areas, people, tools = readme()
    pages = {t["id"]: slug(t["name"]) + ".html" for t in tools}
    site = {"index.html": front(title, intro, areas, people), "tools/index.html": tools_index(tools, pages), "first-hour.html": first_hour()}
    for t in tools:
        site["tools/" + pages[t["id"]]] = tool_page(t, pages)
    tmp = tempfile.mkdtemp(prefix="atlas-")
    try:
        rec = O.gather(build_atlas(tmp), AS_OF)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    back = ('<a class="toplink" href="../">AKOS</a><a class="toplink" href="%s">GitHub</a>'
            '<a class="toplink" href="../first-hour.html" style="background:var(--accent);color:var(--bg)">Start a project</a><div class="search">' % REPO)
    site["atlas/index.html"] = G.render_team(rec, "executive.html").replace('<div class="search">', back, 1)
    site["atlas/executive.html"] = G.render_exec(rec).replace('<div class="search">', back, 1)
    return site


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Build the AKOS site into docs/.")
    ap.add_argument("--check", action="store_true", help="exit 1 if docs/ differs from a fresh build")
    args = ap.parse_args()
    site = build()
    if args.check:
        stale = [p for p, text in sorted(site.items())
                 if not os.path.isfile(os.path.join(DOCS, p)) or io.open(os.path.join(DOCS, p), encoding="utf-8").read() != text]
        if stale:
            sys.exit("docs/ is behind its sources (%s). Run: python site/build_site.py" % ", ".join(stale))
        print("docs/ is current (%d pages)." % len(site))
        return 0
    for p, text in site.items():
        path = os.path.join(DOCS, p)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    io.open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print("docs/: %d pages written." % len(site))
    return 0


if __name__ == "__main__":
    sys.exit(main())
