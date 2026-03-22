"""Integration tests for the assistant API endpoints.

These tests use the FastAPI test client and mock the Ollama LLM backend
so they can run without a real Ollama service.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.assistant.ollama_client import OllamaClient
from app.models import UserRole
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
