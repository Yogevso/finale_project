#!/usr/bin/env python3
"""AA-006: Backup / restore game-day drill script.

Automates: take backup → corrupt DB → restore → verify data integrity.
Designed as a runbook exercise for validating backup procedures.

Usage:
    python -m scripts.backup_restore_drill
    python -m scripts.backup_restore_drill --db-path data/portal.db
    python -m scripts.backup_restore_drill --backup-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def compute_checksum(path: Path) -> str:
    """SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_row_counts(db_path: Path) -> dict[str, int]:
    """Get row counts for all tables in the database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    counts: dict[str, int] = {}
    for table in sorted(tables):
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = -1
    conn.close()
    return counts


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    """Create a timestamped backup of the database."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"portal_backup_{timestamp}.db"

    # Use SQLite online backup API for consistency
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    src.backup(dst)
    src.close()
    dst.close()

    return backup_path


def verify_backup(original_path: Path, backup_path: Path) -> dict:
    """Verify backup integrity by comparing row counts."""
    original_counts = get_row_counts(original_path)
    backup_counts = get_row_counts(backup_path)

    mismatches = {}
    for table, count in original_counts.items():
        backup_count = backup_counts.get(table, -1)
        if count != backup_count:
            mismatches[table] = {"original": count, "backup": backup_count}

    return {
        "original_checksum": compute_checksum(original_path),
        "backup_checksum": compute_checksum(backup_path),
        "checksums_match": compute_checksum(original_path) == compute_checksum(backup_path),
        "table_count_mismatches": mismatches,
        "tables_verified": len(original_counts),
        "integrity_ok": len(mismatches) == 0,
    }


def simulate_corruption(db_path: Path) -> Path:
    """Create a corrupted copy of the database for drill purposes."""
    corrupted_path = db_path.with_suffix(".corrupted.db")
    shutil.copy2(db_path, corrupted_path)

    # Write garbage bytes in the middle of the file to simulate corruption
    with open(corrupted_path, "r+b") as f:
        f.seek(4096)  # Skip header
        f.write(b"\x00\xFF\xDE\xAD" * 256)

    return corrupted_path


def restore_from_backup(backup_path: Path, target_path: Path) -> bool:
    """Restore database from backup."""
    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}")
        return False

    # Verify backup is a valid SQLite file
    try:
        conn = sqlite3.connect(str(backup_path))
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
        conn.close()
    except sqlite3.DatabaseError:
        print(f"ERROR: Backup file is corrupted: {backup_path}")
        return False

    shutil.copy2(backup_path, target_path)
    return True


def run_drill(db_path: Path, backup_dir: Path) -> dict:
    """Execute the full backup/restore drill."""
    report: dict = {
        "drill_started_at": datetime.utcnow().isoformat(),
        "db_path": str(db_path),
        "steps": [],
    }

    # Step 1: Verify source database
    print("Step 1: Verifying source database...")
    try:
        original_counts = get_row_counts(db_path)
        report["steps"].append({
            "step": "verify_source",
            "status": "pass",
            "tables": len(original_counts),
            "total_rows": sum(v for v in original_counts.values() if v >= 0),
        })
        print(f"  ✓ {len(original_counts)} tables, {sum(v for v in original_counts.values() if v >= 0)} total rows")
    except Exception as e:
        report["steps"].append({"step": "verify_source", "status": "fail", "error": str(e)})
        print(f"  ✗ {e}")
        return report

    # Step 2: Create backup
    print("Step 2: Creating backup...")
    backup_path = create_backup(db_path, backup_dir)
    report["backup_path"] = str(backup_path)
    report["steps"].append({"step": "create_backup", "status": "pass", "path": str(backup_path)})
    print(f"  ✓ Backup created: {backup_path}")

    # Step 3: Verify backup
    print("Step 3: Verifying backup integrity...")
    verification = verify_backup(db_path, backup_path)
    report["steps"].append({"step": "verify_backup", "status": "pass" if verification["integrity_ok"] else "fail", **verification})
    if verification["integrity_ok"]:
        print(f"  ✓ Backup verified — {verification['tables_verified']} tables match")
    else:
        print(f"  ✗ Verification failed: {verification['table_count_mismatches']}")

    # Step 4: Simulate corruption (in temp dir)
    print("Step 4: Simulating corruption...")
    with tempfile.TemporaryDirectory() as tmp:
        corrupted_db = Path(tmp) / "corrupted.db"
        shutil.copy2(db_path, corrupted_db)
        # Write garbage to simulate corruption
        with open(corrupted_db, "r+b") as f:
            f.seek(4096)
            f.write(b"\x00\xFF\xDE\xAD" * 256)
        report["steps"].append({"step": "simulate_corruption", "status": "pass"})
        print("  ✓ Corruption simulated")

        # Step 5: Restore
        print("Step 5: Restoring from backup...")
        restored_db = Path(tmp) / "restored.db"
        success = restore_from_backup(backup_path, restored_db)
        report["steps"].append({"step": "restore", "status": "pass" if success else "fail"})
        if success:
            print("  ✓ Database restored from backup")
        else:
            print("  ✗ Restore failed")
            return report

        # Step 6: Verify restoration
        print("Step 6: Verifying restored database...")
        restore_verification = verify_backup(db_path, restored_db)
        report["steps"].append({
            "step": "verify_restoration",
            "status": "pass" if restore_verification["integrity_ok"] else "fail",
            **restore_verification,
        })
        if restore_verification["integrity_ok"]:
            print(f"  ✓ Restored database verified — all {restore_verification['tables_verified']} tables match")
        else:
            print(f"  ✗ Restoration verification failed")

    report["drill_completed_at"] = datetime.utcnow().isoformat()
    report["overall_status"] = "pass" if all(s["status"] == "pass" for s in report["steps"]) else "fail"

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup/restore game-day drill")
    parser.add_argument("--db-path", default="data/portal.db", help="Path to SQLite database")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup output directory")
    parser.add_argument("--backup-only", action="store_true", help="Only create a backup")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    backup_dir = Path(args.backup_dir)

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    if args.backup_only:
        backup_path = create_backup(db_path, backup_dir)
        verification = verify_backup(db_path, backup_path)
        print(f"Backup created: {backup_path}")
        print(f"Checksum: {verification['backup_checksum']}")
        print(f"Integrity: {'OK' if verification['integrity_ok'] else 'FAILED'}")
        return

    print("=" * 60)
    print("  BACKUP / RESTORE GAME-DAY DRILL")
    print("=" * 60)
    print()

    report = run_drill(db_path, backup_dir)

    print()
    print("=" * 60)
    print(f"  DRILL RESULT: {report['overall_status'].upper()}")
    print("=" * 60)

    # Save report
    report_path = backup_dir / f"drill_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
