"""Support REST message realtime tests."""

from __future__ import annotations

import asyncio

from app.config import settings
from app.models import UserRole
from app.services.support_service import SupportTicketService
from tests.factories import create_tenant, create_user


class _FakeStorageBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.counter = 0

    def upload(self, file_data, filename: str, content_type: str) -> str:
        self.counter += 1
        key = f"support-{self.counter}-{filename}"
        self.files[key] = file_data.read()
        return key

    def download(self, storage_key: str) -> bytes:
        if storage_key not in self.files:
            raise FileNotFoundError(storage_key)
        return self.files[storage_key]

    def delete(self, storage_key: str) -> bool:
        self.files.pop(storage_key, None)
        return True


def _login_headers(client, *, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_management_rest_message_triggers_support_broadcast(
    client,
    db,
    admin_headers,
    test_admin,
    default_tenant,
    monkeypatch,
):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    customer = create_user(
        db,
        email="support-rest-customer@example.com",
        username="support_rest_customer",
        full_name="Support Rest Customer",
        plain_password="SupportCust1!",
        role=UserRole.CUSTOMER,
        tenant_id=default_tenant.id,
    )
    ticket = SupportTicketService(db).create_ticket(customer, "REST support", "Need help")
    broadcast_calls: list[tuple[int, int, int]] = []

    async def _capture_broadcast(self, *, ticket, msg, sender):
        broadcast_calls.append((ticket.id, msg.id, sender.id))

    monkeypatch.setattr(
        "app.services.support_service.SupportTicketService.broadcast_message_event",
        _capture_broadcast,
    )
    monkeypatch.setattr(
        "app.api.management.support.run_async_task",
        lambda coro: asyncio.get_running_loop().create_task(coro),
    )

    response = client.post(
        f"/api/v1/support/tickets/{ticket.id}/messages",
        headers=admin_headers,
        json={"content": "REST agent reply", "is_internal_note": False},
    )

    assert response.status_code == 201
    assert broadcast_calls == [(ticket.id, response.json()["id"], test_admin.id)]


def test_management_multipart_message_returns_attachment_metadata_and_downloads(
    client,
    db,
    admin_headers,
    default_tenant,
    monkeypatch,
):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    fake_storage = _FakeStorageBackend()
    monkeypatch.setattr("app.services.support_service.get_storage_backend", lambda: fake_storage)

    customer = create_user(
        db,
        email="support-rest-attach@example.com",
        username="support_rest_attach",
        full_name="Support Rest Attach",
        plain_password="SupportAttach1!",
        role=UserRole.CUSTOMER,
        tenant_id=default_tenant.id,
    )
    customer_headers = _login_headers(
        client,
        username="support_rest_attach",
        password="SupportAttach1!",
    )
    ticket = SupportTicketService(db).create_ticket(customer, "REST attachment", "Need help")

    response = client.post(
        f"/api/v1/support/tickets/{ticket.id}/messages",
        headers=admin_headers,
        data={"content": "Attached log", "is_internal_note": "false"},
        files={"file": ("evidence.txt", b"log-data", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["file_name"] == "evidence.txt"
    assert payload["file_size"] == len(b"log-data")
    assert payload["file_mime_type"] == "text/plain"
    assert payload["file_url"] == (
        f"/api/v1/support/tickets/{ticket.id}/messages/{payload['id']}/attachment"
    )

    download = client.get(payload["file_url"], headers=customer_headers)
    assert download.status_code == 200
    assert download.content == b"log-data"


def test_portal_rest_message_triggers_support_broadcast(
    client,
    db,
    monkeypatch,
):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    tenant = create_tenant(db, name="Portal Support Tenant", slug="portal-support-tenant")
    customer = create_user(
        db,
        email="portal-rest-customer@example.com",
        username="portal_rest_customer",
        full_name="Portal Rest Customer",
        plain_password="PortalCust1!",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    customer_headers = _login_headers(
        client,
        username="portal_rest_customer",
        password="PortalCust1!",
    )
    ticket = SupportTicketService(db).create_ticket(customer, "Portal support", "Need help")
    broadcast_calls: list[tuple[int, int, int]] = []

    async def _capture_broadcast(self, *, ticket, msg, sender):
        broadcast_calls.append((ticket.id, msg.id, sender.id))

    monkeypatch.setattr(
        "app.services.support_service.SupportTicketService.broadcast_message_event",
        _capture_broadcast,
    )
    monkeypatch.setattr(
        "app.api.portal.support.run_async_task",
        lambda coro: asyncio.get_running_loop().create_task(coro),
    )

    response = client.post(
        f"/api/v1/portal/support/tickets/{ticket.id}/messages",
        headers=customer_headers,
        json={"content": "Portal follow-up", "is_internal_note": False},
    )

    assert response.status_code == 201
    assert broadcast_calls == [(ticket.id, response.json()["id"], customer.id)]


def test_portal_multipart_message_returns_attachment_metadata(
    client,
    db,
    monkeypatch,
):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    fake_storage = _FakeStorageBackend()
    monkeypatch.setattr("app.services.support_service.get_storage_backend", lambda: fake_storage)

    tenant = create_tenant(db, name="Portal Attach Tenant", slug="portal-attach-tenant")
    customer = create_user(
        db,
        email="portal-rest-attach@example.com",
        username="portal_rest_attach",
        full_name="Portal Rest Attach",
        plain_password="PortalAttach1!",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    customer_headers = _login_headers(
        client,
        username="portal_rest_attach",
        password="PortalAttach1!",
    )
    ticket = SupportTicketService(db).create_ticket(customer, "Portal attachment", "Need help")

    response = client.post(
        f"/api/v1/portal/support/tickets/{ticket.id}/messages",
        headers=customer_headers,
        data={"content": "Screenshot attached"},
        files={"file": ("notes.txt", b"plain-text-note", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["file_name"] == "notes.txt"
    assert payload["file_size"] == len(b"plain-text-note")
    assert payload["file_mime_type"] == "text/plain"
    assert payload["file_url"] == (
        f"/api/v1/support/tickets/{ticket.id}/messages/{payload['id']}/attachment"
    )

    download = client.get(payload["file_url"], headers=customer_headers)
    assert download.status_code == 200
    assert download.content == b"plain-text-note"
