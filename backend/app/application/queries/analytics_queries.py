"""Application query handlers for analytics read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

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

    def __init__(self, service: AnalyticsService):
        self.service = service

    def execute_overview(self, query: AnalyticsOverviewQuery) -> dict:
        return self.service.get_overview(query.date_from, query.date_to)

    def execute_recent_activity(self, query: RecentActivityQuery) -> list:
        return self.service.get_recent_activity(query.limit)

    def execute_engagement(self, query: EngagementAnalyticsQuery) -> dict:
        return self.service.get_engagement(query.date_from, query.date_to, query.granularity)

    def execute_top_documents(self, query: TopDocumentsQuery) -> dict:
        return self.service.get_top_documents(query.date_from, query.date_to, query.limit)

    def execute_user_analytics(self, query: UserAnalyticsQuery) -> dict:
        return self.service.get_user_analytics(query.date_from, query.date_to, query.granularity)

    def execute_content_analytics(self, query: ContentAnalyticsQuery) -> dict:
        return self.service.get_content_analytics(
            query.date_from,
            query.date_to,
            query.granularity,
        )

    def execute_feedback_analytics(self, query: FeedbackAnalyticsQuery) -> dict:
        return self.service.get_feedback_analytics(
            query.date_from,
            query.date_to,
            query.granularity,
        )

    def execute_tenant_analytics(self, query: TenantAnalyticsQuery) -> dict:
        return self.service.get_tenant_analytics(query.date_from, query.date_to)
