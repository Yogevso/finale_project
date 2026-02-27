"""Tests for backend architecture feature flags."""

from datetime import date

from app.app_factory import create_app
from app.application.queries.analytics_queries import AnalyticsOverviewQuery, AnalyticsQueryHandler
from app.config import settings
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.projections import get_projection_cache


def _middleware_names(app) -> set[str]:
    return {middleware.cls.__name__ for middleware in app.user_middleware}


def test_feature_flags_default_to_enabled():
    assert is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE) is True
    assert is_backend_feature_enabled(BackendFeatureFlag.IDEMPOTENCY_MIDDLEWARE) is True


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
