"""Assistant API endpoints — chat, conversations, tools, health."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.models import User
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
    tenant_id = user.tenant_id

    async def event_stream():
        async for event in engine.chat(
            user=user,
            tenant_id=tenant_id,
            message=body.message,
            conversation_id=body.conversation_id,
            db=db,
        ):
            evt = event.get("event", "message")
            data = event.get("data", "")
            if isinstance(data, dict):
                data = json.dumps(data)
            yield f"event: {evt}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[
            ConversationTurn(
                role=m.role,
                content=m.content,
                tool_call_id=m.tool_call_id,
            )
            for m in messages
        ],
    )


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
