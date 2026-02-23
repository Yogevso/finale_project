"""Managed migration regression tests for the Alembic bootstrap path."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from alembic import command
from alembic.config import Config
from app.db import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "alembic"
HEAD_REVISION = "20260223_0002"


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

    assert revision == HEAD_REVISION
    assert {"semantic_version", "bump_type", "published_by"}.issubset(version_columns)


def test_managed_migration_existing_versions_table_upgrade_path(tmp_path: Path) -> None:
    """Existing DB with a legacy versions table should be upgraded in place."""
    sqlite_path = tmp_path / "legacy_versions.db"

    with sqlite3.connect(sqlite_path) as connection:
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
        row = connection.execute(
            "SELECT semantic_version, bump_type, published_by FROM versions WHERE id = 1"
        ).fetchone()
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    assert {"semantic_version", "bump_type", "published_by"}.issubset(columns)
    assert row == ("2.0.0", "PATCH", None)
    assert revision == HEAD_REVISION
