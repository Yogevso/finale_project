"""Domain event definitions for write-path side effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base type for immutable domain events."""

    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True, slots=True)
class DocumentPublished(DomainEvent):
    """Document version was published and document became active."""

    document_id: int
    version_id: int
    document_title: str
    document_number: str
    document_url: str
    document_author_id: Optional[int]
    published_by_user_id: int


@dataclass(frozen=True, slots=True)
class CommentCreated(DomainEvent):
    """A new comment or reply was created for a document."""

    document_id: int
    document_title: str
    document_url: str
    document_author_id: Optional[int]
    comment_id: int
    comment_content: str
    commenter_user_id: int
    commenter_display_name: str
    parent_comment_author_id: Optional[int]
    is_private: bool
    has_anchor: bool


@dataclass(frozen=True, slots=True)
class CommentChatBridgeRequested(DomainEvent):
    """A comment should be bridged into the internal direct-chat channel."""

    document_id: int
    comment_id: int
    document_author_id: Optional[int]
    commenter_user_id: int
    commenter_display_name: str


@dataclass(frozen=True, slots=True)
class CompanyAssignmentsUpdated(DomainEvent):
    """Document company-assignment set was replaced."""

    document_id: int
    document_row_version: int
    assigned_company_ids: tuple[int, ...]
    actor_user_id: Optional[int]
