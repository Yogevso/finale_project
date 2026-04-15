"""Load test: write contention benchmark — single DB vs 3 DBs.

Measures lock wait time and throughput when performing concurrent writes
to audit_log (analytics) + documents (core) simultaneously.

Run: python -m pytest tests/test_write_contention.py -v --override-ini="addopts=" -p no:logging
"""

import sys
import types

if "chromadb" not in sys.modules:
    _chromadb = types.ModuleType("chromadb")
    _chromadb.__path__ = []

    class _FS:
        def __init__(self, **kw):
            pass

    _cfg = types.ModuleType("chromadb.config")
    _cfg.__path__ = []
    _cfg.Settings = _FS

    class _FC:
        pass

    _chromadb.ClientAPI = _FC
    _chromadb.PersistentClient = lambda **kw: _FC()
    for n, m in [
        ("chromadb", _chromadb),
        ("chromadb.config", _cfg),
        ("chromadb.api", types.ModuleType("chromadb.api")),
        ("chromadb.api.types", types.ModuleType("chromadb.api.types")),
    ]:
        sys.modules.setdefault(n, m)

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

settings.APP_ENV = "testing"

import app.models  # noqa: F401, E402
from app.db.bases import AnalyticsBase, ChatBase, CoreBase  # noqa: E402
from app.models import (  # noqa: E402
    ActionType,
    AssistantConversation,
    AuditLog,
    Tenant,
    User,
    UserRole,
)

WRITE_COUNT = 200  # number of writes per category


def _make_engine():
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def _write_audit_logs(session_factory, n):
    start = time.perf_counter()
    sess = session_factory()
    try:
        for i in range(n):
            sess.add(AuditLog(user_id=1, action=ActionType.VIEW, details=f'{{"i":{i}}}'))
            if i % 50 == 0:
                sess.flush()
        sess.commit()
    finally:
        sess.close()
    return time.perf_counter() - start


def _write_conversations(session_factory, n):
    start = time.perf_counter()
    sess = session_factory()
    try:
        for i in range(n):
            sess.add(AssistantConversation(user_id=1, title=f"Conv {i}"))
            if i % 50 == 0:
                sess.flush()
        sess.commit()
    finally:
        sess.close()
    return time.perf_counter() - start


def _write_users(session_factory, tenant_id, n):
    start = time.perf_counter()
    sess = session_factory()
    try:
        for i in range(n):
            sess.add(
                User(
                    email=f"u{i}@load.test",
                    username=f"load_{i}",
                    full_name=f"Load {i}",
                    hashed_password="x",
                    role=UserRole.VIEWER,
                    is_active=True,
                    tenant_id=tenant_id,
                )
            )
            if i % 50 == 0:
                sess.flush()
        sess.commit()
    finally:
        sess.close()
    return time.perf_counter() - start


class TestSingleDBContention:
    """All writes go to a single database — baseline."""

    @pytest.fixture(autouse=True)
    def setup_single_db(self):
        self.engine = _make_engine()
        CoreBase.metadata.create_all(bind=self.engine)
        AnalyticsBase.metadata.create_all(bind=self.engine)
        ChatBase.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # seed a tenant
        s = self.Session()
        t = Tenant(
            name="Load",
            slug="load",
            is_active=True,
            contact_email="l@t.com",
            company_type="customer",
        )
        s.add(t)
        s.commit()
        self.tenant_id = t.id
        s.close()
        yield
        self.engine.dispose()

    def test_sequential_writes_single_db(self):
        """Single DB must serialize writes — measure sequential throughput."""
        start = time.perf_counter()
        results = {
            "audit": _write_audit_logs(self.Session, WRITE_COUNT),
            "chat": _write_conversations(self.Session, WRITE_COUNT),
            "core": _write_users(self.Session, self.tenant_id, WRITE_COUNT),
        }
        wall = time.perf_counter() - start
        throughput = (WRITE_COUNT * 3) / wall
        print(
            f"\n  [SINGLE DB] audit={results['audit']:.3f}s  chat={results['chat']:.3f}s  core={results['core']:.3f}s"
        )
        print(f"  [SINGLE DB] wall={wall:.3f}s  throughput={throughput:.0f} writes/s (sequential)")
        assert wall < 30, "Write took too long"


class TestMultiDBContention:
    """Each category writes to its own database — should show less contention."""

    @pytest.fixture(autouse=True)
    def setup_multi_db(self):
        self.core_engine = _make_engine()
        self.analytics_engine = _make_engine()
        self.chat_engine = _make_engine()
        CoreBase.metadata.create_all(bind=self.core_engine)
        AnalyticsBase.metadata.create_all(bind=self.analytics_engine)
        ChatBase.metadata.create_all(bind=self.chat_engine)
        self.CoreSession = sessionmaker(bind=self.core_engine)
        self.AnalyticsSession = sessionmaker(bind=self.analytics_engine)
        self.ChatSession = sessionmaker(bind=self.chat_engine)
        # seed a tenant
        s = self.CoreSession()
        t = Tenant(
            name="Load",
            slug="load",
            is_active=True,
            contact_email="l@t.com",
            company_type="customer",
        )
        s.add(t)
        s.commit()
        self.tenant_id = t.id
        s.close()
        yield
        self.core_engine.dispose()
        self.analytics_engine.dispose()
        self.chat_engine.dispose()

    def test_concurrent_writes_multi_db(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(_write_audit_logs, self.AnalyticsSession, WRITE_COUNT): "audit",
                pool.submit(_write_conversations, self.ChatSession, WRITE_COUNT): "chat",
                pool.submit(_write_users, self.CoreSession, self.tenant_id, WRITE_COUNT): "core",
            }
            results = {}
            for f in as_completed(futures):
                results[futures[f]] = f.result()

        total = sum(results.values())
        throughput = (WRITE_COUNT * 3) / total
        print(
            f"\n  [MULTI DB]  audit={results['audit']:.3f}s  chat={results['chat']:.3f}s  core={results['core']:.3f}s"
        )
        print(f"  [MULTI DB]  total_wall={total:.3f}s  throughput={throughput:.0f} writes/s")
        assert all(v < 30 for v in results.values()), "Write took too long"
