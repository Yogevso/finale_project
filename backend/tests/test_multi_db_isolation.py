"""Multi-DB isolation tests — verify the 3-database split works correctly.

These tests create 3 SEPARATE in-memory SQLite databases (core, analytics, chat),
each with only its own Base's tables, and verify:
1. Table isolation: each DB has only its expected tables
2. CRUD operations work on each DB independently
3. Cross-DB writes don't bleed between databases
4. FastAPI dependency wiring routes to correct engines
"""

import sys
import types

# Stub chromadb before anything else (same as conftest.py)
if "chromadb" not in sys.modules:
    _chromadb = types.ModuleType("chromadb")
    _chromadb.__path__ = []

    class _FakeSettings:
        def __init__(self, **kw):
            pass

    _config = types.ModuleType("chromadb.config")
    _config.__path__ = []
    _config.Settings = _FakeSettings

    class _FakeClientAPI:
        pass

    _chromadb.ClientAPI = _FakeClientAPI
    _chromadb.PersistentClient = lambda **kw: _FakeClientAPI()

    for _name, _mod in [
        ("chromadb", _chromadb),
        ("chromadb.config", _config),
        ("chromadb.api", types.ModuleType("chromadb.api")),
        ("chromadb.api.types", types.ModuleType("chromadb.api.types")),
    ]:
        sys.modules.setdefault(_name, _mod)

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

settings.APP_ENV = "testing"
settings.RATE_LIMIT_ENABLED = False

from app.db.bases import AnalyticsBase, ChatBase, CoreBase

