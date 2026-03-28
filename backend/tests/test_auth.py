"""Authentication Tests"""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from app.auth_context.invitation_tokens import hash_invitation_token
from app.config import settings
from app.models import (
    ActionType,
    AuditLog,
    Invitation,
    InvitationStatus,
    SecurityEvent,
    UserRole,
    UserSession,
)
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


def test_update_my_profile_rejects_inactive_company(client, auth_headers, db, default_tenant):
    """Users cannot patch /users/me after their tenant is suspended."""
    default_tenant.is_active = False
    db.commit()

    response = client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"full_name": "Blocked User"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Company is inactive"


def test_get_my_onboarding_defaults(client, auth_headers):
    response = client.get("/api/v1/users/me/onboarding", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["guide_version"] == 1
    assert payload["guide_seen_at"] is None
    assert payload["checklist_version"] == 1
    assert payload["completed_steps"] == []
    assert payload["checklist_completed_at"] is None


def test_update_my_onboarding_state_persists_normalized_steps(
    client,
    auth_headers,
    db,
    test_user,
):
    response = client.patch(
        "/api/v1/users/me/onboarding",
        headers=auth_headers,
        json={
            "guide_version": 1,
            "guide_seen_at": "2026-03-28T09:00:00Z",
            "checklist_version": 1,
            "completed_steps": [" open_documents ", "open_documents", "", "message_support"],
            "checklist_completed_at": "2026-03-28T09:05:00Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_steps"] == ["open_documents", "message_support"]
    assert payload["guide_seen_at"].startswith("2026-03-28T09:00:00")
    assert payload["checklist_completed_at"].startswith("2026-03-28T09:05:00")

    db.refresh(test_user)
    assert test_user.onboarding_state["completed_steps"] == [
        "open_documents",
        "message_support",
    ]


def test_update_my_onboarding_state_can_clear_completion(
    client,
    auth_headers,
    db,
    test_user,
):
    test_user.onboarding_state = {
        "guide_version": 1,
        "guide_seen_at": "2026-03-28T09:00:00",
        "checklist_version": 1,
        "completed_steps": ["open_documents"],
        "checklist_completed_at": "2026-03-28T09:05:00",
    }
    db.commit()

    response = client.patch(
        "/api/v1/users/me/onboarding",
        headers=auth_headers,
        json={
            "completed_steps": [],
            "checklist_completed_at": None,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_steps"] == []
    assert payload["checklist_completed_at"] is None

    db.refresh(test_user)
    assert test_user.onboarding_state["completed_steps"] == []
    assert test_user.onboarding_state["checklist_completed_at"] is None


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


def test_refresh_token_rejects_inactive_session_and_revokes_it(client, test_user, db):
    """Refresh should not rotate tokens for sessions that already exceeded inactivity."""
    login_response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"}
    )
    refresh_token = login_response.json()["refresh_token"]
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == test_user.id, UserSession.revoked_at.is_(None))
        .first()
    )
    assert session is not None

    session.last_active_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=settings.SESSION_INACTIVITY_DAYS + 1
    )
    db.commit()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401
    db.refresh(session)
    assert session.revoked_at is not None


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


def test_logout_revokes_only_current_session(client, test_user):
    """Standard logout should not revoke unrelated active sessions."""
    first_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
        headers={"user-agent": "Browser/one"},
    )
    second_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
        headers={"user-agent": "Browser/two"},
    )

    assert first_login.status_code == 200
    assert second_login.status_code == 200

    first_access_token = first_login.json()["access_token"]
    second_access_token = second_login.json()["access_token"]
    second_refresh_token = second_login.json()["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {second_access_token}"},
    )
    assert logout_response.status_code == 200

    current_session_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second_access_token}"},
    )
    assert current_session_response.status_code == 401

    other_session_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {first_access_token}"},
    )
    assert other_session_response.status_code == 200

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh_token},
    )
    assert refresh_response.status_code == 401


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


