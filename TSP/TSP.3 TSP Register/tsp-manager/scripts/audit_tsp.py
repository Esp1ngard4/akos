#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health report for the TSP Register: register vs disk, vocabularies, reviews.

    python audit_tsp.py "TSP Register.json"
    python audit_tsp.py "TSP Register.json" --tools-root "<folder of tool directories>" --repo-root .

Read-only. Run it before the annual review, and whenever the register and the
tool folders may have drifted.

Skill roots are discovered automatically: the repo's `.claude/skills` plus any
`.claude/skills` inside an tool folder. Project-scoped skills are deliberately
not scanned - they belong to projects, not to tools. Pass `--skills DIR`
(repeatable) to override.

Exits non-zero if any error-level finding is present.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks                                                   # noqa: E402
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("register")
    p.add_argument("--tools-root", help="folder holding the TSP.<n> directories")
    p.add_argument("--repo-root", default=".", help="for discovering .claude/skills")
    p.add_argument("--skills", action="append", default=[],
                   help="explicit skill root (repeatable)")
    p.add_argument("--summary", action="store_true",
                   help="class names and counts only")
    args = p.parse_args()

    data = R.load(args.register)
    roots = args.skills or S.find_skill_roots(args.repo_root, args.tools_root)

    print("TSP Register audit - %s" % os.path.basename(args.register))
    errors, warnings, stats = checks.run(data, tools_root=args.tools_root,
                                         skill_roots=roots)
    print("  %d tools, %d control activities%s"
          % (stats["tools"], stats["controls"],
             ", %d tool folders on disk" % stats["folders"]
             if stats["folders"] is not None else ""))
    if roots:
        print("  skills: %d installed, %d claimed by a tool"
              % (stats["skills_installed"], stats["skills_claimed"]))
        for root in roots:
            print("    scanned %s" % root)
    print("  %d tool(s) overdue an annual review, %d control activity(ies) overdue"
          % (stats["overdue_reviews"], stats["controls_due"]))

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
