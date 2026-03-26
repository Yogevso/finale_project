"""Tests for workflow-stage state objects."""

import pytest

from app.domain.states import document_stage_for, review_stage_for, version_review_stage_for
from app.errors import ConflictError, InvalidStateError
from app.models import DocumentStatus, ReviewStatus


def test_document_stage_supports_configured_transitions():
    pending_stage = document_stage_for(DocumentStatus.PENDING_REVIEW)

    assert pending_stage.can_transition_to(DocumentStatus.APPROVED)
    assert pending_stage.can_transition_to(DocumentStatus.DRAFT)
    assert pending_stage.transition_to(DocumentStatus.APPROVED) == DocumentStatus.APPROVED


def test_document_stage_supports_archive_and_restore_transitions():
    assert document_stage_for(DocumentStatus.DRAFT).can_transition_to(DocumentStatus.ARCHIVED)
    assert document_stage_for(DocumentStatus.ACTIVE).can_transition_to(DocumentStatus.ARCHIVED)
    assert document_stage_for(DocumentStatus.ARCHIVED).can_transition_to(DocumentStatus.DRAFT)
    assert document_stage_for(DocumentStatus.ARCHIVED).can_transition_to(DocumentStatus.ACTIVE)


def test_document_stage_blocks_invalid_transition():
    active_stage = document_stage_for(DocumentStatus.ACTIVE)

    assert not active_stage.can_transition_to(DocumentStatus.PENDING_REVIEW)
    with pytest.raises(InvalidStateError, match="Invalid document status transition"):
        active_stage.transition_to(DocumentStatus.PENDING_REVIEW)


def test_document_stage_normalizes_new_version_candidate_status():
    assert (
        document_stage_for(DocumentStatus.ACTIVE).normalize_for_new_version_candidate()
        == DocumentStatus.ACTIVE
    )
    assert (
        document_stage_for(DocumentStatus.APPROVED).normalize_for_new_version_candidate()
        == DocumentStatus.DRAFT
    )


def test_review_stage_supports_pending_transitions():
    pending_stage = review_stage_for(ReviewStatus.PENDING)

    assert pending_stage.can_transition_to(ReviewStatus.APPROVED)
    assert pending_stage.can_transition_to(ReviewStatus.REJECTED)
    assert pending_stage.can_transition_to(ReviewStatus.CANCELLED)
    assert pending_stage.transition_to(ReviewStatus.REJECTED) == ReviewStatus.REJECTED


def test_review_stage_blocks_invalid_transition():
    approved_stage = review_stage_for(ReviewStatus.APPROVED)

    assert not approved_stage.can_transition_to(ReviewStatus.REJECTED)
    with pytest.raises(ConflictError, match="Invalid review status transition"):
        approved_stage.transition_to(ReviewStatus.REJECTED)


def test_version_review_stage_without_review_blocks_publish():
    no_review_stage = version_review_stage_for(None)

    with pytest.raises(
        ConflictError,
        match="Cannot publish without an approved review for this version",
    ):
        no_review_stage.ensure_publishable_for_version()

    no_review_stage.ensure_version_mutable()


def test_version_review_stage_pending_blocks_publish_and_modify():
    pending_stage = version_review_stage_for(ReviewStatus.PENDING)

    with pytest.raises(ConflictError, match="Cannot publish version while review is pending"):
        pending_stage.ensure_publishable_for_version()
    with pytest.raises(
        ConflictError,
        match="Cannot modify version while it has a pending review",
    ):
        pending_stage.ensure_version_mutable()


def test_version_review_stage_approved_allows_publish_but_blocks_modify():
    approved_stage = version_review_stage_for(ReviewStatus.APPROVED)

    approved_stage.ensure_publishable_for_version()
    with pytest.raises(
        ConflictError,
        match="Cannot modify an approved version. Create a new version instead.",
    ):
        approved_stage.ensure_version_mutable()


@pytest.mark.parametrize("status", [ReviewStatus.REJECTED, ReviewStatus.CANCELLED])
def test_version_review_stage_non_approved_blocks_publish(status):
    non_approved_stage = version_review_stage_for(status)

    with pytest.raises(
        ConflictError,
        match="Cannot publish version that is not approved. Submit and approve review first.",
    ):
        non_approved_stage.ensure_publishable_for_version()

    non_approved_stage.ensure_version_mutable()
