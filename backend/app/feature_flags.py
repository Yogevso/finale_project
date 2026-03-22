"""Backend feature-flag framework for architecture rollout safety."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from app.config import settings


class BackendFeatureFlag(str, Enum):
    """Known backend feature flags."""

    IDEMPOTENCY_MIDDLEWARE = "idempotency_middleware"
    PROJECTION_CACHE = "projection_cache"
    EVENT_SOURCING_REVIEW_PILOT = "event_sourcing_review_pilot"
    NEW_AUDIENCE_RULES = "new_audience_rules"
    COMPANY_AUDIENCE_ENFORCEMENT = "company_audience_enforcement"
    PDF_OCR = "pdf_ocr"
    AUDIENCE_VALIDATION_SAFE_MODE = "audience_validation_safe_mode"
    ASSISTANT = "assistant"
    CSRF_PROTECTION = "csrf_protection"


@dataclass(frozen=True, slots=True)
class BackendFeatureFlags:
    """Resolved backend feature flags from runtime configuration."""

    idempotency_middleware: bool
    projection_cache: bool
    event_sourcing_review_pilot: bool
    new_audience_rules: bool
    new_audience_rules_rollout_percentage: int
    company_audience_enforcement: bool
    pdf_ocr: bool
    audience_validation_safe_mode: bool
    assistant: bool
    csrf_protection: bool

    def is_enabled(
        self,
        flag: BackendFeatureFlag,
        *,
        rollout_key: str | int | None = None,
    ) -> bool:
        if flag == BackendFeatureFlag.IDEMPOTENCY_MIDDLEWARE:
            return bool(self.idempotency_middleware)
        if flag == BackendFeatureFlag.PROJECTION_CACHE:
            return bool(self.projection_cache)
        if flag == BackendFeatureFlag.EVENT_SOURCING_REVIEW_PILOT:
            return bool(self.event_sourcing_review_pilot)
        if flag == BackendFeatureFlag.NEW_AUDIENCE_RULES:
            return self._is_new_audience_rules_enabled(rollout_key=rollout_key)
        if flag == BackendFeatureFlag.COMPANY_AUDIENCE_ENFORCEMENT:
            return bool(self.company_audience_enforcement)
        if flag == BackendFeatureFlag.PDF_OCR:
            return bool(self.pdf_ocr)
        if flag == BackendFeatureFlag.AUDIENCE_VALIDATION_SAFE_MODE:
            return bool(self.audience_validation_safe_mode)
        if flag == BackendFeatureFlag.ASSISTANT:
            return bool(self.assistant)
        if flag == BackendFeatureFlag.CSRF_PROTECTION:
            return bool(self.csrf_protection)
        return False

    def _is_new_audience_rules_enabled(self, *, rollout_key: str | int | None) -> bool:
        if not self.new_audience_rules:
            return False

        rollout_percentage = max(0, min(100, int(self.new_audience_rules_rollout_percentage)))
        if rollout_percentage >= 100:
            return True
        if rollout_percentage <= 0 or rollout_key is None:
            return False

        return _rollout_bucket(rollout_key) < rollout_percentage


def _rollout_bucket(rollout_key: str | int) -> int:
    digest = hashlib.sha256(str(rollout_key).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def get_backend_feature_flags() -> BackendFeatureFlags:
    """Resolve backend feature flags from settings."""
    return BackendFeatureFlags(
        idempotency_middleware=bool(settings.FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE),
        projection_cache=bool(settings.FEATURE_FLAG_PROJECTION_CACHE),
        event_sourcing_review_pilot=bool(settings.FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT),
        new_audience_rules=bool(settings.FEATURE_FLAG_NEW_AUDIENCE_RULES),
        new_audience_rules_rollout_percentage=int(
            settings.FEATURE_FLAG_NEW_AUDIENCE_RULES_ROLLOUT_PERCENTAGE
        ),
        company_audience_enforcement=bool(settings.FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT),
        pdf_ocr=bool(settings.FEATURE_FLAG_PDF_OCR),
        audience_validation_safe_mode=bool(settings.AUDIENCE_VALIDATION_SAFE_MODE_ENABLED),
        assistant=bool(settings.ASSISTANT_ENABLED),
        csrf_protection=bool(settings.CSRF_PROTECTION_ENABLED),
    )


def is_backend_feature_enabled(
    flag: BackendFeatureFlag,
    *,
    rollout_key: str | int | None = None,
) -> bool:
    """Check whether one backend feature flag is enabled."""
    return get_backend_feature_flags().is_enabled(
        flag,
        rollout_key=rollout_key,
    )
