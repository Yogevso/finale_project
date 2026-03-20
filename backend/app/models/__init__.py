"""Database Models"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db import Base
from app.utils.concurrency import build_resource_etag


# Enums
class UserRole(str, enum.Enum):
    """User roles - 6 total roles for the customer portal"""

    SYSTEM_ADMIN = "system_admin"  # Full platform control, manages admins
    ADMIN = "admin"  # Manages users, companies, full access
    MANAGER = "manager"  # Approves content, creates editors, publishes
    EDITOR = "editor"  # Creates/edits content, peer reviews
    VIEWER = "viewer"  # Internal viewer (legacy, same as editor but read-only)
    CUSTOMER = "customer"  # External - views company docs, downloads, submits feedback


class DocumentStatus(str, enum.Enum):
    """Document lifecycle statuses.

    AF-008: The canonical published state is ``PUBLISHED``.
    The database stores ``"active"`` as the value for backward compatibility.
    ``ACTIVE`` is retained as an alias so existing queries continue to work.
    New code should use ``DocumentStatus.PUBLISHED``.
    """

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"  # Waiting for approval
    APPROVED = "approved"  # Approved for publish, not public yet
    ACTIVE = "active"  # Legacy alias — prefer PUBLISHED
    PUBLISHED = "active"  # Canonical published state (DB value is "active")
    ARCHIVED = "archived"


class DocumentVisibility(str, enum.Enum):
    """Document visibility levels"""

    PUBLIC = "public"  # Anyone can see (no login needed)
    INTERNAL = "internal"  # All internal staff (editor+)
    COMPANY = "company"  # Assigned companies + internal staff


class ReviewStatus(str, enum.Enum):
    """Review request statuses"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VersionBumpType(str, enum.Enum):
    """Version bump level for semantic versioning"""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class FeedbackType(str, enum.Enum):
    """Feedback types from customers"""

    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    """Feedback processing status"""

    PENDING = "pending"
    RESPONDED = "responded"
    CLOSED = "closed"


class ActionType(str, enum.Enum):
    """Audit log action types"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    DOWNLOAD = "download"
    PUBLISH = "publish"
    SYSTEM = "system"


class AudienceEventType(str, enum.Enum):
    """Audience-specific audit taxonomy used for compliance analytics."""

    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_REMOVED = "assignment_removed"
    VISIBILITY_CHANGED = "visibility_changed"
    AUDIENCE_SNAPSHOT_TAKEN = "audience_snapshot_taken"
    AUDIENCE_ROLLBACK = "audience_rollback"


class NotificationType(str, enum.Enum):
    """Notification types"""

    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_PUBLISHED = "document_published"
    COMMENT_ADDED = "comment_added"
    COMMENT_REPLY = "comment_reply"
    VERSION_PUBLISHED = "version_published"
    REVIEW_SUBMITTED = "review_submitted"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    REVIEW_REMINDER = "review_reminder"
    REVIEW_ESCALATED = "review_escalated"
    FEEDBACK_RECEIVED = "feedback_received"
    FEEDBACK_RESPONDED = "feedback_responded"
    INVITATION_SENT = "invitation_sent"
    TICKET_HANDOFF = "ticket_handoff"
    TICKET_NEW_CUSTOMER_MSG = "ticket_new_customer_msg"
    TICKET_MENTION = "ticket_mention"
    SYSTEM = "system"


class InvitationStatus(str, enum.Enum):
    """Invitation status"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CollaborationActivityType(str, enum.Enum):
    """Collaboration activity types"""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    CONTENT_EDITED = "content_edited"
    CURSOR_MOVED = "cursor_moved"
    SELECTION_CHANGED = "selection_changed"
    VERSION_CREATED = "version_created"
    COMMENT_ADDED = "comment_added"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_RESTORED = "snapshot_restored"


class SnapshotType(str, enum.Enum):
    """Collaboration snapshot types (NOT release versions)"""

    AUTO_SAVE = "auto_save"  # Automatic periodic saves
    MANUAL_SAVE = "manual_save"  # User-triggered save action
    SESSION_END = "session_end"  # When last user leaves
    PRE_PUBLISH = "pre_publish"  # Before creating a Version


