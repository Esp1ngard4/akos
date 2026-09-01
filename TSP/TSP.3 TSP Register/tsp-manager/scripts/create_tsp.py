#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a new, empty TSP Register.

    python create_tsp.py "TSP Register.json"

The controlled vocabularies are written into the register rather than hardcoded
here, so a register can use the terms its owner already says out loud - in any
language - instead of inheriting someone else's.

**Never use this to reset the live register** - it would destroy the inventory.
The live register is only ever edited in place.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402

# Vocabularies live in the register, not in this script, so a register can use
# whatever terms its owner already says out loud - in any language. These are
# only what a new one starts with.
VOCABULARIES = {
    "en": {
        "status": ["Planned", "In progress", "Implemented", "Obsolete"],
        "type": ["Manual", "Work instruction", "Tool"],
        "relevancy": ["Critical", "Often", "Sometimes", "Specific - relevant",
                      "Specific - questionable", "Rarely", "Not in the last years"],
        "importance": ["Critical", "Important", "Optional", "Not needed", "Obsolete"],
    },
}

# The Days value is what Next Due is computed from, and nothing
# else in the system records it.
FREQUENCY = {"Daily": 1, "Weekly": 7, "Monthly": 31, "6 weeks": 42,
             "2 months": 60, "Quarterly": 90, "4 months": 120,
             "Semi-annual": 180, "Annual": 365, "2-2 Years": 730,
             "5-5 Years": 1825}


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output")
    p.add_argument("--scope", default="TSP", help="what this register covers")
    p.add_argument("--vocabulary", choices=sorted(VOCABULARIES), default="en",
                   help="controlled vocabularies to seed (default: en)")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = p.parse_args()

    if os.path.exists(args.output) and not args.force:
        sys.exit("%s already exists. Pass --force to overwrite.\n"
                 "Never use this on a live register - it would destroy the "
                 "inventory." % args.output)

    vocab = dict(VOCABULARIES[args.vocabulary])
    vocab["frequency"] = dict(FREQUENCY)

    data = R.new(S.KIND, args.scope,
                 {S.TOOLS: [], S.CONTROLS: [], S.ACTIVITY: [], S.CHANGES: []},
                 settings={"vocabularies": vocab})
    R.save(args.output, data)

    print("Created %s" % args.output)
    print("  4 empty collections | %s vocabularies" % args.vocabulary)
    for name in sorted(vocab):
        values = vocab[name]
        print("    %-12s %d %s" % (name, len(values),
                                   "entries (with Days)" if isinstance(values, dict)
                                   else "values"))
    print("\nNext: register a tool")
    print('  python tsp.py register "%s" "<Tool Name>" --type Tool' % args.output)


if __name__ == "__main__":
    main()
