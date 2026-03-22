"""Regression tests for optimistic concurrency controls on mutable resources."""

from __future__ import annotations

from app.models import User, UserRole
from app.security import get_password_hash


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_document_update_requires_if_match_header(client, admin_token, sample_document):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers=headers,
        json={"title": "No precondition token"},
    )
    assert response.status_code == 428
    assert "If-Match" in response.json()["detail"]


def test_document_update_rejects_stale_if_match(client, admin_token, sample_document):
    auth_headers = {"Authorization": f"Bearer {admin_token}"}
    stale_etag = sample_document["etag"]

    first_update = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers={**auth_headers, "If-Match": stale_etag},
        json={"title": "First write"},
    )
    assert first_update.status_code == 200
    assert first_update.json()["row_version"] > sample_document["row_version"]

    second_update = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers={**auth_headers, "If-Match": stale_etag},
        json={"title": "Second write with stale etag"},
    )
    assert second_update.status_code == 409
    assert "conflict" in second_update.json()["detail"].lower()


def test_version_update_rejects_stale_if_match(client, admin_token, sample_document):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_response = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions",
        headers=headers,
        json={"content": "v2", "changes_summary": "candidate"},
    )
    assert create_response.status_code == 201
    created_version = create_response.json()
    stale_etag = created_version["etag"]

    first_update = client.patch(
        f"/api/v1/documents/{sample_document['id']}/versions/{created_version['id']}",
        headers={**headers, "If-Match": stale_etag},
        json={"content": "v2 updated"},
    )
    assert first_update.status_code == 200
    assert first_update.json()["row_version"] > created_version["row_version"]

    second_update = client.patch(
        f"/api/v1/documents/{sample_document['id']}/versions/{created_version['id']}",
        headers={**headers, "If-Match": stale_etag},
        json={"content": "v2 stale update"},
    )
    assert second_update.status_code == 409
    assert "conflict" in second_update.json()["detail"].lower()


def test_version_update_requires_if_match_header(client, admin_token, sample_document):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_response = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions",
        headers=headers,
        json={"content": "v2", "changes_summary": "candidate"},
    )
    assert create_response.status_code == 201
    version_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
        headers=headers,
        json={"content": "missing token"},
    )
    assert update_response.status_code == 428
    assert "If-Match" in update_response.json()["detail"]


def test_visibility_update_rejects_stale_if_match_between_two_admins(
    client,
    db,
    sample_document,
    default_tenant,
):
    second_admin = User(
        email="second-admin@example.com",
        username="second_admin",
        full_name="Second Admin",
        hashed_password=get_password_hash("second-admin-pass-123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_email_verified=True,
        tenant_id=default_tenant.id,
    )
    db.add(second_admin)
    db.commit()

    first_admin_headers = _login_headers(client, "admin", "admin123")
    second_admin_headers = _login_headers(client, "second_admin", "second-admin-pass-123")

    stale_etag = sample_document["etag"]
    first_update = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers={**first_admin_headers, "If-Match": stale_etag},
        json={
            "visibility": "public",
            "reason": "Promote release audience",
        },
    )
    assert first_update.status_code == 200
    assert first_update.json()["visibility"] == "public"

    second_update = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers={**second_admin_headers, "If-Match": stale_etag},
        json={
            "visibility": "internal",
            "reason": "Revert rollout after concurrent moderation decision",
        },
    )
    assert second_update.status_code == 409
    assert "write conflict" in second_update.json()["detail"].lower()
