#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Change requests: anyone drafts, the product manager processes (TSP.18 Change Requests).

    python cr.py draft  <project> --type risk --what "..." --why "..." [--impact "..."] [--affects "WBS 12, RAID 3"] --by "Name"
    python cr.py lookup <project> <words...>          # WBS rows and RAID entries a request may affect, read-only
    python cr.py list   <project> [--all]             # the open requests (--all: the processed ones too)
    python cr.py close  <project> <request> --accepted "as RAID 14" | --declined "why" --by "Name"

<project> is the project's root or its planning folder. Requests live in the
planning folder's Change Requests folder, one Markdown file each; an open one
sits at the top, a processed one in Processed/ with its outcome written on it.
The registers are read, never written: a request becomes a RAID entry or a WBS
change through the skills that keep them.

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

PLANNING = re.compile(r"^(\d+[.\s]\s*)?PrjMgm$", re.I)
FOLDER = re.compile(r"^(\d+[.\s]\s*)?Change Requests$", re.I)
TYPES = ["risk", "issue", "decision", "change", "new work", "idea"]
SKIP = {".git", ".agents", ".claude", ".github", "PreviousV", "Archive", "__pycache__", "Processed"}


# ─── Finding things: the default convention first, then what the project
#     records (the artifact register says which tool governs which folder),
#     then a search by name. Never by assuming how deep a folder sits.

def project_root(project):
    """The project: the folder given, or the one above it when given the planning folder."""
    project = os.path.abspath(project)
    return os.path.dirname(project) if PLANNING.match(os.path.basename(project)) else project


def walk(root):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith("."))
        yield dirpath, dirs, files


def registers(root, kinds):
    """{kind: [(path, data)]} for the registers of these kinds anywhere in the project."""
    out = {}
    for dirpath, _, files in walk(root):
        for name in sorted(files):
            if name.endswith(".json"):
                try:
                    with io.open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                        data = json.load(fh)
                except (OSError, ValueError):
                    continue
                kind = (data.get("meta") or {}).get("kind") if isinstance(data, dict) else None
                if kind in kinds:
                    out.setdefault(kind, []).append((os.path.join(dirpath, name), data))
    return out


def delegated_folder(root, skill):
    """The folder the artifact register says this skill's tool governs (Managed By),
    the tool found in the project's tool register by its Skill column."""
    regs = registers(root, {"tsp-register", "artifact-register"})
    tool_ids = set()
    for _, data in regs.get("tsp-register", []):
        for r in data.get("tools", []):
            if skill in [s.strip() for s in str(r.get("Skill") or "").split(",")]:
                tool_ids.add(str(r.get("ID")))
    folder_ids = set()
    for _, data in regs.get("artifact-register", []):
        for r in data.get("artifacts", []):
            m = re.match(r"^[A-Z]+\.(\d+)$", str(r.get("Managed By") or "").strip())
            if m and m.group(1) in tool_ids and r.get("Type") == "Folder" and r.get("Status") != "Retired":
                folder_ids.add(str(r.get("ID")))
    for dirpath, dirs, _ in walk(root):
        for d in dirs:
            m = re.match(r"^(\d+)\.", d)
            if m and str(int(m.group(1))) in folder_ids:
                return os.path.join(dirpath, d)
    return None


def requests_folder(project):
    root = project_root(project)
    plans = [root] if PLANNING.match(os.path.basename(root)) else \
        [os.path.join(root, n) for n in sorted(os.listdir(root)) if PLANNING.match(n) and os.path.isdir(os.path.join(root, n))]
    for plan in plans:                                     # 1. the default convention
        for name in sorted(os.listdir(plan)):
            if FOLDER.match(name) and os.path.isdir(os.path.join(plan, name)):
                return os.path.join(plan, name)
    found = delegated_folder(root, "change-request")       # 2. what the project records
    if found:
        return found
    for dirpath, dirs, _ in walk(root):                    # 3. by name, anywhere
        for d in dirs:
            if FOLDER.match(d):
                return os.path.join(dirpath, d)
    sys.exit("No Change Requests folder in %s. The convention: a 'Change Requests' folder in the project-management folder "
             "(the project pack sets one up); or one the artifact register says this tool manages." % root)


def slug(text):
    words = re.findall(r"[A-Za-z0-9]+", text or "")[:6]
    return " ".join(words) or "request"


