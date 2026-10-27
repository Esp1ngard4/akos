# -*- coding: utf-8 -*-
"""Stakeholder Register schema.

The register is JSON - see `registry.py` for the envelope. One per project, in
the project folder beside its WBS register, four collections:

    groups          the audiences: G.1, G.2 ...
    stakeholders    who, and where they stand in this scope: S.1, S.2 ...
    communications  what flows to whom, how often: C.1, C.2 ...
    change_log      one row per write, with the reason it was made

How to reach a stakeholder is not here. It is in `Contacts <scope>.csv` beside
the register, keyed by the same S.n, and kept out of git.

What can be derived is never stored: the power/interest quadrant, the
engagement gap, when a communication is next due, and who an audience is.
"""
import datetime as dt
import re

KIND = "stakeholder-register"

GROUPS = "groups"
STAKEHOLDERS = "stakeholders"
COMMS = "communications"
CHANGES = "change_log"

PREFIX = {GROUPS: "G", STAKEHOLDERS: "S", COMMS: "C"}
COLLECTION = dict((v, k) for k, v in PREFIX.items())

FIELDS = {
    GROUPS: ["ID", "Name", "Purpose", "Status"],
    STAKEHOLDERS: ["ID", "Name", "Role", "Organisation", "Groups", "Power", "Interest",
                   "Current", "Desired", "Stake", "Engagement Action", "Share Level",
                   "Status", "Notes"],
    COMMS: ["ID", "What", "Report", "Mode", "Audience", "Cadence", "Channel", "Owner",
            "Last Done", "Status", "Notes"],
    CHANGES: ["ID", "Changed On", "Item", "Change", "Reason"],
}

VOCABULARIES = {
    "status": ["Active", "Inactive"],
    "level": ["High", "Low"],
    # PMBOK's engagement assessment matrix, in order: the gap is a distance.
    "engagement": ["Unaware", "Resistant", "Neutral", "Supportive", "Leading"],
    # As the reporting tool and RAID's Sharable use them.
    "share_level": ["owner", "external"],
    # PRINCE2's channel types: a dashboard someone can open is not a sending.
    "mode": ["push", "pull", "interactive"],
    # `on event` takes what the event is: "on event: kitchen delivered".
    "cadence": ["per sprint", "weekly", "monthly", "quarterly", "on event"],
    # The report a communication carries, when it carries one (the reporting tool's kinds).
    "report": ["status-report", "sprint-update", "closure"],
}

LIST_FIELDS = ("Groups", "Audience")
DATE_FIELDS = ("Last Done",)

# Power x Interest -> how the stakeholder is managed. Derived, never stored.
QUADRANT = {("High", "High"): "Manage closely", ("High", "Low"): "Keep satisfied",
            ("Low", "High"): "Keep informed", ("Low", "Low"): "Monitor"}

CONTACT_COLUMNS = ["ID", "Name", "Organisation", "Email", "Phone", "Other",
                   "Preferred channel"]

ID_RE = re.compile(r"^([GSC])\.(\d+)$")


def clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in ("-", "N/A", "None") else text


def parse_date(value, field="date"):
    """ISO date string, or SystemExit. Rejected rather than coerced."""
    text = clean(value)
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        raise SystemExit("%s %r is not a date - use YYYY-MM-DD." % (field, value))


def parse_id(value):
    """'S.4', 's4', 'S 4' -> ('S', 4). None when it is not one."""
    text = clean(value).upper().replace(" ", "")
    m = re.match(r"^([GSC])\.?(\d+)$", text)
    return (m.group(1), int(m.group(2))) if m else None


def norm_id(value):
    parsed = parse_id(value)
    return "%s.%d" % parsed if parsed else None


def is_active(row):
    return clean(row.get("Status")) in ("", "Active")


def vocabulary(data, name):
    vocab = data.get("meta", {}).get("settings", {}).get("vocabularies", {})
    return vocab.get(name) or VOCABULARIES.get(name, [])


def cadence_kind(value):
    """'on event: x' -> 'on event'. Anything else as written."""
    text = clean(value).lower()
    return "on event" if text.startswith("on event") else text


def quadrant(row):
    return QUADRANT.get((row.get("Power"), row.get("Interest")), "")


def gap(row, data=None):
    """Steps from Current to Desired; 0 when there or either is unknown."""
    order = vocabulary(data, "engagement") if data else VOCABULARIES["engagement"]
    cur, des = row.get("Current"), row.get("Desired")
    if cur in order and des in order:
        return max(order.index(des) - order.index(cur), 0)
    return 0
