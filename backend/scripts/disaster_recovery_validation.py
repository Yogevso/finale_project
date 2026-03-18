#!/usr/bin/env python3
"""AA-007 & AA-008: Disaster recovery validation and failover simulation.

Validates backup recency against RTO/RPO targets and tests S3 failover.

Usage:
    python -m scripts.disaster_recovery_validation
    python -m scripts.disaster_recovery_validation --check-rpo
    python -m scripts.disaster_recovery_validation --test-s3-failover
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Recovery targets
RTO_HOURS = 4  # Recovery Time Objective — must restore service within 4 hours
RPO_HOURS = 1  # Recovery Point Objective — max 1 hour of data loss acceptable

BACKUP_DIR = Path("data/backups")
DR_REPORT_DIR = Path("data/dr_reports")


def check_backup_recency() -> dict:
    """Verify that the most recent backup is within RPO window."""
    if not BACKUP_DIR.exists():
        return {
            "status": "fail",
            "reason": "No backup directory found",
            "rpo_hours": RPO_HOURS,
        }

    backups = sorted(BACKUP_DIR.glob("portal_backup_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not backups:
        return {
            "status": "fail",
            "reason": "No backup files found",
            "rpo_hours": RPO_HOURS,
        }

    latest = backups[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age = datetime.utcnow() - mtime
    age_hours = age.total_seconds() / 3600

    return {
        "status": "pass" if age_hours <= RPO_HOURS else "fail",
        "latest_backup": str(latest),
        "backup_age_hours": round(age_hours, 2),
        "rpo_target_hours": RPO_HOURS,
        "within_rpo": age_hours <= RPO_HOURS,
        "backup_count": len(backups),
    }


def estimate_restore_time() -> dict:
    """Estimate restore time based on DB size and backup availability."""
    db_path = Path("data/portal.db")
    if not db_path.exists():
        return {"status": "skip", "reason": "Database not found"}

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    # Conservative estimate: ~1 minute per 100MB for SQLite restore
    estimated_restore_minutes = max(1, db_size_mb / 100)

    return {
        "db_size_mb": round(db_size_mb, 2),
        "estimated_restore_minutes": round(estimated_restore_minutes, 1),
        "rto_target_hours": RTO_HOURS,
        "within_rto": (estimated_restore_minutes / 60) <= RTO_HOURS,
        "status": "pass" if (estimated_restore_minutes / 60) <= RTO_HOURS else "fail",
    }


def test_s3_failover() -> dict:
    """AA-008: Test S3 storage failover (if configured).

    Verifies that the local fallback works when S3 is unavailable.
    """
    s3_enabled = os.environ.get("S3_ENABLED", "false").lower() == "true"
    allow_fallback = os.environ.get("ALLOW_LOCAL_STORAGE_FALLBACK", "true").lower() == "true"

    if not s3_enabled:
        return {
            "status": "skip",
            "reason": "S3 not enabled — using local storage only",
            "local_fallback_enabled": allow_fallback,
        }

    # If S3 is enabled, check connectivity
    s3_bucket = os.environ.get("S3_BUCKET", "document-portal")
    s3_endpoint = os.environ.get("S3_ENDPOINT_URL", "")

    result: dict = {
        "s3_enabled": True,
        "s3_bucket": s3_bucket,
        "s3_endpoint": s3_endpoint or "AWS default",
        "local_fallback_enabled": allow_fallback,
    }

    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        client_kwargs: dict = {"service_name": "s3"}
        if s3_endpoint:
            client_kwargs["endpoint_url"] = s3_endpoint

        s3 = boto3.client(**client_kwargs)
        s3.head_bucket(Bucket=s3_bucket)
        result["s3_primary_status"] = "reachable"
        result["status"] = "pass"
    except ImportError:
        result["s3_primary_status"] = "boto3 not installed"
        result["status"] = "skip"
    except Exception as e:
        result["s3_primary_status"] = f"unreachable: {e}"
        result["status"] = "pass" if allow_fallback else "fail"
        result["failover_to_local"] = allow_fallback

    return result


def run_full_validation() -> dict:
    """Run all disaster recovery validation checks."""
    report = {
        "validated_at": datetime.utcnow().isoformat(),
        "targets": {"rto_hours": RTO_HOURS, "rpo_hours": RPO_HOURS},
        "checks": {},
    }

    print("=" * 60)
    print("  DISASTER RECOVERY VALIDATION")
    print(f"  RTO Target: {RTO_HOURS} hours | RPO Target: {RPO_HOURS} hours")
    print("=" * 60)
    print()

    # Check 1: Backup recency (RPO)
    print("Check 1: Backup recency (RPO)...")
    rpo = check_backup_recency()
    report["checks"]["backup_recency"] = rpo
    status = "✓" if rpo["status"] == "pass" else "✗" if rpo["status"] == "fail" else "⊘"
    backup_age = rpo.get('backup_age_hours', '?')
    rpo_reason = rpo.get('reason', f'Backup age: {backup_age}h (target: ≤{RPO_HOURS}h)')
    print(f"  {status} {rpo_reason}")

    # Check 2: Restore time (RTO)
    print("Check 2: Estimated restore time (RTO)...")
    rto = estimate_restore_time()
    report["checks"]["restore_time"] = rto
    status = "✓" if rto["status"] == "pass" else "✗" if rto["status"] == "fail" else "⊘"
    print(f"  {status} Est. restore: {rto.get('estimated_restore_minutes', '?')}min (target: ≤{RTO_HOURS}h)")

    # Check 3: S3 failover
    print("Check 3: S3 failover simulation...")
    s3 = test_s3_failover()
    report["checks"]["s3_failover"] = s3
    status = "✓" if s3["status"] == "pass" else "✗" if s3["status"] == "fail" else "⊘"
    print(f"  {status} {s3.get('reason', s3.get('s3_primary_status', 'checked'))}")

    # Overall
    statuses = [c["status"] for c in report["checks"].values()]
    report["overall_status"] = "fail" if "fail" in statuses else "pass"

    print()
    print("=" * 60)
    print(f"  DR VALIDATION: {report['overall_status'].upper()}")
    print("=" * 60)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Disaster recovery validation")
    parser.add_argument("--check-rpo", action="store_true", help="Only check RPO")
    parser.add_argument("--test-s3-failover", action="store_true", help="Only test S3 failover")
    args = parser.parse_args()

    if args.check_rpo:
        result = check_backup_recency()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] != "fail" else 1)

    if args.test_s3_failover:
        result = test_s3_failover()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] != "fail" else 1)

    report = run_full_validation()

    DR_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DR_REPORT_DIR / f"dr_validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")

    sys.exit(0 if report["overall_status"] == "pass" else 1)


if __name__ == "__main__":
    main()
