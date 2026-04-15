"""Tests for the AI assistant conversation manager — CRUD + message history."""

import json

import pytest

from app.assistant.conversation import ConversationManager
from app.models import UserRole
from tests.factories import create_user

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conv_user(db):
    """A user for conversation tests."""
    return create_user(
        db,
        email="convuser@example.com",
        username="convuser",
        full_name="Conv User",
        plain_password="pass123",
        role=UserRole.EDITOR,
        is_active=True,
    )


@pytest.fixture
def mgr(db):
    """A ConversationManager backed by the test DB session."""
    return ConversationManager(db)


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------


class TestConversationCRUD:
    def test_create_conversation(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, tenant_id=None, title="Hello")
        assert conv.id is not None
        assert conv.title == "Hello"
        assert conv.user_id == conv_user.id

    def test_get_conversation_by_owner(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Test")
        found = mgr.get_conversation(conv.id, conv_user.id)
        assert found is not None
        assert found.id == conv.id

    def test_get_conversation_wrong_owner_returns_none(self, mgr, conv_user, db):
        conv = mgr.create_conversation(conv_user.id, None, "Test")
        other_user = create_user(
            db,
            email="other@example.com",
            username="other",
            full_name="Other",
            plain_password="pass123",
            role=UserRole.EDITOR,
            is_active=True,
        )
        assert mgr.get_conversation(conv.id, other_user.id) is None

    def test_list_conversations(self, mgr, conv_user):
        mgr.create_conversation(conv_user.id, None, "First")
        mgr.create_conversation(conv_user.id, None, "Second")
        convs = mgr.list_conversations(conv_user.id)
        assert len(convs) == 2

    def test_list_conversations_excludes_archived(self, mgr, conv_user, db):
        conv = mgr.create_conversation(conv_user.id, None, "Archived")
        conv.is_archived = True
        db.commit()
        convs = mgr.list_conversations(conv_user.id)
        assert len(convs) == 0

    def test_list_conversations_pagination(self, mgr, conv_user):
        for i in range(5):
            mgr.create_conversation(conv_user.id, None, f"Conv {i}")
        page = mgr.list_conversations(conv_user.id, limit=2, offset=0)
        assert len(page) == 2
        page2 = mgr.list_conversations(conv_user.id, limit=2, offset=2)
        assert len(page2) == 2

    def test_delete_conversation(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Delete Me")
        assert mgr.delete_conversation(conv.id, conv_user.id) is True
        assert mgr.get_conversation(conv.id, conv_user.id) is None

    def test_delete_nonexistent_returns_false(self, mgr, conv_user):
        assert mgr.delete_conversation(99999, conv_user.id) is False

    def test_update_title(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Old Title")
        mgr.update_title(conv.id, "New Title")
        updated = mgr.get_conversation(conv.id, conv_user.id)
        assert updated.title == "New Title"

    def test_title_truncation(self, mgr, conv_user):
        long_title = "A" * 200
        conv = mgr.create_conversation(conv_user.id, None, long_title)
        assert len(conv.title) <= 100

    def test_create_conversation_sanitizes_html_title(self, mgr, conv_user):
        conv = mgr.create_conversation(
            conv_user.id,
            None,
            '<img src=x onerror="alert(1)"> Hello <script>alert(2)</script>',
        )
        assert conv.title == "Hello"

    def test_update_title_sanitizes_html(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Old Title")
        updated = mgr.update_title(
            conv.id,
            "<b>Renamed</b> <script>alert(1)</script> Chat",
        )
        assert updated is not None
        assert updated.title == "Renamed Chat"


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class TestMessages:
    def test_add_and_get_messages(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        mgr.add_message(conv.id, "user", "Hello")
        mgr.add_message(conv.id, "assistant", "Hi there!")
        msgs = mgr.get_messages(conv.id)
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "Hello"
        assert msgs[1].role == "assistant"

    def test_add_message_with_tool_calls(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        tool_calls = [{"id": "tc1", "name": "list_users", "arguments": {}}]
        msg = mgr.add_message(conv.id, "assistant", "Calling tool", tool_calls=tool_calls)
        assert msg.tool_calls is not None
        parsed = json.loads(msg.tool_calls)
        assert parsed[0]["name"] == "list_users"

    def test_add_message_with_tool_result(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        msg = mgr.add_message(
            conv.id,
            "tool",
            "Found 5 users",
            tool_call_id="tc1",
            tool_name="list_users",
        )
        assert msg.tool_call_id == "tc1"
        assert msg.tool_name == "list_users"

    def test_message_count(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        assert mgr.get_message_count(conv.id) == 0
        mgr.add_message(conv.id, "user", "msg1")
        mgr.add_message(conv.id, "assistant", "msg2")
        assert mgr.get_message_count(conv.id) == 2

    def test_message_limit(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        for i in range(10):
            mgr.add_message(conv.id, "user", f"msg {i}")
        msgs = mgr.get_messages(conv.id, limit=3)
        assert len(msgs) == 3


# ---------------------------------------------------------------------------
# Message history building
# ---------------------------------------------------------------------------


class TestBuildMessageHistory:
    def test_basic_history(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        mgr.add_message(conv.id, "user", "Hello")
        mgr.add_message(conv.id, "assistant", "Hi")
        history = mgr.build_message_history(conv.id)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi"}

    def test_history_with_tool_calls(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        tool_calls = [{"id": "tc1", "name": "list_users", "arguments": {}}]
        mgr.add_message(conv.id, "assistant", "", tool_calls=tool_calls)
        history = mgr.build_message_history(conv.id)
        assert "tool_calls" in history[0]
        assert history[0]["tool_calls"][0]["name"] == "list_users"

    def test_history_with_tool_result(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Chat")
        mgr.add_message(conv.id, "tool", "result data", tool_call_id="tc1")
        history = mgr.build_message_history(conv.id)
        assert history[0]["role"] == "tool"
        assert history[0]["tool_call_id"] == "tc1"

    def test_empty_conversation_history(self, mgr, conv_user):
        conv = mgr.create_conversation(conv_user.id, None, "Empty")
        assert mgr.build_message_history(conv.id) == []


# ---------------------------------------------------------------------------
# Title generation
# ---------------------------------------------------------------------------


class TestTitleGeneration:
    def test_short_message(self):
        assert ConversationManager.generate_title_from_message("Hello") == "Hello"

    def test_long_message_truncated(self):
        long_msg = "A" * 200
        title = ConversationManager.generate_title_from_message(long_msg)
        assert len(title) <= 100
        assert title.endswith("…")

    def test_multiline_uses_first_line(self):
        title = ConversationManager.generate_title_from_message("First line\nSecond line")
        assert title == "First line"

    def test_whitespace_stripped(self):
        title = ConversationManager.generate_title_from_message("  Hello  \n")
        assert title == "Hello"

    def test_html_and_script_blocks_are_removed(self):
        title = ConversationManager.generate_title_from_message(
            '<script>alert(1)</script><b>Hello</b> <img src="x" onerror="alert(2)">',
        )
        assert title == "Hello"
