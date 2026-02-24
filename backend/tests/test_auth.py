"""Authentication Tests"""

from app.config import settings
from app.services.auth_rate_limit_service import AuthRateLimitService


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "newpass123",
            "role": "viewer",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["role"] == "viewer"
    assert "id" in data


def test_register_duplicate_username(client, test_user):
    """Test registration with duplicate username"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "another@example.com",
            "username": "testuser",  # Duplicate
            "full_name": "Another User",
            "password": "pass123",
            "role": "viewer",
        },
    )

    # 422 Unprocessable Entity for validation errors (duplicate username)
    assert response.status_code in [400, 422]


def test_login_success(client, test_user):
    """Test successful login"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, test_user):
    """Test login with invalid password"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "wrongpassword"}
    )

    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with nonexistent user"""
    response = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "pass123"})

    assert response.status_code == 401


def test_get_current_user(client, auth_headers):
    """Test getting current user info"""
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "permissions" in data
    assert "edit_document" in data["permissions"]


def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication"""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_change_password(client, auth_headers):
    """Test password change"""
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "testpass123", "new_password": "newpass456"},
    )

    assert response.status_code == 200

    # Test login with new password
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "newpass456"}
    )
    assert login_response.status_code == 200


def test_change_password_wrong_old_password(client, auth_headers):
    """Test password change with wrong old password"""
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "wrongpass", "new_password": "newpass456"},
    )

    assert response.status_code == 400


def test_login_returns_refresh_token(client, test_user):
    """Test that login returns a refresh token"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] is not None


def test_refresh_token(client, test_user):
    """Test refreshing access token"""
    # Login to get refresh token
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token to get new access token
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_invalid(client):
    """Test refreshing with invalid token"""
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token"})

    assert response.status_code == 401


def test_logout(client, auth_headers, test_user):
    """Test logout invalidates refresh tokens"""
    # Login to get tokens
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )
    refresh_token = login_response.json()["refresh_token"]
    access_token = login_response.json()["access_token"]

    # Logout
    logout_response = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 200

    # Try to use refresh token - should fail
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_login_rate_limited_by_ip_and_username(client, test_user, monkeypatch):
    """Rapid failed logins should be rate-limited per ip+username key."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    AuthRateLimitService.reset()

    headers = {"x-forwarded-for": "127.0.0.10"}
    for _ in range(AuthRateLimitService.LOGIN_MAX_ATTEMPTS - 1):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
            headers=headers,
        )
        assert response.status_code == 401

    limited_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
        headers=headers,
    )
    assert limited_response.status_code == 429
    payload = limited_response.json()
    assert payload["error_code"] == "RATE_LIMITED"
    assert payload["retry_after"] >= 1
    assert int(limited_response.headers.get("Retry-After", "0")) >= 1

    # Same IP but different username should not be blocked.
    different_user_response = client.post(
        "/api/v1/auth/login",
        json={"username": "another-user", "password": "wrongpassword"},
        headers=headers,
    )
    assert different_user_response.status_code == 401


def test_forgot_password_rate_limited(client, monkeypatch):
    """Forgot-password endpoint should return 429 only after repeated abuse."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    AuthRateLimitService.reset()

    headers = {"x-forwarded-for": "127.0.0.11"}
    for _ in range(AuthRateLimitService.FORGOT_MAX_ATTEMPTS - 1):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "test@example.com"},
            headers=headers,
        )
        assert response.status_code == 200

    limited_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "test@example.com"},
        headers=headers,
    )
    assert limited_response.status_code == 429
    payload = limited_response.json()
    assert payload["error_code"] == "RATE_LIMITED"
    assert payload["retry_after"] >= 1
    assert int(limited_response.headers.get("Retry-After", "0")) >= 1


def test_forgot_password_lock_expires_cleanly(client, monkeypatch):
    """After lock expires, next request should be allowed before any new lock."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(AuthRateLimitService, "FORGOT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(AuthRateLimitService, "FORGOT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(AuthRateLimitService, "FORGOT_LOCK_SECONDS", 5)
    AuthRateLimitService.reset()

    fake_now = {"value": 1000.0}
    monkeypatch.setattr("app.services.auth_rate_limit_service.time.time", lambda: fake_now["value"])

    for _ in range(AuthRateLimitService.FORGOT_MAX_ATTEMPTS - 1):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"identifier": "test@example.com"},
        )
        assert response.status_code == 200

    locked_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "test@example.com"},
    )
    assert locked_response.status_code == 429

    fake_now["value"] += AuthRateLimitService.FORGOT_LOCK_SECONDS + 0.1
    first_after_lock = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "test@example.com"},
    )
    assert first_after_lock.status_code == 200
