"""Async HTTP client for the Ollama inference server."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """Thin async wrapper around the Ollama REST API."""

    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Chat (non-streaming)
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the full response dict."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Chat (streaming — NDJSON)
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming chat — yields partial response dicts (NDJSON lines)."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed NDJSON line from Ollama")

    # ------------------------------------------------------------------
    # Health / model helpers
    # ------------------------------------------------------------------

    async def is_healthy(self) -> bool:
        """Return True if Ollama is reachable and the configured model exists."""
        try:
            models = await self.list_models()
            return self._model in models
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Return names of all locally-available models."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def pull_model(self, model: str | None = None) -> bool:
        """Pull a model. Returns True on success."""
        target = model or self._model
        logger.info("Pulling Ollama model %s …", target)
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(
                    f"{self._base_url}/api/pull",
                    json={"name": target},
                )
                resp.raise_for_status()
                return True
        except Exception:
            logger.exception("Failed to pull model %s", target)
            return False