# Junction table for document-company assignments
document_company_assignments = Table(
    "document_company_assignments",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants.id"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
    Column("assigned_by", Integer, ForeignKey("users.id")),
    Index(
        "ix_document_company_assignments_document_id_tenant_id",
        "document_id",
        "tenant_id",
    ),
)


# Models
class Tenant(Base):
    """Tenant model - represents an organization/company"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(Text, nullable=True)  # JSON settings
    company_logo = Column(String(500), nullable=True)  # Logo URL
    contact_email = Column(String(255), nullable=True)  # Primary contact
    company_type = Column(String(50), default="customer")  # customer, partner, internal
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
    assigned_documents = relationship(
        "Document", secondary=document_company_assignments, back_populates="assigned_companies"
    )


class SystemSetting(Base):
    """System-wide settings stored as key/value entries"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)  # JSON-encoded value
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    updated_by_user = relationship("User")


class RbacPolicy(Base):
    """Role-based access control policy per role"""

    __tablename__ = "rbac_policies"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SQLEnum(UserRole), unique=True, index=True, nullable=False)
    permissions = Column(Text, nullable=False)  # JSON-encoded list of permissions
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    updated_by_user = relationship("User")


class Topic(Base):
    """Public topic metadata"""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Platform(Base):
    """Platform metadata used for release/document grouping."""

    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="platform_ref")


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id"), nullable=True, index=True
    )  # Multi-tenancy
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token_hash = Column(String(255), nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_login_user_agent = Column(String(512), nullable=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    locale = Column(String(10), default="en", nullable=False)
    notification_preferences = Column(JSON, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    documents = relationship("Document", back_populates="created_by_user")
    comments = relationship("Comment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    security_events = relationship("SecurityEvent", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")
    saved_searches = relationship(
        "SavedSearch", back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    watched_documents = relationship(
        "DocumentWatcher", back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        foreign_keys="[Feedback.user_id]",
        cascade="all, delete-orphan",
    )
    reading_progress = relationship(
        "ReadingProgress", back_populates="user", cascade="all, delete-orphan"
    )


class DocumentNumberSequence(Base):
    """Daily counter used for scalable document number allocation."""

    __tablename__ = "document_number_sequences"

    date_key = Column(String(8), primary_key=True)  # YYYYMMDD
    next_value = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Document(Base):
    """Document model"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )  # Multi-tenancy
    title = Column(String(500), nullable=False, index=True)
    document_number = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    version_label = Column(String(50), nullable=True)
    status = Column(
        SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT, nullable=False, index=True
    )
    visibility = Column(
        SQLEnum(DocumentVisibility), default=DocumentVisibility.INTERNAL, nullable=False, index=True
    )
    category = Column(String(100), nullable=True, index=True)
    topic = Column(String(150), nullable=True, index=True)
    platform = Column(String(100), nullable=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True, index=True)
    release_branch = Column(String(100), nullable=True, index=True)
    tags = Column(Text, nullable=True)  # Comma-separated tags
    due_date = Column(Date, nullable=True, index=True)
    thumbnail_url = Column(String(500), nullable=True)  # Cover image / thumbnail URL
    yjs_state = Column(LargeBinary, nullable=True)  # Yjs document state for real-time collaboration
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    row_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    created_by_user = relationship("User", back_populates="documents")
    platform_ref = relationship("Platform", back_populates="documents")
    parent = relationship("Document", remote_side=[id], backref="children")
    versions = relationship("Version", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship(
        "Attachment", back_populates="document", cascade="all, delete-orphan"
    )
    comments = relationship("Comment", back_populates="document", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="document")
    bookmarks = relationship("Bookmark", back_populates="document", cascade="all, delete-orphan")
    watchers = relationship(
        "DocumentWatcher", back_populates="document", cascade="all, delete-orphan"
    )
    feedbacks = relationship("Feedback", back_populates="document", cascade="all, delete-orphan")
    reading_progress = relationship(
        "ReadingProgress", back_populates="document", cascade="all, delete-orphan"
    )
    assigned_companies = relationship(
        "Tenant", secondary=document_company_assignments, back_populates="assigned_documents"
    )
    review_requests = relationship(
        "ReviewRequest", back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def etag(self) -> str:
        return build_resource_etag("document", int(self.id), int(self.row_version or 1))


class Version(Base):
    """Document version model"""

    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    semantic_version = Column(String(32), nullable=True, index=True)
    bump_type = Column(SQLEnum(VersionBumpType), default=VersionBumpType.PATCH, nullable=False)
    content = Column(Text, nullable=True)
    changes_summary = Column(Text, nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)  # Immutable after publishing
    published_at = Column(DateTime, nullable=True)  # When version was published
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    row_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Scheduled publish timestamp (null = not scheduled)
    scheduled_publish_at = Column(DateTime, nullable=True, index=True)
    scheduled_publish_audience_validated_at = Column(DateTime, nullable=True)

    # Audience state snapshot at publish time (carry-forward for auditing)
    audience_visibility_snapshot = Column(String(50), nullable=True)
    audience_company_ids_snapshot = Column(Text, nullable=True)  # JSON array of company IDs

    # AF-003: Attachment snapshot at publish time — JSON array of attachment IDs
    published_attachment_ids_snapshot = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="versions")
    created_by_user = relationship("User", foreign_keys=[created_by])
    published_by_user = relationship("User", foreign_keys=[published_by])
    sections = relationship("Section", back_populates="version", cascade="all, delete-orphan")

    @property
    def etag(self) -> str:
        return build_resource_etag("version", int(self.id), int(self.row_version or 1))


class Attachment(Base):
    """File attachment model"""

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)  # S3 key or local path
    storage_key = Column(String(500), nullable=True, index=True)
    sha256 = Column(String(64), nullable=True, index=True)
    preview_pdf_status = Column(String(20), nullable=True, index=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_storage_key = Column(String(500), nullable=True, index=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_mime_type = Column(String(100), nullable=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_size_bytes = Column(Integer, nullable=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_sha256 = Column(String(64), nullable=True, index=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_error = Column(Text, nullable=True)  # Legacy field - not used for new uploads (PDF support removed)
    preview_pdf_generated_at = Column(DateTime, nullable=True)  # Legacy field - not used for new uploads (PDF support removed)
    reader_html_status = Column(String(20), nullable=True, index=True)
    reader_html_content = Column(Text, nullable=True)
    reader_toc_json = Column(Text, nullable=True)
    reader_toc_source = Column(String(20), nullable=True)
    reader_html_error = Column(Text, nullable=True)
    reader_html_generated_at = Column(DateTime, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="attachments")
    uploaded_by_user = relationship("User")
    artifacts = relationship(
        "AttachmentArtifact", back_populates="attachment", cascade="all, delete-orphan"
    )
    conversion_jobs = relationship(
        "AttachmentConversionJob", back_populates="attachment", cascade="all, delete-orphan"
    )


class AttachmentArtifact(Base):
    """Derived artifact metadata and payload references per attachment."""

    __tablename__ = "attachment_artifacts"
    __table_args__ = (
        UniqueConstraint("attachment_id", "kind", name="uq_attachment_artifacts_attachment_kind"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id"), nullable=False, index=True)
    kind = Column(String(40), nullable=False, index=True)  # e.g. reader_html
    status = Column(String(20), nullable=False, default="pending", index=True)
    mime_type = Column(String(100), nullable=True)
    storage_key = Column(String(500), nullable=True, index=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    content_text = Column(Text, nullable=True)  # reader_html payload
    content_json = Column(Text, nullable=True)  # reader_toc_json payload
    source = Column(String(40), nullable=True)  # bookmarks / contents-fallback / etc.
    error = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    attachment = relationship("Attachment", back_populates="artifacts")


class AttachmentConversionJob(Base):
    """Durable async job queue row for conversion pipeline."""

    __tablename__ = "attachment_conversion_jobs"
    __table_args__ = (
        UniqueConstraint("attachment_id", "job_type", name="uq_attachment_conversion_job"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id"), nullable=False, index=True)
    job_type = Column(String(40), nullable=False, index=True)  # e.g. reader_html
    status = Column(String(20), nullable=False, default="pending", index=True)
    force = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    last_error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    attachment = relationship("Attachment", back_populates="conversion_jobs")


class DomainEventOutbox(Base):
    """Persisted domain events for reliable side-effect delivery."""

    __tablename__ = "domain_event_outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(120), nullable=False, index=True)
    event_key = Column(String(255), nullable=True, unique=True, index=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IdempotencyKeyRecord(Base):
    """Persisted request/response fingerprints for idempotent retries."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "method",
            "path",
            "user_scope",
            name="uq_idempotency_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    user_scope = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="processing", index=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_content_type = Column(String(120), nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Comment(Base):
    """Comment model with threading support and visibility controls"""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(
        Integer, ForeignKey("comments.id"), nullable=True, index=True
    )  # For threading
    content = Column(Text, nullable=False)
    is_private = Column(
        Boolean, default=False, nullable=False
    )  # Private = only admins/editors can see
    anchor_text = Column(Text, nullable=True)  # The text that was selected for inline comment
    anchor_id = Column(String(100), nullable=True)  # Reference to heading/section ID
    is_resolved = Column(Boolean, default=False, nullable=False)  # Mark comment thread as resolved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")


class AuditLog(Base):
    """Audit log model"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(SQLEnum(ActionType), nullable=False, index=True)
    audience_event_type = Column(SQLEnum(AudienceEventType), nullable=True, index=True)
    details = Column(Text, nullable=True)
    assignment_diff = Column(Text, nullable=True)  # JSON object: old/new + added/removed IDs
    signature_key_id = Column(String(32), nullable=True)
    signature = Column(String(128), nullable=True)  # HMAC-SHA256 hex digest
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    document = relationship("Document", back_populates="audit_logs")


class SecurityEvent(Base):
    """Security event log for user account anomalies and security actions."""

    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="security_events")


class UserSession(Base):
    """Persisted user session metadata for active-session management."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="user_sessions")


class Section(Base):
    """Document section model - for rich content within versions"""

    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False, default=0)  # Display order
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # Rich text content (HTML/Markdown)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    version = relationship("Version", back_populates="sections")


class Notification(Base):
    """User notification model"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)  # URL to related resource
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


class PasswordReset(Base):
    """Password reset token model"""

    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)  # Hashed token
    token_prefix = Column(String(16), nullable=True, index=True)  # First 8 chars for indexed lookup
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)  # Null if not used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="password_resets")


class SavedSearch(Base):
    """Saved search model for users"""

    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    query = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="saved_searches")


class Bookmark(Base):
    """User bookmarks for documents"""

    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bookmarks")
    document = relationship("Document", back_populates="bookmarks")


class DocumentWatcher(Base):
    """Users following document updates."""

    __tablename__ = "document_watchers"
    __table_args__ = (
        UniqueConstraint("user_id", "document_id", name="uq_document_watchers_user_document"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="watched_documents")
    document = relationship("Document", back_populates="watchers")


class Feedback(Base):
    """Document feedback from customers"""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = Column(SQLEnum(FeedbackType), default=FeedbackType.OTHER, nullable=False)
    status = Column(
        SQLEnum(FeedbackStatus), default=FeedbackStatus.PENDING, nullable=False, index=True
    )
    content = Column(Text, nullable=False)  # Feedback content
    response = Column(Text, nullable=True)  # Admin response
    responded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    # Legacy field - keep for backwards compatibility
    is_helpful = Column(Boolean, nullable=True)  # True = helpful, False = not helpful
    comment = Column(Text, nullable=True)  # Optional feedback comment (legacy)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="feedbacks", foreign_keys=[user_id])
    document = relationship("Document", back_populates="feedbacks")
    responder = relationship("User", foreign_keys=[responded_by])


class ReadingProgress(Base):
    """Track user reading progress on documents"""

    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    progress_percent = Column(Integer, default=0, nullable=False)  # 0-100
    last_read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)  # When progress reached 100%
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reading_progress")
    document = relationship("Document", back_populates="reading_progress")


class ReviewRequest(Base):
    """Review request for document approval workflow"""

    __tablename__ = "review_requests"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(
        Integer, ForeignKey("versions.id"), nullable=True
    )  # Specific version if applicable
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    message = Column(Text, nullable=True)  # Submission message
    review_comments = Column(Text, nullable=True)  # Reviewer's comments
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_reminded_at = Column(DateTime, nullable=True)
    manager_escalated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Audience state snapshot at submission time
    audience_visibility_snapshot = Column(String(50), nullable=True)
    audience_company_ids_snapshot = Column(Text, nullable=True)  # JSON array of company IDs

    # Relationships
    document = relationship("Document", back_populates="review_requests")
    version = relationship("Version")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class Invitation(Base):
    """User invitation for onboarding new users via email"""

    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False, index=True
    )
    message = Column(Text, nullable=True)  # Optional message to include in invitation
    expires_at = Column(DateTime, nullable=False)  # Invitation expiration
    accepted_at = Column(DateTime, nullable=True)
    created_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User created from invitation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    inviter = relationship("User", foreign_keys=[invited_by])
    created_user = relationship("User", foreign_keys=[created_user_id])


class CollaborationSession(Base):
    """Tracks collaboration sessions for activity feed and analytics"""

    __tablename__ = "collaboration_sessions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)  # Unique session identifier
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    edits_count = Column(Integer, default=0, nullable=False)  # Number of edits made
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document")
    user = relationship("User")


class CollaborationActivity(Base):
    """Individual collaboration activities for the activity feed"""

    __tablename__ = "collaboration_activities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    activity_type = Column(SQLEnum(CollaborationActivityType), nullable=False, index=True)
    details = Column(Text, nullable=True)  # JSON string with activity details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    document = relationship("Document")
    user = relationship("User")


class CollaborationSnapshot(Base):
    """Point-in-time snapshot of collaborative document state (NOT a Version/release)"""

    __tablename__ = "collaboration_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot metadata
    snapshot_type = Column(SQLEnum(SnapshotType), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Optional user-provided name
    description = Column(Text, nullable=True)  # Optional description

    # State data
    yjs_state = Column(LargeBinary, nullable=False)  # The Yjs binary state
    html_content = Column(Text, nullable=True)  # Rendered HTML for preview
    state_size = Column(Integer, nullable=False)  # Size in bytes

    # Context
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for auto-saves
    session_id = Column(String(100), nullable=True, index=True)  # Link to CollaborationSession

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Retention
    is_pinned = Column(Boolean, default=False, nullable=False)  # Pinned = won't auto-delete
    expires_at = Column(DateTime, nullable=True)  # Auto-cleanup after this date

    # Relationships
    document = relationship("Document")
    created_by_user = relationship("User")


# ========== Chat & Support Models (Wave X.1) ==========


class ChatType(str, enum.Enum):
    """Chat types"""

    DIRECT = "direct"
    GROUP = "group"


class ChatParticipantRole(str, enum.Enum):
    """Participant roles in a chat"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ChatMessageType(str, enum.Enum):
    """Chat message types"""

    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"


class SupportTicketStatus(str, enum.Enum):
    """Support ticket statuses"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketPriority(str, enum.Enum):
    """Support ticket priorities"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Chat(Base):
    """Internal chat — direct messages or group conversations"""

    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(ChatType), nullable=False)
    name = Column(String(255), nullable=True)  # Nullable for direct chats
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)  # AH-008: document-scoped chats
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)  # For sorting by activity
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    tenant = relationship("Tenant")
    document = relationship("Document", foreign_keys=[document_id])
    participants = relationship("ChatParticipant", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatParticipant(Base):
    """Participant in a chat"""

    __tablename__ = "chat_participants"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_participant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SQLEnum(ChatParticipantRole), default=ChatParticipantRole.MEMBER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_read_at = Column(DateTime, nullable=True)
    is_muted = Column(Boolean, default=False, nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="participants")
    user = relationship("User")


class ChatMessage(Base):
    """Message in a chat"""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(ChatMessageType), default=ChatMessageType.TEXT, nullable=False)
    context_json = Column(Text, nullable=True)  # AH-009: context card metadata (document title, section, anchor, comment type)
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_mime_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Composite index for efficient message ordering
    __table_args__ = (
        Index("ix_chat_messages_chat_created", "chat_id", "created_at"),
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")


class SupportTicket(Base):
    """Customer support ticket — created from feedback or directly"""

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    status = Column(
        SQLEnum(SupportTicketStatus), default=SupportTicketStatus.OPEN, nullable=False, index=True
    )
    priority = Column(
        SQLEnum(SupportTicketPriority), default=SupportTicketPriority.NORMAL, nullable=False, index=True
    )
    category = Column(String(100), nullable=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id])
    tenant = relationship("Tenant")
    feedback = relationship("Feedback")
    messages = relationship("SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    assignments = relationship("SupportTicketAssignment", back_populates="ticket", cascade="all, delete-orphan")


class SupportTicketMessage(Base):
    """Message in a support ticket conversation"""

    __tablename__ = "support_ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)  # "customer" or "agent"
    content = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False, nullable=False)  # Only visible to agents
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Composite index for efficient message ordering
    __table_args__ = (
        Index("ix_support_messages_ticket_created", "ticket_id", "created_at"),
    )

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User")


