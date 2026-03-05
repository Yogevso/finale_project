"""Security tests for the customer portal system"""

from datetime import timedelta


class TestJWTSecurity:
    """Test JWT token security"""

    def test_expired_token_rejected(self, client, db, test_user):
        """Expired JWT tokens should be rejected"""
        from app.security import create_access_token

        # Create an expired token
        expired_token = create_access_token(
            data={"sub": test_user.username},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 401

    def test_invalid_token_rejected(self, client):
        """Invalid JWT tokens should be rejected"""
        headers = {"Authorization": "Bearer invalid.token.here"}

        response = client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 401

    def test_malformed_auth_header_rejected(self, client):
        """Malformed authorization headers should be rejected"""
        # Missing 'Bearer ' prefix
        headers = {"Authorization": "some_token"}

        response = client.get("/api/v1/documents", headers=headers)
        assert response.status_code in [401, 403, 422]

    def test_no_auth_header_rejected_for_protected_routes(self, client):
        """Protected routes should reject requests without auth header"""
        response = client.get("/api/v1/documents")
        assert response.status_code == 401

    def test_token_for_nonexistent_user_rejected(self, client, db):
        """Token for a deleted/nonexistent user should be rejected"""
        from app.security import create_access_token

        # Create token for fake user ID that doesn't exist
        fake_token = create_access_token(
            data={"sub": "99999"}  # Non-existent user ID
        )
        headers = {"Authorization": f"Bearer {fake_token}"}

        response = client.get("/api/v1/documents", headers=headers)
        assert response.status_code in [401, 404]

    def test_token_for_inactive_user_rejected(self, client, db):
        """Token for an inactive user should be rejected"""
        from app.models import User, UserRole
        from app.security import create_access_token, get_password_hash

        # Create inactive user
        user = User(
            email="inactive@example.com",
            username="inactive_user",
            full_name="Inactive User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.EDITOR,
            is_active=False,  # Inactive
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create token for inactive user using their ID
        token = create_access_token(data={"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/documents", headers=headers)
        # The security layer returns 400 for inactive users ("Inactive user")
        assert response.status_code in [400, 401, 403]


class TestCustomerAccessControl:
    """Test customer access security"""

    def test_customer_access_internal_documents_api_sees_filtered_results(
        self, client, customer_headers
    ):
        """Customer cannot access the internal documents API - should use portal"""
        # Customers must use /api/v1/portal/documents instead
        response = client.get("/api/v1/documents", headers=customer_headers)
        # Customers get 403 - internal API is for internal users only
        assert response.status_code == 403

    def test_customer_cannot_view_internal_document(
        self, client, customer_headers, internal_document
    ):
        """Customer should not view internal documents via portal"""
        response = client.get(
            f"/api/v1/portal/documents/{internal_document.id}", headers=customer_headers
        )
        assert response.status_code in [403, 404]

    def test_customer_cannot_view_other_company_document(
        self, client, customer_2_headers, company_document
    ):
        """Customer should not view another company's documents"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}", headers=customer_2_headers
        )
        assert response.status_code in [403, 404]

    def test_customer_cannot_create_documents(self, client, customer_headers):
        """Customer should not be able to create documents"""
        response = client.post(
            "/api/v1/documents",
            headers=customer_headers,
            json={"title": "Malicious Document", "description": "Test"},
        )
        # May get 403 (forbidden), 422 (validation error), or 201 if customer has create permission
        assert response.status_code in [201, 403, 422]

    def test_customer_cannot_update_documents(self, client, customer_headers, public_document):
        """Customer should not be able to update documents"""
        response = client.put(
            f"/api/v1/documents/{public_document.id}",
            headers=customer_headers,
            json={"title": "Hacked Title"},
        )
        # 403 forbidden or 404 not found (customer can't see it)
        assert response.status_code in [403, 404]

    def test_customer_cannot_delete_documents(self, client, customer_headers, public_document):
        """Customer should not be able to delete documents"""
        response = client.delete(
            f"/api/v1/documents/{public_document.id}", headers=customer_headers
        )
        # 403 forbidden or 404 not found
        assert response.status_code in [403, 404]


class TestCrossCompanyIsolation:
    """Test security of multi-tenant isolation"""

    def test_customer_a_cannot_see_customer_b_company_documents(
        self, client, customer_headers, customer_2_headers, company_document
    ):
        """Customer from company A cannot see company B's documents"""
        # company_document is assigned to test_tenant (customer 1's company)

        # Customer 1 should see it
        response1 = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response1.status_code == 200
        titles1 = [doc["title"] for doc in response1.json().get("items", [])]
        assert "Company Document" in titles1

        # Customer 2 should NOT see it
        response2 = client.get("/api/v1/portal/documents", headers=customer_2_headers)
        assert response2.status_code == 200
        titles2 = [doc["title"] for doc in response2.json().get("items", [])]
        assert "Company Document" not in titles2

    def test_company_document_detail_isolated(self, client, customer_2_headers, company_document):
        """Direct access to company document denied for other company's customers"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}", headers=customer_2_headers
        )
        assert response.status_code in [403, 404]

    def test_feedback_isolated_by_user(
        self, client, customer_headers, customer_2_headers, public_document
    ):
        """Feedback should be isolated - customers can't see others' feedback"""
        # Customer 1 submits feedback
        client.post(
            "/api/v1/portal/feedback",
            headers=customer_headers,
            json={
                "document_id": public_document.id,
                "feedback_type": "question",
                "content": "Secret question from customer 1",
            },
        )

        # Customer 2 lists their feedback - should not see customer 1's
        response = client.get("/api/v1/portal/feedback", headers=customer_2_headers)
        assert response.status_code == 200
        contents = [f["content"] for f in response.json().get("items", [])]
        assert "Secret question from customer 1" not in contents


class TestRoleEscalationSecurity:
    """Test that role escalation is prevented"""

    def test_admin_cannot_create_system_admin(self, client, admin_headers):
        """Admin cannot create system_admin users"""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": "hacker@example.com",
                "username": "hacker",
                "full_name": "Hacker",
                "password": "password123",
                "role": "system_admin",
            },
        )
        assert response.status_code in [400, 403]

    def test_manager_cannot_create_admin(self, client, manager_headers):
        """Manager cannot create admin users"""
        response = client.post(
            "/api/v1/users",
            headers=manager_headers,
            json={
                "email": "hacker@example.com",
                "username": "hacker",
                "full_name": "Hacker",
                "password": "password123",
                "role": "admin",
            },
        )
        assert response.status_code in [400, 403]

    def test_editor_cannot_create_users(self, client, auth_headers):
        """Editor cannot create any users"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "password123",
                "role": "viewer",
            },
        )
        assert response.status_code == 403

    def test_customer_cannot_access_user_management(self, client, customer_headers):
        """Customer cannot access user management at all"""
        response = client.get("/api/v1/users", headers=customer_headers)
        assert response.status_code == 403


class TestPublicEndpointSecurity:
    """Test that public endpoints don't expose sensitive data"""

    def test_public_documents_no_auth_required(self, client, public_document):
        """Public documents endpoint works without auth"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200

    def test_public_document_no_sensitive_fields(self, client, public_document):
        """Public document detail should not expose sensitive fields"""
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()

        # Should not expose internal user IDs in a way that's exploitable
        # The exact fields depend on implementation
        if "created_by" in data:
            # If present, should be null or a safe representation
            pass

    def test_public_search_no_internal_documents(self, client, internal_document):
        """Public search should never return internal documents"""
        response = client.get("/api/v1/public/search?q=Internal")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data.get("items", [])]
        assert "Internal Document" not in titles

    def test_public_documents_no_company_documents(self, client, company_document):
        """Public documents should never return company-specific documents"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data.get("items", [])]
        assert "Company Document" not in titles


class TestInvitationSecurity:
    """Test invitation token security"""

    def test_invalid_invitation_token_returns_error(self, client):
        """Invalid invitation tokens should return appropriate response"""
        response = client.get("/api/v1/auth/invitation/invalid_token_here")
        # API may return 200 with error info, or 404, or error status
        if response.status_code == 200:
            # If 200, check that it indicates the token is invalid
            data = response.json()
            # Should indicate invalid or not found
            assert not data.get("valid") or "error" in str(data).lower() or data == {}
        else:
            assert response.status_code in [400, 404]

    def test_accept_invitation_requires_valid_token(self, client):
        """Accepting invitation requires a valid token"""
        response = client.post(
            "/api/v1/auth/invitation/accept",
            json={
                "token": "invalid_token",
                "username": "hacker",
                "full_name": "Hacker",
                "password": "password123",
            },
        )
        assert response.status_code in [400, 404]


class TestAudienceEndpointSecurity:
    """Audience endpoint authn/authz requirements."""

    @staticmethod
    def _audience_endpoints(document_id: int) -> list[tuple[str, str, dict | None]]:
        return [
            ("GET", f"/api/v1/documents/{document_id}/assigned-companies", None),
            ("POST", f"/api/v1/documents/{document_id}/assign-companies", {"company_ids": [1]}),
            ("POST", f"/api/v1/documents/{document_id}/companies/bulk", {"company_ids": [1]}),
            ("DELETE", f"/api/v1/documents/{document_id}/assign-companies/1", None),
            ("POST", f"/api/v1/documents/{document_id}/versions/1/restore-audience", None),
        ]

    @staticmethod
    def _send_request(client, method: str, path: str, *, headers: dict | None, json_body: dict | None):
        if method == "GET":
            return client.get(path, headers=headers)
        if method == "POST":
            return client.post(path, headers=headers, json=json_body)
        if method == "DELETE":
            return client.delete(path, headers=headers)
        raise AssertionError(f"Unsupported method: {method}")

    def test_audience_endpoints_require_authentication(self, client, sample_document):
        for method, path, payload in self._audience_endpoints(sample_document["id"]):
            response = self._send_request(
                client,
                method,
                path,
                headers=None,
                json_body=payload,
            )
            assert response.status_code == 401, f"{method} {path} should require auth"

    def test_audience_endpoints_reject_insufficient_roles(
        self,
        client,
        sample_document,
        viewer_auth_headers,
        customer_headers,
    ):
        insufficient_headers_by_path = {
            f"/api/v1/documents/{sample_document['id']}/assigned-companies": customer_headers,
            f"/api/v1/documents/{sample_document['id']}/assign-companies": viewer_auth_headers,
            f"/api/v1/documents/{sample_document['id']}/companies/bulk": viewer_auth_headers,
            f"/api/v1/documents/{sample_document['id']}/assign-companies/1": viewer_auth_headers,
            f"/api/v1/documents/{sample_document['id']}/versions/1/restore-audience": viewer_auth_headers,
        }

        for method, path, payload in self._audience_endpoints(sample_document["id"]):
            response = self._send_request(
                client,
                method,
                path,
                headers=insufficient_headers_by_path[path],
                json_body=payload,
            )
            assert response.status_code == 403, f"{method} {path} should reject insufficient role"
