"""Assistant API endpoints — chat, conversations, tools, health."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import logging
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
from app.db import get_chat_db, get_db
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.models import User, UserRole
from app.security import get_current_active_user
from app.services.assistant_capacity_service import (
    AssistantCapacityExceeded,
    acquire_assistant_chat_slot,
    get_assistant_capacity_service,
)
from app.services.distributed_rate_limit_service import DistributedRateLimitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])


def _check_rate_limit(user_id: int) -> None:
    allowed, retry_after = DistributedRateLimitService.check_and_record(
        scope="assistant-chat",
        key=str(user_id),
        max_requests=settings.ASSISTANT_RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before sending another message.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )


def _require_enabled() -> None:
    if not is_backend_feature_enabled(BackendFeatureFlag.ASSISTANT):
        raise HTTPException(status_code=503, detail="AI assistant is currently disabled.")


def _build_engine(chat_db: Session, user: User) -> AssistantEngine:
    ollama = OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.ASSISTANT_MODEL,
        timeout=settings.ASSISTANT_REQUEST_TIMEOUT,
    )
    conv_mgr = ConversationManager(chat_db)
    return AssistantEngine(ollama, registry, conv_mgr)


def _assistant_capacity_payload() -> dict[str, Any]:
    snapshot = get_assistant_capacity_service().snapshot()
    return {
        "status": snapshot.status,
        "recorded_at": snapshot.recorded_at,
        "total_rejections": snapshot.total_rejections,
        "total_timeouts": snapshot.total_timeouts,
        "chat": {
            "status": snapshot.chat.status,
            "active": snapshot.chat.active,
            "queued": snapshot.chat.queued,
            "max_concurrent": snapshot.chat.max_concurrent,
            "max_queue": snapshot.chat.max_queue,
            "queue_timeout_seconds": snapshot.chat.queue_timeout_seconds,
            "total_admitted": snapshot.chat.total_admitted,
            "total_completed": snapshot.chat.total_completed,
            "total_rejected": snapshot.chat.total_rejected,
            "total_timed_out": snapshot.chat.total_timed_out,
            "p50_duration_ms": snapshot.chat.p50_duration_ms,
            "p95_duration_ms": snapshot.chat.p95_duration_ms,
            "p50_queue_wait_ms": snapshot.chat.p50_queue_wait_ms,
            "p95_queue_wait_ms": snapshot.chat.p95_queue_wait_ms,
            "last_rejected_at": snapshot.chat.last_rejected_at,
            "last_rejection_reason": snapshot.chat.last_rejection_reason,
        },
        "embedding": {
            "status": snapshot.embedding.status,
            "active": snapshot.embedding.active,
            "queued": snapshot.embedding.queued,
            "max_concurrent": snapshot.embedding.max_concurrent,
            "max_queue": snapshot.embedding.max_queue,
            "queue_timeout_seconds": snapshot.embedding.queue_timeout_seconds,
            "total_admitted": snapshot.embedding.total_admitted,
            "total_completed": snapshot.embedding.total_completed,
            "total_rejected": snapshot.embedding.total_rejected,
            "total_timed_out": snapshot.embedding.total_timed_out,
            "p50_duration_ms": snapshot.embedding.p50_duration_ms,
            "p95_duration_ms": snapshot.embedding.p95_duration_ms,
            "p50_queue_wait_ms": snapshot.embedding.p50_queue_wait_ms,
            "p95_queue_wait_ms": snapshot.embedding.p95_queue_wait_ms,
            "last_rejected_at": snapshot.embedding.last_rejected_at,
            "last_rejection_reason": snapshot.embedding.last_rejection_reason,
        },
    }


async def _stream_assistant_events(
    *,
    request: Request,
    queue: asyncio.Queue[dict[str, Any] | None],
    done: asyncio.Event,
    prod_task: asyncio.Task[None],
    hb_task: asyncio.Task[None],
):
    idle_deadline = asyncio.get_running_loop().time() + 180
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                if asyncio.get_running_loop().time() >= idle_deadline:
                    yield 'event: error\ndata: {"message":"Request timed out"}\n\n'
                    break
                continue
            if event is None:
                break
            idle_deadline = asyncio.get_running_loop().time() + 180
            if event.get("event") == "_keepalive":
                yield ": keepalive\n\n"
                continue
            evt = event.get("event", "message")
            data = event.get("data", "")
            if isinstance(data, dict):
                data = json.dumps(data)
            yield f"event: {evt}\ndata: {data}\n\n"
    finally:
        done.set()
        for task in (hb_task, prod_task):
            if not task.done():
                task.cancel()
        for task in (hb_task, prod_task):
            with suppress(asyncio.CancelledError):
                await task


# ------------------------------------------------------------------
# SSE Chat
# ------------------------------------------------------------------


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
):
    """Send a message and receive a streamed SSE response."""
    _require_enabled()
    _check_rate_limit(user.id)
    try:
        permit = await acquire_assistant_chat_slot()
    except AssistantCapacityExceeded as exc:
        raise HTTPException(
            status_code=503,
            detail="AI assistant is currently busy. Please try again shortly.",
            headers={"Retry-After": str(max(exc.retry_after_seconds, 1))},
        )

    engine = _build_engine(chat_db, user)
    tenant_id = None if user.role == UserRole.SYSTEM_ADMIN else user.tenant_id

    async def event_stream():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
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
            async for chunk in _stream_assistant_events(
                request=request,
                queue=queue,
                done=done,
                prod_task=prod_task,
                hb_task=hb_task,
            ):
                yield chunk
        finally:
            await permit.release()

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
    db: Session = Depends(get_chat_db),
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
    db: Session = Depends(get_chat_db),
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
    db: Session = Depends(get_chat_db),
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
    db: Session = Depends(get_chat_db),
):
    """Rename a conversation."""
    _require_enabled()
    mgr = ConversationManager(db)
    conv = mgr.get_conversation(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    updated = mgr.update_title(conversation_id, title)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"id": updated.id, "title": updated.title}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_chat_db),
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
    capacity = _assistant_capacity_payload()
    if not is_backend_feature_enabled(BackendFeatureFlag.ASSISTANT):
        return {
            "status": "disabled",
            "model": settings.ASSISTANT_MODEL,
            "ollama_healthy": False,
            "capacity": capacity,
        }

    client = OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.ASSISTANT_MODEL,
        timeout=10,
    )
    healthy = await client.is_healthy()
    status = "ready" if healthy else "unavailable"
    if healthy and capacity["status"] != "ready":
        status = "degraded"
    return {
        "status": status,
        "model": settings.ASSISTANT_MODEL,
        "ollama_healthy": healthy,
        "capacity": capacity,
    }


# ------------------------------------------------------------------
# File Uploads
# ------------------------------------------------------------------


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_chat_db),
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
    db: Session = Depends(get_chat_db),
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
