"""Shared model enums."""

import enum


class UserRole(str, enum.Enum):
    """User roles - 6 total roles for the customer portal."""

    SYSTEM_ADMIN = "system_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"
    CUSTOMER = "customer"


class DocumentStatus(str, enum.Enum):
    """Document lifecycle statuses."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    ACTIVE = "active"
    PUBLISHED = "active"
    ARCHIVED = "archived"


class DocumentVisibility(str, enum.Enum):
    """Document visibility levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    COMPANY = "company"


class ReviewStatus(str, enum.Enum):
    """Review request statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VersionBumpType(str, enum.Enum):
    """Version bump level for semantic versioning."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class FeedbackType(str, enum.Enum):
    """Feedback types from customers."""

    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    """Feedback processing status."""

    PENDING = "pending"
    RESPONDED = "responded"
    CLOSED = "closed"


class ActionType(str, enum.Enum):
    """Audit log action types."""

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
    """Notification types."""

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
    """Invitation status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InvitationEmailDeliveryStatus(str, enum.Enum):
    """Invitation email delivery state."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class CollaborationActivityType(str, enum.Enum):
    """Collaboration activity types."""

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
    """Collaboration snapshot types."""

    AUTO_SAVE = "auto_save"
    MANUAL_SAVE = "manual_save"
    SESSION_END = "session_end"
    PRE_PUBLISH = "pre_publish"


class ChatType(str, enum.Enum):
    """Chat types."""

    DIRECT = "direct"
    GROUP = "group"


class ChatParticipantRole(str, enum.Enum):
    """Participant roles in a chat."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ChatMessageType(str, enum.Enum):
    """Chat message types."""

    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"


class SupportTicketStatus(str, enum.Enum):
    """Support ticket statuses."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketPriority(str, enum.Enum):
    """Support ticket priorities."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AdminActionStatus(str, enum.Enum):
    """Status for queued admin actions requiring approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class AdminActionType(str, enum.Enum):
    """Types of critical admin actions that require approval."""

    TENANT_DELETION = "tenant_deletion"
    MASS_USER_DEACTIVATION = "mass_user_deactivation"
    TENANT_SUSPENSION = "tenant_suspension"
    DATA_EXPORT = "data_export"
    QUOTA_OVERRIDE = "quota_override"
    SYSTEM_SETTING_CHANGE = "system_setting_change"


class DomainVerificationStatus(str, enum.Enum):
    """Status for domain ownership verification."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


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


class ExperimentStatus(str, enum.Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
