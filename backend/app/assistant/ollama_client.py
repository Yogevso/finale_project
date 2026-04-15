"""Async HTTP client for the Ollama inference server."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

import httpx

from app.observability import (
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    current_request_id,
    current_trace_id,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds, doubles each retry


def _trace_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    trace_id = current_trace_id.get(None)
    if trace_id:
        headers[TRACE_ID_HEADER] = trace_id
    request_id = current_request_id.get(None)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return headers


class OllamaClient:
    """Thin async wrapper around the Ollama REST API.

    Uses a class-level shared ``httpx.AsyncClient`` so TCP connections
    are reused across requests (connection pooling).
    """

    _shared_client: httpx.AsyncClient | None = None

    def __init__(self, base_url: str, model: str, timeout: int = 180) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Shared client (connection pool)
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared ``httpx.AsyncClient``."""
        if OllamaClient._shared_client is None or OllamaClient._shared_client.is_closed:
            OllamaClient._shared_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return OllamaClient._shared_client

    # ------------------------------------------------------------------
    # Chat (non-streaming)
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        num_ctx: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the full response dict."""
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if num_ctx is not None:
            options["num_ctx"] = num_ctx

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        client = self._get_client()
        headers = _trace_headers()
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    f"{self._base_url}/api/chat", json=payload, headers=headers
                )
                resp.raise_for_status()
                return resp.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF * (2**attempt)
                    logger.warning(
                        "Ollama chat attempt %d failed (%s), retrying in %.1fs",
                        attempt + 1,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Chat (streaming — NDJSON)
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        num_ctx: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming chat — yields partial response dicts (NDJSON lines)."""
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if num_ctx is not None:
            options["num_ctx"] = num_ctx

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "keep_alive": "30m",
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        client = self._get_client()
        headers = _trace_headers()
        async with client.stream(
            "POST", f"{self._base_url}/api/chat", json=payload, headers=headers
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
        except Exception:  # policy: DEGRADED — health probe failure reports backend as unavailable
            return False

    async def warmup(self) -> None:
        """Pre-load the model into GPU memory with a minimal request."""
        try:
            client = self._get_client()
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": 1, "num_ctx": 2048},
            }
            await client.post(f"{self._base_url}/api/chat", json=payload)
            logger.info("Model %s warmed up and loaded into memory", self._model)
        except Exception:  # policy: LOSSY — warmup failure should not block serving requests
            logger.warning("Model warmup failed (non-fatal)", exc_info=True)

    async def list_models(self) -> list[str]:
        """Return names of all locally-available models."""
        client = self._get_client()
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
        except Exception:  # policy: BOUNDARY — model pull wraps provider failures consistently
            logger.exception("Failed to pull model %s", target)
            return False