def parse(path):
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    field = lambda k: (re.search(r"\*\*%s:\*\*\s*([^·\n]+)" % re.escape(k), text) or [None, ""])[1].strip()
    what = re.search(r"^## What\s*\n+(.+)$", text, re.M)
    return {"file": os.path.basename(path), "type": field("Type"), "by": field("Requested by"), "on": field("On"),
            "what": what.group(1).strip() if what else ""}


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_draft(args):
    folder = requests_folder(args.project)
    today = args.on or date.today().isoformat()
    name = "CR %s %s.md" % (today, slug(args.what))
    path = os.path.join(folder, name)
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, "CR %s %s (%d).md" % (today, slug(args.what), n))
        n += 1
    body = ["# Change request: %s" % args.what.rstrip("."), "",
            "**Type:** %s · **Requested by:** %s · **On:** %s" % (args.type, args.by, today), "",
            "## What", "", args.what, "", "## Why", "", args.why or "", "",
            "## Impact", "", args.impact or "Not said.", "", "## Affects", "", args.affects or "Nothing named.", ""]
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(body))
    print("Drafted %s" % os.path.relpath(path, project_root(args.project)))
    print("The product manager picks it up at the weekly review.")
    return 0


def cmd_lookup(args):
    words = [w.lower() for w in args.words]
    hits = []
    for kind, regs in registers(project_root(args.project), {"wbs-register", "raid-register"}).items():
        for path, data in regs:
            rows = data.get("items") if kind == "wbs-register" else data.get("entries")
            for r in rows or []:
                text = " ".join(str(r.get(k, "")) for k in ("Title", "Description", "Detail"))
                if all(w in text.lower() for w in words):
                    if kind == "wbs-register":
                        hits.append("WBS %s  %s  [%s]" % (r.get("ID"), r.get("Title", ""), r.get("Status", "")))
                    else:
                        hits.append("RAID %s  %s: %s  [%s]" % (r.get("RAID.ID"), r.get("Type", ""), r.get("Detail", ""), r.get("Status", "")))
    print("\n".join(hits[:20]) if hits else "Nothing matches %s." % " ".join(args.words))
    return 0


def cmd_list(args):
    folder = requests_folder(args.project)
    open_ = [parse(os.path.join(folder, n)) for n in sorted(os.listdir(folder)) if n.endswith(".md") and n.startswith("CR ")]
    print("%d open request(s)" % len(open_))
    for r in open_:
        print("  %s  %-8s %-14s %s" % (r["on"], r["type"], r["by"], r["what"][:70]))
        print("     %s" % r["file"])
    done = os.path.join(folder, "Processed")
    if args.all and os.path.isdir(done):
        closed = sorted(n for n in os.listdir(done) if n.endswith(".md"))
        print("\n%d processed" % len(closed))
        for n in closed:
            print("  %s" % n)
    return 0


def cmd_close(args):
    folder = requests_folder(args.project)
    match = [n for n in os.listdir(folder) if n.endswith(".md") and args.request.lower() in n.lower()]
    if len(match) != 1:
        sys.exit("%s open request(s) match %r: %s" % (len(match), args.request, ", ".join(match) or "none"))
    path = os.path.join(folder, match[0])
    verdict = ("Accepted %s" % args.accepted) if args.accepted else ("Declined: %s" % args.declined)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n## Outcome\n\n%s · %s: %s\n" % (args.on or date.today().isoformat(), args.by, verdict))
    done = os.path.join(folder, "Processed")
    os.makedirs(done, exist_ok=True)
    shutil.move(path, os.path.join(done, match[0]))
    print("%s: %s. Moved to Processed/." % (match[0], verdict))
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Change requests (TSP.18).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("draft", help="write a request, for the product manager to process")
    s.add_argument("project")
    s.add_argument("--type", required=True, choices=TYPES)
    s.add_argument("--what", required=True, help="the change, in a sentence")
    s.add_argument("--why", required=True)
    s.add_argument("--impact", help="what happens if it is done, or not")
    s.add_argument("--affects", help="the WBS rows and RAID entries it touches, by ID (see lookup)")
    s.add_argument("--by", required=True, help="who asks")
    s.add_argument("--on", metavar="YYYY-MM-DD")
    s.set_defaults(fn=cmd_draft)
    s = sub.add_parser("lookup", help="WBS rows and RAID entries matching every word, read-only")
    s.add_argument("project"); s.add_argument("words", nargs="+")
    s.set_defaults(fn=cmd_lookup)
    s = sub.add_parser("list", help="the open requests")
    s.add_argument("project"); s.add_argument("--all", action="store_true", help="the processed ones too")
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("close", help="write the outcome on a request and move it to Processed/")
    s.add_argument("project"); s.add_argument("request", help="part of its file name")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--accepted", metavar="AS", help='e.g. "as RAID 14" or "as WBS 63"')
    g.add_argument("--declined", metavar="WHY")
    s.add_argument("--by", required=True, help="who decided")
    s.add_argument("--on", metavar="YYYY-MM-DD")
    s.set_defaults(fn=cmd_close)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
