#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read and write a Stakeholder Register.

    python stk.py add-group <reg> "Site team" --purpose "..."
    python stk.py add       <reg> "Name" --role "..." --groups G.1,G.2 --power High --interest Low
                                  --current Neutral --desired Supportive --share external
    python stk.py add-comm  <reg> "Weekly site update" --mode push --audience G.1
                                  --cadence weekly --channel email
    python stk.py set       <reg> --id S.4 --current Supportive --reason "..."
    python stk.py contact   <reg> --id S.4 --email name@example.com --phone "+00 ..."
    python stk.py done      <reg> --id C.2 [--on 2026-10-13] [--note "..."]
    python stk.py audience  <reg> --id C.2 [--split]
    python stk.py due       <reg>... | --all [--root DIR]  [--as-of DATE] [--within DAYS] [--overdue]
    python stk.py gaps      <reg>... | --all [--root DIR]
    python stk.py check     <reg> | --all [--root DIR]
    python stk.py list      <reg> [--what stakeholders|groups|communications|all]
    python stk.py show      <reg> --id S.4

`<reg>` is the register's JSON, or the project folder that holds it. `--all`
reads every register under `--root` (default: the current folder). Every write
to the register goes through here, and each appends a change log row. Contact
details never enter the register or its log: `contact` writes the CSV beside
it, which is kept out of git. No row is ever deleted - it goes Inactive.
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R                                            # noqa: E402
import stk_register as STK                                      # noqa: E402
import stk_schema as S                                          # noqa: E402

# CLI option -> (field, vocabulary or None). By collection.
OPTIONS = {
    S.GROUPS: [("name", "Name", None), ("purpose", "Purpose", None),
               ("status", "Status", "status")],
    S.STAKEHOLDERS: [("name", "Name", None), ("role", "Role", None),
                     ("org", "Organisation", None), ("groups", "Groups", None),
                     ("power", "Power", "level"), ("interest", "Interest", "level"),
                     ("current", "Current", "engagement"), ("desired", "Desired", "engagement"),
                     ("stake", "Stake", None), ("action", "Engagement Action", None),
                     ("share", "Share Level", "share_level"), ("status", "Status", "status"),
                     ("notes", "Notes", None)],
    S.COMMS: [("what", "What", None), ("report", "Report", "report"),
              ("mode", "Mode", "mode"), ("audience", "Audience", None),
              ("cadence", "Cadence", "cadence"), ("channel", "Channel", None),
              ("owner", "Owner", None), ("last_done", "Last Done", None),
              ("status", "Status", "status"), ("notes", "Notes", None)],
}
ALL_OPTS = sorted(set(o for opts in OPTIONS.values() for o, _, _ in opts))


def today(value=None):
    return S.parse_date(value, "--on") if value else dt.date.today().isoformat()


def as_list(value):
    out = []
    for part in str(value).split(","):
        ref = S.norm_id(part)
        if part.strip() and not ref:
            sys.exit("%r is not an ID (G.1, S.4, C.2)." % part.strip())
        if ref and ref not in out:
            out.append(ref)
    return out


def coerce(data, field, vocab, value):
    """Validate one value. "" means clear. Exits on a bad value."""
    if value == "":
        return ""
    if field in S.LIST_FIELDS:
        return as_list(value)
    if field in S.DATE_FIELDS:
        return S.parse_date(value, field)
    if vocab == "cadence":
        if S.cadence_kind(value) not in S.vocabulary(data, "cadence"):
            sys.exit("Cadence %r is not one of: %s (on event takes what: 'on event: <what>')"
                     % (value, ", ".join(S.vocabulary(data, "cadence"))))
        return value.strip()
    if vocab:
        words = S.vocabulary(data, vocab)
        match = [w for w in words if w.lower() == value.strip().lower()]
        if not match:
            sys.exit("%s %r is not one of: %s" % (field, value, ", ".join(words)))
        return match[0]
    return value.strip()


