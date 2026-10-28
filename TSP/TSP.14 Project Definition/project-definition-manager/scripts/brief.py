# -*- coding: utf-8 -*-
"""The Project Brief, read and checked in one place (TSP.14 Project Definition).

Every tool that needs a brief reads it through this module: the status report
and the charter (TSP.10 Reporting) and the weekly review's revisit check. The format is
defined here once - the file name, the header line, the sections and the
Measures table - so a change to the template changes one reader.

    python brief.py show  <brief or folder> [--json]
    python brief.py check <brief or folder> [--wbs] [--today YYYY-MM-DD]
    python brief.py new   <PrjMgm folder> --title "Atlas Website" [--size lean|full]

A folder resolves to the brief in it, or in its PrjMgm folder one level down.
Standard library only.
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
from datetime import date

HERE = os.path.dirname(os.path.realpath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "Project Brief.md")

# `Project Brief.md`, or numbered by a project's artifact register (`04. Project Brief.md`).
BRIEF_FILE = re.compile(r"^(\d+\.\s*)?project brief.*\.md$", re.I)
PRJMGM_DIR = re.compile(r"^\d+\.\s*PrjMgm$", re.I)
STATEMENT = re.compile(r"^>\s*\*\*[^*]+\*\*.+\*\*[^*]+\*\*")

MEASURE_COLS = ("ID", "Measure", "Role", "Kind", "C/A", "Baseline", "From", "Target", "By",
                "How measured", "Every", "Current", "As of", "Source", "WBS")
ROLES, KINDS, CA, SOURCES = ("lag", "lead"), ("H", "M", "N"), ("C", "A"), ("measured", "estimated", "asked")
EVERY_DAYS = {"week": 7, "sprint": 14, "month": 31, "quarter": 92, "year": 366}
SIZES = ("lean", "full")
# A brief not revised for this long is due a revisit: the outcome, Stop if,
# what it serves and its size are asked again (TD.14).
REVISIT_DAYS = 31


# ─── Finding the brief ───────────────────────────────────────────────────────

def is_brief(name):
    return bool(BRIEF_FILE.match(name))


def find(folder):
    """The brief in this folder, or None. Never searches below it."""
    if not folder or not os.path.isdir(folder):
        return None
    hits = sorted(n for n in os.listdir(folder) if is_brief(n))
    return os.path.join(folder, hits[0]) if hits else None


def prjmgm_of(project_dir):
    """A project's PrjMgm folder one level down (`0. PrjMgm`, `00. PrjMgm`, `0.PrjMgm`)."""
    if not project_dir or not os.path.isdir(project_dir):
        return None
    hits = sorted(n for n in os.listdir(project_dir)
                  if PRJMGM_DIR.match(n) and os.path.isdir(os.path.join(project_dir, n)))
    return os.path.join(project_dir, hits[0]) if hits else None


def resolve(path):
    """A brief's path from a file, a PrjMgm folder or a project folder."""
    if os.path.isfile(path):
        return path
    return find(path) or find(prjmgm_of(path))


# ─── Reading it ──────────────────────────────────────────────────────────────

def _placeholder(value):
    """A template prompt left as written: `<...>`, or a lone ellipsis."""
    return bool(re.search(r"<[^>]+>", value or "")) or (value or "").strip() in ("…", "...")


def _header_field(lines, name):
    """A header-line field, read above the first section; None for a prompt."""
    for line in lines:
        if line.startswith("## "):
            break
        m = re.search(r"\*\*%s:\*\*\s*([^·\n]+)" % re.escape(name), line)
        if m:
            value = m.group(1).strip()
            return None if not value or _placeholder(value) else value
    return None


