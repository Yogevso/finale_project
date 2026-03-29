from __future__ import annotations

import json
import time

from app.models import SupportTicket, SupportTicketPriority, SupportTicketStatus
from app.services.chat_service import ChatService
from app.ws.manager import chat_manager


def _bearer_token(headers: dict[str, str]) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def _wait_for(predicate, timeout: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _reset_manager_state() -> None:
    chat_manager._chat_connections.clear()
    chat_manager._support_connections.clear()
    chat_manager._user_connections.clear()


def test_chat_websocket_registers_authenticated_user(client, db, auth_headers, test_user, test_manager):
    _reset_manager_state()
    chat = ChatService(db).create_direct_chat(test_user, test_manager.id)
    token = _bearer_token(auth_headers)

    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_text(json.dumps({"event": "authenticate", "data": {"token": token}}))

        assert _wait_for(lambda: test_user.id in chat_manager.get_online_users_in_chat(chat.id))
        assert chat_manager.is_user_online(test_user.id) is True

    assert _wait_for(lambda: not chat_manager.is_user_online(test_user.id))


def test_support_websocket_registers_authenticated_agent(client, db, manager_headers, test_user, test_manager):
    _reset_manager_state()
    ticket = SupportTicket(
        customer_id=test_user.id,
        subject="Support WS registration",
        status=SupportTicketStatus.OPEN,
        priority=SupportTicketPriority.NORMAL,
        tenant_id=test_manager.tenant_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    token = _bearer_token(manager_headers)

    with client.websocket_connect("/ws/support") as websocket:
        websocket.send_text(json.dumps({"event": "authenticate", "data": {"token": token}}))

        assert _wait_for(lambda: test_manager.id in chat_manager.get_online_users_in_ticket(ticket.id))
        assert chat_manager.is_user_online(test_manager.id) is True

    assert _wait_for(lambda: not chat_manager.is_user_online(test_manager.id))
