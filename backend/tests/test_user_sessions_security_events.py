"""User session management and security events API tests."""

from datetime import datetime, timedelta

from app.config import settings
from app.models import Invitation, InvitationStatus, PasswordReset, SecurityEvent, UserRole, UserSession
from app.ws.auth import authenticate_ws
from tests.factories.domain import create_user


def _login(
    client,
    *,
    username: str = "testuser",
    password: str = "testpass123",
    headers: dict[str, str] | None = None,
) -> tuple[str, dict]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers=headers or {},
    )
    assert response.status_code == 200
    payload = response.json()
    access_token = payload["access_token"]
    return access_token, {"Authorization": f"Bearer {access_token}"}


def test_login_creates_session_and_lists_active_sessions(client, test_user, db):
    """Successful login should create a user session row and list it."""
    _, auth_headers = _login(
        client,
        headers={"x-forwarded-for": "192.168.10.5", "user-agent": "TestBrowser/2.0"},
    )

    sessions_response = client.get("/api/v1/users/me/sessions", headers=auth_headers)
    assert sessions_response.status_code == 200
    data = sessions_response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["is_current"] is True
    assert data["items"][0]["ip_address"] in {"192.168.10.5", "testclient"}

    assert db.query(UserSession).filter(UserSession.user_id == test_user.id).count() == 1


def test_authenticated_request_updates_session_last_active(client, test_user, db):
    """Any authenticated request should update session last_active_at."""
    _, auth_headers = _login(client)
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == test_user.id, UserSession.revoked_at.is_(None))
        .first()
    )
    assert session is not None

    session.last_active_at = datetime.utcnow() - timedelta(hours=2)
    db.commit()
    previous_last_active = session.last_active_at

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 200

    db.refresh(session)
    assert session.last_active_at > previous_last_active


def test_inactive_session_is_revoked_on_authenticated_request(client, test_user, db):
    """Expired sessions should be persisted as revoked on the first rejected request."""
    access_token, auth_headers = _login(client)
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == test_user.id, UserSession.revoked_at.is_(None))
        .first()
    )
    assert session is not None

    session.last_active_at = datetime.utcnow() - timedelta(days=settings.SESSION_INACTIVITY_DAYS + 1)
    db.commit()

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 401

    db.refresh(session)
    assert session.revoked_at is not None
    _ = access_token


def test_websocket_auth_revokes_inactive_session(client, test_user, db):
    """WebSocket auth should revoke expired sessions in the database too."""
    access_token, _ = _login(client)
    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == test_user.id, UserSession.revoked_at.is_(None))
        .first()
    )
    assert session is not None

    session.last_active_at = datetime.utcnow() - timedelta(days=settings.SESSION_INACTIVITY_DAYS + 1)
    db.commit()

    assert authenticate_ws(access_token, db) is None

    db.refresh(session)
    assert session.revoked_at is not None


def test_revoke_single_session(client, test_user, db):
    """Users can revoke one of their active sessions by id."""
    _, first_auth_headers = _login(client, headers={"user-agent": "Browser/one"})
    _, second_auth_headers = _login(client, headers={"user-agent": "Browser/two"})

    list_response = client.get("/api/v1/users/me/sessions", headers=second_auth_headers)
    assert list_response.status_code == 200
    sessions = list_response.json()["items"]
    assert len(sessions) >= 2

    target_session = next((session for session in sessions if not session["is_current"]), None)
    assert target_session is not None

    revoke_response = client.delete(
        f"/api/v1/users/me/sessions/{target_session['id']}",
        headers=second_auth_headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["message"] == "Session revoked"

    refreshed_sessions = client.get("/api/v1/users/me/sessions", headers=second_auth_headers).json()
    assert all(session["id"] != target_session["id"] for session in refreshed_sessions["items"])

    revoked_session = db.query(UserSession).filter(UserSession.id == target_session["id"]).first()
    assert revoked_session is not None
    assert revoked_session.revoked_at is not None
    assert (
        db.query(SecurityEvent)
        .filter(
            SecurityEvent.user_id == test_user.id,
            SecurityEvent.event_type == "session_revoked",
        )
        .count()
        >= 1
    )
    _ = first_auth_headers


def test_revoke_all_other_sessions_keeps_current(client, test_user, db):
    """Bulk revoke should keep only the current session active."""
    _, _ = _login(client, headers={"user-agent": "Browser/alpha"})
    _, current_auth_headers = _login(client, headers={"user-agent": "Browser/beta"})

    revoke_all_response = client.delete("/api/v1/users/me/sessions", headers=current_auth_headers)
    assert revoke_all_response.status_code == 200
    assert revoke_all_response.json()["revoked_count"] >= 1

    list_response = client.get("/api/v1/users/me/sessions", headers=current_auth_headers)
    assert list_response.status_code == 200
    sessions = list_response.json()["items"]
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True
    assert (
        db.query(SecurityEvent)
        .filter(
            SecurityEvent.user_id == test_user.id,
            SecurityEvent.event_type == "sessions_revoked_all",
        )
        .count()
        >= 1
    )
    _ = test_user


def test_security_events_endpoint_paginated(client, test_user, db, monkeypatch):
    """Security events endpoint should return paginated new_device_login events."""
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["testclient"])

    _login(
        client,
        headers={"x-forwarded-for": "10.11.0.1", "user-agent": "BrowserA/1.0"},
    )
    _login(
        client,
        headers={"x-forwarded-for": "10.11.0.2", "user-agent": "BrowserA/1.0"},
    )
    _, auth_headers = _login(
        client,
        headers={"x-forwarded-for": "10.11.0.3", "user-agent": "BrowserA/1.0"},
    )

    events_response = client.get(
        "/api/v1/users/me/security-events",
        params={"page": 1, "page_size": 1},
        headers=auth_headers,
    )
    assert events_response.status_code == 200
    payload = events_response.json()
    assert payload["total"] >= 2
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_type"] == "new_device_login"

    assert (
        db.query(SecurityEvent)
        .filter(
            SecurityEvent.user_id == test_user.id,
            SecurityEvent.event_type == "new_device_login",
        )
        .count()
        >= 2
    )


