"""Analytics API Endpoints"""

import csv
from datetime import date, timedelta
from io import BytesIO, StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.application.queries.analytics_queries import (
    AnalyticsOverviewQuery,
    AnalyticsQueryHandler,
    ContentAnalyticsQuery,
    EngagementAnalyticsQuery,
    FeedbackAnalyticsQuery,
    RecentActivityQuery,
    TenantAnalyticsQuery,
    TopDocumentsQuery,
    UserAnalyticsQuery,
)
from app.application.queries.dependencies import (
    get_analytics_query_handler,
    get_system_analytics_query_handler,
)
from app.dependencies.permissions import require_admin, require_manager, require_system_admin
from app.models import User
from app.schemas.analytics import (
    AnalyticsOverview,
    ContentAnalytics,
    EngagementAnalytics,
    FeedbackAnalytics,
    TenantAnalytics,
    TimeGranularity,
    TopDocuments,
    UserAnalytics,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

CSV_EXPORT_REPORTS = ("overview", "engagement", "users", "content", "feedback")
PDF_EXPORT_REPORTS = ("overview", "engagement")


def _validate_export_report(report: str, *, allowed: tuple[str, ...], format_name: str) -> None:
    if report not in allowed:
        allowed_list = ", ".join(allowed)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {format_name} report '{report}'. Supported reports: {allowed_list}",
        )


def get_default_date_range() -> tuple[date, date]:
    """Get default date range (last 30 days)"""
    today = date.today()
    return today - timedelta(days=30), today