def values_from(args, data, coll):
    values = {}
    for opt, field, vocab in OPTIONS[coll]:
        value = getattr(args, opt, None)
        if value is not None:
            values[field] = coerce(data, field, vocab, value)
    return values


def referenced(data, values):
    """Refuse a Groups or Audience entry that names nothing in the register."""
    known = set(r.get("ID") for c in (S.GROUPS, S.STAKEHOLDERS) for r in R.rows(data, c))
    groups = set(r.get("ID") for r in R.rows(data, S.GROUPS))
    for ref in values.get("Groups") or []:
        if ref not in groups:
            sys.exit("Group %s does not exist - add it first (add-group)." % ref)
    for ref in values.get("Audience") or []:
        if ref not in known:
            sys.exit("Audience %s is neither a group nor a stakeholder here." % ref)


def describe(field, old, new):
    show = lambda v: ", ".join(v) if isinstance(v, list) else ("" if v is None else str(v))
    return "%s: %s -> %s" % (field, show(old) or "(none)", show(new) or "(none)")


def apply(row, values):
    changes = []
    for field, value in values.items():
        old = row.get(field)
        if value in ("", []):
            if field in row:
                del row[field]
                changes.append(describe(field, old, None))
        elif old != value:
            row[field] = value
            changes.append(describe(field, old, value))
    return changes


def log_change(data, item, changes, reason, on):
    log = R.rows(data, S.CHANGES)
    log.append({"ID": max([c.get("ID", 0) for c in log] or [0]) + 1, "Changed On": on,
                "Item": item, "Change": "; ".join(changes), "Reason": reason or ""})


def next_id(data, coll):
    nums = [S.parse_id(r.get("ID"))[1] for r in R.rows(data, coll) if S.parse_id(r.get("ID"))]
    return "%s.%d" % (S.PREFIX[coll], max(nums or [0]) + 1)


def find_row(data, ref):
    rid = S.norm_id(ref)
    if not rid:
        sys.exit("%r is not an ID (G.1, S.4, C.2)." % ref)
    coll = S.COLLECTION[rid[0]]
    for row in R.rows(data, coll):
        if row.get("ID") == rid:
            return coll, row
    sys.exit("No %s in the register." % rid)


def finish(args, path, data, message):
    print(message)
    if getattr(args, "dry_run", False):
        print("\n  dry run - nothing written.")
        return 0
    R.save(path, data)
    findings = STK.check(data, path)
    errors = [f for f in findings if f[0] == "error"]
    print("\n  check   %d error(s), %d warning(s)" % (len(errors), len(findings) - len(errors)))
    for _, item, msg in errors[:5]:
        print("          ERROR %s %s" % (item, msg))
    for name, _ in R.stale_views(path):
        print("  note: %s is now stale - rerun refresh_stk.py" % name)
    return 0


# --- writes -------------------------------------------------------------------------

def add_row(args, coll, first_field, title):
    path = STK.resolve(args.register)
    data = R.load(path)
    rows = R.rows(data, coll)
    if any(S.clean(r.get(first_field)).lower() == title.strip().lower() and S.is_active(r)
           for r in rows):
        sys.exit("An active row is already called %r - check before adding a second." % title)
    values = {first_field: title.strip()}
    values.update(dict((f, v) for f, v in values_from(args, data, coll).items()
                       if f != first_field and v not in ("", [])))
    values.setdefault("Status", "Active")
    if coll == S.STAKEHOLDERS:
        values.setdefault("Share Level", "owner")
    referenced(data, values)
    rid = next_id(data, coll)
    row = {"ID": rid}
    apply(row, values)
    rows.append(row)
    on = today(args.on)
    log_change(data, rid, ["added"], args.reason or "Added.", on)
    return finish(args, path, data, "Added %s  %s" % (rid, title))


def cmd_add_group(args):
    return add_row(args, S.GROUPS, "Name", args.name)


def cmd_add(args):
    return add_row(args, S.STAKEHOLDERS, "Name", args.name)


def cmd_add_comm(args):
    return add_row(args, S.COMMS, "What", args.what_text)


