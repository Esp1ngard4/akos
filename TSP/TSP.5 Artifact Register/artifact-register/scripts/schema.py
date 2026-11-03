# -*- coding: utf-8 -*-
"""Artifact Register schema, and the filesystem convention it rests on.

The register is JSON - see `registry.py` for the envelope. This module holds what
is specific to artifacts: the fields, the vocabularies, and how to read a folder
through the ID convention.
"""
import os
import re

KIND = "artifact-register"

FIELDS = [
    "ID", "Name", "Description", "Type", "Location",
    "Parent Digital", "Parent Physical", "Managed By", "Area of Focus",
    "Owner", "Created On", "Status", "Last Reviewed", "Comments",
]

TYPES = ["Folder", "Document", "Tool", "Item"]
STATUSES = ["Active", "Retired"]
KINDS = ["Physical", "Digital"]
ROOT_PARENT = "Main"
NO_PARENT = "N/A"
TOOL_PREFIX = "TSP."

# Zero-padded so lexicographic order matches numeric order. Sorting differs by
# platform - Explorer sorts naturally (1, 2, 10), web clients and `ls` do not
# (1, 10, 2) - so padding makes a folder read the same everywhere. Stored per
# register rather than derived, so adding artifact 100 never silently re-pads
# everything below it.
ID_WIDTH_DEFAULT = 2

# "12. Insurance", "12.Insurance", "12 Insurance" - the ID written onto the file
ID_PREFIX = re.compile(r"^(\d+)[.\s]")

SKIP_DIRS = {"PreviousV", ".git", "__pycache__"}
# Generated views, not artifacts. Regenerated on every refresh, so registering
# them would be registering a derived picture of the register itself.
SKIP_FILES = ("Artifact Dashboard.html", "WBS Dashboard.html",
              "RAID Dashboard.html", "TSP Dashboard.html")


def format_id(value, width):
    """`7` -> `07`. Never truncates: an ID wider than the setting prints in full."""
    text = str(value).strip()
    return text.zfill(width) if text.isdigit() else text


def clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in ("-", NO_PARENT, "") else text


def parent_of(row):
    """(digital, physical) parent ids as strings; '' where there is none."""
    return clean(row.get("Parent Digital")), clean(row.get("Parent Physical"))


def scan_folder(root, stop_ids=(), ignore=()):
    """Walk the folder a register describes and split it by the ID convention.

    Returns ({id: [relative paths]}, [unprefixed relative paths]).

    Descent obeys the delegation rule, because the disk has to be read the same
    way the register is written:

    - a directory whose ID is in `stop_ids` is recorded and **not entered** -
      another tool governs its contents, so they are not this register's to
      inventory;
    - an unprefixed directory is reported once and not entered, so one
      unregistered folder yields one finding rather than one per file inside it;
    - everything else is descended into, since a registered container's contents
      are themselves registered artifacts.
    """
    prefixed, bare = {}, []
    if not root or not os.path.isdir(root):
        return prefixed, bare
    stop = set(str(s) for s in stop_ids)
    # Files a tool owns and names itself (an installer's lock), listed in the
    # register's settings: skipped wherever they sit, never a way to hide a document.
    skip = set(ignore or ())

    def walk(path, rel_base):
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return
        for name in entries:
            if name.startswith((".", "~$")) or name in SKIP_DIRS or name in SKIP_FILES or name in skip:
                continue
            full = os.path.join(path, name)
            rel = "%s/%s" % (rel_base, name) if rel_base else name
            match = ID_PREFIX.match(name)
            if match:
                key = str(int(match.group(1)))   # `07.` and `7.` are one artifact
                prefixed.setdefault(key, []).append(rel)
                if os.path.isdir(full) and key not in stop:
                    walk(full, rel)
            else:
                bare.append(rel)          # reported once; not descended into

    walk(root, "")
    return prefixed, bare


def stop_ids(rows, empty=True):
    """IDs a disk scan must not descend into - the delegation rule, applied to
    the filesystem: a row another tool manages, a tool, and with `empty` a row
    nothing sits in. Looking for a misfiled artifact wants `empty=False`: it may
    be in a folder the register thinks is empty."""
    claimed = set()
    for row in rows:
        claimed.update(p for p in parent_of(row) if p and p != ROOT_PARENT)
    stop = set()
    for row in rows:
        rid = clean(row.get("ID"))
        if (clean(row.get("Managed By")) or clean(row.get("Type")) == "Tool"
                or (empty and rid not in claimed)):
            stop.add(rid)
    return stop


# --- where the scope is, and where an artifact sits in it --------------------

def root_of(register, data):
    """(absolute root, problem) from `meta.settings.root`, which is relative to
    the register's own folder. (None, None) when the register records none."""
    rel = ((data.get("meta") or {}).get("settings") or {}).get("root")
    if not rel:
        return None, None
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(register)),
                                         rel.replace("/", os.sep)))
    if not os.path.isdir(path):
        return None, "the register's root %r is not a folder (%s)" % (rel, path)
    return path, None


def relative_root(register, folder):
    """`folder` as the register stores it: from the register's folder, forward slashes."""
    rel = os.path.relpath(os.path.abspath(folder), os.path.dirname(os.path.abspath(register)))
    return rel.replace(os.sep, "/")


def chain(rows, artifact_id):
    """The Parent Digital chain from the top down to the row, as ID strings.
    Raises ValueError saying why when the row has no digital home."""
    by_id = dict((clean(r.get("ID")), r) for r in rows)
    out, cur = [], by_id.get(str(artifact_id))
    if cur is None:
        raise ValueError("no artifact with ID %s in this register" % artifact_id)
    while True:
        rid = clean(cur.get("ID"))
        if rid in out:
            raise ValueError("ID %s sits inside itself (a Parent Digital cycle)" % rid)
        out.insert(0, rid)
        parent, _ = parent_of(cur)
        if parent == ROOT_PARENT:
            return out
        if not parent:
            raise ValueError("ID %s has no digital home (Parent Digital N/A)" % rid
                             if rid == str(artifact_id) else
                             "ID %s sits in ID %s, which has no digital home" % (artifact_id, rid))
        cur = by_id.get(parent)
        if cur is None:
            raise ValueError("ID %s sits in ID %s, which is not in the register" % (rid, parent))


def resolve(root, rows, artifact_id):
    """Walk the row's chain down from `root`, one ID prefix per level - the
    register's claim, not a search. Returns the absolute path; raises ValueError
    naming the deepest folder reached and what was missing there."""
    path = root
    for rid in chain(rows, artifact_id):
        hits = []
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            entries = []
        for name in entries:
            match = ID_PREFIX.match(name)
            if match and str(int(match.group(1))) == rid and not name.startswith(("~$", ".")):
                hits.append(name)
        where = os.path.relpath(path, root).replace(os.sep, "/")
        where = "the root" if where == "." else where
        if not hits:
            raise ValueError("nothing prefixed %s in %s" % (rid, where))
        if len(hits) > 1:
            raise ValueError("%d entries prefixed %s in %s: %s"
                             % (len(hits), rid, where, ", ".join(hits)))
        path = os.path.join(path, hits[0])
        if rid != str(artifact_id) and not os.path.isdir(path):
            raise ValueError("%s is a file, but ID %s sits inside it" % (hits[0], artifact_id))
    return path
