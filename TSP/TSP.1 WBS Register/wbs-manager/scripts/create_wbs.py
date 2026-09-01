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

ITEM_FIELDS = ["ID", "Code", "Title", "Description", "Acceptance Criteria",
               "Owner", "Estimated Effort (h)", "Type", "Category", "Status",
               "Priority", "Sprint Planned", "Sprint Added", "Sprint Ended",
               "Key Dependencies", "Action Plan", "Planning Considerations",
               "Validation Approach", "Comments"]
DELIVERABLE_FIELDS = ["KeyDel.ID", "Key Deliverable", "Description",
                      "Acceptance Criteria", "Owner", "Status",
                      "Estimated Effort (h)", "Control Approach", "Control Tool",
                      "Project Phase", "Priority", "Planned Release",
                      "Released On", "Key Dependencies",
                      "Planning Considerations", "Comments"]

STATUSES = ["Portfolio Backlog", "Funnel", "Not Started", "Implementing",
            "Done", "Cancelled"]
PRIORITIES = ["Must", "Should", "Could", "Won't"]


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
                 {"items": [], "key_deliverables": []},
                 settings={"fields": {"items": ITEM_FIELDS,
                                      "key_deliverables": DELIVERABLE_FIELDS},
                           "vocabularies": {"status": STATUSES,
                                            "priority": PRIORITIES}})
    R.save(args.output, data)
    print("Created %s" % args.output)
    print("  project: %s | %d item fields | %d deliverable fields"
          % (args.project, len(ITEM_FIELDS), len(DELIVERABLE_FIELDS)))
    print("\nNext: add items, then"
          )
    print('  python refresh_wbs.py "%s" "WBS Dashboard.html" "%s"'
          % (args.output, args.project))


if __name__ == "__main__":
    main()
