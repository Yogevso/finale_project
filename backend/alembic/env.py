"""Alembic environment configuration."""

from __future__ import annotations

import logging
import shutil
import sys
import time
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure backend/ is importable when Alembic runs from different cwd values.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: E402,F401
from app.config import settings  # noqa: E402
from app.db import Base  # noqa: E402

_env_logger = logging.getLogger("alembic.env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Default to application DATABASE_URL, but allow overrides from alembic command/config.
config.set_main_option("sqlalchemy.url", config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL)

target_metadata = Base.metadata


def _backup_sqlite_before_migration() -> None:
    """Create a timestamped backup of the SQLite DB before running migrations."""
    db_url = config.get_main_option("sqlalchemy.url") or ""
    if not db_url.startswith("sqlite"):
        return
    # Extract path from sqlite:///./data/portal.db or similar
    db_path_str = db_url.split("///", 1)[-1] if "///" in db_url else None
    if not db_path_str:
        return
    db_path = Path(db_path_str)
    if not db_path.exists():
        return
    backup_path = db_path.with_suffix(f".db.bak.{int(time.time())}")
    shutil.copy2(str(db_path), str(backup_path))
    _env_logger.info("Pre-migration backup: %s -> %s", db_path, backup_path)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        _backup_sqlite_before_migration()
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            _backup_sqlite_before_migration()
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
