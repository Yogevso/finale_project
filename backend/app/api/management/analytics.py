"""Analytics API Endpoints"""

from datetime import date, timedelta
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
from app.dependencies.permissions import (
    require_admin,
    require_internal_user,
    require_manager,
    require_system_admin,
)
from app.dependencies.services import get_analytics_service
from app.dependencies.services import get_document_service
from app.legacy_wrappers import AnalyticsServiceStranglerWrapper
from app.models import User
from app.services.document_service import DocumentService
from app.plugins.exporters import get_analytics_export_plugin_registry
from app.schemas.analytics import (
    AnalyticsOverview,
    CompanyAudienceAnalytics,
    ContentAnalytics,
    EngagementAnalytics,
    FeedbackAnalytics,
    TenantAnalytics,
    TimeGranularity,
    TopDocuments,
    UserAnalytics,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)

_EXPORT_PLUGIN_REGISTRY = get_analytics_export_plugin_registry()
CSV_EXPORT_REPORTS = _EXPORT_PLUGIN_REGISTRY.resolve("csv").supported_reports


def _validate_export_report(report: str, *, allowed: tuple[str, ...], format_name: str) -> None:
    if report not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported analytics export request",
        )


def _resolve_exporter(format_name: str):
    try:
        return _EXPORT_PLUGIN_REGISTRY.resolve(format_name)
    except KeyError as exc:
        logger.warning("Analytics export plugin missing for format %s", format_name, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics export is temporarily unavailable",
        ) from exc


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
    current_user: User = Depends(require_internal_user),
    analytics_query_handler: AnalyticsQueryHandler = Depends(get_analytics_query_handler),
):
    """
    Get recent activity feed.

    Requires: any internal user.
    Returns the most recent actions in the current tenant/system scope.
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


@router.get("/company/{company_id}", response_model=CompanyAudienceAnalytics)
def get_company_audience_analytics(
    company_id: int,
    current_user: User = Depends(require_admin),
    analytics_service: AnalyticsServiceStranglerWrapper = Depends(get_analytics_service),
):
    """
    Company-scoped audience analytics summary.

    Requires: ADMIN role or above.
    Non-system-admin callers are restricted to their own tenant.
    """
    tenant_ctx = analytics_service.tenant_ctx
    if tenant_ctx and not tenant_ctx.is_system_admin and tenant_ctx.tenant_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company scope denied")

    return analytics_service.get_company_audience_analytics(company_id)


@router.get("/documents/{document_id}/audience-churn")
def get_document_audience_churn(
    document_id: int,
    current_user: User = Depends(require_manager),
    analytics_service: AnalyticsServiceStranglerWrapper = Depends(get_analytics_service),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Return assignment churn count for one document over trailing 90 days.
    """
    document = document_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    overview = analytics_service.get_overview(
        date_from=date.today() - timedelta(days=90),
        date_to=date.today(),
    )
    churn_items = overview.get("assignment_churn_90d", [])
    churn_count = 0
    for item in churn_items:
        if int(item.get("document_id", -1)) == document_id:
            churn_count = int(item.get("churn_count", 0))
            break

    return {"document_id": document_id, "assignment_churn_90d": churn_count}


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
    exporter = _resolve_exporter("csv")

    if not date_from or not date_to:
        default_from, default_to = get_default_date_range()
        date_from = date_from or default_from
        date_to = date_to or default_to

    # Cap export range to 90 days
    max_span = timedelta(days=90)
    if date_to - date_from > max_span:
        raise HTTPException(
            status_code=400,
            detail="Export date range cannot exceed 90 days.",
        )

    _validate_export_report(report, allowed=exporter.supported_reports, format_name="CSV")
    try:
        return exporter.export(
            report=report,
            date_from=date_from,
            date_to=date_to,
            analytics_query_handler=analytics_query_handler,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analytics export failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics export is temporarily unavailable",
        ) from exc
