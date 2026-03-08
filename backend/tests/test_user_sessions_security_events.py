"""User session management and security events API tests."""

from datetime import datetime, timedelta

from app.config import settings
from app.models import SecurityEvent, UserSession


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
