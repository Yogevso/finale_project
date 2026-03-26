"""Chat service tests — X1-049 to X1-053."""

import pytest
from fastapi import HTTPException

from app.models import (
    Chat,
    ChatMessage,
    ChatParticipant,
    ChatParticipantRole,
    ChatType,
    UserRole,
)
from app.services.chat_service import ChatService
from tests.factories import create_tenant, create_user


@pytest.fixture
def tenant(db):
    return create_tenant(db, name="Chat Tenant", slug="chat-tenant")


@pytest.fixture
def tenant_b(db):
    return create_tenant(db, name="Other Tenant", slug="other-tenant")


@pytest.fixture
def editor_a(db, tenant):
    return create_user(
        db, username="editor_a", full_name="Editor A",
        role=UserRole.EDITOR, tenant_id=tenant.id,
    )


@pytest.fixture
def editor_b(db, tenant):
    return create_user(
        db, username="editor_b", full_name="Editor B",
        role=UserRole.EDITOR, tenant_id=tenant.id,
    )


@pytest.fixture
def editor_c(db, tenant):
    return create_user(
        db, username="editor_c", full_name="Editor C",
        role=UserRole.EDITOR, tenant_id=tenant.id,
    )


@pytest.fixture
def foreign_customer(db, tenant_b):
    return create_user(
        db, username="foreign_cust", full_name="Foreign Customer",
        role=UserRole.CUSTOMER, tenant_id=tenant_b.id,
    )


@pytest.fixture
def foreign_system_admin(db, tenant_b):
    return create_user(
        db, username="foreign_sysadmin", full_name="Foreign System Admin",
        role=UserRole.SYSTEM_ADMIN, tenant_id=tenant_b.id,
    )


@pytest.fixture
def svc(db):
    return ChatService(db)


# =====================================================================
# X1-049: create_direct_chat deduplication
# =====================================================================