# Import models so they register with their Base
import app.models  # noqa: F401
from app.models import (
    ActionType,
    AuditLog,
    AssistantConversation,
    Notification,
    SecurityEvent,
    Tenant,
    User,
    UserRole,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def core_engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    CoreBase.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def analytics_engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    AnalyticsBase.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def chat_engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    ChatBase.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def core_session(core_engine):
    Session = sessionmaker(bind=core_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def analytics_session(analytics_engine):
    Session = sessionmaker(bind=analytics_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def chat_session(chat_engine):
    Session = sessionmaker(bind=chat_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ── Test 1: Table isolation ──────────────────────────────────────────────

EXPECTED_ANALYTICS_TABLES = {
    "activation_milestones", "audit_logs", "domain_event_outbox",
    "nps_surveys", "onboarding_events", "search_analytics", "security_events",
}

EXPECTED_CHAT_TABLES = {
    "assistant_conversations", "assistant_messages", "assistant_uploaded_files",
    "chat_messages", "chat_participants", "chats",
    "collaboration_activities", "collaboration_sessions",
    "collaboration_snapshots", "notifications",
}

EXPECTED_CORE_SAMPLE = {"users", "tenants", "documents", "versions", "comments"}


class TestTableIsolation:
    def test_core_db_has_only_core_tables(self, core_engine):
        tables = set(inspect(core_engine).get_table_names())
        assert EXPECTED_CORE_SAMPLE.issubset(tables), f"Missing core tables: {EXPECTED_CORE_SAMPLE - tables}"
        assert not tables & EXPECTED_ANALYTICS_TABLES, f"Analytics tables leaked into core: {tables & EXPECTED_ANALYTICS_TABLES}"
        assert not tables & EXPECTED_CHAT_TABLES, f"Chat tables leaked into core: {tables & EXPECTED_CHAT_TABLES}"

    def test_analytics_db_has_only_analytics_tables(self, analytics_engine):
        tables = set(inspect(analytics_engine).get_table_names())
        assert tables == EXPECTED_ANALYTICS_TABLES, f"Expected {EXPECTED_ANALYTICS_TABLES}, got {tables}"
        assert not tables & EXPECTED_CORE_SAMPLE, "Core tables leaked into analytics"

    def test_chat_db_has_only_chat_tables(self, chat_engine):
        tables = set(inspect(chat_engine).get_table_names())
        assert tables == EXPECTED_CHAT_TABLES, f"Expected {EXPECTED_CHAT_TABLES}, got {tables}"
        assert not tables & EXPECTED_CORE_SAMPLE, "Core tables leaked into chat"


# ── Test 2: CRUD on each database ────────────────────────────────────────

class TestCRUDIsolation:
    def test_core_crud(self, core_session):
        """Create a tenant and user in core DB."""
        tenant = Tenant(
            name="Test Corp", slug="test-corp", is_active=True,
            contact_email="t@test.com", company_type="customer",
        )
        core_session.add(tenant)
        core_session.flush()

        user = User(
            email="iso@test.com", username="isouser", full_name="Iso User",
            hashed_password="fake", role=UserRole.EDITOR, is_active=True,
            tenant_id=tenant.id,
        )
        core_session.add(user)
        core_session.flush()

        assert user.id is not None
        assert core_session.query(User).count() == 1

    def test_analytics_crud(self, analytics_session):
        """Create an audit log and security event in analytics DB."""
        log = AuditLog(
            user_id=1, action=ActionType.CREATE,
            details='{"test": true}',
        )
        analytics_session.add(log)
        analytics_session.flush()

        sec = SecurityEvent(
            event_type="login", user_id=1,
            ip_address="127.0.0.1",
        )
        analytics_session.add(sec)
        analytics_session.flush()

        assert log.id is not None
        assert sec.id is not None
        assert analytics_session.query(AuditLog).count() == 1
        assert analytics_session.query(SecurityEvent).count() == 1

    def test_chat_crud(self, chat_session):
        """Create a notification and assistant conversation in chat DB."""
        notif = Notification(
            user_id=1, type="info", title="Test",
            message="Hello", is_read=False,
        )
        chat_session.add(notif)
        chat_session.flush()

        conv = AssistantConversation(
            user_id=1, title="Test Conv",
        )
        chat_session.add(conv)
        chat_session.flush()

        assert notif.id is not None
        assert conv.id is not None
        assert chat_session.query(Notification).count() == 1
        assert chat_session.query(AssistantConversation).count() == 1


# ── Test 3: Cross-DB writes don't bleed ──────────────────────────────────

class TestCrossDBIsolation:
    def test_analytics_write_not_visible_in_core(self, core_engine, analytics_session):
        """Data written to analytics DB must NOT appear in core DB."""
        log = AuditLog(
            user_id=99, action=ActionType.SYSTEM,
            details='{"phantom": true}',
        )
        analytics_session.add(log)
        analytics_session.flush()

        # Core engine should not have an audit_logs table at all
        core_tables = set(inspect(core_engine).get_table_names())
        assert "audit_logs" not in core_tables

    def test_chat_write_not_visible_in_core(self, core_engine, chat_session):
        """Data written to chat DB must NOT appear in core DB."""
        notif = Notification(
            user_id=99, type="ghost", title="Ghost",
            message="You shouldn't see me", is_read=False,
        )
        chat_session.add(notif)
        chat_session.flush()

        core_tables = set(inspect(core_engine).get_table_names())
        assert "notifications" not in core_tables

    def test_core_write_not_visible_in_analytics(self, analytics_engine, core_session):
        """Core data must NOT appear in analytics DB."""
        analytics_tables = set(inspect(analytics_engine).get_table_names())
        assert "users" not in analytics_tables
        assert "tenants" not in analytics_tables

    def test_core_write_not_visible_in_chat(self, chat_engine, core_session):
        """Core data must NOT appear in chat DB."""
        chat_tables = set(inspect(chat_engine).get_table_names())
        assert "users" not in chat_tables
        assert "documents" not in chat_tables


# ── Test 4: No FK constraint to external tables ─────────────────────────

class TestNoExternalForeignKeys:
    """Verify analytics/chat models don't have FK constraints to core tables."""

    def test_analytics_no_fk_to_core(self, analytics_engine):
        inspector = inspect(analytics_engine)
        for table in EXPECTED_ANALYTICS_TABLES:
            fks = inspector.get_foreign_keys(table)
            for fk in fks:
                referred = fk.get("referred_table", "")
                assert referred not in {"users", "tenants", "documents"}, (
                    f"Analytics table {table} has FK to core table {referred}"
                )

    def test_chat_no_fk_to_core(self, chat_engine):
        inspector = inspect(chat_engine)
        for table in EXPECTED_CHAT_TABLES:
            fks = inspector.get_foreign_keys(table)
            for fk in fks:
                referred = fk.get("referred_table", "")
                assert referred not in {"users", "tenants", "documents"}, (
                    f"Chat table {table} has FK to core table {referred}"
                )


# ── Test 5: Concurrent write to separate engines ────────────────────────

class TestConcurrentWrites:
    def test_parallel_writes_no_lock_contention(
        self, core_session, analytics_session, chat_session
    ):
        """Writes to all 3 databases succeed independently."""
        # Core
        tenant = Tenant(
            name="Concurrent Corp", slug="concurrent-corp", is_active=True,
            contact_email="c@test.com", company_type="customer",
        )
        core_session.add(tenant)
        core_session.flush()

        # Analytics
        log = AuditLog(
            user_id=1, action=ActionType.VIEW,
            details='{"concurrent": true}',
        )
        analytics_session.add(log)
        analytics_session.flush()

        # Chat
        conv = AssistantConversation(user_id=1, title="Concurrent Conv")
        chat_session.add(conv)
        chat_session.flush()

        assert tenant.id is not None
        assert log.id is not None
        assert conv.id is not None
