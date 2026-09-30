#!/usr/bin/env python3
"""Run the existing Google Scholar Zotero push implementation.

This wrapper gives the layered google_scholar skill a stable script path while
leaving the existing gs-export skill untouched.
"""

import runpy
import sys
from pathlib import Path


def main():
    script_path = Path(__file__).resolve().parents[2] / "gs-export" / "scripts" / "push_to_zotero.py"
    if not script_path.exists():
        print(f"Error: Zotero push script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
