"""Database session management and migration entrypoints.

Wave AI: Multi-database architecture — Core, Analytics, Chat.
All legacy imports (``from app.db import Base, get_db, SessionLocal, init_db``)
continue to work and resolve to Core database objects.
"""

import logging
from pathlib import Path

from app.config import settings

# Re-export Base classes
from app.db.bases import AnalyticsBase, Base, ChatBase, CoreBase  # noqa: F401

# Re-export FastAPI dependencies
from app.db.dependencies import get_analytics_db, get_chat_db, get_core_db, get_db  # noqa: F401

# Re-export engines
from app.db.engines import analytics_engine, chat_engine, core_engine  # noqa: F401

# Re-export session factories
from app.db.sessions import (  # noqa: F401
    AnalyticsSessionLocal,
    ChatSessionLocal,
    CoreSessionLocal,
    SessionLocal,
)
from app.infrastructure.db import run_lightweight_migrations, run_managed_migrations

# Backward compatibility — old code uses ``engine`` directly
engine = core_engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Initialize database schemas and apply startup migrations.

    Creates tables on all three engines and runs Alembic managed migrations
    for all three databases (core, analytics, chat).
    """
    managed_migrations_applied = _run_managed_migrations()
    if not managed_migrations_applied:
        _bootstrap_schema_from_metadata()
    else:
        _bootstrap_secondary_schemas()
    _run_secondary_managed_migrations()
    _run_lightweight_migrations(skip_versions_semantic_migration=managed_migrations_applied)


def _run_managed_migrations() -> bool:
    """Run Alembic managed migrations for the core database."""
    return run_managed_migrations(
        database_url=settings.DATABASE_URL,
        db_module_path=Path(__file__).parent / "__init__.py",
        logger=logger,
    )


def _bootstrap_schema_from_metadata() -> None:
    """Create all tables on all three engines from metadata."""
    logger.warning("Managed migrations unavailable; bootstrapping schema via SQLAlchemy metadata.")
    CoreBase.metadata.create_all(bind=core_engine)
    AnalyticsBase.metadata.create_all(bind=analytics_engine)
    ChatBase.metadata.create_all(bind=chat_engine)


def _bootstrap_secondary_schemas() -> None:
    """Ensure analytics and chat schemas exist (their managed migrations come later)."""
    AnalyticsBase.metadata.create_all(bind=analytics_engine)
    ChatBase.metadata.create_all(bind=chat_engine)


def _run_secondary_managed_migrations() -> None:
    """Run Alembic managed migrations for analytics and chat databases."""
    db_module_path = Path(__file__).parent / "__init__.py"
    analytics_url = settings.ANALYTICS_DATABASE_URL or settings.DATABASE_URL
    chat_url = settings.CHAT_DATABASE_URL or settings.DATABASE_URL

    run_managed_migrations(
        database_url=analytics_url,
        db_module_path=db_module_path,
        logger=logger,
        section_name="analytics",
    )
    run_managed_migrations(
        database_url=chat_url,
        db_module_path=db_module_path,
        logger=logger,
        section_name="chat",
    )


def _run_lightweight_migrations(*, skip_versions_semantic_migration: bool = False) -> None:
    """Run lightweight SQLite-only data migrations."""
    run_lightweight_migrations(
        engine=core_engine,
        analytics_engine=analytics_engine,
        skip_versions_semantic_migration=skip_versions_semantic_migration,
    )
