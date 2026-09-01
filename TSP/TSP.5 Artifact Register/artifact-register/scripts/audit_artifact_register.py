#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check an Artifact Register against itself, the tool register, and the disk.

    python audit_artifact_register.py "Artifact Register.json"
    python audit_artifact_register.py "07. Artifact Register, Atlas.json" \
        --root "<the folder it describes>" \
        --tool-register "<tool register>"

The filesystem check is the one no other register can do. Because the ID is
written onto the artifact, the register makes a claim about the disk that can be
verified: a file with no ID prefix is unregistered, and a row whose ID appears
nowhere on disk has lost its artifact.

The same findings appear on the dashboard's Findings tab - both come from
`checks.py`, so they cannot disagree.

Exits non-zero if any error-level finding is present.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks                                                   # noqa: E402
import registry as R                                            # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("register")
    p.add_argument("--root", help="folder this register describes, for the disk check")
    p.add_argument("--tool-register", help="tool register, for the Managed By check")
    p.add_argument("--summary", action="store_true",
                   help="class names and counts only, without the individual rows")
    args = p.parse_args()

    data = R.load(args.register)
    rows = R.rows(data, "artifacts")
    print("Artifact Register audit - %s" % os.path.basename(args.register))
    print("  %d artifacts | scope: %s | updated %s"
          % (len(rows), data["meta"].get("scope"), data["meta"].get("updated")))

    errors, warnings, stats = checks.run(
        data, root=args.root, tools=checks.load_tools(args.tool_register))

    if stats.get("delegations_resolved") is not None:
        print("  delegations: %d checked, %d resolved"
              % (stats["delegated"], stats["delegations_resolved"]))
    if stats.get("disk"):
        d = stats["disk"]
        print("  disk: %d prefixed entries, %d without an ID prefix, %d boundaries "
              "not descended into" % (d["prefixed"], d["bare"], d["boundaries"]))
    for name, reason in R.stale_views(args.register):
        warnings.setdefault("generated view is stale", []).append(
            "%s %s" % (name, reason))

    print()
    for msg in errors:
        print("  ERROR    %s" % msg)
    total = 0
    for kind in sorted(warnings, key=lambda k: -len(warnings[k])):
        items = warnings[kind]
        total += len(items)
        print("  warning  %s (%d)" % (kind, len(items)))
        if not args.summary:
            for msg in items:
                print("             %s" % msg)

    print("\n%d error(s), %d warning(s) in %d class(es)."
          % (len(errors), total, len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
