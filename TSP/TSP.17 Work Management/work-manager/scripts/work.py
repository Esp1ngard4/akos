#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A project's work items: their folders and documents (TSP.17 Work Management).

    python work.py start  <project> --id 12 --size medium          # the documents its size calls for
    python work.py add    <project> --id 12 --stage discovery --subject "Vendor survey" [--subfolder]
    python work.py file   <project> --id 12 <file> [--deliverable]
    python work.py next   <project> --id 12                         # what exists, by stage, and the next stage
    python work.py where  <project> --id 12                         # the work item's folder

<project> is the project's root or its planning folder: the WBS is found by its
meta.kind, and the Execution folder where the WBS declares it (meta.execution),
else beside the planning folder. The WBS is read, never written.

A stage holds as many documents as the work needs: the first is named for the
stage (`WP12 Title - Discovery.md`), the others by their subject
(`WP12 Title - Discovery - Vendor survey.md`), and a stage with many may keep
them in a subfolder of its own (`Discovery/`).

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
SKILL = os.path.dirname(HERE)
TEMPLATES = os.path.join(SKILL, "templates")
STAGE_GUIDES = os.path.join(SKILL, "references", "stages")
SKIP = {".git", ".agents", ".claude", ".github", "PreviousV", "Archive", "__pycache__"}
EXECUTION = re.compile(r"^(\d+[.\s]\s*)?Execution$")
# A stage, and the document type that carries it.
STAGES = [("discovery", "Discovery"), ("specification", "Specification"), ("plan", "Plan"), ("implement", "Notes")]
DOC_STAGE = {doc: stage for stage, doc in STAGES}
TYPES = ["Discovery", "Specification", "Plan", "Notes", "Assessment", "Input"]
SIZES = {"small": ["implement"], "medium": ["specification"], "large": ["discovery", "specification", "plan", "implement"]}
ORDER = ["small", "medium", "large"]


# ─── Finding things ──────────────────────────────────────────────────────────

def find_wbs(project):
    for root, dirs, files in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith("."))
        for name in sorted(files):
            if name.endswith(".json"):
                try:
                    with io.open(os.path.join(root, name), encoding="utf-8") as fh:
                        data = json.load(fh)
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict) and (data.get("meta") or {}).get("kind") == "wbs-register":
                    return os.path.join(root, name), data
    sys.exit("No WBS register under %s." % project)


def execution_folder(project, wbs_path, wbs):
    declared = ((wbs.get("meta") or {}).get("execution") or {}).get("folder")
    if declared:
        path = os.path.normpath(os.path.join(os.path.dirname(wbs_path), declared))
        if os.path.isdir(path):
            return path
    for base in (project, os.path.dirname(os.path.abspath(project))):
        for name in sorted(os.listdir(base)):
            if EXECUTION.match(name) and os.path.isdir(os.path.join(base, name)):
                return os.path.join(base, name)
    sys.exit("No Execution folder found: declare it in the WBS (meta.execution.folder) or create one.")


def row(wbs, rid):
    r = next((x for x in wbs.get("items", []) if str(x.get("ID")) == str(rid)), None)
    if not r:
        sys.exit("No row %s in the WBS." % rid)
    return r


def safe(text):
    """Text as part of a file name: a colon reads as a dash, other unsafe characters go."""
    t = re.sub(r"\s*:\s*", " - ", (text or "").strip())
    t = re.sub(r'[\\/*?"<>|]+', "-", t)
    return re.sub(r"\s+", " ", t)[:60].rstrip(" .-")


def item_folder(execution, rid):
    """The work item's own folder, if it has one: WP.<ID> <Title>."""
    for name in sorted(os.listdir(execution)):
        if re.match(r"^WP\.%s(\s|$)" % re.escape(str(rid)), name) and os.path.isdir(os.path.join(execution, name)):
            return os.path.join(execution, name)
    return None


def locate(execution, wbs, r, own=False):
    """Where a work item's documents go: its own folder if it has one; a Story's or
    a Task's, flat in its parent's folder while that has one (flat until it isn't);
    otherwise its own folder, to be created. Returns (folder, exists)."""
    mine = item_folder(execution, r["ID"])
    if mine:
        return mine, True
    if not own and r.get("Type") in ("Story", "Task") and r.get("Parent") is not None:
        parent = item_folder(execution, r["Parent"])
        if parent:
            return parent, True
    return os.path.join(execution, "WP.%s %s" % (r["ID"], safe(r.get("Title")))), False


def context(args):
    project = os.path.abspath(args.project)
    wbs_path, wbs = find_wbs(project)
    return project, wbs, execution_folder(project, wbs_path, wbs)


# ─── The documents ───────────────────────────────────────────────────────────

