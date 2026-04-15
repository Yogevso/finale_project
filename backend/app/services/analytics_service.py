"""Analytics service facade composed from dashboard-specific mixins."""

from typing import Optional

from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.services.analytics import (
    AnalyticsContentMixin,
    AnalyticsEngagementMixin,
    AnalyticsFeedbackMixin,
    AnalyticsHelpersMixin,
    AnalyticsOverviewMixin,
    AnalyticsTenantsMixin,
    AnalyticsUsersMixin,
)
from app.services.base_service import SessionService


class AnalyticsService(
    AnalyticsHelpersMixin,
    AnalyticsOverviewMixin,
    AnalyticsEngagementMixin,
    AnalyticsUsersMixin,
    AnalyticsContentMixin,
    AnalyticsFeedbackMixin,
    AnalyticsTenantsMixin,
    SessionService,
):
    """Service facade for analytics modules with tenant-aware context."""

    def __init__(
        self,
        db: Session,
        tenant_ctx: Optional[TenantContext] = None,
        analytics_db: Session | None = None,
    ):
        super().__init__(db)
        if tenant_ctx is None:
            raise ValueError(
                "AnalyticsService requires an explicit scope; use a system-admin tenant context for cross-tenant analytics"
            )
        self.tenant_ctx = tenant_ctx
        self.analytics_db = analytics_db or db
