"""Projection caching and invalidation public API."""

from app.projections.cache import ProjectionCache, ProjectionCacheError
from app.projections.invalidation import register_projection_invalidation_listeners
from app.projections.runtime import (
    execute_cached_projection,
    get_projection_cache,
    invalidate_projection_scopes,
    reset_projection_cache,
)

__all__ = [
    "ProjectionCache",
    "ProjectionCacheError",
    "execute_cached_projection",
    "get_projection_cache",
    "invalidate_projection_scopes",
    "register_projection_invalidation_listeners",
    "reset_projection_cache",
]
