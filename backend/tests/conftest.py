"""Test Configuration and Fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.projections import reset_projection_cache
from app.security import get_password_hash

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
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.EDITOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


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
    from app.models import User, UserRole

    viewer = User(
        email="viewer@example.com",
        username="viewer",
        full_name="Viewer User",
        hashed_password=get_password_hash("viewer123"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db.add(viewer)
    db.commit()
    db.refresh(viewer)
    return viewer


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
    from app.models import Document, DocumentStatus

    doc = Document(
        title="Test Document",
        document_number="DOC-TEST-001",
        description="A test document",
        status=DocumentStatus.DRAFT,
        created_by=test_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ========== Additional fixtures for customer portal testing ==========


@pytest.fixture
def test_system_admin(db):
    """Create a test system admin user"""
    user = User(
        email="sysadmin@example.com",
        username="sysadmin",
        full_name="System Admin",
        hashed_password=get_password_hash("sysadmin123"),
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    from app.models import User, UserRole

    manager = User(
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        hashed_password=get_password_hash("manager123"),
        role=UserRole.MANAGER,
        is_active=True,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


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
    from app.models import Tenant

    tenant = Tenant(
        name="Test Company",
        slug="test-company",
        is_active=True,
        contact_email="contact@testcompany.com",
        company_type="customer",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_tenant_2(db):
    """Create a second test tenant for isolation testing"""
    from app.models import Tenant

    tenant = Tenant(
        name="Other Company",
        slug="other-company",
        is_active=True,
        contact_email="contact@othercompany.com",
        company_type="customer",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_customer(db, test_tenant):
    """Create a test customer user associated with a tenant"""
    from app.models import User, UserRole

    customer = User(
        email="customer@testcompany.com",
        username="customer1",
        full_name="Customer User",
        hashed_password=get_password_hash("customer123"),
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_customer_2(db, test_tenant_2):
    """Create a second customer for a different tenant"""
    from app.models import User, UserRole

    customer = User(
        email="customer@othercompany.com",
        username="customer2",
        full_name="Other Customer",
        hashed_password=get_password_hash("customer123"),
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant_2.id,
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


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
    from app.models import Document, DocumentStatus, DocumentVisibility

    doc = Document(
        title="Public Document",
        document_number="DOC-PUB-001",
        description="A public document for testing",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def internal_document(db, test_admin):
    """Create an internal active document"""
    from app.models import Document, DocumentStatus, DocumentVisibility

    doc = Document(
        title="Internal Document",
        document_number="DOC-INT-001",
        description="An internal document for testing",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def company_document(db, test_admin, test_tenant):
    """Create a company-specific document assigned to test_tenant"""
    from app.models import Document, DocumentStatus, DocumentVisibility

    doc = Document(
        title="Company Document",
        document_number="DOC-COMP-001",
        description="A company-specific document",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    db.add(doc)
    db.commit()
    # Assign to tenant
    doc.assigned_companies.append(test_tenant)
    db.commit()
    db.refresh(doc)
    return doc
