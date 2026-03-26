"""Tests for backend architecture feature flags."""

from datetime import date

import pytest

from app.app_factory import create_app
from app.application.queries.analytics_queries import AnalyticsOverviewQuery, AnalyticsQueryHandler
from app.config import Settings, settings
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.projections import get_projection_cache


def _middleware_names(app) -> set[str]:
    return {middleware.cls.__name__ for middleware in app.user_middleware}


def test_feature_flags_default_to_enabled():
    assert is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE) is True
    assert is_backend_feature_enabled(BackendFeatureFlag.IDEMPOTENCY_MIDDLEWARE) is True
    assert is_backend_feature_enabled(BackendFeatureFlag.COMPANY_AUDIENCE_ENFORCEMENT) is True
    assert is_backend_feature_enabled(BackendFeatureFlag.EVENT_SOURCING_REVIEW_PILOT) is False
    assert is_backend_feature_enabled(BackendFeatureFlag.NEW_AUDIENCE_RULES) is False


def test_create_app_skips_idempotency_middleware_when_flag_disabled(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE", False)
    app = create_app()

    assert "IdempotencyMiddleware" not in _middleware_names(app)


def test_create_app_mounts_idempotency_middleware_when_flag_enabled(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE", True)
    app = create_app()

    assert "IdempotencyMiddleware" in _middleware_names(app)


def test_analytics_query_handler_bypasses_cache_when_projection_flag_disabled(monkeypatch):
    class StubAnalyticsService:
        def __init__(self):
            self.tenant_ctx = None
            self.calls = 0

        def get_overview(self, date_from, date_to):
            self.calls += 1
            return {"kind": "overview", "from": date_from, "to": date_to}

    monkeypatch.setattr(settings, "FEATURE_FLAG_PROJECTION_CACHE", False)

    cache = get_projection_cache()

    def fail_if_cache_used(**_kwargs):
        raise AssertionError("Projection cache should be bypassed when feature flag is disabled")

    monkeypatch.setattr(cache, "get_or_load", fail_if_cache_used)

    service = StubAnalyticsService()
    handler = AnalyticsQueryHandler(service, projection_cache=cache)
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    result = handler.execute_overview(AnalyticsOverviewQuery(start, end))

    assert result["kind"] == "overview"
    assert service.calls == 1


def test_new_audience_rules_rollout_requires_rollout_key_when_percentage_is_partial(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES", True)
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES_ROLLOUT_PERCENTAGE", 50)

    assert is_backend_feature_enabled(BackendFeatureFlag.NEW_AUDIENCE_RULES) is False


def test_new_audience_rules_rollout_honors_percentage_bucket(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES", True)
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES_ROLLOUT_PERCENTAGE", 25)

    monkeypatch.setattr("app.feature_flags._rollout_bucket", lambda _key: 24)
    assert (
        is_backend_feature_enabled(
            BackendFeatureFlag.NEW_AUDIENCE_RULES,
            rollout_key="tenant-24",
        )
        is True
    )

    monkeypatch.setattr("app.feature_flags._rollout_bucket", lambda _key: 25)
    assert (
        is_backend_feature_enabled(
            BackendFeatureFlag.NEW_AUDIENCE_RULES,
            rollout_key="tenant-25",
        )
        is False
    )


def test_new_audience_rules_rollout_can_be_forced_fully_on(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES", True)
    monkeypatch.setattr(settings, "FEATURE_FLAG_NEW_AUDIENCE_RULES_ROLLOUT_PERCENTAGE", 100)

    assert (
        is_backend_feature_enabled(
            BackendFeatureFlag.NEW_AUDIENCE_RULES,
            rollout_key=None,
        )
        is True
    )


def test_production_rejects_implicit_enabled_default_feature_flags():
    with pytest.raises(RuntimeError, match="Production requires explicit values for feature flags"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="s" * 32,
            AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
        )


def test_production_accepts_explicit_enabled_default_feature_flags():
    resolved = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="s" * 32,
        AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
        REDIS_URL="redis://localhost:6379/0",
        FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
        FEATURE_FLAG_PROJECTION_CACHE=True,
        FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
        ASSISTANT_ENABLED=True,
        SEARCH_BACKEND_MODE="portable_like",
    )

    assert resolved.FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE is True
    assert resolved.FEATURE_FLAG_PROJECTION_CACHE is True
    assert resolved.FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT is True
    assert resolved.ASSISTANT_ENABLED is True


def test_production_rejects_rate_limiting_without_redis():
    with pytest.raises(RuntimeError, match="Production requires REDIS_URL when RATE_LIMIT_ENABLED is True"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="s" * 32,
            AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
            FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
            FEATURE_FLAG_PROJECTION_CACHE=True,
            FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
            ASSISTANT_ENABLED=True,
            SEARCH_BACKEND_MODE="portable_like",
        )


def test_production_allows_rate_limiting_with_redis():
    resolved = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="s" * 32,
        AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
        REDIS_URL="redis://localhost:6379/0",
        FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
        FEATURE_FLAG_PROJECTION_CACHE=True,
        FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
        ASSISTANT_ENABLED=True,
        SEARCH_BACKEND_MODE="portable_like",
    )

    assert resolved.REDIS_URL == "redis://localhost:6379/0"


def test_production_rejects_auto_search_backend_mode():
    with pytest.raises(RuntimeError, match="Production requires explicit SEARCH_BACKEND_MODE"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="s" * 32,
            AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
            REDIS_URL="redis://localhost:6379/0",
            FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
            FEATURE_FLAG_PROJECTION_CACHE=True,
            FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
            ASSISTANT_ENABLED=True,
            SEARCH_BACKEND_MODE="auto",
        )


def test_production_rejects_sqlite_search_mode_for_postgres_database():
    with pytest.raises(RuntimeError, match="SEARCH_BACKEND_MODE=sqlite_fts5 requires a SQLite DATABASE_URL"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DATABASE_URL="postgresql://portal:secret@db:5432/portal",
            SECRET_KEY="s" * 32,
            AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
            REDIS_URL="redis://localhost:6379/0",
            FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
            FEATURE_FLAG_PROJECTION_CACHE=True,
            FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
            ASSISTANT_ENABLED=True,
            SEARCH_BACKEND_MODE="sqlite_fts5",
        )


def test_production_accepts_postgres_search_mode_for_postgres_database():
    resolved = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL="postgresql://portal:secret@db:5432/portal",
        SECRET_KEY="s" * 32,
        AUDIENCE_AUDIT_HMAC_KEYS="v1:secure-audit-key-material-1234567890",
        REDIS_URL="redis://localhost:6379/0",
        FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE=True,
        FEATURE_FLAG_PROJECTION_CACHE=True,
        FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=True,
        ASSISTANT_ENABLED=True,
        SEARCH_BACKEND_MODE="postgres_tsv",
    )

    assert resolved.SEARCH_BACKEND_MODE == "postgres_tsv"


def test_assistant_capacity_settings_reject_negative_values():
    with pytest.raises(RuntimeError, match="Assistant capacity settings must be zero or positive"):
        Settings(
            _env_file=None,
            APP_ENV="development",
            ASSISTANT_CHAT_MAX_QUEUE=-1,
        )
