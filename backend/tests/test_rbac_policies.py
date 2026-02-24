from app.services.permissions import Permission, clear_dynamic_role_permissions, has_permission


def test_rbac_policy_update_publishes_dynamic_permissions(client, test_user, system_admin_headers):
    clear_dynamic_role_permissions()

    payload = {
        "policies": [
            {
                "role": "editor",
                "permissions": ["view_public_docs"],
            }
        ]
    }
    response = client.put("/api/v1/rbac/policies", headers=system_admin_headers, json=payload)

    assert response.status_code == 200
    assert response.json()["policies"][0]["role"] == "editor"

    assert has_permission(test_user, Permission.VIEW_PUBLIC_DOCS)
    assert not has_permission(test_user, Permission.EDIT_DOCUMENT)


def test_auth_me_uses_effective_dynamic_permissions(
    client, test_user, auth_headers, system_admin_headers
):
    clear_dynamic_role_permissions()

    payload = {
        "policies": [
            {
                "role": "editor",
                "permissions": ["view_public_docs"],
            }
        ]
    }
    update_response = client.put("/api/v1/rbac/policies", headers=system_admin_headers, json=payload)
    assert update_response.status_code == 200

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    permissions = me_response.json()["permissions"]

    assert permissions == ["view_public_docs"]
    assert "edit_document" not in permissions
