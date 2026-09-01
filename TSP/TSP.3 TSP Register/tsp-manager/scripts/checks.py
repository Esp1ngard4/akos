# -*- coding: utf-8 -*-
"""The TSP Register's health checks.

Defined once and called by `audit_tsp.py`, which prints them, and
`refresh_tsp.py`, which renders them into the dashboard. A check that lived in
only one of those would be a check the other silently lacked.
"""
import datetime as dt
import os

import registry as R
import schema as S

OBSOLETE_HINTS = ("absoleto", "obsolete", "obsoleto")


def _date(value):
    try:
        return dt.datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def is_obsolete(status):
    return S.clean(status).lower() in OBSOLETE_HINTS


def run(data, tools_root=None, skill_roots=(), today=None):
    """Check a TSP register. Returns (errors, warnings, stats)."""
    today = today or dt.datetime.now()
    errors, warnings, stats = [], {}, {}

    def err(msg):
        errors.append(msg)

    def warn(kind, msg):
        warnings.setdefault(kind, []).append(msg)

    tools = R.rows(data, S.TOOLS)
    controls = R.rows(data, S.CONTROLS)
    stats["tools"] = len(tools)
    stats["controls"] = len(controls)

    # --- ids and vocabularies -------------------------------------------
    seen = {}
    for row in tools:
        tid = S.clean(row.get("ID"))
        if not tid:
            err("a tool has no ID: %r" % S.tool_name(row))
        elif tid in seen:
            err("duplicate tool ID %s" % tid)
        else:
            seen[tid] = row

    for name, (collection, field) in S.VOCAB_FIELD.items():
        allowed = S.vocabulary(data, name)
        if not allowed:
            continue
        for row in R.rows(data, collection):
            value = S.clean(row.get(field))
            if value and value not in allowed:
                err("%s %s: %s %r is not in the %s vocabulary"
                    % (collection, S.clean(row.get("ID")), field, value, name))

    # --- register against the disk --------------------------------------
    if tools_root:
        folders, unnumbered = S.scan_fsp_folders(tools_root)
        for entry in unnumbered:
            warn("tool folder with no number",
                 "%s - claim an ID for it, or rename it out of the TSP namespace"
                 % entry)
        stats["folders"] = len(folders)
        for fid, folder in sorted(folders.items(), key=lambda kv: int(kv[0])):
            if fid not in seen:
                warn("folder with no register row", "TSP.%s %s" % (fid, folder))
        for tid, row in sorted(seen.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
            if tid not in folders and not is_obsolete(row.get("Status")):
                warn("register row with no folder",
                     "%s %s (%s)" % (tid, S.tool_name(row),
                                     S.clean(row.get("Status"))))
    else:
        stats["folders"] = None

    # --- skills ----------------------------------------------------------
    installed = S.installed_skills(skill_roots) if skill_roots else {}
    claimed = {}
    for row in tools:
        for skill in S.split_skills(row.get("Skill")):
            claimed.setdefault(skill, []).append(S.clean(row.get("ID")))
    stats["skills_claimed"] = len(claimed)
    stats["skills_installed"] = len(installed)
    if skill_roots:
        for skill, ids in sorted(claimed.items()):
            if skill not in installed:
                err("skill %r is named by tool %s but is not installed"
                    % (skill, ", ".join(ids)))
        for skill in sorted(installed):
            if skill not in claimed:
                warn("installed skill claimed by no tool", skill)

    # --- reviews and controls -------------------------------------------
    overdue = []
    for row in tools:
        if is_obsolete(row.get("Status")):
            continue
        reviewed = _date(row.get("Last Reviewed"))
        age = (today - reviewed).days if reviewed else None
        if age is None:
            overdue.append((row, None))
        elif age > S.REVIEW_DAYS:
            overdue.append((row, age))
    stats["overdue_reviews"] = len(overdue)
    for row, age in overdue:
        warn("annual review overdue",
             "%s %s (%s)" % (S.clean(row.get("ID")),
                             S.tool_name(row),
                             "never reviewed" if age is None else "%d days" % age))

    due = []
    for row in controls:
        nxt = _date(row.get("Next Due"))
        if nxt and nxt < today:
            due.append((row, (today - nxt).days))
        elif not nxt:
            warn("control activity with no Next Due",
                 "%s %s" % (S.clean(row.get("ID")), S.clean(row.get("Activity Name"))))
        days = S.frequency_days(data, row.get("Frequency"))
        last = _date(row.get("Last Done"))
        if days and last and nxt:
            expected = last + dt.timedelta(days=days)
            if abs((expected - nxt).days) > 1:
                warn("Next Due does not match Last Done plus Frequency",
                     "%s %s: due %s, expected %s"
                     % (S.clean(row.get("ID")), S.clean(row.get("Activity Name")),
                        nxt.date(), expected.date()))
    stats["controls_due"] = len(due)
    for row, days in sorted(due, key=lambda rd: -rd[1]):
        warn("control activity overdue",
             "%s %s (%d days)" % (S.clean(row.get("ID")),
                                  S.clean(row.get("Activity Name")), days))

    # --- linked tools ----------------------------------------------------
    names = set(S.tool_name(r) for r in tools)
    for row in controls:
        linked = S.clean(row.get("Linked Tool"))
        if linked and linked not in names:
            warn("control activity links to no known tool",
                 "%s %s -> %r" % (S.clean(row.get("ID")),
                                  S.clean(row.get("Activity Name")), linked))

    return errors, warnings, stats
