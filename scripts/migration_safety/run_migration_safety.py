#!/usr/bin/env python3
"""Migration safety framework runner.

Stages:
1) Preflight guards (revision graph + filesystem checks)
2) Dry-run validation (ephemeral upgrade + SQL schema dump artifact)
3) Rollback probe (upgrade head -> downgrade -1 -> re-upgrade head)
4) Post-migration schema assertions
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "docs" / "migrations" / "evidence"
DEFAULT_REPORT_PATH = DEFAULT_EVIDENCE_DIR / "latest-migration-safety.json"
DEFAULT_DRY_RUN_SQL_PATH = DEFAULT_EVIDENCE_DIR / "latest-dry-run.sql"


@dataclass(slots=True)
class SafetyCheckResult:
    name: str
    passed: bool
    details: str


@dataclass(slots=True)
class PreflightResult:
    passed: bool
    head_revision: str
    revision_count: int
    high_risk_revisions: list[str]
    checks: list[SafetyCheckResult]


@dataclass(slots=True)
class DryRunResult:
    passed: bool
    sql_path: str
    sql_line_count: int
    details: str


@dataclass(slots=True)
class RollbackProbeResult:
    passed: bool
    revision_after_upgrade: str
    revision_after_downgrade: str | None
    revision_after_reupgrade: str
    details: str


@dataclass(slots=True)
class PostAssertionResult:
    passed: bool
    checks: list[SafetyCheckResult]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_alembic_config(backend_dir: Path, *, database_url: str | None = None) -> Config:
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def _bootstrap_baseline_schema(backend_dir: Path, *, database_url: str) -> None:
    """Bootstrap schema metadata for migration probes in mixed-init environments."""
    backend_path = str(backend_dir)
    inserted = False
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
        inserted = True

    try:
        import app.models  # noqa: F401
        from app.db import Base

        engine = create_engine(database_url, poolclass=NullPool)
        try:
            Base.metadata.create_all(bind=engine)
        finally:
            engine.dispose()
    finally:
        if inserted:
            try:
                sys.path.remove(backend_path)
            except ValueError:
                pass


def _dump_sqlite_schema(db_path: Path) -> str:
    with sqlite3.connect(db_path.as_posix()) as connection:
        dump_lines = list(connection.iterdump())
    if not dump_lines:
        return ""
    return "\n".join(dump_lines) + "\n"


def _is_high_risk_migration(migration_text: str) -> bool:
    high_risk_markers = (
        "op.create_table(",
        "op.drop_table(",
        "op.add_column(",
        "op.drop_column(",
        "op.alter_column(",
        "op.execute(",
    )
    text = migration_text.lower()
    return any(marker in text for marker in high_risk_markers)


def _collect_high_risk_revisions(script_dir: ScriptDirectory) -> list[str]:
    high_risk: list[str] = []
    for revision in script_dir.walk_revisions(base="base", head="heads"):
        if revision.path is None:
            continue
        source = Path(revision.path).read_text(encoding="utf-8")
        if _is_high_risk_migration(source):
            high_risk.append(revision.revision)
    return sorted(set(high_risk))


def run_preflight(backend_dir: Path) -> PreflightResult:
    checks: list[SafetyCheckResult] = []
    required_paths = [
        backend_dir / "alembic.ini",
        backend_dir / "alembic" / "env.py",
        backend_dir / "alembic" / "versions",
    ]

    for path in required_paths:
        exists = path.exists()
        checks.append(
            SafetyCheckResult(
                name=f"exists:{path.relative_to(REPO_ROOT).as_posix()}",
                passed=exists,
                details="present" if exists else "missing",
            )
        )

    if not all(check.passed for check in checks):
        return PreflightResult(
            passed=False,
            head_revision="",
            revision_count=0,
            high_risk_revisions=[],
            checks=checks,
        )

    config = _build_alembic_config(backend_dir)
    script_dir = ScriptDirectory.from_config(config)
    heads = script_dir.get_heads()
    checks.append(
        SafetyCheckResult(
            name="single-head",
            passed=len(heads) == 1,
            details=f"heads={heads}",
        )
    )

    revisions = list(script_dir.walk_revisions(base="base", head="heads"))
    checks.append(
        SafetyCheckResult(
            name="has-managed-revisions",
            passed=len(revisions) > 0,
            details=f"count={len(revisions)}",
        )
    )

    revision_ids = [revision.revision for revision in revisions if revision.revision]
    unique_revision_ids = set(revision_ids)
    checks.append(
        SafetyCheckResult(
            name="unique-revision-ids",
            passed=len(unique_revision_ids) == len(revision_ids),
            details=f"unique={len(unique_revision_ids)} total={len(revision_ids)}",
        )
    )

    high_risk_revisions = _collect_high_risk_revisions(script_dir)
    checks.append(
        SafetyCheckResult(
            name="high-risk-migrations-detected",
            passed=True,
            details=f"{len(high_risk_revisions)} revisions: {high_risk_revisions}",
        )
    )

    head_revision = heads[0] if heads else ""
    return PreflightResult(
        passed=all(check.passed for check in checks),
        head_revision=head_revision,
        revision_count=len(revisions),
        high_risk_revisions=high_risk_revisions,
        checks=checks,
    )


def run_dry_run(
    backend_dir: Path,
    *,
    sql_output_path: Path,
) -> DryRunResult:
    with tempfile.TemporaryDirectory(prefix="migration_safety_dry_run_") as temp_dir:
        db_path = Path(temp_dir) / "dry_run.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        config = _build_alembic_config(backend_dir, database_url=database_url)

        try:
            _bootstrap_baseline_schema(backend_dir, database_url=database_url)
            command.upgrade(config, "head")
            sql_output = _dump_sqlite_schema(db_path)
            details = "Dry-run upgrade and schema SQL dump succeeded."
            passed = True
        except Exception as exc:
            sql_output = ""
            details = f"Dry-run failed: {exc}"
            passed = False

    sql_output_path.parent.mkdir(parents=True, exist_ok=True)
    sql_output_path.write_text(sql_output, encoding="utf-8")
    line_count = len(sql_output.splitlines())

    return DryRunResult(
        passed=passed,
        sql_path=sql_output_path.relative_to(REPO_ROOT).as_posix(),
        sql_line_count=line_count,
        details=details,
    )


def _get_current_revision(engine: Engine) -> str | None:
    try:
        with engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version LIMIT 1"
            ).fetchall()
    except SQLAlchemyError:
        return None

    if not rows:
        return None
    return str(rows[0][0]) if rows[0][0] is not None else None


def run_rollback_probe(backend_dir: Path, *, head_revision: str) -> RollbackProbeResult:
    with tempfile.TemporaryDirectory(prefix="migration_safety_probe_") as temp_dir:
        db_path = Path(temp_dir) / "probe.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        config = _build_alembic_config(backend_dir, database_url=database_url)

        try:
            _bootstrap_baseline_schema(backend_dir, database_url=database_url)
            command.upgrade(config, "head")
            engine = create_engine(database_url, poolclass=NullPool)
            revision_after_upgrade = _get_current_revision(engine) or ""
            command.downgrade(config, "-1")
            revision_after_downgrade = _get_current_revision(engine)
            command.upgrade(config, "head")
            revision_after_reupgrade = _get_current_revision(engine) or ""
            engine.dispose()
        except Exception as exc:
            return RollbackProbeResult(
                passed=False,
                revision_after_upgrade="",
                revision_after_downgrade=None,
                revision_after_reupgrade="",
                details=f"Rollback probe failed: {exc}",
            )

        checks = [
            revision_after_upgrade == head_revision,
            revision_after_reupgrade == head_revision,
            revision_after_downgrade != head_revision,
        ]
        passed = all(checks)
        details = (
            "Rollback probe succeeded."
            if passed
            else "Unexpected revision state during rollback probe."
        )
        return RollbackProbeResult(
            passed=passed,
            revision_after_upgrade=revision_after_upgrade,
            revision_after_downgrade=revision_after_downgrade,
            revision_after_reupgrade=revision_after_reupgrade,
            details=details,
        )


def _assert_table_exists(inspector, table_name: str) -> SafetyCheckResult:
    exists = table_name in set(inspector.get_table_names())
    return SafetyCheckResult(
        name=f"table:{table_name}",
        passed=exists,
        details="present" if exists else "missing",
    )


def _assert_column_exists(inspector, table_name: str, column_name: str) -> SafetyCheckResult:
    try:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
    except SQLAlchemyError:
        columns = set()
    exists = column_name in columns
    return SafetyCheckResult(
        name=f"column:{table_name}.{column_name}",
        passed=exists,
        details="present" if exists else "missing",
    )


def run_post_assertions(backend_dir: Path) -> PostAssertionResult:
    checks: list[SafetyCheckResult] = []
    with tempfile.TemporaryDirectory(prefix="migration_safety_post_") as temp_dir:
        db_path = Path(temp_dir) / "post_assertions.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        config = _build_alembic_config(backend_dir, database_url=database_url)

        try:
            _bootstrap_baseline_schema(backend_dir, database_url=database_url)
            command.upgrade(config, "head")
        except Exception as exc:
            return PostAssertionResult(
                passed=False,
                checks=[
                    SafetyCheckResult(
                        name="upgrade-head-before-assertions",
                        passed=False,
                        details=f"failed: {exc}",
                    )
                ],
            )

        engine = create_engine(database_url, poolclass=NullPool)
        try:
            inspector = inspect(engine)
            checks.extend(
                [
                    _assert_table_exists(inspector, "document_number_sequences"),
                    _assert_table_exists(inspector, "domain_event_outbox"),
                    _assert_table_exists(inspector, "idempotency_keys"),
                    _assert_column_exists(inspector, "documents", "row_version"),
                    _assert_column_exists(inspector, "versions", "row_version"),
                ]
            )
        finally:
            engine.dispose()

    return PostAssertionResult(
        passed=all(check.passed for check in checks),
        checks=checks,
    )


def _serialize_result_payload(
    *,
    backend_dir: Path,
    preflight: PreflightResult,
    dry_run: DryRunResult,
    rollback_probe: RollbackProbeResult,
    post_assertions: PostAssertionResult,
) -> dict[str, Any]:
    return {
        "generated_at": _utc_now_iso(),
        "backend_dir": backend_dir.relative_to(REPO_ROOT).as_posix(),
        "head_revision": preflight.head_revision,
        "high_risk_revisions": preflight.high_risk_revisions,
        "preflight": asdict(preflight),
        "dry_run": asdict(dry_run),
        "rollback_probe": asdict(rollback_probe),
        "post_assertions": asdict(post_assertions),
        "overall_passed": all(
            [
                preflight.passed,
                dry_run.passed,
                rollback_probe.passed,
                post_assertions.passed,
            ]
        ),
    }


def _print_human_summary(payload: dict[str, Any], report_path: Path) -> None:
    print("Migration safety summary:")
    print(f"- head_revision: {payload['head_revision']}")
    print(f"- high_risk_revisions: {payload['high_risk_revisions']}")
    print(f"- preflight: {'pass' if payload['preflight']['passed'] else 'fail'}")
    print(f"- dry_run: {'pass' if payload['dry_run']['passed'] else 'fail'}")
    print(f"- rollback_probe: {'pass' if payload['rollback_probe']['passed'] else 'fail'}")
    print(f"- post_assertions: {'pass' if payload['post_assertions']['passed'] else 'fail'}")
    print(f"- report: {report_path.relative_to(REPO_ROOT).as_posix()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run migration safety framework checks")
    parser.add_argument(
        "--backend-dir",
        default=str(DEFAULT_BACKEND_DIR),
        help="Path to backend directory containing alembic.ini",
    )
    parser.add_argument(
        "--report-file",
        default=str(DEFAULT_REPORT_PATH),
        help="JSON report output path",
    )
    parser.add_argument(
        "--dry-run-sql-file",
        default=str(DEFAULT_DRY_RUN_SQL_PATH),
        help="Dry-run SQL output file path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend_dir = Path(args.backend_dir).resolve()
    report_path = Path(args.report_file).resolve()
    dry_run_sql_path = Path(args.dry_run_sql_file).resolve()

    preflight = run_preflight(backend_dir)
    if not preflight.passed:
        payload = _serialize_result_payload(
            backend_dir=backend_dir,
            preflight=preflight,
            dry_run=DryRunResult(False, "", 0, "Skipped due to preflight failure"),
            rollback_probe=RollbackProbeResult(False, "", None, "", "Skipped due to preflight failure"),
            post_assertions=PostAssertionResult(
                False,
                [
                    SafetyCheckResult(
                        name="post-assertions",
                        passed=False,
                        details="Skipped due to preflight failure",
                    )
                ],
            ),
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _print_human_summary(payload, report_path)
        return 1

    dry_run = run_dry_run(backend_dir, sql_output_path=dry_run_sql_path)
    rollback_probe = run_rollback_probe(backend_dir, head_revision=preflight.head_revision)
    post_assertions = run_post_assertions(backend_dir)

    payload = _serialize_result_payload(
        backend_dir=backend_dir,
        preflight=preflight,
        dry_run=dry_run,
        rollback_probe=rollback_probe,
        post_assertions=post_assertions,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_human_summary(payload, report_path)

    if payload["overall_passed"]:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
