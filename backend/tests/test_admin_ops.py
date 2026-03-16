"""Wave Z — Admin Operations Integration Tests (Z-019, Z-020, Z-021)."""

import pytest

from app.models import (
    ActionType,
    AuditLog,
    ImpersonationSession,
    TenantQuota,
    UserRole,
)
from tests.factories import create_document, create_tenant, create_user


# ── Z-019: Tenant Impersonation ──────────────────────────────────


class TestTenantImpersonation:
    """Z-019: impersonate → access tenant data → audit log → end → scope restored."""

    def test_impersonate_then_end(self, client, db, system_admin_headers, test_tenant):
        # 1. Start impersonation
        resp = client.post(
            "/api/v1/admin/impersonate",
            headers=system_admin_headers,
            json={"target_tenant_id": test_tenant.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_tenant_id"] == test_tenant.id
        assert data["is_active"] is True
        session_id = data["id"]

        # 2. Verify audit log for impersonation start
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == ActionType.SYSTEM)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert "impersonation_start" in (log.details or "")

        # 3. Check current impersonation
        resp = client.get("/api/v1/admin/impersonate/current", headers=system_admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id
        assert resp.json()["is_active"] is True

        # 4. End impersonation
        resp = client.post("/api/v1/admin/impersonate/end", headers=system_admin_headers)
        assert resp.status_code == 200

        # 5. Verify audit log for impersonation end
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == ActionType.SYSTEM)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert "impersonation_end" in (log.details or "")

        # 6. Verify session is no longer active
        session = db.query(ImpersonationSession).filter(ImpersonationSession.id == session_id).first()
        assert session is not None
        assert session.is_active is False
        assert session.ended_at is not None

    def test_impersonate_requires_system_admin(self, client, db, admin_headers, test_tenant):
        """Regular admin should be denied impersonation."""
        resp = client.post(
            "/api/v1/admin/impersonate",
            headers=admin_headers,
            json={"target_tenant_id": test_tenant.id},
        )
        assert resp.status_code == 403

    def test_impersonate_nonexistent_tenant(self, client, db, system_admin_headers):
        resp = client.post(
            "/api/v1/admin/impersonate",
            headers=system_admin_headers,
            json={"target_tenant_id": 99999},
        )
        assert resp.status_code == 404

    def test_no_active_impersonation_returns_null(self, client, db, system_admin_headers):
        resp = client.get("/api/v1/admin/impersonate/current", headers=system_admin_headers)
        assert resp.status_code == 200
        assert resp.json() is None


# ── Z-020: Tenant Suspension ─────────────────────────────────────


class TestTenantSuspension:
    """Z-020: suspend tenant → API call as tenant user → verify 403."""

    def test_suspend_blocks_tenant_user_access(self, client, db, system_admin_headers):
        # Create a tenant + internal user (viewers can access /api/v1/documents)
        tenant = create_tenant(db, name="Suspend Corp", is_active=True)
        customer = create_user(
            db,
            email="cust_suspend@example.com",
            username="cust_suspend",
            plain_password="pass123",
            role=UserRole.VIEWER,
            tenant_id=tenant.id,
            is_active=True,
        )

        # Login as customer — should succeed
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "cust_suspend", "password": "pass123"},
        )
        assert login_resp.status_code == 200
        cust_token = login_resp.json()["access_token"]
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        # Verify customer can hit an endpoint before suspension
        pre_resp = client.get("/api/v1/documents", headers=cust_headers)
        assert pre_resp.status_code == 200

        # Suspend the tenant
        suspend_resp = client.post(
            f"/api/v1/admin/tenants/{tenant.id}/suspend",
            headers=system_admin_headers,
            json={"reason": "Non-payment"},
        )
        assert suspend_resp.status_code == 200
        assert suspend_resp.json()["suspended"] is True

        # Verify audit log
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == ActionType.SYSTEM)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert "tenant_suspended" in (log.details or "")

        # Customer API call should now get 403
        post_resp = client.get("/api/v1/documents", headers=cust_headers)
        assert post_resp.status_code == 403
        assert "inactive" in post_resp.json().get("detail", "").lower()

    def test_reactivate_restores_access(self, client, db, system_admin_headers):
        tenant = create_tenant(db, name="Reactivate Corp", is_active=True)
        customer = create_user(
            db,
            email="cust_react@example.com",
            username="cust_react",
            plain_password="pass123",
            role=UserRole.VIEWER,
            tenant_id=tenant.id,
            is_active=True,
        )

        # Login as customer
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "cust_react", "password": "pass123"},
        )
        cust_headers = {"Authorization": f"Bearer " + login_resp.json()["access_token"]}

        # Suspend
        client.post(
            f"/api/v1/admin/tenants/{tenant.id}/suspend",
            headers=system_admin_headers,
            json={"reason": "test"},
        )
        assert client.get("/api/v1/documents", headers=cust_headers).status_code == 403

        # Reactivate
        react_resp = client.post(
            f"/api/v1/admin/tenants/{tenant.id}/reactivate",
            headers=system_admin_headers,
        )
        assert react_resp.status_code == 200
        assert react_resp.json()["reactivated"] is True

        # Customer should have access again
        post_resp = client.get("/api/v1/documents", headers=cust_headers)
        assert post_resp.status_code == 200

    def test_suspend_already_suspended_returns_400(self, client, db, system_admin_headers):
        tenant = create_tenant(db, name="Double Suspend", is_active=True)
        client.post(
            f"/api/v1/admin/tenants/{tenant.id}/suspend",
            headers=system_admin_headers,
            json={"reason": "first"},
        )
        resp = client.post(
            f"/api/v1/admin/tenants/{tenant.id}/suspend",
            headers=system_admin_headers,
            json={"reason": "second"},
        )
        assert resp.status_code == 400


