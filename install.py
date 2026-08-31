#!/usr/bin/env python3
"""Install AKOS tools into a project, and keep them in sync afterwards.

    python install.py list
    python install.py add wbs-manager --into ../my-project
    python install.py status
    python install.py diff wbs-manager
    python install.py update wbs-manager
    python install.py accept wbs-manager -m "why we diverged"

A skill only loads from the working tree of whoever is running the agent. So a team
shares a tool by committing it into the project: everyone gets it on clone, nobody
runs a setup step, and a change to it shows up in a pull request like any other.

That is a copy, and copies drift. This script makes the copy deliberate rather than
accidental. It records where each one came from and at which commit, which is what
lets a later update do a three-way merge - upstream changes applied, local changes
kept, and a human asked only about the overlap.

The record lives in tools.lock.json at the project root.
"""

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

LOCK_NAME = "tools.lock.json"
DEFAULT_DEST = ".github/skills"
SKIP = {".git", "__pycache__", ".pytest_cache", ".DS_Store"}
CATALOGUE = os.path.dirname(os.path.abspath(__file__))
CONFLICT_MARKER = "<" * 7 + " ours"


# --- plumbing ---------------------------------------------------------------

def git(args, cwd=None, check=True):
    proc = subprocess.run(["git"] + args, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (
            " ".join(args), proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace").strip()


def content(path):
    """File bytes, with text line endings normalized to LF.

    Everything here compares a working-tree copy against `git archive` output.
    Those disagree about line endings the moment core.autocrlf is on, which is
    the Windows default: the checkout is CRLF, the archive is LF, and every text
    file then looks changed on both sides. Normalizing makes the comparison mean
    what it is supposed to mean, and stops a Windows clone reporting the whole
    estate as modified.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if b"\0" in data[:8192]:
        return data
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest(path):
    return "sha256:" + hashlib.sha256(content(path)).hexdigest()


def walk(root):
    """Every file under root as a sorted list of POSIX-style relative paths."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if name in SKIP:
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def hashes(root):
    return dict((rel, digest(os.path.join(root, rel))) for rel in walk(root))


def is_binary(path):
    with open(path, "rb") as fh:
        return b"\0" in fh.read(8192)


def extract(tar_path, dest):
    with tarfile.open(tar_path) as tar:
        try:
            tar.extractall(dest, filter="data")          # Python 3.12+
        except TypeError:
            tar.extractall(dest)


def materialize(source, ref, dest):
    """Put the catalogue as it stood at `ref` into `dest`.

    `source` is a local clone or a remote URL. Commits are addressed by SHA rather
    than by tag, because a tag can be moved and this has to reconstruct the exact
    content a copy was originally taken from.
    """
    os.makedirs(dest, exist_ok=True)
    if os.path.isdir(source):
        archive = dest + ".tar"
        git(["archive", ref, "--format=tar", "-o", archive], cwd=source)
        extract(archive, dest)
        os.remove(archive)
        return dest
    git(["init", "-q", dest])
    git(["remote", "add", "origin", source], cwd=dest)
    try:
        git(["fetch", "-q", "--depth", "1", "origin", ref], cwd=dest)
        git(["checkout", "-q", "FETCH_HEAD"], cwd=dest)
    except RuntimeError:                        # server refuses fetch-by-SHA
        shutil.rmtree(dest, ignore_errors=True)
        git(["clone", "-q", source, dest])
        git(["checkout", "-q", ref], cwd=dest)
    return dest


def read_text(path, limit=200000):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


# --- catalogue and lock -----------------------------------------------------

def read_catalogue(root):
    """Every skill published under TSP/, keyed by skill name.

    A tool folder is `TSP/TSP.<n> <Name>/`; its skill is the directory inside
    holding a SKILL.md. Tools with no skill do not appear here - they are still
    tools, they just have nothing to install.
    """
    found = {}
    tsp = os.path.join(root, "TSP")
    if not os.path.isdir(tsp):
        return found
    for tool in sorted(os.listdir(tsp)):
        tool_dir = os.path.join(tsp, tool)
        if not os.path.isdir(tool_dir):
            continue
        for entry in sorted(os.listdir(tool_dir)):
            skill_dir = os.path.join(tool_dir, entry)
            if os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
                found[entry] = {
                    "path": skill_dir,
                    "tool": tool,
                    "tsp": tool.split(" ")[0],
                    "origin": "TSP/%s/%s" % (tool, entry),
                }
    return found


def load_lock(project):
    path = os.path.join(project, LOCK_NAME)
    if not os.path.isfile(path):
        return {"source": None, "tools": {}}
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_lock(project, lock):
    path = os.path.join(project, LOCK_NAME)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(lock, indent=2, ensure_ascii=False) + "\n")


def require(lock, name):
    if name not in lock["tools"]:
        installed = ", ".join(sorted(lock["tools"])) or "none"
        sys.exit("'%s' is not installed here. Installed: %s" % (name, installed))
    return lock["tools"][name]


def local_root(project, rec):
    return os.path.join(project, rec["path"].replace("/", os.sep))


# --- commands ---------------------------------------------------------------

def cmd_list(args):
    cat = read_catalogue(args.catalogue)
    if not cat:
        sys.exit("No skills found under %s/TSP" % args.catalogue)
    print("Installable skills in %s:\n" % args.catalogue)
    for name in sorted(cat):
        print("  %-18s %s" % (name, cat[name]["tool"]))
    print("\n  python install.py add <name> --into <project>")
    return 0


def cmd_add(args):
    cat = read_catalogue(args.catalogue)
    if args.skill not in cat:
        sys.exit("Unknown skill '%s'. Try: python install.py list" % args.skill)
    entry = cat[args.skill]

    project = os.path.abspath(args.into)
    if os.path.abspath(args.catalogue) == project:
        sys.exit("Refusing to install into the catalogue itself.\n"
                 "This repo lists tools; it is not a working environment.\n"
                 "Pass --into <your project>.")

    dest_rel = "%s/%s" % (args.dest.replace(os.sep, "/").rstrip("/"), args.skill)
    dest = os.path.join(project, dest_rel.replace("/", os.sep))
    if os.path.exists(dest):
        if not args.force:
            sys.exit("%s already exists.\n"
                     "Use 'update' to bring in upstream changes, or --force to "
                     "overwrite." % dest_rel)
        shutil.rmtree(dest)

    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copytree(entry["path"], dest, ignore=shutil.ignore_patterns(*SKIP))

    lock = load_lock(project)
    if not lock.get("source"):
        lock["source"] = (args.source
                          or git(["remote", "get-url", "origin"],
                                 cwd=args.catalogue, check=False)
                          or os.path.abspath(args.catalogue))
    lock["tools"][args.skill] = {
        "tsp": entry["tsp"],
        "tool": entry["tool"],
        "origin": entry["origin"],
        "path": dest_rel,
        "commit": git(["rev-parse", "HEAD"], cwd=args.catalogue),
        "installed": dt.date.today().isoformat(),
        "files": hashes(dest),
    }
    save_lock(project, lock)

    rec = lock["tools"][args.skill]
    print("Installed %s (%s) -> %s" % (args.skill, entry["tsp"], dest_rel))
    print("  from %s @ %s" % (lock["source"], rec["commit"][:7]))
    print("  %d files recorded in %s" % (len(rec["files"]), LOCK_NAME))
    print("\nCommit the skill folder and %s together, so the team gets both on "
          "clone." % LOCK_NAME)
    return 0


def compare(recorded, root):
    """Recorded hashes vs what is on disk now."""
    if not os.path.isdir(root):
        return sorted(recorded), [], []
    current = hashes(root)
    missing = sorted(set(recorded) - set(current))
    added = sorted(set(current) - set(recorded))
    modified = sorted(p for p in set(recorded) & set(current)
                      if recorded[p] != current[p])
    return missing, added, modified


def cmd_status(args):
    project = os.path.abspath(args.project)
    lock = load_lock(project)
    if not lock["tools"]:
        print("No tools installed (%s not found or empty)." % LOCK_NAME)
        return 0

    dirty = 0
    print("source: %s\n" % lock.get("source"))
    for name in sorted(lock["tools"]):
        rec = lock["tools"][name]
        missing, added, modified = compare(rec["files"], local_root(project, rec))
        merging = rec.get("merging")

        state = "clean"
        if missing or added or modified:
            state = "MODIFIED"
            dirty += 1
        if merging:
            state = "MERGING"
            dirty += 1

        print("%-18s %-9s %s @ %s" % (name, state, rec["tsp"], rec["commit"][:7]))
        if rec.get("local_changes"):
            print("     declared: %s" % rec["local_changes"])
        if merging:
            print("     merge to %s unresolved: %s"
                  % (merging["commit"][:7], ", ".join(merging["conflicts"])))
        for path in modified:
            print("     modified  %s" % path)
        for path in missing:
            print("     MISSING   %s" % path)
        for path in added:
            print("     added     %s" % path)

    if args.check and dirty:
        print("\n%d tool(s) differ from the lock. If that is intended, run:\n"
              '    python install.py accept <tool> -m "<why>"' % dirty)
        return 1
    if args.check:
        print("\nAll copies match the lock.")
    return 0


def cmd_diff(args):
    project = os.path.abspath(args.project)
    lock = load_lock(project)
    rec = require(lock, args.skill)
    source = args.source or lock.get("source")
    ref = args.ref or "HEAD"

    scratch = tempfile.mkdtemp(prefix="akos-diff-")
    try:
        up = materialize(source, ref, os.path.join(scratch, "up"))
        theirs = os.path.join(up, rec["origin"].replace("/", os.sep))
        proc = subprocess.run(
            ["git", "diff", "--no-index", "--", theirs, local_root(project, rec)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout.decode("utf-8", "replace")
        print(out if out.strip() else "No difference from upstream %s." % ref)
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def merge_file(mine, base, theirs):
    """Three-way merge in place. Returns conflict count, or -1 if unmergeable.

    The merge runs on LF-normalized copies for the reason given in content(),
    then the result is written back in whatever line ending the local file used.
    """
    if is_binary(mine) or is_binary(base) or is_binary(theirs):
        return -1
    with open(mine, "rb") as fh:
        raw = fh.read()
    was_crlf = raw.count(b"\r\n") * 2 > raw.count(b"\n")

    scratch = tempfile.mkdtemp(prefix="akos-merge-")
    try:
        sides = []
        for name, src in (("ours", mine), ("base", base), ("upstream", theirs)):
            path = os.path.join(scratch, name)
            with open(path, "wb") as fh:
                fh.write(content(src))
            sides.append(path)
        proc = subprocess.run(["git", "merge-file", "-L", "ours", "-L", "base",
                               "-L", "upstream"] + sides,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(sides[0], "rb") as fh:
            merged = fh.read()
        if was_crlf:
            merged = merged.replace(b"\n", b"\r\n")
        with open(mine, "wb") as fh:
            fh.write(merged)
        return proc.returncode if proc.returncode >= 0 else -1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def cmd_update(args):
    project = os.path.abspath(args.project)
    lock = load_lock(project)
    rec = require(lock, args.skill)
    source = args.source or lock.get("source")
    mine_root = local_root(project, rec)

    if not os.path.isdir(mine_root):
        sys.exit("%s is missing from disk." % rec["path"])
    if rec.get("merging"):
        sys.exit("A merge is already in progress for %s.\n"
                 "Resolve the conflicts, then: python install.py accept %s"
                 % (args.skill, args.skill))

    scratch = tempfile.mkdtemp(prefix="akos-update-")
    try:
        sub = rec["origin"].replace("/", os.sep)
        ref = args.ref or "HEAD"
        base_root = os.path.join(
            materialize(source, rec["commit"], os.path.join(scratch, "base")), sub)
        theirs_dir = materialize(source, ref, os.path.join(scratch, "theirs"))
        theirs_root = os.path.join(theirs_dir, sub)
        new_commit = git(["rev-parse", ref], cwd=source) if os.path.isdir(source) \
            else git(["rev-parse", "HEAD"], cwd=theirs_dir)

        if new_commit == rec["commit"]:
            print("%s is already at %s (upstream has not moved)."
                  % (args.skill, new_commit[:7]))
            return 0
        if not os.path.isdir(base_root):
            sys.exit("Cannot reconstruct the original at %s - was the tool moved or "
                     "renamed upstream?\nCompare by hand with 'diff'."
                     % rec["commit"][:7])
        if not os.path.isdir(theirs_root):
            sys.exit("%s no longer exists upstream at %s." % (rec["origin"], ref))

        base, theirs, mine = walk(base_root), walk(theirs_root), walk(mine_root)
        every = sorted(set(base) | set(theirs) | set(mine))

        def same(a_root, b_root, rel):
            a, b = os.path.join(a_root, rel), os.path.join(b_root, rel)
            return (os.path.isfile(a) and os.path.isfile(b)
                    and digest(a) == digest(b))

        took, kept, added_up, removed, conflicts = [], [], [], [], []

        for rel in every:
            in_base, in_theirs, in_mine = rel in base, rel in theirs, rel in mine
            target = os.path.join(mine_root, rel.replace("/", os.sep))

            if in_base and in_theirs and in_mine:
                if same(base_root, theirs_root, rel):
                    if not same(base_root, mine_root, rel):
                        kept.append(rel)                    # ours only
                    continue
                if same(base_root, mine_root, rel):
                    shutil.copy2(os.path.join(theirs_root, rel), target)
                    took.append(rel)                        # fast-forward
                    continue
                rc = merge_file(target, os.path.join(base_root, rel),
                                os.path.join(theirs_root, rel))
                if rc == 0:
                    took.append(rel + "  (merged)")
                else:
                    if rc < 0:                              # binary: keep ours
                        shutil.copy2(os.path.join(theirs_root, rel),
                                     target + ".upstream")
                        conflicts.append(rel + "  (binary; theirs left as .upstream)")
                    else:
                        conflicts.append(rel)
            elif in_theirs and not in_base:
                if in_mine:
                    if not same(theirs_root, mine_root, rel):
                        conflicts.append(rel + "  (added on both sides)")
                else:
                    parent = os.path.dirname(target)
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    shutil.copy2(os.path.join(theirs_root, rel), target)
                    added_up.append(rel)
            elif in_base and not in_theirs and in_mine:
                if same(base_root, mine_root, rel):
                    os.remove(target)
                    removed.append(rel)
                else:
                    conflicts.append(rel + "  (deleted upstream, modified here)")
            elif in_mine and not in_base and not in_theirs:
                kept.append(rel + "  (local addition)")

        print("%s  %s -> %s" % (args.skill, rec["commit"][:7], new_commit[:7]))
        for rel in took:
            print("  updated   %s" % rel)
        for rel in added_up:
            print("  new       %s" % rel)
        for rel in removed:
            print("  removed   %s" % rel)
        for rel in kept:
            print("  kept      %s" % rel)
        for rel in conflicts:
            print("  CONFLICT  %s" % rel)
        if not (took or added_up or removed or kept or conflicts):
            print("  already up to date")

        if conflicts:
            rec["merging"] = {"commit": new_commit, "conflicts": conflicts}
            save_lock(project, lock)
            print("\n%d conflict(s). The lock still points at %s, so this stays "
                  "retryable." % (len(conflicts), rec["commit"][:7]))
            print("Resolve the markers, then: python install.py accept %s"
                  % args.skill)
            return 1

        rec["commit"] = new_commit
        rec["updated"] = dt.date.today().isoformat()
        rec["files"] = hashes(mine_root)
        save_lock(project, lock)
        print("\nLock updated to %s." % new_commit[:7])
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def cmd_accept(args):
    """Record the copy on disk as intended: re-hash, and finish any merge."""
    project = os.path.abspath(args.project)
    lock = load_lock(project)
    rec = require(lock, args.skill)
    root = local_root(project, rec)
    if not os.path.isdir(root):
        sys.exit("%s is missing from disk." % rec["path"])

    leftovers = [p for p in walk(root)
                 if p.endswith(".upstream")
                 or CONFLICT_MARKER in read_text(os.path.join(root, p))]
    if leftovers and not args.force:
        sys.exit("Unresolved merge output still present:\n  %s\n"
                 "Resolve these first, or pass --force." % "\n  ".join(leftovers))

    merging = rec.pop("merging", None)
    if merging:
        rec["commit"] = merging["commit"]
        rec["updated"] = dt.date.today().isoformat()
    if args.message:
        rec["local_changes"] = args.message
    rec["files"] = hashes(root)
    save_lock(project, lock)

    print("Accepted %s at %s (%d files)."
          % (args.skill, rec["commit"][:7], len(rec["files"])))
    if merging:
        print("  merge to %s completed" % merging["commit"][:7])
    if args.message:
        print("  declared: %s" % args.message)
    elif not merging:
        print("  no reason recorded - pass -m to say why this copy differs")
    return 0


# --- entry point ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest="command")

    def project_args(sub):
        sub.add_argument("--project", default=".", help="project root (default: cwd)")
        sub.add_argument("--source", help="catalogue clone or URL (default: from the lock)")

    p = subs.add_parser("list", help="show what the catalogue publishes")
    p.add_argument("--catalogue", default=CATALOGUE)
    p.set_defaults(func=cmd_list)

    p = subs.add_parser("add", help="vendor a skill into a project")
    p.add_argument("skill")
    p.add_argument("--into", default=".", help="project root (default: cwd)")
    p.add_argument("--dest", default=DEFAULT_DEST,
                   help="skills directory (default: %s)" % DEFAULT_DEST)
    p.add_argument("--catalogue", default=CATALOGUE)
    p.add_argument("--source", help="URL to record (default: the catalogue's origin)")
    p.add_argument("--force", action="store_true", help="overwrite an existing copy")
    p.set_defaults(func=cmd_add)

    p = subs.add_parser("status", help="compare installed copies against the lock")
    p.add_argument("--check", action="store_true",
                   help="exit 1 on any difference (for CI)")
    project_args(p)
    p.set_defaults(func=cmd_status)

    p = subs.add_parser("diff", help="show ours vs upstream")
    p.add_argument("skill")
    p.add_argument("--ref", help="upstream ref (default: HEAD)")
    project_args(p)
    p.set_defaults(func=cmd_diff)

    p = subs.add_parser("update", help="three-way merge upstream changes in")
    p.add_argument("skill")
    p.add_argument("--ref", help="upstream ref (default: HEAD)")
    project_args(p)
    p.set_defaults(func=cmd_update)

    p = subs.add_parser("accept", help="record the current copy as intended")
    p.add_argument("skill")
    p.add_argument("-m", "--message", help="why this copy differs from upstream")
    p.add_argument("--force", action="store_true", help="accept even with merge markers")
    project_args(p)
    p.set_defaults(func=cmd_accept)

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
