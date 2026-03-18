#!/usr/bin/env python3
"""AA-010: SOC2 evidence collection script.

Gathers compliance evidence: user access logs, config change logs,
uptime metrics, test results — outputs as a compliance bundle.

Usage:
    python -m scripts.soc2_evidence_collector
    python -m scripts.soc2_evidence_collector --output-dir data/compliance
    python -m scripts.soc2_evidence_collector --days 90
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def collect_user_access_logs(db_path: Path, days: int) -> dict:
    """CC6.1 — Logical access controls: user login history."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Active/inactive users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 0")
    inactive_users = cursor.fetchone()[0]

    # User sessions in period
    try:
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE created_at >= ?", (cutoff,))
        sessions = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        sessions = 0

    # Security events (failed logins, lockouts)
    try:
        cursor.execute("SELECT event_type, COUNT(*) FROM security_events WHERE created_at >= ? GROUP BY event_type", (cutoff,))
        security_events = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        security_events = {}

    # Role distribution
    cursor.execute("SELECT role, COUNT(*) FROM users WHERE is_active = 1 GROUP BY role")
    role_distribution = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return {
        "evidence_type": "user_access_logs",
        "period_days": days,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "sessions_in_period": sessions,
        "security_events": security_events,
        "role_distribution": role_distribution,
    }


def collect_config_change_logs(db_path: Path, days: int) -> dict:
    """CC8.1 — Change management: system configuration changes."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Audit logs for system config changes
    cursor.execute(
        """SELECT COUNT(*) FROM audit_logs
           WHERE action = 'system' AND created_at >= ?""",
        (cutoff,),
    )
    system_changes = cursor.fetchone()[0]

    cursor.execute(
        """SELECT action, COUNT(*) FROM audit_logs
           WHERE created_at >= ?
           GROUP BY action ORDER BY COUNT(*) DESC""",
        (cutoff,),
    )
    action_distribution = {row[0]: row[1] for row in cursor.fetchall()}

    # Admin actions (approval workflow)
    try:
        cursor.execute(
            """SELECT status, COUNT(*) FROM admin_actions
               WHERE created_at >= ?
               GROUP BY status""",
            (cutoff,),
        )
        admin_actions = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        admin_actions = {}

    conn.close()
    return {
        "evidence_type": "config_change_logs",
        "period_days": days,
        "system_events": system_changes,
        "action_distribution": action_distribution,
        "admin_actions_by_status": admin_actions,
    }


def collect_data_integrity_evidence(db_path: Path) -> dict:
    """CC6.5 — Data integrity: audit log signature verification."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE signature IS NOT NULL")
    signed = cursor.fetchone()[0]

    # Check for immutability triggers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'prevent_audit%'")
    triggers = [row[0] for row in cursor.fetchall()]

    conn.close()
    return {
        "evidence_type": "data_integrity",
        "total_audit_entries": total,
        "signed_entries": signed,
        "unsigned_entries": total - signed,
        "immutability_triggers": triggers,
        "immutability_enforced": len(triggers) >= 2,
    }


def collect_test_results() -> dict:
    """CC7.1 — System monitoring: test suite results."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=no", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        output = result.stdout.strip().split("\n")
        summary_line = output[-1] if output else ""
        return {
            "evidence_type": "test_results",
            "exit_code": result.returncode,
            "summary": summary_line,
            "all_passed": result.returncode == 0,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {
            "evidence_type": "test_results",
            "exit_code": -1,
            "error": str(e),
            "all_passed": False,
        }


def collect_uptime_metrics() -> dict:
    """A1.1 — Availability: service uptime indicators."""
    # Check if backend health endpoint is reachable
    import urllib.request

    health_url = "http://localhost:8000/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            body = json.loads(resp.read().decode())
        return {
            "evidence_type": "uptime_metrics",
            "health_check_status": status,
            "health_response": body,
            "service_reachable": True,
        }
    except Exception:
        return {
            "evidence_type": "uptime_metrics",
            "service_reachable": False,
            "note": "Service not running at time of evidence collection",
        }


def generate_bundle(db_path: Path, days: int, output_dir: Path, skip_tests: bool = False) -> dict:
    """Generate the full SOC2 compliance evidence bundle."""
    print("=" * 60)
    print("  SOC2 EVIDENCE COLLECTION")
    print(f"  Period: last {days} days")
    print("=" * 60)
    print()

    bundle = {
        "generated_at": datetime.utcnow().isoformat(),
        "period_days": days,
        "evidence": {},
    }

    # 1. User access logs
    print("Collecting user access logs...")
    bundle["evidence"]["user_access"] = collect_user_access_logs(db_path, days)
    print(f"  ✓ {bundle['evidence']['user_access']['active_users']} active users")

    # 2. Config change logs
    print("Collecting configuration change logs...")
    bundle["evidence"]["config_changes"] = collect_config_change_logs(db_path, days)
    print(f"  ✓ {bundle['evidence']['config_changes']['system_events']} system events")

    # 3. Data integrity
    print("Collecting data integrity evidence...")
    bundle["evidence"]["data_integrity"] = collect_data_integrity_evidence(db_path)
    enforced = bundle["evidence"]["data_integrity"]["immutability_enforced"]
    print(f"  ✓ Immutability {'enforced' if enforced else 'NOT enforced'}")

    # 4. Uptime
    print("Collecting uptime metrics...")
    bundle["evidence"]["uptime"] = collect_uptime_metrics()
    reachable = bundle["evidence"]["uptime"]["service_reachable"]
    print(f"  ✓ Service {'reachable' if reachable else 'not running'}")

    # 5. Test results (optional — slow)
    if not skip_tests:
        print("Running test suite for evidence...")
        bundle["evidence"]["test_results"] = collect_test_results()
        passed = bundle["evidence"]["test_results"]["all_passed"]
        print(f"  ✓ Tests {'passed' if passed else 'FAILED'}")
    else:
        print("Skipping test suite (--skip-tests)")

    # Save bundle
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bundle_path = output_dir / f"soc2_evidence_{timestamp}.json"
    bundle_path.write_text(json.dumps(bundle, indent=2))

    print()
    print("=" * 60)
    print(f"  Evidence bundle saved to: {bundle_path}")
    print("=" * 60)

    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="SOC2 evidence collection")
    parser.add_argument("--db-path", default="data/portal.db", help="Path to SQLite database")
    parser.add_argument("--output-dir", default="data/compliance", help="Output directory")
    parser.add_argument("--days", type=int, default=90, help="Evidence period in days")
    parser.add_argument("--skip-tests", action="store_true", help="Skip test suite execution")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    generate_bundle(db_path, args.days, Path(args.output_dir), skip_tests=args.skip_tests)


if __name__ == "__main__":
    main()
