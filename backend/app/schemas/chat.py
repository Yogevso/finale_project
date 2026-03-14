"""Pydantic schemas for chat and support features (Wave X.1)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ChatMessageType,
    ChatParticipantRole,
    ChatType,
    SupportTicketPriority,
    SupportTicketStatus,
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


class CreateDirectChatRequest(BaseModel):
    user_id: int = Field(..., description="ID of the other user")


class CreateGroupChatRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    participant_ids: List[int] = Field(..., min_length=1)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


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

    model_config = ConfigDict(from_attributes=True)


class SupportTicketDetailResponse(SupportTicketResponse):
    messages: List[SupportTicketMessageResponse] = []
    assignments: List[SupportTicketAssignmentResponse] = []


class SupportTicketListResponse(BaseModel):
    items: List[SupportTicketResponse]
    total: int
    page: int
    page_size: int


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
