"""WebSocket manager for real-time chat and support (Wave X.1).

Handles connection lifecycle, room subscriptions, message broadcasting,
typing indicators, and read receipts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for chat and support namespaces."""

    def __init__(self):
        # chat_id -> set of (user_id, websocket)
        self._chat_connections: dict[int, dict[int, WebSocket]] = {}
        # support ticket_id -> set of (user_id, websocket)
        self._support_connections: dict[int, dict[int, WebSocket]] = {}
        # user_id -> set of websockets (for notification routing)
        self._user_connections: dict[int, set[WebSocket]] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_chat(self, websocket: WebSocket, user_id: int, chat_ids: list[int]) -> None:
        """Accept connection and subscribe user to their chat rooms."""
        await websocket.accept()
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(websocket)

        for chat_id in chat_ids:
            if chat_id not in self._chat_connections:
                self._chat_connections[chat_id] = {}
            self._chat_connections[chat_id][user_id] = websocket

    async def connect_support(self, websocket: WebSocket, user_id: int, ticket_ids: list[int]) -> None:
        """Accept connection and subscribe user to their support ticket rooms."""
        await websocket.accept()
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(websocket)

        for ticket_id in ticket_ids:
            if ticket_id not in self._support_connections:
                self._support_connections[ticket_id] = {}
            self._support_connections[ticket_id][user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Remove connection from all rooms."""
        # Remove from user connections
        if user_id in self._user_connections:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

        # Remove from chat rooms
        for chat_id in list(self._chat_connections.keys()):
            if self._chat_connections[chat_id].get(user_id) is websocket:
                del self._chat_connections[chat_id][user_id]
                if not self._chat_connections[chat_id]:
                    del self._chat_connections[chat_id]

        # Remove from support rooms
        for ticket_id in list(self._support_connections.keys()):
            if self._support_connections[ticket_id].get(user_id) is websocket:
                del self._support_connections[ticket_id][user_id]
                if not self._support_connections[ticket_id]:
                    del self._support_connections[ticket_id]

    def join_chat(self, websocket: WebSocket, user_id: int, chat_id: int) -> None:
        """Subscribe to a specific chat room (e.g., after creating a new chat)."""
        if chat_id not in self._chat_connections:
            self._chat_connections[chat_id] = {}
        self._chat_connections[chat_id][user_id] = websocket

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast_to_chat(self, chat_id: int, event: str, data: dict, exclude_user: Optional[int] = None) -> None:
        """Send event to all users in a chat room."""
        connections = self._chat_connections.get(chat_id, {})
        payload = json.dumps({"event": event, "data": data})
        for uid, ws in list(connections.items()):
            if uid == exclude_user:
                continue
            await self._safe_send(ws, payload)

    async def broadcast_to_ticket(self, ticket_id: int, event: str, data: dict, exclude_user: Optional[int] = None) -> None:
        """Send event to all users in a support ticket room."""
        connections = self._support_connections.get(ticket_id, {})
        payload = json.dumps({"event": event, "data": data})
        for uid, ws in list(connections.items()):
            if uid == exclude_user:
                continue
            await self._safe_send(ws, payload)

    async def send_to_user(self, user_id: int, event: str, data: dict) -> None:
        """Send event to all connections for a specific user."""
        sockets = self._user_connections.get(user_id, set())
        payload = json.dumps({"event": event, "data": data})
        for ws in list(sockets):
            await self._safe_send(ws, payload)

    async def _safe_send(self, ws: WebSocket, payload: str) -> None:
        """Send data, silently removing dead connections."""
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(payload)
        except Exception:  # policy: LOSSY — connection already closed; cleanup via disconnect
            logger.debug("Failed to send WS payload — connection already closed")

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_online_users_in_chat(self, chat_id: int) -> list[int]:
        return list(self._chat_connections.get(chat_id, {}).keys())

    def get_online_users_in_ticket(self, ticket_id: int) -> list[int]:
        return list(self._support_connections.get(ticket_id, {}).keys())

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self._user_connections and len(self._user_connections[user_id]) > 0


# Singleton instance
chat_manager = ConnectionManager()
