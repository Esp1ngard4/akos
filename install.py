#!/usr/bin/env python3
"""Install AKOS tools into a project, and keep them in sync afterwards.

    python install.py list
    python install.py init ../my-project --pack project --name "Atlas"
    python install.py add wbs-manager --into ../my-project
    python install.py status
    python install.py status --upstream --source ../akos    # which tools have a newer version
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

With --docs, a tool's definition document (its TD) is placed too, in the
project's own TSP folder, and locked as its own entry: a project that owns and
evolves its TDs still sees where the catalogue's have moved on.

`init` starts a new project from a pack (packs/<name>.json): the pack's tools
added as above, then its structure set up by those installed tools' own
scripts. It refuses a folder that already holds a project; a running project
adds its tools one at a time instead.
"""

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

LOCK_NAME = "tools.lock.json"
DEFAULT_DEST = ".agents/skills"
SKIP = {".git", "__pycache__", ".pytest_cache", ".DS_Store"}
SHARED_NAME = "_shared"
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


def require_clone(catalogue):
    """The lock records the commit a tool came from; that is what lets `update`
    merge later. A ZIP download has no commit, so say so plainly."""
    top = git(["rev-parse", "--show-toplevel"], cwd=catalogue, check=False)
    same = top and os.path.normcase(os.path.abspath(top)) == os.path.normcase(os.path.abspath(catalogue))
    if not same or not git(["rev-parse", "HEAD"], cwd=catalogue, check=False):
        sys.exit("%s is not a git clone (a ZIP download, perhaps).\n"
                 "The lock records the version each tool came from, which is what makes\n"
                 "updates possible, and only a clone has one. Clone it instead:\n"
                 "  git clone https://github.com/Esp1ngard4/akos.git" % os.path.abspath(catalogue))


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


def is_td(rel):
    """A tool definition document at the top of a tool folder: `TD.<n> - <Name>.md`."""
    return "/" not in rel and rel.startswith("TD.") and rel.endswith(".md")


ONLY = {"TD": is_td}


def walk(root, only=None):
    """Every file under root as a sorted list of POSIX-style relative paths.

    `only` names a filter from ONLY: a TD entry is the TD files at the top of
    its folder, never the skills or `_shared/` beside them upstream, nor
    anything else a project keeps in that folder."""
    keep = ONLY.get(only) if only else None
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if name in SKIP:
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            if keep is None or keep(rel):
                out.append(rel)
    return sorted(out)


