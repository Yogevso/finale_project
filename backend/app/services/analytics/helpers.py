"""Shared helpers for analytics service modules."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func

from app.schemas.analytics import TimeGranularity


class AnalyticsHelpersMixin:
    """Reusable helper methods used across analytics modules."""

    def _get_tenant_filter(self, model):
        if not self.tenant_ctx or self.tenant_ctx.is_system_admin:
            return True
        if hasattr(model, "tenant_id"):
            return model.tenant_id == self.tenant_ctx.tenant_id
        return True

    def _get_date_trunc(self, granularity: TimeGranularity, column):
        if granularity == TimeGranularity.DAILY:
            return func.date(column)
        if granularity == TimeGranularity.WEEKLY:
            return func.strftime("%Y-W%W", column)
        if granularity == TimeGranularity.MONTHLY:
            return func.strftime("%Y-%m", column)
        return func.date(column)

    @staticmethod
    def _auto_granularity(date_from: date, date_to: date) -> TimeGranularity:
        days = (date_to - date_from).days
        if days <= 30:
            return TimeGranularity.DAILY
        if days <= 180:
            return TimeGranularity.WEEKLY
        return TimeGranularity.MONTHLY
