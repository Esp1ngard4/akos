#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create an empty RAID register for a project.

    python create_raid.py "RAID P.208.json" "AKOS"

Built programmatically, so the schema has exactly one definition.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402

FIELDS = ["RAID.ID", "Detail", "Type", "DRI", "Urgency (1-5)",
          "Consequences (1-5)", "Feasibility", "Probability of Occurrence (1-5)",
          "Severity (1-5)", "Response Strategy", "Mitigation Target %",
          "Residual Risk Score", "MoSCoW", "Status", "Last Review", "Review On",
          "Next Review On", "Description", "Action Plan", "Acceptance Criteria",
          "Action Log", "Category", "Tracked Externally", "Opened On",
          "Requested By", "Involve", "Has AuxMat", "Estimated Effort", "ETC",
          "ETC Renegotiated", "Closed On", "Closed By"]

TYPES = ["Risk", "Action", "Issue", "Decision", "Idea"]
STATUSES = ["Open", "Closed"]

# Priority and Target Residual Risk are not fields: they are computed from the
# scores when the dashboard is rendered, so a stored copy cannot go stale.


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output")
    p.add_argument("project", help="project this register covers")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    if os.path.exists(args.output) and not args.force:
        sys.exit("%s already exists. Pass --force to overwrite." % args.output)

    data = R.new("raid-register", args.project, {"entries": []},
                 settings={"fields": {"entries": FIELDS},
                           "vocabularies": {"type": TYPES, "status": STATUSES}})
    R.save(args.output, data)
    print("Created %s" % args.output)
    print("  project: %s | %d fields | types: %s"
          % (args.project, len(FIELDS), ", ".join(TYPES)))
    print("\nNext: add entries, then"
          )
    print('  python refresh_raid.py "%s" "RAID Dashboard.html" "%s"'
          % (args.output, args.project))


if __name__ == "__main__":
    main()