def hashes(root, only=None):
    return dict((rel, digest(os.path.join(root, rel))) for rel in walk(root, only))


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

    A tool with several skills may also ship `_shared/` - material the skills
    read rather than duplicate. It has no SKILL.md, so it is never offered for
    installation on its own; it travels with whichever skill needs it, and each
    entry below records where to find it.
    """
    found = {}
    tsp = os.path.join(root, "TSP")
    if not os.path.isdir(tsp):
        return found
    for tool in sorted(os.listdir(tsp)):
        tool_dir = os.path.join(tsp, tool)
        if not os.path.isdir(tool_dir):
            continue
        has_shared = os.path.isdir(os.path.join(tool_dir, SHARED_NAME))
        for entry in sorted(os.listdir(tool_dir)):
            skill_dir = os.path.join(tool_dir, entry)
            if os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
                found[entry] = {
                    "path": skill_dir,
                    "tool": tool,
                    "tsp": tool.split(" ")[0],
                    "origin": "TSP/%s/%s" % (tool, entry),
                    "shared": ("TSP/%s/%s" % (tool, SHARED_NAME)
                               if has_shared else None),
                }
    return found


def read_docs(root):
    """Every tool's TD, keyed by its TSP ID: what `add --docs` places.

    A TD is `TD.<n> - <Name>.md` at the top of the tool folder. Every tool has
    one, including a tool with no skill, which is installed by its ID."""
    found = {}
    tsp = os.path.join(root, "TSP")
    if not os.path.isdir(tsp):
        return found
    for tool in sorted(os.listdir(tsp)):
        tool_dir = os.path.join(tsp, tool)
        if not os.path.isdir(tool_dir):
            continue
        tds = [n for n in sorted(os.listdir(tool_dir)) if is_td(n)]
        if tds:
            found[tool.split(" ")[0]] = {"tool": tool, "tsp": tool.split(" ")[0],
                                         "origin": "TSP/%s" % tool, "path": tool_dir, "files": tds}
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


def docs_key(tsp):
    return "%s docs" % tsp


def install_docs(doc, lock, project, docs_rel, catalogue):
    """Place a tool's TD in <docs_rel>/<tool folder>/ and lock it as its own entry.

    Once per tool, as `_shared/` is: a second skill of the same tool finds the
    entry and leaves it alone. The entry carries `only: TD`, so every command
    compares the TD files and nothing else in the folder.
    """
    key = docs_key(doc["tsp"])
    dest_rel = "%s/%s" % (docs_rel.replace(os.sep, "/").strip("/"), doc["tool"])
    dest = os.path.join(project, dest_rel.replace("/", os.sep))
    commit = git(["rev-parse", "HEAD"], cwd=catalogue)
    existing = lock["tools"].get(key)
    if existing and os.path.isdir(dest):
        missing, added, modified = compare(existing["files"], dest, "TD")
        if missing or added or modified:
            print("  %s is present and locally modified - left as it is." % key)
            print("    'status' shows the differences; 'accept' declares them")
            return key, "kept"
        if existing.get("commit") == commit:
            return key, "reused"
    os.makedirs(dest, exist_ok=True)
    for name in walk(dest, "TD"):                      # an older TD of this tool
        os.remove(os.path.join(dest, name))
    for name in doc["files"]:
        shutil.copy2(os.path.join(doc["path"], name), os.path.join(dest, name))
    lock["tools"][key] = {
        "tsp": doc["tsp"],
        "tool": doc["tool"],
        "origin": doc["origin"],
        "path": dest_rel,
        "only": "TD",
        "commit": commit,
        "installed": dt.date.today().isoformat(),
        "files": hashes(dest, "TD"),
    }
    return key, ("refreshed" if existing else "installed")


def shared_key(tsp):
    return "%s%s" % (tsp, SHARED_NAME)


def install_shared(entry, lock, project, dest_parent, dest_parent_rel, catalogue):
    """Place a tool's `_shared/` beside the skill that needs it.

    The skills address it as `../_shared/`, so it has to be a sibling of the
    skill folder rather than live inside it. That makes it shared in the
    destination too: two skills from the same tool install one copy between
    them, which is the point - the contracts have a single owner here and must
    keep one there.

    It is recorded as an ordinary lock entry, so `status`, `diff`, `update` and
    `accept` all operate on it with no special case. It is never offered by
    `list`: it has no SKILL.md, and installing it alone would install nothing
    that runs.
    """
    key = shared_key(entry["tsp"])
    dest = os.path.join(dest_parent, SHARED_NAME)
    dest_rel = "%s/%s" % (dest_parent_rel.rstrip("/"), SHARED_NAME)

    clash = [n for n, r in lock["tools"].items()
             if r.get("path") == dest_rel and r.get("origin") != entry["shared"]]
    if clash:
        sys.exit("%s is already occupied by %s.\n"
                 "Two tools cannot both ship _shared into the same folder. "
                 "Install this skill with a different --dest."
                 % (dest_rel, ", ".join(sorted(clash))))

    commit = git(["rev-parse", "HEAD"], cwd=catalogue)
    existing = lock["tools"].get(key)
    if existing and os.path.isdir(dest):
        missing, added, modified = compare(existing["files"], dest)
        if missing or added or modified:
            print("  %s is present and locally modified - left as it is."
                  % SHARED_NAME)
            print("    'status' shows the differences; 'accept' declares them")
            return key, "kept"
        if existing.get("commit") == commit:
            # The usual case: a second skill from the same tool. One copy
            # serves both, and it is already the right one - do not touch it.
            return key, "reused"
        shutil.rmtree(dest)

    shutil.copytree(os.path.join(catalogue, entry["shared"].replace("/", os.sep)),
                    dest, ignore=shutil.ignore_patterns(*SKIP))
    lock["tools"][key] = {
        "tsp": entry["tsp"],
        "tool": entry["tool"],
        "origin": entry["shared"],
        "path": dest_rel,
        "commit": commit,
        "installed": dt.date.today().isoformat(),
        "shared_for": entry["tool"],
        "files": hashes(dest),
    }
    return key, ("refreshed" if existing else "installed")


def cmd_add(args):
    require_clone(args.catalogue)
    cat = read_catalogue(args.catalogue)
    docs = read_docs(args.catalogue) if args.docs else {}
    tool_id = re.match(r"^TSP\.\d+$", args.skill)
    if tool_id and not args.docs:
        sys.exit("%s is a tool, not a skill: pass --docs <folder> to place its TD,\n"
                 "or name one of its skills (python install.py list)." % args.skill)
    if not tool_id and args.skill not in cat:
        sys.exit("Unknown skill '%s'. Try: python install.py list" % args.skill)

    project = os.path.abspath(args.into)
    if os.path.abspath(args.catalogue) == project:
        sys.exit("Refusing to install into the catalogue itself.\n"
                 "This repo lists tools; it is not a working environment.\n"
                 "Pass --into <your project>.")

    if tool_id:
        if args.skill not in docs:
            sys.exit("No TD for %s in %s/TSP." % (args.skill, args.catalogue))
        lock = load_lock(project)
        if not lock.get("source"):
            lock["source"] = (args.source
                              or git(["remote", "get-url", "origin"],
                                     cwd=args.catalogue, check=False)
                              or os.path.abspath(args.catalogue))
        key, action = install_docs(docs[args.skill], lock, project, args.docs, args.catalogue)
        save_lock(project, lock)
        rec = lock["tools"][key]
        print("TD %s %s -> %s (%d file(s))" % (action, args.skill, rec["path"], len(rec["files"])))
        print("  from %s @ %s" % (lock["source"], rec["commit"][:7]))
        print("\nCommit the TD folder and %s together." % LOCK_NAME)
        return 0
    entry = cat[args.skill]

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

    lock = load_lock(project)
    if not lock.get("source"):
        lock["source"] = (args.source
                          or git(["remote", "get-url", "origin"],
                                 cwd=args.catalogue, check=False)
                          or os.path.abspath(args.catalogue))

    # Shared material first. It is the step that can fail on an occupied or
    # locked folder, and failing before the skill is copied leaves nothing
    # half-installed for the lock to disagree with.
    shared = shared_action = None
    if entry.get("shared"):
        shared, shared_action = install_shared(
            entry, lock, project, parent or project,
            os.path.dirname(dest_rel) or ".", args.catalogue)

    doc_key = doc_action = None
    if args.docs:
        if entry["tsp"] not in docs:
            sys.exit("No TD for %s in %s/TSP." % (entry["tsp"], args.catalogue))
        doc_key, doc_action = install_docs(docs[entry["tsp"]], lock, project, args.docs, args.catalogue)

    shutil.copytree(entry["path"], dest, ignore=shutil.ignore_patterns(*SKIP))

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
    if shared and shared in lock["tools"]:
        srec = lock["tools"][shared]
        print("  + %s %s -> %s (%d files, shared by this tool's skills)"
              % (SHARED_NAME, shared_action, srec["path"], len(srec["files"])))
    if doc_key and doc_key in lock["tools"]:
        drec = lock["tools"][doc_key]
        print("  + TD %s -> %s (%d file(s))" % (doc_action, drec["path"], len(drec["files"])))
    missing = works_with(cat, lock, args.skill)
    if missing:
        print("  Works with, not installed here: %s" % ", ".join(missing))
        print("    python install.py add <name> --into %s" % args.into)
    print("\nCommit the skill folder%s and %s together, so the team gets %s on "
          "clone." % (", its TD" if doc_key else "", LOCK_NAME, "them all" if doc_key else "both"))
    return 0


# --- init: a new project from a pack ----------------------------------------

PACKS = "packs"
# What a freshly created repository may already hold before init.
FRESH = {".git", ".gitignore", ".gitattributes", ".github", "README.md", "LICENSE", "LICENSE.md"}


def read_pack(catalogue, name):
    path = os.path.join(catalogue, PACKS, "%s.json" % name)
    if not os.path.isfile(path):
        have = sorted(n[:-5] for n in os.listdir(os.path.join(catalogue, PACKS)) if n.endswith(".json")) \
            if os.path.isdir(os.path.join(catalogue, PACKS)) else []
        sys.exit("No pack '%s'. Packs: %s" % (name, ", ".join(have) or "none"))
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def next_monday(today=None):
    today = today or dt.date.today()
    return today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)


def run_skill(skills, skill, script, args, cwd):
    path = os.path.join(skills, skill, "scripts", script)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, path] + args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    if p.returncode != 0:
        sys.exit("init stopped at %s %s:\n%s" % (skill, script, (p.stdout + p.stderr)[-1500:]))
    return p.stdout


def numbered_child(parent, name):
    """The entry under `parent` named `name`, numbered or not."""
    for n in os.listdir(parent):
        if n == name or re.match(r"^\d+\.\s*%s$" % re.escape(name), n):
            return os.path.join(parent, n)
    return None


def quiet(fn, ns):
    out, stdout = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        return fn(ns)
    finally:
        sys.stdout = stdout


def cmd_init(args):
    require_clone(args.catalogue)
    pack = read_pack(args.catalogue, args.pack)
    project = os.path.abspath(args.project)
    if os.path.abspath(args.catalogue) == project:
        sys.exit("Refusing to start a project inside the catalogue itself. Pass a folder of your own.")
    os.makedirs(project, exist_ok=True)
    extra = sorted(n for n in os.listdir(project) if n not in FRESH)
    if extra:
        sys.exit("%s already holds a project (%s).\n"
                 "init starts new projects only; add tools to a running one with:\n"
                 "  python install.py add <skill> --into %s" % (project, ", ".join(extra[:4]), args.project))
    first = dt.date.fromisoformat(args.first_day) if args.first_day else next_monday()
    cat = read_catalogue(args.catalogue)
    missing = [s for s in pack["skills"] if s not in cat]
    if missing:
        sys.exit("The pack names skills the catalogue lacks: %s" % ", ".join(missing))

    print("Starting %s from the '%s' pack.\n" % (args.name, args.pack))
    # The top-level folders, as yet unnumbered; a child names its parent.
    where = {}
    for name, _, parent in pack["top"]:
        where[name] = os.path.join(where[parent] if parent else project, name)
        os.makedirs(where[name])
    planning = where[pack["planning"]]

    # Every skill is the product manager's: installed into the planning folder,
    # with its lock beside it, never at the root.
    for skill in pack["skills"]:
        quiet(cmd_add, argparse.Namespace(skill=skill, into=planning, dest=args.dest, catalogue=args.catalogue,
                                          source=args.source, force=False, docs=None))
    print("  installed %d skills into %s/" % (len(pack["skills"]), pack["planning"]))

    def skills():
        return os.path.join(planning, args.dest.replace("/", os.sep))

    # The artifact register describes the whole project: the top folders first
    # (00 onwards, as the pack lists them), then the planning folder's contents,
    # the register's own folder first.
    reg = pack["register"]
    first_id = len(pack["top"])
    art = os.path.join(planning, "%02d. %s" % (first_id, reg["folder"]), reg["file"].format(name=args.name))
    run_skill(skills(), "artifact-register", "create_artifact_register.py", [art, args.name, "--folder"], project)
    ids = {}

    def artifact(path, name, about, parent, kind="Folder", new_id=None):
        nonlocal art, planning
        argv = ["add", art, path, "--root", project, "--name", name, "--type", kind, "--description", about,
                "--parent-digital", str(ids[parent]) if parent is not None else "Main"]
        if new_id is not None:
            argv += ["--new-id", str(new_id)]
        run_skill(skills(), "artifact-register", "artifact.py", argv, project)
        # Re-find what moved: the register may sit inside what was renamed.
        planning = numbered_child(project, pack["planning"])
        art = next(os.path.join(dp, f) for dp, _, fs in os.walk(planning) for f in fs if f == os.path.basename(art))
        ids[name] = new_id if new_id is not None else max(ids.values()) + 1

    for i, (name, about, parent) in enumerate(pack["top"]):
        holder = numbered_child(project, parent) if parent else project
        artifact(numbered_child(holder, name), name, about, parent, new_id=i)
    ids[reg["folder"]] = first_id
    run_skill(skills(), "artifact-register", "artifact.py", ["move", art, "--id", str(first_id), "--parent-digital", str(ids[pack["planning"]])], project)
    for name, about, parent in pack["folders"]:
        holder = numbered_child(planning, parent) if parent else planning
        os.makedirs(os.path.join(holder, name))
        artifact(os.path.join(holder, name), name, about, parent if parent else pack["planning"])

    found = {}
    for dp, dirs, _ in os.walk(project):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for d in dirs:
            m = re.match(r"^\d+\.\s*(.+)$", d)
            if m and m.group(1) not in found:
                found[m.group(1)] = os.path.join(dp, d)
    print("  structure: %s" % ", ".join(sorted(os.path.relpath(p, project).replace(os.sep, "/") for p in found.values())))

    # The tool register, and each tool's TD beside it: the project owns them.
    tools = pack["tools"]
    tsp_dir = found[tools["folder"]]
    with io.open(os.path.join(args.catalogue, "registry", "TSP Register.json"), encoding="utf-8") as fh:
        catalogue_rows = {"TSP.%s" % r["ID"]: r for r in json.load(fh).get("tools", [])}
    by_tool = {}
    for skill in pack["skills"]:
        by_tool.setdefault(cat[skill]["tsp"], []).append(skill)
    register = os.path.join(tsp_dir, tools["file"].format(name=args.name))
    run_skill(skills(), "tsp-manager", "create_tsp.py", [register, "--scope", args.name], project)
    for tsp in sorted(by_tool, key=lambda t: int(t.split(".")[1])):
        quiet(cmd_add, argparse.Namespace(skill=tsp, into=planning, dest=args.dest, catalogue=args.catalogue,
                                          source=args.source, force=False, docs=os.path.relpath(tsp_dir, planning)))
        row = catalogue_rows.get(tsp, {})
        argv = ["register", register, row.get("Name") or tsp, "--upstream", "%s %s" % (tools["upstream"], tsp), "--doc-aux", "Yes",
                "--skill", ", ".join(by_tool[tsp]), "--reason", "Installed from %s %s by install.py init." % (tools["upstream"], tsp)]
        for flag, field in (("--description", "Description"), ("--type", "Type"), ("--relevancy", "Relevancy"),
                            ("--area", "Primary Area"), ("--status", "Status")):
            if row.get(field):
                argv += [flag, str(row[field])]
        td = next((f for f in os.listdir(os.path.join(tsp_dir, cat[by_tool[tsp][0]]["tool"])) if f.startswith("TD.")), None)
        if td:
            argv += ["--links", "%s/%s" % (cat[by_tool[tsp][0]]["tool"], td)]
        run_skill(skills(), "tsp-manager", "tsp.py", argv, project)
    print("  tool register: %d tools, each with its TD and its %s number" % (len(by_tool), tools["upstream"]))

    execution = os.path.basename(found[pack["execution"]])
    values = dict(found, name=args.name, planning=planning, execution=execution, first_day=first.isoformat(),
                  year=str(first.year), days=str(args.sprint_days))
    for step in pack["steps"]:
        skill, script, argv = step[:3]
        run_skill(skills(), skill, script, [a.format(**values) for a in argv], project)
        print("  %s: %s" % (skill, step[3] if len(step) > 3 else script))

    for filename, name, about in pack.get("documents", []):
        path = os.path.join(planning, filename)
        if os.path.exists(path):
            artifact(path, name, about, pack["planning"], kind="Document")
            print("  artifact-register: %s numbered" % filename)

    lines = list(pack.get("gitignore", []))
    for name in pack.get("confidential", []):
        lines.append(os.path.relpath(found[name], project).replace(os.sep, "/") + "/")
    if lines:
        gi = os.path.join(project, ".gitignore")
        have = io.open(gi, encoding="utf-8").read().split("\n") if os.path.exists(gi) else []
        add = [line for line in lines if line not in have]
        if add:
            with io.open(gi, "a", encoding="utf-8") as fh:
                fh.write(("\n" if have and have[-1] else "") + "\n".join(add) + "\n")

    ws_dir = found.get("Workspaces")
    for profile, names in (pack.get("workspaces") or {}).items():
        # "@root" is the project itself. An editor loads the skills of each
        # folder a workspace opens, not of folders nested inside one, so the
        # project-management folder is opened as a folder of its own.
        paths = [project if n == "@root" else found[n] for n in names]
        folders = [{"name": os.path.basename(p), "path": os.path.relpath(p, ws_dir).replace(os.sep, "/")} for p in paths]
        with io.open(os.path.join(ws_dir, "%s.code-workspace" % profile), "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"folders": folders, "settings": {}}, fh, indent=2)
            fh.write("\n")

    print("\n%s is set up: %d skills (%d tools) in %s, sprints of %d days from %s, and its guide in %s."
          % (args.name, len(pack["skills"]), len(by_tool), os.path.basename(planning), args.sprint_days, first.isoformat(),
             os.path.relpath(found.get("Onboarding", planning), project)))
    if ws_dir:
        print("Open %s with your agent, so the skills load." %
              os.path.relpath(os.path.join(ws_dir, "Product manager.code-workspace"), project))
    print("Commit everything, then say to your agent:")
    for line in pack.get("next", []):
        print("  \"%s\"" % line)
    return 0


def works_with(cat, lock, skill):
    """The catalogue's other skills that this skill's SKILL.md names, in
    backticks, and that the project does not have yet. The skill's own text is
    the list, so nothing beside it has to be kept in step."""
    text = read_text(os.path.join(cat[skill]["path"], "SKILL.md"))
    named = set(re.findall(r"`([a-z][a-z0-9-]+)`", text))
    return sorted(n for n in named if n in cat and n != skill and n not in lock["tools"])


def compare(recorded, root, only=None):
    """Recorded hashes vs what is on disk now."""
    if not os.path.isdir(root):
        return sorted(recorded), [], []
    current = hashes(root, only)
    missing = sorted(set(recorded) - set(current))
    added = sorted(set(current) - set(recorded))
    modified = sorted(p for p in set(recorded) & set(current)
                      if recorded[p] != current[p])
    return missing, added, modified


def upstream_changes(clone, rec):
    """The catalogue's commits after the one the lock records that touched this
    entry, newest first, as [(sha, subject)]; None when the clone does not
    have the lock's commit (it needs a pull)."""
    known = subprocess.run(["git", "merge-base", "--is-ancestor", rec["commit"], "HEAD"], cwd=clone,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode
    if known != 0:
        return None
    out = git(["log", "--format=@@commit %h %s", "--name-only", "%s..HEAD" % rec["commit"], "--", rec["origin"]], cwd=clone)
    changes = []
    for block in out.split("@@commit ")[1:]:
        lines = [l for l in block.strip().split("\n") if l.strip()]
        sha, _, subject = lines[0].partition(" ")
        files = [os.path.relpath(f, rec["origin"]).replace(os.sep, "/") for f in lines[1:]]
        # A TD entry covers the TD alone: a change to the skill beside it is not its own.
        if rec.get("only") and not any(is_td(f) for f in files):
            continue
        changes.append((sha, subject))
    return changes


def cmd_status(args):
    project = os.path.abspath(args.project)
    lock = load_lock(project)
    if not lock["tools"]:
        print("No tools installed (%s not found or empty)." % LOCK_NAME)
        return 0

    clone = scratch = None
    if args.upstream:
        source = args.source or lock.get("source")
        if source and os.path.isdir(source):
            require_clone(source)
            clone = source
        else:
            scratch = tempfile.mkdtemp(prefix="akos-upstream-")
            clone = os.path.join(scratch, "akos")
            git(["clone", "-q", source, clone])
    try:
        return _status(args, project, lock, clone)
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)


