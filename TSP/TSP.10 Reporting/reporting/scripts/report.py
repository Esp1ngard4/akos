#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate reports from the registers: a JSON record and an HTML view.

    python report.py status  "<project folder>" [--records <sprint records>] [--sprint S26.Q3.7] [--as-of YYYY-MM-DD]
    python report.py sprint  --sprint S26.Q3.7 --records <sprint records> --project "<project folder>" [--project ...]
    python report.py confirm "<record.json>" --signal time --rating amber [--reason "..."]
    python report.py confirm "<record.json>" --signal all            # accept every proposal
    python report.py render  "<record.json>"                          # rebuild the view

The record is the report: proposed ratings with the evidence behind each, then
the PM's confirmations and any override with its reason. The HTML is generated
from it and never edited by hand. The next status report reads the latest
confirmed record of its scope for trend, which is why the ratings live in a
diffable file rather than only on a page.

Reads the WBS and RAID registers and the sprint records, through the tools that
own them: `wbs-manager` and `sprint-facilitator`, found beside this skill in the
skills folder. Standard library only.
"""
import argparse
import glob
import html
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))


def sibling(skill):
    """A sibling skill's folder: beside this one once installed, or anywhere in
    the catalogue when run from the AKOS repository itself."""
    skills = os.path.dirname(os.path.dirname(HERE))
    for path in [os.path.join(skills, skill)] + sorted(
            glob.glob(os.path.join(skills, "..", "*", skill))):
        if os.path.isdir(path):
            return os.path.abspath(path)
    sys.exit("The %s skill is not installed beside this one (looked in %s). "
             "Install it: python install.py add %s --into <project>" % (skill, skills, skill))


WBS_SCRIPTS = os.path.join(sibling("wbs-manager"), "scripts")
SPRINT_RECORD = os.path.join(sibling("sprint-facilitator"), "scripts", "sprint_record.py")
# One folder per report type under a Reports folder, so reports stay findable
# as types are added. The type stays in the file name as well: a report sent
# on its own has lost its folder.
TYPE_DIRS = {"status-report": "Status", "sprint-update": "Sprint Update"}


def reports_dir(root, kind):
    return os.path.join(root, TYPE_DIRS[kind])

sys.path.insert(0, WBS_SCRIPTS)
import dates as D                                               # noqa: E402
import registry as R                                            # noqa: E402


def _sprint_record():
    """sprint_record's own table parser, so the record has one reader."""
    spec = importlib.util.spec_from_file_location("sprint_record", SPRINT_RECORD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F91 = _sprint_record()

SIGNALS = [("time", "On Time"), ("scope", "On Scope"), ("quality", "On Quality"),
           ("resources", "Resources")]
RATINGS = ("green", "amber", "red")
SEVERITY = {"green": 0, "amber": 1, "red": 2}
CLOSED = ("Done", "Cancelled")
RAID_REF = re.compile(r"\b[RIADC]\.\d+\b")


# ─── Sources ─────────────────────────────────────────────────────────────────

def discover(prjmgm):
    """The WBS and RAID registers under a project folder, by meta.kind.

    Kind, not filename: the folder may hold other JSON (agile conventions),
    and a register renamed by hand is still a register."""
    found = {"wbs": [], "raid": []}
    for root, dirs, files in os.walk(prjmgm):
        dirs[:] = [d for d in dirs if d not in ("PreviousV", "Reports", "AuxMat")]
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(root, name)
            try:
                kind = R.load(path).get("meta", {}).get("kind")
            except Exception:
                continue
            if kind == "wbs-register":
                found["wbs"].append(path)
            elif kind == "raid-register":
                found["raid"].append(path)
    return found


def run_json(args):
    """A sibling tool's --json output. Its exit code is ignored on purpose:
    `goals` exits 1 when it has findings, and the findings are data here.
    The child is told to write UTF-8: on Windows it would otherwise print in
    the console code page, which cannot encode what the records hold (a ✅)."""
    out = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                         encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    try:
        return json.loads(out.stdout)
    except ValueError:
        sys.exit("Could not read %s:\n%s" % (os.path.basename(args[0]), out.stderr or out.stdout))


def sprint_window(wbs_data, sprint=None, as_of=None):
    cal = R.rows(wbs_data, "sprints")
    if sprint:
        for s in cal:
            if s["Sprint"] == sprint:
                return s
        sys.exit("%s is not in the register's sprint calendar." % sprint)
    iso = (as_of or date.today()).isoformat()
    for s in cal:
        if s["Starts"] <= iso <= s["Ends"]:
            return s
    sys.exit("No sprint in the calendar contains %s; pass --sprint." % iso)


def record_facts(records, sprint):
    """Capacity, fist of five and committed hours per area, from the sprint
    record's planning block. Empty facts when there are no records to read."""
    path = os.path.join(records, sprint + ".md") if records else ""
    facts = {"available": None, "planned": None, "mood": None, "area": {}}
    if not path or not os.path.exists(path):
        return facts
    text = io.open(path, encoding="utf-8").read()
    planning = F91.block(text, "Planning") or ""
    m = re.search(r"\*\*Capacity:\*\*\s*([\d.]+)h available\s*·\s*([\d.]+)h planned", planning)
    if m:
        facts["available"], facts["planned"] = float(m.group(1)), float(m.group(2))
    _, fist = F91.table(planning, "Fist of five")
    scores = [float(r["Score (1-5)"]) for r in fist
              if re.match(r"^\d(\.\d+)?$", r.get("Score (1-5)", ""))]
    if scores:
        facts["mood"] = sum(scores) / len(scores)
    header, rows = F91.table(planning, "Committed items")
    if header and "Area" in header:
        for r in rows:
            item = r.get("Item", "")
            if item.startswith("~~") or (item.startswith("**") and item.endswith("**")):
                continue
            hit = F91.EFFORT_RE.search(r.get("Effort", ""))
            area = r.get("Area", "").strip() or "None"
            facts["area"][area] = facts["area"].get(area, 0.0) + (float(hit.group(1)) if hit else 0.0)
    return facts


# ─── RAID ────────────────────────────────────────────────────────────────────

def raid_entries(paths):
    out = []
    for p in paths:
        data = R.load(p)
        scope = data.get("meta", {}).get("scope") or os.path.basename(p)
        author = R.setting(data, "author")
        for e in R.rows(data, "entries"):
            e = dict(e)
            e["_scope"], e["_pm"] = scope, author
            out.append(e)
    return out


def latest_log(e):
    log = e.get("Action Log")
    if isinstance(log, list):
        dates_ = [x.get("on") for x in log if isinstance(x, dict) and x.get("on")]
        return max(dates_) if dates_ else None
    return None


def decided_on(e):
    log = e.get("Action Log")
    if not isinstance(log, list):
        return None
    hits = [x.get("on") for x in log if isinstance(x, dict) and x.get("on")
            and "Outcome" in (x.get("changed") or {})]
    return max(hits) if hits else None


def priority(e):
    u, c = e.get("Urgency (1-5)") or 0, e.get("Consequences (1-5)") or 0
    return round((u * 1.5 + c) / 12.5 * 100) if (u or c) else 0


def is_open(e):
    return R.clean(e.get("Status")) != "Closed"


def raid_card(e, as_of):
    upd = latest_log(e)
    stale = (as_of - date.fromisoformat(upd)).days if upd else None
    return {"ref": "%s.%s" % ((e.get("Type") or "?")[0], e.get("RAID.ID")),
            "scope": e["_scope"], "type": e.get("Type"), "detail": e.get("Detail"),
            "description": e.get("Description", ""), "plan": e.get("Action Plan", ""),
            "dri": e.get("DRI"), "priority": priority(e), "moscow": e.get("MoSCoW"),
            "trend": e.get("Trend"), "days_since_update": stale}


def top_risks(entries, as_of, n=3):
    """Risks and Issues only, never Decisions; MoSCoW, then priority, then
    the most recently updated."""
    pool = [e for e in entries if is_open(e) and e.get("Type") in ("Risk", "Issue")]
    pool.sort(key=lambda e: (str(e.get("MoSCoW") or "9"), -priority(e),
                             "".join(chr(255 - ord(ch)) for ch in (latest_log(e) or ""))))
    return [raid_card(e, as_of) for e in pool[:n]]


# ─── WBS ─────────────────────────────────────────────────────────────────────

class Wbs(object):
    def __init__(self, path):
        self.path = path
        self.data = R.load(path)
        self.scope = self.data.get("meta", {}).get("scope") or os.path.basename(path)
        self.items = {i["ID"]: i for i in R.rows(self.data, "items")}
        self.kids = {}
        for i in self.items.values():
            if i.get("Parent") is not None:
                self.kids.setdefault(i["Parent"], []).append(i["ID"])

    def subtree(self, rid):
        out, stack = [], [rid]
        while stack:
            cur = stack.pop()
            out.append(cur)
            stack.extend(self.kids.get(cur, []))
        return out

    def plan_end(self, rid):
        """Own Planned End on a leaf; the latest of the descendants' on a parent
        (parents derive, leaves carry). A closed row's plan is history:
        a Cancelled row adds nothing, and a Done row counts by when it landed."""
        item = self.items[rid]
        if item.get("Status") == "Cancelled":
            return None
        if rid in self.kids:
            ends = [self.plan_end(k) for k in self.kids[rid]]
            ends = [e for e in ends if e]
            return max(ends, key=lambda r: r["end"]) if ends else None
        if item.get("Status") == "Done":
            return D.resolve(item.get("Actual End")) or D.resolve(item.get("Planned End"))
        return D.resolve(item.get("Planned End"))

    def actual_end(self, rid):
        """When a row landed: its own Actual End, or on a parent - which never
        stores one - the latest of its descendants'. Cancelled rows add nothing."""
        item = self.items[rid]
        if item.get("Status") == "Cancelled":
            return None
        own = D.resolve(item.get("Actual End"))
        if own or rid not in self.kids:
            return own
        ends = [self.actual_end(k) for k in self.kids[rid]]
        ends = [e for e in ends if e]
        return max(ends, key=lambda r: r["end"]) if ends else None

    def scheduled(self, rid):
        for k in self.subtree(rid):
            i = self.items[k]
            if i.get("Status") in CLOSED:
                continue
            if any(i.get(f) for f in ("Planned End", "Horizon", "Sprint Planned",
                                      "Sprint Added", "Sprint Carried")):
                return True
        return False

    def open_key_deliverables(self):
        return [i for i in self.items.values()
                if i.get("Key Deliverable") == "Y" and i.get("Status") not in CLOSED]

    def in_sprint(self, i, sprint):
        return (i.get("Sprint Planned") == sprint or i.get("Sprint Added") == sprint
                or sprint in (i.get("Sprint Carried") or []))


# ─── The Essential 4 ─────────────────────────────────────────────────────────

def rate(red, amber):
    return "red" if red else "amber" if amber else "green"


def signal_time(wbs, window, as_of):
    red, amber, ev = [], [], []
    kds = wbs.open_key_deliverables()
    for kd in kds:
        base = D.resolve(kd.get("Baseline End"))
        plan = wbs.plan_end(kd["ID"])
        name = "#%s %s" % (kd["ID"], kd["Title"])
        if not base:
            continue
        if base["end"] < as_of.isoformat() and not (plan and plan["end"] >= as_of.isoformat()):
            red.append("%s: baseline %s passed, no plan beyond it" % (name, base["text"]))
            continue
        var = D.variance(base, plan) if plan else None
        if var and var["amount"] > 0:
            amber.append("%s: planned %s against baseline %s (%s)"
                         % (name, plan["text"], base["text"], D.describe(var)))
    subtree = {k for kd in kds for k in wbs.subtree(kd["ID"])}
    for s in R.rows(wbs.data, "schedule_log"):
        if (s.get("Field", "").startswith("Baseline") and s.get("Item") in subtree
                and window["Starts"] <= s.get("Changed On", "") <= window["Ends"]):
            amber.append("#%s rebaselined %s -> %s on %s: %s"
                         % (s["Item"], s.get("From"), s.get("To"), s["Changed On"], s.get("Reason", "")))
    ev = red + amber or ["%d open key deliverable(s), none planned past its baseline" % len(kds)]
    return rate(red, amber), ev


def signal_scope(wbs, raid, metrics, window, as_of):
    red, amber = [], []
    for e in raid:
        if e.get("Type") != "Change":
            continue
        ref = "C.%s %s" % (e.get("RAID.ID"), e.get("Detail"))
        on = decided_on(e)
        if e.get("Outcome") == "Approved" and on and window["Starts"] <= on <= window["Ends"]:
            amber.append("%s: approved %s" % (ref, on))
        review = e.get("Review On") or e.get("Next Review On")
        if not e.get("Outcome") and review and review < as_of.isoformat():
            red.append("%s: undecided, decision was due %s" % (ref, review))
    for kd in wbs.open_key_deliverables():
        if not wbs.scheduled(kd["ID"]):
            red.append("#%s %s: nothing schedules it" % (kd["ID"], kd["Title"]))
    if metrics:
        c, p = metrics["committed"]["h"], metrics["pulled_in"]["h"]
        if p > c:
            amber.append("%gh pulled in against %gh committed this sprint" % (p, c))
    ev = red + amber or ["No approved Change this sprint, no undecided Change overdue, every key deliverable scheduled"]
    return rate(red, amber), ev


CLOSURE_RE = re.compile(r"^Closure [^:]*:(.*?)(?:\n\n|$)", re.S)


def signal_quality(wbs, sprint):
    red, amber = [], []
    for i in wbs.items.values():
        if not wbs.in_sprint(i, sprint) and i.get("Sprint Ended") != sprint:
            continue
        name = "#%s %s" % (i["ID"], i["Title"])
        if i.get("Status") not in CLOSED and not i.get("Acceptance Criteria") and i["ID"] not in wbs.kids:
            amber.append("%s: committed with no acceptance criteria" % name)
        if i.get("Status") == "Done" and i.get("Sprint Ended") == sprint:
            m = CLOSURE_RE.search(i.get("Comments") or "")
            note = m.group(1) if m else ""
            follow = re.search(r"Follow-up:\s*(none)\b", note, re.I)
            if re.search(r"-\s*not met", note, re.I):
                (red if follow else amber).append("%s: closed with an AC not met%s"
                                                  % (name, "" if follow else ", follow-up named"))
            elif re.search(r"-\s*partial", note, re.I):
                amber.append("%s: closed with an AC partial" % name)
    ev = red + amber or ["Every committed row states its AC; no closure this sprint missed one"]
    return rate(red, amber), ev


def signal_resources(metrics, facts, window, as_of):
    red, amber, ev = [], [], []
    if facts["available"] and facts["planned"] and facts["planned"] > facts["available"]:
        amber.append("%gh planned against %gh available (%d%%): a stretch, so amber, never red"
                     % (facts["planned"], facts["available"], round(100 * facts["planned"] / facts["available"])))
    if metrics and metrics["committed"]["h"]:
        c, d = metrics["committed"]["h"], metrics["delivered"]["h"]
        start, end = date.fromisoformat(window["Starts"]), date.fromisoformat(window["Ends"])
        frac = min(1.0, max(0.0, ((as_of - start).days + 1) / float((end - start).days + 1)))
        expected = c * frac
        ratio = d / expected if expected else 1.0
        line = "%gh delivered against %gh committed%s" % (
            d, c, "" if frac >= 1 else " (%d%% of the sprint elapsed, %.1fh expected by now)" % (round(100 * frac), expected))
        if ratio < 0.5:
            red.append(line + ": under 50%")
        elif ratio < 0.8:
            amber.append(line + ": 50-80%")
        else:
            ev.append(line)
    elif metrics is not None:
        ev.append("Nothing committed to this sprint in this register")
    return rate(red, amber), red + amber + ev


def mood(facts):
    m = facts.get("mood")
    if m is None:
        return None
    return {"score": round(m, 1), "proposed": "green" if m >= 4 else "amber" if m >= 3 else "red",
            "evidence": ["Fist of five at planning: %.1f" % m]}


def worst(ratings):
    rs = [r for r in ratings if r in SEVERITY]
    return max(rs, key=lambda r: SEVERITY[r]) if rs else None


def trend_arrow(prev, now):
    if prev not in SEVERITY or now not in SEVERITY:
        return None
    return {2: u"\u2191", 1: u"\u2197", 0: u"\u2192", -1: u"\u2198", -2: u"\u2193"}[SEVERITY[now] - SEVERITY[prev]]


# ─── The executive summary ───────────────────────────────────────────────────
#
# Two or three sentences a stakeholder can follow without the registers: what
# was achieved, where the work is heading or what is at risk, and what is needed
# from the reader - in plain language, with no IDs, codes or colour names. A
# narrative takes judgement, which a template cannot supply: a fill-in sentence
# only restates the codes. So this script never writes the prose. It gathers the
# facts a narrative draws on, in plain words, and the agent running the report
# drafts the summary from them for the PM to confirm or rewrite.

SUMMARY_RULES = (
    "Draft the executive summary from the facts in the record: two or three sentences, "
    "plain language, no IDs, codes or colour names. Say what was achieved, where the work "
    "is heading or what is at risk, and what is needed from the reader - or that nothing is. "
    "Mid-sprint, say so (\"so far this sprint\") - never word it as the sprint's outcome. "
    "Show it to the PM; write it with: report.py confirm \"<record>\" --summary \"...\"")


def _done_in(wbs, sprint):
    rows = [i for i in wbs.items.values() if i.get("Sprint Ended") == sprint and i.get("Status") == "Done"]
    rows.sort(key=lambda i: -(i.get("Estimated Effort (h)") or 0))
    return [{"title": i["Title"], "hours": i.get("Estimated Effort (h)"), "scope": wbs.scope,
             "part_of": (wbs.items.get(i.get("Parent")) or {}).get("Title")} for i in rows]


def _in_progress(wbs):
    return [{"title": i["Title"], "scope": wbs.scope} for i in wbs.items.values()
            if i.get("Status") == "Implementing" and i["ID"] not in wbs.kids]


def _slipped(wbs):
    out = []
    for kd in wbs.open_key_deliverables():
        base, plan = D.resolve(kd.get("Baseline End")), wbs.plan_end(kd["ID"])
        if base and plan and D.variance(base, plan)["amount"] > 0:
            out.append({"title": kd["Title"], "was_due": base["text"], "now_expected": plan["text"]})
    return out


def _awaiting_decision(raid):
    return [{"change": e.get("Detail"), "description": e.get("Description"),
             "requested_by": e.get("Requested By"), "decide_by": e.get("Review On") or e.get("Next Review On")}
            for e in raid if e.get("Type") == "Change" and is_open(e) and not e.get("Outcome")]


def _risk_words(risks):
    return [{"risk": x["detail"], "description": x["description"], "trend": TREND_NAME.get(x.get("trend"))}
            for x in risks]


def sprint_progress(window, as_of):
    """Where in the sprint the report stands, so a draft written mid-sprint
    cannot read as the sprint's outcome."""
    start, end = date.fromisoformat(window["Starts"]), date.fromisoformat(window["Ends"])
    length, day = (end - start).days + 1, (as_of - start).days + 1
    return {"state": "closed" if as_of > end else "in progress", "day": min(max(day, 1), length),
            "of_days": length, "days_left": max((end - as_of).days, 0)}


def status_facts(wbs, raid, sprint, facts, risks):
    return {"delivered_this_sprint": _done_in(wbs, sprint), "in_progress": _in_progress(wbs),
            "key_deliverables_slipped": _slipped(wbs), "awaiting_a_decision": _awaiting_decision(raid),
            "top_risks": _risk_words(risks),
            "capacity": {"hours_available": facts["available"], "hours_planned": facts["planned"]}}


def update_facts(last, this, committed, wbss, raid, risks, facts):
    return {"last_sprint": {"sprint": last["sprint"], "goals": [
                {"goal": g["goal"], "verdict": g.get("achieved"), "why": g.get("why")} for g in last["goals"]],
                "hours_delivered": last["metrics"]["delivered"]["h"], "hours_committed": last["metrics"]["committed"]["h"],
                "main_deliveries": [d["title"] for d in last["delivered"][:5]], "highlights": last.get("highlights")},
            "this_sprint": {"sprint": this["sprint"], "goals": [
                {"goal": g["goal"], "done_when": g.get("done_when"), "carried_from": g.get("carried_from")}
                for g in this["goals"]],
                "largest_commitments": [c["item"] for c in committed[:5]],
                "hours_planned": facts["planned"], "hours_available": facts["available"]},
            "key_deliverables_slipped": [dict(s, scope=w.scope) for w in wbss for s in _slipped(w)],
            "awaiting_a_decision": _awaiting_decision(raid), "top_risks": _risk_words(risks)}


def summary_html(rec):
    s = rec.get("summary") or {}
    extra = ""
    if rec["kind"] == "sprint-update" and (rec.get("last") or {}).get("highlights"):
        extra = '<p class="small" style="margin-top:6px">Highlights from the last sprint\'s Review: %s</p>' % e(rec["last"]["highlights"])
    if s.get("text"):
        body = '<p class="sum-text">%s</p>' % e(s["text"])
    else:
        body = ('<p class="muted">Not written yet. Drafted from the facts in the record, in plain language, '
                'and confirmed with report.py confirm --summary.</p>')
    return '<section class="card summary"><h2>Executive summary</h2>%s%s</section>' % (body, extra)


# ─── Commands ────────────────────────────────────────────────────────────────

def months_window(as_of, back=1, ahead=2):
    y, m = as_of.year, as_of.month
    out = []
    for k in range(-back, ahead + 1):
        mm, yy = m + k, y
        while mm < 1:
            mm, yy = mm + 12, yy - 1
        while mm > 12:
            mm, yy = mm - 12, yy + 1
        out.append((yy, mm))
    return out


def milestone_map(wbs, as_of):
    cols = months_window(as_of)
    keys = ["%04d-%02d" % c for c in cols]
    buckets = {k: [] for k in keys}
    unscheduled = []
    for kd in sorted(wbs.open_key_deliverables(), key=lambda i: i["ID"]):
        plan = wbs.plan_end(kd["ID"])
        base = D.resolve(kd.get("Baseline End"))
        eff = plan or base
        card = {"id": kd["ID"], "title": kd["Title"], "status": kd.get("Status"),
                "baseline": base["text"] if base else None, "plan": plan["text"] if plan else None,
                "late": bool(base and plan and D.variance(base, plan)["amount"] > 0), "cue": None}
        if not eff:
            unscheduled.append(card)
            continue
        key = eff["end"][:7]
        if key < keys[0]:
            card["cue"] = "actually %s" % eff["text"]
            key = keys[0]
        elif key > keys[-1]:
            card["cue"] = "actually %s" % eff["text"]
            key = keys[-1]
        buckets[key].append(card)
    # What was delivered belongs on it too, or the roadmap reads as if nothing
    # ever landed. Inside the window a delivered deliverable gets its card in the
    # month it landed; before the window it is listed by title only under the
    # first column, so the view is complete without filling with history.
    earlier = []
    for kd in sorted(wbs.items.values(), key=lambda i: i["ID"]):
        if kd.get("Key Deliverable") != "Y" or kd.get("Status") != "Done":
            continue
        actual = wbs.actual_end(kd["ID"])
        if not actual or actual["end"][:7] < keys[0]:
            earlier.append({"id": kd["ID"], "title": kd["Title"],
                            "delivered": actual["text"] if actual else None,
                            "sort": actual["end"] if actual else ""})
            continue
        base = D.resolve(kd.get("Baseline End"))
        key = min(actual["end"][:7], keys[-1])
        buckets[key].insert(0, {"id": kd["ID"], "title": kd["Title"], "status": "Done",
                                "baseline": base["text"] if base else None, "plan": None,
                                "delivered": actual["text"], "cue": None,
                                "late": bool(base and D.variance(base, actual)["amount"] > 0)})
    # The edge columns hold whatever was clamped onto them, so they are labelled
    # as open ranges: "Dec 2026" would read as exactly December.
    label = lambda k: datetime(int(k[:4]), int(k[5:]), 1).strftime("%b %Y") + (
        " & earlier" if k == keys[0] else " & later" if k == keys[-1] else "")
    earlier.sort(key=lambda d: d.pop("sort"), reverse=True)
    return {"months": [{"key": k, "label": label(k),
                        "current": k == as_of.isoformat()[:7], "items": buckets[k]} for k in keys],
            "unscheduled": unscheduled, "earlier": earlier}


def previous_record(folder, kind, before):
    if not os.path.isdir(folder):
        return None
    best = None
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            rec = json.load(io.open(os.path.join(folder, name), encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind") != kind or rec.get("as_of", "") >= before:
            continue
        if any(s.get("confirmed") for s in rec.get("signals", {}).values()):
            best = (name, rec)
    return best


def cmd_status(args):
    prjmgm = os.path.abspath(args.prjmgm)
    regs = discover(prjmgm)
    if len(regs["wbs"]) != 1:
        sys.exit("Expected one WBS register under %s, found %d." % (prjmgm, len(regs["wbs"])))
    wbs = Wbs(regs["wbs"][0])
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    window = sprint_window(wbs.data, args.sprint, as_of)
    sprint = window["Sprint"]
    raid = raid_entries(regs["raid"])
    m = run_json([os.path.join(WBS_SCRIPTS, "wbs.py"), "metrics", wbs.path, "--sprint", sprint, "--json"])
    metrics = m.get("total", m) if m.get("total", m).get("committed") else None
    facts = record_facts(args.records, sprint)

    out_dir = reports_dir(os.path.join(prjmgm, "Reports"), "status-report")
    stem = "%s Status" % as_of.isoformat()
    path = os.path.join(out_dir, stem + ".json")
    if os.path.exists(path) and not args.force:
        old = json.load(io.open(path, encoding="utf-8"))
        if any(s.get("confirmed") for s in old.get("signals", {}).values()):
            sys.exit("%s already has confirmed ratings. Pass --force to regenerate and lose them."
                     % path)

    signals = {}
    for key, fn in (("time", lambda: signal_time(wbs, window, as_of)),
                    ("scope", lambda: signal_scope(wbs, raid, metrics, window, as_of)),
                    ("quality", lambda: signal_quality(wbs, sprint)),
                    ("resources", lambda: signal_resources(metrics, facts, window, as_of))):
        rating, ev = fn()
        signals[key] = {"proposed": rating, "evidence": ev, "confirmed": None,
                        "reason": None, "confirmed_on": None}
    mo = mood(facts)
    if mo:
        signals["mood"] = {"proposed": mo["proposed"], "evidence": mo["evidence"],
                           "confirmed": None, "reason": None, "confirmed_on": None}

    prev = previous_record(out_dir, "status-report", as_of.isoformat())
    rec = {"kind": "status-report", "version": 1, "scope": wbs.scope, "sprint": sprint,
           "period": {"start": window["Starts"], "end": window["Ends"]}, "as_of": as_of.isoformat(),
           "generated": datetime.now().isoformat(timespec="seconds"),
           "sources": {"wbs": os.path.relpath(wbs.path, prjmgm),
                       "raid": [os.path.relpath(p, prjmgm) for p in regs["raid"]]},
           "previous": None, "signals": signals,
           "focus": "", "highlights": "",
           # What waits on a decision is a Change with no Outcome. A RAID Decision
           # records a choice already made, so it asks nothing of the reader.
           "decisions": [raid_card(e, as_of) for e in raid if is_open(e) and e.get("Type") == "Change"
                         and not e.get("Outcome")],
           "help": [raid_card(e, as_of) for e in raid if is_open(e)
                    and e.get("Type") in ("Risk", "Issue", "Action")
                    and e.get("_pm") and R.clean(e.get("DRI")) != e["_pm"]],
           "risks": top_risks(raid, as_of), "milestones": milestone_map(wbs, as_of),
           "metrics": metrics,
           "summary": {"text": None, "confirmed_on": None}}
    rec["facts"] = status_facts(wbs, raid, sprint, facts, rec["risks"])
    rec["facts"]["sprint_progress"] = sprint_progress(window, as_of)
    if prev:
        rec["previous"] = {"file": prev[0], "as_of": prev[1]["as_of"],
                           "ratings": {k: v.get("confirmed") for k, v in prev[1]["signals"].items()}}
    os.makedirs(out_dir, exist_ok=True)
    write_record(path, rec)
    print("Status report for %s, %s (as of %s)" % (wbs.scope, sprint, as_of))
    for key, label in SIGNALS + [("mood", "Mood")]:
        if key in signals:
            print("  %-10s proposed %-6s  %s" % (label, signals[key]["proposed"], signals[key]["evidence"][0][:90]))
    print("  Record: %s\n  View:   %s" % (path, path[:-5] + ".html"))
    print("  Confirm each rating, or override it with a reason:")
    print("    report.py confirm \"%s\" --signal all" % path)
    print("  " + SUMMARY_RULES)
    return 0


def committed_items(records, sprint):
    """The new sprint's committed items, largest first, from its planning block."""
    path = os.path.join(records, sprint + ".md")
    text = io.open(path, encoding="utf-8").read()
    header, rows = F91.table(F91.block(text, "Planning") or "", "Committed items")
    out = []
    for r_ in rows:
        item = r_.get("Item", "")
        if not item or item.startswith("~~") or (item.startswith("**") and item.endswith("**")):
            continue
        hit = F91.EFFORT_RE.search(r_.get("Effort", ""))
        out.append({"item": item.replace("**", "").replace("`", ""), "hours": float(hit.group(1)) if hit else None,
                    "area": r_.get("Area", ""), "goal": r_.get("Goal", "")})
    out.sort(key=lambda c: -(c["hours"] or 0))
    return out


def board_column(status):
    return "doing" if status == "Implementing" else "done" if status == "Done" else "todo"


def sprint_board(wbss, sprint):
    """Every project's cards in the sprint, by the deliverable each serves.

    Which cards, their role, lane and path come from wbs.py's sprint_board(),
    the function the WBS dashboard's Current Sprint tab draws from, so a card
    sits in the same lane in both. Cancelled cards are left out: the update is
    a snapshot, with no toggle to bring them back. Projects and lanes run
    largest share of the sprint first; cards with no deliverable come last.
    """
    import wbs as WBS
    hrs = lambda cs: round(sum(c["hours"] or 0 for c in cs), 2)
    projects = []
    for w in wbss:
        lanes = {}
        for c in WBS.sprint_board(list(w.items.values()), sprint):
            row = w.items[c["id"]]
            if row.get("Status") == "Cancelled":
                continue
            lane = lanes.setdefault(c["lane"], {"id": c["lane"], "cards": []})
            lane["cards"].append({"id": c["id"], "title": row.get("Title", ""),
                                  "status": row.get("Status", ""), "type": row.get("Type", ""),
                                  "hours": row.get("Estimated Effort (h)"), "role": c["role"],
                                  "path": c["path"], "column": board_column(row.get("Status"))})
        if not lanes:
            continue
        for lane in lanes.values():
            head = w.items.get(lane["id"]) or {}
            lane.update({"title": head.get("Title"), "key": head.get("Key Deliverable") == "Y",
                         "hours": hrs(lane["cards"]),
                         "done_hours": hrs([c for c in lane["cards"] if c["column"] == "done"])})
            lane["cards"].sort(key=lambda c: -(c["hours"] or 0))
        ordered = sorted(lanes.values(), key=lambda l: (l["id"] is None, -l["hours"]))
        projects.append({"scope": w.scope, "hours": round(sum(l["hours"] for l in ordered), 2),
                         "lanes": ordered})
    projects.sort(key=lambda p: -p["hours"])
    return {"projects": projects}


def confirmed_overalls(folder, upto):
    """(as_of, overall) for each status record whose four signals are all
    confirmed, oldest first. A proposal is the generator's view; the update
    reports the PM's."""
    out = []
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            rec = json.load(io.open(os.path.join(folder, name), encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind") != "status-report" or rec.get("as_of", "") > upto:
            continue
        four = [rec.get("signals", {}).get(k, {}).get("confirmed") for k, _ in SIGNALS]
        if all(four):
            out.append((rec["as_of"], worst(four)))
    return out


def cmd_sprint(args):
    """The sprint update: the last sprint's outcome beside the new sprint's
    commitments. Run on the new sprint's first day, after planning."""
    if not args.project:
        sys.exit("Pass --project for every project the sprint spans.")
    wbss, raid_paths, folders = [], [], []
    for p in args.project:
        regs = discover(os.path.abspath(p))
        for w in regs["wbs"]:
            wbss.append(Wbs(w))
            folders.append(os.path.abspath(p))
        raid_paths += regs["raid"]
    if not wbss:
        sys.exit("No WBS register found under the projects given.")
    cal = R.rows(wbss[0].data, "sprints")
    window = sprint_window(wbss[0].data, args.sprint)
    sprint = window["Sprint"]
    idx = [s["Sprint"] for s in cal].index(sprint)
    if idx == 0:
        sys.exit("%s is the first sprint in the calendar; there is no last sprint to report." % sprint)
    prev = cal[idx - 1]["Sprint"]
    records = os.path.abspath(args.records)
    if not os.path.exists(os.path.join(records, sprint + ".md")):
        sys.exit("%s has not been planned: there is no record, so nothing is committed yet. "
                 "The sprint update runs after planning." % sprint)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    paths = [w.path for w in wbss]
    wbs_py = os.path.join(WBS_SCRIPTS, "wbs.py")
    m_prev = run_json([wbs_py, "metrics"] + paths + ["--sprint", prev, "--json"])
    m_prev = m_prev.get("total", m_prev)
    goals = run_json([SPRINT_RECORD, "goals", records, "--json"])
    by_sprint = {g["sprint"]: g for g in goals}
    g_prev, g_this = by_sprint.get(prev) or {"goals": []}, by_sprint.get(sprint) or {"goals": []}
    order = [g["sprint"] for g in goals]
    history = [g for g in goals[:order.index(sprint) + 1] if g["structured"]][-6:] if sprint in order else []

    by_key = {(g["sprint"], x["id"]): x for g in goals for x in g["goals"]}

    def chain(sp, goal):
        steps, cur = [(sp, goal)], goal
        while cur.get("carried_from"):
            ref = tuple(cur["carried_from"].split())
            if ref not in by_key or len(steps) > 12:
                break
            steps.append((ref[0], by_key[ref]))
            cur = by_key[ref]
        return steps

    carried = []
    for goal in g_this["goals"]:
        if goal.get("carried_from"):
            steps = chain(sprint, goal)
            carried.append({"sprint": sprint, "id": goal["id"], "goal": goal["goal"], "sprints": len(steps),
                            "trail": [s for s, _ in reversed(steps)],
                            "blockers": sorted({b for _, s in steps for b in RAID_REF.findall(s.get("why") or "")})})

    facts = record_facts(records, sprint)
    committed = committed_items(records, sprint)
    raid = raid_entries(raid_paths)
    risks = top_risks(raid, as_of)

    projects = []
    if len(wbss) > 1:
        for folder, w in zip(folders, wbss):
            hist = confirmed_overalls(reports_dir(os.path.join(folder, "Reports"), "status-report"), as_of.isoformat())
            last = hist[-1] if hist else None
            projects.append({"scope": w.scope, "overall": last[1] if last else None,
                             "as_of": last[0] if last else None,
                             "trend": trend_arrow(hist[-2][1], last[1]) if len(hist) > 1 else None})
    maps = [milestone_map(w, as_of) for w in wbss]
    for w, mm in zip(wbss, maps):
        for col in mm["months"]:
            for it in col["items"]:
                it["scope"] = w.scope
        for it in mm["unscheduled"] + mm["earlier"]:
            it["scope"] = w.scope
    roadmap = maps[0]
    for mm in maps[1:]:
        for a, b in zip(roadmap["months"], mm["months"]):
            a["items"] += b["items"]
        roadmap["unscheduled"] += mm["unscheduled"]
        roadmap["earlier"] += mm["earlier"]

    last = {"sprint": prev, "goals": g_prev.get("goals", []), "highlights": g_prev.get("highlights"),
            "metrics": m_prev, "delivered": [d for w in wbss for d in _done_in(w, prev)]}
    last["delivered"].sort(key=lambda d: -(d["hours"] or 0))
    this = {"sprint": sprint, "goals": g_this.get("goals", []), "hours": g_this.get("hours")}
    rec = {"kind": "sprint-update", "version": 1, "sprint": sprint,
           "period": {"start": window["Starts"], "end": window["Ends"]},
           "as_of": as_of.isoformat(), "generated": datetime.now().isoformat(timespec="seconds"),
           "projects_spanned": [w.scope for w in wbss], "last": last, "this": this,
           "committed": committed,
           "capacity": {"available": facts["available"], "planned": facts["planned"]},
           "mood": facts["mood"], "area": facts["area"], "projects": projects, "roadmap": roadmap,
           "history": history, "carried": carried, "risks": risks,
           "board": sprint_board(wbss, sprint),
           "summary": {"text": None, "confirmed_on": None}}
    rec["facts"] = update_facts(last, this, committed, wbss, raid, risks, facts)
    # Beside the sprint records by default: the update is the sprint's, and
    # the sprint spans projects, so no one project's Reports folder owns it.
    out_dir = reports_dir(args.out_dir or os.path.join(os.path.dirname(records), "Reports"),
                          "sprint-update")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "%s Sprint Update.json" % sprint)
    if os.path.exists(path):
        old = json.load(io.open(path, encoding="utf-8")).get("summary") or {}
        if old.get("text"):
            rec["summary"] = {"text": old["text"], "confirmed_on": old.get("confirmed_on")}
    write_record(path, rec)
    print("Sprint update for %s (last sprint %s) across %s" % (sprint, prev, ", ".join(rec["projects_spanned"])))
    if not rec["summary"].get("text"):
        print("  " + SUMMARY_RULES)
    print("  Record: %s\n  View:   %s" % (path, path[:-5] + ".html"))
    return 0


def cmd_confirm(args):
    path = args.record
    rec = json.load(io.open(path, encoding="utf-8"))
    today = date.today().isoformat()
    if rec.get("kind") not in ("status-report", "sprint-update"):
        sys.exit("Not a report record.")
    if not (args.signal or args.summary is not None or args.focus is not None or args.highlights is not None):
        sys.exit("Nothing to confirm: pass --signal, --summary, --focus or --highlights.")
    if args.signal:
        if rec["kind"] != "status-report":
            sys.exit("A sprint update carries no ratings; only its summary is confirmed.")
        sigs = rec["signals"]
        if args.signal == "all":
            if args.rating:
                sys.exit("--signal all accepts every proposal as it stands; it takes no --rating.")
            for s in sigs.values():
                if not s.get("confirmed"):
                    s["confirmed"], s["confirmed_on"] = s["proposed"], today
        else:
            if args.signal not in sigs:
                sys.exit("No signal %r in this report. Signals: %s" % (args.signal, ", ".join(sigs)))
            s = sigs[args.signal]
            rating = args.rating or s["proposed"]
            if rating != s["proposed"] and not args.reason:
                sys.exit("Overriding the proposed %s with %s needs --reason: the record must say why "
                         "a rating differs from what the registers show." % (s["proposed"], rating))
            s["confirmed"], s["reason"], s["confirmed_on"] = rating, args.reason, today
    summary = rec.setdefault("summary", {"text": None, "confirmed_on": None})
    if args.summary is not None:
        summary["text"] = args.summary or None
        summary["confirmed_on"] = today if args.summary else None
    if args.focus is not None:
        rec["focus"] = args.focus
    if args.highlights is not None:
        rec["highlights"] = args.highlights
    write_record(path, rec)
    left = [k for k, s in rec.get("signals", {}).items() if not s.get("confirmed")]
    if not rec["summary"].get("text"):
        left.append("summary")
    print("Confirmed. %s" % ("Still open: " + ", ".join(left) if left else "Everything is confirmed."))
    return 0


def cmd_render(args):
    rec = json.load(io.open(args.record, encoding="utf-8"))
    write_record(args.record, rec)
    print("Rendered %s" % (args.record[:-5] + ".html"))
    return 0


def write_record(path, rec):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    page = {"status-report": render_status}.get(rec["kind"], render_update)(rec)
    with io.open(path[:-5] + ".html", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)


# ─── Views ───────────────────────────────────────────────────────────────────

def e(text):
    return html.escape("" if text is None else str(text))


CSS = """
:root { color-scheme: light;
  --page:#f6f6f4; --surface:#fcfcfb; --border:rgba(11,11,11,0.10); --ink:#0b0b0b; --ink2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --s1:#2a78d6;
  --good:#0ca30c; --warn:#fab219; --crit:#d03b3b; --none:#c3c2b7;
  --goodbg:#e8f5e8; --warnbg:#fdf3dc; --critbg:#f9e6e6; --nonebg:#efeee9; --donebg:#e3edfa; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --border:rgba(255,255,255,0.10); --ink:#ffffff; --ink2:#c3c2b7;
  --muted:#898781; --grid:#2c2c2a; --s1:#3987e5;
  --goodbg:#16301a; --warnbg:#3a2f12; --critbg:#3a1a1a; --nonebg:#262624; --donebg:#17263a; } }
:root[data-theme="dark"] { color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --border:rgba(255,255,255,0.10); --ink:#ffffff; --ink2:#c3c2b7;
  --muted:#898781; --grid:#2c2c2a; --s1:#3987e5;
  --goodbg:#16301a; --warnbg:#3a2f12; --critbg:#3a1a1a; --nonebg:#262624; --donebg:#17263a; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background:var(--page); color:var(--ink);
  font-size:13px; line-height:1.5; padding:20px 16px; }
.page { max-width:1180px; margin:0 auto; }
header { margin-bottom:16px; }
h1 { font-size:20px; font-weight:700; }
.meta { color:var(--ink2); font-size:12px; margin-top:2px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:14px; }
h2 { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.8px; color:var(--ink2); margin-bottom:10px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:start; }
.grid2 > .card { margin-bottom:0; }
@media (max-width:760px) { .grid2 { grid-template-columns:1fr; } }
.muted { color:var(--muted); }
.small { font-size:11.5px; color:var(--ink2); }
.status { display:inline-flex; align-items:center; gap:6px; border-radius:16px; padding:3px 10px 3px 6px;
  font-size:12px; font-weight:600; white-space:nowrap; }
.status .dot { width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center;
  justify-content:center; color:#fff; font-size:11px; font-weight:800; }
.st-green { background:var(--goodbg); } .st-green .dot { background:var(--good); }
.st-amber { background:var(--warnbg); } .st-amber .dot { background:var(--warn); color:#0b0b0b; }
.st-red { background:var(--critbg); } .st-red .dot { background:var(--crit); }
.st-none { background:var(--nonebg); } .st-none .dot { background:var(--none); color:#0b0b0b; }
.st-done { background:var(--donebg); } .st-done .dot { background:var(--s1); }
.proposed { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); margin-left:6px; }
.e4 { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; }
@media (max-width:760px) { .e4 { grid-template-columns:1fr 1fr; } }
.e4-cell { border:1px solid var(--border); border-radius:8px; padding:10px; }
.e4-head { display:flex; align-items:center; justify-content:space-between; gap:6px; margin-bottom:6px; }
.e4-name { font-weight:700; font-size:12.5px; }
.arrow { font-size:16px; font-weight:700; color:var(--ink2); }
details summary { cursor:pointer; color:var(--ink2); font-size:11.5px; }
details ul { margin:6px 0 0 16px; font-size:11.5px; color:var(--ink2); }
.overall { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.override { font-size:11px; color:var(--ink2); margin-top:4px; font-style:italic; }
.kpis { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; margin-bottom:14px; }
@media (max-width:760px) { .kpis { grid-template-columns:1fr 1fr; } }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px; }
.tile .label { font-size:11.5px; color:var(--ink2); }
.tile .value { font-size:24px; font-weight:650; margin-top:2px; }
.tile .sub { font-size:11px; color:var(--muted); }
.goal { border:1px solid var(--border); border-radius:8px; padding:10px 12px; margin-bottom:8px; }
.goal-head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
.goal-title { font-weight:600; }
.goal-id { font-weight:700; color:var(--ink2); margin-right:6px; }
.chip { display:inline-block; font-size:10.5px; border:1px solid var(--border); border-radius:10px; padding:0 7px; color:var(--ink2); margin-left:4px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.4px; color:var(--ink2);
  border-bottom:1px solid var(--grid); padding:6px 8px; font-weight:600; }
td { padding:6px 8px; border-bottom:1px solid var(--grid); vertical-align:top; font-variant-numeric:tabular-nums; }
.stack { display:flex; gap:2px; height:12px; width:160px; }
.stack span { display:block; height:12px; }
.stack span:first-child { border-radius:2px 0 0 2px; } .stack span:last-child { border-radius:0 4px 4px 0; }
.legend { display:flex; gap:14px; flex-wrap:wrap; font-size:11.5px; color:var(--ink2); margin-bottom:8px; }
.key { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.hbar { display:grid; grid-template-columns:110px 1fr 56px; align-items:center; gap:8px; margin:5px 0; }
.hbar .track { height:14px; }
.hbar .fill { height:14px; background:var(--s1); border-radius:0 4px 4px 0; min-width:2px; }
.hbar .v { text-align:right; font-variant-numeric:tabular-nums; color:var(--ink2); }
.risk { border:1px solid var(--border); border-radius:8px; padding:10px 12px; margin-bottom:8px; }
.risk-head { display:flex; align-items:center; gap:8px; }
.risk-ref { font-weight:700; }
.risk-title { font-weight:600; flex:1; }
.risk-desc { font-size:12px; color:var(--ink2); margin-top:4px; }
.risk-desc strong { color:var(--ink); }
.stale { font-size:11px; color:var(--muted); font-style:italic; white-space:nowrap; }
.months { display:grid; gap:10px; align-items:start; }
.month { border:1px solid var(--border); border-radius:8px; padding:10px; min-width:0; }
.month.current { box-shadow: inset 0 0 0 2px var(--s1); }
.month h3 { font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:var(--ink2); margin-bottom:6px; }
.ms { padding:5px 0; border-bottom:1px solid var(--grid); font-size:12px; }
.ms:last-child { border-bottom:none; }
.ms .cue { font-size:11px; color:var(--ink2); font-weight:600; }
.list li { margin:0 0 6px 16px; }
footer { color:var(--muted); font-size:11px; margin-top:8px; }
.summary { border-left:4px solid var(--s1); }
.sum-text { font-size:14px; line-height:1.6; }
.minis { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; }
.mini { border:1px solid var(--border); border-radius:8px; padding:8px 10px; }
.mini .label { font-size:11px; color:var(--ink2); }
.mini .value { font-size:20px; font-weight:650; }
.mini .sub { font-size:11px; color:var(--muted); }
.ex-rows { display:flex; flex-wrap:wrap; gap:10px 28px; }
.ex-row { display:flex; align-items:center; gap:8px; }
.ex-name { font-weight:700; }
.tabs > input { position:absolute; opacity:0; pointer-events:none; }
.tab-bar { display:flex; gap:4px; border-bottom:1px solid var(--grid); margin-bottom:14px; }
.tab-bar label { padding:8px 14px; font-size:12.5px; font-weight:600; color:var(--ink2); cursor:pointer;
  border-bottom:2px solid transparent; margin-bottom:-1px; }
.tab-bar label:hover { color:var(--ink); }
.tab-panel { display:none; }
#v-overview:checked ~ .p-overview, #v-board:checked ~ .p-board { display:block; }
#v-overview:checked ~ .tab-bar label[for=v-overview], #v-board:checked ~ .tab-bar label[for=v-board] {
  color:var(--ink); border-bottom-color:var(--s1); }
#v-overview:focus-visible ~ .tab-bar label[for=v-overview], #v-board:focus-visible ~ .tab-bar label[for=v-board] {
  outline:2px solid var(--s1); outline-offset:2px; }
@media print { .tab-bar, .p-board { display:none !important; } .p-overview { display:block !important; } }
.bd-cols { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); }
.bd-heads { border-bottom:1px solid var(--grid); margin:8px 0 2px; }
.bd-colhead { font-size:10.5px; text-transform:uppercase; letter-spacing:.4px; color:var(--ink2); font-weight:600; padding:6px 8px; }
.bd-colhead span { text-transform:none; letter-spacing:0; font-weight:400; color:var(--muted); margin-left:6px; }
.bd-project { font-size:13px; margin:14px 0 4px; }
.bd-lane { border:1px solid var(--border); border-radius:8px; margin-bottom:8px; overflow:hidden; }
.bd-lanehead { display:flex; justify-content:space-between; gap:10px; padding:6px 10px; border-bottom:1px solid var(--grid); font-size:12px; }
.bd-cell { padding:6px; display:flex; flex-direction:column; gap:6px; min-width:0; }
.bd-cell + .bd-cell { border-left:1px dashed var(--grid); }
.bd-card { border:1px solid var(--border); border-left:3px solid var(--muted); border-radius:6px; padding:5px 8px; font-size:12px; }
.bd-doing { border-left-color:var(--s1); } .bd-done { border-left-color:var(--good); }
@media (max-width:760px) {
  .bd-cols { grid-template-columns:1fr; } .bd-heads { display:none; }
  .bd-cell + .bd-cell { border-left:none; border-top:1px dashed var(--grid); }
  .bd-cell::before { content:attr(data-col); font-size:10px; font-weight:600; text-transform:uppercase; color:var(--ink2); }
}
"""

ICON = {"green": u"\u2713", "amber": "!", "red": u"\u2715", None: u"\u2013"}
LABEL = {"green": "Green", "amber": "Amber", "red": "Red", None: "Not rated"}
MEANING = {"green": "aligned with the plan", "amber": "not aligned, in recovery",
           "red": "not aligned, no recovery", None: ""}
VERDICT = {"Yes": "green", "Partial": "amber", "No": "red"}
TREND_NAME = {u"\u2191": "Worsening fast", u"\u2197": "Worsening", u"\u2192": "Stable",
              u"\u2198": "Improving", u"\u2193": "Improving fast"}
CUES = re.compile(r"(because of|there is a risk that|which may result in|which is resulting in)", re.I)


def status_chip(rating, text=None):
    cls = "st-%s" % (rating if rating in SEVERITY else "none")
    return ('<span class="status %s"><span class="dot" aria-hidden="true">%s</span>%s</span>'
            % (cls, ICON.get(rating, ICON[None]), e(text or LABEL.get(rating, LABEL[None]))))


def done_chip():
    # Delivered is a state, not a rating: its own tint, icon and word, so it
    # is never read as green "on plan".
    return '<span class="status st-done"><span class="dot" aria-hidden="true">\u2713</span>delivered</span>'


def page(title, subtitle, body):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "<meta name=\"generator\" content=\"reporting\">\n<title>%s</title>\n<style>%s</style>\n</head>\n"
            "<body><div class=\"page\"><header><h1>%s</h1><div class=\"meta\">%s</div></header>\n%s\n"
            "<footer>Generated from the record beside this page; never edited by hand. "
            "Confirm or override ratings with report.py confirm.</footer></div></body></html>\n"
            % (e(title), CSS, e(title), subtitle, body))


def risks_html(risks):
    if not risks:
        return '<p class="muted">No open risks or issues.</p>'
    out = []
    for r in risks:
        if r.get("trend"):
            trend = '<span class="arrow" title="%s">%s</span>' % (e(TREND_NAME.get(r["trend"], "")), e(r["trend"]))
        elif r.get("days_since_update") is not None:
            trend = '<span class="stale">no update in %dd</span>' % r["days_since_update"]
        else:
            trend = '<span class="stale">never updated</span>'
        desc = CUES.sub(lambda m: "<strong>%s</strong>" % m.group(1), e(r["description"]))
        out.append('<div class="risk"><div class="risk-head"><span class="risk-ref">%s</span>'
                   '<span class="risk-title">%s</span>%s</div><div class="risk-desc">%s</div>'
                   '<div class="small" style="margin-top:4px">%s · DRI %s · priority %s%%%s</div></div>'
                   % (e(r["ref"]), e(r["detail"]), trend, desc, e(r["scope"]), e(r.get("dri") or "-"),
                      r["priority"], (" · plan: " + e(r["plan"])) if r.get("plan") else ""))
    return "".join(out)


def roadmap_html(ms, with_scope=False, compact=False):
    """Month columns: last month, now, the next two, then anything undated.
    The edge columns hold whatever falls outside the window, with its date."""
    cols = ms["months"] + ([{"label": "Unscheduled", "current": False, "items": ms["unscheduled"]}] if ms["unscheduled"] else [])

    def card(it):
        if it.get("delivered"):
            chip = done_chip()
            when = "delivered %s · baseline %s%s" % (it["delivered"], it["baseline"] or "-",
                                                     " (late)" if it["late"] else "")
        else:
            chip = (status_chip("amber", "late") if it["late"] else status_chip("green", "on plan")) \
                if (it["plan"] or it["baseline"]) else status_chip(None, "no date")
            when = "baseline %s · plan %s" % (it["baseline"] or "-", it["plan"] or "-")
        return '<div class="ms">%s <strong>%s#%s</strong> %s%s%s</div>' % (
            chip, (e(it["scope"]) + " ") if with_scope and it.get("scope") else "", it["id"], e(it["title"]),
            ('<div class="cue">%s</div>' % e(it["cue"])) if it.get("cue") else "",
            "" if compact else '<div class="small">%s</div>' % e(when))

    earlier = ms.get("earlier") or []
    before = ('<details class="small" style="margin-top:6px"><summary>%d delivered earlier</summary>%s</details>'
              % (len(earlier), "".join('<div>%s<strong>#%s</strong> %s%s</div>' % (
                  (e(it["scope"]) + " ") if with_scope and it.get("scope") else "", it["id"], e(it["title"]),
                  (" · %s" % e(it["delivered"])) if it.get("delivered") else "") for it in earlier))
              if earlier else "")
    mcols = []
    for n, c in enumerate(cols):
        items = "".join(card(it) for it in c["items"]) or ("" if (n == 0 and before) else '<p class="muted small">Nothing due</p>')
        if n == 0:
            items += before
        mcols.append('<div class="month%s"><h3>%s%s</h3>%s</div>'
                     % (" current" if c.get("current") else "", e(c["label"]), " · now" if c.get("current") else "", items))
    return ('<div class="months" style="grid-template-columns:repeat(%d, minmax(0,1fr))">%s</div>'
            '<p class="small" style="margin-top:8px">Key deliverables: open ones placed by planned end, else baseline; delivered ones by the date they landed, and those delivered before the window listed under the first column. The first '
            'and last columns hold anything earlier or later, with its real date.</p>' % (len(mcols), "".join(mcols)))


def render_status(rec):
    sigs = rec["signals"]
    prev = (rec.get("previous") or {}).get("ratings", {})
    shown = lambda s: s.get("confirmed") or s.get("proposed")
    overall = worst([shown(sigs[k]) for k, _ in SIGNALS if k in sigs])
    all_confirmed = all(sigs[k].get("confirmed") for k, _ in SIGNALS if k in sigs)
    cells = []
    for key, label in SIGNALS + [("mood", "Mood")]:
        if key not in sigs:
            continue
        s = sigs[key]
        r = shown(s)
        arrow = trend_arrow(prev.get(key), r) if s.get("confirmed") else None
        cells.append(
            '<div class="e4-cell"><div class="e4-head"><span class="e4-name">%s</span>%s</div>%s%s%s'
            '<details><summary>Evidence</summary><ul>%s</ul></details></div>'
            % (e(label),
               ('<span class="arrow" title="%s since %s">%s</span>' % (e(TREND_NAME[arrow]), e(rec["previous"]["as_of"]), arrow)) if arrow else "",
               status_chip(r), "" if s.get("confirmed") else '<span class="proposed">proposed</span>',
               ('<div class="override">Override: %s</div>' % e(s["reason"])) if s.get("reason") else "",
               "".join("<li>%s</li>" % e(x) for x in s["evidence"])))
    first = "" if rec.get("previous") else '<span class="small">First confirmed report of this scope: no trend yet.</span>'
    e4 = ('<section class="card"><h2>Essential 4</h2><div class="overall"><strong>Overall</strong>%s%s %s</div>'
          '<div class="e4">%s</div><p class="small" style="margin-top:10px">Overall is the worst of the four; Mood '
          'is shown but not counted. Green: %s. Amber: %s. Red: %s.</p></section>'
          % (status_chip(overall), "" if all_confirmed else '<span class="proposed">proposed</span>', first,
             "".join(cells), MEANING["green"], MEANING["amber"], MEANING["red"]))

    def lst(items, empty):
        if not items:
            return '<p class="muted">%s</p>' % e(empty)
        return '<ul class="list">%s</ul>' % "".join(
            "<li><strong>%s</strong> %s <span class='small'>(DRI %s)</span></li>"
            % (e(x["ref"]), e(x["detail"]), e(x.get("dri") or "-")) for x in items)
    focus = ('<section class="grid2"><div class="card"><h2>Focus</h2>%s<h2 style="margin-top:12px">Highlights</h2>%s</div>'
             '<div class="card"><h2>Decisions required</h2>%s<h2 style="margin-top:12px">Help required</h2>%s</div></section>'
             % ('<p>%s</p>' % e(rec["focus"]) if rec.get("focus") else '<p class="muted">Not written yet: report.py confirm --focus "…"</p>',
                '<p>%s</p>' % e(rec["highlights"]) if rec.get("highlights") else '<p class="muted">Not written yet: report.py confirm --highlights "…"</p>',
                lst(rec["decisions"], "No change request is waiting for a decision."), lst(rec["help"], "Nothing waits on someone else.")))
    milestones = ('<section class="card"><h2>Key deliverables</h2>%s</section>' % roadmap_html(rec["milestones"]))
    risks = '<section class="card"><h2>Top risks and issues</h2>%s</section>' % risks_html(rec["risks"])
    sub = "%s · %s → %s · as of %s" % (e(rec["sprint"]), e(rec["period"]["start"]), e(rec["period"]["end"]), e(rec["as_of"]))
    return page("%s status" % rec["scope"], sub, summary_html(rec) + e4 + focus + milestones + risks)


def goal_card(x, show_verdict):
    v = x.get("achieved")
    chip = (status_chip(VERDICT.get(v), v) if v else status_chip(None, "Open")) if show_verdict else ""
    extra = ""
    if show_verdict and x.get("why"):
        extra = '<div class="small">Why: %s</div>' % e(x["why"])
    elif not show_verdict:
        extra = '<div class="small">Done when: %s</div>' % e(x.get("done_when") or "-")
    return ('<div class="goal"><div class="goal-head"><div><span class="goal-id">%s</span><span class="goal-title">%s</span>%s</div>%s</div>%s</div>'
            % (e(x["id"]), e(x["goal"]),
               ('<span class="chip">carried from %s</span>' % e(x["carried_from"])) if x.get("carried_from") else "",
               chip, extra))


BOARD_COLUMNS = (("todo", "To do"), ("doing", "Doing"), ("done", "Done"))


def board_html(board, as_of):
    """The sprint's cards in project and deliverable lanes, by status."""
    projects = (board or {}).get("projects") or []
    if not projects:
        return ""
    cards = [c for p in projects for l in p["lanes"] for c in l["cards"]]
    hrs = lambda cs: "%gh" % round(sum(c["hours"] or 0 for c in cs), 2)
    heads = "".join('<div class="bd-colhead">%s<span>%d · %s</span></div>'
                    % (lab, len([c for c in cards if c["column"] == k]), hrs([c for c in cards if c["column"] == k]))
                    for k, lab in BOARD_COLUMNS)

    def card(c):
        tag = "" if c["role"] == "Committed" else '<span class="chip">%s</span>' % e(c["role"].lower())
        path = ('<div class="small">› %s</div>' % e(" › ".join(c["path"]))) if c["path"] else ""
        meta = " · ".join(x for x in (c["type"], ("%gh" % c["hours"]) if c["hours"] else "no estimate") if x)
        return ('<div class="bd-card bd-%s"><strong>#%s</strong> %s%s%s<div class="small">%s</div></div>'
                % (c["column"], c["id"], e(c["title"]), tag, path, e(meta)))

    out = []
    for p in projects:
        lanes = []
        for l in p["lanes"]:
            title = ('<strong>#%s</strong> %s%s' % (l["id"], e(l["title"]), ' <span class="chip">key</span>' if l["key"] else "")
                     if l["id"] is not None else '<span class="muted">No deliverable: these cards have no parent</span>')
            cells = "".join('<div class="bd-cell" data-col="%s">%s</div>'
                            % (lab, "".join(card(c) for c in l["cards"] if c["column"] == k) or '<span class="muted small">–</span>')
                            for k, lab in BOARD_COLUMNS)
            lanes.append('<div class="bd-lane"><div class="bd-lanehead"><span>%s</span><span class="small">%gh in sprint · %gh done</span></div>'
                         '<div class="bd-cols">%s</div></div>' % (title, l["hours"], l["done_hours"], cells))
        out.append('<h3 class="bd-project">%s <span class="small">%gh</span></h3>%s' % (e(p["scope"]), p["hours"], "".join(lanes)))
    return ('<section class="card"><h2>Sprint board · as of %s</h2>'
            '<p class="small">The deep dive behind the overview: every project\'s cards in this sprint, by the deliverable each serves. A snapshot: '
            'rerun <code>report.py sprint</code> to bring it up to date; the confirmed summary is kept.</p>'
            '<div class="bd-cols bd-heads">%s</div>%s</section>' % (e(as_of), heads, "".join(out)))


def render_update(rec):
    last, this = rec["last"], rec["this"]
    lm = last["metrics"]
    lg = last["goals"]
    met = {v: sum(1 for g in lg if g.get("achieved") == v) for v in ("Yes", "Partial", "No")}
    cap = rec.get("capacity") or {}

    def stat(label, value, sub=""):
        return '<div class="mini"><div class="label">%s</div><div class="value">%s</div><div class="sub">%s</div></div>' % (e(label), e(value), e(sub))

    last_stats = '<div class="minis">%s%s</div>' % (
        stat("Goals met", "%d of %d" % (met["Yes"], len(lg)) if lg else "-",
             ("%d partly, %d not" % (met["Partial"], met["No"])) if lg else "no goals recorded"),
        stat("Delivered", "%gh" % lm["delivered"]["h"], "%d items · %gh committed" % (lm["delivered"]["n"], lm["committed"]["h"])))
    pieces = "".join("<li>%s <span class='small'>%s</span></li>" % (e(d["title"]), e(d["scope"]))
                     for d in last["delivered"][:5])
    last_html = ('<section class="card"><h2>Last sprint · %s</h2>%s%s%s</section>'
                 % (e(last["sprint"]), last_stats,
                    "".join(goal_card(g, True) for g in lg) or '<p class="muted">No goals recorded.</p>',
                    ('<h2 style="margin-top:12px">Main pieces delivered</h2><ul class="list">%s</ul>' % pieces) if pieces else ""))

    tg = this["goals"]
    hours = this.get("hours") or {}
    focus = ("%d%% of committed hours serve a goal" % round(100 * hours["goal_linked"] / hours["committed"])) if hours.get("committed") else ""
    this_stats = '<div class="minis">%s%s</div>' % (
        stat("Planned", "%gh" % cap["planned"] if cap.get("planned") else "-",
             ("against %gh available (%d%%)" % (cap["available"], round(100 * cap["planned"] / cap["available"])))
             if cap.get("planned") and cap.get("available") else ""),
        stat("Confidence", "%.1f of 5" % rec["mood"] if rec.get("mood") is not None else "-", focus))
    items = rec.get("committed") or []
    shown, rest = items[:8], items[8:]
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (e(c["item"]), ("%gh" % c["hours"]) if c["hours"] is not None else "-", e(c["area"]), e(c["goal"]))
                   for c in shown)
    if rest:
        rows += "<tr><td colspan=4 class='small'>and %d more (%gh)</td></tr>" % (len(rest), sum(c["hours"] or 0 for c in rest))
    this_html = ('<section class="card"><h2>This sprint · %s</h2>%s%s<h2 style="margin-top:12px">Committed</h2>'
                 '<table><thead><tr><th>Item</th><th>Effort</th><th>Area</th><th>Goal</th></tr></thead><tbody>%s</tbody></table></section>'
                 % (e(this["sprint"]), this_stats,
                    "".join(goal_card(g, False) for g in tg) or '<p class="muted">No goals set.</p>',
                    rows or "<tr><td colspan=4 class='muted'>Nothing committed.</td></tr>"))

    projects = ""
    if rec.get("projects"):
        projects = '<section class="card"><h2>Projects</h2><div class="ex-rows">%s</div></section>' % "".join(
            '<div class="ex-row"><span class="ex-name">%s</span>%s%s<span class="small">%s</span></div>'
            % (e(p["scope"]), status_chip(p["overall"]) if p["overall"] else status_chip(None, "No confirmed status"),
               ('<span class="arrow" title="%s since the previous confirmed status">%s</span>' % (e(TREND_NAME[p["trend"]]), p["trend"])) if p.get("trend") else "",
               ("confirmed %s" % e(p["as_of"])) if p.get("as_of") else "")
            for p in rec["projects"])
    roadmap = '<section class="card"><h2>Key deliverables</h2>%s</section>' % roadmap_html(rec["roadmap"], with_scope=len(rec["projects_spanned"]) > 1, compact=True)

    hrows = []
    for h in rec.get("history", []):
        n = len(h["goals"]) or 1
        seg = "".join('<span style="width:%d%%;background:var(--%s)" title="%s: %d"></span>' % (100 * c / n, col, lab, c)
                      for lab, col, c in (("Yes", "good", sum(1 for g in h["goals"] if g.get("achieved") == "Yes")),
                                          ("Partial", "warn", sum(1 for g in h["goals"] if g.get("achieved") == "Partial")),
                                          ("No", "crit", sum(1 for g in h["goals"] if g.get("achieved") == "No")),
                                          ("Open", "none", sum(1 for g in h["goals"] if not g.get("achieved")))) if c)
        hh = h.get("hours") or {}
        fp = "%d%%" % round(100 * hh["goal_linked"] / hh["committed"]) if hh.get("committed") else "-"
        hrows.append("<tr><td>%s</td><td><div class='stack'>%s</div></td><td>%s</td></tr>" % (e(h["sprint"]), seg, fp))
    legend = "".join('<span><span class="key" style="background:var(--%s)"></span>%s</span>' % (c, l)
                     for l, c in (("Yes", "good"), ("Partial", "warn"), ("No", "crit"), ("Open", "none")))
    carried = "".join('<div class="small" style="margin-top:6px"><strong>%s</strong> %s: in %d sprints (%s)%s</div>'
                      % (e(c["id"]), e(c["goal"]), c["sprints"], e(" → ".join(c["trail"])),
                         (", blocked by " + e(", ".join(c["blockers"]))) if c["blockers"] else "")
                      for c in rec.get("carried") or [])
    history = ('<section class="card"><h2>Goal history and focus</h2><div class="legend">%s</div><table><thead><tr><th>Sprint</th>'
               '<th>Goals</th><th>Goal focus</th></tr></thead><tbody>%s</tbody></table>%s</section>'
               % (legend, "".join(hrows) or "<tr><td colspan=3 class='muted'>No structured sprint yet.</td></tr>",
                  ('<h2 style="margin-top:12px">Carried over</h2>' + carried) if carried else ""))
    af = rec.get("area") or {}
    top = max(af.values()) if af else 0
    af_rows = "".join('<div class="hbar"><span>%s</span><div class="track"><div class="fill" style="width:%d%%" title="%s: %gh"></div></div><span class="v">%gh</span></div>'
                      % (e(k), round(100 * v / top) if top else 0, e(k), v, v) for k, v in sorted(af.items(), key=lambda kv: -kv[1]))
    risks_effort = ('<section class="card"><h2>Top risks and issues</h2>%s<h2 style="margin-top:14px">This sprint\'s hours by area</h2>%s</section>'
                    % (risks_html(rec["risks"]), af_rows or '<p class="muted">The record has no Area column.</p>'))
    sub = "%s → %s · last sprint %s · %s" % (e(rec["period"]["start"]), e(rec["period"]["end"]), e(last["sprint"]),
                                             e(", ".join(rec["projects_spanned"])))
    overview = (summary_html(rec) + '<div class="grid2">' + last_html + this_html + "</div>"
                + '<div style="height:14px"></div>' + projects + roadmap
                + '<div class="grid2">' + history + risks_effort + "</div>")
    board = board_html(rec.get("board"), rec["as_of"])
    if not board:
        return page("Sprint update · %s" % rec["sprint"], sub, overview)
    # The update is an executive overview for people outside the work; the
    # board is a deep dive. It gets its own tab so the page a stakeholder
    # opens (and prints) is the overview alone. Radio inputs, not script, so
    # the page stays a static file.
    body = ('<div class="tabs"><input type="radio" name="view" id="v-overview" checked>'
            '<input type="radio" name="view" id="v-board">'
            '<div class="tab-bar"><label for="v-overview">Overview</label><label for="v-board">Sprint board</label></div>'
            '<div class="tab-panel p-overview">%s</div><div class="tab-panel p-board">%s</div></div>' % (overview, board))
    return page("Sprint update · %s" % rec["sprint"], sub, body)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command")
    s = sub.add_parser("status", help="project status record and view, with the Essential 4 proposed")
    s.add_argument("prjmgm", help="the folder holding the project's WBS and RAID registers")
    s.add_argument("--records", help="the sprint records folder; without it, capacity and confidence are not read")
    s.add_argument("--sprint", help="default: the sprint containing --as-of")
    s.add_argument("--as-of", metavar="YYYY-MM-DD")
    s.add_argument("--force", action="store_true", help="overwrite a same-day record with confirmed ratings")
    s.set_defaults(func=cmd_status)
    s = sub.add_parser("sprint", help="sprint update: the last sprint's outcome and this sprint's commitments")
    s.add_argument("--sprint", required=True, help="the sprint being started; run after its planning")
    s.add_argument("--records", required=True, help="the sprint records folder (sprint-facilitator)")
    s.add_argument("--project", action="append", help="a folder holding a project's WBS and RAID registers; repeat for each")
    s.add_argument("--as-of", metavar="YYYY-MM-DD")
    s.add_argument("--out-dir", help="the Reports folder; the update goes in its Sprint Update subfolder (default: Reports beside the records folder)")
    s.set_defaults(func=cmd_sprint)
    s = sub.add_parser("confirm", help="confirm a proposed rating, or override it with a reason")
    s.add_argument("record")
    s.add_argument("--signal", help="time, scope, quality, resources, mood, or all (status reports)")
    s.add_argument("--rating", choices=RATINGS)
    s.add_argument("--reason")
    s.add_argument("--summary", help="the executive summary, as agreed with the PM; an empty string clears it")
    s.add_argument("--focus")
    s.add_argument("--highlights")
    s.set_defaults(func=cmd_confirm)
    s = sub.add_parser("render", help="rebuild the view from its record")
    s.add_argument("record")
    s.set_defaults(func=cmd_render)
    args = p.parse_args()
    if not getattr(args, "command", None):
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