def parse(text):
    """Everything a reader takes from a brief, as written.

    statement   the executive statement (To ... so that ...), or None
    outcome     the outcome sentence: the first plain line under Outcome and done-when
    done_when   the numbered items under it
    stop_if     the Stop if line
    size, written, last_revised, serves   from the header line
    header, rows   the Measures table: its column names and its rows as dicts
    """
    lines = text.split("\n")
    # The statement is the quoted line with its two halves in bold, in whatever
    # language the brief is written: **To** ... **so that**, **Para** ... **para que**.
    statement = next((l.lstrip("> ").replace("**", "").strip() for l in lines
                      if STATEMENT.match(l)), None)
    statement = None if _placeholder(statement) else statement
    stop = re.search(r"\*\*Stop if:\*\*\s*(.+)", text)
    stop = None if not stop or _placeholder(stop.group(1)) else stop.group(1).strip()
    size = (_header_field(lines, "Size") or "").lower() or None
    outcome, done_when, rows, header = None, [], [], None
    sec, listed = None, False
    for line in lines:
        if line.startswith("## "):
            sec = line[3:].strip().lower()
        elif line.startswith("### "):
            sec = line[4:].strip().lower()
        if sec and sec.startswith("outcome") and not line.startswith("#"):
            m = re.match(r"^\d+\.\s+(.*)", line)
            # The outcome sentence comes before the done-when list, never after it.
            listed = listed or bool(m) or line.lower().startswith("done when")
            if outcome is None and not listed and line.strip() \
                    and not line.startswith(("|", ">", "-", "<", "**")):
                outcome = line.strip()
            if m and not _placeholder(m.group(1)):
                done_when.append(m.group(1).strip())
        if sec == "measures" and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
            elif not set(line.replace("|", "").strip()) <= set("-: "):
                rows.append(dict(zip(header, cells)))
    return {"statement": statement, "outcome": outcome, "done_when": done_when,
            "stop_if": stop,
            "size": size if size in SIZES else size and "unknown",
            "written": _header_field(lines, "Written"),
            "last_revised": _header_field(lines, "Last revised"),
            "serves": _header_field(lines, "Serves"),
            "header": header, "rows": rows}


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        out = parse(fh.read())
    out["path"] = path
    return out


def serves_list(serves):
    """'G-2, B-1' as ['G-2', 'B-1']."""
    return [s.strip() for s in re.split(r"[,;]", serves or "") if s.strip()]


# ─── Checking it ─────────────────────────────────────────────────────────────

def _date(cell):
    try:
        return date.fromisoformat((cell or "").strip())
    except ValueError:
        return None


def measure_findings(row):
    """A measure's vocabulary and dates against the template's rules. Whether
    its values read as numbers is the reporting tool's, which scores them."""
    mid, out = row.get("ID", "?"), []
    for col, vocab in (("Role", ROLES), ("Kind", KINDS), ("C/A", CA), ("Source", SOURCES)):
        if row.get(col) and row.get(col) not in vocab:
            out.append("%s: %s %r is not %s" % (mid, col, row.get(col), " / ".join(vocab)))
    if row.get("Every") and row["Every"] not in EVERY_DAYS:
        out.append("%s: Every %r is not %s" % (mid, row["Every"], " / ".join(EVERY_DAYS)))
    for col in ("From", "By", "As of"):
        if row.get(col) and _date(row[col]) is None:
            out.append("%s: %s %r is not a date (YYYY-MM-DD)" % (mid, col, row[col]))
    return out


def revisit_due(parts, today=None):
    """The revisit finding, or None (TD.14: Revisit)."""
    today = today or date.today()
    last = _date(parts.get("last_revised") or parts.get("written"))
    if last is None:
        return "no Last revised date, so its revisit cannot be judged"
    if (today - last).days > REVISIT_DAYS:
        return "revisit due: last revised %s" % last.isoformat()
    return None


def table_findings(parts):
    """The Measures table's shape: its columns, each row's vocabulary and dates,
    and at least one lag measure. Empty for a brief with no table."""
    if not parts["rows"]:
        return []
    out = []
    missing = [c for c in MEASURE_COLS if c not in (parts["header"] or [])]
    if missing:
        out.append("Measures table lacks %s" % ", ".join(missing))
    for row in parts["rows"]:
        out.extend(measure_findings(row))
    if not any(r.get("Role") == "lag" for r in parts["rows"]):
        out.append("no lag measure: lead measures alone show activity, not value")
    return out


