#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create an empty WBS register for a project.

    python create_wbs.py "WBS P.208.json" "AKOS"

Built programmatically rather than copied from a template, so the schema has one
definition and a fresh register can never carry another project's rows across.
That also removes the template file the skill used to have to ship - a shipped
asset is one more thing that can be missing from a copy.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402

ITEM_FIELDS = ["ID", "Parent", "Code", "Title", "Description",
               "Acceptance Criteria", "Owner", "Estimated Effort (h)",
               "Type", "Class", "Nature", "Delivers", "Key Deliverable", "Category",
               "Status", "Priority", "Horizon", "Sprint Planned", "Sprint Added",
               "Sprint Ended", "Key Dependencies", "Action Plan",
               "Planning Considerations", "Validation Approach",
               "Control Approach", "Control Tool", "Project Phase",
               "Planned Release", "Released On", "Comments"]

STATUSES = ["Portfolio Backlog", "Funnel", "Not Started", "Implementing",
            "Done", "Cancelled"]
PRIORITIES = ["Must", "Should", "Could", "Won't"]
# Level only, and defined without reference to duration - size lives in
# Estimated Effort (h). What a row delivers is Delivers, what kind of value it
# serves is Class, and what is being done to it is Nature.
TYPES = ["Deliverable", "Feature", "Story", "Task"]
# Whether a row serves the value the project exists to create, the running of
# the project, or the delivery of the product without being visible in it.
# PRINCE2 calls the first two specialist and management products.
CLASSES = ["Product", "Management", "Enabler"]
NATURES = ["Build", "Improve", "Analyse", "Fix", "Maintain"]
DELIVERS = ["Tool", "System", "Process", "Document"]
# How soon, which is neither how important (Priority) nor where it stands
# (Status). An item can be Could and Next, or Must and Future. Cleared the
# moment a real sprint supersedes it, or the row closes.
HORIZONS = ["Next", "Future"]
YESNO = ["Y", "N"]

# The sprint calendar, imported from the project's agile conventions and
# never defined here - the ceremonies own the cadence, the register consumes it.
SPRINT_FIELDS = ["Sprint", "Starts", "Ends"]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output")
    p.add_argument("project", help="project this WBS covers")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    if os.path.exists(args.output) and not args.force:
        sys.exit("%s already exists. Pass --force to overwrite." % args.output)

    data = R.new("wbs-register", args.project,
                 {"items": [], "sprints": []},
                 settings={"fields": {"items": ITEM_FIELDS,
                                      "sprints": SPRINT_FIELDS},
                           "vocabularies": {"status": STATUSES,
                                            "priority": PRIORITIES,
                                            "type": TYPES,
                                            "class": CLASSES,
                                            "nature": NATURES,
                                            "delivers": DELIVERS,
                                            "horizon": HORIZONS,
                                            "key deliverable": YESNO}})
    R.save(args.output, data)
    print("Created %s" % args.output)
    print("  project: %s | %d item fields" % (args.project, len(ITEM_FIELDS)))
    print("\nNext: add items, then"
          )
    print('  python refresh_wbs.py "%s" "WBS Dashboard.html" "%s"'
          % (args.output, args.project))


if __name__ == "__main__":
    main()
