"""Assistant API endpoints — chat, conversations, tools, health."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.assistant.conversation import ConversationManager
from app.assistant.engine import AssistantEngine
from app.assistant.ollama_client import OllamaClient
from app.assistant.schemas import (
    AvailableTool,
    ChatRequest,
    ConversationDetail,
    ConversationSummary,
    ConversationTurn,
)
from app.assistant.tools import registry
from app.config import settings
from app.db import get_db
from app.models import User, UserRole
from app.security import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])

# Simple in-memory per-user rate limiter
_rate_buckets: dict[int, list[float]] = defaultdict(list)


def _check_rate_limit(user_id: int) -> None:
    now = time.time()
    window = 60.0
    bucket = _rate_buckets[user_id]
    # Prune old entries
    _rate_buckets[user_id] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[user_id]) >= settings.ASSISTANT_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before sending another message.")
    _rate_buckets[user_id].append(now)


def _require_enabled() -> None:
    if not settings.ASSISTANT_ENABLED:
        raise HTTPException(status_code=503, detail="AI assistant is currently disabled.")


def _build_engine(db: Session, user: User) -> AssistantEngine:
    ollama = OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.ASSISTANT_MODEL,
        timeout=settings.ASSISTANT_REQUEST_TIMEOUT,
    )
    conv_mgr = ConversationManager(db)
    return AssistantEngine(ollama, registry, conv_mgr)


# ------------------------------------------------------------------
# SSE Chat
# ------------------------------------------------------------------


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a message and receive a streamed SSE response."""
    _require_enabled()
    _check_rate_limit(user.id)

    engine = _build_engine(db, user)
    tenant_id = None if user.role == UserRole.SYSTEM_ADMIN else user.tenant_id

    async def event_stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()
        done = asyncio.Event()

        async def _producer():
            try:
                async for event in engine.chat(
                    user=user,
                    tenant_id=tenant_id,
                    message=body.message,
                    conversation_id=body.conversation_id,
                    db=db,
                    file_ids=body.file_ids,
                    document_ids=body.document_ids,
                ):
                    await queue.put(event)
            finally:
                done.set()
                await queue.put(None)

        async def _heartbeat():
            """Send SSE keepalive comments every 3s to prevent proxy/browser timeouts."""
            while not done.is_set():
                await asyncio.sleep(3)
                if not done.is_set():
                    await queue.put({"event": "_keepalive"})

        prod_task = asyncio.create_task(_producer())
        hb_task = asyncio.create_task(_heartbeat())

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=180)
                except asyncio.TimeoutError:
                    yield 'event: error\ndata: {"message":"Request timed out"}\n\n'
                    break
                if event is None:
                    break
                if event.get("event") == "_keepalive":
                    yield ": keepalive\n\n"
                    continue
                evt = event.get("event", "message")
                data = event.get("data", "")
                if isinstance(data, dict):
                    data = json.dumps(data)
                yield f"event: {evt}\ndata: {data}\n\n"
        finally:
            hb_task.cancel()
            if not prod_task.done():
                prod_task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ------------------------------------------------------------------
# Conversations CRUD
# ------------------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List the current user's conversations."""
    _require_enabled()
    mgr = ConversationManager(db)
    convs = mgr.list_conversations(user.id, limit=limit, offset=offset)
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=mgr.get_message_count(c.id),
        )
        for c in convs
    ]


@router.post("/conversations", response_model=ConversationSummary, status_code=201)
def create_conversation(
    title: str = "New Chat",
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new empty conversation."""
    _require_enabled()
    mgr = ConversationManager(db)
    conv = mgr.create_conversation(user.id, user.tenant_id, title)
    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a conversation with all its messages."""
    _require_enabled()
    mgr = ConversationManager(db)
    conv = mgr.get_conversation(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = mgr.get_messages(conversation_id)

    def _parse_tool_calls(raw: str | None) -> list[dict] | None:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[
            ConversationTurn(
                role=m.role,
                content=m.content,
                tool_calls=_parse_tool_calls(m.tool_calls),
                tool_call_id=m.tool_call_id,
                tool_name=m.tool_name,
            )
            for m in messages
        ],
    )


@router.patch("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    title: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Rename a conversation."""
    _require_enabled()
    mgr = ConversationManager(db)
    conv = mgr.get_conversation(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    mgr.update_title(conversation_id, title)
    return {"id": conv.id, "title": title}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    _require_enabled()
    mgr = ConversationManager(db)
    if not mgr.delete_conversation(conversation_id, user.id):
        raise HTTPException(status_code=404, detail="Conversation not found.")


# ------------------------------------------------------------------
# Tools listing
# ------------------------------------------------------------------


@router.get("/tools", response_model=list[AvailableTool])
def list_tools(user: User = Depends(get_current_active_user)):
    """List tools available to the current user based on their permissions."""
    _require_enabled()
    tools = registry.get_tools_for_user(user)
    return [
        AvailableTool(name=t.name, description=t.description, parameters=t.parameters)
        for t in sorted(tools, key=lambda x: x.name)
    ]


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------


@router.get("/health")
async def assistant_health(user: User = Depends(get_current_active_user)):
    """Check if the AI assistant is ready."""
    if not settings.ASSISTANT_ENABLED:
        return {"status": "disabled", "model": settings.ASSISTANT_MODEL, "ollama_healthy": False}

    client = OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.ASSISTANT_MODEL,
        timeout=10,
    )
    healthy = await client.is_healthy()
    return {
        "status": "ready" if healthy else "unavailable",
        "model": settings.ASSISTANT_MODEL,
        "ollama_healthy": healthy,
    }


# ------------------------------------------------------------------
# File Uploads
# ------------------------------------------------------------------


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload a file for assistant analysis."""
    _require_enabled()
    from app.assistant.file_handler import AssistantFileHandler

    handler = AssistantFileHandler()
    try:
        record = await handler.save_upload(file, user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "file_id": record.id,
        "filename": record.original_filename,
        "mime_type": record.mime_type,
        "file_size": record.file_size,
        "has_text": bool(record.extracted_text),
    }


@router.get("/files/{file_id}")
def get_uploaded_file(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get metadata and text preview for an uploaded file."""
    _require_enabled()
    from app.assistant.file_handler import AssistantFileHandler

    handler = AssistantFileHandler()
    record = handler.get_file(file_id, user.id, db)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    preview = (record.extracted_text or "")[:500]
    return {
        "file_id": record.id,
        "filename": record.original_filename,
        "mime_type": record.mime_type,
        "file_size": record.file_size,
        "has_text": bool(record.extracted_text),
        "text_preview": preview,
        "created_at": record.created_at.isoformat(),
    }