def cmd_set(args):
    path = STK.resolve(args.register)
    data = R.load(path)
    coll, row = find_row(data, args.id)
    allowed = set(o for o, _, _ in OPTIONS[coll])
    stray = [o for o in ALL_OPTS if getattr(args, o, None) is not None and o not in allowed]
    if stray:
        sys.exit("%s has no %s." % (row["ID"], ", ".join("--" + o.replace("_", "-") for o in stray)))
    values = values_from(args, data, coll)
    if not values:
        sys.exit("Nothing to set.")
    referenced(data, values)
    changes = apply(row, values)
    if not changes:
        print("%s already holds those values - nothing written." % row["ID"])
        return 0
    log_change(data, row["ID"], changes, args.reason, today(args.on))
    return finish(args, path, data, "%s\n  %s" % (row["ID"], "\n  ".join(changes)))


def cmd_done(args):
    """A communication happened: stamp Last Done. A skip is not recorded."""
    path = STK.resolve(args.register)
    data = R.load(path)
    coll, row = find_row(data, args.id)
    if coll != S.COMMS:
        sys.exit("`done` is for a communication (C.n), not %s." % row["ID"])
    on = today(args.on)
    changes = apply(row, {"Last Done": on})
    if not changes:
        print("%s already done on %s - nothing written." % (row["ID"], on))
        return 0
    log_change(data, row["ID"], changes, args.note or "Done.", on)
    return finish(args, path, data, "%s  %s - done %s" % (row["ID"], row.get("What"), on))


def cmd_contact(args):
    """Write the stakeholder's row in the contacts CSV. Never the register."""
    path = STK.resolve(args.register)
    data = R.load(path)
    coll, row = find_row(data, args.id)
    if coll != S.STAKEHOLDERS:
        sys.exit("Contacts are for stakeholders (S.n), not %s." % row["ID"])
    cpath = STK.contacts_path(path, data)
    contacts, columns, _ = STK.read_contacts(cpath)
    card = contacts.get(row["ID"]) or {"ID": row["ID"]}
    card.setdefault("Name", row.get("Name", ""))
    card.setdefault("Organisation", row.get("Organisation", ""))
    changed = []
    for opt, col in (("email", "Email"), ("phone", "Phone"), ("other", "Other"),
                     ("preferred", "Preferred channel"), ("name", "Name"),
                     ("org", "Organisation")):
        value = getattr(args, opt, None)
        if value is not None and card.get(col, "") != value.strip():
            card[col] = value.strip()
            changed.append(col)
    contacts[row["ID"]] = card
    if args.dry_run:
        print("%s  %s - would update %s (dry run)" % (row["ID"], card["Name"], ", ".join(changed) or "nothing"))
        return 0
    STK.write_contacts(cpath, contacts, columns)
    # The values are not echoed: this output may be pasted where git or a log keeps it.
    print("%s  %s - contacts row %s%s" % (row["ID"], card.get("Name"),
                                          "updated: " if changed else "written",
                                          ", ".join(changed)))
    print("  %s (outside git)" % cpath)
    return 0


# --- reads ----------------------------------------------------------------------------