def check(parts, runs_wbs=False, today=None):
    """Findings on a parsed brief, as plain sentences; empty when it is sound.

    runs_wbs: whether the project keeps a WBS register, which makes the full
    size the right one. The caller knows; the brief does not.
    """
    out = []
    size = parts["size"] if parts["size"] in SIZES else None
    if runs_wbs and size != "full":
        out.append("%s, but the project runs a WBS - grow it to full" % (size or "unsized"))
    elif not size:
        out.append("no Size line (lean or full)")
    if not parts["statement"]:
        out.append("no executive statement (To ... so that ...)")
    if not parts["outcome"]:
        out.append("no outcome sentence under Outcome and done-when")
    if not parts["done_when"]:
        out.append("no done-when items")
    if not parts["stop_if"]:
        out.append("no Stop if line")
    if parts["size"] == "full" and not parts["rows"]:
        out.append("full, but no Measures table")
    out.extend(table_findings(parts))
    due = revisit_due(parts, today)
    if due:
        out.append(due)
    return out


# ─── Starting one ────────────────────────────────────────────────────────────

def new(prjmgm, title, size="full", serves=None, today=None):
    """Copy the template into a PrjMgm folder as `Project Brief.md`, its title,
    size and dates filled. Refuses when the folder already has a brief."""
    if not os.path.isdir(prjmgm):
        raise SystemExit("No folder at %s" % prjmgm)
    existing = find(prjmgm)
    if existing:
        raise SystemExit("%s already has a brief: %s" % (prjmgm, os.path.basename(existing)))
    today = (today or date.today()).isoformat()
    with io.open(TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"^# .*? — Project Brief", lambda m: "# %s — Project Brief" % title, text, count=1, flags=re.M)
    text = text.replace("**Size:** full", "**Size:** %s" % size, 1)
    text = text.replace("**Written:** YYYY-MM-DD", "**Written:** %s" % today, 1)
    text = text.replace("**Last revised:** YYYY-MM-DD", "**Last revised:** %s" % today, 1)
    if serves:
        text = text.replace("<the objective or bet this project moves, if any>", serves, 1)
    path = os.path.join(prjmgm, "Project Brief.md")
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _brief_or_exit(target):
    path = resolve(target)
    if not path:
        raise SystemExit("No Project Brief in %s" % target)
    return path


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Read, check and start a Project Brief (TSP.14).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="what readers take from the brief")
    s.add_argument("target")
    s.add_argument("--json", action="store_true")
    c = sub.add_parser("check", help="findings on the brief; exit 1 when there are any")
    c.add_argument("target")
    c.add_argument("--wbs", action="store_true", help="the project keeps a WBS register")
    c.add_argument("--today", type=date.fromisoformat)
    n = sub.add_parser("new", help="start a brief from the template")
    n.add_argument("prjmgm")
    n.add_argument("--title", required=True, help='the project name, e.g. "Atlas Website"')
    n.add_argument("--size", choices=SIZES, default="full")
    n.add_argument("--serves")
    args = ap.parse_args(argv)

    if args.cmd == "new":
        print("Written %s - fill Why, Outcome and done-when and Stop if with the owner, "
              "then the executive statement." % new(args.prjmgm, args.title, args.size, args.serves))
        return 0
    path = _brief_or_exit(args.target)
    parts = read(path)
    if args.cmd == "show":
        if args.json:
            print(json.dumps(parts, ensure_ascii=False, indent=1))
            return 0
        print("  %s (%s, last revised %s)" % (path, parts["size"] or "unsized", parts["last_revised"] or "-"))
        for label, key in (("Statement", "statement"), ("Outcome", "outcome"), ("Serves", "serves"),
                           ("Stop if", "stop_if")):
            print("  %-9s %s" % (label + ":", parts[key] or "-"))
        for i, item in enumerate(parts["done_when"], 1):
            print("  %d. %s" % (i, item))
        print("  Measures: %d" % len(parts["rows"]))
        return 0
    found = check(parts, runs_wbs=args.wbs, today=args.today)
    for f in found:
        print("  ! %s" % f)
    if not found:
        print("  The brief is sound.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
