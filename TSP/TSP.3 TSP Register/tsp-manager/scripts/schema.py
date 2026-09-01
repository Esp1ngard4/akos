# -*- coding: utf-8 -*-
"""TSP Register schema.

The register is JSON - see `registry.py` for the envelope. Four collections plus
the controlled vocabularies, which in the spreadsheet were stacked blocks on a
Lookups sheet separated by blank rows. That was a workaround for a spreadsheet
having no nested structure; here they are simply a dict.
"""
import os
import re

KIND = "tsp-register"

TOOLS = "tools"
CONTROLS = "control_activities"
ACTIVITY = "activity_log"
CHANGES = "change_log"

FIELDS = {
    TOOLS: ["ID", "Name", "Description", "Type", "Status",
            "Relevancy", "Primary AF", "Other AFs", "Doc Aux", "Links",
            "Notes", "Last Reviewed", "Skill"],
    CONTROLS: ["ID", "Activity Name", "Frequency", "Duration (min)",
               "Importance", "Commitment", "Linked Tool", "Description",
               "Last Done", "Next Due"],
    ACTIVITY: ["ID", "Activity", "Done On", "Planned For", "Notes",
               "Review On", "Times Postponed"],
    CHANGES: ["ID", "Tool", "Changed On", "Description"],
}

# Vocabularies are per register, not per tool. An established register often has
# terms its owner already uses, sometimes in another language; a new one starts
# from the defaults. Reading them from the register is what lets both exist.
VOCAB_FIELD = {
    "status": (TOOLS, "Status"),
    "type": (TOOLS, "Type"),
    "relevancy": (TOOLS, "Relevancy"),
    "importance": (CONTROLS, "Importance"),
    "frequency": (CONTROLS, "Frequency"),
}

# A tool's folder under the tool root, e.g. "TSP.3 Tool Mgm"
FOLDER = re.compile(r"^TSP\.(\d+)\s+(.+)$")

REVIEW_DAYS = 365          # a tool is due an annual review


# Established registers often name this column "Tool/System Name"; new ones use
# "Name". Accepting both means adopting this tool does not require renaming a
# column across a register you already keep.
NAME_FIELDS = ("Name", "Tool/System Name")


def tool_name(row):
    for field in NAME_FIELDS:
        if row.get(field):
            return str(row[field]).strip()
    return ""


def clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in ("-", "N/A", "None", "") else text


def vocabulary(data, name):
    """Allowed values for a vocabulary. Frequency is a name -> days map."""
    vocab = data.get("meta", {}).get("settings", {}).get("vocabularies", {})
    values = vocab.get(name)
    if isinstance(values, dict):
        return list(values)
    return values or []


def frequency_days(data, frequency):
    """How many days a Frequency represents. None if unknown.

    Next Due is Last Done plus this, and nothing else in the system records it.
    """
    vocab = data.get("meta", {}).get("settings", {}).get("vocabularies", {})
    return (vocab.get("frequency") or {}).get(clean(frequency))


def split_skills(value):
    return [s.strip() for s in str(value or "").split(",") if s.strip()]


def scan_fsp_folders(tools_root):
    """({id: folder name}, [unnumbered tool folders]) on disk.

    Unnumbered ones are returned separately rather than skipped: a folder named
    `TSP.XXX <something>` is a tool somebody started and never registered, which
    is precisely what this audit exists to surface.
    """
    found, unnumbered = {}, []
    if not tools_root or not os.path.isdir(tools_root):
        return found, unnumbered
    for entry in sorted(os.listdir(tools_root)):
        if not os.path.isdir(os.path.join(tools_root, entry)):
            continue
        match = FOLDER.match(entry)
        if match:
            found[match.group(1)] = entry
        elif entry.upper().startswith("TSP."):
            unnumbered.append(entry)
    return found, unnumbered


def find_skill_roots(repo_root, tools_root):
    """Every `.claude/skills` a skill could be installed in.

    The repo root holds most; a couple of tools ship their own nested one. Only
    tool folders are scanned - skills under project folders belong to projects,
    not to tools.
    """
    roots = []
    top = os.path.join(repo_root, ".claude", "skills")
    if os.path.isdir(top):
        roots.append(top)
    # A catalogue has no .claude/skills: each skill sits beside its tool.
    if tools_root and os.path.isdir(tools_root):
        roots.append(tools_root)
    if tools_root and os.path.isdir(tools_root):
        for dirpath, dirnames, _ in os.walk(tools_root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            if os.path.basename(dirpath) == "skills" and \
                    os.path.basename(os.path.dirname(dirpath)) == ".claude":
                roots.append(dirpath)
    return roots


def infer_root(register_path):
    """The folder holding the tool directories, derived from the register.

    The register lives inside one of those directories, so its grandparent is
    the root in every normal layout. Derived rather than required because the
    obvious command - point the audit at a register - otherwise runs with the
    folder and skill checks silently switched off.
    """
    here = os.path.dirname(os.path.abspath(register_path))
    for _ in range(4):
        parent = os.path.dirname(here)
        if not parent or parent == here:
            return None
        try:
            names = os.listdir(parent)
        except OSError:
            return None
        if any(FOLDER.match(n) and os.path.isdir(os.path.join(parent, n))
               for n in names):
            return parent
        here = parent
    return None


def installed_skills(roots):
    """{skill name: where it was found}.

    A skill is any directory holding a SKILL.md. Two layouts are in use and both
    are legitimate, so both are searched: a working environment installs skills
    flat under a skills directory, while a catalogue keeps each skill beside the
    tool it belongs to. Looking only one level down would silently find nothing
    in the second case - and an audit that checks nothing reports clean.
    """
    found = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            path = os.path.join(root, entry)
            if not os.path.isdir(path):
                continue
            if os.path.isfile(os.path.join(path, "SKILL.md")):
                found.setdefault(entry, root)
                continue
            for nested in sorted(os.listdir(path)):
                if os.path.isfile(os.path.join(path, nested, "SKILL.md")):
                    found.setdefault(nested, path)
    return found
