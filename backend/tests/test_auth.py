"""Authentication Tests"""

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app.config import settings
from app.models import SecurityEvent
from app.services.auth_rate_limit_service import AuthRateLimitService


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPass1!",
            "role": "viewer",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["role"] == "customer"
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
        json={"old_password": "testpass123", "new_password": "NewPass4!"},
    )

    assert response.status_code == 200

    # Test login with new password
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "NewPass4!"}
    )
    assert login_response.status_code == 200


def test_change_password_wrong_old_password(client, auth_headers):
    """Test password change with wrong old password"""
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "wrongpass", "new_password": "NewPass4!"},
    )

    assert response.status_code == 400


def test_update_my_profile_timezone_and_locale(client, auth_headers, db, test_user):
    """Users can update timezone/locale via PATCH /users/me."""
    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={
            "full_name": "Test User",
            "timezone": "Asia/Jerusalem",
            "locale": "he",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["timezone"] == "Asia/Jerusalem"
    assert payload["locale"] == "he"

    db.refresh(test_user)
    assert test_user.timezone == "Asia/Jerusalem"
    assert test_user.locale == "he"


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
    monkeypatch.setattr(settings, "ACCOUNT_LOCKOUT_MAX_ATTEMPTS", 999)
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


def test_email_verification_register_verify_allows_login(client, monkeypatch):
    """Register -> verify email -> login succeeds."""
    captured_verification_url: dict[str, str] = {}

    def _capture_email_verification(
        _to_email: str,
        verification_url: str,
        _expires_minutes: int,
    ) -> None:
        captured_verification_url["url"] = verification_url

    monkeypatch.setattr(
        "app.api.management.auth._send_email_verification_task",
        _capture_email_verification,
    )

    registration_payload = {
        "email": "verify-flow@example.com",
        "username": "verify_flow_user",
        "full_name": "Verify Flow User",
        "password": "VerifyP1!",
        "role": "viewer",
    }
    register_response = client.post("/api/v1/auth/register", json=registration_payload)
    assert register_response.status_code == 201
    assert "url" in captured_verification_url

    login_before_verify = client.post(
        "/api/v1/auth/login",
        json={"username": "verify_flow_user", "password": "VerifyP1!"},
    )
    assert login_before_verify.status_code == 403
    assert login_before_verify.json()["detail"] == "email_not_verified"

    verification_url = captured_verification_url["url"]
    token = parse_qs(urlparse(verification_url).query)["token"][0]
    verify_response = client.get("/api/v1/auth/verify-email", params={"token": token})
    assert verify_response.status_code == 200

    login_after_verify = client.post(
        "/api/v1/auth/login",
        json={"username": "verify_flow_user", "password": "VerifyP1!"},
    )
    assert login_after_verify.status_code == 200
    assert "access_token" in login_after_verify.json()


def test_email_verification_register_without_verify_blocks_login(client, monkeypatch):
    """Register without verification should return 403 on login."""
    monkeypatch.setattr(
        "app.api.management.auth._send_email_verification_task",
        lambda *_args, **_kwargs: None,
    )

    registration_payload = {
        "email": "verify-skip@example.com",
        "username": "verify_skip_user",
        "full_name": "Verify Skip User",
        "password": "SkipVer1!",
        "role": "viewer",
    }
    register_response = client.post("/api/v1/auth/register", json=registration_payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "verify_skip_user", "password": "SkipVer1!"},
    )
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "email_not_verified"


def test_login_lockout_then_auto_unlock_after_window(client, test_user, monkeypatch):
    """After max failed attempts user is locked, then auto-unlocked after window."""
    monkeypatch.setattr(settings, "ACCOUNT_LOCKOUT_MAX_ATTEMPTS", 5)
    monkeypatch.setattr(settings, "ACCOUNT_LOCKOUT_DURATION_MINUTES", 30)

    fake_now = {"value": datetime(2026, 1, 1, 9, 0, 0)}

    class _FrozenDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return fake_now["value"]

    monkeypatch.setattr("app.services.auth_service.datetime", _FrozenDateTime)

    for _ in range(4):
        failed_response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert failed_response.status_code == 401

    locked_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    # H-08: locked accounts return 401 (not 403) to prevent user enumeration
    assert locked_response.status_code == 401

    while_locked_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert while_locked_response.status_code == 401

    fake_now["value"] = fake_now["value"] + timedelta(minutes=31)
    unlocked_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert unlocked_response.status_code == 200
    assert "access_token" in unlocked_response.json()


def test_login_anomaly_detection_records_security_event(client, test_user, db, monkeypatch):
    """Successful logins from new IP/device should create a security event."""
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["testclient"])

    initial_headers = {"x-forwarded-for": "10.10.0.1", "user-agent": "BrowserA/1.0"}
    same_headers = {"x-forwarded-for": "10.10.0.1", "user-agent": "BrowserA/1.0"}
    changed_headers = {"x-forwarded-for": "10.10.0.2", "user-agent": "BrowserA/1.0"}

    first_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
        headers=initial_headers,
    )
    assert first_login.status_code == 200

    db.refresh(test_user)
    assert test_user.last_login_ip == "10.10.0.1"
    assert test_user.last_login_user_agent == "BrowserA/1.0"
    assert (
        db.query(SecurityEvent)
        .filter(SecurityEvent.user_id == test_user.id, SecurityEvent.event_type == "new_device_login")
        .count()
        == 0
    )

    second_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
        headers=same_headers,
    )
    assert second_login.status_code == 200
    assert (
        db.query(SecurityEvent)
        .filter(SecurityEvent.user_id == test_user.id, SecurityEvent.event_type == "new_device_login")
        .count()
        == 0
    )

    third_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
        headers=changed_headers,
    )
    assert third_login.status_code == 200

    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.user_id == test_user.id, SecurityEvent.event_type == "new_device_login")
        .all()
    )
    assert len(events) == 1
    assert events[0].ip_address == "10.10.0.2"
    assert events[0].user_agent == "BrowserA/1.0"


# ---------------------------------------------------------------------------
# H-23 / H-03: Collab token endpoint requires write permission
# ---------------------------------------------------------------------------


def test_collab_token_requires_write_permission(client, admin_headers, sample_document):
    """Editors+ can obtain a collab token for a document they can edit."""
    response = client.post(
        "/api/v1/auth/collab-token",
        headers=admin_headers,
        json={"document_id": sample_document["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "write" in data["permissions"]
    assert data["document_id"] == sample_document["id"]


def test_collab_token_rejected_for_viewer(client, viewer_auth_headers, sample_document):
    """Viewers must be refused a collab token (no write permission)."""
    response = client.post(
        "/api/v1/auth/collab-token",
        headers=viewer_auth_headers,
        json={"document_id": sample_document["id"]},
    )
    assert response.status_code == 403


def test_collab_token_requires_auth(client, sample_document):
    """Unauthenticated requests must be rejected."""
    response = client.post(
        "/api/v1/auth/collab-token",
        json={"document_id": sample_document["id"]},
    )
    assert response.status_code in (401, 403)
