"""Application query handlers for analytics read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.projections import ProjectionCache, execute_cached_projection, get_projection_cache
from app.schemas.analytics import TimeGranularity
from app.services.analytics_service import AnalyticsService


@dataclass(frozen=True, slots=True)
class AnalyticsOverviewQuery:
    """Fetch overview analytics for a date range."""

    date_from: date
    date_to: date


@dataclass(frozen=True, slots=True)
class RecentActivityQuery:
    """Fetch recent audit activity feed."""

    limit: int = 10


@dataclass(frozen=True, slots=True)
class EngagementAnalyticsQuery:
    """Fetch engagement analytics for a date range."""

    date_from: date
    date_to: date
    granularity: Optional[TimeGranularity] = None


@dataclass(frozen=True, slots=True)
class TopDocumentsQuery:
    """Fetch top viewed/downloaded documents."""

    date_from: date
    date_to: date
    limit: int = 10


@dataclass(frozen=True, slots=True)
class UserAnalyticsQuery:
    """Fetch user analytics for a date range."""

    date_from: date
    date_to: date
    granularity: Optional[TimeGranularity] = None


@dataclass(frozen=True, slots=True)
class ContentAnalyticsQuery:
    """Fetch content production analytics for a date range."""

    date_from: date
    date_to: date
    granularity: Optional[TimeGranularity] = None


@dataclass(frozen=True, slots=True)
class FeedbackAnalyticsQuery:
    """Fetch feedback analytics for a date range."""

    date_from: date
    date_to: date
    granularity: Optional[TimeGranularity] = None


@dataclass(frozen=True, slots=True)
class TenantAnalyticsQuery:
    """Fetch cross-tenant analytics for a date range."""

    date_from: date
    date_to: date


class AnalyticsQueryHandler:
    """CQRS-lite query handler facade for analytics read-model operations."""

    def __init__(
        self,
        service: AnalyticsService,
        *,
        projection_cache: ProjectionCache | None = None,
    ):
        self.service = service
        self.projection_cache = projection_cache or get_projection_cache()

    def _cache_tenant_scope(self) -> str:
        tenant_ctx = getattr(self.service, "tenant_ctx", None)
        if not tenant_ctx or tenant_ctx.is_system_admin:
            return "system"
        return f"tenant:{tenant_ctx.tenant_id}"

    def _execute_cached(
        self,
        *,
        projection_name: str,
        key_parts: tuple[object, ...],
        loader,
        ttl_seconds: int = 60,
        validator=None,
    ):
        if not is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE):
            return loader()
        return execute_cached_projection(
            cache=self.projection_cache,
            namespace=f"analytics.{projection_name}",
            key_parts=(self._cache_tenant_scope(), *key_parts),
            scopes={"analytics"},
            loader=loader,
            ttl_seconds=ttl_seconds,
            validator=validator,
        )

    def execute_overview(self, query: AnalyticsOverviewQuery) -> dict:
        return self._execute_cached(
            projection_name="overview",
            key_parts=(query.date_from, query.date_to),
            loader=lambda: self.service.get_overview(query.date_from, query.date_to),
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_recent_activity(self, query: RecentActivityQuery) -> list:
        return self._execute_cached(
            projection_name="recent_activity",
            key_parts=(query.limit,),
            loader=lambda: self.service.get_recent_activity(query.limit),
            ttl_seconds=20,
            validator=lambda payload: isinstance(payload, list),
        )

    def execute_engagement(self, query: EngagementAnalyticsQuery) -> dict:
        return self._execute_cached(
            projection_name="engagement",
            key_parts=(query.date_from, query.date_to, query.granularity),
            loader=lambda: self.service.get_engagement(
                query.date_from,
                query.date_to,
                query.granularity,
            ),
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_top_documents(self, query: TopDocumentsQuery) -> dict:
        return self._execute_cached(
            projection_name="top_documents",
            key_parts=(query.date_from, query.date_to, query.limit),
            loader=lambda: self.service.get_top_documents(
                query.date_from,
                query.date_to,
                query.limit,
            ),
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_user_analytics(self, query: UserAnalyticsQuery) -> dict:
        return self._execute_cached(
            projection_name="users",
            key_parts=(query.date_from, query.date_to, query.granularity),
            loader=lambda: self.service.get_user_analytics(
                query.date_from,
                query.date_to,
                query.granularity,
            ),
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_content_analytics(self, query: ContentAnalyticsQuery) -> dict:
        return self._execute_cached(
            projection_name="content",
            key_parts=(query.date_from, query.date_to, query.granularity),
            loader=lambda: self.service.get_content_analytics(
                query.date_from,
                query.date_to,
                query.granularity,
            ),
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_feedback_analytics(self, query: FeedbackAnalyticsQuery) -> dict:
        return self._execute_cached(
            projection_name="feedback",
            key_parts=(query.date_from, query.date_to, query.granularity),
            loader=lambda: self.service.get_feedback_analytics(
                query.date_from,
                query.date_to,
                query.granularity,
            ),
            validator=lambda payload: isinstance(payload, dict),
        )

    def execute_tenant_analytics(self, query: TenantAnalyticsQuery) -> dict:
        return self._execute_cached(
            projection_name="tenants",
            key_parts=(query.date_from, query.date_to),
            loader=lambda: self.service.get_tenant_analytics(query.date_from, query.date_to),
            ttl_seconds=120,
            validator=lambda payload: isinstance(payload, dict),
        )
