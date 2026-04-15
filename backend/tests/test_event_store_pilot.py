"""Tests for selective event-sourcing review workflow pilot."""

import pytest

from app.event_store import InMemoryEventStore, OptimisticConcurrencyError
from app.event_store.review_workflow_pilot import ReviewWorkflowEventSourcingPilot


def test_in_memory_event_store_enforces_expected_version():
    store = InMemoryEventStore()
    store.append(
        stream_id="review_workflow:1",
        event_type="review_submitted",
        payload={"document_id": 3},
        expected_version=0,
    )

    with pytest.raises(OptimisticConcurrencyError):
        store.append(
            stream_id="review_workflow:1",
            event_type="review_approved",
            payload={"reviewer_id": 2},
            expected_version=0,
        )


def test_review_workflow_pilot_replays_terminal_state():
    pilot = ReviewWorkflowEventSourcingPilot(enabled=True)

    first_event = pilot.append_submission(
        review_id=55,
        document_id=120,
        version_id=7,
        submitted_by=3,
        comments="ready for review",
    )
    second_event = pilot.append_decision(
        review_id=55,
        outcome="approved",
        reviewer_id=8,
        comments="looks good",
    )

    assert first_event is not None
    assert second_event is not None

    projection = pilot.replay(55)
    assert projection.status == "approved"
    assert projection.document_id == 120
    assert projection.version_id == 7
    assert projection.submitted_by == 3
    assert projection.reviewer_id == 8
    assert projection.event_version == 2


def test_review_workflow_pilot_blocks_invalid_transition_before_submission():
    pilot = ReviewWorkflowEventSourcingPilot(enabled=True)

    with pytest.raises(ValueError, match="pending"):
        pilot.append_decision(
            review_id=88,
            outcome="rejected",
            reviewer_id=9,
            comments="missing evidence",
        )


def test_review_workflow_pilot_respects_disable_flag_shadow_mode():
    pilot = ReviewWorkflowEventSourcingPilot(enabled=False)

    assert (
        pilot.append_submission(
            review_id=101,
            document_id=9,
            version_id=4,
            submitted_by=1,
        )
        is None
    )
    projection = pilot.replay(101)
    assert projection.status == "not_started"
    assert projection.event_version == 0


def test_review_workflow_pilot_exposes_optimistic_concurrency_for_stale_writes():
    pilot = ReviewWorkflowEventSourcingPilot(enabled=True)
    pilot.append_submission(
        review_id=66,
        document_id=5,
        version_id=2,
        submitted_by=4,
    )

    with pytest.raises(OptimisticConcurrencyError):
        pilot.append_decision(
            review_id=66,
            outcome="cancelled",
            reviewer_id=4,
            expected_version=0,
        )
