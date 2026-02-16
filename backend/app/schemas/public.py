"""Public API Schemas - For unauthenticated access"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PublicDocumentSummary(BaseModel):
    """Minimal document fields for public listing"""

    id: int
    document_number: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    release_branch: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    version_number: Optional[int] = None

    class Config:
        from_attributes = True


class PublicDocumentDetail(BaseModel):
    """Full document content for public viewing"""

    id: int
    document_number: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    release_branch: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Version content
    content: Optional[str] = None
    version_number: Optional[int] = None
    published_at: Optional[datetime] = None
    # Attachments info
    has_attachments: bool = False
    attachment_count: int = 0

    class Config:
        from_attributes = True


class PublicAttachmentInfo(BaseModel):
    """Public attachment information"""

    id: int
    filename: str
    file_size: int
    content_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class PublicDocumentWithAttachments(PublicDocumentDetail):
    """Document with attachment list"""

    attachments: List[PublicAttachmentInfo] = []


class PublicPlatformDocument(BaseModel):
    """Document entry for platform history grouping"""

    id: int
    document_number: str
    title: str
    category: Optional[str] = None
    platform: Optional[str] = None
    release_branch: Optional[str] = None
    version_label: Optional[str] = None
    version_number: Optional[int] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PublicPlatformYearGroup(BaseModel):
    """Year grouping for platform history"""

    year: Optional[int] = None
    documents: List[PublicPlatformDocument]


class PublicPlatformCategoryGroup(BaseModel):
    """Category grouping for platform history"""

    category: str
    years: List[PublicPlatformYearGroup]


class PublicPlatformGroup(BaseModel):
    """Platform grouping for platform history"""

    platform: str
    categories: List[PublicPlatformCategoryGroup]


class PublicPlatformHistoryResponse(BaseModel):
    """Platform history response"""

    items: List[PublicPlatformGroup]


class PublicPlatformLatestRelease(BaseModel):
    """Latest release metadata for a platform summary row."""

    id: int
    document_number: str
    title: str
    release_branch: Optional[str] = None
    version_label: Optional[str] = None
    version_number: Optional[int] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PublicPlatformOverviewItem(BaseModel):
    """Platform overview entry used in the platforms landing table."""

    id: int
    platform: str
    doc_count: int
    latest_release: Optional[PublicPlatformLatestRelease] = None


class PublicPlatformOverviewResponse(BaseModel):
    """Response schema for platform overview rows."""

    items: List[PublicPlatformOverviewItem]


class PublicPlatformDocumentRow(BaseModel):
    """Single document row returned for a platform details table."""

    id: int
    title: str
    document_number: str
    category: Optional[str] = None
    version_label: Optional[str] = None
    version_number: Optional[int] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str


class PublicPlatformDocumentsResponse(BaseModel):
    """Paginated document list for a given platform."""

    platform_id: int
    platform: str
    total: int
    items: List[PublicPlatformDocumentRow]


class PublicCategoryCount(BaseModel):
    """Category with document count"""

    category: str
    count: int


class PublicCategoriesResponse(BaseModel):
    """List of categories with counts"""

    items: List[PublicCategoryCount]
    total: int


class PublicDocumentListResponse(BaseModel):
    """Paginated list of public documents"""

    items: List[PublicDocumentSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class PublicSearchResult(BaseModel):
    """Search result item"""

    id: int
    document_number: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    snippet: Optional[str] = None  # Highlighted search snippet
    score: float = 0.0

    class Config:
        from_attributes = True


class PublicSearchResponse(BaseModel):
    """Search response with results"""

    query: str
    items: List[PublicSearchResult]
    total: int
    page: int
    page_size: int


class PublicTopic(BaseModel):
    """Public topic metadata"""

    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    document_count: int


class PublicTopicsResponse(BaseModel):
    """List of topics with counts"""

    items: List[PublicTopic]
    total: int
