"""Tests for domain aggregate roots and invariants."""

from datetime import datetime

import pytest

from app.domain.aggregates import DocumentAggregate, InvitationAggregate, ReviewAggregate
from app.errors import ConflictError, InvalidStateError, PermissionDeniedError, ValidationError
from app.models import (
    Document,
    DocumentStatus,
    Invitation,
    InvitationStatus,
    ReviewRequest,
    ReviewStatus,
    UserRole,
    Version,
)


def test_document_aggregate_requires_draft_for_review_submission(db, test_user):
    document = Document(
        title="Review status doc",
        document_number="DOC-AGG-0001",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=test_user.tenant_id,
    )

    aggregate = DocumentAggregate(document)
    with pytest.raises(InvalidStateError, match="draft status"):
        aggregate.ensure_submittable_for_review()


def test_document_aggregate_visibility_change_requires_manager_or_above():
    document = Document(
        title="Visibility doc",
        document_number="DOC-AGG-0002",
        status=DocumentStatus.DRAFT,
    )

    aggregate = DocumentAggregate(document)
    with pytest.raises(PermissionDeniedError, match="Only managers"):
        aggregate.ensure_visibility_change_allowed(UserRole.EDITOR)


def test_document_aggregate_keeps_published_documents_active_during_review_flows():
    document = Document(
        title="Published lifecycle doc",
        document_number="DOC-AGG-0003",
        status=DocumentStatus.APPROVED,
        created_by=1,
        tenant_id=1,
    )
    document.versions = [
        Version(
            id=10,
            document_id=1,
            version_number=1,
            created_by=1,
            is_published=True,
        ),
        Version(
            id=11,
            document_id=1,
            version_number=2,
            created_by=1,
            is_published=False,
        ),
    ]

    aggregate = DocumentAggregate(document)
    aggregate.finalize_review_approval()
    assert document.status == DocumentStatus.ACTIVE

    document.status = DocumentStatus.DRAFT
    aggregate.revert_review_submission()
    assert document.status == DocumentStatus.ACTIVE

    document.status = DocumentStatus.APPROVED
    aggregate.prepare_for_new_version_candidate()
    assert document.status == DocumentStatus.ACTIVE


def test_review_aggregate_approve_updates_state():
    review = ReviewRequest(document_id=1, submitted_by=2, status=ReviewStatus.PENDING)

    aggregate = ReviewAggregate(review)
    now = datetime.utcnow()
    aggregate.approve(reviewer_id=5, comments="looks good", reviewed_at=now)

    assert review.status == ReviewStatus.APPROVED
    assert review.reviewed_by == 5
    assert review.review_comments == "looks good"
    assert review.reviewed_at == now


def test_review_aggregate_blocks_outdated_version_approval():
    review = ReviewRequest(document_id=1, version_id=4, submitted_by=2, status=ReviewStatus.PENDING)
    aggregate = ReviewAggregate(review)
    review_version = Version(id=4, document_id=1, version_number=4, created_by=2, is_published=False)
    latest_version = Version(id=5, document_id=1, version_number=5, created_by=2, is_published=False)

    with pytest.raises(ConflictError, match="outdated review"):
        aggregate.ensure_approvable_version(
            review_version=review_version,
            latest_version=latest_version,
        )


def test_invitation_aggregate_requires_tenant_for_customer():
    with pytest.raises(ValidationError, match="assigned to a company"):
        InvitationAggregate.ensure_customer_has_tenant(UserRole.CUSTOMER, None)


def test_invitation_aggregate_cancel_requires_pending_status():
    invitation = Invitation(
        email="accepted@example.com",
        token="token",
        role=UserRole.CUSTOMER,
        invited_by=1,
        status=InvitationStatus.ACCEPTED,
        expires_at=datetime.utcnow(),
    )
    aggregate = InvitationAggregate(invitation)

    with pytest.raises(ValidationError, match="pending invitations"):
        aggregate.cancel()
