"""Test Configuration and Fixtures"""

# ruff: noqa: E402

# ---------------------------------------------------------------------------
# Stub out chromadb early to prevent numpy C-extension load failures.
# On systems where numpy's .pyd is blocked (e.g. Windows Smart App Control),
# importing chromadb crashes the process. Since no tests actually need a real
# vector store, we inject lightweight fakes into sys.modules before anything
# else is imported.
# ---------------------------------------------------------------------------
import sys
import types

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = []  # make it a "package"
    return mod

if "chromadb" not in sys.modules:
    _chromadb = _make_stub("chromadb")

    # Minimal attributes that application code references at import time
    class _FakeSettings:
        def __init__(self, **kw):
            pass
    _config = _make_stub("chromadb.config")
    _config.Settings = _FakeSettings  # type: ignore[attr-defined]

    class _FakeClientAPI:
        """Duck-typed stand-in for chromadb.ClientAPI."""
        pass

    _chromadb.ClientAPI = _FakeClientAPI  # type: ignore[attr-defined]

    def _PersistentClient(**kw):  # noqa: N802
        return _FakeClientAPI()

    _chromadb.PersistentClient = _PersistentClient  # type: ignore[attr-defined]

    # Register stubs so that `import chromadb` / `from chromadb.config import ...`
    # resolve without hitting the real package (and numpy).
    for _name, _mod in [
        ("chromadb", _chromadb),
        ("chromadb.config", _config),
        ("chromadb.api", _make_stub("chromadb.api")),
        ("chromadb.api.types", _make_stub("chromadb.api.types")),
    ]:
        sys.modules.setdefault(_name, _mod)

import asyncio
import os
import shutil
import tempfile
import warnings
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Use the checked-in OpenAPI snapshot during tests to avoid flaky live-schema
# generation on Windows/Python 3.14.
settings.APP_ENV = "testing"

# ---------------------------------------------------------------------------
# Use fast bcrypt rounds during tests.  Default rounds=12 costs ~200-300 ms per
# hash/verify.  With rounds=4 each call drops to <1 ms, saving minutes across
# the full 1400+ test suite (every create_user + login fixture benefits).
# ---------------------------------------------------------------------------
from passlib.context import CryptContext as _CryptContext
import app.auth_context.passwords as _pwd_mod

_pwd_mod.pwd_context = _CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)

from app.db import Base, get_db, get_analytics_db, get_chat_db
from app.db.bases import AnalyticsBase, ChatBase
from app.models import DocumentStatus, DocumentVisibility, ReviewRequest, ReviewStatus, UserRole, Version
from app.projections import reset_projection_cache
from tests.factories import create_document, create_tenant, create_user
from tests.tenant_isolation.harness import TenantIsolationScenario

# Disable rate limiting and CSRF protection for tests
settings.RATE_LIMIT_ENABLED = False
settings.CSRF_PROTECTION_ENABLED = False

# Test database URL - use in-memory SQLite with StaticPool (single shared
# connection).  The previous file-based approach caused "disk I/O error" in
# Docker containers.
TEST_DATABASE_URL = "sqlite://"
_test_tmp_root = Path(__file__).resolve().parent / "_tmp_runtime"
_test_tmp_root.mkdir(parents=True, exist_ok=True)

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Create all tables ONCE at import time (not per-test) to avoid
# Python 3.14 + SQLite C-driver segfault caused by hundreds of
# repeated create_all / drop_all cycles on the same in-memory DB.
# Per-test isolation is achieved via SAVEPOINT rollback below.
# ---------------------------------------------------------------------------
# IMPORTANT: create_all MUST run BEFORE importing app.main because that import
# initialises the application's own database engine.  With StaticPool the two
# engines share the underlying SQLite connection, and if the app engine is
# created first the test create_all hits a "disk I/O error".
Base.metadata.create_all(bind=engine)
AnalyticsBase.metadata.create_all(bind=engine)
ChatBase.metadata.create_all(bind=engine)

