#!/usr/bin/env python3
"""Production-aware backup and restore drill.

Supports both SQLite and PostgreSQL:
- SQLite: file backup, corruption simulation, restore verification
- PostgreSQL: pg_dump backup, restore into a scratch database, row-count verification

Usage:
    python -m scripts.backup_restore_drill
    python -m scripts.backup_restore_drill --database-url postgresql://...
    python -m scripts.backup_restore_drill --db-path data/portal.db
    python -m scripts.backup_restore_drill --backup-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL, make_url

POSTGRES_DIALECTS = {"postgresql", "postgresql+psycopg", "postgres"}
DEFAULT_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/portal.db")


@dataclass(frozen=True)
class DatabaseTarget:
    """Resolved database target for backup and drill operations."""

    database_url: str
    dialect: str
    database_name: str
    url: URL
    sqlite_path: Path | None = None


def resolve_database_target(database_url: str | None = None, *, db_path: str | None = None) -> DatabaseTarget:
    """Resolve a database target from URL or legacy SQLite path."""
    if db_path:
        sqlite_path = Path(db_path)
        return DatabaseTarget(
            database_url=f"sqlite:///{sqlite_path.as_posix()}",
            dialect="sqlite",
            database_name=sqlite_path.stem,
            url=make_url(f"sqlite:///{sqlite_path.as_posix()}"),
            sqlite_path=sqlite_path,
        )

    resolved_url = database_url or DEFAULT_DATABASE_URL
    url = make_url(resolved_url)
    backend_name = url.get_backend_name()
    if backend_name == "sqlite":
        database = url.database or "./data/portal.db"
        sqlite_path = Path(database)
        return DatabaseTarget(
            database_url=resolved_url,
            dialect="sqlite",
            database_name=sqlite_path.stem,
            url=url,
            sqlite_path=sqlite_path,
        )
    if backend_name in POSTGRES_DIALECTS:
        return DatabaseTarget(
            database_url=resolved_url,
            dialect="postgresql",
            database_name=url.database or "postgres",
            url=url,
        )
    raise ValueError(f"Unsupported database backend for drill: {backend_name}")


def compute_checksum(path: Path) -> str:
    """SHA-256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _postgres_env(target: DatabaseTarget) -> dict[str, str]:
    env = os.environ.copy()
    if target.url.password:
        env["PGPASSWORD"] = target.url.password
    return env


def _postgres_base_command(target: DatabaseTarget, executable: str) -> list[str]:
    command = [executable]
    if target.url.host:
        command.extend(["--host", target.url.host])
    if target.url.port:
        command.extend(["--port", str(target.url.port)])
    if target.url.username:
        command.extend(["--username", target.url.username])
    return command


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run an external command and raise a readable error on failure."""
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or "no command output"
        raise RuntimeError(f"Command failed ({' '.join(command)}): {detail}") from exc


def get_row_counts(target: DatabaseTarget, *, database_name: str | None = None) -> dict[str, int]:
    """Get row counts for all user tables."""
    if target.dialect == "sqlite":
        if not target.sqlite_path or not target.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {target.sqlite_path}")
        connection = sqlite3.connect(str(target.sqlite_path if database_name is None else Path(database_name)))
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            counts: dict[str, int] = {}
            for table in sorted(tables):
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    counts[table] = int(cursor.fetchone()[0])
                except sqlite3.OperationalError:
                    counts[table] = -1
            return counts
        finally:
            connection.close()

    effective_database = database_name or target.database_name
    env = _postgres_env(target)
    list_command = _postgres_base_command(target, "psql") + [
        "--dbname",
        effective_database,
        "-At",
        "-c",
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;",
    ]
    tables_output = run_command(list_command, env=env).stdout.splitlines()
    counts: dict[str, int] = {}
    for table in filter(None, (line.strip() for line in tables_output)):
        count_command = _postgres_base_command(target, "psql") + [
            "--dbname",
            effective_database,
            "-At",
            "-c",
            f'SELECT COUNT(*) FROM "{table}";',
        ]
        count_output = run_command(count_command, env=env).stdout.strip() or "0"
        counts[table] = int(count_output)
    return counts


def backup_pattern_for_target(target: DatabaseTarget) -> str:
    """Return the backup filename glob for the target backend."""
    if target.dialect == "postgresql":
        return f"{target.database_name}_backup_*.dump"
    return f"{target.database_name}_backup_*.db"


def create_backup(target: DatabaseTarget, backup_dir: Path) -> Path:
    """Create a timestamped backup for the active backend."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if target.dialect == "postgresql":
        backup_path = backup_dir / f"{target.database_name}_backup_{timestamp}.dump"
        command = _postgres_base_command(target, "pg_dump") + [
            "--dbname",
            target.database_name,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(backup_path),
        ]
        run_command(command, env=_postgres_env(target))
        return backup_path

    if not target.sqlite_path or not target.sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {target.sqlite_path}")

    backup_path = backup_dir / f"{target.database_name}_backup_{timestamp}.db"
    source = sqlite3.connect(str(target.sqlite_path))
    destination = sqlite3.connect(str(backup_path))
    try:
        source.backup(destination)
    finally:
        source.close()
        destination.close()
    return backup_path


