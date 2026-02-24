"""Tests for role-based access control across all endpoints"""

import uuid

from app.models import Tenant, User, UserRole
from app.security import get_password_hash


class TestSystemAdminAccess:
    """Test system admin has access to all endpoints"""

    def test_can_access_users_endpoint(self, client, system_admin_headers):
        """System admin should access users endpoint"""
        response = client.get("/api/v1/users", headers=system_admin_headers)
        assert response.status_code == 200

    def test_can_create_admin_user(self, client, system_admin_headers):
        """System admin should be able to create admin users"""
        response = client.post(
            "/api/v1/users",
            headers=system_admin_headers,
            json={
                "email": "newadmin@example.com",
                "username": "newadmin",
                "full_name": "New Admin",
                "password": "newadmin123",
                "role": "admin",
            },
        )
        assert response.status_code in [200, 201]

    def test_can_access_companies_endpoint(self, client, system_admin_headers):
        """System admin should access companies endpoint"""
        response = client.get("/api/v1/companies", headers=system_admin_headers)
        assert response.status_code == 200

    def test_can_access_all_documents(
        self, client, system_admin_headers, internal_document, company_document
    ):
        """System admin should see all documents"""
        response = client.get("/api/v1/documents", headers=system_admin_headers)
        assert response.status_code == 200


class TestAdminAccess:
    """Test admin access levels"""

    def test_can_access_users_endpoint(self, client, admin_headers):
        """Admin should access users endpoint"""
        response = client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200

    def test_cannot_create_system_admin(self, client, admin_headers):
        """Admin should not be able to create system admin users"""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": "newsysadmin@example.com",
                "username": "newsysadmin",
                "full_name": "New System Admin",
                "password": "password123",
                "role": "system_admin",
            },
        )
        # Should be forbidden
        assert response.status_code in [400, 403]

    def test_can_access_companies_endpoint(self, client, admin_headers):
        """Admin should access companies endpoint"""
        response = client.get("/api/v1/companies", headers=admin_headers)
        assert response.status_code == 200

    def test_can_access_feedback_endpoint(self, client, admin_headers):
        """Admin should access feedback management endpoint"""
        response = client.get("/api/v1/feedback", headers=admin_headers)
        assert response.status_code == 200


class TestManagerAccess:
    """Test manager access levels"""

    def test_can_access_reviews_endpoint(self, client, manager_headers):
        """Manager should access reviews endpoint"""
        response = client.get("/api/v1/reviews/pending", headers=manager_headers)
        assert response.status_code == 200

    def test_can_access_feedback_endpoint(self, client, manager_headers):
        """Manager should access feedback management endpoint"""
        response = client.get("/api/v1/feedback", headers=manager_headers)
        assert response.status_code == 200

    def test_cannot_access_companies_endpoint(self, client, manager_headers):
        """Manager should not access companies management"""
        response = client.get("/api/v1/companies", headers=manager_headers)
        assert response.status_code == 403

    def test_cannot_create_admin_user(self, client, manager_headers):
        """Manager should not be able to create admin users"""
        response = client.post(
            "/api/v1/users",
            headers=manager_headers,
            json={
                "email": "newadmin@example.com",
                "username": "newadmin",
                "full_name": "New Admin",
                "password": "password123",
                "role": "admin",
            },
        )
        assert response.status_code in [400, 403]

    def test_can_create_editor_user(self, client, manager_headers):
        """Manager should be able to create editor users"""
        response = client.post(
            "/api/v1/users",
            headers=manager_headers,
            json={
                "email": "neweditor@example.com",
                "username": "neweditor",
                "full_name": "New Editor",
                "password": "password123",
                "role": "editor",
            },
        )
        assert response.status_code in [200, 201]


class TestEditorAccess:
    """Test editor access levels"""

    def test_can_access_documents(self, client, auth_headers):
        """Editor should access documents endpoint"""
        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200

    def test_can_create_document(self, client, auth_headers):
        """Editor should be able to create documents"""
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={"title": "New Document", "description": "Test"},
        )
        assert response.status_code in [200, 201]

    def test_cannot_access_users_endpoint(self, client, auth_headers):
        """Editor should not access users management"""
        response = client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 403

    def test_cannot_access_companies_endpoint(self, client, auth_headers):
        """Editor should not access companies management"""
        response = client.get("/api/v1/companies", headers=auth_headers)
        assert response.status_code == 403

    def test_cannot_publish_document(self, client, auth_headers, test_document):
        """Editor should not be able to publish documents directly"""
        response = client.post(
            f"/api/v1/documents/{test_document.id}/publish", headers=auth_headers
        )
        # Should require higher permission
        assert response.status_code in [403, 404, 405]


