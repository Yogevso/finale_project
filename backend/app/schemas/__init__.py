"""Pydantic Schemas - API Contracts"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import (
    ActionType,
    AudienceEventType,
    DocumentStatus,
    DocumentVisibility,
    ReviewStatus,
    UserRole,
    VersionBumpType,
)


# ========== Tenant Schemas ==========
class TenantSummary(BaseModel):
    """Minimal tenant info for document responses"""

    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


# ========== User Schemas ==========
class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """User creation schema (admin use — includes role and tenant_id)."""

    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.VIEWER
    tenant_id: Optional[int] = None  # Company ID - required for customers

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """AD-011: enforce password complexity — upper, lower, digit, special."""
        import re

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class PublicRegistrationRequest(UserBase):
    """AF-009: Public self-registration schema — no role or tenant_id fields.

    External API payloads must not carry server-owned authority fields.
    """

    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """AD-011: enforce password complexity."""
        import re

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """User update schema"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    tenant_id: Optional[int] = None  # Company ID
    timezone: Optional[str] = Field(None, min_length=1, max_length=64)
    locale: Optional[str] = Field(None, min_length=1, max_length=10)


class UserResponse(UserBase):
    """User response schema"""

    id: int
    role: UserRole
    is_active: bool
    tenant_id: Optional[int] = None
    permissions: List[str] = Field(default_factory=list)
    timezone: str
    locale: str
    notification_preferences: Optional[dict[str, bool]] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithCompanyResponse(UserResponse):
    """User response with company details"""

    company_name: Optional[str] = None
    company_slug: Optional[str] = None


# ========== Authentication Schemas ==========
class LoginRequest(BaseModel):
    """Login request schema"""

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""

    # AD-004: made optional so the cookie-based flow can send an empty body
    refresh_token: Optional[str] = None


class PasswordChange(BaseModel):
    """Password change schema"""

    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """AD-011: enforce password complexity — upper, lower, digit, special."""
        import re

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v


# ========== Document Schemas ==========
class DocumentBase(BaseModel):
    """Base document schema"""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    version_label: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=150)
    platform: Optional[str] = Field(None, max_length=100)
    platform_id: Optional[int] = None
    release_branch: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[date] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)


class DocumentCreate(DocumentBase):
    """Document creation schema"""

    document_number: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[int] = None
    status: DocumentStatus = DocumentStatus.DRAFT
    visibility: DocumentVisibility = DocumentVisibility.INTERNAL
    company_ids: Optional[List[int]] = None


class DocumentUpdate(BaseModel):
    """Document update schema"""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    version_label: Optional[str] = Field(None, max_length=50)
    visibility: Optional[DocumentVisibility] = None
    company_ids: Optional[List[int]] = None
    category: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=150)
    platform: Optional[str] = Field(None, max_length=100)
    platform_id: Optional[int] = None
    release_branch: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = None
    due_date: Optional[date] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    reason: Optional[str] = Field(None, min_length=3, max_length=1000)


