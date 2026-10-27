# -*- coding: utf-8 -*-
"""Reading a Stakeholder Register: what consumers import.

    import stk_register as STK
    data = STK.load_or_default("<project folder>")    # never None
    for comm, level in STK.audiences_for(data, "status-report"): ...

Everything here reads; nothing writes the register (that is stk.py). The
contacts file is read here and written by stk.py's `contact`, or by hand.

A register is found by its shape: a JSON file whose meta.kind is
`stakeholder-register`. Never by a configured path. Across projects, a root
folder is walked for that shape, skipping PreviousV/, Reports/ and AuxMat/.
"""
import calendar as _cal
import csv
import datetime as dt
import glob
import io
import json
import os
import re
import subprocess

import registry as R
import stk_schema as S

SKIP_DIRS = ("PreviousV", "Reports", "AuxMat", ".git", "__pycache__", "node_modules")


# --- finding ------------------------------------------------------------------

def _kind(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh).get("meta", {}).get("kind")
    except (OSError, ValueError, AttributeError):
        return None


def find(folder):
    """The register in a project folder, or None. Two is an error."""
    hits = [p for p in glob.glob(os.path.join(folder, "Stakeholders *.json"))
            if _kind(p) == S.KIND]
    if len(hits) > 1:
        raise SystemExit("More than one stakeholder register in %s: %s"
                         % (folder, ", ".join(os.path.basename(h) for h in hits)))
    return hits[0] if hits else None


def resolve(path):
    """A register path from a register path or its folder. Exits if neither."""
    if os.path.isdir(path):
        found = find(path)
        if not found:
            raise SystemExit("No stakeholder register in %s." % path)
        return found
    return path


def all_registers(root):
    """Every stakeholder register under a root folder, found by meta.kind."""
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = os.path.join(base, name)
            if name.endswith(".json") and _kind(path) == S.KIND:
                found.append(path)
    return found


# --- the solo default -----------------------------------------------------------

def default_register(scope=""):
    """What a scope with no register has: its owner, and a status report to them."""
    return {
        "meta": {"kind": S.KIND, "scope": scope, "default": True, "settings": {}},
        S.GROUPS: [],
        S.STAKEHOLDERS: [{"ID": "S.1", "Name": "Owner", "Role": "Project manager",
                          "Power": "High", "Interest": "High", "Current": "Leading",
                          "Desired": "Leading", "Share Level": "owner", "Status": "Active"}],
        S.COMMS: [{"ID": "C.1", "What": "Status report", "Report": "status-report",
                   "Mode": "push", "Audience": ["S.1"], "Cadence": "per sprint",
                   "Channel": "the report file", "Status": "Active"}],
        S.CHANGES: [],
    }


def load_or_default(folder, scope=""):
    """The project's register, or the solo default. Consumers call this and never
    test for the file themselves."""
    found = find(folder) if os.path.isdir(folder) else None
    if found:
        data = R.load(found)
        data["meta"]["path"] = found
        return data
    return default_register(scope)


def audiences_for(data, report):
    """[(communication, share level)] for every active communication carrying a
    report kind - what the reporting tool asks."""
    out = []
    for comm in R.rows(data, S.COMMS):
        if S.is_active(comm) and comm.get("Report") == report:
            out.append((comm, resolve_audience(data, comm)["share_level"]))
    return out


# --- contacts ---------------------------------------------------------------------

def contacts_path(register_path, data):
    folder = os.path.dirname(os.path.abspath(register_path))
    return os.path.join(folder, "Contacts %s.csv" % data["meta"].get("scope", ""))


def read_contacts(path):
    """{S.n: row} plus the file's columns. Tolerant: extra columns kept, blanks fine."""
    if not path or not os.path.isfile(path):
        return {}, list(S.CONTACT_COLUMNS), False
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or S.CONTACT_COLUMNS)
        rows = {}
        for row in reader:
            sid = S.norm_id(row.get("ID"))
            if sid:
                rows[sid] = dict((k, S.clean(v)) for k, v in row.items() if k)
    for col in S.CONTACT_COLUMNS:
        if col not in columns:
            columns.append(col)
    return rows, columns, True


def write_contacts(path, rows, columns):
    """UTF-8 with a BOM, so Excel opens accents correctly."""
    def key(sid):
        p = S.parse_id(sid)
        return p[1] if p else 0
    with io.open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for sid in sorted(rows, key=key):
            writer.writerow(rows[sid])


