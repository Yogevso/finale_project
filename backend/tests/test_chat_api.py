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
    assert cross_tenant_response.json() == missing_user_response.json() == {
        "detail": "User not found"
    }
    assert db.query(Chat).count() == 0