class SupportTicketAssignment(Base):
    """Agent assignment to a support ticket"""

    __tablename__ = "support_ticket_assignments"
    __table_args__ = (
        UniqueConstraint("ticket_id", "agent_id", name="uq_ticket_assignment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary handler

    # Relationships
    ticket = relationship("SupportTicket", back_populates="assignments")
    agent = relationship("User")


class CannedResponse(Base):
    """Reusable canned response template for support agents (X1-103)"""

    __tablename__ = "canned_responses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User")
    tenant = relationship("Tenant")


class SearchAnalytics(Base):
    """Search analytics — tracks queries, results, and clicks (Y2-005)"""

    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    results_count = Column(Integer, nullable=False, default=0)
    clicked_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant")
    clicked_document = relationship("Document")


class BrokenLinkReport(Base):
    """Stores broken internal link scan results."""

    __tablename__ = "broken_link_reports"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("versions.id", ondelete="CASCADE"), nullable=False)
    broken_url = Column(String(1000), nullable=False)
    link_text = Column(String(500), nullable=True)
    reason = Column(String(200), nullable=False)  # e.g. "target_not_found", "target_archived"
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document")
    version = relationship("Version")


class ChangelogEntry(Base):
    """Release notes / changelog entries created by admins."""

    __tablename__ = "changelog_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    version_tag = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)  # e.g. "feature", "bugfix", "improvement"
    published = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    author = relationship("User")


