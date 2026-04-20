"""Comments, reviews, feedback, sessions, and user engagement models."""

from app.models._shared import (
    Base,
    Boolean,
    ChatBase,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SQLEnum,
    String,
    Text,
    UniqueConstraint,
    datetime,
    relationship,
)
from app.models.enums import (
    FeedbackStatus,
    FeedbackType,
    InvitationEmailDeliveryStatus,
    InvitationStatus,
    NotificationType,
    ReviewStatus,
    UserRole,
)


class Comment(Base):
    """Comment model with threading support and visibility controls."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    anchor_text = Column(Text, nullable=True)
    anchor_id = Column(String(100), nullable=True)
    review_id = Column(Integer, ForeignKey("review_requests.id"), nullable=True, index=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")
    review = relationship("ReviewRequest", back_populates="comments")


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

    user = relationship("User", back_populates="user_sessions")


class Notification(ChatBase):
    """User notification model (Chat DB)."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PasswordReset(Base):
    """Password reset token model."""

    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    token_prefix = Column(String(16), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="password_resets")


class SavedSearch(Base):
    """Saved search model for users."""

    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    query = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="saved_searches")


class Bookmark(Base):
    """User bookmarks for documents."""

    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="watched_documents")
    document = relationship("Document", back_populates="watchers")


class Feedback(Base):
    """Document feedback from customers."""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_type = Column(SQLEnum(FeedbackType), default=FeedbackType.OTHER, nullable=False)
    status = Column(
        SQLEnum(FeedbackStatus), default=FeedbackStatus.PENDING, nullable=False, index=True
    )
    content = Column(Text, nullable=False)
    anchor_text = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    is_helpful = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="feedbacks", foreign_keys=[user_id])
    document = relationship("Document", back_populates="feedbacks")
    responder = relationship("User", foreign_keys=[responded_by])


class ReadingProgress(Base):
    """Track user reading progress on documents."""

    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress_percent = Column(Integer, default=0, nullable=False)
    last_read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reading_progress")
    document = relationship("Document", back_populates="reading_progress")


class ReviewRequest(Base):
    """Review request for document approval workflow."""

    __tablename__ = "review_requests"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    message = Column(Text, nullable=True)
    review_comments = Column(Text, nullable=True)
    review_feedback_json = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_reminded_at = Column(DateTime, nullable=True)
    manager_escalated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    audience_visibility_snapshot = Column(String(50), nullable=True)
    audience_company_ids_snapshot = Column(Text, nullable=True)
    audience_version_snapshot = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="review_requests")
    version = relationship("Version")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    comments = relationship("Comment", back_populates="review")
    reviewer_assignments = relationship(
        "ReviewRequestReviewer",
        back_populates="review",
        cascade="all, delete-orphan",
    )

    @property
    def requested_reviewer_ids(self) -> list[int]:
        return [assignment.reviewer_id for assignment in self.reviewer_assignments]

    @property
    def requested_reviewers(self) -> list["User"]:
        return [
            assignment.reviewer
            for assignment in self.reviewer_assignments
            if getattr(assignment, "reviewer", None) is not None
        ]

    @property
    def review_feedback(self) -> dict | None:
        from app.services.review_feedback import deserialize_review_feedback

        return deserialize_review_feedback(
            self.review_feedback_json,
            fallback_comments=self.review_comments,
        )


class ReviewOwnershipRule(Base):
    """Ownership routing rules for review assignment."""

    __tablename__ = "review_ownership_rules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    platform = Column(String(100), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    priority = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    company = relationship("Tenant", foreign_keys=[company_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    review_assignments = relationship(
        "ReviewRequestReviewer",
        back_populates="ownership_rule",
    )


class ReviewRequestReviewer(Base):
    """Reviewer assignments attached to a review request."""

    __tablename__ = "review_request_reviewers"
    __table_args__ = (
        UniqueConstraint(
            "review_id",
            "reviewer_id",
            name="uq_review_request_reviewers_review_reviewer",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(
        Integer,
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(20), nullable=False, default="manual")
    rule_id = Column(Integer, ForeignKey("review_ownership_rules.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    review = relationship("ReviewRequest", back_populates="reviewer_assignments")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    ownership_rule = relationship("ReviewOwnershipRule", back_populates="review_assignments")


class Invitation(Base):
    """User invitation for onboarding new users via email."""

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
    message = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    email_delivery_status = Column(
        SQLEnum(InvitationEmailDeliveryStatus),
        default=InvitationEmailDeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    email_delivery_attempt_count = Column(Integer, default=0, nullable=False)
    email_last_attempted_at = Column(DateTime, nullable=True)
    email_last_sent_at = Column(DateTime, nullable=True)
    email_last_error = Column(Text, nullable=True)
    email_last_subject = Column(String(255), nullable=True)
    email_last_sender_email = Column(String(255), nullable=True)
    email_last_sender_name = Column(String(255), nullable=True)
    created_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    inviter = relationship("User", foreign_keys=[invited_by])
    created_user = relationship("User", foreign_keys=[created_user_id])
