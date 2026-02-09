"""Database Models"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, LargeBinary
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db import Base


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
    """Document statuses"""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"  # Waiting for approval
    ACTIVE = "active"
    PUBLISHED = "active"  # Alias for ACTIVE
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
    FEEDBACK_RECEIVED = "feedback_received"
    FEEDBACK_RESPONDED = "feedback_responded"
    INVITATION_SENT = "invitation_sent"
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

    AUTO_SAVE = "auto_save"      # Automatic periodic saves
    MANUAL_SAVE = "manual_save"  # User-triggered save action
    SESSION_END = "session_end"  # When last user leaves
    PRE_PUBLISH = "pre_publish"  # Before creating a Version


# Junction table for document-company assignments
document_company_assignments = Table(
    "document_company_assignments",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id"), primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants.id"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
    Column("assigned_by", Integer, ForeignKey("users.id")),
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    documents = relationship("Document", back_populates="created_by_user")
    comments = relationship("Comment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")
    saved_searches = relationship(
        "SavedSearch", back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        foreign_keys="[Feedback.user_id]",
        cascade="all, delete-orphan",
    )
    reading_progress = relationship(
        "ReadingProgress", back_populates="user", cascade="all, delete-orphan"
    )


class Document(Base):
    """Document model"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id"), nullable=True, index=True
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
    release_branch = Column(String(100), nullable=True, index=True)
    tags = Column(Text, nullable=True)  # Comma-separated tags
    yjs_state = Column(LargeBinary, nullable=True)  # Yjs document state for real-time collaboration
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    created_by_user = relationship("User", back_populates="documents")
    parent = relationship("Document", remote_side=[id], backref="children")
    versions = relationship("Version", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship(
        "Attachment", back_populates="document", cascade="all, delete-orphan"
    )
    comments = relationship("Comment", back_populates="document", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="document")
    bookmarks = relationship("Bookmark", back_populates="document", cascade="all, delete-orphan")
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


class Version(Base):
    """Document version model"""

    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=True)
    changes_summary = Column(Text, nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)  # Immutable after publishing
    published_at = Column(DateTime, nullable=True)  # When version was published
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="versions")
    created_by_user = relationship("User")
    sections = relationship("Section", back_populates="version", cascade="all, delete-orphan")


class Attachment(Base):
    """File attachment model"""

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)  # S3 key or local path
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="attachments")
    uploaded_by_user = relationship("User")


class Comment(Base):
    """Comment model with threading support and visibility controls"""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    action = Column(SQLEnum(ActionType), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    document = relationship("Document", back_populates="audit_logs")


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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bookmarks")
    document = relationship("Document", back_populates="bookmarks")


class Feedback(Base):
    """Document feedback from customers"""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
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
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

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
    "Comment",
    "AuditLog",
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
    # Enums
    "UserRole",
    "DocumentStatus",
    "DocumentVisibility",
    "ReviewStatus",
    "FeedbackType",
    "FeedbackStatus",
    "ActionType",
    "NotificationType",
    "InvitationStatus",
    "CollaborationActivityType",
    "SnapshotType",
    # Junction tables
    "document_company_assignments",
]
