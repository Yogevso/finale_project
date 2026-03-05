"""Strangler wrapper boundary around legacy analytics service internals."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.legacy_wrappers.tracking import get_legacy_wrapper_tracker

ANALYTICS_WRAPPER_NAME = "analytics_service"

_tracker = get_legacy_wrapper_tracker()
_tracker.register_wrapper(
    wrapper_name=ANALYTICS_WRAPPER_NAME,
    legacy_module="app.services.analytics_service",
    migration_completion_percent=0,
)


class AnalyticsServiceStranglerWrapper:
    """Compatibility wrapper around analytics service while internals are migrated."""

    def __init__(self, legacy_service: Any):
        self._legacy_service = legacy_service

    @property
    def tenant_ctx(self) -> Any:
        return getattr(self._legacy_service, "tenant_ctx", None)

    def _record_legacy_usage(self) -> None:
        _tracker.increment_call(ANALYTICS_WRAPPER_NAME)

    def get_overview(self, date_from: date, date_to: date) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_overview(date_from, date_to)

    def get_recent_activity(self, limit: int = 10) -> list:
        self._record_legacy_usage()
        return self._legacy_service.get_recent_activity(limit)

    def get_engagement(self, date_from: date, date_to: date, granularity=None) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_engagement(date_from, date_to, granularity)

    def get_top_documents(self, date_from: date, date_to: date, limit: int = 10) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_top_documents(date_from, date_to, limit)

    def get_user_analytics(self, date_from: date, date_to: date, granularity=None) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_user_analytics(date_from, date_to, granularity)

    def get_content_analytics(self, date_from: date, date_to: date, granularity=None) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_content_analytics(date_from, date_to, granularity)

    def get_feedback_analytics(self, date_from: date, date_to: date, granularity=None) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_feedback_analytics(date_from, date_to, granularity)

    def get_tenant_analytics(self, date_from: date, date_to: date) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_tenant_analytics(date_from, date_to)

    def get_company_audience_analytics(self, company_id: int) -> dict:
        self._record_legacy_usage()
        return self._legacy_service.get_company_audience_analytics(company_id)

    def export_audit_logs(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        self._record_legacy_usage()
        return self._legacy_service.export_audit_logs(date_from=date_from, date_to=date_to)
