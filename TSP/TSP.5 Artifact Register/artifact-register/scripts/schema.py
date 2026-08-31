# -*- coding: utf-8 -*-
"""Shared schema for the Artifact Register (TSP.5).

Defined once, imported by create/refresh/audit, so the three cannot disagree
about what a register looks like.
"""
import os
import re

COLUMNS = [
    "ID", "Name", "Description", "Type", "Location",
    "Parent Digital", "Parent Physical", "Managed By", "Area of Focus",
    "Owner", "Created On", "Status", "Last Reviewed", "Comments",
]

TYPES = ["Folder", "Document", "Tool", "Item"]
STATUSES = ["Active", "Retired"]
KINDS = ["Physical", "Digital"]
# How a tool is referenced in `Managed By`. Change this one constant if your
# tool register numbers things differently.
TOOL_PREFIX = "TSP."

ROOT_PARENT = "Main"
NO_PARENT = "N/A"

HEADER_ROW = 6          # for registers this tool creates
TITLE_ROW = 2
SHEET = "Artifacts"
LOOKUP_LOCATIONS = "Locations"
LOOKUP_AREAS = "Areas of Focus"

# "12. Insurance", "12.Insurance", "12 Insurance" - the ID written onto the file
ID_PREFIX = re.compile(r"^(\d+)[.\s]")


def find_header(ws):
    """Locate the header row and build {column name: index}.

    Registers built before this tool put headers on row 5 with a blank column A;
    ones it creates use row 6 from column A. Detect rather than assume.
    """
    for row in range(1, min(ws.max_row, 12) + 1):
        names = {}
        for col in range(1, ws.max_column + 1):
            val = ws.cell(row, col).value
            if isinstance(val, str) and val.strip():
                names[val.strip()] = col
        if "ID" in names and "Name" in names:
            return row, names
    raise SystemExit("No header row found - expected a row containing 'ID' and 'Name'.")


def read_rows(ws, header_row, cols):
    """Every populated row as a dict, plus its sheet row number."""
    out = []
    for r in range(header_row + 1, ws.max_row + 1):
        if ws.cell(r, cols["ID"]).value is None:
            continue
        rec = dict((name, ws.cell(r, idx).value) for name, idx in cols.items())
        rec["_row"] = r
        out.append(rec)
    return out


def clean(value):
    """Normalize a cell to a stripped string, treating placeholders as empty."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in ("-", NO_PARENT, "") else text


def parent_of(rec):
    """(digital, physical) parent ids as strings; '' where there is none."""
    return clean(rec.get("Parent Digital")), clean(rec.get("Parent Physical"))


SKIP_DIRS = {"PreviousV", ".git", "__pycache__"}
# Generated output, not artifacts. Regenerated on every refresh, so registering
# them would be registering a derived view of the register itself.
SKIP_FILES = ("Artifact Dashboard.html", "WBS Dashboard.html", "RAID Dashboard.html",
              "TSP Dashboard.html")


def scan_folder(root, stop_ids=()):
    """Walk the folder a register describes and split it by the ID convention.

    Returns ({id: [relative paths]}, [unprefixed relative paths]).

    Descent obeys the delegation rule, because the disk has to be read the same
    way the register is written:

    - a directory whose ID is in `stop_ids` is recorded and **not entered** —
      another tool governs its contents, so they are not this register's to
      inventory;
    - an unprefixed directory is reported once and not entered, so one
      unregistered folder yields one finding rather than one per file inside it;
    - everything else is descended into, since a registered container's contents
      are themselves registered artifacts.
    """
    prefixed, bare = {}, []
    if not os.path.isdir(root):
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
                prefixed.setdefault(match.group(1), []).append(rel)
                if os.path.isdir(full) and match.group(1) not in stop:
                    walk(full, rel)
            else:
                bare.append(rel)          # reported once; not descended into

    walk(root, "")
    return prefixed, bare