def test_forgot_password_email_uses_reset_password_route(client, test_user, monkeypatch):
    """Forgot-password emails must deep-link to the reset-password page."""
    captured_reset_url: dict[str, str] = {}

    def _capture_password_reset_email(
        _to_email: str,
        reset_url: str,
        _expires_minutes: int,
    ) -> None:
        captured_reset_url["url"] = reset_url

    monkeypatch.setattr(settings, "BASE_URL", "http://frontend.test")
    monkeypatch.setattr(
        "app.api.management.auth._send_password_reset_email_task",
        _capture_password_reset_email,
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": test_user.email},
    )

    assert response.status_code == 200
    assert captured_reset_url["url"].startswith("http://frontend.test/reset-password?token=")
    parsed = urlparse(captured_reset_url["url"])
    assert parsed.path == "/reset-password"
    token = parse_qs(parsed.query)["token"][0]
    assert token


def test_reset_password_rate_limited(client, monkeypatch):
    """Reset-password completion attempts should be rate-limited by client IP."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(AuthRateLimitService, "RESET_PASSWORD_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(AuthRateLimitService, "RESET_PASSWORD_WINDOW_SECONDS", 60)
    monkeypatch.setattr(AuthRateLimitService, "RESET_PASSWORD_LOCK_SECONDS", 5)
    AuthRateLimitService.reset()

    headers = {"x-forwarded-for": "127.0.0.12"}
    payload = {"token": "invalid-reset-token", "new_password": "ResetPass1!"}

    for _ in range(AuthRateLimitService.RESET_PASSWORD_MAX_ATTEMPTS - 1):
        response = client.post(
            "/api/v1/auth/reset-password",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 400

    limited_response = client.post(
        "/api/v1/auth/reset-password",
        json=payload,
        headers=headers,
    )
    assert limited_response.status_code == 429
    assert limited_response.json()["error_code"] == "RATE_LIMITED"
    assert int(limited_response.headers.get("Retry-After", "0")) >= 1


def test_register_duplicate_email_and_username_share_generic_error(client, test_user):
    """Public registration should not reveal whether email or username was duplicated."""
    duplicate_username = client.post(
        "/api/v1/auth/register",
        json={
            "email": "another-register@example.com",
            "username": test_user.username,
            "full_name": "Duplicate Username",
            "password": "Register1!",
        },
    )
    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "username": "another_register_user",
            "full_name": "Duplicate Email",
            "password": "Register1!",
        },
    )

    assert duplicate_username.status_code == 400
    assert duplicate_email.status_code == 400
    assert duplicate_username.json()["detail"] == duplicate_email.json()["detail"]


def test_admin_create_user_duplicate_email_and_username_share_generic_error(
    client,
    admin_headers,
    test_user,
):
    """Admin user creation should not reveal which unique field collided."""
    duplicate_email = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": test_user.email,
            "username": "brand_new_username",
            "full_name": "Duplicate Email User",
            "password": "Password1!",
            "role": "viewer",
        },
    )
    duplicate_username = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "brand-new-email@example.com",
            "username": test_user.username,
            "full_name": "Duplicate Username User",
            "password": "Password1!",
            "role": "viewer",
        },
    )

    assert duplicate_email.status_code == 400
    assert duplicate_username.status_code == 400
    assert duplicate_email.json()["detail"] == duplicate_username.json()["detail"]


def test_accept_invitation_uses_locked_lookup(
    client,
    db,
    test_admin,
    default_tenant,
    monkeypatch,
):
    """Invitation acceptance must use the row-locking lookup path."""
    invitation = Invitation(
        email="invitee-locked@example.com",
        token="locked-invitation-token",
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    locked_lookup_calls: list[str] = []

    def _locked_lookup(self, token: str):
        locked_lookup_calls.append(token)
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def _unexpected_unlocked_lookup(self, _token: str):
        raise AssertionError("accept_invitation should not use the unlocked invitation lookup")

    monkeypatch.setattr(
        "app.api.management.auth.InvitationRepository.get_by_token_for_update",
        _locked_lookup,
    )
    monkeypatch.setattr(
        "app.api.management.auth.InvitationRepository.get_by_token",
        _unexpected_unlocked_lookup,
    )

    response = client.post(
        "/api/v1/auth/invitation/accept",
        json={
            "token": invitation.token,
            "username": "locked_invitee",
            "full_name": "Locked Invitee",
            "password": "Password1!",
        },
    )

    assert response.status_code == 200
    assert locked_lookup_calls == [invitation.token]

    db.refresh(invitation)
    assert invitation.status == InvitationStatus.ACCEPTED
    assert invitation.created_user_id is not None


def test_accept_invitation_supports_hashed_token_storage(
    client,
    db,
    test_admin,
    default_tenant,
):
    """Invitation acceptance should work when the DB stores only the token hash."""
    raw_token = "hashed-accept-token"
    invitation = Invitation(
        email="invitee-hashed@example.com",
        token=hash_invitation_token(raw_token),
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    response = client.post(
        "/api/v1/auth/invitation/accept",
        json={
            "token": raw_token,
            "username": "hashed_invitee",
            "full_name": "Hashed Invitee",
            "password": "Password1!",
        },
    )

    assert response.status_code == 200
    db.refresh(invitation)
    assert invitation.status == InvitationStatus.ACCEPTED
    assert invitation.created_user_id is not None


def test_accept_invitation_duplicate_email_and_username_share_generic_error(
    client,
    db,
    test_admin,
    default_tenant,
    test_user,
):
    """Invitation acceptance should not disclose which account field collided."""
    duplicate_email_invitation = Invitation(
        email=test_user.email,
        token=hash_invitation_token("duplicate-email-invite-token"),
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    duplicate_username_invitation = Invitation(
        email="different-email@example.com",
        token=hash_invitation_token("duplicate-username-invite-token"),
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(duplicate_email_invitation)
    db.add(duplicate_username_invitation)
    db.commit()

    duplicate_email_response = client.post(
        "/api/v1/auth/invitation/accept",
        json={
            "token": "duplicate-email-invite-token",
            "username": "new_invitee_name",
            "full_name": "Duplicate Email Invitee",
            "password": "Password1!",
        },
    )
    duplicate_username_response = client.post(
        "/api/v1/auth/invitation/accept",
        json={
            "token": "duplicate-username-invite-token",
            "username": test_user.username,
            "full_name": "Duplicate Username Invitee",
            "password": "Password1!",
        },
    )

    assert duplicate_email_response.status_code == 400
    assert duplicate_username_response.status_code == 400
    assert duplicate_email_response.json()["detail"] == duplicate_username_response.json()["detail"]


def test_accept_invitation_creates_audit_log(
    client,
    db,
    test_admin,
    default_tenant,
):
    """Invitation acceptance should create an immutable audit trail entry."""
    invitation = Invitation(
        email="invitee-audit@example.com",
        token="audit-invitation-token",
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(invitation)
    db.commit()

    response = client.post(
        "/api/v1/auth/invitation/accept",
        json={
            "token": invitation.token,
            "username": "audit_invitee",
            "full_name": "Audit Invitee",
            "password": "Password1!",
        },
    )

    assert response.status_code == 200

    audit_row = (
        db.query(AuditLog)
        .filter(AuditLog.action == ActionType.CREATE)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_row is not None
    details = json.loads(audit_row.details or "{}")
    assert details["event"] == "invitation_accepted"
    assert details["invitation_id"] == invitation.id
    assert details["email"] == invitation.email
    assert details["role"] == invitation.role.value
    assert details["tenant_id"] == invitation.tenant_id
    assert details["created_user_id"] == audit_row.user_id


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
# H-23 / M-16: Collab token endpoint supports read-only viewers
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
    """Viewers receive a read-only collab token."""
    response = client.post(
        "/api/v1/auth/collab-token",
        headers=viewer_auth_headers,
        json={"document_id": sample_document["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["permissions"] == ["read"]


def test_collab_token_requires_auth(client, sample_document):
    """Unauthenticated requests must be rejected."""
    response = client.post(
        "/api/v1/auth/collab-token",
        json={"document_id": sample_document["id"]},
    )
    assert response.status_code in (401, 403)
