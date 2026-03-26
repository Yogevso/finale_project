"""Admin user-management recovery and notification flows."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app.config import settings
from app.models import Notification, NotificationType, User, UserRole
from tests.factories.domain import create_user


def test_admin_created_user_requires_email_verification(
    client,
    db,
    admin_headers,
    default_tenant,
    monkeypatch,
):
    """Admin-created users should receive verification flow before first login."""
    captured_verification_url: dict[str, str] = {}

    def _capture_email_verification(
        _to_email: str,
        verification_url: str,
        _expires_minutes: int,
    ) -> None:
        captured_verification_url["url"] = verification_url

    monkeypatch.setattr(settings, "BASE_URL", "http://frontend.test")
    monkeypatch.setattr(
        "app.api.management.users._send_email_verification_task",
        _capture_email_verification,
    )

    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "managed-user@example.com",
            "username": "managed_user",
            "full_name": "Managed User",
            "password": "ManagedPass1!",
            "role": "viewer",
            "tenant_id": default_tenant.id,
        },
    )

    assert response.status_code == 201
    assert captured_verification_url["url"].startswith(
        "http://frontend.test/api/v1/auth/verify-email?token="
    )

    created_user = db.query(User).filter(User.username == "managed_user").first()
    assert created_user is not None
    assert created_user.is_email_verified is False
    assert created_user.email_verification_token_hash is not None

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "managed_user", "password": "ManagedPass1!"},
    )
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "email_not_verified"


def test_admin_force_password_reset_returns_manual_reset_link_when_email_disabled(
    client,
    db,
    admin_headers,
    default_tenant,
    monkeypatch,
):
    """Admins should be able to recover locked users even without outbound email."""
    target_user = create_user(
        db,
        email="locked-user@example.com",
        username="locked_user",
        full_name="Locked User",
        plain_password="LockedPass1!",
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
        is_active=True,
    )
    target_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
    target_user.failed_login_attempts = 5
    db.commit()

    monkeypatch.setattr(settings, "BASE_URL", "http://frontend.test")
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)

    response = client.post(
        f"/api/v1/admin/users/{target_user.id}/force-password-reset",
        headers=admin_headers,
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["email_sent"] is False
    assert payload["expires_minutes"] == settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    assert payload["reset_url"].startswith("http://frontend.test/reset-password?token=")

    reset_token = parse_qs(urlparse(payload["reset_url"]).query)["token"][0]
    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "RecoveredPass1!"},
    )
    assert reset_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "locked_user", "password": "RecoveredPass1!"},
    )
    assert login_response.status_code == 200


def test_role_change_creates_user_notification(
    client,
    db,
    admin_headers,
    default_tenant,
):
    """Role changes should notify the affected user about updated permissions."""
    target_user = create_user(
        db,
        email="role-change@example.com",
        username="role_change_user",
        full_name="Role Change User",
        plain_password="RoleChange1!",
        role=UserRole.VIEWER,
        tenant_id=default_tenant.id,
        is_active=True,
    )

    response = client.put(
        f"/api/v1/users/{target_user.id}",
        headers=admin_headers,
        json={"role": "editor"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "editor"

    notification = (
        db.query(Notification)
        .filter(Notification.user_id == target_user.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.type == NotificationType.SYSTEM
    assert notification.title == "Your access role changed"
    assert "viewer" in (notification.message or "")
    assert "editor" in (notification.message or "")
    assert notification.link == "/profile"
