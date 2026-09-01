#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create an empty Artifact Register for a scope.

    python create_artifact_register.py "07. Artifact Register, Atlas.json" "Atlas"

The filename should start with the ID this register holds in its own scope - it
is an artifact of that scope like any other, and it seeds itself as that row.
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402

DEFAULT_LOCATIONS = [("Physical", "Home"), ("Physical", "Office"),
                     ("Digital", "Cloud drive"), ("Digital", "Local disk")]


def build(path, scope, locations, areas, width):
    seed_match = S.ID_PREFIX.match(os.path.basename(path))
    seed = int(seed_match.group(1)) if seed_match else 0

    stem = os.path.splitext(os.path.basename(path))[0]
    prefix = S.ID_PREFIX.match(stem)
    # Name excludes the ID prefix; the prefix is rebuilt from the ID whenever a
    # filename is generated. Storing it in both places is how you get "07. 07. x".
    name = stem[prefix.end():].strip() if prefix else stem
    today = dt.date.today().isoformat()

    data = R.new(S.KIND, scope, {
        "artifacts": [{
            "ID": seed, "Name": name, "Description": "This register.",
            "Type": "Document", "Parent Digital": S.ROOT_PARENT,
            "Parent Physical": S.NO_PARENT, "Status": "Active",
            "Created On": today, "Last Reviewed": today,
        }],
        "locations": [{"ID": i, "Location": n, "Kind": k, "Active": "Yes"}
                      for i, (k, n) in enumerate(locations, start=1)],
        "areas_of_focus": [{"ID": a, "Name": n} for a, n in areas],
    }, settings={"id_width": width})
    R.save(path, data)
    return seed


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", help="path of the register to create")
    p.add_argument("scope", help="what this register covers")
    p.add_argument("--location", action="append", default=[], metavar="Kind:Name",
                   help="seed a location, e.g. Physical:Garage (repeatable)")
    p.add_argument("--area", action="append", default=[], metavar="ID:Name",
                   help="seed an Area of Focus, e.g. 5:Financial Freedom (repeatable)")
    p.add_argument("--id-width", type=int, default=S.ID_WIDTH_DEFAULT, metavar="N",
                   help="digits to pad IDs to on filenames (default: %d). Two suits "
                        "a register under 100 artifacts." % S.ID_WIDTH_DEFAULT)
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = p.parse_args()

    if os.path.exists(args.output) and not args.force:
        sys.exit("%s already exists. Pass --force to overwrite." % args.output)

    locations = []
    for spec in args.location:
        kind, _, name = spec.partition(":")
        if kind.strip().capitalize() not in S.KINDS or not name:
            sys.exit("--location wants Physical:Name or Digital:Name, got %r" % spec)
        locations.append((kind.strip().capitalize(), name.strip()))
    areas = []
    for spec in args.area:
        aid, _, name = spec.partition(":")
        if not name:
            sys.exit("--area wants ID:Name, got %r" % spec)
        areas.append((aid.strip(), name.strip()))

    seed = build(args.output, args.scope, locations or DEFAULT_LOCATIONS,
                 areas, args.id_width)
    padded = S.format_id(seed, args.id_width)
    print("Created %s" % args.output)
    print("  scope: %s | %d locations | %d areas | IDs padded to %d digits"
          % (args.scope, len(locations or DEFAULT_LOCATIONS), len(areas),
             args.id_width))
    print("  seeded with itself as artifact %s" % padded)
    if not os.path.basename(args.output).startswith(padded + "."):
        print("  note: rename this file to start %s. so its own prefix is padded too"
              % padded)
    print("\nNext:")
    print('  python artifact.py add "%s" <path> --name "..." --root <folder>'
          % args.output)


if __name__ == "__main__":
    main()