def test_role_change_revokes_existing_user_sessions_immediately(
    client,
    db,
    admin_headers,
    default_tenant,
):
    """Demoting a user should immediately kill their access and refresh tokens."""
    target_user = create_user(
        db,
        email="demote-me@example.com",
        username="demote_me",
        full_name="Demote Me",
        plain_password="AdminPass1!",
        role=UserRole.ADMIN,
        tenant_id=default_tenant.id,
        is_active=True,
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": target_user.username, "password": "AdminPass1!"},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    access_headers = {"Authorization": f"Bearer {payload['access_token']}"}
    refresh_token = payload["refresh_token"]

    assert client.get("/api/v1/auth/me", headers=access_headers).status_code == 200

    demote_response = client.put(
        f"/api/v1/users/{target_user.id}",
        headers=admin_headers,
        json={"role": "editor"},
    )
    assert demote_response.status_code == 200
    assert demote_response.json()["role"] == "editor"

    me_after_demote = client.get("/api/v1/auth/me", headers=access_headers)
    assert me_after_demote.status_code == 401

    refresh_after_demote = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_after_demote.status_code == 401

    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == target_user.id)
        .order_by(UserSession.id.desc())
        .first()
    )
    assert session is not None
    assert session.revoked_at is not None

    active_refresh_tokens = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.user_id == target_user.id,
            PasswordReset.used_at.is_(None),
        )
        .count()
    )
    assert active_refresh_tokens == 0


def test_delete_user_revokes_sessions_refresh_tokens_and_pending_invitations(
    client,
    db,
    admin_headers,
    default_tenant,
):
    """DELETE /users/{id} should mirror deactivation cleanup, not just flip is_active."""
    target_user = create_user(
        db,
        email="delete-me@example.com",
        username="delete_me",
        full_name="Delete Me",
        plain_password="DeletePass1!",
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        is_active=True,
    )
    invitation = Invitation(
        email="pending-delete-invite@example.com",
        token="delete-user-pending-invite-token",
        role=UserRole.VIEWER,
        tenant_id=default_tenant.id,
        invited_by=target_user.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(target_user)
    db.refresh(invitation)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": target_user.username, "password": "DeletePass1!"},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    access_headers = {"Authorization": f"Bearer {payload['access_token']}"}
    refresh_token = payload["refresh_token"]

    delete_response = client.delete(
        f"/api/v1/users/{target_user.id}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 204

    me_after_delete = client.get("/api/v1/auth/me", headers=access_headers)
    assert me_after_delete.status_code == 401

    refresh_after_delete = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_after_delete.status_code == 401

    db.refresh(target_user)
    db.refresh(invitation)
    assert target_user.is_active is False
    assert invitation.status == InvitationStatus.CANCELLED

    session = (
        db.query(UserSession)
        .filter(UserSession.user_id == target_user.id)
        .order_by(UserSession.id.desc())
        .first()
    )
    assert session is not None
    assert session.revoked_at is not None

    active_refresh_tokens = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.user_id == target_user.id,
            PasswordReset.used_at.is_(None),
        )
        .count()
    )
    assert active_refresh_tokens == 0
