"""Test Configuration and Fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import DocumentStatus, DocumentVisibility, UserRole
from app.projections import reset_projection_cache
from tests.factories import create_document, create_tenant, create_user

# Disable rate limiting for tests
settings.RATE_LIMIT_ENABLED = False

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite://"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def projection_cache_isolation():
    """Ensure global projection cache state does not leak across tests."""
    reset_projection_cache()
    yield
    reset_projection_cache()


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user"""
    return create_user(
        db,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        plain_password="testpass123",
        role=UserRole.EDITOR,
        is_active=True,
    )


@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    return create_user(
        db,
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        plain_password="admin123",
        role=UserRole.ADMIN,
        is_active=True,
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
        json={"title": "Test Document", "description": "Test description"},
    )
    return response.json()


@pytest.fixture
def test_viewer(db):
    """Create a test viewer user"""
    return create_user(
        db,
        email="viewer@example.com",
        username="viewer",
        full_name="Viewer User",
        plain_password="viewer123",
        role=UserRole.VIEWER,
        is_active=True,
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
def test_system_admin(db):
    """Create a test system admin user"""
    return create_user(
        db,
        email="sysadmin@example.com",
        username="sysadmin",
        full_name="System Admin",
        plain_password="sysadmin123",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
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
def test_manager(db):
    """Create a test manager user"""
    return create_user(
        db,
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        plain_password="manager123",
        role=UserRole.MANAGER,
        is_active=True,
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
    """Create a public active document"""
    return create_document(
        db,
        title="Public Document",
        document_number="DOC-PUB-001",
        description="A public document for testing",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
    )


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
    db.commit()
    db.refresh(doc)
    return doc
