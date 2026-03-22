#!/usr/bin/env python3
"""Split a single portal.db into 3 databases (core, analytics, chat).

Usage:
    python scripts/split_databases.py                   # dry-run by default
    python scripts/split_databases.py --execute         # actually copy rows
    python scripts/split_databases.py --execute --cleanup  # copy + delete from source

The script is idempotent: rows that already exist in the target are skipped.
A backup of portal.db is created before any writes.
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Table assignments (must match alembic env.py filters and model bases)
# ---------------------------------------------------------------------------
ANALYTICS_TABLES = [
    "audit_logs",
    "security_events",
    "search_analytics",
    "nps_surveys",
    "onboarding_events",
    "activation_milestones",
    "domain_event_outbox",
]

CHAT_TABLES = [
    "notifications",
    "chats",
    "chat_participants",
    "chat_messages",
    "collaboration_sessions",
    "collaboration_activities",
    "collaboration_snapshots",
    "assistant_conversations",
    "assistant_messages",
    "assistant_uploaded_files",
]

# Insertion order matters for FK constraints within the same domain.
# Parent tables first, children after.
CHAT_TABLES_ORDERED = [
    "chats",
    "chat_participants",
    "chat_messages",
    "notifications",
    "assistant_conversations",
    "assistant_messages",
    "assistant_uploaded_files",
    "collaboration_sessions",
    "collaboration_activities",
    "collaboration_snapshots",
]


def _backup(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = path.with_suffix(f".db.bak.{ts}")
    shutil.copy2(path, dest)
    print(f"  Backed up {path.name} -> {dest.name}")
    return dest


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info([{table}])")
    return [row[1] for row in cur.fetchall()]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]


def _copy_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    dry_run: bool,
) -> int:
    """Copy rows from src to dst for a single table. Returns rows copied."""
    if not _table_exists(src, table):
        print(f"    {table}: not found in source — skipping")
        return 0

    src_count = _row_count(src, table)
    if src_count == 0:
        print(f"    {table}: 0 rows — nothing to copy")
        return 0

    # Ensure target table exists (schema must be created by alembic/init_db first)
    if not _table_exists(dst, table):
        # Bootstrap: copy schema from source, stripping cross-DB FK constraints
        schema_sql = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()[0]
        if not dry_run:
            dst.execute("PRAGMA foreign_keys=OFF")
            dst.execute(schema_sql)
            dst.commit()
            dst.execute("PRAGMA foreign_keys=ON")
        print(f"    {table}: created target table from source schema")

    dst_count = _row_count(dst, table)
    if dst_count >= src_count:
        print(f"    {table}: {dst_count} rows already in target (>= {src_count} source) — skipping")
        return 0

    cols = _get_columns(src, table)
    col_list = ", ".join(f"[{c}]" for c in cols)
    placeholders = ", ".join("?" for _ in cols)

    rows = src.execute(f"SELECT {col_list} FROM [{table}]").fetchall()

    if dry_run:
        print(f"    {table}: would copy {len(rows)} rows ({len(cols)} columns)")
        return len(rows)

    # Use INSERT OR IGNORE to be idempotent (relies on PK/UNIQUE constraints)
    dst.execute("PRAGMA foreign_keys=OFF")
    dst.executemany(
        f"INSERT OR IGNORE INTO [{table}] ({col_list}) VALUES ({placeholders})",
        rows,
    )
    dst.commit()
    dst.execute("PRAGMA foreign_keys=ON")
    new_count = _row_count(dst, table)
    copied = new_count - dst_count
    print(f"    {table}: copied {copied} rows (total now: {new_count})")
    return copied


def _delete_migrated(
    conn: sqlite3.Connection, tables: list[str], dry_run: bool
) -> None:
    """Delete rows from source for migrated tables (reverse order for FK safety)."""
    for table in reversed(tables):
        if not _table_exists(conn, table):
            continue
        count = _row_count(conn, table)
        if count == 0:
            continue
        if dry_run:
            print(f"    {table}: would delete {count} rows from source")
        else:
            conn.execute(f"DELETE FROM [{table}]")
            conn.commit()
            print(f"    {table}: deleted {count} rows from source")


def main() -> int:
    parser = argparse.ArgumentParser(description="Split portal.db into 3 databases")
    parser.add_argument(
        "--source",
        default="data/portal.db",
        help="Path to the source database (default: data/portal.db)",
    )
    parser.add_argument(
        "--analytics-db",
        default="data/analytics.db",
        help="Path for analytics database (default: data/analytics.db)",
    )
    parser.add_argument(
        "--chat-db",
        default="data/chat.db",
        help="Path for chat database (default: data/chat.db)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the migration (default is dry-run)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete migrated rows from source after copy (requires --execute)",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    if args.cleanup and dry_run:
        print("ERROR: --cleanup requires --execute")
        return 1

    source_path = Path(args.source)
    analytics_path = Path(args.analytics_db)
    chat_path = Path(args.chat_db)

    if not source_path.exists():
        print(f"ERROR: Source database not found: {source_path}")
        return 1

    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n{'='*60}")
    print(f"  Database Split — {mode}")
    print(f"{'='*60}")
    print(f"  Source:    {source_path}")
    print(f"  Analytics: {analytics_path}")
    print(f"  Chat:      {chat_path}")
    print(f"  Cleanup:   {'yes' if args.cleanup else 'no'}")
    print(f"{'='*60}\n")

    # Backup source
    if not dry_run:
        print("Step 0: Backing up databases...")
        _backup(source_path)
        if analytics_path.exists():
            _backup(analytics_path)
        if chat_path.exists():
            _backup(chat_path)
        print()

    # Connect
    src = sqlite3.connect(str(source_path))
    src.execute("PRAGMA journal_mode=WAL")

    analytics_path.parent.mkdir(parents=True, exist_ok=True)
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    dst_analytics = sqlite3.connect(str(analytics_path))
    dst_analytics.execute("PRAGMA journal_mode=WAL")
    dst_chat = sqlite3.connect(str(chat_path))
    dst_chat.execute("PRAGMA journal_mode=WAL")

    # Copy analytics tables
    print("Step 1: Copying analytics tables...")
    total_analytics = 0
    for table in ANALYTICS_TABLES:
        total_analytics += _copy_table(src, dst_analytics, table, dry_run)
    print(f"  => Analytics: {total_analytics} total rows\n")

    # Copy chat tables (ordered for FK constraints)
    print("Step 2: Copying chat tables...")
    total_chat = 0
    for table in CHAT_TABLES_ORDERED:
        total_chat += _copy_table(src, dst_chat, table, dry_run)
    print(f"  => Chat: {total_chat} total rows\n")

    # Optional cleanup
    if args.cleanup:
        print("Step 3: Cleaning up migrated rows from source...")
        _delete_migrated(src, ANALYTICS_TABLES, dry_run)
        _delete_migrated(src, CHAT_TABLES_ORDERED, dry_run)
        print()

    # Verification
    print("Step 3: Verification...")
    all_ok = True
    for table in ANALYTICS_TABLES:
        src_c = _row_count(src, table)
        dst_c = _row_count(dst_analytics, table)
        status = "OK" if dst_c >= src_c or dry_run else "MISMATCH"
        if status == "MISMATCH":
            all_ok = False
        print(f"    {table}: source={src_c}, analytics={dst_c} [{status}]")
    for table in CHAT_TABLES_ORDERED:
        src_c = _row_count(src, table)
        dst_c = _row_count(dst_chat, table)
        status = "OK" if dst_c >= src_c or dry_run else "MISMATCH"
        if status == "MISMATCH":
            all_ok = False
        print(f"    {table}: source={src_c}, chat={dst_c} [{status}]")

    src.close()
    dst_analytics.close()
    dst_chat.close()

    print(f"\n{'='*60}")
    if dry_run:
        print("  DRY RUN complete. Use --execute to perform the migration.")
    elif all_ok:
        print("  Migration complete. All row counts verified.")
    else:
        print("  WARNING: Some row counts don't match. Check above.")
    print(f"{'='*60}\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
