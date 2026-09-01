# -*- coding: utf-8 -*-
"""The Artifact Register's health checks.

Defined once and called by `audit_artifact_register.py`, which prints them,
`refresh_artifact_register.py`, which renders them into the dashboard's Findings
tab, and `artifact.py`, which runs them after every edit. A check that lived in
only one of those would be a check the others silently lacked.
"""
import datetime as dt
import io
import json
import os

import registry as R
import schema as S

STALE_YEARS = 2


def _parse_date(value):
    try:
        return dt.datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _stop_ids(rows, claimed):
    """IDs the disk scan must not descend into - the delegation rule, applied to
    the filesystem. See TD.5."""
    stop = set()
    for row in rows:
        rid = S.clean(row.get("ID"))
        if (S.clean(row.get("Managed By")) or S.clean(row.get("Type")) == "Tool"
                or rid not in claimed):
            stop.add(rid)
    return stop


def load_tools(path):
    """{id: name} from the tool register, or None if not supplied."""
    if not path or not os.path.isfile(path):
        return None
    data = R.load(path)
    rows = data.get("tools") or []
    return dict((str(r.get("ID")).strip(), r.get("Tool/System Name") or r.get("Name"))
                for r in rows if r.get("ID") is not None)


def run(data, root=None, tools=None, stale_years=STALE_YEARS):
    """Check a register. Returns (errors, warnings, stats).

    `root`  - folder the register describes; enables the disk reconciliation.
    `tools` - {id: name} from the tool register; enables the delegation check.
    """
    rows = R.rows(data, "artifacts")
    width = R.setting(data, "id_width", S.ID_WIDTH_DEFAULT)
    errors, warnings, stats = [], {}, {}

    def err(msg):
        errors.append(msg)

    def warn(kind, msg):
        warnings.setdefault(kind, []).append(msg)

    ids = {}
    for row in rows:
        rid = S.clean(row.get("ID"))
        if not rid:
            err("an entry has no ID: %s" % json.dumps(row)[:120])
        elif rid in ids:
            err("duplicate ID %s" % rid)
        else:
            ids[rid] = row

    claimed = set()
    for row in rows:
        digital, physical = S.parent_of(row)
        claimed.update(p for p in (digital, physical) if p and p != S.ROOT_PARENT)

    for row in rows:
        rid = S.clean(row.get("ID"))
        where = "ID %s (%s)" % (rid, S.clean(row.get("Name")) or "unnamed")
        typ, status = S.clean(row.get("Type")), S.clean(row.get("Status"))

        for field in row:
            if field not in S.FIELDS:
                warn("unknown field", "%s: %r" % (where, field))
        if typ and typ not in S.TYPES:
            err("%s: Type %r not in %s" % (where, typ, S.TYPES))
        if status and status not in S.STATUSES:
            err("%s: Status %r not in %s" % (where, status, S.STATUSES))
        if not status:
            warn("no Status", where)
        if not typ:
            warn("no Type", where)

        for label, parent in zip(("Parent Digital", "Parent Physical"),
                                 S.parent_of(row)):
            if parent and parent != S.ROOT_PARENT and parent not in ids:
                err("%s: %s points at %r, which is not an ID in this register"
                    % (where, label, parent))
            if parent and parent == rid:
                err("%s: %s points at itself" % (where, label))

        reviewed = _parse_date(row.get("Last Reviewed"))
        if reviewed and status == "Active":
            age = (dt.datetime.now() - reviewed).days / 365.25
            if age > stale_years:
                warn("review older than %d years" % stale_years,
                     "%s last reviewed %s (%.1f yrs)"
                     % (where, reviewed.date(), age))
        elif status == "Active" and not row.get("Last Reviewed"):
            warn("Active but never reviewed", where)

    # --- delegation ------------------------------------------------------
    delegated = [(S.clean(r.get("ID")), S.clean(r.get("Managed By")))
                 for r in rows if S.clean(r.get("Managed By"))]
    stats["delegated"] = len(delegated)
    if tools is None:
        if delegated:
            warn("delegations unchecked",
                 "%d found - supply the tool register to verify them" % len(delegated))
        stats["delegations_resolved"] = None
    else:
        resolved = 0
        for rid, target in delegated:
            key = target.replace(S.TOOL_PREFIX, "").replace("F.", "").strip()
            if key not in tools:
                err("ID %s: Managed By %r is not a tool in the tool register"
                    % (rid, target))
            else:
                resolved += 1
                if not target.startswith(S.TOOL_PREFIX):
                    warn("Managed By not written %sn" % S.TOOL_PREFIX,
                         "ID %s: %r" % (rid, target))
        stats["delegations_resolved"] = resolved

    # --- the disk --------------------------------------------------------
    if root:
        stop = _stop_ids(rows, claimed)
        prefixed, bare = S.scan_folder(root, stop)
        stats["disk"] = {"prefixed": len(prefixed), "bare": len(bare),
                         "boundaries": len(stop), "root": root}
        for name in bare:
            err("unregistered on disk: %r has no ID prefix" % name)
        for pid, names in prefixed.items():
            want = S.format_id(pid, width)
            for rel in names:
                got = S.ID_PREFIX.match(os.path.basename(rel)).group(1)
                if got != want:
                    warn("filename not padded to %d digits" % width,
                         "%s should start %s." % (rel, want))
        for pid, names in sorted(prefixed.items(), key=lambda kv: int(kv[0])):
            if pid not in ids:
                err("orphan on disk: %s is prefixed %s, which is not in the register"
                    % (names[0], pid))
            if len(names) > 1:
                nested = all(n.startswith(names[0] + "/") for n in names[1:])
                if nested:
                    warn("ID carried by both a folder and its contents",
                         "ID %s: %s" % (pid, ", ".join(names)))
                else:
                    err("ID %s is used by %d unrelated entries on disk: %s"
                        % (pid, len(names), names))
        for row in rows:
            rid = S.clean(row.get("ID"))
            digital, _ = S.parent_of(row)
            if (digital and rid not in prefixed
                    and S.clean(row.get("Status")) != "Retired"):
                warn("in the register but not on disk",
                     "ID %s %s" % (rid, S.clean(row.get("Name"))))
    else:
        stats["disk"] = None
        warn("disk not checked",
             "supply the folder this register describes to reconcile against it")

    return errors, warnings, stats


def dashboard_stale(register_path, dashboard_path):
    """Whether the dashboard still reflects the register.

    The dashboard embeds the hash it was built from, so this is two small reads
    rather than a recomputation.
    """
    if not os.path.isfile(dashboard_path):
        return None
    with io.open(dashboard_path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(8192)
    marker = 'data-values-hash="'
    if marker not in head:
        return None
    built_from = head.split(marker, 1)[1].split('"', 1)[0]
    return built_from != R.load(register_path)["meta"].get("values_hash")
