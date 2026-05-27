"""Regression coverage for review notification recipient rules."""

from app.models import Notification, NotificationType, UserRole
from tests.factories import create_tenant, create_user


def test_submit_for_review_notifies_same_tenant_reviewers_only(
    client,
    db,
    auth_headers,
    test_document,
    test_user,
    default_tenant,
):
    peer_editor = create_user(
        db,
        email="review-peer-editor@example.com",
        username="review_peer_editor",
        full_name="Review Peer Editor",
        plain_password="ReviewPeer1!",
        role=UserRole.EDITOR,
        tenant_id=default_tenant.id,
    )
    peer_manager = create_user(
        db,
        email="review-peer-manager@example.com",
        username="review_peer_manager",
        full_name="Review Peer Manager",
        plain_password="ReviewPeer2!",
        role=UserRole.MANAGER,
        tenant_id=default_tenant.id,
    )
    foreign_tenant = create_tenant(
        db,
        name="Foreign Review Tenant",
        slug="foreign-review-tenant",
    )
    foreign_editor = create_user(
        db,
        email="review-foreign-editor@example.com",
        username="review_foreign_editor",
        full_name="Review Foreign Editor",
        plain_password="ReviewPeer3!",
        role=UserRole.EDITOR,
        tenant_id=foreign_tenant.id,
    )

    response = client.post(
        f"/api/v1/reviews/documents/{test_document.id}/submit",
        headers=auth_headers,
        json={"message": "Please review this draft."},
    )

    assert response.status_code in [200, 201]
    notifications = (
        db.query(Notification).filter(Notification.type == NotificationType.REVIEW_SUBMITTED).all()
    )
    notified_ids = {notification.user_id for notification in notifications}
    assert notified_ids == {peer_editor.id, peer_manager.id}
    assert test_user.id not in notified_ids
    assert foreign_editor.id not in notified_ids


def test_review_approval_notifies_submitter(
    client,
    db,
    auth_headers,
    manager_headers,
    test_document,
    test_user,
):
    submit_response = client.post(
        f"/api/v1/reviews/documents/{test_document.id}/submit",
        headers=auth_headers,
        json={"message": "Ready for approval."},
    )
    assert submit_response.status_code in [200, 201]
    review_id = submit_response.json()["id"]

    approve_response = client.post(
        f"/api/v1/reviews/{review_id}/approve",
        headers=manager_headers,
        json={"comments": "Looks good."},
    )

    assert approve_response.status_code == 200
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.REVIEW_APPROVED,
        )
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.title == "Document approved"
    assert notification.link == f"/documents/{test_document.id}"


def test_review_rejection_notifies_submitter(
    client,
    db,
    auth_headers,
    manager_headers,
    test_document,
    test_user,
):
    submit_response = client.post(
        f"/api/v1/reviews/documents/{test_document.id}/submit",
        headers=auth_headers,
        json={"message": "Needs another pass."},
    )
    assert submit_response.status_code in [200, 201]
    review_id = submit_response.json()["id"]

    reject_response = client.post(
        f"/api/v1/reviews/{review_id}/reject",
        headers=manager_headers,
        json={"comments": "Please fix the release notes."},
    )

    assert reject_response.status_code == 200
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.REVIEW_REJECTED,
        )
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.title == "Sent back for changes"
    assert notification.link == f"/documents/{test_document.id}"