def cmd_audience(args):
    path = STK.resolve(args.register)
    data = R.load(path)
    coll, comm = find_row(data, args.id)
    if coll != S.COMMS:
        sys.exit("`audience` is for a communication (C.n), not %s." % comm["ID"])
    contacts, _, has_file = STK.read_contacts(STK.contacts_path(path, data))
    res = STK.resolve_audience(data, comm, contacts if has_file else None)
    print("%s  %s  [%s, %s, %s]" % (comm["ID"], comm.get("What"), comm.get("Mode", "?"),
                                    comm.get("Cadence", "?"), comm.get("Channel", "?")))
    if res["public"]:
        print("\n  Public: this is a Content Mgm plan's audience, not a list of people.")
        print("  %s" % comm.get("Channel"))
        return 0
    print("  Share level: %s%s" % (res["share_level"],
                                   " - the external copy goes to everyone below, or --split"
                                   if res["share_level"] == "external" and not args.split else ""))
    groups = [("owner", [p for p in res["people"] if p["Share Level"] == "owner"]),
              ("external", [p for p in res["people"] if p["Share Level"] == "external"])] \
        if args.split else [(None, res["people"])]
    for level, people in groups:
        if not people:
            continue
        if level:
            print("\n  -- %s copy --" % level)
        print("")
        for p in people:
            print("  %-5s %-28s %-6s %s" % (p["ID"], p["Name"][:28], p["Field"], p["Address"] or "(no address)"))
        addrs = [p["Address"] for p in people if p["Address"] and p["Field"] == "Email"]
        if addrs:
            print("\n  To: %s" % "; ".join(addrs))
    for ref in res["unknown"]:
        print("  ERROR audience names %s, which does not exist" % ref)
    if res["missing"]:
        print("\n  No address for: %s" % ", ".join(res["missing"]))
    if not has_file:
        print("\n  No contacts file - names only.")
    print("\n  Nothing is sent. When it goes: stk.py done <reg> --id %s" % comm["ID"])
    return 0


def root_of(args):
    root = os.path.abspath(args.root or os.getcwd())
    if not os.path.isdir(root):
        sys.exit("No folder %s." % root)
    return root


def registers_from(args):
    if args.all:
        found = STK.all_registers(root_of(args))
        if not found:
            print("  No stakeholder register under %s." % root_of(args))
        return found
    if not args.registers:
        sys.exit("Name a register (or its folder), or pass --all.")
    return [STK.resolve(r) for r in args.registers]


def cmd_due(args):
    as_of = dt.date.fromisoformat(S.parse_date(args.as_of, "--as-of")) if args.as_of else dt.date.today()
    rows = []
    for path in registers_from(args):
        data = R.load(path)
        sprints = STK.sprint_calendar(path)
        if not sprints and any(S.cadence_kind(c.get("Cadence")) == "per sprint" and S.is_active(c)
                               for c in R.rows(data, S.COMMS)):
            print("  %s: no sprint calendar (agile conventions or WBS) - per sprint read as every 14 days"
                  % data["meta"].get("scope", ""))
        for comm in R.rows(data, S.COMMS):
            state, when = STK.due(comm, as_of, sprints, args.within)
            if state in ("overdue", "due") or (state == "event" and args.events):
                if args.overdue and state != "overdue":
                    continue
                rows.append((state, data["meta"].get("scope", ""), comm, when))
    order = {"overdue": 0, "due": 1, "event": 2}
    for state, scope, comm, when in sorted(rows, key=lambda r: (order[r[0]], r[1], r[2]["ID"])):
        print("  %-8s %-24s %-5s %-34s %-11s %s" % (
            state, scope[:24], comm["ID"], S.clean(comm.get("What"))[:34], comm.get("Cadence", ""),
            ("due %s" % when.isoformat()) if when else "on event"))
    print("\n  %d communication(s) as of %s%s" % (
        len(rows), as_of.isoformat(), " (within %d days)" % args.within if args.within else ""))
    return 0


def cmd_gaps(args):
    """Active stakeholders below the engagement wanted, with no action to close it."""
    n = 0
    for path in registers_from(args):
        data = R.load(path)
        for p in R.rows(data, S.STAKEHOLDERS):
            if S.is_active(p) and S.gap(p, data) and not S.clean(p.get("Engagement Action")):
                n += 1
                print("  %-24s %-5s %-26s %s -> %s" % (data["meta"].get("scope", "")[:24], p["ID"],
                                                      p.get("Name", "")[:26], p.get("Current"), p.get("Desired")))
    print("\n  %d gap(s) with no engagement action" % n)
    return 0


