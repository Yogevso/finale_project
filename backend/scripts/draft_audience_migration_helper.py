#!/usr/bin/env python3
"""CLI helper for Wave P draft-audience data remediation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import SessionLocal  # noqa: E402
from app.migrations import (  # noqa: E402
    DraftAudienceMigrationStrategy,
    run_draft_audience_migration,
)

DEFAULT_REPORT_PATH = REPO_ROOT / "data" / "migrations" / "wave-p-draft-audience-migration.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repair draft documents that still use company visibility without assigned companies."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--strategy",
        choices=[strategy.value for strategy in DraftAudienceMigrationStrategy],
        default=DraftAudienceMigrationStrategy.AUTO.value,
        help=(
            "Remediation strategy: "
            "auto (assign owner when possible, else demote), "
            "assign_owner, or demote_internal."
        ),
    )
    parser.add_argument(
        "--actor-user-id",
        type=int,
        default=None,
        help="Optional user id to attribute audit-log entries to.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional candidate limit for incremental rollout.",
    )
    parser.add_argument(
        "--report-file",
        default=str(DEFAULT_REPORT_PATH),
        help="JSON report output path.",
    )
    parser.add_argument(
        "--fail-on-unresolved",
        action="store_true",
        help="Exit with code 1 if unresolved candidates remain.",
    )
    return parser.parse_args()


def _print_summary(payload: dict[str, object], report_file: Path) -> None:
    strategy_value = payload["strategy"]
    if hasattr(strategy_value, "value"):
        strategy_value = strategy_value.value

    print("Wave P draft-audience migration summary:")
    print(f"- mode: {payload['mode']}")
    print(f"- strategy: {strategy_value}")
    print(f"- total_candidates: {payload['total_candidates']}")
    print(f"- applied_count: {payload['applied_count']}")
    print(f"- unresolved_count: {payload['unresolved_count']}")
    print(f"- audit_entries_created: {payload['audit_entries_created']}")
    print(f"- report: {report_file}")


def main() -> int:
    args = parse_args()
    strategy = DraftAudienceMigrationStrategy(args.strategy)
    report_file = Path(args.report_file).resolve()

    db = SessionLocal()
    try:
        report = run_draft_audience_migration(
            db,
            strategy=strategy,
            apply_changes=args.apply,
            actor_user_id=args.actor_user_id,
            limit=args.limit,
        )
    finally:
        db.close()

    payload = asdict(report)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_summary(payload, report_file)

    if args.fail_on_unresolved and report.unresolved_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
