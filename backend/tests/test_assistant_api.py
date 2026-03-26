"""Integration tests for the assistant API endpoints.

These tests use the FastAPI test client and mock the Ollama LLM backend
so they can run without a real Ollama service.
"""

import io
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.management.assistant import _stream_assistant_events
from app.assistant.ollama_client import OllamaClient
from app.config import settings
from app.models import UserRole
from app.services.distributed_rate_limit_service import DistributedRateLimitService
from tests.factories import create_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sysadmin(db):
    return create_user(
        db,
        email="ai_sysadmin@example.com",
        username="ai_sysadmin",
        full_name="AI SysAdmin",
        plain_password="sysadmin123",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
    )


@pytest.fixture
def sysadmin_headers(client, sysadmin):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ai_sysadmin", "password": "sysadmin123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def viewer_user(db, default_tenant):
    return create_user(
        db,
        email="ai_viewer@example.com",
        username="ai_viewer",
        full_name="AI Viewer",
        plain_password="viewer123",
        role=UserRole.VIEWER,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def viewer_headers(client, viewer_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ai_viewer", "password": "viewer123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# /assistant/health
# ---------------------------------------------------------------------------

class TestAssistantHealth:
    def test_health_when_enabled(self, client, sysadmin_headers):
        with patch.object(OllamaClient, 'is_healthy', return_value=True):
            resp = client.get("/api/v1/assistant/health", headers=sysadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["ollama_healthy"] is True

    def test_health_when_ollama_down(self, client, sysadmin_headers):
        with patch.object(OllamaClient, 'is_healthy', return_value=False):
            resp = client.get("/api/v1/assistant/health", headers=sysadmin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "unavailable"

    def test_health_requires_auth(self, client):
        resp = client.get("/api/v1/assistant/health")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /assistant/tools
# ---------------------------------------------------------------------------

class TestAssistantTools:
    def test_list_tools_for_sysadmin(self, client, sysadmin_headers):
        resp = client.get("/api/v1/assistant/tools", headers=sysadmin_headers)
        assert resp.status_code == 200
        tools = resp.json()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # SysAdmin should see all tools
        names = {t["name"] for t in tools}
        assert "list_users" in names
        assert "get_site_settings" in names
        assert "get_my_profile" in names

    def test_list_tools_for_viewer(self, client, viewer_headers):
        resp = client.get("/api/v1/assistant/tools", headers=viewer_headers)
        assert resp.status_code == 200
        tools = resp.json()
        names = {t["name"] for t in tools}
        # Viewer should NOT see admin tools
        assert "list_users" not in names
        assert "create_user" not in names
        # But should see info tools
        assert "get_my_profile" in names

    def test_tools_have_expected_fields(self, client, sysadmin_headers):
        resp = client.get("/api/v1/assistant/tools", headers=sysadmin_headers)
        for tool in resp.json():
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_tools_requires_auth(self, client):
        resp = client.get("/api/v1/assistant/tools")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /assistant/conversations CRUD
# ---------------------------------------------------------------------------

class TestConversationsCRUD:
    def test_create_conversation(self, client, sysadmin_headers):
        resp = client.post(
            "/api/v1/assistant/conversations?title=Test%20Chat",
            headers=sysadmin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert data["message_count"] == 0
        assert "id" in data

    def test_create_conversation_sanitizes_title(self, client, sysadmin_headers):
        resp = client.post(
            "/api/v1/assistant/conversations",
            headers=sysadmin_headers,
            params={"title": '<img src=x onerror="alert(1)"> <b>Safe</b>'},
        )

        assert resp.status_code == 201
        assert resp.json()["title"] == "Safe"

    def test_list_conversations(self, client, sysadmin_headers):
        # Create a couple
        client.post("/api/v1/assistant/conversations?title=Chat1", headers=sysadmin_headers)
        client.post("/api/v1/assistant/conversations?title=Chat2", headers=sysadmin_headers)

        resp = client.get("/api/v1/assistant/conversations", headers=sysadmin_headers)
        assert resp.status_code == 200
        convs = resp.json()
        assert len(convs) >= 2

    def test_get_conversation_detail(self, client, sysadmin_headers):
        create_resp = client.post(
            "/api/v1/assistant/conversations?title=Detail",
            headers=sysadmin_headers,
        )
        conv_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=sysadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert "messages" in data

    def test_get_conversation_not_found(self, client, sysadmin_headers):
        resp = client.get("/api/v1/assistant/conversations/99999", headers=sysadmin_headers)
        assert resp.status_code == 404

    def test_rename_conversation(self, client, sysadmin_headers):
        create_resp = client.post(
            "/api/v1/assistant/conversations?title=Old",
            headers=sysadmin_headers,
        )
        conv_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/assistant/conversations/{conv_id}?title=New%20Title",
            headers=sysadmin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_rename_conversation_returns_sanitized_title(self, client, sysadmin_headers):
        create_resp = client.post(
            "/api/v1/assistant/conversations?title=Old",
            headers=sysadmin_headers,
        )
        conv_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/assistant/conversations/{conv_id}",
            headers=sysadmin_headers,
            params={"title": '<script>alert(1)</script><b>Renamed</b> Chat'},
        )

        assert resp.status_code == 200
        assert resp.json()["title"] == "Renamed Chat"

    def test_delete_conversation(self, client, sysadmin_headers):
        create_resp = client.post(
            "/api/v1/assistant/conversations?title=Delete%20Me",
            headers=sysadmin_headers,
        )
        conv_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/assistant/conversations/{conv_id}", headers=sysadmin_headers)
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=sysadmin_headers)
        assert resp.status_code == 404

    def test_conversation_isolation_between_users(self, client, sysadmin_headers, viewer_headers):
        """One user cannot see another's conversations."""
        create_resp = client.post(
            "/api/v1/assistant/conversations?title=Private",
            headers=sysadmin_headers,
        )
        conv_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=viewer_headers)
        assert resp.status_code == 404

    def test_conversations_require_auth(self, client):
        resp = client.get("/api/v1/assistant/conversations")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /assistant/chat — SSE streaming
# ---------------------------------------------------------------------------

class TestAssistantChat:
    def test_chat_requires_auth(self, client):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code in (401, 403)

    def test_chat_empty_message_rejected(self, client, sysadmin_headers):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={"message": ""},
            headers=sysadmin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("field_name", ["file_ids", "document_ids"])
    def test_chat_rejects_more_than_three_context_ids(
        self, client, sysadmin_headers, field_name
    ):
        payload = {"message": "Hello", field_name: [1, 2, 3, 4]}

        resp = client.post(
            "/api/v1/assistant/chat",
            json=payload,
            headers=sysadmin_headers,
        )

        assert resp.status_code == 422

    def test_chat_returns_sse_stream(self, client, sysadmin_headers):
        """Chat endpoint should return SSE content type."""
        async def mock_chat_stream(**kwargs):
            yield {"message": {"content": "Hi"}}

        with patch.object(OllamaClient, 'chat_stream', side_effect=mock_chat_stream), \
             patch.object(OllamaClient, 'chat', return_value={"message": {"content": "Hi", "tool_calls": None}}):
            resp = client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hello"},
                headers=sysadmin_headers,
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_chat_rate_limit_uses_shared_service(self, client, sysadmin_headers, monkeypatch):
        class StubEngine:
            async def chat(self, **kwargs):
                yield {"event": "message", "data": {"content": "ok"}}

        DistributedRateLimitService.reset()
        monkeypatch.setattr(settings, "ASSISTANT_RATE_LIMIT_PER_MINUTE", 1)
        monkeypatch.setattr("app.api.management.assistant._build_engine", lambda *_args: StubEngine())

        first = client.post(
            "/api/v1/assistant/chat",
            json={"message": "first"},
            headers=sysadmin_headers,
        )
        second = client.post(
            "/api/v1/assistant/chat",
            json={"message": "second"},
            headers=sysadmin_headers,
        )

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["Retry-After"] == "60"

    def test_stream_helper_cancels_producer_when_client_disconnects(self):
        class DisconnectingRequest:
            async def is_disconnected(self):
                return True

        async def run_case():
            queue: asyncio.Queue[dict | None] = asyncio.Queue()
            done = asyncio.Event()
            prod_task = asyncio.create_task(asyncio.sleep(60))
            hb_task = asyncio.create_task(asyncio.sleep(60))

            chunks = [
                chunk
                async for chunk in _stream_assistant_events(
                    request=DisconnectingRequest(),
                    queue=queue,
                    done=done,
                    prod_task=prod_task,
                    hb_task=hb_task,
                )
            ]

            assert chunks == []
            assert done.is_set() is True
            assert prod_task.cancelled() is True
            assert hb_task.cancelled() is True

        asyncio.run(run_case())


class TestAssistantUploads:
    def test_upload_rejects_malware(self, client, sysadmin_headers, monkeypatch):
        def block_upload(*_args, **_kwargs):
            raise ValueError("Upload blocked: malware detected in 'dangerous.txt'.")

        monkeypatch.setattr(
            "app.assistant.file_handler.scan_upload_bytes",
            block_upload,
        )

        response = client.post(
            "/api/v1/assistant/upload",
            headers=sysadmin_headers,
            files={"file": ("dangerous.txt", io.BytesIO(b"not-clean"), "text/plain")},
        )

        assert response.status_code == 400
        assert "malware detected" in response.json()["detail"].lower()