# ============================================================================
# Overview Analytics
# ============================================================================


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    date_from: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    date_to: Optional[date] = Query(None, description="End date (default: today)"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get overview analytics.

    Requires: MANAGER role or above.
    Returns summary statistics including document counts, views, downloads,
    and breakdowns by status and category.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_overview(
        AnalyticsOverviewQuery(date_from=date_from, date_to=date_to)
    )


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get recent activity feed.

    Requires: MANAGER role or above.
    Returns the most recent actions in the system.
    """
    return analytics_query_handler.execute_recent_activity(RecentActivityQuery(limit=limit))


# ============================================================================
# Engagement Analytics
# ============================================================================


@router.get("/engagement", response_model=EngagementAnalytics)
def get_engagement_analytics(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    granularity: Optional[TimeGranularity] = Query(None, description="Time granularity"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get engagement analytics.

    Requires: MANAGER role or above.
    Returns views over time, downloads over time, reading progress metrics.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_engagement(
        EngagementAnalyticsQuery(
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
        )
    )


@router.get("/engagement/top-documents", response_model=TopDocuments)
def get_top_documents(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    limit: int = Query(10, ge=1, le=50, description="Number of documents"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get top documents by views and downloads.

    Requires: MANAGER role or above.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_top_documents(
        TopDocumentsQuery(date_from=date_from, date_to=date_to, limit=limit)
    )


# ============================================================================
# User Analytics
# ============================================================================


@router.get("/users", response_model=UserAnalytics)
def get_user_analytics(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    granularity: Optional[TimeGranularity] = Query(None, description="Time granularity"),
    current_user: User = Depends(require_admin),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get user analytics.

    Requires: ADMIN role or above.
    Returns user counts, role distribution, new registrations over time.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_user_analytics(
        UserAnalyticsQuery(date_from=date_from, date_to=date_to, granularity=granularity)
    )


# ============================================================================
# Content Production Analytics
# ============================================================================


@router.get("/content", response_model=ContentAnalytics)
def get_content_analytics(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    granularity: Optional[TimeGranularity] = Query(None, description="Time granularity"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get content production analytics.

    Requires: MANAGER role or above.
    Returns document creation trends, version publishing, review metrics.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_content_analytics(
        ContentAnalyticsQuery(date_from=date_from, date_to=date_to, granularity=granularity)
    )


# ============================================================================
# Feedback Analytics
# ============================================================================


@router.get("/feedback", response_model=FeedbackAnalytics)
def get_feedback_analytics(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    granularity: Optional[TimeGranularity] = Query(None, description="Time granularity"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get feedback analytics.

    Requires: MANAGER role or above.
    Returns feedback counts, type distribution, response times.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_feedback_analytics(
        FeedbackAnalyticsQuery(date_from=date_from, date_to=date_to, granularity=granularity)
    )


# ============================================================================
# Tenant Analytics (System Admin Only)
# ============================================================================


@router.get("/tenants", response_model=TenantAnalytics)
def get_tenant_analytics(
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(require_system_admin),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_system_analytics_query_handler),
):
    """
    Get cross-tenant analytics.

    Requires: SYSTEM_ADMIN role.
    Returns per-tenant metrics and health scores.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    return analytics_query_handler.execute_tenant_analytics(
        TenantAnalyticsQuery(date_from=date_from, date_to=date_to)
    )


# ============================================================================
# Export Endpoints
# ============================================================================


@router.get("/export/csv")
def export_csv(
    report: str = Query(
        ..., description="Report type: overview, engagement, users, content, feedback"
    ),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Export analytics data as CSV.

    Requires: MANAGER role or above.
    Supported reports: overview, engagement, users, content, feedback.
    """
    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    _validate_export_report(report, allowed=CSV_EXPORT_REPORTS, format_name="CSV")

    # Get data based on report type
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
        # Add status breakdown
        for status, count in data["documents_by_status"].items():
            rows.append({"metric": f"Documents - {status}", "value": count})

    elif report == "engagement":
        data = analytics_query_handler.execute_engagement(
            EngagementAnalyticsQuery(date_from=date_from, date_to=date_to)
        )
        rows = [
            {"metric": "Unique Visitors", "value": data["unique_visitors"]},
            {"metric": "Avg Reading Progress (%)", "value": data["avg_reading_progress"]},
            {"metric": "Completion Rate (%)", "value": data["completion_rate"]},
            {"metric": "Total Time Spent (min)", "value": data["total_time_spent_minutes"]},
        ]
        # Add time series data
        for point in data["views_over_time"]:
            rows.append({"metric": f"Views - {point['date']}", "value": point["value"]})

    elif report == "users":
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

    elif report == "content":
        data = analytics_query_handler.execute_content_analytics(
            ContentAnalyticsQuery(date_from=date_from, date_to=date_to)
        )
        rows = [
            {"metric": "Documents Created", "value": data["total_documents_created"]},
            {"metric": "Versions Published", "value": data["total_versions_published"]},
            {"metric": "Total Comments", "value": data["total_comments"]},
            {"metric": "Approval Rate (%)", "value": data["approval_rate"]},
            {
                "metric": "Avg Review Turnaround (hrs)",
                "value": data["avg_review_turnaround_hours"] or "N/A",
            },
        ]

    elif report == "feedback":
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
        for ftype, count in data["feedback_by_type"].items():
            rows.append({"metric": f"Feedback - {ftype}", "value": count})

    # Generate CSV
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


@router.get("/export/pdf")
def export_pdf(
    report: str = Query(..., description="Report type"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(require_manager),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Export analytics data as PDF.

    Requires: MANAGER role or above.
    Note: Requires reportlab package to be installed.
    """
    _validate_export_report(report, allowed=PDF_EXPORT_REPORTS, format_name="PDF")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF export requires reportlab package. Install with: pip install reportlab",
        ) from None

    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    # Get data
    if report == "overview":
        data = analytics_query_handler.execute_overview(
            AnalyticsOverviewQuery(date_from=date_from, date_to=date_to)
        )
        table_data = [
            ["Metric", "Value"],
            ["Total Documents", str(data["total_documents"])],
            ["Total Users", str(data["total_users"])],
            ["Total Views", str(data["total_views"])],
            ["Total Downloads", str(data["total_downloads"])],
            ["Pending Reviews", str(data["pending_reviews"])],
        ]
        title = "Analytics Overview Report"
    elif report == "engagement":
        data = analytics_query_handler.execute_engagement(
            EngagementAnalyticsQuery(date_from=date_from, date_to=date_to)
        )
        table_data = [
            ["Metric", "Value"],
            ["Unique Visitors", str(data["unique_visitors"])],
            ["Avg Reading Progress", f"{data['avg_reading_progress']}%"],
            ["Completion Rate", f"{data['completion_rate']}%"],
            ["Total Time Spent", f"{data['total_time_spent_minutes']} minutes"],
        ]
        title = "Engagement Analytics Report"

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(f"Period: {date_from} to {date_to}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    table = Table(table_data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"analytics_{report}_{date_to.isoformat()}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
