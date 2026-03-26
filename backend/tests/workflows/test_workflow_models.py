"""Model-based tests for document/review workflow transition graphs."""

from __future__ import annotations

import pytest

from app.domain.workflows import DocumentWorkflow, ReviewWorkflow
from app.errors import ConflictError, InvalidStateError
from app.models import DocumentStatus, ReviewStatus


def test_document_workflow_model_shape_and_terminals():
    model = DocumentWorkflow.model()

    assert model.name == "document_lifecycle"
    assert model.initial_states == (DocumentStatus.DRAFT,)
    assert model.allowed_targets(DocumentStatus.DRAFT) == (
        DocumentStatus.PENDING_REVIEW,
        DocumentStatus.ARCHIVED,
    )
    assert model.allowed_targets(DocumentStatus.PENDING_REVIEW) == (
        DocumentStatus.DRAFT,
        DocumentStatus.APPROVED,
        DocumentStatus.ARCHIVED,
    )
    assert model.allowed_targets(DocumentStatus.APPROVED) == (
        DocumentStatus.ACTIVE,
        DocumentStatus.ARCHIVED,
    )
    assert model.allowed_targets(DocumentStatus.ACTIVE) == (
        DocumentStatus.DRAFT,
        DocumentStatus.ARCHIVED,
    )
    assert model.allowed_targets(DocumentStatus.ARCHIVED) == (
        DocumentStatus.DRAFT,
        DocumentStatus.ACTIVE,
    )
    assert model.terminal_states() == ()


def test_document_workflow_model_based_transition_matrix():
    workflow = DocumentWorkflow()
    model = workflow.model()

    for source in model.states:
        for target in model.states:
            expected = model.can_transition(source, target)
            assert workflow.can_transition(source, target) is expected
            if expected:
                assert workflow.transition(source, target) == target
            else:
                with pytest.raises(InvalidStateError, match="Invalid document status transition"):
                    workflow.transition(source, target)


def test_document_workflow_model_reachability_and_paths():
    model = DocumentWorkflow.model()

    assert model.reachable_states() == frozenset(
        {
            DocumentStatus.DRAFT,
            DocumentStatus.PENDING_REVIEW,
            DocumentStatus.APPROVED,
            DocumentStatus.ACTIVE,
            DocumentStatus.ARCHIVED,
        }
    )
    assert (DocumentStatus.DRAFT, DocumentStatus.ARCHIVED) in model.enumerate_paths(max_steps=1)
    assert (DocumentStatus.DRAFT, DocumentStatus.PENDING_REVIEW) in model.enumerate_paths(
        max_steps=1
    )


def test_review_workflow_model_shape_and_terminals():
    model = ReviewWorkflow.model()

    assert model.name == "review_lifecycle"
    assert model.initial_states == (ReviewStatus.PENDING,)
    assert model.allowed_targets(ReviewStatus.PENDING) == (
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        ReviewStatus.CANCELLED,
    )
    assert model.terminal_states() == (
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        ReviewStatus.CANCELLED,
    )


def test_review_workflow_model_based_transition_matrix():
    workflow = ReviewWorkflow()
    model = workflow.model()

    for source in model.states:
        for target in model.states:
            expected = model.can_transition(source, target)
            assert workflow.can_transition(source, target) is expected
            if expected:
                assert workflow.transition(source, target) == target
            else:
                with pytest.raises(ConflictError, match="Invalid review status transition"):
                    workflow.transition(source, target)


def test_review_workflow_paths_cover_all_pending_outcomes():
    model = ReviewWorkflow.model()

    paths = model.enumerate_paths(max_steps=1)
    assert paths == (
        (ReviewStatus.PENDING, ReviewStatus.APPROVED),
        (ReviewStatus.PENDING, ReviewStatus.REJECTED),
        (ReviewStatus.PENDING, ReviewStatus.CANCELLED),
    )
    assert model.reachable_states() == frozenset(
        {
            ReviewStatus.PENDING,
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.CANCELLED,
        }
    )


def test_workflow_model_rejects_negative_max_steps():
    model = DocumentWorkflow.model()

    with pytest.raises(ValueError, match="max_steps must be >= 0"):
        model.enumerate_paths(max_steps=-1)
