#!/usr/bin/env python3
"""
Create a new WBS file from the AI-First template.

Usage:
    python create_wbs.py "<output-path>" "<project-name>"

Copies the template structure with clean headers and an example row.
"""

import sys
import shutil
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent


def main():
    if len(sys.argv) < 3:
        print("Usage: create_wbs.py <output-path> <project-name>")
        sys.exit(1)

    output_path = sys.argv[1]
    project_name = sys.argv[2]

    template = TEMPLATE_DIR / "WBS Template.xlsx"
    if not template.exists():
        print(f"Template not found: {template}")
        sys.exit(1)

    shutil.copy2(str(template), output_path)
    print(f"Created new WBS: {output_path}")
    print(f"  Template: {template}")
    print(f"  Project: {project_name}")
    print("  Remove the [Example] rows and start adding your items.")


if __name__ == '__main__':
    main()
