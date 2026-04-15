"""Search backend mode selection helpers."""

from __future__ import annotations

import enum

from sqlalchemy.orm import Session


class SearchBackendMode(str, enum.Enum):
    AUTO = "auto"
    SQLITE_FTS5 = "sqlite_fts5"
    POSTGRES_TSV = "postgres_tsv"
    PORTABLE_LIKE = "portable_like"


def database_dialect_from_url(database_url: str) -> str:
    normalized = (database_url or "").strip().lower()
    if normalized.startswith("postgresql"):
        return "postgresql"
    if normalized.startswith("postgres"):
        return "postgresql"
    if normalized.startswith("sqlite"):
        return "sqlite"
    return normalized.split(":", 1)[0] if normalized else "unknown"


def database_dialect_name(db: Session | None) -> str:
    bind = getattr(db, "bind", None)
    if bind is None and db is not None and hasattr(db, "get_bind"):
        bind = db.get_bind()
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    return str(dialect or "unknown")


def resolve_search_backend_mode(
    configured_mode: str,
    *,
    dialect_name: str,
) -> SearchBackendMode:
    requested_mode = SearchBackendMode(configured_mode)
    if requested_mode == SearchBackendMode.AUTO:
        if dialect_name == "sqlite":
            return SearchBackendMode.SQLITE_FTS5
        if dialect_name == "postgresql":
            return SearchBackendMode.POSTGRES_TSV
        return SearchBackendMode.PORTABLE_LIKE

    if requested_mode == SearchBackendMode.SQLITE_FTS5 and dialect_name != "sqlite":
        return SearchBackendMode.PORTABLE_LIKE
    if requested_mode == SearchBackendMode.POSTGRES_TSV and dialect_name != "postgresql":
        return SearchBackendMode.PORTABLE_LIKE
    return requested_mode
