"""Tests for the AI assistant engine — tool routing, tool-call loop, streaming."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.assistant.engine import AssistantEngine, _select_relevant_tools
from app.assistant.ollama_client import OllamaClient
from app.assistant.tools.registry import ToolRegistry
from app.assistant.conversation import ConversationManager
from app.models import UserRole


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _collect_events(async_gen):
    events = []
    async for event in async_gen:
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role=UserRole.SYSTEM_ADMIN, user_id=1, tenant_id=None):
    user = MagicMock()
    user.id = user_id
    user.username = "testuser"
    user.full_name = "Test User"
    user.role = role
    user.tenant_id = tenant_id
    return user


def _make_tool_def(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Tool {name}",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }


ALL_TOOL_NAMES = [
    "list_users", "get_user", "create_user", "deactivate_user", "change_user_role",
    "search_documents", "get_document", "create_document", "edit_document",
    "delete_document", "search_public_documents", "get_document_content",
    "get_site_settings", "update_site_setting",
    "create_announcement", "list_announcements",
    "list_topics", "create_topic",
    "list_tenants", "get_tenant", "update_tenant",
    "create_support_ticket", "list_my_tickets", "get_ticket_details",
    "submit_feedback", "get_my_feedback",
    "get_my_profile", "get_my_permissions", "get_help",
]

ALL_TOOL_DEFS = [_make_tool_def(n) for n in ALL_TOOL_NAMES]


# ---------------------------------------------------------------------------
# Tool routing — _select_relevant_tools
# ---------------------------------------------------------------------------

class TestSelectRelevantTools:
    def test_user_keywords_select_user_tools(self):
        selected = _select_relevant_tools("Show me all users", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "list_users" in names
        assert "get_user" in names

    def test_document_keywords_select_doc_tools(self):
        selected = _select_relevant_tools("Find documents about API", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "search_documents" in names
        assert "get_document" in names

    def test_settings_keywords(self):
        selected = _select_relevant_tools("Show system settings", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "get_site_settings" in names

    def test_who_am_i_selects_profile(self):
        selected = _select_relevant_tools("Who am I?", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "get_my_profile" in names

    def test_help_selects_info_tools(self):
        selected = _select_relevant_tools("Help me", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "get_help" in names

    def test_info_tools_always_included(self):
        """Info group should always be included regardless of keywords."""
        selected = _select_relevant_tools("list all tenants", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "get_my_profile" in names  # info is always included

    def test_no_keyword_match_includes_defaults(self):
        """When nothing specific matches, include users+documents+settings+info."""
        selected = _select_relevant_tools("xyzzy blorp", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "list_users" in names
        assert "search_documents" in names
        assert "get_site_settings" in names

    def test_support_keywords(self):
        selected = _select_relevant_tools("create a support ticket", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "create_support_ticket" in names

    def test_feedback_keywords(self):
        selected = _select_relevant_tools("submit feedback", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "submit_feedback" in names

    def test_tenant_keywords(self):
        selected = _select_relevant_tools("list all tenants", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "list_tenants" in names

    def test_announcement_keywords(self):
        selected = _select_relevant_tools("create an announcement", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "create_announcement" in names

    def test_topic_keywords(self):
        selected = _select_relevant_tools("list categories", ALL_TOOL_DEFS)
        names = {t["function"]["name"] for t in selected}
        assert "list_topics" in names

    def test_fewer_tools_than_total(self):
        """Smart routing should return fewer tools than the full set."""
        selected = _select_relevant_tools("list users", ALL_TOOL_DEFS)
        assert len(selected) < len(ALL_TOOL_DEFS)

    def test_empty_tools_returns_empty(self):
        selected = _select_relevant_tools("list users", [])
        assert selected == []


# ---------------------------------------------------------------------------
# Engine chat — no tools scenario
# ---------------------------------------------------------------------------

class TestEngineNoTools:
    def test_no_tools_streams_text(self):
        """When registry has no tools for user, engine should stream text directly."""
        ollama = AsyncMock(spec=OllamaClient)
        registry = MagicMock(spec=ToolRegistry)
        conv_mgr = MagicMock(spec=ConversationManager)

        registry.get_ollama_tools.return_value = []

        mock_conv = MagicMock()
        mock_conv.id = 1
        conv_mgr.create_conversation.return_value = mock_conv
        conv_mgr.build_message_history.return_value = []

        async def mock_stream(**kwargs):
            for word in ["Hello", " world"]:
                yield {"message": {"content": word}}
        ollama.chat_stream = mock_stream

        engine = AssistantEngine(ollama, registry, conv_mgr)
        user = _make_user()

        events = _run(_collect_events(engine.chat(user, None, "Hi", None, MagicMock())))

        event_types = [e["event"] for e in events]
        assert "conversation_id" in event_types
        assert "token" in event_types
        assert "done" in event_types

        tokens = [e["data"] for e in events if e["event"] == "token"]
        assert "".join(tokens) == "Hello world"


# ---------------------------------------------------------------------------
# Engine chat — tool calling scenario
# ---------------------------------------------------------------------------

class TestEngineToolCalling:
    def test_tool_call_flow(self):
        """Engine calls tool, then streams summary."""
        from app.assistant.schemas import ToolResult

        ollama = AsyncMock(spec=OllamaClient)
        reg = MagicMock(spec=ToolRegistry)
        conv_mgr = MagicMock(spec=ConversationManager)

        reg.get_ollama_tools.return_value = [_make_tool_def("list_users")]
        reg.get.return_value = None  # No confirmation required

        mock_conv = MagicMock()
        mock_conv.id = 1
        conv_mgr.create_conversation.return_value = mock_conv
        conv_mgr.build_message_history.return_value = []

        ollama.chat.return_value = {
            "message": {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "list_users", "arguments": {}}}
                ],
            }
        }

        reg.execute_tool.return_value = ToolResult(
            tool_call_id="", name="list_users", success=True,
            result="Found 3 users:\n- alice\n- bob\n- carol",
        )

        async def mock_stream(**kwargs):
            yield {"message": {"content": "Here are 3 users"}}
        ollama.chat_stream = mock_stream

        engine = AssistantEngine(ollama, reg, conv_mgr)
        user = _make_user()
        db = MagicMock()

        events = _run(_collect_events(engine.chat(user, None, "List all users", None, db)))

        event_types = [e["event"] for e in events]
        assert "conversation_id" in event_types
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "token" in event_types
        assert "done" in event_types

        tool_call_events = [e for e in events if e["event"] == "tool_call"]
        assert tool_call_events[0]["data"]["name"] == "list_users"

        tool_result_events = [e for e in events if e["event"] == "tool_result"]
        assert tool_result_events[0]["data"]["success"] is True

    def test_existing_conversation(self):
        """Engine uses existing conversation when ID is provided."""
        ollama = AsyncMock(spec=OllamaClient)
        reg = MagicMock(spec=ToolRegistry)
        conv_mgr = MagicMock(spec=ConversationManager)

        reg.get_ollama_tools.return_value = []

        mock_conv = MagicMock()
        mock_conv.id = 42
        conv_mgr.get_conversation.return_value = mock_conv
        conv_mgr.build_message_history.return_value = []

        async def mock_stream(**kwargs):
            yield {"message": {"content": "response"}}
        ollama.chat_stream = mock_stream

        engine = AssistantEngine(ollama, reg, conv_mgr)
        user = _make_user()

        events = _run(_collect_events(engine.chat(user, None, "Hi", 42, MagicMock())))

        conv_events = [e for e in events if e["event"] == "conversation_id"]
        assert conv_events[0]["data"] == 42
        conv_mgr.get_conversation.assert_called_once_with(42, user.id)

    def test_conversation_not_found(self):
        """Engine returns error if conversation doesn't exist."""
        ollama = AsyncMock(spec=OllamaClient)
        reg = MagicMock(spec=ToolRegistry)
        conv_mgr = MagicMock(spec=ConversationManager)

        conv_mgr.get_conversation.return_value = None

        engine = AssistantEngine(ollama, reg, conv_mgr)
        user = _make_user()

        events = _run(_collect_events(engine.chat(user, None, "Hi", 999, MagicMock())))

        assert any(e["event"] == "error" for e in events)

    def test_ollama_failure_yields_error(self):
        """Engine yields error when Ollama is unreachable."""
        ollama = AsyncMock(spec=OllamaClient)
        reg = MagicMock(spec=ToolRegistry)
        conv_mgr = MagicMock(spec=ConversationManager)

        reg.get_ollama_tools.return_value = [_make_tool_def("list_users")]

        mock_conv = MagicMock()
        mock_conv.id = 1
        conv_mgr.create_conversation.return_value = mock_conv
        conv_mgr.build_message_history.return_value = []

        ollama.chat.side_effect = Exception("Connection refused")

        engine = AssistantEngine(ollama, reg, conv_mgr)
        user = _make_user()

        events = _run(_collect_events(engine.chat(user, None, "Hi", None, MagicMock())))

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert "unavailable" in error_events[0]["data"]["message"].lower()