class DocumentResponse(DocumentBase):
    """Document response schema"""

    id: int
    document_number: str
    parent_id: Optional[int] = None
    row_version: int = 1
    etag: str
    status: DocumentStatus
    visibility: DocumentVisibility = DocumentVisibility.INTERNAL
    created_by: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    purge_at: Optional[datetime] = None
    deleted_by: Optional[int] = None

    # Optional related data
    created_by_user: Optional["UserResponse"] = None
    versions_count: Optional[int] = None
    attachments_count: Optional[int] = None
    comments_count: Optional[int] = None
    assigned_companies: Optional[List[TenantSummary]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Document list response schema"""

    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentTagSuggestionsResponse(BaseModel):
    """Tenant-scoped tag suggestions for document metadata editors."""

    items: List[str]


class DuplicateDocumentMatch(BaseModel):
    """One similar document match for duplicate-title warnings."""

    document_id: int
    title: str
    document_number: str
    similarity: float


class DuplicateCheckResponse(BaseModel):
    """Similarity check result for a prospective document title."""

    title: str
    threshold: float
    has_matches: bool
    matches: List[DuplicateDocumentMatch] = []


class BulkDocumentMetadataUpdateRequest(BaseModel):
    """Batch metadata update payload for list-view editing."""

    document_ids: List[int] = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    visibility: Optional[DocumentVisibility] = None
    company_ids: Optional[List[int]] = None
    reason: Optional[str] = Field(None, min_length=3, max_length=1000)


class BulkDocumentMetadataUpdateResponse(BaseModel):
    """Result payload for bulk metadata updates."""

    updated_count: int
    document_ids: List[int]
    message: str


# ========== Version Schemas ==========
class VersionBase(BaseModel):
    """Base version schema"""

    content: Optional[str] = Field(None, max_length=500000)  # 500KB max for rich HTML content
    changes_summary: Optional[str] = Field(None, max_length=2000)


class VersionCreate(VersionBase):
    """Version creation schema"""

    bump_type: VersionBumpType = VersionBumpType.PATCH


class VersionUpdate(BaseModel):
    """Version update schema (only unpublished versions)"""

    content: Optional[str] = Field(None, max_length=500000)
    changes_summary: Optional[str] = Field(None, max_length=2000)


class VersionResponse(VersionBase):
    """Version response schema"""

    id: int
    document_id: int
    version_number: int
    semantic_version: Optional[str] = None
    bump_type: VersionBumpType = VersionBumpType.PATCH
    row_version: int = 1
    etag: str
    is_published: bool = False
    published_at: Optional[datetime] = None
    published_by: Optional[int] = None
    created_by: int
    created_at: datetime
    created_by_user: Optional["UserResponse"] = None
    published_by_user: Optional["UserResponse"] = None
    latest_review: Optional["VersionReviewSummary"] = None
    # Audience snapshot at publish time (carry-forward auditing)
    audience_visibility_snapshot: Optional[str] = None
    audience_company_ids_snapshot: Optional[str] = None
    warnings: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    """Version list response"""

    items: List[VersionResponse]
    total: int


class VersionReviewSummary(BaseModel):
    """Latest review details associated with a version"""

    id: int
    status: ReviewStatus
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    submitted_by: int
    reviewed_by: Optional[int] = None
    submitter: Optional["UserResponse"] = None
    reviewer: Optional["UserResponse"] = None

    model_config = ConfigDict(from_attributes=True)


VersionResponse.model_rebuild()
VersionReviewSummary.model_rebuild()


# ========== Attachment Schemas ==========
class AttachmentResponse(BaseModel):
    """Attachment response schema"""

    id: int
    document_id: int
    filename: str
    original_filename: str
    file_size: int
    size_bytes: Optional[int] = None
    mime_type: str
    sha256: Optional[str] = None
    reader_html_status: Optional[str] = None
    reader_toc_source: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentUploadResponse(BaseModel):
    """Attachment upload response"""

    id: int
    filename: str
    sha256: Optional[str] = None
    url: Optional[str] = None
    message: str = "File uploaded successfully"


class AttachmentExtractionWarningResponse(BaseModel):
    """Non-fatal warning emitted during attachment extraction."""

    code: str
    message: str
    count: Optional[int] = None


class AttachmentReaderViewResponse(BaseModel):
    """Derived reader-view artifact status/content for attachment previews."""

    attachment_id: int
    status: str
    html_content: Optional[str] = None
    toc_items: List["AttachmentOutlineItem"] = Field(default_factory=list)
    toc_source: Optional[str] = None
    warnings: List["AttachmentExtractionWarningResponse"] = Field(default_factory=list)
    confidence: Optional[float] = None
    error: Optional[str] = None
    generated_at: Optional[datetime] = None


class AttachmentOutlineItem(BaseModel):
    """Reader-view outline item for TOC navigation."""

    id: str
    level: int
    title: str
    page: int
    page_start: int
    page_end: Optional[int] = None
    anchor_id: Optional[str] = None

AttachmentReaderViewResponse.model_rebuild()


# ========== Comment Schemas ==========
class CommentBase(BaseModel):
    """Base comment schema"""

    content: str = Field(..., min_length=1, max_length=5000)


class CommentCreate(CommentBase):
    """Comment creation schema"""

    is_private: bool = False  # Private = only admins/editors can see
    anchor_text: Optional[str] = None  # The text that was selected for inline comment
    anchor_id: Optional[str] = None  # Reference to heading/section ID
    parent_id: Optional[int] = None  # For replies to create threads


class CommentUpdate(BaseModel):
    """Comment update schema"""

    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_resolved: Optional[bool] = None  # Mark thread as resolved


class CommentAuthor(BaseModel):
    """Minimal author info for comments"""

    id: int
    username: str
    full_name: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(CommentBase):
    """Comment response schema"""

    id: int
    document_id: int
    user_id: int
    parent_id: Optional[int] = None
    is_private: bool = False
    anchor_text: Optional[str] = None
    anchor_id: Optional[str] = None
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime
    user: Optional[CommentAuthor] = None
    replies: list["CommentResponse"] = []
    reply_count: int = 0
    chat_id: Optional[int] = None  # Direct chat created/found for this comment

    model_config = ConfigDict(from_attributes=True)


# Forward reference for nested replies
CommentResponse.model_rebuild()


# ========== Audit Log Schemas ==========
class AuditLogResponse(BaseModel):
    """Audit log response schema"""

    id: int
    user_id: Optional[int]
    document_id: Optional[int]
    action: ActionType
    audience_event_type: Optional[AudienceEventType] = None
    details: Optional[str]
    assignment_diff: Optional[str] = None
    signature_key_id: Optional[str] = None
    signature: Optional[str] = None
    ip_address: Optional[str]
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ========== Review Schemas ==========
class ReviewSubmit(BaseModel):
    """Submit document for review"""

    version_id: Optional[int] = None
    message: Optional[str] = Field(None, max_length=1000)


class ReviewAction(BaseModel):
    """Approve or reject a review"""

    comments: Optional[str] = Field(None, max_length=2000)


class ReviewReject(BaseModel):
    """Reject a review (comments required)"""

    comments: str = Field(..., min_length=1, max_length=2000)


class AudienceDiff(BaseModel):
    """Diff between review snapshot and current document audience state."""

    has_changes: bool = False
    snapshot_visibility: Optional[str] = None
    current_visibility: Optional[str] = None
    visibility_changed: bool = False
    snapshot_company_ids: List[int] = []
    current_company_ids: List[int] = []
    companies_added: List[int] = []
    companies_removed: List[int] = []


class ApprovalPolicyCheck(BaseModel):
    """Individual policy check result for approval."""

    id: str
    label: str
    passed: bool
    message: Optional[str] = None


class PreApprovePolicy(BaseModel):
    """Pre-approve policy explanation payload."""

    can_approve: bool
    checks: List[ApprovalPolicyCheck]
    audience_summary: Optional[str] = None
    warnings: List[str] = []


class ReviewResponse(BaseModel):
    """Review response with document info"""

    id: int
    document_id: int
    version_id: Optional[int] = None
    submitted_by: int
    reviewed_by: Optional[int] = None
    status: ReviewStatus
    message: Optional[str] = None
    review_comments: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_reminded_at: Optional[datetime] = None
    manager_escalated_at: Optional[datetime] = None
    created_at: datetime
    audience_visibility_snapshot: Optional[str] = None
    audience_company_ids_snapshot: Optional[str] = None
    audience_diff: Optional[AudienceDiff] = None
    document: Optional["DocumentResponse"] = None
    submitter: Optional[UserResponse] = None
    reviewer: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated list of reviews"""

    items: List[ReviewResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class ReviewSlaItem(BaseModel):
    """One review evaluated by the SLA processor."""

    review_id: int
    document_id: int
    reminder_sent: bool = False
    escalation_sent: bool = False
    reminder_recipient_ids: List[int] = []
    escalation_recipient_ids: List[int] = []


class ReviewSlaProcessResponse(BaseModel):
    """Summary of one SLA processing pass."""

    processed_at: datetime
    reminder_threshold_hours: int
    escalation_threshold_hours: int
    reviews_scanned: int
    reminders_sent: int
    escalations_sent: int
    items: List[ReviewSlaItem] = []


# ========== BFF Schemas ==========
class AudienceAccessPreviewResponse(BaseModel):
    """Computed audience preview for a document's current visibility state."""

    visibility: DocumentVisibility
    is_public: bool
    includes_internal_users: bool
    target_companies: List[TenantSummary]
    access_summary: str
    # Snapshot from last published version (None if never published)
    published_visibility_snapshot: Optional[str] = None
    published_company_ids_snapshot: Optional[List[int]] = None
    audience_changed_since_publish: bool = False


class DocumentDetailPageBundleResponse(BaseModel):
    """Aggregated payload for the internal document detail page."""

    document: DocumentResponse
    attachments: List[AttachmentResponse]
    assigned_companies: List[TenantSummary]
    audience_access_preview: AudienceAccessPreviewResponse
    review_history: ReviewListResponse
    # Partial-failure tracking: lists sub-sections that failed to load
    partial_errors: Optional[List[str]] = None


# ========== General Schemas ==========
class MessageResponse(BaseModel):
    """Generic message response"""

    message: str


class DocumentWatchStatusResponse(BaseModel):
    """Current user's watch state for a document."""

    is_watching: bool


class DocumentWatchResponse(BaseModel):
    """Response payload for watch/unwatch state changes."""

    document_id: int
    user_id: int
    is_watching: bool
    watched_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Error response schema"""

    detail: str


class DocumentCalendarExportResponse(BaseModel):
    """JSON payload used by the frontend to download an iCal file."""

    document_id: int
    filename: str
    content_type: str = "text/calendar"
    due_date: date
    ical: str


class ForcePublishRequest(BaseModel):
    """Request body for forced publish override."""

    reason: str = Field(..., min_length=10, max_length=1000, description="Admin justification for forced publish")
    acknowledge_risks: bool = Field(..., description="Confirm acknowledgment of risks")


class ForcePublishResponse(BaseModel):
    """Response for forced publish override."""

    version_id: int
    document_id: int
    published_at: str
    forced_by_user_id: int
    reason: str
    warnings_overridden: List[str] = []


class SchedulePublishRequest(BaseModel):
    """Request to schedule a version for future publish."""

    scheduled_publish_at: datetime

    @field_validator("scheduled_publish_at")
    @classmethod
    def validate_future_date(cls, v):
        if v <= datetime.utcnow():
            raise ValueError("Scheduled publish time must be in the future")
        return v


class SchedulePublishResponse(BaseModel):
    """Response for scheduled publish."""

    version_id: int
    document_id: int
    scheduled_publish_at: str
    audience_validated_at: str


class CancelScheduledPublishResponse(BaseModel):
    """Response for cancelled scheduled publish."""

    version_id: int
    document_id: int
    cancelled_scheduled_at: str


class ScheduledPublishReport(BaseModel):
    """Report from processing scheduled publishes."""

    processed: int
    published: int
    failed_validation: int
    failed_stale_company: int
    errors: List[dict] = []


class PublishPreflightCheckItem(BaseModel):
    """A single preflight check item for publish readiness"""

    id: str
    label: str
    passed: bool
    message: Optional[str] = None


class PublishPreflightResponse(BaseModel):
    """Response containing all preflight checks for publishing a version"""

    ready: bool
    checks: List[PublishPreflightCheckItem]


# Export all schemas
__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "PublicRegistrationRequest",
    "UserUpdate",
    "UserResponse",
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordChange",
    # Document
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentTagSuggestionsResponse",
    "DuplicateDocumentMatch",
    "DuplicateCheckResponse",
    "BulkDocumentMetadataUpdateRequest",
    "BulkDocumentMetadataUpdateResponse",
    # Version
    "VersionBase",
    "VersionCreate",
    "VersionUpdate",
    "VersionResponse",
    "VersionListResponse",
    "VersionReviewSummary",
    # Attachment
    "AttachmentResponse",
    "AttachmentUploadResponse",
    "AttachmentExtractionWarningResponse",
    "AttachmentReaderViewResponse",
    "AttachmentOutlineItem",
    # Comment
    "CommentBase",
    "CommentCreate",
    "CommentUpdate",
    "CommentResponse",
    # Review
    "ReviewSubmit",
    "ReviewAction",
    "ReviewReject",
    "ReviewResponse",
    "ReviewListResponse",
    "ReviewSlaItem",
    "ReviewSlaProcessResponse",
    # BFF
    "AudienceAccessPreviewResponse",
    "DocumentDetailPageBundleResponse",
    # Audit
    "AuditLogResponse",
    # General
    "MessageResponse",
    "DocumentCalendarExportResponse",
    "ErrorResponse",
    # Publish preflight
    "PublishPreflightCheckItem",
    "PublishPreflightResponse",
]
