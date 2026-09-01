#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Edits that must change the register and the disk together.

    python artifact.py add    <register> <path> --name "Land Deed" --type Document
    python artifact.py add    <register> --name "Box of deeds" --type Item  # physical
    python artifact.py add    <register> <path> --id 22        # row exists, lost its prefix
    python artifact.py rename <register> --id 22 --name "New Name" --root <folder>
    python artifact.py move   <register> --id 22 --parent-digital 12 --root <folder>
    python artifact.py retire <register> --id 22 --root <folder> --yes
    python artifact.py repad  <register> --root <folder> [--width 3]
    python artifact.py review <register> --before 2020-01-01   # bulk stamp

`Name` and the parent columns are encoded into the filesystem, so changing either
in the register alone leaves the two disagreeing in a way no check can see - the
audit matches on ID, not on name. These operations change both together.

Plain field edits - Description, Comments, Owner, Managed By, Area of Focus,
Type - are just JSON. Edit the file.

`retire` deletes the artifact. It refuses to orphan registered children, and does
nothing without --yes.
"""
import argparse
import datetime as dt
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks                                                   # noqa: E402
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402


# --- helpers ----------------------------------------------------------------

def load(path):
    data = R.load(path)
    return data, R.rows(data, "artifacts"), R.setting(data, "id_width",
                                                      S.ID_WIDTH_DEFAULT)


def row_for(rows, artifact_id):
    for row in rows:
        if S.clean(row.get("ID")) == str(artifact_id):
            return row
    sys.exit("No artifact with ID %s in this register." % artifact_id)


def next_id(rows):
    used = [int(S.clean(r.get("ID"))) for r in rows
            if S.clean(r.get("ID")).isdigit()]
    return max(used) + 1 if used else 0


def strip_prefix(name):
    match = S.ID_PREFIX.match(name)
    return name[match.end():].strip() if match else name


def target_name(artifact_id, name, original, width):
    ext = os.path.splitext(original)[1] if os.path.isfile(original) else ""
    return "%s. %s%s" % (S.format_id(artifact_id, width), name, ext)


def locate(root, artifact_id):
    prefixed, _ = S.scan_folder(root)
    hits = prefixed.get(str(artifact_id), [])
    if not hits:
        return None
    hits.sort(key=lambda p: p.count("/"))    # shallowest is the artifact itself
    return os.path.join(root, hits[0].replace("/", os.sep))


def children_of(rows, artifact_id):
    out = []
    for row in rows:
        if str(artifact_id) in S.parent_of(row):
            out.append(row)
    return out


def rename_on_disk(path, new_name, dry):
    dest = os.path.join(os.path.dirname(path), new_name)
    if os.path.abspath(dest) == os.path.abspath(path):
        print("  disk    already named %r" % new_name)
        return path
    if os.path.exists(dest):
        sys.exit("Refusing to overwrite an existing %s" % dest)
    print("  disk    %s -> %s" % (os.path.basename(path), new_name))
    if not dry:
        os.rename(path, dest)
    return dest


def report(register, root, tool_register):
    """Re-check after the edit, so a half-done operation says so now."""
    errors, warnings, _ = checks.run(R.load(register), root=root,
                                     tools=checks.load_tools(tool_register))
    print("\n  check   %d error(s), %d warning(s)"
          % (len(errors), sum(len(v) for v in warnings.values())))
    for msg in errors[:5]:
        print("          ERROR %s" % msg)
    if len(errors) > 5:
        print("          ... and %d more (run audit_artifact_register.py)"
              % (len(errors) - 5))


def finish(args, data, register=None):
    if args.dry_run:
        print("\n  dry run - nothing written.")
        return 0
    R.save(register or args.register, data)
    report(register or args.register, args.root, args.tool_register)
    return 0


# --- commands ---------------------------------------------------------------

def cmd_add(args):
    data, rows, width = load(args.register)

    # An artifact need not be a file. Most of a general reference register is
    # physical - a box, a folder in a drawer - and those get a row and a label
    # rather than a rename. Requiring a path would exclude the majority.
    if args.path is None:
        if not args.name:
            sys.exit("Give --name when registering something with no file.")
        if args.id is not None:
            sys.exit("--id re-prefixes an existing file, so it needs a path.")
        original = None
    else:
        if not os.path.exists(args.path):
            sys.exit(("%s does not exist." + chr(10) +
                      "If this is a physical artifact, omit the path and pass "
                      "--name instead.") % args.path)
        original = os.path.basename(args.path)

    if args.id is not None:
        row = row_for(rows, args.id)
        artifact_id = S.clean(row.get("ID"))
        name = args.name or S.clean(row.get("Name")) or strip_prefix(original)
        if args.name:
            row["Name"] = args.name
        print("Re-prefixing existing artifact %s (%s)" % (artifact_id, name))
    else:
        artifact_id = str(next_id(rows))
        name = args.name or os.path.splitext(strip_prefix(original))[0]
        today = dt.date.today().isoformat()
        row = {"ID": int(artifact_id), "Name": name, "Status": "Active",
               "Created On": today, "Last Reviewed": today,
               "Parent Digital": args.parent_digital or S.NO_PARENT,
               "Parent Physical": args.parent_physical or S.NO_PARENT}
        for key, value in (("Description", args.description), ("Type", args.type),
                           ("Location", args.location), ("Managed By", args.managed_by),
                           ("Area of Focus", args.area), ("Owner", args.owner)):
            if value:
                row[key] = value
        rows.append(row)
        print("Adding artifact %s (%s)" % (artifact_id, name))
        print("  row     added")

    if original is None:
        print("  disk    none - physical artifact. Label it %s"
              % S.format_id(artifact_id, width))
    else:
        rename_on_disk(args.path, target_name(artifact_id, name, args.path, width),
                       args.dry_run)
    return finish(args, data)


def cmd_rename(args):
    data, rows, width = load(args.register)
    row = row_for(rows, args.id)
    print("Renaming artifact %s: %r -> %r"
          % (args.id, S.clean(row.get("Name")), args.name))
    row["Name"] = args.name
    print("  row     updated")

    path = locate(args.root, args.id)
    if path:
        rename_on_disk(path, target_name(args.id, args.name, path, width),
                       args.dry_run)
    else:
        print("  disk    nothing found with prefix %s%s" %
              (args.id, "" if args.root else " (pass --root to rename the file too)"))
    return finish(args, data)


def cmd_move(args):
    if args.parent_digital is None and args.parent_physical is None:
        sys.exit("Give --parent-digital and/or --parent-physical.")
    data, rows, _ = load(args.register)
    row = row_for(rows, args.id)
    ids = set(S.clean(r.get("ID")) for r in rows)

    print("Moving artifact %s (%s)" % (args.id, S.clean(row.get("Name"))))
    for flag, field in (("parent_digital", "Parent Digital"),
                        ("parent_physical", "Parent Physical")):
        value = getattr(args, flag)
        if value is None:
            continue
        if value not in ids and value not in (S.ROOT_PARENT, S.NO_PARENT):
            sys.exit("%s %r is not an ID in this register." % (field, value))
        if value == str(args.id):
            sys.exit("%s cannot point at itself." % field)
        print("  row     %s: %r -> %r"
              % (field, S.clean(row.get(field)) or S.NO_PARENT, value))
        row[field] = value

    if args.root and args.parent_digital is not None:
        path = locate(args.root, args.id)
        if not path:
            print("  disk    nothing found with prefix %s" % args.id)
        else:
            if args.parent_digital in (S.ROOT_PARENT, S.NO_PARENT):
                dest_dir = args.root
            else:
                dest_dir = locate(args.root, args.parent_digital)
                if not dest_dir or not os.path.isdir(dest_dir):
                    sys.exit("Parent %s is not a folder on disk; move it by hand."
                             % args.parent_digital)
            dest = os.path.join(dest_dir, os.path.basename(path))
            if os.path.abspath(dest) == os.path.abspath(path):
                print("  disk    already in place")
            elif os.path.exists(dest):
                sys.exit("Refusing to overwrite %s" % dest)
            else:
                print("  disk    %s -> %s%s" % (os.path.basename(path),
                                                os.path.relpath(dest_dir, args.root),
                                                os.sep))
                if not args.dry_run:
                    shutil.move(path, dest)
    return finish(args, data)


def cmd_retire(args):
    data, rows, _ = load(args.register)
    row = row_for(rows, args.id)
    name = S.clean(row.get("Name"))

    live = [r for r in children_of(rows, args.id)
            if S.clean(r.get("Status")) != "Retired"]
    if live:
        listing = ", ".join("%s %s" % (S.clean(r.get("ID")), S.clean(r.get("Name")))
                            for r in live[:6])
        sys.exit("Refusing to retire %s (%s): %d active artifact(s) are inside it.\n"
                 "  %s%s\nRetire those first - deleting the container would take "
                 "them with it and leave rows pointing at nothing."
                 % (args.id, name, len(live), listing,
                    "" if len(live) <= 6 else ", ..."))

    print("Retiring artifact %s (%s)" % (args.id, name))
    verb = "archive" if args.archive else "delete"
    path = locate(args.root, args.id) if args.root else None
    if path:
        kind = "folder" if os.path.isdir(path) else "file"
        where = (" -> %s" % args.archive) if args.archive else ""
        print("  %-7s %s %s%s" % (verb, kind, os.path.relpath(path, args.root), where))
    elif args.root:
        print("  %-7s nothing on disk with prefix %s (physical, or already gone)"
              % (verb, args.id))
    else:
        print("  %-7s skipped - pass --root to act on the file" % verb)
    print("  row     Status -> Retired (kept; ID %s stays spent)" % args.id)

    if not args.yes:
        print("\n  Nothing done. This %ss the artifact - re-run with --yes." % verb)
        return 1

    if path:
        if args.archive:
            os.makedirs(args.archive, exist_ok=True)
            dest = os.path.join(args.archive, os.path.basename(path))
            if os.path.exists(dest):
                sys.exit("%s already exists in the archive." % dest)
            shutil.move(path, dest)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    row["Status"] = "Retired"
    row["Last Reviewed"] = dt.date.today().isoformat()
    if args.reason:
        existing = S.clean(row.get("Comments"))
        row["Comments"] = ("%s | " % existing if existing else "") + \
            "Retired %s: %s" % (dt.date.today().isoformat(), args.reason)
    R.save(args.register, data)
    report(args.register, args.root, args.tool_register)
    return 0


def cmd_repad(args):
    """Bring every filename up to the register's ID width.

    Only the number changes. The name, separator and extension are left exactly
    as they are - rebuilding names from the register would quietly rewrite
    filenames that have legitimately drifted from it, a different decision.
    """
    data, rows, width = load(args.register)
    if args.width:
        width = args.width
        data["meta"].setdefault("settings", {})["id_width"] = width
        print("Setting ID width to %d" % width)

    widest = max((len(S.clean(r.get("ID"))) for r in rows), default=1)
    if widest > width:
        sys.exit("This register has %d-digit IDs but the width is %d. "
                 "Re-run with --width %d, or padding would sort wrongly above "
                 "10^%d." % (widest, width, widest, width))

    plan = []
    prefixed = {}
    if args.root:
        prefixed, _ = S.scan_folder(args.root)
        known = set(S.clean(r.get("ID")) for r in rows)
        for rid in sorted(prefixed, key=int):
            if rid not in known:
                continue
            for rel in prefixed[rid]:
                path = os.path.abspath(os.path.join(args.root,
                                                    rel.replace("/", os.sep)))
                current = os.path.basename(path)
                match = S.ID_PREFIX.match(current)
                sep = current[match.end(1):match.end()]
                want = "%s%s%s" % (S.format_id(rid, width), sep,
                                   current[match.end():])
                if current != want:
                    plan.append((path, want))

    for path, want in plan:
        print("  %s -> %s" % (os.path.basename(path), want))
    print("\n  %d to rename, %d already correct"
          % (len(plan), sum(len(v) for v in prefixed.values()) - len(plan)))
    if args.dry_run:
        print("  dry run - nothing written.")
        return 0

    R.save(args.register, data)
    register = os.path.abspath(args.register)
    failed = []
    # Deepest first, so a parent rename never invalidates a path still queued.
    for path, want in sorted(plan, key=lambda pw: pw[0].count(os.sep), reverse=True):
        dest = os.path.join(os.path.dirname(path), want)
        for _ in range(5):
            try:
                os.rename(path, dest)
                if register == path or register.startswith(path + os.sep):
                    register = dest + register[len(path):]
                break
            except OSError:
                time.sleep(0.2)
        else:
            failed.append((os.path.basename(path), want))

    if failed:
        print("\n  Could not rename %d item(s) - close anything open inside "
              "them and re-run:" % len(failed))
        for old, want in failed:
            print("    %s  ->  %s" % (old, want))
    if register != os.path.abspath(args.register):
        print("  register is now %s" % os.path.relpath(register, args.root or "."))
    report(register, args.root, args.tool_register)
    return 0


def cmd_review(args):
    """Bulk-stamp Last Reviewed - the annual walk-through, in one command.

    This is the operation the spreadsheet used to be needed for.
    """
    data, rows, _ = load(args.register)
    today = dt.date.today().isoformat()
    cutoff = args.before
    touched = []
    for row in rows:
        if args.status and S.clean(row.get("Status")) != args.status:
            continue
        if args.type and S.clean(row.get("Type")) != args.type:
            continue
        reviewed = S.clean(row.get("Last Reviewed"))
        if cutoff and reviewed and reviewed >= cutoff:
            continue
        touched.append(row)

    print("Stamping Last Reviewed = %s on %d artifact(s)" % (today, len(touched)))
    for row in touched[:10]:
        print("  ID %-4s %s (was %s)" % (S.clean(row.get("ID")),
                                         S.clean(row.get("Name")),
                                         S.clean(row.get("Last Reviewed")) or "never"))
    if len(touched) > 10:
        print("  ... and %d more" % (len(touched) - 10))
    if args.dry_run:
        print("\n  dry run - nothing written.")
        return 0
    for row in touched:
        row["Last Reviewed"] = today
    return finish(args, data)


# --- entry point ------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = p.add_subparsers(dest="command")

    def shared(sub, dry=True):
        sub.add_argument("register")
        sub.add_argument("--root", help="folder the register describes")
        sub.add_argument("--tool-register", help="tool register, for the post-edit check")
        if dry:
            sub.add_argument("--dry-run", action="store_true",
                             help="show what would change, write nothing")

    s = subs.add_parser("add", help="register a new artifact and prefix its file")
    shared(s)
    s.add_argument("path", nargs="?",
                   help="the file or folder to register; omit for a "
                        "physical artifact that has no file")
    s.add_argument("--id", help="existing row whose file lost its prefix")
    s.add_argument("--name")
    s.add_argument("--type", choices=S.TYPES)
    s.add_argument("--description")
    s.add_argument("--location")
    s.add_argument("--parent-digital")
    s.add_argument("--parent-physical")
    s.add_argument("--managed-by")
    s.add_argument("--area")
    s.add_argument("--owner")
    s.set_defaults(func=cmd_add)

    s = subs.add_parser("rename", help="change the name in the register and on disk")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("--name", required=True)
    s.set_defaults(func=cmd_rename)

    s = subs.add_parser("move", help="change the container, and move the file")
    shared(s)
    s.add_argument("--id", required=True)
    s.add_argument("--parent-digital")
    s.add_argument("--parent-physical")
    s.set_defaults(func=cmd_move)

    s = subs.add_parser("repad", help="pad every filename to the register's ID width")
    shared(s)
    s.add_argument("--width", type=int, help="also change the register's ID width")
    s.set_defaults(func=cmd_repad)

    s = subs.add_parser("review", help="bulk-stamp Last Reviewed")
    shared(s)
    s.add_argument("--before", metavar="YYYY-MM-DD",
                   help="only artifacts last reviewed before this date, or never")
    s.add_argument("--status", choices=S.STATUSES)
    s.add_argument("--type", choices=S.TYPES)
    s.set_defaults(func=cmd_review)

    s = subs.add_parser("retire", help="dispose of the artifact; keep the row and ID")
    shared(s, dry=False)
    s.add_argument("--id", required=True)
    s.add_argument("--reason", help="recorded in Comments")
    s.add_argument("--archive", metavar="DIR",
                   help="move the artifact here instead of deleting it")
    s.add_argument("--yes", action="store_true",
                   help="required - without --archive this deletes files")
    s.set_defaults(func=cmd_retire)

    args = p.parse_args()
    if not getattr(args, "command", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
