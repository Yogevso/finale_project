"""Regression tests for invitation tenant-assignment rules."""

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app.auth_context.invitation_tokens import hash_invitation_token
from app.models import Invitation, InvitationStatus, UserRole


class TestInvitationTenantAssignment:
    def test_admin_cannot_invite_customer_to_other_tenant(
        self, client, db, admin_headers, test_admin, test_tenant, test_tenant_2
    ):
        test_admin.tenant_id = test_tenant.id
        db.commit()

        response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "cross-tenant-customer@example.com",
                "role": "customer",
                "tenant_id": test_tenant_2.id,
            },
        )
        assert response.status_code == 403

    def test_admin_customer_invite_defaults_to_inviter_tenant(
        self, client, db, admin_headers, test_admin, test_tenant
    ):
        test_admin.tenant_id = test_tenant.id
        db.commit()

        response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "same-tenant-customer@example.com",
                "role": "customer",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["tenant_id"] == test_tenant.id
        assert payload["role"] == "customer"

    def test_manager_cannot_invite_customer_to_other_tenant(
        self, client, db, manager_headers, test_manager, test_tenant, test_tenant_2
    ):
        test_manager.tenant_id = test_tenant.id
        db.commit()

        response = client.post(
            "/api/v1/invitations",
            headers=manager_headers,
            json={
                "email": "manager-cross-tenant@example.com",
                "role": "customer",
                "tenant_id": test_tenant_2.id,
            },
        )
        assert response.status_code == 403

    def test_system_admin_can_invite_customer_to_any_tenant(
        self, client, system_admin_headers, test_tenant_2
    ):
        response = client.post(
            "/api/v1/invitations",
            headers=system_admin_headers,
            json={
                "email": "sysadmin-any-tenant@example.com",
                "role": "customer",
                "tenant_id": test_tenant_2.id,
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["tenant_id"] == test_tenant_2.id
        assert payload["role"] == "customer"

    def test_create_invitation_uses_generic_conflict_detail(
        self,
        client,
        db,
        admin_headers,
        test_user,
    ):
        existing_user_response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": test_user.email,
                "role": "viewer",
            },
        )

        pending_invitation_response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "pending-invite@example.com",
                "role": "viewer",
            },
        )
        assert pending_invitation_response.status_code == 201

        duplicate_pending_response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "pending-invite@example.com",
                "role": "viewer",
            },
        )

        assert existing_user_response.status_code == 400
        assert duplicate_pending_response.status_code == 400
        assert existing_user_response.json()["detail"] == duplicate_pending_response.json()["detail"]

    def test_create_invitation_stores_hashed_token_and_sanitized_message(
        self,
        client,
        db,
        admin_headers,
        monkeypatch,
    ):
        captured_email: dict[str, str | None] = {}

        def _capture_invitation_email(
            to_email: str,
            accept_url: str,
            inviter_name: str,
            expires_days: int,
            message: str | None,
        ) -> None:
            captured_email["to_email"] = to_email
            captured_email["accept_url"] = accept_url
            captured_email["inviter_name"] = inviter_name
            captured_email["expires_days"] = str(expires_days)
            captured_email["message"] = message

        monkeypatch.setattr(
            "app.api.management.invitations._send_invitation_email_task",
            _capture_invitation_email,
        )

        response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "sanitized-invite@example.com",
                "role": "viewer",
                "message": '<script>alert("x")</script><b>Hello</b> team',
            },
        )

        assert response.status_code == 201
        invitation = db.query(Invitation).filter(Invitation.id == response.json()["id"]).first()
        assert invitation is not None

        raw_token = parse_qs(urlparse(str(captured_email["accept_url"])).query)["token"][0]
        assert invitation.token == hash_invitation_token(raw_token)
        assert invitation.token != raw_token
        assert invitation.message == "Hello team"
        assert captured_email["message"] == "Hello team"
        assert response.json()["message"] == "Hello team"

    def test_resend_invitation_sends_new_email_with_new_raw_token(
        self,
        client,
        db,
        admin_headers,
        test_admin,
        default_tenant,
        monkeypatch,
    ):
        invitation = Invitation(
            email="resend-invite@example.com",
            token=hash_invitation_token("old-resend-token"),
            role=UserRole.VIEWER,
            tenant_id=default_tenant.id,
            invited_by=test_admin.id,
            status=InvitationStatus.PENDING,
            message="Please join",
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        old_stored_token = invitation.token

        captured_email: dict[str, str | None] = {}

        def _capture_invitation_email(
            to_email: str,
            accept_url: str,
            inviter_name: str,
            expires_days: int,
            message: str | None,
        ) -> None:
            captured_email["to_email"] = to_email
            captured_email["accept_url"] = accept_url
            captured_email["inviter_name"] = inviter_name
            captured_email["expires_days"] = str(expires_days)
            captured_email["message"] = message

        monkeypatch.setattr(
            "app.api.management.invitations._send_invitation_email_task",
            _capture_invitation_email,
        )

        response = client.post(
            f"/api/v1/invitations/{invitation.id}/resend",
            headers=admin_headers,
        )

        assert response.status_code == 200
        db.refresh(invitation)
        raw_token = parse_qs(urlparse(str(captured_email["accept_url"])).query)["token"][0]
        assert invitation.token == hash_invitation_token(raw_token)
        assert invitation.token != old_stored_token
        assert captured_email["message"] == "Please join"
