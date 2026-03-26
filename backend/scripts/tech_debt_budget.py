#!/usr/bin/env python3
"""AB-014: Tech-Debt Budget CI Gate.

Scans the codebase for TODO/FIXME/HACK/XXX markers, counts them, and
exits non-zero if the total exceeds a configurable budget.

Usage:
    python scripts/tech_debt_budget.py                   # default budget 200
    python scripts/tech_debt_budget.py --budget 150      # custom budget
    python scripts/tech_debt_budget.py --json             # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

MARKERS = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}
SKIP_DIRS = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".git",
    "htmlcov",
    ".next",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


class Hit(NamedTuple):
    file: str
    line: int
    marker: str
    text: str


def scan_directory(root: Path) -> list[Hit]:
    hits: list[Hit] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext not in EXTENSIONS:
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, encoding="utf-8", errors="replace") as fh:
                    for lineno, line in enumerate(fh, 1):
                        for m in MARKERS.finditer(line):
                            hits.append(
                                Hit(
                                    file=os.path.relpath(fpath, root),
                                    line=lineno,
                                    marker=m.group(1).upper(),
                                    text=line.strip()[:120],
                                )
                            )
            except OSError:
                continue
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Tech-debt budget checker")
    parser.add_argument(
        "--budget",
        type=int,
        default=200,
        help="Maximum allowed markers (default: 200)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    parser.add_argument(
        "root",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent.parent),
        help="Root directory to scan (default: project root)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    hits = scan_directory(root)
    counts: Counter[str] = Counter(h.marker for h in hits)
    total = len(hits)
    over_budget = total > args.budget

    if args.as_json:
        print(
            json.dumps(
                {
                    "total": total,
                    "budget": args.budget,
                    "over_budget": over_budget,
                    "by_marker": dict(counts),
                    "hits": [h._asdict() for h in hits],
                },
                indent=2,
            )
        )
    else:
        print("\nTech-Debt Budget Report")
        print("=======================\n")
        for marker in ("TODO", "FIXME", "HACK", "XXX"):
            c = counts.get(marker, 0)
            print(f"  {marker:8s}  {c:4d}")
        print("  " + ("-" * 14))
        print(f"  {'TOTAL':8s}  {total:4d}  / {args.budget}")
        print()
        if over_budget:
            print(f"  !  OVER BUDGET by {total - args.budget}")
        else:
            print(f"  OK Within budget ({args.budget - total} remaining)")
        print()

    sys.exit(1 if over_budget else 0)


if __name__ == "__main__":
    main()