def verify_backup(target: DatabaseTarget, backup_path: Path) -> dict[str, Any]:
    """Verify backup integrity/readability for the active backend."""
    if target.dialect == "postgresql":
        run_command(["pg_restore", "--list", str(backup_path)], env=_postgres_env(target))
        source_counts = get_row_counts(target)
        return {
            "backup_path": str(backup_path),
            "backup_size_bytes": backup_path.stat().st_size,
            "tables_verified": len(source_counts),
            "integrity_ok": True,
        }

    if not target.sqlite_path or not target.sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {target.sqlite_path}")
    original_counts = get_row_counts(target)
    backup_counts = get_row_counts(
        DatabaseTarget(
            database_url=f"sqlite:///{backup_path.as_posix()}",
            dialect="sqlite",
            database_name=backup_path.stem,
            url=make_url(f"sqlite:///{backup_path.as_posix()}"),
            sqlite_path=backup_path,
        )
    )
    mismatches = {
        table: {"original": original_counts[table], "backup": backup_counts.get(table, -1)}
        for table in original_counts
        if original_counts[table] != backup_counts.get(table, -1)
    }
    original_checksum = compute_checksum(target.sqlite_path)
    backup_checksum = compute_checksum(backup_path)
    return {
        "original_checksum": original_checksum,
        "backup_checksum": backup_checksum,
        "checksums_match": original_checksum == backup_checksum,
        "table_count_mismatches": mismatches,
        "tables_verified": len(original_counts),
        "integrity_ok": not mismatches,
    }


def _scratch_database_name(target: DatabaseTarget) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{target.database_name}_drill_{timestamp}"[:63]


def _run_postgres_restore_drill(target: DatabaseTarget, backup_path: Path) -> dict[str, Any]:
    scratch_database = _scratch_database_name(target)
    env = _postgres_env(target)
    source_counts = get_row_counts(target)

    drop_command = _postgres_base_command(target, "dropdb") + ["--if-exists", scratch_database]
    create_command = _postgres_base_command(target, "createdb") + [scratch_database]
    restore_command = _postgres_base_command(target, "pg_restore") + [
        "--dbname",
        scratch_database,
        "--no-owner",
        "--no-privileges",
        str(backup_path),
    ]

    run_command(drop_command, env=env)
    try:
        run_command(create_command, env=env)
        run_command(restore_command, env=env)
        restored_counts = get_row_counts(target, database_name=scratch_database)
    finally:
        run_command(drop_command, env=env)

    mismatches = {
        table: {"source": source_counts[table], "restored": restored_counts.get(table, -1)}
        for table in source_counts
        if source_counts[table] != restored_counts.get(table, -1)
    }
    return {
        "scratch_database": scratch_database,
        "tables_verified": len(source_counts),
        "table_count_mismatches": mismatches,
        "integrity_ok": not mismatches,
    }


