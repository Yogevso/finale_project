"""Analytics Schemas for Dashboard API"""

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TimeGranularity(str, Enum):
    """Time granularity for analytics aggregations"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TimeSeriesPoint(BaseModel):
    """Single data point in a time series"""

    date: str  # ISO format (YYYY-MM-DD) or week/month format
    value: int


class DocumentStats(BaseModel):
    """Document statistics for leaderboards"""

    document_id: int
    document_number: str
    title: str
    view_count: int = 0
    download_count: int = 0


class CategoryCount(BaseModel):
    """Category with document count"""

    category: str
    count: int


class AssignmentChurnItem(BaseModel):
    """Assignment churn count per document."""

    document_id: int
    churn_count: int


class RecentActivity(BaseModel):
    """Recent activity item"""

    id: int
    action: str
    document_id: Optional[int] = None
    document_title: Optional[str] = None
    user_id: int
    user_name: str
    created_at: str
    details: Optional[str] = None


# ============================================================================
# Overview Analytics
# ============================================================================


class AnalyticsOverview(BaseModel):
    """Overview analytics response"""

    period_start: date
    period_end: date

    # Document counts
    total_documents: int
    total_users: int
    total_views: int
    total_downloads: int

    # Breakdowns
    documents_by_status: Dict[str, int]
    documents_by_category: List[CategoryCount]
    by_audience_type: Dict[str, int]

    # Action items
    pending_reviews: int

    # Quick stats
    views_today: int = 0
    new_docs_this_week: int = 0
    exposure_risk_transitions_30d: int = 0
    assignment_churn_90d: List[AssignmentChurnItem] = Field(default_factory=list)


class CompanyAudienceAnalytics(BaseModel):
    """Company-scoped audience analytics summary."""

    company_id: int
    company_name: str
    document_count: int
    active_document_count: int
    company_visible_document_count: int
    view_count_30d: int
    download_count_30d: int
    assignment_churn_90d: int


# ============================================================================
# Engagement Analytics
# ============================================================================


class EngagementAnalytics(BaseModel):
    """Engagement analytics response"""

    period_start: date
    period_end: date
    granularity: TimeGranularity

    # Time series
    views_over_time: List[TimeSeriesPoint]
    downloads_over_time: List[TimeSeriesPoint]

    # Metrics
    unique_visitors: int
    avg_reading_progress: float = Field(ge=0, le=100)
    completion_rate: float = Field(ge=0, le=100)
    total_time_spent_minutes: int


class TopDocuments(BaseModel):
    """Top documents by views and downloads"""

    by_views: List[DocumentStats]
    by_downloads: List[DocumentStats]


# ============================================================================
# User Analytics
# ============================================================================


class UserActivityItem(BaseModel):
    """User activity summary"""

    user_id: int
    username: str
    full_name: str
    role: str
    action_count: int
    last_active: Optional[str] = None


class UserAnalytics(BaseModel):
    """User analytics response"""

    period_start: date
    period_end: date
    granularity: TimeGranularity

    # Counts
    total_users: int
    active_users: int
    inactive_users: int

    # Breakdowns
    users_by_role: Dict[str, int]
    new_users_over_time: List[TimeSeriesPoint]

    # Activity
    most_active_users: List[UserActivityItem]


# ============================================================================
# Content Production Analytics
# ============================================================================


class ContentAnalytics(BaseModel):
    """Content production analytics response"""

    period_start: date
    period_end: date
    granularity: TimeGranularity

    # Time series
    documents_created_over_time: List[TimeSeriesPoint]
    versions_published_over_time: List[TimeSeriesPoint]
    comments_over_time: List[TimeSeriesPoint]

    # Review metrics
    avg_review_turnaround_hours: Optional[float] = None
    approval_rate: float = Field(ge=0, le=100)
    reviews_by_status: Dict[str, int]

    # Totals
    total_documents_created: int
    total_versions_published: int
    total_comments: int


# ============================================================================
# Feedback Analytics
# ============================================================================


class FeedbackAnalytics(BaseModel):
    """Feedback analytics response"""

    period_start: date
    period_end: date
    granularity: TimeGranularity

    # Counts
    total_feedback: int
    pending_feedback: int
    responded_feedback: int

    # Breakdowns
    feedback_by_type: Dict[str, int]
    feedback_by_status: Dict[str, int]
    feedback_over_time: List[TimeSeriesPoint]

    # Metrics
    avg_response_time_hours: Optional[float] = None
    helpfulness_rate: float = Field(ge=0, le=100)


# ============================================================================
# Tenant Analytics (System Admin Only)
# ============================================================================


class TenantMetrics(BaseModel):
    """Metrics for a single tenant"""

    tenant_id: int
    tenant_name: str
    tenant_slug: str
    is_active: bool

    # Counts
    total_documents: int
    total_users: int
    active_users_30d: int
    total_views_30d: int

    # Health score (0-100)
    health_score: float = Field(ge=0, le=100)


class TenantAnalytics(BaseModel):
    """Cross-tenant analytics response"""

    period_start: date
    period_end: date

    # Summary
    total_tenants: int
    active_tenants: int

    # Per-tenant metrics
    tenants: List[TenantMetrics]

    # Comparison time series (optional)
    tenant_activity_over_time: Optional[Dict[str, List[TimeSeriesPoint]]] = None


# ============================================================================
# Export Schemas
# ============================================================================


class ExportRequest(BaseModel):
    """Export request parameters"""

    report_type: str  # overview, engagement, users, content, feedback, tenant-comparison
    date_from: date
    date_to: date
    format: str = "csv"  # csv or pdf


class ExportResponse(BaseModel):
    """Export response metadata"""

    filename: str
    content_type: str
    size_bytes: int