# ---------------------------------------------------------------------------
# Engine — audit logging
# ---------------------------------------------------------------------------

class TestAuditLogging:
    def test_log_tool_use(self):
        from app.assistant.schemas import ToolCall, ToolResult
        db = MagicMock()
        user = _make_user()
        tc = ToolCall(id="tc1", name="list_users", arguments={"limit": 10})
        result = ToolResult(
            tool_call_id="tc1", name="list_users",
            success=True, result="Found 3 users",
        )
        AssistantEngine._log_tool_use(db, user, tc, result)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_log_tool_use_handles_db_error(self):
        """Audit log failure should not crash the engine."""
        from app.assistant.schemas import ToolCall, ToolResult
        db = MagicMock()
        db.commit.side_effect = Exception("DB error")
        user = _make_user()
        tc = ToolCall(id="tc1", name="test", arguments={})
        result = ToolResult(tool_call_id="tc1", name="test", success=True, result="ok")
        # Should not raise
        AssistantEngine._log_tool_use(db, user, tc, result)


# ---------------------------------------------------------------------------
# Engine — parse_tool_calls
# ---------------------------------------------------------------------------

class TestParseToolCalls:
    def test_parse_single_tool_call(self):
        raw = [{"function": {"name": "list_users", "arguments": {"limit": 10}}}]
        calls = AssistantEngine._parse_tool_calls(raw)
        assert len(calls) == 1
        assert calls[0].name == "list_users"
        assert calls[0].arguments == {"limit": 10}
        assert calls[0].id  # UUID should be populated

    def test_parse_multiple_tool_calls(self):
        raw = [
            {"function": {"name": "list_users", "arguments": {}}},
            {"function": {"name": "get_user", "arguments": {"user_id": 1}}},
        ]
        calls = AssistantEngine._parse_tool_calls(raw)
        assert len(calls) == 2
        assert calls[0].name == "list_users"
        assert calls[1].name == "get_user"
        # IDs should be unique
        assert calls[0].id != calls[1].id

    def test_parse_empty_list(self):
        assert AssistantEngine._parse_tool_calls([]) == []

    def test_parse_missing_fields_uses_defaults(self):
        raw = [{"function": {}}]
        calls = AssistantEngine._parse_tool_calls(raw)
        assert calls[0].name == ""
        assert calls[0].arguments == {}
