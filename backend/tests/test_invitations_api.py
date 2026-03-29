"""Regression tests for invitation tenant-assignment rules."""

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import sessionmaker

from app.auth_context.invitation_tokens import hash_invitation_token
from app.models import Invitation, InvitationEmailDeliveryStatus, InvitationStatus, UserRole
from app.services.email_service import EmailSendResult


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
            invitation_id: int,
            to_email: str,
            accept_url: str,
            inviter_name: str,
            expires_days: int,
            message: str | None,
        ) -> None:
            captured_email["invitation_id"] = str(invitation_id)
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
        assert captured_email["invitation_id"] == str(invitation.id)
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
            invitation_id: int,
            to_email: str,
            accept_url: str,
            inviter_name: str,
            expires_days: int,
            message: str | None,
        ) -> None:
            captured_email["invitation_id"] = str(invitation_id)
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
        assert captured_email["invitation_id"] == str(invitation.id)
        assert captured_email["message"] == "Please join"

    def test_get_invitation_email_preview_redacts_live_token(
        self,
        client,
        admin_headers,
        monkeypatch,
    ):
        monkeypatch.setattr(
            "app.api.management.invitations._send_invitation_email_task",
            lambda *args, **kwargs: None,
        )

        response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "preview-invite@example.com",
                "role": "viewer",
                "message": "Welcome aboard",
            },
        )

        assert response.status_code == 201
        invitation_id = response.json()["id"]

        preview_response = client.get(
            f"/api/v1/invitations/{invitation_id}/email-preview",
            headers=admin_headers,
        )

        assert preview_response.status_code == 200
        payload = preview_response.json()
        assert payload["invitation_id"] == invitation_id
        assert payload["email"] == "preview-invite@example.com"
        assert "preview-token-redacted" in payload["preview_accept_url"]
        assert "preview-token-redacted" in payload["html_content"]
        assert "preview-token-redacted" in payload["text_content"]
        assert payload["subject"] == "Admin User invited you to Documentation Platform"

    def test_create_invitation_records_failed_delivery_metadata(
        self,
        client,
        db,
        admin_headers,
        monkeypatch,
    ):
        fixed_attempted_at = datetime(2026, 3, 27, 10, 30, 0)
        background_session_factory = sessionmaker(
            bind=db.get_bind(),
            autocommit=False,
            autoflush=False,
        )

        async def _fail_invitation_email(**kwargs):
            return EmailSendResult(
                status="failed",
                attempted_at=fixed_attempted_at,
                attempt_count=3,
                subject="Admin User invited you to Documentation Platform",
                sender_email="mailer@example.com",
                sender_name="Mailer",
                error_message="SMTP timeout",
            )

        monkeypatch.setattr(
            "app.api.management.invitations._background_session_factory",
            background_session_factory,
        )
        monkeypatch.setattr(
            "app.api.management.invitations.email_service.send_invitation_detailed",
            _fail_invitation_email,
        )

        response = client.post(
            "/api/v1/invitations",
            headers=admin_headers,
            json={
                "email": "delivery-fail@example.com",
                "role": "viewer",
            },
        )

        assert response.status_code == 201
        invitation_id = response.json()["id"]

        db.expire_all()
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        assert invitation is not None
        assert invitation.email_delivery_status == InvitationEmailDeliveryStatus.FAILED
        assert invitation.email_delivery_attempt_count == 3
        assert invitation.email_last_attempted_at == fixed_attempted_at
        assert invitation.email_last_error == "SMTP timeout"
        assert invitation.email_last_subject == "Admin User invited you to Documentation Platform"
        assert invitation.email_last_sender_email == "mailer@example.com"
        assert invitation.email_last_sender_name == "Mailer"

        detail_response = client.get(
            f"/api/v1/invitations/{invitation_id}",
            headers=admin_headers,
        )
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["email_delivery_status"] == "failed"
        assert detail_payload["email_delivery_attempt_count"] == 3
        assert detail_payload["email_last_error"] == "SMTP timeout"
