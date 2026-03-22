"""Alembic environment for the Chat database."""

from __future__ import annotations

import logging
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: E402,F401
from app.config import settings  # noqa: E402
from app.db.bases import ChatBase  # noqa: E402

_env_logger = logging.getLogger("alembic.env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve chat URL (fall back to main DATABASE_URL)
_chat_url = settings.CHAT_DATABASE_URL or settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", _chat_url)

target_metadata = ChatBase.metadata

# Only consider chat tables during autogenerate comparison.
_CHAT_TABLES = {
    "notifications", "chats", "chat_participants", "chat_messages",
    "collaboration_sessions", "collaboration_activities",
    "collaboration_snapshots", "assistant_conversations",
    "assistant_messages", "assistant_uploaded_files",
}


def _include_name(name, type_, parent_names):
    if type_ == "table":
        return name in _CHAT_TABLES
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version_chat",
        include_name=_include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
            version_table="alembic_version_chat",
            include_name=_include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
