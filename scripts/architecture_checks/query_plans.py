#!/usr/bin/env python3
"""Query-plan regression checks for audience-critical SQL paths."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "backend" / "data" / "query-plan-check.db"
LARGE_TABLE_THRESHOLD = 1_000


@dataclass(frozen=True, slots=True)
class QueryPlanCheck:
    name: str
    sql: str
    params: tuple[object, ...]
    guarded_tables: tuple[str, ...]


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _bootstrap_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            tenant_id INTEGER,
            title TEXT NOT NULL,
            document_number TEXT NOT NULL,
            status TEXT NOT NULL,
            visibility TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document_company_assignments (
            document_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            PRIMARY KEY (document_id, tenant_id)
        );

        CREATE TABLE IF NOT EXISTS domain_event_outbox (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            next_attempt_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_document_company_assignments_document_id_tenant_id
          ON document_company_assignments (document_id, tenant_id);
        CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status);
        CREATE INDEX IF NOT EXISTS ix_documents_visibility ON documents (visibility);
        CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_status ON domain_event_outbox (status);
        CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_next_attempt_at
          ON domain_event_outbox (next_attempt_at);
        """
    )
    conn.commit()


def _ensure_seed_data(conn: sqlite3.Connection) -> None:
    document_count = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
    if document_count < LARGE_TABLE_THRESHOLD:
        rows = [
            (
                idx,
                1 if idx % 3 else 2,
                f"Plan Doc {idx}",
                f"DOC-PLAN-{idx:05d}",
                "active" if idx % 5 else "draft",
                "company" if idx % 4 == 0 else "internal",
                "2026-03-05T00:00:00",
            )
            for idx in range(1, LARGE_TABLE_THRESHOLD + 1)
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO documents
                (id, tenant_id, title, document_number, status, visibility, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        assignment_rows = [
            (idx, 1 if idx % 2 else 2)
            for idx in range(1, LARGE_TABLE_THRESHOLD + 1, 2)
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO document_company_assignments (document_id, tenant_id) VALUES (?, ?)",
            assignment_rows,
        )
        outbox_rows = [
            (
                idx,
                "company_assignments_updated",
                "pending" if idx % 3 else "processed",
                "2026-03-05T00:00:00",
                "2026-03-05T00:00:00",
            )
            for idx in range(1, LARGE_TABLE_THRESHOLD + 1)
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO domain_event_outbox
                (id, event_type, status, next_attempt_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            outbox_rows,
        )
        conn.commit()


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _explain_plan_lines(conn: sqlite3.Connection, sql: str, params: tuple[object, ...]) -> list[str]:
    rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    return [str(row[3]) for row in rows]


def _is_sequential_scan(plan_line: str, table: str) -> bool:
    normalized = plan_line.upper()
    table_token = table.upper()
    return f"SCAN {table_token}" in normalized and "USING INDEX" not in normalized


def run_checks(conn: sqlite3.Connection) -> list[str]:
    checks = [
        QueryPlanCheck(
            name="assignment_lookup_by_document_and_tenant",
            sql=(
                "SELECT document_id FROM document_company_assignments "
                "WHERE document_id = ? AND tenant_id = ?"
            ),
            params=(200, 1),
            guarded_tables=("document_company_assignments",),
        ),
        QueryPlanCheck(
            name="active_document_visibility_filter",
            sql=(
                "SELECT id FROM documents "
                "WHERE status = ? AND visibility = ? "
                "ORDER BY updated_at DESC LIMIT 20"
            ),
            params=("active", "company"),
            guarded_tables=("documents",),
        ),
        QueryPlanCheck(
            name="pending_outbox_poll",
            sql=(
                "SELECT id FROM domain_event_outbox "
                "WHERE status = ? ORDER BY next_attempt_at ASC LIMIT 50"
            ),
            params=("pending",),
            guarded_tables=("domain_event_outbox",),
        ),
    ]

    failures: list[str] = []
    for check in checks:
        plan_lines = _explain_plan_lines(conn, check.sql, check.params)
        for table in check.guarded_tables:
            if _table_count(conn, table) < LARGE_TABLE_THRESHOLD:
                continue
            if any(_is_sequential_scan(line, table) for line in plan_lines):
                failures.append(
                    f"{check.name}: sequential scan detected on large table '{table}' -> {plan_lines}"
                )
    return failures


def main() -> int:
    conn = _connect(DEFAULT_DB_PATH)
    try:
        _bootstrap_schema(conn)
        _ensure_seed_data(conn)
        failures = run_checks(conn)
    finally:
        conn.close()

    if failures:
        print("Query plan regression check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Query plan regression check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
