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
import subprocess
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


def resolve_git_ref(explicit_ref: str | None, env_var: str, fallback: str) -> str:
    value = (explicit_ref or os.getenv(env_var, "")).strip()
    if value and value != "0000000000000000000000000000000000000000":
        return value
    return fallback


def scan_new_markers_from_diff(root: Path, base_ref: str, head_ref: str) -> list[Hit]:
    diff_cmd = ["git", "diff", "--unified=0", "--no-color", base_ref, head_ref]
    try:
        diff_text = subprocess.check_output(diff_cmd, cwd=root, text=True, encoding="utf-8")
    except subprocess.CalledProcessError as exc:
        print(
            f"Warning: failed to diff {base_ref}..{head_ref} ({exc}); falling back to empty delta.",
            file=sys.stderr,
        )
        return []

    hits: list[Hit] = []
    current_file: str | None = None
    new_line_number: int | None = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            candidate = raw_line[6:]
            ext = os.path.splitext(candidate)[1]
            current_file = candidate if ext in EXTENSIONS else None
            continue

        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            new_line_number = int(match.group(1)) if match else None
            continue

        if current_file is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            text = raw_line[1:]
            for marker_match in MARKERS.finditer(text):
                hits.append(
                    Hit(
                        file=current_file,
                        line=new_line_number or 0,
                        marker=marker_match.group(1).upper(),
                        text=text.strip()[:120],
                    )
                )
            if new_line_number is not None:
                new_line_number += 1
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue

        if raw_line.startswith(" ") and new_line_number is not None:
            new_line_number += 1

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
        "--delta-only",
        action="store_true",
        help=(
            "Fail only when NEW debt markers are introduced in git diff "
            "(compares base/head refs; does not fail on historical debt)."
        ),
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Git base ref/sha for --delta-only (defaults to GITHUB_BASE_SHA / GITHUB_BEFORE_SHA / HEAD~1).",
    )
    parser.add_argument(
        "--head-ref",
        default=None,
        help="Git head ref/sha for --delta-only (defaults to GITHUB_HEAD_SHA / HEAD).",
    )
    parser.add_argument(
        "--max-new",
        type=int,
        default=0,
        help="Maximum allowed NEW markers when --delta-only is enabled (default: 0).",
    )
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

    new_hits: list[Hit] = []
    new_counts: Counter[str] = Counter()
    new_total = 0
    delta_over_budget = False
    base_ref = None
    head_ref = None
    if args.delta_only:
        base_ref = resolve_git_ref(args.base_ref, "GITHUB_BASE_SHA", "")
        if not base_ref:
            base_ref = resolve_git_ref(None, "GITHUB_BEFORE_SHA", "HEAD~1")
        head_ref = resolve_git_ref(args.head_ref, "GITHUB_HEAD_SHA", "HEAD")
        new_hits = scan_new_markers_from_diff(root, base_ref, head_ref)
        new_counts = Counter(h.marker for h in new_hits)
        new_total = len(new_hits)
        delta_over_budget = new_total > args.max_new

    if args.as_json:
        print(
            json.dumps(
                {
                    "total": total,
                    "budget": args.budget,
                    "over_budget": over_budget,
                    "by_marker": dict(counts),
                    "delta_only": bool(args.delta_only),
                    "base_ref": base_ref,
                    "head_ref": head_ref,
                    "new_total": new_total,
                    "max_new": args.max_new,
                    "new_over_budget": delta_over_budget,
                    "new_by_marker": dict(new_counts),
                    "hits": [h._asdict() for h in hits],
                    "new_hits": [h._asdict() for h in new_hits],
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

    if args.delta_only:
        print("Tech-Debt Delta Report")
        print("======================")
        print(f"Base ref: {base_ref}")
        print(f"Head ref: {head_ref}")
        print()
        for marker in ("TODO", "FIXME", "HACK", "XXX"):
            c = new_counts.get(marker, 0)
            print(f"  NEW {marker:4s}  {c:4d}")
        print("  " + ("-" * 14))
        print(f"  {'NEW TOTAL':8s}  {new_total:4d}  / {args.max_new}")
        print()
        if delta_over_budget:
            print(f"  !  OVER DELTA BUDGET by {new_total - args.max_new}")
            sys.exit(1)
        print("  OK No new tech-debt markers introduced")
        print()
        sys.exit(0)

    sys.exit(1 if over_budget else 0)


if __name__ == "__main__":
    main()
