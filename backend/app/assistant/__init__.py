"""AI Assistant module — tool-calling engine, Ollama client, conversation management."""

from app.assistant.ollama_client import OllamaClient
from app.assistant.conversation import ConversationManager
from app.assistant.engine import AssistantEngine

__all__ = ["OllamaClient", "ConversationManager", "AssistantEngine"]
