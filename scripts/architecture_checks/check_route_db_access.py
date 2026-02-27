#!/usr/bin/env python3
"""Prevent new direct db.query usage in API route modules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "backend" / "app" / "api"
BASELINE_FILE = (
    REPO_ROOT / "scripts" / "architecture_checks" / "baselines" / "route_db_access_baseline.txt"
)
QUERY_RE = re.compile(r"\bdb\.query\s*\(")


def scan_route_db_queries() -> set[str]:
    hits: set[str] = set()
    for path in sorted(API_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if QUERY_RE.search(line):
                hits.add(f"{rel}:{idx}")
    return hits


def read_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    entries = set()
    for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            entries.add(entry)
    return entries


def write_baseline(entries: set[str]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Route-level direct db.query baseline",
        "# This file is managed by scripts/architecture_checks/check_route_db_access.py",
        "# New entries should fail CI unless baseline is intentionally regenerated.",
        "",
    ]
    body = sorted(entries)
    BASELINE_FILE.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate baseline from current route db.query usage",
    )
    args = parser.parse_args()

    current = scan_route_db_queries()
    if args.update_baseline:
        write_baseline(current)
        print(
            f"Updated baseline at {BASELINE_FILE.relative_to(REPO_ROOT)} "
            f"with {len(current)} entries."
        )
        return 0

    baseline = read_baseline()
    if not baseline:
        print(
            "Route DB baseline is missing or empty. Run:\n"
            "python scripts/architecture_checks/check_route_db_access.py --update-baseline"
        )
        return 1

    new_violations = sorted(current - baseline)
    resolved_since_baseline = sorted(baseline - current)

    print(f"Current route db.query entries: {len(current)}")
    print(f"Baseline entries: {len(baseline)}")

    if resolved_since_baseline:
        print(f"Resolved baseline entries: {len(resolved_since_baseline)}")

    if new_violations:
        print("New direct db.query route usages detected:")
        for violation in new_violations:
            print(f"- {violation}")
        return 1

    print("Route DB access check passed (no new direct db.query usages).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
