#!/usr/bin/env python3
"""Disaster recovery validation for the active production database backend.

Validates:
- backup recency against RPO targets
- restore tooling/readiness against the active backend
- S3 failover behavior (when configured)

Usage:
    python -m scripts.disaster_recovery_validation
    python -m scripts.disaster_recovery_validation --database-url postgresql://...
    python -m scripts.disaster_recovery_validation --check-rpo
    python -m scripts.disaster_recovery_validation --test-s3-failover
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.backup_restore_drill import (
    DEFAULT_DATABASE_URL,
    backup_pattern_for_target,
    resolve_database_target,
)

RTO_HOURS = 4
RPO_HOURS = 1
BACKUP_DIR = Path("data/backups")
DR_REPORT_DIR = Path("data/dr_reports")


def check_backup_recency(
    *,
    database_url: str | None = None,
    backup_dir: Path = BACKUP_DIR,
) -> dict[str, Any]:
    """Verify that the latest backend-specific backup is inside the RPO window."""
    target = resolve_database_target(database_url or DEFAULT_DATABASE_URL)
    if not backup_dir.exists():
        return {
            "status": "fail",
            "reason": "No backup directory found",
            "backend": target.dialect,
            "rpo_hours": RPO_HOURS,
        }

    backups = sorted(
        backup_dir.glob(backup_pattern_for_target(target)),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        return {
            "status": "fail",
            "reason": f"No {target.dialect} backup files found",
            "backend": target.dialect,
            "rpo_hours": RPO_HOURS,
        }

    latest = backups[0]
    age = datetime.now(UTC) - datetime.fromtimestamp(latest.stat().st_mtime, UTC)
    age_hours = age.total_seconds() / 3600
    return {
        "status": "pass" if age_hours <= RPO_HOURS else "fail",
        "backend": target.dialect,
        "latest_backup": str(latest),
        "backup_age_hours": round(age_hours, 2),
        "rpo_target_hours": RPO_HOURS,
        "within_rpo": age_hours <= RPO_HOURS,
        "backup_count": len(backups),
    }


def estimate_restore_time(
    *,
    database_url: str | None = None,
    backup_dir: Path = BACKUP_DIR,
) -> dict[str, Any]:
    """Estimate restore readiness and tooling support for the active backend."""
    target = resolve_database_target(database_url or DEFAULT_DATABASE_URL)
    latest_backups = sorted(
        backup_dir.glob(backup_pattern_for_target(target)),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )
    latest_backup = latest_backups[0] if latest_backups else None

    if target.dialect == "postgresql":
        required_tools = ["pg_dump", "pg_restore", "psql", "createdb", "dropdb"]
        missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
        size_bytes = latest_backup.stat().st_size if latest_backup else 0
        size_mb = size_bytes / (1024 * 1024)
        estimated_minutes = max(1.0, size_mb / 250.0)
        return {
            "backend": target.dialect,
            "latest_backup": str(latest_backup) if latest_backup else None,
            "backup_size_mb": round(size_mb, 2),
            "estimated_restore_minutes": round(estimated_minutes, 1),
            "rto_target_hours": RTO_HOURS,
            "within_rto": (estimated_minutes / 60) <= RTO_HOURS,
            "missing_tools": missing_tools,
            "status": "pass"
            if latest_backup is not None and not missing_tools and (estimated_minutes / 60) <= RTO_HOURS
            else "fail",
        }

    sqlite_path = target.sqlite_path
    if not sqlite_path or not sqlite_path.exists():
        return {"status": "skip", "backend": target.dialect, "reason": "SQLite database not found"}

    db_size_mb = sqlite_path.stat().st_size / (1024 * 1024)
    estimated_minutes = max(1.0, db_size_mb / 100.0)
    return {
        "backend": target.dialect,
        "db_size_mb": round(db_size_mb, 2),
        "estimated_restore_minutes": round(estimated_minutes, 1),
        "rto_target_hours": RTO_HOURS,
        "within_rto": (estimated_minutes / 60) <= RTO_HOURS,
        "status": "pass" if (estimated_minutes / 60) <= RTO_HOURS else "fail",
    }


def test_s3_failover() -> dict[str, Any]:
    """Validate the documented S3-to-local fallback behavior."""
    s3_enabled = os.environ.get("S3_ENABLED", "false").lower() == "true"
    allow_fallback = os.environ.get("ALLOW_LOCAL_STORAGE_FALLBACK", "true").lower() == "true"

    if not s3_enabled:
        return {
            "status": "skip",
            "reason": "S3 not enabled; local storage is the only active path",
            "local_fallback_enabled": allow_fallback,
        }

    s3_bucket = os.environ.get("S3_BUCKET", "document-portal")
    s3_endpoint = os.environ.get("S3_ENDPOINT_URL", "")
    result: dict[str, Any] = {
        "s3_enabled": True,
        "s3_bucket": s3_bucket,
        "s3_endpoint": s3_endpoint or "AWS default",
        "local_fallback_enabled": allow_fallback,
    }

    try:
        import boto3

        client_kwargs: dict[str, Any] = {"service_name": "s3"}
        if s3_endpoint:
            client_kwargs["endpoint_url"] = s3_endpoint
        boto3.client(**client_kwargs).head_bucket(Bucket=s3_bucket)
        result["s3_primary_status"] = "reachable"
        result["status"] = "pass"
    except ImportError:
        result["s3_primary_status"] = "boto3 not installed"
        result["status"] = "skip"
    except Exception as exc:  # policy: DEGRADED - failover validation should report primary outage and fallback truthfully
        result["s3_primary_status"] = f"unreachable: {exc}"
        result["status"] = "pass" if allow_fallback else "fail"
        result["failover_to_local"] = allow_fallback
    return result


def run_full_validation(*, database_url: str | None = None) -> dict[str, Any]:
    """Run all DR validation checks."""
    target = resolve_database_target(database_url or DEFAULT_DATABASE_URL)
    report = {
        "validated_at": datetime.utcnow().isoformat(),
        "backend": target.dialect,
        "database_url": target.database_url,
        "targets": {"rto_hours": RTO_HOURS, "rpo_hours": RPO_HOURS},
        "checks": {},
    }

    print("=" * 60)
    print("  DISASTER RECOVERY VALIDATION")
    print(f"  Backend: {target.dialect} | RTO: {RTO_HOURS}h | RPO: {RPO_HOURS}h")
    print("=" * 60)
    print()

    print("Check 1: Backup recency (RPO)...")
    rpo = check_backup_recency(database_url=target.database_url)
    report["checks"]["backup_recency"] = rpo
    print(f"  {'PASS' if rpo['status'] == 'pass' else 'FAIL'} {rpo.get('reason', rpo.get('latest_backup', 'no backup'))}")

    print("Check 2: Restore tooling/readiness (RTO)...")
    rto = estimate_restore_time(database_url=target.database_url)
    report["checks"]["restore_time"] = rto
    print(
        f"  {'PASS' if rto['status'] == 'pass' else 'FAIL'} "
        f"Est. restore: {rto.get('estimated_restore_minutes', '?')}min"
    )

    print("Check 3: S3 failover simulation...")
    s3 = test_s3_failover()
    report["checks"]["s3_failover"] = s3
    print(f"  {'PASS' if s3['status'] == 'pass' else 'FAIL' if s3['status'] == 'fail' else 'SKIP'} {s3.get('reason', s3.get('s3_primary_status', 'checked'))}")

    statuses = [check["status"] for check in report["checks"].values()]
    report["overall_status"] = "fail" if "fail" in statuses else "pass"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate disaster recovery readiness")
    parser.add_argument("--database-url", default=None, help="SQLAlchemy database URL")
    parser.add_argument("--check-rpo", action="store_true", help="Only check RPO")
    parser.add_argument("--test-s3-failover", action="store_true", help="Only test S3 failover")
    args = parser.parse_args()

    if args.check_rpo:
        result = check_backup_recency(database_url=args.database_url)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] != "fail" else 1)

    if args.test_s3_failover:
        result = test_s3_failover()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] != "fail" else 1)

    report = run_full_validation(database_url=args.database_url)
    DR_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DR_REPORT_DIR / f"dr_validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report saved to: {report_path}")
    sys.exit(0 if report["overall_status"] == "pass" else 1)


if __name__ == "__main__":
    main()
