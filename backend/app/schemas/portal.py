"""
Portal schemas for customer-facing API responses
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models import FeedbackStatus, FeedbackType

# ============ Document Schemas ============


class PortalAttachment(BaseModel):
    """Attachment info for portal users"""

    id: int
    filename: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: datetime
    download_url: Optional[str] = None

    class Config:
        from_attributes = True


class PortalDocumentSummary(BaseModel):
    """Minimal document info for list views"""

    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: str
    version: int = 1
    updated_at: datetime
    has_attachments: bool = False

    class Config:
        from_attributes = True


class PortalDocumentDetail(BaseModel):
    """Full document details for portal users"""

    id: int
    title: str
    description: Optional[str] = None
    content: str
    category: Optional[str] = None
    tags: List[str] = []
    visibility: str
    version: int = 1
    created_at: datetime
    updated_at: datetime
    attachments: List[PortalAttachment] = []

    class Config:
        from_attributes = True


class PortalDocumentListResponse(BaseModel):
    """Paginated document list response"""

    items: List[PortalDocumentSummary]
    total: int
    page: int
    per_page: int
    pages: int


# ============ Feedback Schemas ============


class FeedbackCreate(BaseModel):
    """Schema for submitting feedback"""

    document_id: int
    feedback_type: FeedbackType = FeedbackType.OTHER
    content: str = Field(..., min_length=10, max_length=5000)


class FeedbackResponse(BaseModel):
    """Feedback with status and response"""

    id: int
    document_id: int
    document_title: str
    feedback_type: FeedbackType
    content: str
    status: FeedbackStatus
    response: Optional[str] = None
    responded_at: Optional[datetime] = None
    responded_by_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None  # Optional - Feedback model may not have it

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Paginated feedback list response"""

    items: List[FeedbackResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============ Dashboard Schemas ============


class PortalDashboardStats(BaseModel):
    """Statistics for customer dashboard"""

    total_documents: int
    public_documents: int
    company_documents: int
    pending_feedback: int
    responded_feedback: int
