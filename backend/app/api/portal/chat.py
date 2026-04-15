"""Portal chat API - customer access to existing cross-role conversations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_chat_db, get_db
from app.dependencies.permissions import require_customer
from app.models import User
from app.schemas.chat import (
    ChatDetailResponse,
    ChatListItem,
    ChatListResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatParticipantResponse,
    ChatResponse,
    SendMessageRequest,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/portal/chats", tags=["Customer Chat"])


def _get_chat_service(
    chat_db: Session = Depends(get_chat_db), db: Session = Depends(get_db)
) -> ChatService:
    return ChatService(chat_db, core_db=db)


def _msg_to_response(msg, db: Session) -> ChatMessageResponse:
    sender = db.query(User).filter(User.id == msg.sender_id).first() if msg.sender_id else None
    return ChatMessageResponse(
        id=msg.id,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        content=msg.content,
        message_type=msg.message_type,
        context_json=msg.context_json,
        file_url=msg.file_url,
        file_name=msg.file_name,
        file_size=msg.file_size,
        file_mime_type=msg.file_mime_type,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        sender_full_name=sender.full_name if sender else None,
    )


def _participant_to_response(participant, db: Session) -> ChatParticipantResponse:
    user = (
        db.query(User).filter(User.id == participant.user_id).first()
        if participant.user_id
        else None
    )
    return ChatParticipantResponse(
        id=participant.id,
        user_id=participant.user_id,
        role=participant.role,
        joined_at=participant.joined_at,
        last_read_at=participant.last_read_at,
        is_muted=participant.is_muted,
        user_full_name=user.full_name if user else None,
    )


@router.get("", response_model=ChatListResponse)
def list_my_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_customer),
    svc: ChatService = Depends(_get_chat_service),
):
    """List chats the current customer already participates in."""
    all_items = svc.get_user_chats(current_user)
    total = len(all_items)
    offset = (page - 1) * page_size
    page_items = all_items[offset : offset + page_size]
    return ChatListResponse(
        items=[
            ChatListItem(
                chat=ChatResponse.model_validate(item["chat"]),
                display_name=item["display_name"],
                last_message=_msg_to_response(item["last_message"], svc.core_db)
                if item["last_message"]
                else None,
                unread_count=item["unread_count"],
                is_muted=item["is_muted"],
            )
            for item in page_items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    chat_id: int,
    current_user: User = Depends(require_customer),
    svc: ChatService = Depends(_get_chat_service),
):
    """Return chat details for a customer-visible conversation."""
    chat = svc.get_chat(chat_id, current_user)
    return ChatDetailResponse(
        id=chat.id,
        type=chat.type,
        name=chat.name,
        document_id=chat.document_id,
        created_by=chat.created_by,
        tenant_id=chat.tenant_id,
        last_message_at=chat.last_message_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        participants=[
            _participant_to_response(participant, svc.core_db) for participant in chat.participants
        ],
    )


@router.get("/{chat_id}/messages", response_model=ChatMessageListResponse)
def get_messages(
    chat_id: int,
    before_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_customer),
    svc: ChatService = Depends(_get_chat_service),
):
    """Return paginated messages for a customer-visible conversation."""
    messages = svc.get_chat_history(chat_id, current_user, before_id=before_id, limit=limit)
    return ChatMessageListResponse(
        items=[_msg_to_response(message, svc.core_db) for message in messages],
        has_more=len(messages) == limit,
    )


@router.post(
    "/{chat_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED
)
def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(require_customer),
    svc: ChatService = Depends(_get_chat_service),
):
    """Send a customer reply in an existing chat thread."""
    msg = svc.send_message(chat_id, current_user, body.content, context_json=body.context_json)
    return _msg_to_response(msg, svc.core_db)


@router.post("/{chat_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_chat_read(
    chat_id: int,
    current_user: User = Depends(require_customer),
    svc: ChatService = Depends(_get_chat_service),
):
    """Mark a portal chat as read for the current customer."""
    svc.mark_as_read(chat_id, current_user)