# Now it is safe to import the FastAPI application.
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# ONE shared TestClient for the entire session.  Creating a TestClient spins
# up an anyio blocking-portal thread + asyncio event-loop thread.  When a
# *new* TestClient is created per-test (×1 000+ tests), the thread-pool
# accumulates and eventually triggers a CPython 3.14 access-violation crash
# inside socket.getaddrinfo running on a concurrent-futures worker thread.
# Reusing a single client avoids this.
# ---------------------------------------------------------------------------
_shared_test_client = TestClient(app)
_shared_test_client.__enter__()


@pytest.fixture(autouse=True)
def event_loop_compat():
    """Provide a default event loop for tests that call asyncio.get_event_loop()."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def projection_cache_isolation():
    """Ensure global projection cache state does not leak across tests."""
    reset_projection_cache()
    yield
    reset_projection_cache()


@pytest.fixture(autouse=True)
def auth_rate_limit_isolation():
    """Reset auth rate-limit buckets between tests to prevent cross-test pollution."""
    from app.services.auth_rate_limit_service import AuthRateLimitService
    AuthRateLimitService.reset()
    # Also clear the general middleware's per-IP buckets so auth-path limits
    # don't carry over between tests that enable RATE_LIMIT_ENABLED.
    from app.middleware.rate_limit import RateLimitMiddleware
    # Walk the built middleware_stack chain (not .app) to find the live instance.
    _app = getattr(_shared_test_client.app, "middleware_stack", None)
    while _app is not None:
        if isinstance(_app, RateLimitMiddleware):
            _app.clients.clear()
            break
        _app = getattr(_app, "app", None)
    yield
    AuthRateLimitService.reset()


@pytest.fixture(scope="function")
def db():
    """Provide a DB session with per-test isolation via SAVEPOINT rollback.

    Tables are created once at module level. Each test runs inside a
    transaction that is rolled back on teardown, so every test starts
    with a clean database.
    """
    from app.services.audit_helper import set_session_factory

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Start a SAVEPOINT so the session's own .commit() calls don't
    # actually commit; they release and re-open the savepoint instead.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    # Override audit helper to use the same test connection so AuditLog
    # writes are visible within the test and rolled back on teardown.
    set_session_factory(lambda: TestingSessionLocal(bind=connection))

    try:
        yield session
    finally:
        set_session_factory(None)
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def tmp_path():
    """Windows-stable tmp_path replacement for Python 3.14 pytest runs."""
    tmp_dir = _test_tmp_root / f"case_{uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def client(db):
    """Reuse the shared TestClient, just swap the DB override per test."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_analytics_db] = override_get_db
    app.dependency_overrides[get_chat_db] = override_get_db
    try:
        yield _shared_test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def default_tenant(db):
    """Provide a default tenant for tests that need one implicitly."""
    return create_tenant(
        db,
        name="Default Test Tenant",
        slug="default-test-tenant",
        is_active=True,
        contact_email="default@test.com",
        company_type="customer",
    )