def cmd_check(args):
    if args.all:
        root = root_of(args)
        total = 0
        for path in STK.all_registers(root):
            data = R.load(path)
            findings = STK.check(data, path)
            total += len([f for f in findings if f[0] == "error"])
            print("%s  %d finding(s)" % (data["meta"].get("scope"), len(findings)))
            for sev, item, msg in findings:
                print("  %-7s %-6s %s" % (sev.upper() if sev == "error" else sev, item or "", msg))
        across = STK.check_all(root)
        print("\nAcross projects  %d finding(s)" % len(across))
        for sev, item, msg in across:
            print("  %-7s %s: %s" % (sev, item, msg))
        return 1 if total else 0
    path = STK.resolve(args.registers[0]) if args.registers else sys.exit("Name a register, or --all.")
    data = R.load(path)
    findings = STK.check(data, path)
    for sev, item, msg in findings:
        print("  %-7s %-6s %s" % (sev.upper() if sev == "error" else sev, item or "", msg))
    errors = len([f for f in findings if f[0] == "error"])
    print("\n  %d stakeholder(s), %d group(s), %d communication(s) - %d error(s), %d warning(s)" % (
        len(R.rows(data, S.STAKEHOLDERS)), len(R.rows(data, S.GROUPS)), len(R.rows(data, S.COMMS)),
        errors, len(findings) - errors))
    return 1 if errors else 0


def cmd_list(args):
    path = STK.resolve(args.register)
    data = R.load(path)
    show_all = args.what == "all"
    if show_all or args.what == "groups":
        print("Groups")
        for g in R.rows(data, S.GROUPS):
            members = [p["ID"] for p in R.rows(data, S.STAKEHOLDERS)
                       if g["ID"] in (p.get("Groups") or []) and S.is_active(p)]
            print("  %-5s %-8s %-28s %s" % (g["ID"], g.get("Status", ""), g.get("Name", "")[:28],
                                            ", ".join(members)))
    if show_all or args.what == "stakeholders":
        print("Stakeholders")
        for p in R.rows(data, S.STAKEHOLDERS):
            gap = S.gap(p, data)
            print("  %-5s %-8s %-24s %-22s %-16s %-24s %s" % (
                p["ID"], p.get("Status", ""), p.get("Name", "")[:24], p.get("Role", "")[:22],
                S.quadrant(p), "%s -> %s" % (p.get("Current", "?"), p.get("Desired", "?"))
                + (" (gap %d)" % gap if gap else ""), ", ".join(p.get("Groups") or [])))
    if show_all or args.what == "communications":
        print("Communications")
        sprints = STK.sprint_calendar(path)
        for c in R.rows(data, S.COMMS):
            state, when = STK.due(c, dt.date.today(), sprints)
            print("  %-5s %-30s %-11s %-12s %-14s %s" % (
                c["ID"], c.get("What", "")[:30], c.get("Mode", ""), c.get("Cadence", "")[:12],
                ", ".join(c.get("Audience") or [])[:14],
                "%s%s" % (state, " %s" % when.isoformat() if when else "")))
    return 0


