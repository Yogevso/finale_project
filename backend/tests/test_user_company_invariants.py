"""Regression tests for customer-company invariants across user/company flows."""


class TestUserCompanyInvariants:
    def test_admin_create_customer_defaults_to_admin_tenant(
        self, client, db, admin_headers, test_admin, test_tenant
    ):
        test_admin.tenant_id = test_tenant.id
        db.commit()

        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": "customer-default-tenant@example.com",
                "username": "customer_default_tenant",
                "full_name": "Customer Default Tenant",
                "password": "password123",
                "role": "customer",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["role"] == "customer"
        assert payload["tenant_id"] == test_tenant.id

    def test_system_admin_cannot_clear_customer_tenant_via_update(
        self, client, system_admin_headers, test_customer
    ):
        response = client.put(
            f"/api/v1/users/{test_customer.id}",
            headers=system_admin_headers,
            json={"tenant_id": None},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Customers must be assigned to a company"

    def test_customer_to_non_customer_transition_can_clear_tenant(
        self, client, system_admin_headers, test_customer
    ):
        response = client.put(
            f"/api/v1/users/{test_customer.id}",
            headers=system_admin_headers,
            json={"role": "editor", "tenant_id": None},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["role"] == "editor"
        assert payload["tenant_id"] is None

    def test_remove_user_from_company_blocks_customer_role(
        self, client, system_admin_headers, test_customer, test_tenant
    ):
        response = client.delete(
            f"/api/v1/companies/{test_tenant.id}/users/{test_customer.id}",
            headers=system_admin_headers,
        )
        assert response.status_code == 400
        assert "Customers must be assigned to a company" in response.json()["detail"]

    def test_transition_to_customer_requires_tenant_or_same_request_assignment(
        self, client, system_admin_headers, test_user, test_tenant
    ):
        fail_response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=system_admin_headers,
            json={"role": "customer"},
        )
        assert fail_response.status_code == 400
        assert fail_response.json()["detail"] == "Customers must be assigned to a company"

        success_response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=system_admin_headers,
            json={"role": "customer", "tenant_id": test_tenant.id},
        )
        assert success_response.status_code == 200
        payload = success_response.json()
        assert payload["role"] == "customer"
        assert payload["tenant_id"] == test_tenant.id
