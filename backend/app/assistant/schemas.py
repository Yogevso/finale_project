"""Pydantic schemas for the AI assistant module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Tool definitions ---


class ToolParameter(BaseModel):
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Describes a tool that the LLM can invoke."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format for Ollama
    required_permission: str | None = None  # Permission enum value
    required_role: str | None = None  # Minimum role


class ToolCall(BaseModel):
    """A single tool invocation requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """The result returned after executing a tool."""

    tool_call_id: str
    name: str
    success: bool
    result: str  # Serialised result text
    error: str | None = None


# --- Conversation turns ---


class ConversationTurn(BaseModel):
    """A single turn in the conversation history."""

    role: str  # "user", "assistant", "tool", "system"
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None


# --- API request / response ---


class ChatRequest(BaseModel):
    conversation_id: int | None = None  # None = new conversation
    message: str = Field(..., min_length=1, max_length=4000)
    file_ids: list[int] | None = Field(
        default=None,
        max_length=3,
    )  # IDs of uploaded files to include as context
    document_ids: list[int] | None = Field(
        default=None,
        max_length=3,
    )  # IDs of platform documents to inject as context


class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    tool_calls_made: list[dict[str, Any]] | None = None


class StreamChunk(BaseModel):
    """A single chunk in a streamed assistant response."""

    conversation_id: int
    delta: str  # Partial text
    done: bool = False
    tool_calls_made: list[dict[str, Any]] | None = None


# --- Conversation listing / detail ---


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: int
    title: str
    messages: list[ConversationTurn]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Available tools listing ---


class AvailableTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]
