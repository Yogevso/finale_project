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
    tags: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicDocumentDetail(BaseModel):
    """Full document content for public viewing"""

    id: int
    document_number: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
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
