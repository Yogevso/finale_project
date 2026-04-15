"""Tests for document/review workflow state machines."""

import pytest

from app.domain.workflows import DocumentWorkflow, ReviewWorkflow
from app.errors import ConflictError, InvalidStateError
from app.models import DocumentStatus, ReviewStatus


def test_document_workflow_can_transition_for_supported_paths():
    workflow = DocumentWorkflow()

    assert workflow.can_transition(DocumentStatus.DRAFT, DocumentStatus.PENDING_REVIEW)
    assert workflow.can_transition(DocumentStatus.DRAFT, DocumentStatus.ARCHIVED)
    assert workflow.can_transition(DocumentStatus.PENDING_REVIEW, DocumentStatus.APPROVED)
    assert workflow.can_transition(DocumentStatus.PENDING_REVIEW, DocumentStatus.DRAFT)
    assert workflow.can_transition(DocumentStatus.PENDING_REVIEW, DocumentStatus.ARCHIVED)
    assert workflow.can_transition(DocumentStatus.APPROVED, DocumentStatus.ACTIVE)
    assert workflow.can_transition(DocumentStatus.APPROVED, DocumentStatus.ARCHIVED)
    assert workflow.can_transition(DocumentStatus.ACTIVE, DocumentStatus.ARCHIVED)
    assert workflow.can_transition(DocumentStatus.ARCHIVED, DocumentStatus.DRAFT)
    assert workflow.can_transition(DocumentStatus.ARCHIVED, DocumentStatus.ACTIVE)


def test_document_workflow_blocks_invalid_transition():
    workflow = DocumentWorkflow()

    assert not workflow.can_transition(DocumentStatus.ACTIVE, DocumentStatus.PENDING_REVIEW)
    with pytest.raises(InvalidStateError, match="Invalid document status transition"):
        workflow.transition(DocumentStatus.ACTIVE, DocumentStatus.PENDING_REVIEW)


def test_document_workflow_normalizes_new_version_candidate_status():
    workflow = DocumentWorkflow()

    assert (
        workflow.normalize_for_new_version_candidate(DocumentStatus.ACTIVE) == DocumentStatus.ACTIVE
    )
    assert (
        workflow.normalize_for_new_version_candidate(DocumentStatus.DRAFT) == DocumentStatus.DRAFT
    )
    assert (
        workflow.normalize_for_new_version_candidate(DocumentStatus.APPROVED)
        == DocumentStatus.DRAFT
    )


def test_review_workflow_can_transition_from_pending():
    workflow = ReviewWorkflow()

    assert workflow.can_transition(ReviewStatus.PENDING, ReviewStatus.APPROVED)
    assert workflow.can_transition(ReviewStatus.PENDING, ReviewStatus.REJECTED)
    assert workflow.can_transition(ReviewStatus.PENDING, ReviewStatus.CANCELLED)


def test_review_workflow_blocks_invalid_transition():
    workflow = ReviewWorkflow()

    assert not workflow.can_transition(ReviewStatus.APPROVED, ReviewStatus.REJECTED)
    with pytest.raises(ConflictError, match="Invalid review status transition"):
        workflow.transition(ReviewStatus.APPROVED, ReviewStatus.REJECTED)
