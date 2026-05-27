#!/usr/bin/env python3
"""Prevent new direct SQL execution in API route handlers."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "backend" / "app" / "api"
BASELINE_FILE = (
    REPO_ROOT / "scripts" / "architecture_checks" / "baselines" / "route_sql_usage_baseline.txt"
)
DIRECT_SQL_RE = re.compile(r"\b(?:db|session)\.execute\s*\(")


def scan_route_sql_usage() -> set[str]:
    hits: set[str] = set()
    for path in sorted(API_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if DIRECT_SQL_RE.search(line):
                hits.add(f"{rel}:{idx}")
    return hits


def read_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    rows = set()
    for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            rows.add(entry)
    return rows


def write_baseline(entries: set[str]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Route-level direct SQL execution baseline",
        "# Managed by scripts/architecture_checks/check_route_sql_usage.py",
        "",
    ]
    BASELINE_FILE.write_text("\n".join(header + sorted(entries)) + "\n", encoding="utf-8")


def _file_counts(entries: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        file_path = entry.rsplit(":", 1)[0]
        counts[file_path] = counts.get(file_path, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    current = scan_route_sql_usage()
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
            "Route SQL baseline is missing or empty. Run:\n"
            "python scripts/architecture_checks/check_route_sql_usage.py --update-baseline"
        )
        return 1

    new_violations = sorted(current - baseline)
    resolved = sorted(baseline - current)

    print(f"Current route direct SQL entries: {len(current)}")
    print(f"Baseline entries: {len(baseline)}")
    if resolved:
        print(f"Resolved baseline entries: {len(resolved)}")

    if new_violations:
        print("New direct SQL route usages detected:")
        for violation in new_violations:
            print(f"- {violation}")
        resolved_counts = _file_counts(set(resolved))
        new_counts = _file_counts(set(new_violations))
        if resolved_counts == new_counts and resolved_counts:
            print(
                "\nHint: detected additions/resolutions are mirrored per file. "
                "This often indicates line-number drift after formatting/refactors. "
                "If no new direct SQL calls were introduced, regenerate baseline with:\n"
                "python scripts/architecture_checks/check_route_sql_usage.py --update-baseline"
            )
        return 1

    print("Route SQL usage check passed (no new direct execute calls in routes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