def git_state(path):
    """How git sees a file: "tracked", "unignored" (`git add` would take it),
    "ignored", or None (not in a repository, or no git). The contacts file must
    be ignored: git keeps every version of other people's personal data for good."""
    folder, name = os.path.split(os.path.abspath(path))

    def git(*args):
        try:
            return subprocess.run(("git",) + args, cwd=folder, capture_output=True, text=True)
        except OSError:
            return None
    inside = git("rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return None
    if git("ls-files", "--error-unmatch", name).returncode == 0:
        return "tracked"
    return "ignored" if git("check-ignore", "-q", name).returncode == 0 else "unignored"


# --- sprint calendar --------------------------------------------------------------

def sprint_calendar(register_path):
    """[(start, end)] dates, ascending: the project's agile conventions file, else
    its WBS register, each found by meta.kind in the register's folder and below.
    Empty when there is neither; `per sprint` then reads as every 14 days, and
    the callers say so."""
    folder = os.path.dirname(os.path.abspath(register_path)) if register_path else None
    candidates = []
    if folder:
        jsons = [p for p in glob.glob(os.path.join(folder, "**", "*.json"), recursive=True)
                 if not any(part in SKIP_DIRS for part in p[len(folder):].split(os.sep))]
        candidates += [p for p in jsons if _kind(p) == "agile-conventions"]
        candidates += [p for p in jsons if _kind(p) == "wbs-register"]
    for path in candidates:
        try:
            with io.open(path, encoding="utf-8") as fh:
                sprints = json.load(fh).get("sprints") or []
            spans = sorted((dt.date.fromisoformat(s["Starts"]), dt.date.fromisoformat(s["Ends"]))
                           for s in sprints if s.get("Starts") and s.get("Ends"))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if spans:
            return spans
    return []


# --- when a communication is due ----------------------------------------------------

def _add_months(day, months):
    m = day.month - 1 + months
    y, m = day.year + m // 12, m % 12 + 1
    return dt.date(y, m, min(day.day, _cal.monthrange(y, m)[1]))


PERIODS = {"weekly": lambda d: d + dt.timedelta(days=7),
           "monthly": lambda d: _add_months(d, 1),
           "quarterly": lambda d: _add_months(d, 3)}


def due(comm, as_of, sprints, within=0):
    """(state, due date or None). States: overdue, due, ok, event, inactive.

    A calendar cadence is due `period` after Last Done; overdue once that has
    passed. `per sprint` is due during each sprint: done since the current
    sprint started is ok, last done in the previous sprint (or never) is due,
    a whole sprint missed is overdue. Never done is due."""
    if not S.is_active(comm):
        return "inactive", None
    kind = S.cadence_kind(comm.get("Cadence"))
    if kind == "on event":
        return "event", None
    last = comm.get("Last Done")
    last = dt.date.fromisoformat(last) if last else None
    if kind == "per sprint" and sprints:
        current = [i for i, (s, e) in enumerate(sprints) if s <= as_of <= e]
        if current:
            i = current[0]
            start, end = sprints[i]
            if last and last >= start:
                nxt = sprints[i + 1][1] if i + 1 < len(sprints) else end
                return "ok", nxt
            prev_start = sprints[i - 1][0] if i > 0 else start
            if last is None or last >= prev_start:
                return "due", end
            return "overdue", sprints[i - 1][1] if i > 0 else end
    step = PERIODS.get(kind) or (lambda d: d + dt.timedelta(days=14))
    if last is None:
        return "due", as_of
    nxt = step(last)
    if nxt < as_of:
        return "overdue", nxt
    if nxt <= as_of + dt.timedelta(days=within):
        return "due", nxt
    return "ok", nxt


# --- who an audience is ----------------------------------------------------------------

CHANNEL_FIELD = (("e-mail", "Email"), ("email", "Email"), ("mail", "Email"),
                 ("whatsapp", "Phone"), ("sms", "Phone"), ("call", "Phone"),
                 ("phone", "Phone"), ("meeting", "Email"), ("link", "Email"))


def channel_field(channel):
    text = S.clean(channel).lower()
    for word, field in CHANNEL_FIELD:
        if word in text:
            return field
    return None


def is_content(comm):
    return S.clean(comm.get("Channel")).lower().startswith("content:")


def resolve_audience(data, comm, contacts=None):
    """Who receives a communication, each once, with an address where one exists.

    {"people": [{ID, Name, Share Level, Field, Address}], "missing": [names],
     "unknown": [IDs], "share_level": "owner"|"external", "public": bool}
    """
    groups = dict((g.get("ID"), g) for g in R.rows(data, S.GROUPS))
    people = dict((p.get("ID"), p) for p in R.rows(data, S.STAKEHOLDERS))
    chosen, unknown = [], []
    for ref in comm.get("Audience") or []:
        if ref in groups:
            for p in R.rows(data, S.STAKEHOLDERS):
                if ref in (p.get("Groups") or []) and S.is_active(p) and p["ID"] not in chosen:
                    chosen.append(p["ID"])
        elif ref in people:
            if S.is_active(people[ref]) and ref not in chosen:
                chosen.append(ref)
        else:
            unknown.append(ref)
    field = channel_field(comm.get("Channel"))
    out, missing = [], []
    for sid in chosen:
        p = people[sid]
        card = (contacts or {}).get(sid, {})
        use = field or channel_field(card.get("Preferred channel")) or "Email"
        address = card.get(use) or ""
        if not address and card.get("Preferred channel"):
            alt = channel_field(card.get("Preferred channel"))
            if alt and card.get(alt):
                use, address = alt, card[alt]
        if not address and card.get("Other"):
            use, address = "Other", card["Other"]
        out.append({"ID": sid, "Name": p.get("Name", ""), "Share Level": p.get("Share Level", "owner"),
                    "Field": use, "Address": address})
        if not address and contacts is not None and comm.get("Mode") != "pull":
            missing.append("%s %s" % (sid, p.get("Name", "")))
    level = "external" if any(x["Share Level"] == "external" for x in out) else "owner"
    return {"people": out, "missing": missing, "unknown": unknown,
            "share_level": level, "public": is_content(comm)}


# --- content pointers ------------------------------------------------------------------

def content_root(register_path):
    """The nearest content-system/strategies/ at or above the register's folder,
    where the content system keeps its strategies; None when there is none."""
    here = os.path.dirname(os.path.abspath(register_path))
    while True:
        strategies = os.path.join(here, "content-system", "strategies")
        if os.path.isdir(strategies):
            return strategies
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def content_plan_exists(strategies, channel):
    """True/False for a `content: <scope> › <plan>` channel; None when unparsable
    or there is no content system to look in. The content system is never written."""
    text = S.clean(channel)[len("content:"):].strip()
    parts = re.split(r"\s*(?:›|>)\s*", text, maxsplit=1)
    if len(parts) != 2 or not strategies:
        return None
    scope, plan = parts
    files = glob.glob(os.path.join(strategies, "**", *scope.split("/")) + ".md", recursive=True)
    if not files:
        return False
    with io.open(files[0], encoding="utf-8") as fh:
        body = fh.read()
    return re.search(r"^## Plan:\s*%s\s*$" % re.escape(plan), body, re.M | re.I) is not None


# --- the audit -------------------------------------------------------------------------

def check(data, register_path=None):
    """[(severity, item, message)] for one project: the register and its contacts."""
    found = []
    add = lambda sev, item, msg: found.append((sev, item, msg))
    seen = set()
    for coll in (S.GROUPS, S.STAKEHOLDERS, S.COMMS):
        for row in R.rows(data, coll):
            rid = row.get("ID")
            p = S.parse_id(rid)
            if not p or p[0] != S.PREFIX[coll] or rid != S.norm_id(rid):
                add("error", rid, "ID must be %s.<n>" % S.PREFIX[coll])
            elif rid in seen:
                add("error", rid, "duplicate ID")
            seen.add(rid)
            if row.get("Status") and row["Status"] not in S.vocabulary(data, "status"):
                add("error", rid, "Status %r not in vocabulary" % row["Status"])

    groups = dict((g["ID"], g) for g in R.rows(data, S.GROUPS) if g.get("ID"))
    people = dict((p["ID"], p) for p in R.rows(data, S.STAKEHOLDERS) if p.get("ID"))

    for p in people.values():
        sid = p["ID"]
        if not S.clean(p.get("Name")):
            add("error", sid, "no Name")
        for field, vocab in (("Power", "level"), ("Interest", "level"), ("Current", "engagement"),
                             ("Desired", "engagement"), ("Share Level", "share_level")):
            if p.get(field) and p[field] not in S.vocabulary(data, vocab):
                add("error", sid, "%s %r not in vocabulary" % (field, p[field]))
        for g in p.get("Groups") or []:
            if g not in groups:
                add("error", sid, "in group %s, which does not exist" % g)
            elif not S.is_active(groups[g]) and S.is_active(p):
                add("warning", sid, "in group %s, which is Inactive" % g)
        if S.is_active(p):
            for field in ("Power", "Interest", "Current", "Desired"):
                if not p.get(field):
                    add("warning", sid, "no %s" % field)
            if S.gap(p, data) and not S.clean(p.get("Engagement Action")):
                add("warning", sid, "%s, wanted %s, and no Engagement Action"
                    % (p.get("Current"), p.get("Desired")))

    for g in groups.values():
        if S.is_active(g) and not any(g["ID"] in (p.get("Groups") or []) and S.is_active(p)
                                      for p in people.values()):
            add("warning", g["ID"], "no active members")

    contacts, _, has_file = ({}, [], False)
    if register_path:
        contacts, _, has_file = read_contacts(contacts_path(register_path, data))
        active = [p for p in people.values() if S.is_active(p)]
        if active and not has_file:
            add("warning", "", "no contacts file beside the register")
        if has_file:
            state = git_state(contacts_path(register_path, data))
            if state == "tracked":
                add("error", "", "the contacts file is tracked by git: `git rm --cached` it, "
                    "and add `Contacts *.csv` to .gitignore")
            elif state == "unignored":
                add("warning", "", "the contacts file is not ignored by git: add `Contacts *.csv` "
                    "to .gitignore")
            for p in active:
                if p["ID"] not in contacts:
                    add("warning", p["ID"], "no row in the contacts file")
            for sid in contacts:
                if sid not in people:
                    add("warning", sid, "contacts row with no stakeholder")

    strategies = content_root(register_path) if register_path else None
    unchecked = False
    for c in R.rows(data, S.COMMS):
        cid = c.get("ID")
        for field, vocab in (("Mode", "mode"), ("Report", "report")):
            if c.get(field) and c[field] not in S.vocabulary(data, vocab):
                add("error", cid, "%s %r not in vocabulary" % (field, c[field]))
        if c.get("Cadence") and S.cadence_kind(c["Cadence"]) not in S.vocabulary(data, "cadence"):
            add("error", cid, "Cadence %r not in vocabulary" % c["Cadence"])
        if c.get("Last Done"):
            try:
                dt.date.fromisoformat(c["Last Done"])
            except ValueError:
                add("error", cid, "Last Done %r is not YYYY-MM-DD" % c["Last Done"])
        if not S.is_active(c):
            continue
        if not S.clean(c.get("Cadence")):
            add("warning", cid, "no Cadence")
        if is_content(c):
            ok = content_plan_exists(strategies, c.get("Channel"))
            if ok is False:
                add("warning", cid, "content plan not found: %s" % c.get("Channel"))
            elif ok is None and not strategies:
                unchecked = True
            continue
        if not c.get("Audience"):
            add("error", cid, "no Audience")
            continue
        res = resolve_audience(data, c, contacts if has_file else None)
        for ref in res["unknown"]:
            add("error", cid, "Audience names %s, which does not exist" % ref)
        for ref in c.get("Audience") or []:
            row = groups.get(ref) or people.get(ref)
            if row and not S.is_active(row):
                add("warning", cid, "Audience names %s, which is Inactive" % ref)
        if not res["people"] and not res["unknown"]:
            add("warning", cid, "the audience resolves to nobody")
        for who in res["missing"]:
            add("warning", cid, "no address for %s" % who)
    if unchecked:
        add("note", "", "content pointers not checked: no content-system/ at or above the register")
    return found


def check_all(root):
    """The same person with different details in two projects' contacts files.
    Named, never fixed: the owner settles it."""
    by_key = {}
    for reg in all_registers(root):
        data = R.load(reg)
        scope = data["meta"].get("scope", "")
        contacts, _, _ = read_contacts(contacts_path(reg, data))
        for sid, row in contacts.items():
            for key in (("email", row.get("Email", "").lower()),
                        ("name", re.sub(r"\s+", " ", row.get("Name", "")).strip().casefold())):
                if key[1]:
                    by_key.setdefault(key, []).append((scope, sid, row))
    found, reported = [], set()
    for (kind, value), hits in sorted(by_key.items()):
        if len(set(h[0] for h in hits)) < 2:
            continue
        for col in ("Name", "Email", "Phone", "Other", "Organisation"):
            values = set(h[2].get(col, "") for h in hits if h[2].get(col, ""))
            if len(values) > 1:
                where = ", ".join("%s %s" % (h[0], h[1]) for h in hits)
                note = (where, col)
                if note not in reported:
                    reported.add(note)
                    found.append(("warning", hits[0][2].get("Name", value),
                                  "%s differs across %s" % (col, where)))
    return found
