"""Database session management and migration entrypoints."""

import logging
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import Pool

from app.config import settings
from app.infrastructure.db import run_lightweight_migrations, run_managed_migrations

logger = logging.getLogger(__name__)


# Connection pool health check event handlers (Y15-030)
@event.listens_for(Pool, "checkout")
def _ping_connection_on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Validate connection is alive before handing to application.
    
    This prevents stale connections from causing errors. If the connection
    is broken, SQLAlchemy will invalidate it and get a fresh one.
    """
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    except Exception:
        # Connection is stale - raise so SQLAlchemy invalidates it
        logger.warning("Database connection health check failed, recycling connection")
        raise
    finally:
        cursor.close()


@event.listens_for(Pool, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable SQLite foreign key enforcement on new connections."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.SQL_ECHO,
    "pool_pre_ping": True,  # Additional pool-level health check (Y15-030)
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production-grade pool for PostgreSQL / other RDBMS
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
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