def render(doc, r, size, today, subject=""):
    with io.open(os.path.join(TEMPLATES, "%s.md" % doc), encoding="utf-8") as fh:
        text = fh.read()
    header = "**%s:** ID %s · **Written:** %s · **Size:** %s" % (r.get("Type") or "Item", r["ID"], today, size)
    plan = ("## Plan\n\n<!-- For medium work the plan is a checklist here, agreed before building starts. -->\n\n- [ ] \n"
            if doc == "Specification" and size == "medium" and not subject else "")
    return text.format(id=r["ID"], title=r.get("Title", ""), header=header, date=today, plan=plan,
                       subject=": %s" % subject if subject else "")


def doc_name(r, doc, subject=""):
    return "WP%s %s - %s%s.md" % (r["ID"], safe(r.get("Title")), doc, " - %s" % safe(subject) if subject else "")


def present(folder, rid):
    """{document type: [(path, subject)]} of this work item's documents: in the folder
    (a parent's holds its stories' too, each prefixed with its own ID) and in any
    stage subfolder of it."""
    out = {}
    if not folder or not os.path.isdir(folder):
        return out
    pattern = re.compile(r"^WP%s .* - (%s)(?: - (.+))?\.md$" % (re.escape(str(rid)), "|".join(TYPES)))
    places = [folder] + [os.path.join(folder, d) for d in sorted(os.listdir(folder))
                         if d in TYPES + [s.capitalize() for s, _ in STAGES] and os.path.isdir(os.path.join(folder, d))]
    for place in places:
        for name in sorted(os.listdir(place)):
            m = pattern.match(name)
            if m:
                out.setdefault(m.group(1), []).append((os.path.join(place, name), m.group(2) or ""))
    return out


def size_of(docs):
    """The largest size any document was started at: work moves up a size, never down."""
    found = []
    for paths in docs.values():
        for path, _ in paths:
            with io.open(path, encoding="utf-8") as fh:
                m = re.search(r"\*\*Size:\*\*\s*(small|medium|large)", fh.read(2000), re.I)
            if m:
                found.append(m.group(1).lower())
    return max(found, key=ORDER.index) if found else None


def written(path, doc, r, subject=""):
    """Whether a document holds more than its template: one never touched does not count."""
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"\*\*Written:\*\*\s*(\S+)\s*·\s*\*\*Size:\*\*\s*(\w+)", text)
    if not m or not os.path.isfile(os.path.join(TEMPLATES, "%s.md" % doc)):
        return True
    blank = render(doc, r, m.group(2).lower(), m.group(1), subject)
    squash = lambda s: re.sub(r"\s+", " ", s).strip()
    return squash(text) != squash(blank)


def started(docs, r):
    """The stages with at least one document written."""
    return {DOC_STAGE[doc] for doc, paths in docs.items() if doc in DOC_STAGE
            and any(written(p, doc, r, s) for p, s in paths)}


def next_stage(size, docs, r):
    """The first stage its size calls for that no written document covers yet."""
    done = started(docs, r)
    for stage in SIZES[size if size in SIZES else "large"]:
        if stage == "implement":
            return "implement"
        if stage not in done:
            return stage
    return "implement"


def guideline(stage):
    """A stage's guideline, as written in this copy of the skill."""
    path = os.path.join(STAGE_GUIDES, "%s.md" % stage)
    if not os.path.isfile(path):
        return ""
    with io.open(path, encoding="utf-8") as fh:
        return re.sub(r"^# .*\n+", "", fh.read()).strip()


