import pytest

from app.services.permissions import (
    Permission,
    clear_dynamic_role_permissions,
    get_user_permissions,
    has_permission,
)


@pytest.fixture(autouse=True)
def _clean_dynamic_permissions():
    """Ensure dynamic RBAC overrides never leak to subsequent tests."""
    clear_dynamic_role_permissions()
    yield
    clear_dynamic_role_permissions()


def test_rbac_policy_update_publishes_dynamic_permissions(client, test_user, system_admin_headers):
    payload = {
        "policies": [
            {
                "role": "editor",
                "permissions": ["view_public_docs"],
            }
        ],
        "confirm_password": "sysadmin123",
    }
    response = client.put("/api/v1/rbac/policies", headers=system_admin_headers, json=payload)

    assert response.status_code == 200
    assert response.json()["policies"][0]["role"] == "editor"

    assert has_permission(test_user, Permission.VIEW_PUBLIC_DOCS)
    assert not has_permission(test_user, Permission.EDIT_DOCUMENT)


def test_auth_me_uses_effective_dynamic_permissions(
    client, test_user, auth_headers, system_admin_headers
):
    payload = {
        "policies": [
            {
                "role": "editor",
                "permissions": ["view_public_docs"],
            }
        ],
        "confirm_password": "sysadmin123",
    }
    update_response = client.put(
        "/api/v1/rbac/policies", headers=system_admin_headers, json=payload
    )
    assert update_response.status_code == 200

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    permissions = me_response.json()["permissions"]

    assert permissions == ["view_public_docs"]
    assert "edit_document" not in permissions


def test_rbac_policy_update_rejects_removing_required_role_permissions(
    client, test_user, auth_headers, system_admin_headers
):
    payload = {
        "policies": [
            {
                "role": "editor",
                "permissions": [],
            }
        ],
        "confirm_password": "sysadmin123",
    }

    update_response = client.put(
        "/api/v1/rbac/policies", headers=system_admin_headers, json=payload
    )
    assert update_response.status_code == 422
    detail = update_response.json()["detail"]
    assert detail["message"] == "RBAC policy invariant violation"
    assert any(
        "editor: cannot remove required [view_public_docs]" in item for item in detail["violations"]
    )

    assert get_user_permissions(test_user) != set()
    assert has_permission(test_user, Permission.VIEW_PUBLIC_DOCS)
    assert has_permission(test_user, Permission.EDIT_DOCUMENT)

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert "view_public_docs" in me_response.json()["permissions"]
