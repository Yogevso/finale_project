"""Test Configuration and Fixtures"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.db import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import get_password_hash
from app.config import settings

# Disable rate limiting for tests
settings.RATE_LIMIT_ENABLED = False

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
        is_active=True
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
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client, test_admin):
    """Get authentication token for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def sample_document(client, admin_token):
    """Create a sample document for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={"title": "Test Document", "description": "Test description"}
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
        is_active=True
    )
    db.add(viewer)
    db.commit()
    db.refresh(viewer)
    return viewer


@pytest.fixture
def viewer_auth_headers(client, test_viewer):
    """Get authentication headers for viewer user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "viewer123"}
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
        created_by=test_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc