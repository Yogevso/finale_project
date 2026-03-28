"""Chat API endpoints — internal messaging (Wave X.1)."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_chat_db, get_db
from app.dependencies.permissions import require_internal_user
from app.models import User, ChatMessage, ChatParticipant

CHAT_UPLOAD_DIR = Path("data/uploads/chat")
CHAT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_CHAT_FILE_SIZE = settings.MAX_UPLOAD_SIZE
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_FILE_TYPES = ALLOWED_IMAGE_TYPES | {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
}
from app.schemas.chat import (
    AddParticipantRequest,
    ChatDetailResponse,
    ChatEligibleUserResponse,
    ChatListItem,
    ChatListResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatParticipantResponse,
    ChatResponse,
    CreateDirectChatRequest,
    CreateDocumentChatRequest,
    CreateGroupChatRequest,
    SendMessageRequest,
    UpdateChatRequest,
    UpdateParticipantRoleRequest,
)
from app.services.chat_service import ChatService

router = APIRouter()


def _get_chat_service(chat_db: Session = Depends(get_chat_db), db: Session = Depends(get_db)) -> ChatService:
    return ChatService(chat_db, core_db=db)


def _msg_to_response(msg, db: Session) -> ChatMessageResponse:
    sender = db.query(User).filter(User.id == msg.sender_id).first() if msg.sender_id else None
    return ChatMessageResponse(
        id=msg.id,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        content=msg.content,
        message_type=msg.message_type,
        file_url=msg.file_url,
        file_name=msg.file_name,
        file_size=msg.file_size,
        file_mime_type=msg.file_mime_type,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        sender_full_name=sender.full_name if sender else None,
    )


def _participant_to_response(p, db: Session) -> ChatParticipantResponse:
    user = db.query(User).filter(User.id == p.user_id).first() if p.user_id else None
    return ChatParticipantResponse(
        id=p.id,
        user_id=p.user_id,
        role=p.role,
        joined_at=p.joined_at,
        last_read_at=p.last_read_at,
        is_muted=p.is_muted,
        user_full_name=user.full_name if user else None,
    )


# ---- Chat CRUD ----


@router.get("/chats/eligible-users", response_model=list[ChatEligibleUserResponse])
def list_chat_eligible_users(
    search: str | None = Query(None, min_length=1, max_length=255),
    current_user: User = Depends(require_internal_user),
    db: Session = Depends(get_db),
):
    """List active same-tenant chat targets for any internal user."""
    query = db.query(User).filter(
        User.tenant_id == current_user.tenant_id,
        User.is_active.is_(True),
        User.id != current_user.id,
    )
    if search:
        normalized = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(normalized),
                User.email.ilike(normalized),
                User.username.ilike(normalized),
            )
        )

    users = (
        query.order_by(User.full_name.asc(), User.id.asc())
        .limit(50)
        .all()
    )
    return [
        ChatEligibleUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            avatar_url=user.avatar_url,
        )
        for user in users
    ]


@router.get("/chats", response_model=ChatListResponse)
def list_my_chats(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """List all chats for the current user."""
    all_items = svc.get_user_chats(current_user)
    total = len(all_items)
    offset = (page - 1) * page_size
    page_items = all_items[offset:offset + page_size]
    return ChatListResponse(
        items=[
            ChatListItem(
                chat=ChatResponse.model_validate(i["chat"]),
                display_name=i["display_name"],
                last_message=_msg_to_response(i["last_message"], svc.core_db) if i["last_message"] else None,
                unread_count=i["unread_count"],
                is_muted=i["is_muted"],
            )
            for i in page_items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/chats/direct", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_direct_chat(
    body: CreateDirectChatRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Create or return an existing direct chat with another user."""
    chat = svc.create_direct_chat(current_user, body.user_id)
    return ChatResponse.model_validate(chat)


@router.post("/chats/group", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_group_chat(
    body: CreateGroupChatRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Create a new group chat."""
    chat = svc.create_group_chat(current_user, body.name, body.participant_ids)
    return ChatResponse.model_validate(chat)


@router.post("/chats/document", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_document_chat(
    body: CreateDocumentChatRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """AH-008: Create or return existing chat scoped to a document.

    Automatically adds the document's author(s) as participants.
    """
    chat = svc.create_document_chat(
        current_user, body.document_id, body.participant_ids
    )
    return ChatResponse.model_validate(chat)


@router.get("/chats/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    chat_id: int,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Get chat details with participant list."""
    chat = svc.get_chat(chat_id, current_user)
    return ChatDetailResponse(
        id=chat.id,
        type=chat.type,
        name=chat.name,
        created_by=chat.created_by,
        tenant_id=chat.tenant_id,
        last_message_at=chat.last_message_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        participants=[_participant_to_response(p, svc.core_db) for p in chat.participants],
    )


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Delete a chat. Group chats require owner permission."""
    svc.delete_chat(chat_id, current_user)


# ---- Messages ----


@router.get("/chats/{chat_id}/messages", response_model=ChatMessageListResponse)
def get_messages(
    chat_id: int,
    before_id: int | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Get paginated message history for a chat."""
    messages = svc.get_chat_history(chat_id, current_user, before_id=before_id, limit=limit)
    return ChatMessageListResponse(
        items=[_msg_to_response(m, svc.core_db) for m in messages],
        has_more=len(messages) == limit,
    )


@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Send a message in a chat."""
    msg = svc.send_message(chat_id, current_user, body.content, context_json=body.context_json)
    return _msg_to_response(msg, svc.core_db)


@router.post("/chats/{chat_id}/messages/upload", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def upload_chat_file(
    chat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Upload a file or image and create a file message in the chat."""
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")

    data = await file.read()
    if len(data) > MAX_CHAT_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_CHAT_FILE_SIZE // (1024 * 1024)} MB)",
        )

    ext = Path(file.filename or "file").suffix
    storage_name = f"{uuid.uuid4().hex}{ext}"
    chat_dir = CHAT_UPLOAD_DIR / str(chat_id)
    await asyncio.to_thread(chat_dir.mkdir, parents=True, exist_ok=True)
    file_path = chat_dir / storage_name
    await asyncio.to_thread(file_path.write_bytes, data)

    file_url = f"/api/v1/chats/{chat_id}/files/{storage_name}"
    msg = svc.send_file_message(
        chat_id,
        current_user,
        file_url=file_url,
        file_name=file.filename or "file",
        file_size=len(data),
        file_mime_type=content_type,
    )
    return _msg_to_response(msg, svc.core_db)


@router.get("/chats/{chat_id}/files/{filename}")
def download_chat_file(
    chat_id: int,
    filename: str,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Download a chat file. Only chat participants can access files."""
    svc._get_chat_with_permission(chat_id, current_user)

    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = CHAT_UPLOAD_DIR / str(chat_id) / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=safe_name)


# ---- Participants ----


@router.post("/chats/{chat_id}/participants", response_model=ChatParticipantResponse, status_code=status.HTTP_201_CREATED)
def add_participant(
    chat_id: int,
    body: AddParticipantRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Add a participant to a group chat. Requires owner/admin role."""
    p = svc.add_participant(chat_id, current_user, body.user_id)
    return _participant_to_response(p, svc.core_db)


@router.delete("/chats/{chat_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(
    chat_id: int,
    user_id: int,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Remove a participant from a group chat. Requires owner/admin role."""
    svc.remove_participant(chat_id, current_user, user_id)


# ---- Read receipts ----


@router.post("/chats/{chat_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_chat_read(
    chat_id: int,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Mark all messages in a chat as read."""
    svc.mark_as_read(chat_id, current_user)


# ---- Search ----


@router.get("/chats/messages/search", response_model=ChatMessageListResponse)
def search_all_messages(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Search messages across all user's chats."""
    messages = svc.search_all_messages(current_user, q, limit=limit)
    return ChatMessageListResponse(
        items=[_msg_to_response(m, svc.core_db) for m in messages],
        has_more=len(messages) == limit,
    )


@router.get("/chats/{chat_id}/messages/search", response_model=ChatMessageListResponse)
def search_messages(
    chat_id: int,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Search messages in a chat by content (X1-043)."""
    messages = svc.search_messages(chat_id, current_user, q, limit=limit)
    return ChatMessageListResponse(
        items=[_msg_to_response(m, svc.core_db) for m in messages],
        has_more=len(messages) == limit,
    )


# ---- Chat update (rename) ----


@router.patch("/chats/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    body: UpdateChatRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Update chat settings (e.g. rename group) (X1-045)."""
    if body.name is not None:
        chat = svc.update_chat(chat_id, current_user, body.name)
        return ChatResponse.model_validate(chat)
    raise HTTPException(status_code=400, detail="No update fields provided")


# ---- Mute toggle ----


@router.put("/chats/{chat_id}/mute", status_code=status.HTTP_200_OK)
def toggle_mute(
    chat_id: int,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Toggle mute for a chat (X1-025)."""
    is_muted = svc.toggle_mute(chat_id, current_user)
    return {"is_muted": is_muted}


# ---- Participant role ----


@router.patch(
    "/chats/{chat_id}/participants/{user_id}/role",
    response_model=ChatParticipantResponse,
)
def update_participant_role(
    chat_id: int,
    user_id: int,
    body: UpdateParticipantRoleRequest,
    current_user: User = Depends(require_internal_user),
    svc: ChatService = Depends(_get_chat_service),
):
    """Change a participant's role in a group chat (X1-046)."""
    p = svc.update_participant_role(chat_id, current_user, user_id, body.role)
    return _participant_to_response(p, svc.core_db)
