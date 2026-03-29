"""Pydantic schemas for chat and support features (Wave X.1)."""

import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import (
    ChatMessageType,
    ChatParticipantRole,
    ChatType,
    SupportTicketPriority,
    SupportTicketStatus,
    UserRole,
)


# ========== Chat Schemas ==========


class ChatParticipantResponse(BaseModel):
    id: int
    user_id: int
    role: ChatParticipantRole
    joined_at: datetime
    last_read_at: Optional[datetime] = None
    is_muted: bool
    # Nested user info
    user_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    content: str
    message_type: ChatMessageType
    context_json: Optional[str] = None  # AH-009: context card metadata
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_mime_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sender_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    id: int
    type: ChatType
    name: Optional[str] = None
    document_id: Optional[int] = None  # AH-008: document-scoped chat
    created_by: int
    tenant_id: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatDetailResponse(ChatResponse):
    participants: List[ChatParticipantResponse] = []


class ChatListItem(BaseModel):
    chat: ChatResponse
    display_name: str
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0
    is_muted: bool = False


class ChatListResponse(BaseModel):
    items: List[ChatListItem]
    total: int
    page: int = 1
    page_size: int = 50


class ChatEligibleUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CreateDirectChatRequest(BaseModel):
    user_id: int = Field(..., description="ID of the other user")


class CreateGroupChatRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    participant_ids: List[int] = Field(..., min_length=1)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    context_json: Optional[str] = Field(None, max_length=5000, description="AH-009: context card metadata (document title, section, anchor, comment type)")

    # FIX-026e: Validate context_json is well-formed JSON with known keys
    _ALLOWED_CONTEXT_KEYS = {
        "document_id", "document_title", "section", "section_id",
        "anchor", "comment_type", "version_id", "page", "highlight",
    }

    @field_validator("context_json")
    @classmethod
    def validate_context_json(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            parsed = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("context_json must be valid JSON")
        if not isinstance(parsed, dict):
            raise ValueError("context_json must be a JSON object")
        unknown = set(parsed.keys()) - cls._ALLOWED_CONTEXT_KEYS
        if unknown:
            raise ValueError(f"context_json contains unknown keys: {', '.join(sorted(unknown))}")
        return v


class CreateDocumentChatRequest(BaseModel):
    """AH-008: Create or return existing chat scoped to a document."""
    document_id: int = Field(..., description="Document to scope the chat to")
    participant_ids: List[int] = Field(default_factory=list, description="Extra user IDs to include (authors auto-added)")


class AddParticipantRequest(BaseModel):
    user_id: int


class ChatMessageListResponse(BaseModel):
    items: List[ChatMessageResponse]
    has_more: bool


class UpdateChatRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class UpdateParticipantRoleRequest(BaseModel):
    role: ChatParticipantRole


# ========== Support Ticket Schemas ==========


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    priority: SupportTicketPriority = SupportTicketPriority.NORMAL
    category: Optional[str] = Field(None, max_length=100)
    feedback_id: Optional[int] = None


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[SupportTicketStatus] = None
    priority: Optional[SupportTicketPriority] = None
    category: Optional[str] = Field(None, max_length=100)


class SupportTicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_type: str
    content: str
    is_internal_note: bool
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_mime_type: Optional[str] = None
    created_at: datetime
    sender_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupportTicketAssignmentResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: int
    is_primary: bool
    assigned_at: datetime
    agent_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupportTicketResponse(BaseModel):
    id: int
    customer_id: int
    subject: str
    status: SupportTicketStatus
    priority: SupportTicketPriority
    category: Optional[str] = None
    feedback_id: Optional[int] = None
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    customer_full_name: Optional[str] = None
    last_customer_message_at: Optional[datetime] = None
    has_unread_activity: bool = False
    awaiting_agent_reply: bool = False
    needs_attention: bool = False

    model_config = ConfigDict(from_attributes=True)


class SupportTicketDetailResponse(SupportTicketResponse):
    messages: List[SupportTicketMessageResponse] = []
    assignments: List[SupportTicketAssignmentResponse] = []


class SupportTicketListResponse(BaseModel):
    items: List[SupportTicketResponse]
    total: int
    page: int
    page_size: int


class SupportTicketSummaryResponse(BaseModel):
    unread_count: int = 0
    customer_reply_count: int = 0
    needs_attention_count: int = 0
    nav_badge_count: int = 0


class SendTicketMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    is_internal_note: bool = False


class AssignAgentRequest(BaseModel):
    agent_id: int
    is_primary: bool = False


class HandoffRequest(BaseModel):
    target_agent_id: int
    note: str = ""


# ========== Canned Response Schemas (X1-103) ==========


class CannedResponseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    category: Optional[str] = Field(None, max_length=100)


class CannedResponseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    category: Optional[str] = Field(None, max_length=100)


class CannedResponseResponse(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str] = None
    created_by: int
    creator_name: Optional[str] = None
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CannedResponseListResponse(BaseModel):
    items: List[CannedResponseResponse]
    total: int