@pytest.fixture
def test_user(db, default_tenant):
    """Create a test user"""
    return create_user(
        db,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        plain_password="testpass123",
        role=UserRole.EDITOR,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def test_admin(db, default_tenant):
    """Create a test admin user"""
    return create_user(
        db,
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        plain_password="admin123",
        role=UserRole.ADMIN,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client, test_admin):
    """Get authentication token for admin user"""
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    return response.json()["access_token"]


@pytest.fixture
def sample_document(client, admin_token):
    """Create a sample document for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "title": "Test Document",
            "description": "Test description",
            "platform": "default",  # Required field
        },
    )
    return response.json()


@pytest.fixture
def test_viewer(db, default_tenant):
    """Create a test viewer user"""
    return create_user(
        db,
        email="viewer@example.com",
        username="viewer",
        full_name="Viewer User",
        plain_password="viewer123",
        role=UserRole.VIEWER,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def viewer_auth_headers(client, test_viewer):
    """Get authentication headers for viewer user"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "viewer", "password": "viewer123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_document(db, test_user):
    """Create a test document owned by test_user"""
    return create_document(
        db,
        title="Test Document",
        document_number="DOC-TEST-001",
        description="A test document",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_user.id,
    )


# ========== Additional fixtures for customer portal testing ==========


@pytest.fixture
def test_system_admin(db, default_tenant):
    """Create a test system admin user"""
    return create_user(
        db,
        email="sysadmin@example.com",
        username="sysadmin",
        full_name="System Admin",
        plain_password="sysadmin123",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def system_admin_headers(client, test_system_admin):
    """Get authentication headers for system admin"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "sysadmin", "password": "sysadmin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_manager(db, default_tenant):
    """Create a test manager user"""
    return create_user(
        db,
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        plain_password="manager123",
        role=UserRole.MANAGER,
        is_active=True,
        tenant_id=default_tenant.id,
    )


@pytest.fixture
def manager_headers(client, test_manager):
    """Get authentication headers for manager"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "manager", "password": "manager123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_tenant(db):
    """Create a test tenant/company"""
    return create_tenant(
        db,
        name="Test Company",
        slug="test-company",
        is_active=True,
        contact_email="contact@testcompany.com",
        company_type="customer",
    )


@pytest.fixture
def test_tenant_2(db):
    """Create a second test tenant for isolation testing"""
    return create_tenant(
        db,
        name="Other Company",
        slug="other-company",
        is_active=True,
        contact_email="contact@othercompany.com",
        company_type="customer",
    )


@pytest.fixture
def test_customer(db, test_tenant):
    """Create a test customer user associated with a tenant"""
    return create_user(
        db,
        email="customer@testcompany.com",
        username="customer1",
        full_name="Customer User",
        plain_password="customer123",
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant.id,
        is_active=True,
    )


@pytest.fixture
def test_customer_2(db, test_tenant_2):
    """Create a second customer for a different tenant"""
    return create_user(
        db,
        email="customer@othercompany.com",
        username="customer2",
        full_name="Other Customer",
        plain_password="customer123",
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant_2.id,
        is_active=True,
    )


@pytest.fixture
def customer_headers(client, test_customer):
    """Get authentication headers for customer user"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "customer1", "password": "customer123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer_2_headers(client, test_customer_2):
    """Get authentication headers for second customer"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "customer2", "password": "customer123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def public_document(db, test_admin):
    """Create a public active document with a published version"""
    from datetime import datetime

    doc = create_document(
        db,
        title="Public Document",
        document_number="DOC-PUB-001",
        description="A public document for testing",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
    )
    version = Version(
        document_id=doc.id,
        version_number=1,
        content="Published test content",
        is_published=True,
        published_at=datetime.utcnow(),
        created_by=test_admin.id,
        published_by=test_admin.id,
    )
    db.add(version)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def internal_document(db, test_admin):
    """Create an internal active document"""
    return create_document(
        db,
        title="Internal Document",
        document_number="DOC-INT-001",
        description="An internal document for testing",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_admin.id,
    )


@pytest.fixture
def company_document(db, test_admin, test_tenant):
    """Create a company-specific document assigned to test_tenant"""
    from datetime import datetime

    doc = create_document(
        db,
        title="Company Document",
        document_number="DOC-COMP-001",
        description="A company-specific document",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    # Assign to tenant
    doc.assigned_companies.append(test_tenant)
    version = Version(
        document_id=doc.id,
        version_number=1,
        content="Published company content",
        is_published=True,
        published_at=datetime.utcnow(),
        created_by=test_admin.id,
        published_by=test_admin.id,
    )
    db.add(version)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def tenant_isolation_scenario(db):
    """Create a reusable owner/attacker scenario for tenant-isolation attack suites."""
    owner_tenant = create_tenant(
        db,
        name="Harness Owner Tenant",
        slug="harness-owner-tenant",
        company_type="customer",
    )
    attacker_tenant = create_tenant(
        db,
        name="Harness Attacker Tenant",
        slug="harness-attacker-tenant",
        company_type="customer",
    )

    owner_user = create_user(
        db,
        email="harness-owner@example.com",
        username="harness_owner",
        full_name="Harness Owner",
        plain_password="owner-pass-123",
        role=UserRole.ADMIN,
        tenant_id=owner_tenant.id,
        is_active=True,
    )

    attacker_editor_password = "attacker-editor-pass-123"
    attacker_manager_password = "attacker-manager-pass-123"
    attacker_editor = create_user(
        db,
        email="harness-attacker-editor@example.com",
        username="harness_attacker_editor",
        full_name="Harness Attacker Editor",
        plain_password=attacker_editor_password,
        role=UserRole.EDITOR,
        tenant_id=attacker_tenant.id,
        is_active=True,
    )
    attacker_manager = create_user(
        db,
        email="harness-attacker-manager@example.com",
        username="harness_attacker_manager",
        full_name="Harness Attacker Manager",
        plain_password=attacker_manager_password,
        role=UserRole.MANAGER,
        tenant_id=attacker_tenant.id,
        is_active=True,
    )

    document = create_document(
        db,
        title="Tenant Harness Target Document",
        document_number="DOC-HARNESS-0001",
        description="Tenant-isolation target document",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=owner_user.id,
        tenant_id=owner_tenant.id,
    )
    document.assigned_companies.append(owner_tenant)
    document.yjs_state = b"\x01\x02\x03"

    review = ReviewRequest(
        document_id=document.id,
        submitted_by=owner_user.id,
        status=ReviewStatus.PENDING,
        message="Harness review seed",
    )
    db.add(review)

    # H-23: Feedback isolation seed
    from app.models import Feedback, FeedbackType, FeedbackStatus, SearchAnalytics

    feedback = Feedback(
        document_id=document.id,
        user_id=owner_user.id,
        feedback_type=FeedbackType.OTHER,
        status=FeedbackStatus.PENDING,
        content="Harness feedback seed",
    )
    db.add(feedback)

    # H-23: Search analytics isolation seed
    search_analytics = SearchAnalytics(
        query="harness search test",
        user_id=owner_user.id,
        tenant_id=owner_tenant.id,
        results_count=3,
    )
    db.add(search_analytics)

    db.commit()
    db.refresh(document)
    db.refresh(review)
    db.refresh(feedback)
    db.refresh(search_analytics)

    return TenantIsolationScenario(
        owner_tenant=owner_tenant,
        attacker_tenant=attacker_tenant,
        owner_user=owner_user,
        attacker_editor=attacker_editor,
        attacker_manager=attacker_manager,
        attacker_editor_password=attacker_editor_password,
        attacker_manager_password=attacker_manager_password,
        document=document,
        review=review,
        feedback=feedback,
        search_analytics=search_analytics,
    )


@pytest.fixture
def tenant_isolation_actor_headers(client, tenant_isolation_scenario: TenantIsolationScenario):
    """Issue auth headers for attacker actors used by tenant attack harnesses."""

    def _login(username: str, password: str) -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {
        "attacker_editor": _login(
            tenant_isolation_scenario.attacker_editor.username,
            tenant_isolation_scenario.attacker_editor_password,
        ),
        "attacker_manager": _login(
            tenant_isolation_scenario.attacker_manager.username,
            tenant_isolation_scenario.attacker_manager_password,
        ),
    }


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """
    Work around intermittent Windows temp-dir ACL failures in pytest cleanup.

    Python 3.14 + Windows may raise WinError 5 while pytest scans/removes
    basetemp symlink remnants after tests complete. This hook suppresses only
    that cleanup exception so real test outcomes are preserved.
    """
    _ = exitstatus
    outcome = yield
    try:
        outcome.get_result()
    except PermissionError as exc:
        message = str(exc)
        if "[WinError 5]" in message and ("\\temp\\pytest" in message or "\\tmp_pytest\\" in message):
            warnings.warn(
                f"Suppressed pytest temp cleanup permission error: {message}",
                RuntimeWarning,
                stacklevel=1,
            )
            outcome.force_result(None)
            return
        raise
