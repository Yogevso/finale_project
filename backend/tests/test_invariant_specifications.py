"""Tests for reusable domain invariant specifications."""

from datetime import datetime

import pytest

from app.domain.specifications import (
    CustomerInvitationTenantSpec,
    DocumentDraftOrActiveSpec,
    DocumentDraftStatusSpec,
    InvitationPendingStatusSpec,
    InvitationResendableSpec,
    ManagerVisibilityRoleSpec,
    ReviewApprovableVersionSpec,
    ReviewPendingStatusSpec,
    ReviewSubmitterMatchesSpec,
)
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


def test_document_draft_status_spec_requires_draft():
    spec = DocumentDraftStatusSpec()
    document = Document(
        title="Spec status doc",
        document_number="DOC-SPEC-0001",
        status=DocumentStatus.ACTIVE,
    )

    assert not spec.is_satisfied_by(document)
    with pytest.raises(InvalidStateError, match="draft status"):
        spec.assert_satisfied(document)


def test_document_draft_or_active_spec_allows_expected_statuses():
    spec = DocumentDraftOrActiveSpec()
    draft_doc = Document(
        title="Draft doc",
        document_number="DOC-SPEC-0002",
        status=DocumentStatus.DRAFT,
    )
    active_doc = Document(
        title="Active doc",
        document_number="DOC-SPEC-0003",
        status=DocumentStatus.ACTIVE,
    )
    approved_doc = Document(
        title="Approved doc",
        document_number="DOC-SPEC-0004",
        status=DocumentStatus.APPROVED,
    )

    assert spec.is_satisfied_by(draft_doc)
    assert spec.is_satisfied_by(active_doc)
    assert not spec.is_satisfied_by(approved_doc)


def test_manager_visibility_role_spec_requires_manager_or_above():
    spec = ManagerVisibilityRoleSpec()

    assert spec.is_satisfied_by(UserRole.MANAGER)
    assert spec.is_satisfied_by(UserRole.ADMIN)
    assert spec.is_satisfied_by(UserRole.SYSTEM_ADMIN)
    assert not spec.is_satisfied_by(UserRole.EDITOR)

    with pytest.raises(PermissionDeniedError, match="Only managers"):
        spec.assert_satisfied(UserRole.EDITOR)


def test_review_pending_status_spec_requires_pending():
    spec = ReviewPendingStatusSpec()
    review = ReviewRequest(document_id=1, submitted_by=10, status=ReviewStatus.APPROVED)

    assert not spec.is_satisfied_by(review)
    with pytest.raises(ConflictError, match="not pending"):
        spec.assert_satisfied(review)


def test_review_submitter_matches_spec_requires_same_submitter():
    review = ReviewRequest(document_id=1, submitted_by=10, status=ReviewStatus.PENDING)
    matching_spec = ReviewSubmitterMatchesSpec(expected_user_id=10)
    non_matching_spec = ReviewSubmitterMatchesSpec(expected_user_id=22)

    assert matching_spec.is_satisfied_by(review)
    assert not non_matching_spec.is_satisfied_by(review)

    with pytest.raises(PermissionDeniedError, match="cancel your own"):
        non_matching_spec.assert_satisfied(review)


def test_review_approvable_version_spec_handles_version_invariants():
    spec = ReviewApprovableVersionSpec()
    review = ReviewRequest(
        document_id=1, version_id=4, submitted_by=10, status=ReviewStatus.PENDING
    )
    review_version = Version(
        id=4, document_id=1, version_number=4, created_by=10, is_published=False
    )
    latest_version = Version(
        id=5, document_id=1, version_number=5, created_by=10, is_published=False
    )
    published_review_version = Version(
        id=4,
        document_id=1,
        version_number=4,
        created_by=10,
        is_published=True,
    )

    assert not spec.is_satisfied_by(
        review=review,
        review_version=None,
        latest_version=latest_version,
    )
    with pytest.raises(ConflictError, match="no longer exists"):
        spec.assert_satisfied(
            review=review,
            review_version=None,
            latest_version=latest_version,
        )

    assert not spec.is_satisfied_by(
        review=review,
        review_version=review_version,
        latest_version=latest_version,
    )
    with pytest.raises(ConflictError, match="outdated review"):
        spec.assert_satisfied(
            review=review,
            review_version=review_version,
            latest_version=latest_version,
        )

    same_latest_version = Version(
        id=4,
        document_id=1,
        version_number=4,
        created_by=10,
        is_published=False,
    )
    assert not spec.is_satisfied_by(
        review=review,
        review_version=published_review_version,
        latest_version=same_latest_version,
    )
    with pytest.raises(ConflictError, match="already published"):
        spec.assert_satisfied(
            review=review,
            review_version=published_review_version,
            latest_version=same_latest_version,
        )


def test_customer_invitation_tenant_spec_requires_customer_tenant():
    spec = CustomerInvitationTenantSpec()

    assert spec.is_satisfied_by(UserRole.ADMIN, None)
    assert spec.is_satisfied_by(UserRole.CUSTOMER, 17)
    assert not spec.is_satisfied_by(UserRole.CUSTOMER, None)

    with pytest.raises(ValidationError, match="assigned to a company"):
        spec.assert_satisfied(UserRole.CUSTOMER, None)


def test_invitation_pending_status_spec_requires_pending():
    spec = InvitationPendingStatusSpec()
    invitation = Invitation(
        email="accepted@example.com",
        token="token",
        role=UserRole.CUSTOMER,
        invited_by=1,
        status=InvitationStatus.ACCEPTED,
        expires_at=datetime.utcnow(),
    )

    assert not spec.is_satisfied_by(invitation)
    with pytest.raises(ValidationError, match="pending invitations"):
        spec.assert_satisfied(invitation)


def test_invitation_resendable_spec_blocks_accepted_invitations():
    spec = InvitationResendableSpec()
    invitation = Invitation(
        email="accepted@example.com",
        token="token",
        role=UserRole.CUSTOMER,
        invited_by=1,
        status=InvitationStatus.ACCEPTED,
        expires_at=datetime.utcnow(),
    )

    assert not spec.is_satisfied_by(invitation)
    with pytest.raises(ValidationError, match="accepted invitation"):
        spec.assert_satisfied(invitation)
