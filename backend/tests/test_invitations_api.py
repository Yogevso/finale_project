"""Regression tests for invitation tenant-assignment rules."""


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
