"""Regression tests for auth/portal behavior when a company is deactivated."""


class TestCompanyDeactivationAccess:
    def test_login_denied_for_user_in_inactive_company(
        self, client, db, test_customer, test_tenant
    ):
        test_tenant.is_active = False
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "customer1", "password": "customer123"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Company is inactive"

    def test_existing_access_token_blocked_after_company_deactivation(
        self, client, db, customer_headers, test_tenant
    ):
        test_tenant.is_active = False
        db.commit()

        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "Company is inactive"

    def test_refresh_token_denied_after_company_deactivation(
        self, client, db, test_customer, test_tenant
    ):
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "customer1", "password": "customer123"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        test_tenant.is_active = False
        db.commit()

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 403
        assert refresh_response.json()["detail"] == "Company is inactive"

    def test_system_admin_login_not_blocked_by_other_company_deactivation(
        self, client, db, test_tenant, test_system_admin
    ):
        test_tenant.is_active = False
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "sysadmin", "password": "sysadmin123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