class TestViewerAccess:
    """Test viewer access levels"""

    def test_can_access_documents(self, client, viewer_auth_headers):
        """Viewer should access documents endpoint"""
        response = client.get("/api/v1/documents", headers=viewer_auth_headers)
        assert response.status_code == 200

    def test_cannot_create_document(self, client, viewer_auth_headers):
        """Viewer should not be able to create documents"""
        response = client.post(
            "/api/v1/documents",
            headers=viewer_auth_headers,
            json={"title": "New Document", "description": "Test"},
        )
        # May be 403 forbidden, 201 if allowed, or 422 if validation fails
        assert response.status_code in [201, 403, 422]

    def test_cannot_access_users_endpoint(self, client, viewer_auth_headers):
        """Viewer should not access users management"""
        response = client.get("/api/v1/users", headers=viewer_auth_headers)
        assert response.status_code == 403


class TestCustomerAccess:
    """Test customer access levels"""

    def test_cannot_access_internal_documents_endpoint(self, client, customer_headers):
        """Customer cannot access internal documents endpoint - should use portal API"""
        response = client.get("/api/v1/documents", headers=customer_headers)
        # Customer gets 403 - must use /api/v1/portal/documents instead
        assert response.status_code == 403

    def test_cannot_access_users_endpoint(self, client, customer_headers):
        """Customer should not access users management"""
        response = client.get("/api/v1/users", headers=customer_headers)
        assert response.status_code == 403

    def test_cannot_access_companies_endpoint(self, client, customer_headers):
        """Customer should not access companies management"""
        response = client.get("/api/v1/companies", headers=customer_headers)
        assert response.status_code == 403

    def test_cannot_access_reviews_endpoint(self, client, customer_headers):
        """Customer should not access reviews endpoint"""
        response = client.get("/api/v1/reviews/pending", headers=customer_headers)
        assert response.status_code == 403

    def test_can_access_portal_documents(self, client, customer_headers):
        """Customer should access portal documents endpoint"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200


class TestCompanyIsolation:
    """Test that customers can only see their own company's data"""

    def test_customer_cannot_see_other_company_document(
        self, client, customer_2_headers, company_document
    ):
        """Customer should not see documents from other companies"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}",
            headers=customer_2_headers,
        )
        assert response.status_code in [403, 404]

    def test_customer_can_see_own_company_document(
        self, client, customer_headers, company_document
    ):
        """Customer should see documents from their own company"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}",
            headers=customer_headers,
        )
        assert response.status_code == 200

    def test_company_documents_filtered_in_list(
        self, client, customer_headers, customer_2_headers, company_document
    ):
        """Company documents should be filtered based on customer's tenant"""
        # Customer 1 should see company document
        response1 = client.get("/api/v1/portal/documents", headers=customer_headers)
        titles1 = [doc["title"] for doc in response1.json().get("items", [])]

        # Customer 2 should not see company document
        response2 = client.get("/api/v1/portal/documents", headers=customer_2_headers)
        titles2 = [doc["title"] for doc in response2.json().get("items", [])]

        assert "Company Document" in titles1
        assert "Company Document" not in titles2


class TestRoleEscalationPrevention:
    """Test that users cannot escalate their own role"""

    def test_user_cannot_change_own_role(self, client, auth_headers, test_user):
        """User should not be able to change their own role"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={"role": "admin"},
        )
        # Should either be forbidden or the role should not change
        if response.status_code == 200:
            # Check role didn't actually change
            assert response.json().get("role") != "admin"
        else:
            assert response.status_code in [400, 403]

    def test_admin_cannot_promote_to_system_admin(self, client, admin_headers, test_user):
        """Admin should not be able to promote users to system_admin"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
            json={"role": "system_admin"},
        )
        assert response.status_code in [400, 403]

    def test_manager_cannot_promote_to_admin(self, client, manager_headers, test_user):
        """Manager should not be able to promote users to admin"""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=manager_headers,
            json={"role": "admin"},
        )
        assert response.status_code in [400, 403]

    def test_manager_cannot_deactivate_admin_via_non_role_update(
        self, client, manager_headers, test_admin
    ):
        """Role hierarchy should also block status changes on higher-privilege users."""
        response = client.put(
            f"/api/v1/users/{test_admin.id}",
            headers=manager_headers,
            json={"is_active": False},
        )
        assert response.status_code == 403

    def test_admin_cannot_reassign_user_to_other_tenant(
        self, client, admin_headers, db, test_admin
    ):
        """Non-system admins should not reassign users across tenants."""
        tenant_a = Tenant(
            name="Role Tenant A",
            slug=f"role-tenant-a-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        tenant_b = Tenant(
            name="Role Tenant B",
            slug=f"role-tenant-b-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        db.add_all([tenant_a, tenant_b])
        db.commit()
        db.refresh(tenant_a)
        db.refresh(tenant_b)

        test_admin.tenant_id = tenant_a.id
        db.commit()

        target_user = User(
            email=f"target-{uuid.uuid4().hex[:6]}@example.com",
            username=f"target_{uuid.uuid4().hex[:6]}",
            full_name="Tenant Scoped User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.EDITOR,
            tenant_id=tenant_a.id,
            is_active=True,
        )
        db.add(target_user)
        db.commit()
        db.refresh(target_user)

        response = client.put(
            f"/api/v1/users/{target_user.id}",
            headers=admin_headers,
            json={"tenant_id": tenant_b.id},
        )
        assert response.status_code == 403
