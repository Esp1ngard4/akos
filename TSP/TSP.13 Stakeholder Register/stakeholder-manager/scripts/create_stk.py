#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a new, empty Stakeholder Register for a project, and its contacts file.

    python create_stk.py "<project folder>" --scope "Atlas"

Writes `Stakeholders <scope>.json` and `Contacts <scope>.csv` into the folder.
`--scope` is the same string as the project's WBS `meta.scope`, so a ref reads
the same in both. The contacts file gets its header only, and is kept out of
git: when the folder is in a git repository that would take it, this prints the
line to add to .gitignore.

**Never use this to reset a live register** - it would destroy the list. A live
register is only ever edited in place, through stk.py.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import stk_register as STK                                      # noqa: E402
import stk_schema as S                                          # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", help="the project folder, where its WBS register is")
    p.add_argument("--scope", required=True, help='the WBS meta.scope, e.g. "Atlas"')
    p.add_argument("--force", action="store_true", help="overwrite an existing register")
    args = p.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit("No folder %s." % args.folder)
    existing = STK.find(args.folder)
    if existing and not args.force:
        sys.exit("%s already holds a register: %s. Pass --force to overwrite.\n"
                 "Never use this on a live register - it would destroy the list."
                 % (args.folder, os.path.basename(existing)))

    path = os.path.join(args.folder, "Stakeholders %s.json" % args.scope)
    data = R.new(S.KIND, args.scope,
                 {S.GROUPS: [], S.STAKEHOLDERS: [], S.COMMS: [], S.CHANGES: []},
                 settings={"fields": S.FIELDS, "vocabularies": S.VOCABULARIES})
    R.save(path, data)
    print("Created %s" % path)

    contacts = STK.contacts_path(path, data)
    if os.path.exists(contacts):
        print("Kept   %s (already there)" % contacts)
    else:
        STK.write_contacts(contacts, {}, list(S.CONTACT_COLUMNS))
        print("Created %s (header only; outside git)" % contacts)
    state = STK.git_state(contacts)
    if state == "tracked":
        print("\n  WARNING: git tracks %s. Untrack it (git rm --cached) and add this line to"
              " .gitignore:\n    Contacts *.csv" % os.path.basename(contacts))
    elif state == "unignored":
        print("\n  This folder is in a git repository that would take the contacts file."
              "\n  Add this line to .gitignore:\n    Contacts *.csv")
    print("\nNext: add a group and a stakeholder")
    print('  python stk.py add-group "%s" "Steering group" --purpose "..."' % args.folder)
    print('  python stk.py add "%s" "Name" --role "..." --groups G.1' % args.folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
