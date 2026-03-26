from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

from app.models import (
    SupportTicket,
    SupportTicketMessage,
    SupportTicketPriority,
    SupportTicketStatus,
    UserRole,
)
from app.ws import support_ws
from tests.factories import create_tenant, create_user


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _DummyWebSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, payload: str) -> None:
        self.sent.append(payload)


def test_support_ws_send_message_sanitizes_before_storage_and_broadcast(db, monkeypatch):
    tenant = create_tenant(db, name="Support WS Tenant", slug="support-ws-tenant")
    customer = create_user(
        db,
        username="support_ws_customer",
        full_name="Support WS Customer",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    agent = create_user(
        db,
        username="support_ws_agent",
        full_name="Support WS Agent",
        role=UserRole.MANAGER,
        tenant_id=tenant.id,
    )
    ticket = SupportTicket(
        customer_id=customer.id,
        subject="Support WS Ticket",
        status=SupportTicketStatus.OPEN,
        priority=SupportTicketPriority.NORMAL,
        tenant_id=tenant.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    broadcast = AsyncMock()
    monkeypatch.setattr(support_ws.chat_manager, "broadcast_to_ticket", broadcast)

    malicious_content = (
        '<img src="https://example.com/pixel.png" onerror="alert(1)">'
        '<script>alert(2)</script>'
        '<a href="javascript:alert(3)">bad</a>'
        '<p>Hello</p>'
    )

    _run(
        support_ws._handle_send_message(
            _DummyWebSocket(),
            agent,
            {"ticket_id": ticket.id, "content": malicious_content, "is_internal_note": False},
            db,
        )
    )

    stored_message = (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .one()
    )
    assert stored_message.content == '<img src="https://example.com/pixel.png">alert(2)<a>bad</a><p>Hello</p>'
    assert "<script" not in stored_message.content
    assert "onerror" not in stored_message.content
    assert "javascript:" not in stored_message.content

    broadcast.assert_awaited_once()
    assert broadcast.await_args.args[0] == ticket.id
    assert broadcast.await_args.args[1] == "new_message"
    assert broadcast.await_args.args[2]["content"] == stored_message.content


def test_support_ws_rejects_message_that_becomes_empty_after_sanitization(db):
    tenant = create_tenant(db, name="Support WS Empty Tenant", slug="support-ws-empty")
    customer = create_user(
        db,
        username="support_ws_empty_customer",
        full_name="Support WS Empty Customer",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    agent = create_user(
        db,
        username="support_ws_empty_agent",
        full_name="Support WS Empty Agent",
        role=UserRole.MANAGER,
        tenant_id=tenant.id,
    )
    ticket = SupportTicket(
        customer_id=customer.id,
        subject="Support WS Empty Ticket",
        status=SupportTicketStatus.OPEN,
        priority=SupportTicketPriority.NORMAL,
        tenant_id=tenant.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    websocket = _DummyWebSocket()

    _run(
        support_ws._handle_send_message(
            websocket,
            agent,
            {
                "ticket_id": ticket.id,
                "content": '<iframe src="https://evil.test/embed"></iframe>',
                "is_internal_note": False,
            },
            db,
        )
    )

    assert (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .count()
        == 0
    )
    assert len(websocket.sent) == 1
    payload = json.loads(websocket.sent[0])
    assert payload == {
        "event": "error",
        "data": {"message": "content is empty after sanitization"},
    }