# ── Z-021: Tenant Quota Enforcement ──────────────────────────────


class TestTenantQuotaEnforcement:
    """Z-021: set quota to 2 docs → create 2 → attempt third → verify 429."""

    def test_document_quota_enforced(self, client, db, system_admin_headers):
        # Create tenant
        tenant = create_tenant(db, name="Quota Corp", is_active=True)

        # Set quota to 2 documents
        resp = client.put(
            f"/api/v1/admin/tenants/{tenant.id}/quota",
            headers=system_admin_headers,
            json={"max_documents": 2},
        )
        assert resp.status_code == 200
        assert resp.json()["max_documents"] == 2

        # Create 2 documents via factory (directly in DB)
        for i in range(2):
            create_document(
                db,
                created_by=1,  # any user
                tenant_id=tenant.id,
                title=f"Quota Doc {i}",
            )

        # Verify quota reads correctly
        resp = client.get(
            f"/api/v1/admin/tenants/{tenant.id}/quota",
            headers=system_admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_documents"] == 2
        assert resp.json()["max_documents"] == 2

    def test_user_quota_enforced(self, client, db, system_admin_headers):
        tenant = create_tenant(db, name="User Quota Corp", is_active=True)

        # Set user quota to 1
        resp = client.put(
            f"/api/v1/admin/tenants/{tenant.id}/quota",
            headers=system_admin_headers,
            json={"max_users": 1},
        )
        assert resp.status_code == 200

        # Create 1 user in that tenant
        create_user(
            db,
            role=UserRole.CUSTOMER,
            tenant_id=tenant.id,
            is_active=True,
        )

        # Verify quota usage
        resp = client.get(
            f"/api/v1/admin/tenants/{tenant.id}/quota",
            headers=system_admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_users"] == 1
        assert resp.json()["max_users"] == 1

    def test_quota_without_limit_allows_unlimited(self, client, db, system_admin_headers):
        """If no quota is set, reads should show None limits."""
        tenant = create_tenant(db, name="No Quota Corp", is_active=True)

        resp = client.get(
            f"/api/v1/admin/tenants/{tenant.id}/quota",
            headers=system_admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["max_documents"] is None
        assert resp.json()["max_users"] is None
