"""Database engine factories for Core, Analytics, and Chat databases.

Each engine is configured independently with appropriate pool sizing.
When ANALYTICS_DATABASE_URL or CHAT_DATABASE_URL are not set (empty string),
they fall back to the main DATABASE_URL for backward compatibility.
"""

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import Pool

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_url(url: str, fallback: str) -> str:
    """Return *url* if non-empty, otherwise *fallback*."""
    return url if url else fallback


def _base_engine_kwargs(echo: bool) -> dict:
    """Common engine keyword arguments."""
    return {
        "echo": echo,
        "pool_pre_ping": True,
    }


def _sqlite_kwargs() -> dict:
    return {"connect_args": {"check_same_thread": False}}


def _pg_kwargs(pool_size: int, max_overflow: int) -> dict:
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": 1800,
    }


def _build_engine(url: str, *, echo: bool, pool_size: int = 10, max_overflow: int = 20):
    """Create a SQLAlchemy engine for *url* with the right dialect options."""
    kwargs = _base_engine_kwargs(echo)
    if url.startswith("sqlite"):
        kwargs.update(_sqlite_kwargs())
    else:
        kwargs.update(_pg_kwargs(pool_size, max_overflow))
    return create_engine(url, **kwargs)


# ---------------------------------------------------------------------------
# Pool-level event listeners (applied globally to all pools)
# ---------------------------------------------------------------------------

@event.listens_for(Pool, "checkout")
def _ping_connection_on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Validate connection is alive before handing to application."""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    except Exception:  # policy: FAIL_FAST — unhealthy DB connections must be recycled immediately
        logger.warning("Database connection health check failed, recycling connection")
        raise
    finally:
        cursor.close()


@event.listens_for(Pool, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable SQLite foreign key enforcement on new connections."""
    # Detect SQLite via the module name of the DBAPI connection
    module_name = type(dbapi_conn).__module__
    if "sqlite" in module_name:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# Engine instances (created at import time, same as the old db.py)
# ---------------------------------------------------------------------------

_core_url = settings.DATABASE_URL
_analytics_url = _resolve_url(settings.ANALYTICS_DATABASE_URL, _core_url)
_chat_url = _resolve_url(settings.CHAT_DATABASE_URL, _core_url)

core_engine = _build_engine(_core_url, echo=settings.SQL_ECHO, pool_size=10, max_overflow=20)
analytics_engine = _build_engine(
    _analytics_url,
    echo=settings.ANALYTICS_SQL_ECHO if settings.ANALYTICS_SQL_ECHO is not None else settings.SQL_ECHO,
    pool_size=5, max_overflow=10,
)
chat_engine = _build_engine(
    _chat_url,
    echo=settings.CHAT_SQL_ECHO if settings.CHAT_SQL_ECHO is not None else settings.SQL_ECHO,
    pool_size=8, max_overflow=15,
)