class Announcement(Base):
    """In-app announcement banners set by admins."""

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String(500), nullable=False)
    type = Column(String(20), nullable=False, default="info")  # info, warning, success
    active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    author = relationship("User")


class NpsSurvey(Base):
    """Net Promoter Score survey responses."""

    __tablename__ = "nps_surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    score = Column(Integer, nullable=False)  # 0-10
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    tenant = relationship("Tenant")


# ========== Admin Operations Models (Wave Z) ==========


class AdminActionStatus(str, enum.Enum):
    """Status for queued admin actions requiring approval"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class AdminActionType(str, enum.Enum):
    """Types of critical admin actions that require approval"""

    TENANT_DELETION = "tenant_deletion"
    MASS_USER_DEACTIVATION = "mass_user_deactivation"
    TENANT_SUSPENSION = "tenant_suspension"
    DATA_EXPORT = "data_export"
    QUOTA_OVERRIDE = "quota_override"
    SYSTEM_SETTING_CHANGE = "system_setting_change"


class DomainVerificationStatus(str, enum.Enum):
    """Status for domain ownership verification"""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class ImpersonationSession(Base):
    """Tracks when a system admin is impersonating a tenant (Z-001)"""

    __tablename__ = "impersonation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    target_tenant = relationship("Tenant")


class AdminAction(Base):
    """Queued admin actions requiring second sysadmin approval (Z-002)"""

    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(SQLEnum(AdminActionType), nullable=False, index=True)
    status = Column(SQLEnum(AdminActionStatus), default=AdminActionStatus.PENDING, nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON with action details
    reason = Column(Text, nullable=True)  # Why this action is being requested
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    # Relationships
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    target_tenant = relationship("Tenant")


class TenantQuota(Base):
    """Configurable quotas per tenant (Z-012)"""

    __tablename__ = "tenant_quotas"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_quota"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    max_users = Column(Integer, nullable=True)  # null = unlimited
    max_documents = Column(Integer, nullable=True)
    max_storage_mb = Column(Integer, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", backref="quota")
    updater = relationship("User")


class FeatureFlag(Base):
    """Per-tenant feature flags (Z-005) with targeting (AB-001)"""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_key", name="uq_tenant_feature"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    feature_key = Column(String(100), nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    rollout_percentage = Column(Integer, nullable=True, default=100)  # AB-001
    target_tenant_ids = Column(Text, nullable=True)  # AB-001: JSON list of targeted tenant IDs
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    updater = relationship("User")


class DomainVerification(Base):
    """DNS domain verification for tenant ownership (Z-010)"""

    __tablename__ = "domain_verifications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    verification_token = Column(String(128), nullable=False)  # TXT record value
    status = Column(
        SQLEnum(DomainVerificationStatus),
        default=DomainVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Token validity window

    # Relationships
    tenant = relationship("Tenant")


class MaintenanceWindow(Base):
    """Scheduled maintenance windows with notification (Z-018)"""

    __tablename__ = "maintenance_windows"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False)
    is_read_only = Column(Boolean, default=True, nullable=False)  # Read-only mode during window
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    notification_sent = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User")


# ---------------------------------------------------------------------------
# Wave AA — GDPR Data Requests
# ---------------------------------------------------------------------------


class DataRequestType(str, enum.Enum):
    """Types of GDPR data requests."""

    EXPORT = "export"
    DELETION = "deletion"


class DataRequestStatus(str, enum.Enum):
    """Processing status for GDPR data requests."""

    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataRequest(Base):
    """GDPR data export/deletion request (AA-001, AA-002)."""

    __tablename__ = "data_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_type = Column(SQLEnum(DataRequestType), nullable=False, index=True)
    status = Column(
        SQLEnum(DataRequestStatus),
        default=DataRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    admin_comment = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    download_token = Column(String(128), nullable=True, unique=True)
    download_expires_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ---------------------------------------------------------------------------
# AI Assistant (conversations & messages)
# ---------------------------------------------------------------------------

class AssistantConversation(Base):
    """A conversation between a user and the AI assistant."""

    __tablename__ = "assistant_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)  # null for SYSTEM_ADMIN
    title = Column(String(255), default="New Chat", nullable=False)
    summary = Column(Text, nullable=True)  # Auto-generated summary for long conversations
    context_document_ids = Column(Text, nullable=True)  # JSON list of document IDs for context injection
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant")
    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )

    __table_args__ = (
        Index("ix_assistant_conv_user_created", "user_id", "created_at"),
    )


class AssistantMessage(Base):
    """A single message within an assistant conversation."""

    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)  # user, assistant, tool, system
    content = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)   # JSON-serialised list of tool-call dicts
    tool_call_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("AssistantConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_assistant_msg_conv_created", "conversation_id", "created_at"),
    )


class AssistantUploadedFile(Base):
    """A file uploaded by a user in the assistant chat."""

    __tablename__ = "assistant_uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(
        Integer,
        ForeignKey("assistant_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename = Column(String(255), nullable=False)       # UUID-based storage name
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)           # bytes
    storage_path = Column(String(500), nullable=False)    # relative path
    extracted_text = Column(Text, nullable=True)           # extracted content
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    conversation = relationship("AssistantConversation")

    __table_args__ = (
        Index("ix_assistant_file_user", "user_id"),
    )


# ---------------------------------------------------------------------------
# Wave AB — Experimentation and Growth Systems
# ---------------------------------------------------------------------------


class ExperimentStatus(str, enum.Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class Experiment(Base):
    """A/B experiment definition (AB-002)."""

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    feature_flag_key = Column(String(100), nullable=True, index=True)
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False, index=True)
    variants = Column(Text, nullable=False, default='["control","treatment"]')  # JSON list
    traffic_percentage = Column(Integer, default=100, nullable=False)  # % of users enrolled
    primary_metric = Column(String(100), nullable=True)
    guardrail_metrics = Column(Text, nullable=True)  # JSON list of metric names
    guardrail_threshold = Column(Integer, default=10, nullable=False)  # max % degradation before halt
    winner_variant = Column(String(100), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    creator = relationship("User")
    assignments = relationship("ExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentAssignment(Base):
    """Deterministic user→variant assignment for an experiment (AB-002)."""

    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    variant = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    experiment = relationship("Experiment", back_populates="assignments")
    user = relationship("User")


class ExperimentMetricSnapshot(Base):
    """Point-in-time metric readings per variant (AB-003)."""

    __tablename__ = "experiment_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    variant = Column(String(100), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(String(50), nullable=False)  # stored as string for flexibility
    sample_size = Column(Integer, default=0, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OnboardingEvent(Base):
    """Funnel event for onboarding analytics (AB-005)."""

    __tablename__ = "onboarding_events"
    __table_args__ = (
        Index("ix_onboarding_user_step", "user_id", "step"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    step = Column(String(50), nullable=False)  # invitation_sent, accepted, first_login, first_view, first_action
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    tenant = relationship("Tenant")


class ActivationMilestone(Base):
    """Per-user milestone tracking (AB-006)."""

    __tablename__ = "activation_milestones"
    __table_args__ = (
        UniqueConstraint("user_id", "milestone", name="uq_user_milestone"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    milestone = Column(String(50), nullable=False)  # viewed_5_docs, created_1_doc, completed_profile, etc.
    achieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    tenant = relationship("Tenant")


class WebhookRegistration(Base):
    """Registered webhook URLs for domain events (AB-009)."""

    __tablename__ = "webhook_registrations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)  # HMAC signing secret
    event_types = Column(Text, nullable=False)  # JSON list of subscribed event types
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    creator = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Delivery log for a webhook invocation (AB-011)."""

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhook_registrations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(120), nullable=False)
    payload_json = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=1, nullable=False)
    delivered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    webhook = relationship("WebhookRegistration", back_populates="deliveries")


