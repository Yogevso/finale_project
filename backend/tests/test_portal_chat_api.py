"""Portal chat API tests for customer-visible conversations."""

from __future__ import annotations

from app.models import UserRole
from app.services.chat_service import ChatService
from tests.factories import create_user


def test_customer_can_list_and_reply_to_existing_chat(client, db, test_tenant, customer_headers, test_customer):
    internal_user = create_user(
        db,
        email="portal-chat-editor@example.com",
        username="portal_chat_editor",
        full_name="Portal Chat Editor",
        plain_password="PortalChat1!",
        role=UserRole.EDITOR,
        tenant_id=test_tenant.id,
    )
    chat = ChatService(db).create_direct_chat(test_customer, internal_user.id)

    list_response = client.get("/api/v1/portal/chats", headers=customer_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["chat"]["id"] == chat.id
    assert list_payload["items"][0]["display_name"] == "Portal Chat Editor"

    detail_response = client.get(f"/api/v1/portal/chats/{chat.id}", headers=customer_headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == chat.id
    assert {participant["user_id"] for participant in detail_payload["participants"]} == {
        test_customer.id,
        internal_user.id,
    }

    send_response = client.post(
        f"/api/v1/portal/chats/{chat.id}/messages",
        headers=customer_headers,
        json={"content": "Customer follow-up"},
    )
    assert send_response.status_code == 201
    send_payload = send_response.json()
    assert send_payload["chat_id"] == chat.id
    assert send_payload["sender_id"] == test_customer.id
    assert send_payload["content"] == "Customer follow-up"

    history_response = client.get(f"/api/v1/portal/chats/{chat.id}/messages", headers=customer_headers)
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["items"][0]["content"] == "Customer follow-up"
    assert history_payload["items"][0]["sender_full_name"] == test_customer.full_name


def test_customer_cannot_access_foreign_chat(client, db, test_tenant_2, customer_headers):
    foreign_customer = create_user(
        db,
        email="foreign-portal-customer@example.com",
        username="foreign_portal_customer",
        full_name="Foreign Portal Customer",
        plain_password="ForeignPortal1!",
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant_2.id,
    )
    foreign_internal = create_user(
        db,
        email="foreign-portal-editor@example.com",
        username="foreign_portal_editor",
        full_name="Foreign Portal Editor",
        plain_password="ForeignEditor1!",
        role=UserRole.EDITOR,
        tenant_id=test_tenant_2.id,
    )
    foreign_chat = ChatService(db).create_direct_chat(foreign_customer, foreign_internal.id)

    response = client.get(f"/api/v1/portal/chats/{foreign_chat.id}", headers=customer_headers)
    assert response.status_code == 404


def test_customer_can_mark_portal_chat_as_read(client, db, test_tenant, customer_headers, test_customer):
    internal_user = create_user(
        db,
        email="portal-chat-manager@example.com",
        username="portal_chat_manager",
        full_name="Portal Chat Manager",
        plain_password="PortalChat2!",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
    )
    chat = ChatService(db).create_direct_chat(test_customer, internal_user.id)
    ChatService(db).send_message(chat.id, internal_user, "Please review this update")

    response = client.post(f"/api/v1/portal/chats/{chat.id}/read", headers=customer_headers)
    assert response.status_code == 204

    refreshed = client.get("/api/v1/portal/chats", headers=customer_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["items"][0]["unread_count"] == 0
