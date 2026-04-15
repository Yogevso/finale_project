"""Chat API regressions."""

from app.models import Chat, UserRole
from tests.factories import create_user


def test_direct_chat_api_hides_cross_tenant_system_admin_target(
    client,
    db,
    auth_headers,
    test_tenant_2,
):
    foreign_system_admin = create_user(
        db,
        email="foreign-chat-admin@example.com",
        username="foreign_chat_admin",
        full_name="Foreign Chat Admin",
        plain_password="foreignpass123",
        role=UserRole.SYSTEM_ADMIN,
        tenant_id=test_tenant_2.id,
        is_active=True,
    )

    response = client.post(
        "/api/v1/chats/direct",
        headers=auth_headers,
        json={"user_id": foreign_system_admin.id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    assert db.query(Chat).count() == 0


def test_direct_chat_api_masks_cross_tenant_user_enumeration_like_missing_user(
    client,
    db,
    auth_headers,
    test_tenant_2,
):
    foreign_user = create_user(
        db,
        email="foreign-chat-user@example.com",
        username="foreign_chat_user",
        full_name="Foreign Chat User",
        plain_password="foreignpass123",
        role=UserRole.EDITOR,
        tenant_id=test_tenant_2.id,
        is_active=True,
    )

    cross_tenant_response = client.post(
        "/api/v1/chats/direct",
        headers=auth_headers,
        json={"user_id": foreign_user.id},
    )
    missing_user_response = client.post(
        "/api/v1/chats/direct",
        headers=auth_headers,
        json={"user_id": foreign_user.id + 999999},
    )

    assert cross_tenant_response.status_code == 404
    assert missing_user_response.status_code == 404
    assert (
        cross_tenant_response.json()
        == missing_user_response.json()
        == {
            "detail": "User not found",
            "error_code": "not_found",
        }
    )
    assert db.query(Chat).count() == 0


def test_editor_can_list_same_tenant_chat_targets_including_customers(
    client,
    db,
    auth_headers,
    test_user,
):
    create_user(
        db,
        email="customer-chat-target@example.com",
        username="customer_chat_target",
        full_name="Customer Chat Target",
        plain_password="customerpass123",
        role=UserRole.CUSTOMER,
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    create_user(
        db,
        email="inactive-chat-target@example.com",
        username="inactive_chat_target",
        full_name="Inactive Chat Target",
        plain_password="inactivepass123",
        role=UserRole.CUSTOMER,
        tenant_id=test_user.tenant_id,
        is_active=False,
    )

    response = client.get("/api/v1/chats/eligible-users?search=chat", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert [item["full_name"] for item in payload] == ["Customer Chat Target"]
    assert payload[0]["role"] == "customer"
    assert all(item["id"] != test_user.id for item in payload)


def test_viewer_can_list_chat_targets_but_customer_cannot(
    client,
    db,
    viewer_auth_headers,
    customer_headers,
    test_viewer,
):
    customer = create_user(
        db,
        email="chat-target-viewer@example.com",
        username="chat_target_viewer",
        full_name="Chat Target Viewer",
        plain_password="customerpass123",
        role=UserRole.CUSTOMER,
        tenant_id=test_viewer.tenant_id,
        is_active=True,
    )

    viewer_response = client.get(
        "/api/v1/chats/eligible-users?search=viewer", headers=viewer_auth_headers
    )
    customer_response = client.get("/api/v1/chats/eligible-users", headers=customer_headers)

    assert viewer_response.status_code == 200
    assert [item["id"] for item in viewer_response.json()] == [customer.id]
    assert customer_response.status_code == 403
