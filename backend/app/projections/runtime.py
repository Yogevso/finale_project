"""Projection runtime helpers and global cache instance."""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from app.projections.cache import ProjectionCache, ProjectionCacheError

logger = logging.getLogger(__name__)

T = TypeVar("T")

_projection_cache = ProjectionCache(default_ttl_seconds=45, max_entries=4096)


def get_projection_cache() -> ProjectionCache:
    """Return the shared projection cache instance."""
    return _projection_cache


def invalidate_projection_scopes(scopes: set[str]) -> int:
    """Invalidate all cache entries touching the provided scopes."""
    return _projection_cache.invalidate_scopes(scopes)


def invalidate_portal_audience_cache() -> int:
    """Explicitly invalidate portal projections after audience/visibility changes.

    Call this as a safety net after any operation that modifies a document's
    visibility or company assignments, especially when the change may not
    trigger SQLAlchemy session flush hooks (e.g. raw SQL, bulk updates).
    """
    count = _projection_cache.invalidate_scopes({"portal"})
    if count:
        logger.info("Invalidated %d portal projection entries due to audience change", count)
    return count


def invalidate_search_audience_cache() -> int:
    """Invalidate search + public projection caches after audience changes.

    Call alongside ``invalidate_portal_audience_cache`` whenever visibility
    or company assignments change so that search results and public listings
    reflect the updated audience rules.
    """
    count = _projection_cache.invalidate_scopes({"search", "public"})
    if count:
        logger.info("Invalidated %d search/public projection entries due to audience change", count)
    return count


def reset_projection_cache() -> None:
    """Clear the shared projection cache (used in tests)."""
    _projection_cache.clear()


def execute_cached_projection(
    *,
    cache: ProjectionCache,
    namespace: str,
    key_parts: tuple[object, ...],
    scopes: set[str],
    loader: Callable[[], T],
    ttl_seconds: int | None = None,
    validator: Callable[[T], bool] | None = None,
) -> T:
    """Execute read-through cached projection with safe bypass fallback."""
    try:
        return cache.get_or_load(
            namespace=namespace,
            key_parts=key_parts,
            scopes=scopes,
            loader=loader,
            ttl_seconds=ttl_seconds,
            validator=validator,
        )
    except ProjectionCacheError as exc:
        logger.warning("Bypassing projection cache for %s: %s", namespace, exc)
        return loader()
