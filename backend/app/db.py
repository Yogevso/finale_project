"""Database session management and migration entrypoints."""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.infrastructure.db import run_lightweight_migrations, run_managed_migrations

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.SQL_ECHO,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database schema and apply startup migrations."""
    managed_migrations_applied = _run_managed_migrations()
    if not managed_migrations_applied:
        _bootstrap_schema_from_metadata()
    _run_lightweight_migrations(skip_versions_semantic_migration=managed_migrations_applied)


def _run_managed_migrations() -> bool:
    """Compatibility wrapper for managed migration execution."""
    return run_managed_migrations(
        database_url=settings.DATABASE_URL,
        db_module_path=Path(__file__),
        logger=logger,
    )


def _bootstrap_schema_from_metadata() -> None:
    """Compatibility wrapper for metadata bootstrap fallback."""
    logger.warning("Managed migrations unavailable; bootstrapping schema via SQLAlchemy metadata.")
    Base.metadata.create_all(bind=engine)


def _run_lightweight_migrations(*, skip_versions_semantic_migration: bool = False) -> None:
    """Compatibility wrapper for lightweight migration execution."""
    run_lightweight_migrations(
        engine=engine,
        skip_versions_semantic_migration=skip_versions_semantic_migration,
    )
