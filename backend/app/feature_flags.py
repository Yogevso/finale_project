"""Backend feature-flag framework for architecture rollout safety."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config import settings


class BackendFeatureFlag(str, Enum):
    """Known backend feature flags."""

    IDEMPOTENCY_MIDDLEWARE = "idempotency_middleware"
    PROJECTION_CACHE = "projection_cache"


@dataclass(frozen=True, slots=True)
class BackendFeatureFlags:
    """Resolved backend feature flags from runtime configuration."""

    idempotency_middleware: bool
    projection_cache: bool

    def is_enabled(self, flag: BackendFeatureFlag) -> bool:
        if flag == BackendFeatureFlag.IDEMPOTENCY_MIDDLEWARE:
            return bool(self.idempotency_middleware)
        if flag == BackendFeatureFlag.PROJECTION_CACHE:
            return bool(self.projection_cache)
        return False


def get_backend_feature_flags() -> BackendFeatureFlags:
    """Resolve backend feature flags from settings."""
    return BackendFeatureFlags(
        idempotency_middleware=bool(settings.FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE),
        projection_cache=bool(settings.FEATURE_FLAG_PROJECTION_CACHE),
    )


def is_backend_feature_enabled(flag: BackendFeatureFlag) -> bool:
    """Check whether one backend feature flag is enabled."""
    return get_backend_feature_flags().is_enabled(flag)
