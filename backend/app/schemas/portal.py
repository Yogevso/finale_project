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
    document_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    release_branch: Optional[str] = None
    tags: Optional[str] = None
    thumbnail_url: Optional[str] = None
    visibility: str
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: datetime
    published_at: Optional[datetime] = None
    has_attachments: bool = False

    class Config:
        from_attributes = True


class PortalDocumentDetail(BaseModel):
    """Full document details for portal users"""

    id: int
    document_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    content: str
    category: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    release_branch: Optional[str] = None
    tags: List[str] = []
    thumbnail_url: Optional[str] = None
    visibility: str
    version: int = 1
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    toc_items: List["PortalDocumentTocItem"] = []
    attachments: List[PortalAttachment] = []

    class Config:
        from_attributes = True


class PortalDocumentTocItem(BaseModel):
    """Stored reader outline item for portal consumers."""

    id: str
    level: int = 1
    title: str
    page: int = 1
    page_start: int = 1
    page_end: Optional[int] = None
    anchor_id: Optional[str] = None


PortalDocumentDetail.model_rebuild()


class PortalDocumentListResponse(BaseModel):
    """Paginated document list response"""

    items: List[PortalDocumentSummary]
    total: int
    page: int
    per_page: int
    total_pages: int


class FacetItem(BaseModel):
    name: str
    count: int


class PortalFacetsResponse(BaseModel):
    """Facet counts for portal sidebar filters"""

    categories: List[FacetItem] = []
    topics: List[FacetItem] = []
    platforms: List[FacetItem] = []


# ============ Feedback Schemas ============


class FeedbackCreate(BaseModel):
    """Schema for submitting feedback"""

    document_id: int
    feedback_type: FeedbackType = FeedbackType.OTHER
    content: str = Field(..., min_length=10, max_length=5000)
    anchor_text: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Feedback with status and response"""

    id: int
    document_id: int
    document_title: str
    ticket_id: Optional[int] = None
    feedback_type: FeedbackType
    content: str
    anchor_text: Optional[str] = None
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
    total_pages: int


# ============ Dashboard Schemas ============


class PortalDashboardStats(BaseModel):
    """Statistics for customer dashboard"""

    total_documents: int
    public_documents: int
    company_documents: int
    pending_feedback: int
    responded_feedback: int
