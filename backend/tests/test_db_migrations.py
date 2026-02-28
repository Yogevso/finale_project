"""Managed migration regression tests for the Alembic bootstrap path."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.db import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "alembic"


def _head_revision() -> str:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:  # pragma: no cover - defensive for empty migration trees.
        raise RuntimeError("Expected at least one managed migration revision")
    return head


HEAD_REVISION = _head_revision()


def _upgrade_to_head(sqlite_path: Path) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{sqlite_path.as_posix()}")
    command.upgrade(config, "head")


def test_managed_migration_fresh_db_boot_path(tmp_path: Path) -> None:
    """Fresh schema should upgrade cleanly and stamp Alembic head revision."""
    sqlite_path = tmp_path / "fresh_boot.db"
    engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}")

    Base.metadata.create_all(bind=engine)
    _upgrade_to_head(sqlite_path)

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    inspector = inspect(engine)
    version_columns = {column["name"] for column in inspector.get_columns("versions")}
    sequence_columns = {
        column["name"] for column in inspector.get_columns("document_number_sequences")
    }

    assert revision == HEAD_REVISION
    assert {"semantic_version", "bump_type", "published_by"}.issubset(version_columns)
    assert {"date_key", "next_value", "created_at", "updated_at"}.issubset(sequence_columns)


def test_managed_migration_existing_versions_table_upgrade_path(tmp_path: Path) -> None:
    """Existing DB with a legacy versions table should be upgraded in place."""
    sqlite_path = tmp_path / "legacy_versions.db"

    with sqlite3.connect(sqlite_path) as connection:
        # Newer revisions touch documents metadata too; keep a minimal legacy table present.
        connection.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE versions (
                id INTEGER PRIMARY KEY,
                version_number INTEGER
            )
            """
        )
        connection.execute("INSERT INTO versions (id, version_number) VALUES (1, 2)")
        connection.commit()

    _upgrade_to_head(sqlite_path)

    with sqlite3.connect(sqlite_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(versions)").fetchall()
        }
        sequence_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(document_number_sequences)").fetchall()
        }
        row = connection.execute(
            "SELECT semantic_version, bump_type, published_by FROM versions WHERE id = 1"
        ).fetchone()
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    assert {"semantic_version", "bump_type", "published_by"}.issubset(columns)
    assert {"date_key", "next_value", "created_at", "updated_at"}.issubset(sequence_columns)
    assert row == ("2.0.0", "PATCH", None)
    assert revision == HEAD_REVISION
