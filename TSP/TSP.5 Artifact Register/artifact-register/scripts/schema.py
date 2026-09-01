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


def scan_folder(root, stop_ids=()):
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

    def walk(path, rel_base):
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return
        for name in entries:
            if name.startswith((".", "~$")) or name in SKIP_DIRS or name in SKIP_FILES:
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