def cmd_show(args):
    path = STK.resolve(args.register)
    data = R.load(path)
    coll, row = find_row(data, args.id)
    for field in S.FIELDS[coll]:
        if field in row:
            v = row[field]
            print("  %-18s %s" % (field, ", ".join(v) if isinstance(v, list) else v))
    if coll == S.STAKEHOLDERS:
        print("  %-18s %s" % ("(quadrant)", S.quadrant(row) or "-"))
        print("  %-18s %s" % ("(gap)", S.gap(row, data)))
    if coll == S.COMMS:
        state, when = STK.due(row, dt.date.today(), STK.sprint_calendar(path))
        print("  %-18s %s%s" % ("(due)", state, " %s" % when.isoformat() if when else ""))
    mine = [f for f in STK.check(data, path) if f[1] == row["ID"]]
    for sev, _, msg in mine:
        print("  %-7s %s" % (sev, msg))
    log = [c for c in R.rows(data, S.CHANGES) if c.get("Item") == row["ID"]][-5:]
    if log:
        print("\n  Last changes:")
        for c in log:
            print("    %s %s - %s" % (c.get("Changed On"), c.get("Change"), c.get("Reason", "")))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = p.add_subparsers(dest="command")

    def writes(sub):
        sub.add_argument("register", help="the register's JSON, or the folder that holds it")
        sub.add_argument("--on", metavar="YYYY-MM-DD", help="date of the change (default: today)")
        sub.add_argument("--dry-run", action="store_true")
        sub.add_argument("--reason", help="why - goes into the change log")

    def fields(sub, coll, skip=()):
        for opt, field, vocab in OPTIONS[coll]:
            if opt in skip:
                continue
            hint = field
            if vocab:
                hint += ": " + ", ".join(S.VOCABULARIES[vocab])
            if field in S.LIST_FIELDS:
                hint += " (comma-separated IDs; replaces the list)"
            sub.add_argument("--" + opt.replace("_", "-"), help=hint)

    s = subs.add_parser("add-group", help="add a group (an audience)")
    writes(s)
    s.add_argument("name")
    fields(s, S.GROUPS, skip=("name",))
    s.set_defaults(func=cmd_add_group)

    s = subs.add_parser("add", help="add a stakeholder")
    writes(s)
    s.add_argument("name")
    fields(s, S.STAKEHOLDERS, skip=("name",))
    s.set_defaults(func=cmd_add)

    s = subs.add_parser("add-comm", help="add a communication")
    writes(s)
    s.add_argument("what_text", metavar="what")
    fields(s, S.COMMS, skip=("what", "last_done"))
    s.set_defaults(func=cmd_add_comm)

    s = subs.add_parser("set", help="change fields on a group, stakeholder or communication")
    writes(s)
    s.add_argument("--id", required=True)
    for opt in ALL_OPTS:
        s.add_argument("--" + opt.replace("_", "-"))
    s.set_defaults(func=cmd_set)

    s = subs.add_parser("done", help="a communication happened: stamp Last Done")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("--on", metavar="YYYY-MM-DD")
    s.add_argument("--note")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_done)

    s = subs.add_parser("contact", help="write a stakeholder's row in the contacts CSV (outside git)")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    for opt in ("email", "phone", "other", "preferred", "name", "org"):
        s.add_argument("--" + opt)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_contact)

    s = subs.add_parser("audience", help="who a communication goes to, with addresses")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.add_argument("--split", action="store_true", help="separate owner and external lists")
    s.set_defaults(func=cmd_audience)

    s = subs.add_parser("due", help="communications due or overdue")
    s.add_argument("registers", nargs="*")
    s.add_argument("--all", action="store_true", help="every register under --root")
    s.add_argument("--root", help="the folder --all walks (default: the current one)")
    s.add_argument("--as-of", metavar="YYYY-MM-DD")
    s.add_argument("--within", type=int, default=0, metavar="DAYS",
                   help="also list calendar cadences falling due within DAYS")
    s.add_argument("--overdue", action="store_true", help="overdue only")
    s.add_argument("--events", action="store_true", help="also list on-event communications")
    s.set_defaults(func=cmd_due)

    s = subs.add_parser("gaps", help="stakeholders below the engagement wanted, with no action")
    s.add_argument("registers", nargs="*")
    s.add_argument("--all", action="store_true", help="every register under --root")
    s.add_argument("--root", help="the folder --all walks (default: the current one)")
    s.set_defaults(func=cmd_gaps)

    s = subs.add_parser("check", help="audit a register and its contacts; --all adds across projects")
    s.add_argument("registers", nargs="*")
    s.add_argument("--all", action="store_true", help="every register under --root")
    s.add_argument("--root", help="the folder --all walks (default: the current one)")
    s.set_defaults(func=cmd_check)

    s = subs.add_parser("list", help="list the register")
    s.add_argument("register")
    s.add_argument("--what", default="all", choices=["all", "groups", "stakeholders", "communications"])
    s.set_defaults(func=cmd_list)

    s = subs.add_parser("show", help="one row in full, with what is derived")
    s.add_argument("register")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_show)

    args = p.parse_args()
    if not getattr(args, "command", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