def _status(args, project, lock, clone):
    dirty, behind, unknown = 0, [], []
    print("source: %s%s\n" % (lock.get("source"), "  (compared with %s at %s)" % (clone, git(["rev-parse", "--short", "HEAD"], cwd=clone)) if clone else ""))
    for name in sorted(lock["tools"]):
        rec = lock["tools"][name]
        missing, added, modified = compare(rec["files"], local_root(project, rec), rec.get("only"))
        merging = rec.get("merging")

        state = "clean"
        if missing or added or modified:
            state = "MODIFIED"
            dirty += 1
        if merging:
            state = "MERGING"
            dirty += 1

        news = ""
        if clone:
            changes = upstream_changes(clone, rec)
            if changes is None:
                unknown.append(name)
                news = "  ? not in the clone: pull it"
            elif changes:
                behind.append(name)
                news = "  %d change(s) behind: %s %s" % (len(changes), changes[0][0], changes[0][1][:60])
            else:
                news = "  up to date"
        print("%-18s %-9s %s @ %s%s" % (name, state, rec["tsp"], rec["commit"][:7], news))
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

    if clone:
        if behind:
            print("\n%d tool(s) have a newer version. To bring them in:" % len(behind))
            for name in behind:
                print('    python install.py update "%s" --project "%s"%s'
                      % (name, args.project, ' --source "%s"' % args.source if args.source else ""))
        elif not unknown:
            print("\nEvery tool is up to date.")
        if unknown:
            print("\nThe clone does not have the commit %d tool(s) came from: git pull it, then run this again." % len(unknown))
    if args.check and dirty:
        print("\n%d tool(s) differ from the lock. If that is intended, run:\n"
              '    python install.py accept <tool> -m "<why>"' % dirty)
        return 1
    if args.check and behind:
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
        mine = local_root(project, rec)
        if rec.get("only"):
            # A TD entry: compare its files one by one, not the folders, which
            # hold more than the TD on either side.
            out = ""
            for rel in sorted(set(walk(theirs, rec["only"])) | set(walk(mine, rec["only"]))):
                a, b = os.path.join(theirs, rel), os.path.join(mine, rel)
                proc = subprocess.run(
                    ["git", "diff", "--no-index", "--",
                     a if os.path.exists(a) else os.devnull, b if os.path.exists(b) else os.devnull],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                out += proc.stdout.decode("utf-8", "replace")
        else:
            proc = subprocess.run(
                ["git", "diff", "--no-index", "--", theirs, mine],
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

        only = rec.get("only")
        base, theirs, mine = walk(base_root, only), walk(theirs_root, only), walk(mine_root, only)
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
        rec["files"] = hashes(mine_root, only)
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
                 if (rec.get("only") is None or ONLY[rec["only"]](p.replace(".upstream", "")))
                 and p.endswith(".upstream")
                 or (rec.get("only") is None or ONLY[rec["only"]](p))
                 and CONFLICT_MARKER in read_text(os.path.join(root, p))]
    if leftovers and not args.force:
        sys.exit("Unresolved merge output still present:\n  %s\n"
                 "Resolve these first, or pass --force." % "\n  ".join(leftovers))

    merging = rec.pop("merging", None)
    if merging:
        rec["commit"] = merging["commit"]
        rec["updated"] = dt.date.today().isoformat()
    if args.message:
        rec["local_changes"] = args.message
    rec["files"] = hashes(root, rec.get("only"))
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

    p = subs.add_parser("add", help="vendor a skill (or, with --docs, a tool's TD) into a project")
    p.add_argument("skill", help="a skill name, or a tool ID (TSP.4) with --docs for its TD alone")
    p.add_argument("--into", default=".", help="project root (default: cwd)")
    p.add_argument("--dest", default=DEFAULT_DEST,
                   help="skills directory (default: %s)" % DEFAULT_DEST)
    p.add_argument("--catalogue", default=CATALOGUE)
    p.add_argument("--source", help="URL to record (default: the catalogue's origin)")
    p.add_argument("--force", action="store_true", help="overwrite an existing copy")
    p.add_argument("--docs", metavar="FOLDER",
                   help="also place the tool's TD in FOLDER/<tool folder>/ (relative to --into), "
                        "locked as its own entry")
    p.set_defaults(func=cmd_add)

    p = subs.add_parser("init", help="start a new project from a pack: its tools and its structure")
    p.add_argument("project", help="the new project's folder (empty, or a fresh repository)")
    p.add_argument("--pack", default="project", help="a pack in packs/ (default: project)")
    p.add_argument("--name", required=True, help="the project's name, e.g. \"Atlas\"")
    p.add_argument("--sprint-days", type=int, default=14, help="sprint length in days (default: 14)")
    p.add_argument("--first-day", metavar="YYYY-MM-DD", help="the first sprint's first day (default: next Monday)")
    p.add_argument("--dest", default=DEFAULT_DEST, help="skills directory (default: %s)" % DEFAULT_DEST)
    p.add_argument("--catalogue", default=CATALOGUE)
    p.add_argument("--source", help="URL to record (default: the catalogue's origin)")
    p.set_defaults(func=cmd_init)

    p = subs.add_parser("status", help="compare installed copies against the lock")
    p.add_argument("--check", action="store_true",
                   help="exit 1 on any difference (for CI); with --upstream, also when a tool is behind")
    p.add_argument("--upstream", action="store_true",
                   help="also say which tools the catalogue has changed since they were installed "
                        "(reads --source, a local clone, or else the lock's URL)")
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
