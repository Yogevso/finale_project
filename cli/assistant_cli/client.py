"""HTTP client for the Portal API with SSE stream parsing."""

from __future__ import annotations

from typing import AsyncGenerator

import httpx

from .config import CLIConfig


class PortalClient:
    """Async API client that wraps the Portal backend endpoints."""

    def __init__(self, config: CLIConfig):
        self.base_url = config.base_url
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

    # ── Chat (SSE streaming) ─────────────────────────────────────

    async def chat_stream(
        self, message: str, conversation_id: int | None = None
    ) -> AsyncGenerator[dict, None]:
        """Send a chat message and yield SSE events as they arrive."""
        payload: dict = {"message": message}
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id

        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/assistant/chat",
                json=payload,
                headers=self.headers,
            ) as resp:
                if resp.status_code == 401:
                    yield {"event": "error", "data": "Session expired. Please login again."}
                    return
                if resp.status_code == 429:
                    yield {"event": "error", "data": "Rate limit exceeded. Please wait."}
                    return
                if resp.status_code != 200:
                    text = ""
                    async for chunk in resp.aiter_text():
                        text += chunk
                    yield {"event": "error", "data": f"Server error ({resp.status_code}): {text[:200]}"}
                    return

                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_block, buffer = buffer.split("\n\n", 1)
                        parsed = self._parse_sse_block(event_block)
                        if parsed:
                            yield parsed

    @staticmethod
    def _parse_sse_block(block: str) -> dict | None:
        event_name = "message"
        event_data = ""
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event_name = line[7:].strip()
            elif line.startswith("data: "):
                event_data = line[6:]
        if not event_name:
            return None

        import json as _json

        try:
            data = _json.loads(event_data)
        except (ValueError, TypeError):
            data = event_data

        return {"event": event_name, "data": data}

    # ── REST helpers ─────────────────────────────────────────────

    async def _get(self, path: str, **params) -> dict | list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.base_url}{path}", headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def list_conversations(self, limit: int = 30) -> list:
        return await self._get("/assistant/conversations", limit=limit)

    async def get_conversation(self, cid: int) -> dict:
        return await self._get(f"/assistant/conversations/{cid}")

    async def delete_conversation(self, cid: int) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.delete(
                f"{self.base_url}/assistant/conversations/{cid}",
                headers=self.headers,
            )
            return r.status_code == 204

    async def get_available_tools(self) -> list:
        return await self._get("/assistant/tools")

    async def get_assistant_health(self) -> dict:
        return await self._get("/assistant/health")
