# -*- coding: utf-8 -*-
"""The JSON register format, shared by every register tool here.

A register is one JSON file: a `meta` envelope plus one or more named
collections of rows. The envelope is identical across tools; the collections
are whatever that tool holds.

    {
      "meta": {
        "kind": "artifact-register",
        "version": 1,
        "scope": "Atlas",
        "updated": "2026-09-01T09:40:00",
        "values_hash": "sha256:4f2a...",
        "settings": {"id_width": 2}
      },
      "artifacts": [ {...}, {...} ],
      "locations": [ {...} ]
    }

Why JSON and not a spreadsheet: every write went through a script anyway, and
the spreadsheet cost a subprocess to read, a dependency to install, and a file
lock whenever the sync client or the application had it open. What the
spreadsheet gave back - validated dropdowns at the point of typing - is now the
audit's job, which catches the same errors slightly later.

`values_hash` fingerprints the rows, not the file. A generated view records the
hash it was built from, so it can say it has gone stale rather than quietly
showing old numbers. It ignores formatting, so reindenting the file is not a
data change.

This module is intentionally standard-library only, so a tool that uses it has
no install step at all.
"""
import datetime as dt
import hashlib
import io
import json
import os

FORMAT_VERSION = 1


# --- reading and writing ----------------------------------------------------

def load(path):
    """Read a register. Raises SystemExit with a usable message if it cannot."""
    if not os.path.isfile(path):
        raise SystemExit("No register at %s" % path)
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise SystemExit("%s is not valid JSON: %s" % (path, exc))
    if "meta" not in data:
        raise SystemExit("%s has no 'meta' block - is it a register?" % path)
    return data


def save(path, data, touch=True):
    """Write a register, refreshing its hash and timestamp.

    Sorted keys and a trailing newline so that a diff shows what changed rather
    than a reshuffle.
    """
    if touch:
        data["meta"]["updated"] = dt.datetime.now().replace(microsecond=0).isoformat()
        data["meta"]["values_hash"] = values_hash(data)
    data["meta"].setdefault("version", FORMAT_VERSION)
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)          # written whole, so a crash never truncates it
    return path


def new(kind, scope, collections, settings=None):
    data = {"meta": {"kind": kind, "version": FORMAT_VERSION, "scope": scope,
                     "settings": settings or {}}}
    data.update(collections)
    return data


# --- identity ---------------------------------------------------------------

def values_hash(data):
    """Fingerprint the rows, ignoring the envelope.

    Excludes `meta` deliberately: the timestamp and the hash itself live there,
    so including them would make every write look like a data change.
    """
    payload = dict((k, v) for k, v in data.items() if k != "meta")
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


# --- generated views --------------------------------------------------------

VIEW_MARKER = 'data-values-hash="'


def stale_views(register_path):
    """Generated views beside the register that no longer match it.

    Returns [(filename, reason)]. A view stamps the hash it was built from, so
    this is a read of two small files - cheap enough to run after every edit,
    which is when it matters: the commands change the register and do not
    regenerate anything, so a dashboard is stale the moment you use one.
    """
    folder = os.path.dirname(os.path.abspath(register_path)) or "."
    try:
        current = load(register_path)["meta"].get("values_hash")
    except SystemExit:
        return []
    stale = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".html"):
            continue
        path = os.path.join(folder, name)
        try:
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                head = fh.read(8192)
        except OSError:
            continue
        if VIEW_MARKER not in head:
            continue
        built_from = head.split(VIEW_MARKER, 1)[1].split('"', 1)[0]
        if built_from != current:
            stale.append((name, "built from different data - regenerate it"))
    return stale


# --- collection helpers -----------------------------------------------------

def rows(data, name):
    return data.get(name, [])


def get(data, name, key, value):
    for row in rows(data, name):
        if str(row.get(key, "")).strip() == str(value).strip():
            return row
    return None


def next_id(data, name, key="ID"):
    used = [int(r[key]) for r in rows(data, name)
            if str(r.get(key, "")).strip().lstrip("-").isdigit()]
    return max(used) + 1 if used else 0


def clean(value):
    """A cell as a stripped string, treating placeholders as empty."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in ("-", "N/A") else text


def setting(data, name, default=None):
    return data.get("meta", {}).get("settings", {}).get(name, default)