class TestDirectChatDeduplication:
    """X1-049: Verify same chat returned for A→B and B→A."""

    def test_same_chat_returned_for_reverse_pair(self, svc, editor_a, editor_b):
        chat1 = svc.create_direct_chat(editor_a, editor_b.id)
        chat2 = svc.create_direct_chat(editor_b, editor_a.id)
        assert chat1.id == chat2.id

    def test_direct_chat_has_two_participants(self, db, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        participants = db.query(ChatParticipant).filter_by(chat_id=chat.id).all()
        assert len(participants) == 2
        user_ids = {p.user_id for p in participants}
        assert user_ids == {editor_a.id, editor_b.id}

    def test_cannot_create_chat_with_self(self, svc, editor_a):
        with pytest.raises(HTTPException) as exc:
            svc.create_direct_chat(editor_a, editor_a.id)
        assert exc.value.status_code == 400

    def test_different_pairs_get_different_chats(self, svc, editor_a, editor_b, editor_c):
        chat_ab = svc.create_direct_chat(editor_a, editor_b.id)
        chat_ac = svc.create_direct_chat(editor_a, editor_c.id)
        assert chat_ab.id != chat_ac.id


# =====================================================================
# X1-050: Group chat permissions
# =====================================================================

class TestGroupChatPermissions:
    """X1-050: Only owner can delete, admin can add members."""

    def test_owner_can_delete_group(self, svc, editor_a, editor_b):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        svc.delete_chat(chat.id, editor_a)  # should not raise

    def test_member_cannot_delete_group(self, svc, editor_a, editor_b):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        with pytest.raises(HTTPException) as exc:
            svc.delete_chat(chat.id, editor_b)
        assert exc.value.status_code == 403

    def test_owner_can_add_participant(self, svc, editor_a, editor_b, editor_c):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        p = svc.add_participant(chat.id, editor_a, editor_c.id)
        assert p.user_id == editor_c.id

    def test_member_cannot_add_participant(self, svc, editor_a, editor_b, editor_c):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        with pytest.raises(HTTPException) as exc:
            svc.add_participant(chat.id, editor_b, editor_c.id)
        assert exc.value.status_code == 403

    def test_cannot_remove_owner(self, svc, editor_a, editor_b):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        with pytest.raises(HTTPException) as exc:
            svc.remove_participant(chat.id, editor_a, editor_a.id)
        assert exc.value.status_code == 400

    def test_owner_can_remove_member(self, svc, editor_a, editor_b):
        chat = svc.create_group_chat(editor_a, "Test Group", [editor_b.id])
        svc.remove_participant(chat.id, editor_a, editor_b.id)
        remaining = (
            svc.db.query(ChatParticipant).filter_by(chat_id=chat.id).all()
        )
        assert len(remaining) == 1
        assert remaining[0].user_id == editor_a.id


# =====================================================================
# X1-051: Tenant isolation
# =====================================================================

class TestChatTenantIsolation:
    """X1-051: User cannot access chat from different tenant."""

    def test_cross_tenant_customer_blocked(self, svc, foreign_customer, editor_a):
        """Non-participant from different tenant gets 404 (hides existence)."""
        customer_same = create_user(
            svc.db, username="cust_same", full_name="Same Tenant Customer",
            role=UserRole.CUSTOMER, tenant_id=foreign_customer.tenant_id,
        )
        chat = svc.create_direct_chat(foreign_customer, customer_same.id)
        with pytest.raises(HTTPException) as exc:
            svc._get_chat_with_permission(chat.id, editor_a)
        # Different tenant + not a participant → 404 to hide existence
        assert exc.value.status_code == 404

    def test_cannot_access_other_tenant_chat(self, svc, editor_a, editor_b, foreign_customer):
        """A non-participant from another tenant gets 404."""
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        with pytest.raises(HTTPException) as exc:
            svc._get_chat_with_permission(chat.id, foreign_customer)
        assert exc.value.status_code == 404

    def test_internal_staff_cannot_chat_cross_tenant(self, svc, editor_a, foreign_customer):
        """Cross-tenant direct chats are hidden by tenant-scoped user lookup."""
        with pytest.raises(HTTPException) as exc:
            svc.create_direct_chat(editor_a, foreign_customer.id)
        assert exc.value.status_code == 404

    def test_system_admin_cannot_bypass_cross_tenant_direct_chat(
        self, svc, editor_a, foreign_system_admin
    ):
        with pytest.raises(HTTPException) as exc:
            svc.create_direct_chat(editor_a, foreign_system_admin.id)
        assert exc.value.status_code == 404


# =====================================================================
# X1-052: Message pagination
# =====================================================================

class TestMessagePagination:
    """X1-052: Create 100 messages, verify pagination works correctly."""

    def test_pagination_default_limit(self, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        for i in range(100):
            svc.send_message(chat.id, editor_a, f"Message {i}")

        # Default limit = 50
        page1 = svc.get_chat_history(chat.id, editor_a, limit=50)
        assert len(page1) == 50
        # Messages are ordered DESC so page1[0] is the newest
        assert "Message 99" in page1[0].content

    def test_pagination_with_before_id(self, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        for i in range(100):
            svc.send_message(chat.id, editor_a, f"Message {i}")

        page1 = svc.get_chat_history(chat.id, editor_a, limit=50)
        oldest_in_page1 = page1[-1]  # oldest message in first page

        page2 = svc.get_chat_history(chat.id, editor_a, before_id=oldest_in_page1.id, limit=50)
        assert len(page2) == 50
        # page2 should contain older messages
        assert all(m.id < oldest_in_page1.id for m in page2)

    def test_pagination_no_overlap(self, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        for i in range(100):
            svc.send_message(chat.id, editor_a, f"Message {i}")

        page1 = svc.get_chat_history(chat.id, editor_a, limit=50)
        page2 = svc.get_chat_history(
            chat.id, editor_a, before_id=page1[-1].id, limit=50
        )
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_small_limit(self, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        for i in range(10):
            svc.send_message(chat.id, editor_a, f"Message {i}")

        page = svc.get_chat_history(chat.id, editor_a, limit=3)
        assert len(page) == 3


# =====================================================================
# X1-053: Read receipts
# =====================================================================

class TestReadReceipts:
    """X1-053: Mark as read, verify last_read_at updated."""

    def test_mark_as_read_updates_timestamp(self, db, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        svc.send_message(chat.id, editor_a, "Hello")

        participant = (
            db.query(ChatParticipant)
            .filter_by(chat_id=chat.id, user_id=editor_b.id)
            .first()
        )
        assert participant.last_read_at is None

        svc.mark_as_read(chat.id, editor_b)

        db.refresh(participant)
        assert participant.last_read_at is not None

    def test_unread_count_decreases_after_read(self, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        svc.send_message(chat.id, editor_a, "Msg 1")
        svc.send_message(chat.id, editor_a, "Msg 2")

        chats_before = svc.get_user_chats(editor_b)
        unread_before = next(c["unread_count"] for c in chats_before if c["chat"].id == chat.id)
        assert unread_before == 2

        svc.mark_as_read(chat.id, editor_b)

        chats_after = svc.get_user_chats(editor_b)
        unread_after = next(c["unread_count"] for c in chats_after if c["chat"].id == chat.id)
        assert unread_after == 0

    def test_mark_read_idempotent(self, db, svc, editor_a, editor_b):
        chat = svc.create_direct_chat(editor_a, editor_b.id)
        svc.mark_as_read(chat.id, editor_b)
        participant = (
            db.query(ChatParticipant)
            .filter_by(chat_id=chat.id, user_id=editor_b.id)
            .first()
        )
        first_read = participant.last_read_at

        svc.mark_as_read(chat.id, editor_b)
        db.refresh(participant)
        # Should have updated to a new (or equal) timestamp
        assert participant.last_read_at >= first_read