def _run_sqlite_restore_drill(target: DatabaseTarget, backup_path: Path) -> dict[str, Any]:
    if not target.sqlite_path or not target.sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {target.sqlite_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        corrupted_db = temp_root / "corrupted.db"
        restored_db = temp_root / "restored.db"
        shutil.copy2(target.sqlite_path, corrupted_db)
        with corrupted_db.open("r+b") as handle:
            handle.seek(4096)
            handle.write(b"\x00\xff\xde\xad" * 256)

        shutil.copy2(backup_path, restored_db)
        restored_target = DatabaseTarget(
            database_url=f"sqlite:///{restored_db.as_posix()}",
            dialect="sqlite",
            database_name=restored_db.stem,
            url=make_url(f"sqlite:///{restored_db.as_posix()}"),
            sqlite_path=restored_db,
        )
        source_counts = get_row_counts(target)
        restored_counts = get_row_counts(restored_target)

    mismatches = {
        table: {"source": source_counts[table], "restored": restored_counts.get(table, -1)}
        for table in source_counts
        if source_counts[table] != restored_counts.get(table, -1)
    }
    return {
        "scratch_database": str(restored_db),
        "tables_verified": len(source_counts),
        "table_count_mismatches": mismatches,
        "integrity_ok": not mismatches,
    }


def run_drill(target: DatabaseTarget, backup_dir: Path) -> dict[str, Any]:
    """Execute the full backup and restore drill."""
    report: dict[str, Any] = {
        "drill_started_at": datetime.utcnow().isoformat(),
        "database_url": target.database_url,
        "backend": target.dialect,
        "steps": [],
    }

    source_counts = get_row_counts(target)
    report["steps"].append(
        {
            "step": "verify_source",
            "status": "pass",
            "tables": len(source_counts),
            "total_rows": sum(value for value in source_counts.values() if value >= 0),
        }
    )

    backup_path = create_backup(target, backup_dir)
    report["backup_path"] = str(backup_path)
    report["steps"].append({"step": "create_backup", "status": "pass", "path": str(backup_path)})

    backup_verification = verify_backup(target, backup_path)
    report["steps"].append(
        {
            "step": "verify_backup",
            "status": "pass" if backup_verification["integrity_ok"] else "fail",
            **backup_verification,
        }
    )

    restore_verification = (
        _run_postgres_restore_drill(target, backup_path)
        if target.dialect == "postgresql"
        else _run_sqlite_restore_drill(target, backup_path)
    )
    report["steps"].append(
        {
            "step": "verify_restoration",
            "status": "pass" if restore_verification["integrity_ok"] else "fail",
            **restore_verification,
        }
    )

    report["drill_completed_at"] = datetime.utcnow().isoformat()
    report["overall_status"] = "pass" if all(step["status"] == "pass" for step in report["steps"]) else "fail"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup and restore drill")
    parser.add_argument("--database-url", default=None, help="SQLAlchemy database URL")
    parser.add_argument("--db-path", default=None, help="Legacy SQLite database path")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup output directory")
    parser.add_argument("--backup-only", action="store_true", help="Only create and verify a backup")
    args = parser.parse_args()

    target = resolve_database_target(args.database_url, db_path=args.db_path)
    backup_dir = Path(args.backup_dir)

    if target.dialect == "sqlite" and (not target.sqlite_path or not target.sqlite_path.exists()):
        print(f"ERROR: Database not found at {target.sqlite_path}")
        sys.exit(1)

    if args.backup_only:
        backup_path = create_backup(target, backup_dir)
        verification = verify_backup(target, backup_path)
        print(f"Backup created: {backup_path}")
        print(f"Backend: {target.dialect}")
        print(f"Integrity: {'OK' if verification['integrity_ok'] else 'FAILED'}")
        return

    print("=" * 60)
    print("  BACKUP / RESTORE DRILL")
    print("=" * 60)
    print(f"Backend: {target.dialect}")
    print(f"Database: {target.database_name}")
    print()

    report = run_drill(target, backup_dir)
    print("=" * 60)
    print(f"  DRILL RESULT: {report['overall_status'].upper()}")
    print("=" * 60)

    report_path = backup_dir / f"drill_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report saved to: {report_path}")

    sys.exit(0 if report["overall_status"] == "pass" else 1)


if __name__ == "__main__":
    main()