def write_doc(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_start(args):
    project, wbs, execution = context(args)
    r = row(wbs, args.id)
    today = args.on or date.today().isoformat()
    folder, exists = locate(execution, wbs, r, own=args.own_folder)
    if not exists:
        os.makedirs(folder)
        print("Created %s" % os.path.relpath(folder, project))
    elif not os.path.basename(folder).startswith("WP.%s " % r["ID"]):
        print("Using its parent's folder, %s (a %s's documents sit there until it has about three of its own; --own-folder then)"
              % (os.path.relpath(folder, project), r.get("Type", "row").lower()))
    else:
        print("Using %s" % os.path.relpath(folder, project))
    have = present(folder, r["ID"])
    for stage in SIZES[args.size]:
        doc = dict(STAGES)[stage]
        if doc in have:
            continue                                  # a stage already begun keeps its documents
        path = os.path.join(folder, doc_name(r, doc))
        write_doc(path, render(doc, r, args.size, today))
        print("  + %s" % os.path.basename(path))
    docs = present(folder, r["ID"])
    stage = next_stage(size_of(docs) or args.size, docs, r)
    print("\n%s work. Next: %s." % (args.size.capitalize(), stage.capitalize()))
    return 0


def cmd_add(args):
    """Another document for a stage: research that takes three documents gets three."""
    project, wbs, execution = context(args)
    r = row(wbs, args.id)
    folder, exists = locate(execution, wbs, r)
    docs = present(folder, r["ID"]) if exists else {}
    if not docs:
        sys.exit("WP.%s has not been started: start it first, with a size." % r["ID"])
    doc = dict(STAGES)[args.stage]
    place = os.path.join(folder, args.stage.capitalize()) if args.subfolder else folder
    if not args.subfolder and os.path.isdir(os.path.join(folder, args.stage.capitalize())):
        place = os.path.join(folder, args.stage.capitalize())      # the stage keeps its documents together
    os.makedirs(place, exist_ok=True)
    path = os.path.join(place, doc_name(r, doc, args.subject))
    if os.path.exists(path):
        sys.exit("%s exists already." % os.path.relpath(path, project))
    write_doc(path, render(doc, r, size_of(docs) or "large", args.on or date.today().isoformat(), args.subject))
    print("Added %s" % os.path.relpath(path, project))
    return 0


def cmd_file(args):
    project, wbs, execution = context(args)
    r = row(wbs, args.id)
    folder, exists = locate(execution, wbs, r)
    if not exists:
        sys.exit("WP.%s has no folder yet: start it first (work.py start --id %s --size ...)." % (r["ID"], r["ID"]))
    if not os.path.isfile(args.file):
        sys.exit("No file at %s." % args.file)
    dest_dir = os.path.join(folder, "Deliverables" if args.deliverable else "Inputs")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(args.file))
    if os.path.exists(dest):
        sys.exit("%s is already there; rename it to keep both." % os.path.relpath(dest, project))
    shutil.copy2(args.file, dest)
    print("Filed %s" % os.path.relpath(dest, project))
    return 0


def cmd_next(args):
    project, wbs, execution = context(args)
    r = row(wbs, args.id)
    folder, exists = locate(execution, wbs, r)
    docs = present(folder, r["ID"]) if exists else {}
    if not docs:
        print("WP.%s %s has not been started. Start it, with a size: small, medium or large." % (r["ID"], r.get("Title", "")))
        return 0
    size = size_of(docs) or "unsized"
    print("WP.%s %s (%s)" % (r["ID"], r.get("Title", ""), size))
    for stage, doc in STAGES + [(t.lower(), t) for t in ("Assessment", "Input")]:
        for path, subject in docs.get(doc, []):
            state = "written" if written(path, doc, r, subject) else "not started"
            print("  %-13s %s  (%s)" % (stage, os.path.relpath(path, folder), state))
    for extra in ("Inputs", "Deliverables"):
        if os.path.isdir(os.path.join(folder, extra)):
            print("  %-13s %d file(s)" % (extra.lower(), len(os.listdir(os.path.join(folder, extra)))))
    stage = next_stage(size, docs, r)
    print("\nNext: %s.\n\n%s" % (stage.capitalize(), guideline(stage)))
    return 0


def cmd_where(args):
    project, wbs, execution = context(args)
    r = row(wbs, args.id)
    folder, exists = locate(execution, wbs, r)
    print(folder if exists else "WP.%s has no folder yet." % r["ID"])
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="A project's work items (TSP.17 Work Management).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="the work item's folder, and the documents its size calls for")
    s.add_argument("project"); s.add_argument("--id", required=True)
    s.add_argument("--size", required=True, choices=ORDER, help="the person's call; the agent proposes")
    s.add_argument("--on", metavar="YYYY-MM-DD", help="the date written in the documents (default: today)")
    s.add_argument("--own-folder", action="store_true",
                   help="a folder of its own for a story or task, once it has about three documents (default: its parent's)")
    s.set_defaults(fn=cmd_start)
    s = sub.add_parser("add", help="another document for a stage, named by its subject")
    s.add_argument("project"); s.add_argument("--id", required=True)
    s.add_argument("--stage", required=True, choices=[st for st, _ in STAGES])
    s.add_argument("--subject", required=True, help='what this document is about, e.g. "Vendor survey"')
    s.add_argument("--subfolder", action="store_true", help="keep the stage's documents in a subfolder of its own")
    s.add_argument("--on", metavar="YYYY-MM-DD")
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser("file", help="file a received or delivered file in the work item's folder")
    s.add_argument("project"); s.add_argument("--id", required=True); s.add_argument("file")
    s.add_argument("--deliverable", action="store_true", help="into Deliverables/, frozen as sent (default: Inputs/)")
    s.set_defaults(fn=cmd_file)
    s = sub.add_parser("next", help="what exists, by stage, and the next stage with its guideline")
    s.add_argument("project"); s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_next)
    s = sub.add_parser("where", help="the work item's folder")
    s.add_argument("project"); s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_where)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
