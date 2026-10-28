#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for brief.py. Builds its own briefs in a temporary folder and never
touches a real project. One line per check; exits 1 on the first failure.

    python smoke_test.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brief as B                                               # noqa: E402

TODAY = date(2026, 10, 28)


def ok(cond, what):
    print("  %s  %s" % ("ok  " if cond else "FAIL", what))
    if not cond:
        sys.exit(1)


def write(folder, name, text):
    path = os.path.join(folder, name)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


LEAN = """# P1 Test — Project Brief

**Size:** lean · **Written:** 2026-10-20 · **Last revised:** 2026-10-20 · **Serves:** G-1, B-1

> **To** test the reader **so that** the format has one reader.

## Why

Because.

## Outcome and done-when

The reader reads every brief the same way.

Done when:

1. Parsed.
2. Checked.

**Stop if:** nobody reads briefs.
"""

FULL_TABLE = """
### Measures

| ID | Measure | Role | Kind | C/A | Baseline | From | Target | By | How measured | Every | Current | As of | Source | WBS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Briefs read | lead | N | C | 0 | 2026-10-01 | 12 | soon | count | fortnight | 3 | 2026-10-20 | guessed | |
"""


def main():
    tmp = tempfile.mkdtemp(prefix="brief-smoke-")
    try:
        prj = os.path.join(tmp, "P1 Test")
        prjmgm = os.path.join(prj, "00. PrjMgm")
        os.makedirs(prjmgm)

        path = B.new(prjmgm, "P1 Test", size="lean", serves="G-1", today=TODAY)
        text = io.open(path, encoding="utf-8").read()
        ok(text.startswith("# P1 Test — Project Brief"), "new fills the title")
        ok("**Size:** lean · **Written:** 2026-10-28 · **Last revised:** 2026-10-28 · **Serves:** G-1" in text,
           "new fills the size, both dates and Serves")
        try:
            B.new(prjmgm, "P1 Test")
            ok(False, "new refuses a folder that already has a brief")
        except SystemExit:
            ok(True, "new refuses a folder that already has a brief")
        parts = B.read(path)
        ok(parts["size"] == "lean" and parts["serves"] == "G-1", "a new brief reads back its header")
        ok(parts["outcome"] is None, "the template's prompt is not taken for an outcome")
        os.remove(path)

        path = write(prjmgm, "04. Project Brief.md", LEAN)
        ok(B.resolve(prj) == path, "a project folder resolves to a numbered brief in its PrjMgm folder")
        ok(B.find(prj) is None, "find never searches below the folder it is given")
        parts = B.read(path)
        ok(parts["statement"] == "To test the reader so that the format has one reader.", "the executive statement")
        ok(parts["outcome"] == "The reader reads every brief the same way.", "the outcome sentence")
        ok(parts["done_when"] == ["Parsed.", "Checked."], "the done-when items")
        ok(parts["stop_if"] == "nobody reads briefs.", "the Stop if line")
        ok(B.serves_list(parts["serves"]) == ["G-1", "B-1"], "Serves, as a list")
        ok(B.check(parts, today=TODAY) == [], "a sound lean brief has no findings")
        ok(B.check(parts, runs_wbs=True, today=TODAY) == ["lean, but the project runs a WBS - grow it to full"],
           "a lean brief on a project with a WBS is told to grow")
        ok(B.check(parts, today=date(2026, 12, 1)) == ["revisit due: last revised 2026-10-20"],
           "a brief not revised for a month is due a revisit")

        pt = B.parse(LEAN.replace("> **To** test the reader **so that** the format has one reader.",
                                  "> **Para** testar o leitor **para que** o formato tenha um leitor."))
        ok(pt["statement"] == "Para testar o leitor para que o formato tenha um leitor.",
           "a statement in another language is still the statement")

        full = B.parse(LEAN.replace("**Size:** lean", "**Size:** full"))
        ok("full, but no Measures table" in B.check(full, today=TODAY), "a full brief with no Measures table")
        full = B.parse(LEAN.replace("**Size:** lean", "**Size:** full") + FULL_TABLE)
        found = B.check(full, today=TODAY)
        ok(len(full["rows"]) == 1 and full["rows"][0]["ID"] == "M1", "the Measures table's rows")
        for want in ("M1: Source 'guessed' is not measured / estimated / asked",
                     "M1: Every 'fortnight' is not week / sprint / month / quarter / year",
                     "M1: By 'soon' is not a date (YYYY-MM-DD)",
                     "no lag measure: lead measures alone show activity, not value"):
            ok(want in found, "finding: %s" % want)

        bare = B.parse("# P2\n\n## Why\n\nNothing else.\n")
        found = B.check(bare, today=TODAY)
        for want in ("no Size line (lean or full)", "no executive statement (To ... so that ...)",
                     "no outcome sentence under Outcome and done-when", "no done-when items",
                     "no Stop if line", "no Last revised date, so its revisit cannot be judged"):
            ok(want in found, "finding: %s" % want)

        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        run = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, "brief.py")] + list(a),
                                        capture_output=True, text=True, encoding="utf-8", env=env)
        p = run("check", prj, "--today", "2026-10-28")
        ok(p.returncode == 0 and "sound" in p.stdout, "check on a sound brief exits 0")
        p = run("check", prj, "--wbs", "--today", "2026-10-28")
        ok(p.returncode == 1 and "grow it to full" in p.stdout, "check with --wbs exits 1 with the finding")
        p = run("show", prj, "--json")
        ok(p.returncode == 0 and '"outcome": "The reader reads every brief the same way."' in p.stdout,
           "show --json gives what readers take")
        p = run("show", tmp)
        ok(p.returncode != 0 and "No Project Brief" in p.stderr, "a folder with no brief is refused")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("All checks passed.")


if __name__ == "__main__":
    main()
