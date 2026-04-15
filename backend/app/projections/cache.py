"""Projection cache primitives for heavy read-model endpoints."""

from __future__ import annotations

import dataclasses
import enum
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from threading import RLock
from typing import Any, Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


class ProjectionCacheError(RuntimeError):
    """Raised when projection cache operations fail before query execution."""


@dataclass(slots=True)
class _ProjectionCacheEntry(Generic[T]):
    value: T
    expires_at: float
    scopes: frozenset[str]
    created_at: float


class ProjectionCache:
    """In-memory read-through cache with scoped invalidation."""

    def __init__(
        self,
        *,
        default_ttl_seconds: int = 45,
        max_entries: int = 2048,
    ) -> None:
        self.default_ttl_seconds = max(1, int(default_ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._entries: dict[tuple[str, str], _ProjectionCacheEntry[Any]] = {}
        self._lock = RLock()

    @staticmethod
    def _normalize_key_fragment(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, enum.Enum):
            return value.value
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return ProjectionCache._normalize_key_fragment(value.model_dump())
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return ProjectionCache._normalize_key_fragment(dataclasses.asdict(value))
        if isinstance(value, dict):
            return {
                str(k): ProjectionCache._normalize_key_fragment(v)
                for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            }
        if isinstance(value, (list, tuple)):
            return [ProjectionCache._normalize_key_fragment(item) for item in value]
        if isinstance(value, (set, frozenset)):
            normalized = [ProjectionCache._normalize_key_fragment(item) for item in value]
            return sorted(normalized, key=lambda item: repr(item))
        return str(value)

    def _serialize_key_parts(self, key_parts: tuple[Any, ...]) -> str:
        try:
            normalized = [ProjectionCache._normalize_key_fragment(part) for part in key_parts]
            return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        except (
            Exception
        ) as exc:  # policy: DEGRADED — projection cache failure falls back to uncached path
            raise ProjectionCacheError(f"Unable to serialize projection cache key: {exc}") from exc

    def _evict_if_needed(self, *, now: float) -> None:
        if len(self._entries) <= self.max_entries:
            return

        expired_keys = [k for k, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired_keys:
            self._entries.pop(key, None)
        if len(self._entries) <= self.max_entries:
            return

        overflow = len(self._entries) - self.max_entries
        oldest_entries = sorted(
            self._entries.items(),
            key=lambda item: item[1].created_at,
        )[:overflow]
        for key, _entry in oldest_entries:
            self._entries.pop(key, None)

    def get_or_load(
        self,
        *,
        namespace: str,
        key_parts: tuple[Any, ...],
        scopes: Iterable[str],
        loader: Callable[[], T],
        ttl_seconds: int | None = None,
        validator: Callable[[T], bool] | None = None,
    ) -> T:
        if not namespace or not namespace.strip():
            raise ProjectionCacheError("Projection cache namespace is required")

        scope_set = frozenset(scope for scope in scopes if scope)
        if not scope_set:
            raise ProjectionCacheError("At least one invalidation scope is required")

        ttl = self.default_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        if ttl <= 0:
            return loader()

        cache_key = (namespace, self._serialize_key_parts(key_parts))
        now = time.monotonic()

        with self._lock:
            entry = self._entries.get(cache_key)
            if entry:
                if entry.expires_at <= now:
                    self._entries.pop(cache_key, None)
                elif validator is None or validator(entry.value):
                    return entry.value
                else:
                    self._entries.pop(cache_key, None)

        value = loader()
        if validator is not None and not validator(value):
            return value

        created_at = time.monotonic()
        with self._lock:
            self._entries[cache_key] = _ProjectionCacheEntry(
                value=value,
                expires_at=created_at + ttl,
                scopes=scope_set,
                created_at=created_at,
            )
            self._evict_if_needed(now=created_at)
        return value

    def invalidate_scopes(self, scopes: Iterable[str]) -> int:
        scope_set = {scope for scope in scopes if scope}
        if not scope_set:
            return 0

        with self._lock:
            stale_keys = [
                key for key, entry in self._entries.items() if entry.scopes.intersection(scope_set)
            ]
            for key in stale_keys:
                self._entries.pop(key, None)
            return len(stale_keys)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)