class ApiKey(Base):
    """Developer API keys for programmatic access (AB-010)."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_prefix = Column(String(8), nullable=False)  # first 8 chars for identification
    key_hash = Column(String(255), nullable=False, unique=True)  # SHA-256 hash of full key
    scopes = Column(Text, nullable=True)  # JSON list of allowed scopes
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    user = relationship("User")


@event.listens_for(Document, "before_update", propagate=True)
def _bump_document_row_version(_mapper, _connection, target: Document) -> None:
    target.row_version = int(target.row_version or 0) + 1


@event.listens_for(Version, "before_update", propagate=True)
def _bump_version_row_version(_mapper, _connection, target: Version) -> None:
    target.row_version = int(target.row_version or 0) + 1


# Export all models
__all__ = [
    # Models
    "Tenant",
    "SystemSetting",
    "RbacPolicy",
    "Topic",
    "User",
    "Document",
    "Version",
    "Section",
    "Attachment",
    "AttachmentArtifact",
    "AttachmentConversionJob",
    "DomainEventOutbox",
    "IdempotencyKeyRecord",
    "Comment",
    "AuditLog",
    "SecurityEvent",
    "UserSession",
    "Notification",
    "PasswordReset",
    "SavedSearch",
    "Bookmark",
    "Feedback",
    "ReadingProgress",
    "ReviewRequest",
    "Invitation",
    "CollaborationSession",
    "CollaborationActivity",
    "CollaborationSnapshot",
    # Chat & Support (Wave X.1)
    "Chat",
    "ChatParticipant",
    "ChatMessage",
    "SupportTicket",
    "SupportTicketMessage",
    "SupportTicketAssignment",
    "CannedResponse",
    "SearchAnalytics",
    "BrokenLinkReport",
    "ChangelogEntry",
    "Announcement",
    "NpsSurvey",
    # Admin Operations (Wave Z)
    "ImpersonationSession",
    "AdminAction",
    "TenantQuota",
    "FeatureFlag",
    "DomainVerification",
    "MaintenanceWindow",
    # GDPR Data Requests (Wave AA)
    "DataRequest",
    "DataRequestType",
    "DataRequestStatus",
    # Experimentation & Growth (Wave AB)
    "Experiment",
    "ExperimentAssignment",
    "ExperimentMetricSnapshot",
    "ExperimentStatus",
    "OnboardingEvent",
    "ActivationMilestone",
    "WebhookRegistration",
    "WebhookDelivery",
    "ApiKey",
    # Enums
    "UserRole",
    "DocumentStatus",
    "DocumentVisibility",
    "ReviewStatus",
    "VersionBumpType",
    "FeedbackType",
    "FeedbackStatus",
    "ActionType",
    "AudienceEventType",
    "NotificationType",
    "InvitationStatus",
    "CollaborationActivityType",
    "SnapshotType",
    "ChatType",
    "ChatParticipantRole",
    "ChatMessageType",
    "SupportTicketStatus",
    "SupportTicketPriority",
    "AdminActionStatus",
    "AdminActionType",
    "DomainVerificationStatus",
    # AI Assistant
    "AssistantConversation",
    "AssistantMessage",
    "AssistantUploadedFile",
    # Junction tables
    "document_company_assignments",
]
