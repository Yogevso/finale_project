"""Core tenant, user, document, and content models."""

from app.models._shared import (
    JSON,
    Base,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SQLEnum,
    String,
    Table,
    Text,
    UniqueConstraint,
    build_resource_etag,
    datetime,
    event,
    relationship,
)
from app.models.enums import DocumentStatus, DocumentVisibility, UserRole, VersionBumpType

document_company_assignments = Table(
    "document_company_assignments",
    Base.metadata,
    Column(
        "document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("tenant_id", Integer, ForeignKey("tenants.id"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
    Column("assigned_by", Integer, ForeignKey("users.id")),
    Index(
        "ix_document_company_assignments_document_id_tenant_id",
        "document_id",
        "tenant_id",
    ),
)


class Tenant(Base):
    """Tenant model - represents an organization/company."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(Text, nullable=True)
    company_logo = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    company_type = Column(String(50), default="customer")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
    assigned_documents = relationship(
        "Document",
        secondary=document_company_assignments,
        back_populates="assigned_companies",
    )


class SystemSetting(Base):
    """System-wide settings stored as key/value entries."""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    updated_by_user = relationship("User")


class RbacPolicy(Base):
    """Role-based access control policy per role."""

    __tablename__ = "rbac_policies"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SQLEnum(UserRole), unique=True, index=True, nullable=False)
    permissions = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    updated_by_user = relationship("User")


class Topic(Base):
    """Public topic metadata."""

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

    documents = relationship("Document", back_populates="platform_ref")


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
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
    onboarding_state = Column(JSON, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="users")
    documents = relationship(
        "Document",
        back_populates="created_by_user",
        foreign_keys="[Document.created_by]",
    )
    deleted_documents = relationship(
        "Document",
        foreign_keys="[Document.deleted_by]",
        back_populates="deleted_by_user",
    )
    comments = relationship("Comment", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")
    saved_searches = relationship(
        "SavedSearch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    watched_documents = relationship(
        "DocumentWatcher",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        foreign_keys="[Feedback.user_id]",
        cascade="all, delete-orphan",
    )
    reading_progress = relationship(
        "ReadingProgress",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class DocumentNumberSequence(Base):
    """Daily counter used for scalable document number allocation."""

    __tablename__ = "document_number_sequences"

    date_key = Column(String(8), primary_key=True)
    next_value = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Document(Base):
    """Document model."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    document_number = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    version_label = Column(String(50), nullable=True)
    status = Column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    visibility = Column(
        SQLEnum(DocumentVisibility),
        default=DocumentVisibility.INTERNAL,
        nullable=False,
        index=True,
    )
    category = Column(String(100), nullable=True, index=True)
    topic = Column(String(150), nullable=True, index=True)
    platform = Column(String(100), nullable=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True, index=True)
    release_branch = Column(String(100), nullable=True, index=True)
    tags = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    thumbnail_url = Column(String(500), nullable=True)
    yjs_state = Column(LargeBinary, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    purge_at = Column(DateTime, nullable=True, index=True)
    parent_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    row_version = Column(Integer, nullable=False, default=1)
    audience_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="documents")
    created_by_user = relationship("User", back_populates="documents", foreign_keys=[created_by])
    deleted_by_user = relationship(
        "User", foreign_keys=[deleted_by], back_populates="deleted_documents"
    )
    platform_ref = relationship("Platform", back_populates="documents")
    parent = relationship("Document", remote_side=[id], backref="children")
    versions = relationship("Version", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship(
        "Attachment", back_populates="document", cascade="all, delete-orphan"
    )
    comments = relationship("Comment", back_populates="document", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="document", cascade="all, delete-orphan")
    watchers = relationship(
        "DocumentWatcher", back_populates="document", cascade="all, delete-orphan"
    )
    feedbacks = relationship("Feedback", back_populates="document", cascade="all, delete-orphan")
    reading_progress = relationship(
        "ReadingProgress",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    assigned_companies = relationship(
        "Tenant",
        secondary=document_company_assignments,
        back_populates="assigned_documents",
    )
    review_requests = relationship(
        "ReviewRequest",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @property
    def platform_name(self) -> str | None:
        """Resolve platform name through the FK relationship first."""
        if self.platform_ref is not None:
            return self.platform_ref.name
        return self.platform

    @property
    def etag(self) -> str:
        return build_resource_etag("document", int(self.id), int(self.row_version or 1))


class Version(Base):
    """Document version model."""

    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number = Column(Integer, nullable=False)
    semantic_version = Column(String(32), nullable=True, index=True)
    bump_type = Column(SQLEnum(VersionBumpType), default=VersionBumpType.PATCH, nullable=False)
    content = Column(Text, nullable=True)
    # Table of contents for this version's content, as JSON. Held beside the
    # HTML rather than derived from it, so entries keep the page numbers and
    # stable heading ids the source document declared.
    toc_json = Column(Text, nullable=True)
    changes_summary = Column(Text, nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, nullable=True)
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    row_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_publish_at = Column(DateTime, nullable=True, index=True)
    scheduled_publish_audience_validated_at = Column(DateTime, nullable=True)
    audience_visibility_snapshot = Column(String(50), nullable=True)
    audience_company_ids_snapshot = Column(Text, nullable=True)
    published_attachment_ids_snapshot = Column(Text, nullable=True)

    document = relationship("Document", back_populates="versions")
    created_by_user = relationship("User", foreign_keys=[created_by])
    published_by_user = relationship("User", foreign_keys=[published_by])
    sections = relationship("Section", back_populates="version", cascade="all, delete-orphan")

    @property
    def etag(self) -> str:
        return build_resource_etag("version", int(self.id), int(self.row_version or 1))

    @property
    def toc_items(self) -> str | None:
        """Expose the stored contents under the name the response uses."""
        return self.toc_json


class Attachment(Base):
    """File attachment model."""

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    storage_key = Column(String(500), nullable=True, index=True)
    sha256 = Column(String(64), nullable=True, index=True)
    preview_pdf_status = Column(String(20), nullable=True, index=True)
    preview_pdf_storage_key = Column(String(500), nullable=True, index=True)
    preview_pdf_mime_type = Column(String(100), nullable=True)
    preview_pdf_size_bytes = Column(Integer, nullable=True)
    preview_pdf_sha256 = Column(String(64), nullable=True, index=True)
    preview_pdf_error = Column(Text, nullable=True)
    preview_pdf_generated_at = Column(DateTime, nullable=True)
    reader_html_status = Column(String(20), nullable=True, index=True)
    reader_html_content = Column(Text, nullable=True)
    reader_toc_json = Column(Text, nullable=True)
    reader_toc_source = Column(String(20), nullable=True)
    reader_html_error = Column(Text, nullable=True)
    reader_html_generated_at = Column(DateTime, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="attachments")
    uploaded_by_user = relationship("User")
    artifacts = relationship(
        "AttachmentArtifact", back_populates="attachment", cascade="all, delete-orphan"
    )
    conversion_jobs = relationship(
        "AttachmentConversionJob",
        back_populates="attachment",
        cascade="all, delete-orphan",
    )


class AttachmentArtifact(Base):
    """Derived artifact metadata and payload references per attachment."""

    __tablename__ = "attachment_artifacts"
    __table_args__ = (
        UniqueConstraint("attachment_id", "kind", name="uq_attachment_artifacts_attachment_kind"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id"), nullable=False, index=True)
    kind = Column(String(40), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    mime_type = Column(String(100), nullable=True)
    storage_key = Column(String(500), nullable=True, index=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    content_text = Column(Text, nullable=True)
    content_json = Column(Text, nullable=True)
    source = Column(String(40), nullable=True)
    error = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    attachment = relationship("Attachment", back_populates="artifacts")


class AttachmentConversionJob(Base):
    """Durable async job queue row for conversion pipeline."""

    __tablename__ = "attachment_conversion_jobs"
    __table_args__ = (
        UniqueConstraint("attachment_id", "job_type", name="uq_attachment_conversion_job"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id"), nullable=False, index=True)
    job_type = Column(String(40), nullable=False, index=True)
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

    attachment = relationship("Attachment", back_populates="conversion_jobs")


class Section(Base):
    """Document section model - for rich content within versions."""

    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False, default=0)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    version = relationship("Version", back_populates="sections")


class BrokenLinkReport(Base):
    """Stores broken internal link scan results."""

    __tablename__ = "broken_link_reports"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(Integer, ForeignKey("versions.id", ondelete="CASCADE"), nullable=False)
    broken_url = Column(String(1000), nullable=False)
    link_text = Column(String(500), nullable=True)
    reason = Column(String(200), nullable=False)
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
    category = Column(String(50), nullable=True)
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
    type = Column(String(20), nullable=False, default="info")
    active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    author = relationship("User")


@event.listens_for(Document, "before_update", propagate=True)
def _bump_document_row_version(_mapper, _connection, target: Document) -> None:
    target.row_version = int(target.row_version or 0) + 1


@event.listens_for(Version, "before_update", propagate=True)
def _bump_version_row_version(_mapper, _connection, target: Version) -> None:
    target.row_version = int(target.row_version or 0) + 1
