"""Database Models"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db import Base


# Enums
class UserRole(str, enum.Enum):
    """User roles"""
    SUPER_ADMIN = "super_admin"  # Can manage all tenants
    ADMIN = "admin"              # Tenant admin
    EDITOR = "editor"
    VIEWER = "viewer"


class DocumentStatus(str, enum.Enum):
    """Document statuses"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ActionType(str, enum.Enum):
    """Audit log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    DOWNLOAD = "download"
    PUBLISH = "publish"


class NotificationType(str, enum.Enum):
    """Notification types"""
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_PUBLISHED = "document_published"
    COMMENT_ADDED = "comment_added"
    COMMENT_REPLY = "comment_reply"
    VERSION_PUBLISHED = "version_published"
    SYSTEM = "system"


# Models
class Tenant(Base):
    """Tenant model - represents an organization"""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(Text, nullable=True)  # JSON settings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # Multi-tenancy
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
    saved_searches = relationship("SavedSearch", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    reading_progress = relationship("ReadingProgress", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # Multi-tenancy
    title = Column(String(500), nullable=False, index=True)
    document_number = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT, nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    tags = Column(Text, nullable=True)  # Comma-separated tags
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    created_by_user = relationship("User", back_populates="documents")
    versions = relationship("Version", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="document", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="document", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="document")
    bookmarks = relationship("Bookmark", back_populates="document", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="document", cascade="all, delete-orphan")
    reading_progress = relationship("ReadingProgress", back_populates="document", cascade="all, delete-orphan")


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
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)  # For threading
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)  # Private = only admins/editors can see
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
    """Document feedback/rating model"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    is_helpful = Column(Boolean, nullable=False)  # True = helpful, False = not helpful
    comment = Column(Text, nullable=True)  # Optional feedback comment
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    document = relationship("Document", back_populates="feedbacks")


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


# Export all models
__all__ = [
    "Tenant",
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
    "UserRole",
    "DocumentStatus",
    "ActionType",
    "NotificationType",
]
