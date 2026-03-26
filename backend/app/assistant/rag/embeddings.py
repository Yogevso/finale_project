"""Async wrapper around Ollama /api/embed endpoint for text embeddings."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import settings
from app.observability import REQUEST_ID_HEADER, TRACE_ID_HEADER, current_request_id, current_trace_id

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0


def _trace_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    trace_id = current_trace_id.get(None)
    if trace_id:
        headers[TRACE_ID_HEADER] = trace_id
    request_id = current_request_id.get(None)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return headers


class OllamaEmbeddings:
    """Generate text embeddings via Ollama's /api/embed endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.ASSISTANT_EMBEDDING_MODEL
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0),
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string, returns a vector (list of floats)."""
        result = await self._request(text)
        return result

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. Ollama /api/embed supports batch input."""
        if not texts:
            return []
        client = self._get_client()
        payload: dict[str, Any] = {"model": self._model, "input": texts}
        headers = _trace_headers()

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    f"{self._base_url}/api/embed", json=payload, headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                # Ollama returns {"embeddings": [[...], [...]]}
                return data.get("embeddings", [])
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Ollama embed batch attempt %d failed (%s), retrying in %.1fs",
                        attempt + 1, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def _request(self, text: str) -> list[float]:
        """Send a single embed request with retry logic."""
        client = self._get_client()
        payload: dict[str, Any] = {"model": self._model, "input": text}
        headers = _trace_headers()

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    f"{self._base_url}/api/embed", json=payload, headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
                raise ValueError("Empty embeddings response from Ollama")
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Ollama embed attempt %d failed (%s), retrying in %.1fs",
                        attempt + 1, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def ensure_model(self) -> bool:
        """Check if the embedding model is available, pull if not."""
        try:
            client = self._get_client()
            resp = await client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            if self._model in models or f"{self._model}:latest" in models:
                return True
            # Try to pull
            logger.info("Pulling embedding model %s...", self._model)
            resp = await client.post(
                f"{self._base_url}/api/pull",
                json={"name": self._model, "stream": False},
                timeout=httpx.Timeout(600.0, connect=10.0),
            )
            resp.raise_for_status()
            return True
        except Exception:  # policy: BOUNDARY — embedding backend failure becomes a stable fallback
            logger.warning("Failed to ensure embedding model %s", self._model, exc_info=True)
            return False
