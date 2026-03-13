"""Plugin registry for analytics export formats."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import date
from io import StringIO
from typing import Protocol

from fastapi.responses import StreamingResponse

from app.application.queries.analytics_queries import (
    AnalyticsOverviewQuery,
    AnalyticsQueryHandler,
    ContentAnalyticsQuery,
    EngagementAnalyticsQuery,
    FeedbackAnalyticsQuery,
    UserAnalyticsQuery,
)


class AnalyticsExporterPlugin(Protocol):
    """Plugin contract for analytics export formatters."""

    format_name: str
    supported_reports: tuple[str, ...]

    def export(
        self,
        *,
        report: str,
        date_from: date,
        date_to: date,
        analytics_query_handler: AnalyticsQueryHandler,
    ) -> StreamingResponse:
        """Export analytics report payload to a concrete response format."""


class AnalyticsExportPluginRegistry:
    """Registry that manages export-format plugin lifecycle."""

    def __init__(self, plugins: Sequence[AnalyticsExporterPlugin] | None = None) -> None:
        self._plugins: dict[str, AnalyticsExporterPlugin] = {}
        self.load(plugins or [])

    def load(self, plugins: Sequence[AnalyticsExporterPlugin]) -> None:
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: AnalyticsExporterPlugin) -> None:
        format_name = (plugin.format_name or "").strip().lower()
        if not format_name:
            raise ValueError("Exporter plugin format_name is required")
        if format_name in self._plugins:
            raise ValueError(f"Exporter plugin '{format_name}' is already registered")
        if not plugin.supported_reports:
            raise ValueError(f"Exporter plugin '{format_name}' must declare supported reports")
        self._plugins[format_name] = plugin

    def resolve(self, format_name: str) -> AnalyticsExporterPlugin:
        normalized = format_name.strip().lower()
        plugin = self._plugins.get(normalized)
        if not plugin:
            raise KeyError(f"No analytics exporter plugin registered for format '{format_name}'")
        return plugin


class CsvAnalyticsExporterPlugin:
    """CSV analytics export plugin."""

    format_name = "csv"
    supported_reports = ("overview", "engagement", "users", "content", "feedback")

    def export(
        self,
        *,
        report: str,
        date_from: date,
        date_to: date,
        analytics_query_handler: AnalyticsQueryHandler,
    ) -> StreamingResponse:
        rows = self._build_rows(
            report=report,
            date_from=date_from,
            date_to=date_to,
            analytics_query_handler=analytics_query_handler,
        )

        output = StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        output.seek(0)
        filename = f"analytics_{report}_{date_to.isoformat()}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    def _build_rows(
        self,
        *,
        report: str,
        date_from: date,
        date_to: date,
        analytics_query_handler: AnalyticsQueryHandler,
    ) -> list[dict[str, object]]:
        if report == "overview":
            data = analytics_query_handler.execute_overview(
                AnalyticsOverviewQuery(date_from=date_from, date_to=date_to)
            )
            rows = [
                {"metric": "Total Documents", "value": data["total_documents"]},
                {"metric": "Total Users", "value": data["total_users"]},
                {"metric": "Total Views", "value": data["total_views"]},
                {"metric": "Total Downloads", "value": data["total_downloads"]},
                {"metric": "Pending Reviews", "value": data["pending_reviews"]},
                {"metric": "Views Today", "value": data["views_today"]},
                {"metric": "New Docs This Week", "value": data["new_docs_this_week"]},
            ]
            for status_name, count in data["documents_by_status"].items():
                rows.append({"metric": f"Documents - {status_name}", "value": count})
            return rows

        if report == "engagement":
            data = analytics_query_handler.execute_engagement(
                EngagementAnalyticsQuery(date_from=date_from, date_to=date_to)
            )
            rows = [
                {"metric": "Unique Visitors", "value": data["unique_visitors"]},
                {"metric": "Avg Reading Progress (%)", "value": data["avg_reading_progress"]},
                {"metric": "Completion Rate (%)", "value": data["completion_rate"]},
                {"metric": "Total Time Spent (min)", "value": data["total_time_spent_minutes"]},
            ]
            for point in data["views_over_time"]:
                rows.append({"metric": f"Views - {point['date']}", "value": point["value"]})
            return rows

        if report == "users":
            data = analytics_query_handler.execute_user_analytics(
                UserAnalyticsQuery(date_from=date_from, date_to=date_to)
            )
            rows = [
                {"metric": "Total Users", "value": data["total_users"]},
                {"metric": "Active Users", "value": data["active_users"]},
                {"metric": "Inactive Users", "value": data["inactive_users"]},
            ]
            for role, count in data["users_by_role"].items():
                rows.append({"metric": f"Users - {role}", "value": count})
            return rows

        if report == "content":
            data = analytics_query_handler.execute_content_analytics(
                ContentAnalyticsQuery(date_from=date_from, date_to=date_to)
            )
            return [
                {"metric": "Documents Created", "value": data["total_documents_created"]},
                {"metric": "Versions Published", "value": data["total_versions_published"]},
                {"metric": "Total Comments", "value": data["total_comments"]},
                {"metric": "Approval Rate (%)", "value": data["approval_rate"]},
                {
                    "metric": "Avg Review Turnaround (hrs)",
                    "value": data["avg_review_turnaround_hours"] or "N/A",
                },
            ]

        if report == "feedback":
            data = analytics_query_handler.execute_feedback_analytics(
                FeedbackAnalyticsQuery(date_from=date_from, date_to=date_to)
            )
            rows = [
                {"metric": "Total Feedback", "value": data["total_feedback"]},
                {"metric": "Pending Feedback", "value": data["pending_feedback"]},
                {"metric": "Responded Feedback", "value": data["responded_feedback"]},
                {"metric": "Helpfulness Rate (%)", "value": data["helpfulness_rate"]},
                {
                    "metric": "Avg Response Time (hrs)",
                    "value": data["avg_response_time_hours"] or "N/A",
                },
            ]
            for feedback_type, count in data["feedback_by_type"].items():
                rows.append({"metric": f"Feedback - {feedback_type}", "value": count})
            return rows

        raise ValueError(f"Unsupported CSV report '{report}'")


def build_default_analytics_export_plugin_registry() -> AnalyticsExportPluginRegistry:
    """Load default export plugins."""
    return AnalyticsExportPluginRegistry(
        plugins=[
            CsvAnalyticsExporterPlugin(),
        ]
    )


_default_analytics_export_plugin_registry = build_default_analytics_export_plugin_registry()


def get_analytics_export_plugin_registry() -> AnalyticsExportPluginRegistry:
    """Resolve shared analytics export plugin registry singleton."""
    return _default_analytics_export_plugin_registry
