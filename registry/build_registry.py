#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate REGISTRY.md from the register.

    python registry/build_registry.py

REGISTRY.md is a generated view, and a generated file whose generator lives
somewhere else is a file that quietly stops matching its source. This is the
generator. Run it after any change to `registry/TSP Register.json`.
"""
import datetime as dt
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "TSP", "TSP.3 TSP Register",
                                "tsp-manager", "scripts"))
import registry as R                                            # noqa: E402
import schema as S                                              # noqa: E402

REGISTER = os.path.join(HERE, "TSP Register.json")
OUTPUT = os.path.join(HERE, "REGISTRY.md")

STATUS_MEANINGS = [
    ("Implemented", "Ready to adopt. Works from a clean checkout."),
    ("In Progress", "Usable but still changing; expect rough edges."),
    ("Planned", "Listed so the number is reserved; not yet built."),
    ("Obsolete", "Superseded. Kept for reference, do not adopt."),
]


def main():
    data = R.load(REGISTER)
    tools = sorted(R.rows(data, S.TOOLS), key=lambda r: int(r["ID"]))

    lines = [
        "# Tool registry", "",
        "<!-- GENERATED FILE - do not edit.",
        "     Source of truth: registry/TSP Register.json",
        "     Regenerate with: python registry/build_registry.py -->", "",
        "What this repository publishes, and how ready each one is.", "",
        "Every tool below is a folder under [`TSP/`](../TSP) containing a definition",
        "document, and — where one makes sense — the skill or skills that operate it.",
        "A tool with no skill is still a tool, and a tool may have more than one; the",
        "skill is an attribute, not the unit.", "",
        "Install one with [`install.py`](../install.py), which records where the copy",
        "came from so it stays reconcilable with upstream:", "",
        "```bash", "python install.py add <skill> --into <your-project>", "```", "",
        "| ID | Tool | Status | Skill | Definition doc |", "|---|---|---|---|---|",
    ]
    for row in tools:
        skills = ", ".join("`%s`" % s for s in S.split_skills(row.get("Skill"))) or "_none_"
        lines.append("| TSP.%s | **%s** | %s | %s | [TD.%s](../%s) |"
                     % (row["ID"], S.tool_name(row), S.clean(row.get("Status")),
                        skills, row["ID"],
                        S.clean(row.get("Links")).replace(" ", "%20")))

    lines += ["", "## What each is for", ""]
    for row in tools:
        lines += ["**TSP.%s %s** — %s" % (row["ID"], S.tool_name(row),
                                          S.clean(row.get("Description"))), ""]

    lines += ["## Status meanings", "", "| Status | Meaning |", "|---|---|"]
    lines += ["| `%s` | %s |" % pair for pair in STATUS_MEANINGS]
    lines += ["", "---", "",
              "Generated from `registry/TSP Register.json` on %s."
              % dt.date.today().isoformat()]

    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("REGISTRY.md regenerated: %d tools" % len(tools))
    for row in tools:
        print("  TSP.%-3s %-20s %s" % (row["ID"], S.tool_name(row),
                                       S.clean(row.get("Skill")) or "(no skill)"))


if __name__ == "__main__":
    main()
