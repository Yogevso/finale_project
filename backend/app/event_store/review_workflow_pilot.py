"""Selective event-sourcing pilot for review workflow transitions.

The pilot intentionally runs as a shadow path with a feature flag gate so the
existing relational write path remains source-of-truth and rollback is a config
change.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal

from app.event_store.store import EventEnvelope, InMemoryEventStore
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled

ReviewWorkflowStatus = Literal["not_started", "pending", "approved", "rejected", "cancelled"]
ReviewOutcome = Literal["approved", "rejected", "cancelled"]

REVIEW_EVENT_SUBMITTED = "review_submitted"
REVIEW_EVENT_APPROVED = "review_approved"
REVIEW_EVENT_REJECTED = "review_rejected"
REVIEW_EVENT_CANCELLED = "review_cancelled"

_REVIEW_STREAM_PREFIX = "review_workflow"


@dataclass(frozen=True, slots=True)
class ReviewWorkflowProjection:
    """Replay projection representing pilot review workflow state."""

    review_id: int
    status: ReviewWorkflowStatus = "not_started"
    document_id: int | None = None
    version_id: int | None = None
    submitted_by: int | None = None
    reviewer_id: int | None = None
    submitted_at: str | None = None
    reviewed_at: str | None = None
    comments: str | None = None
    event_version: int = 0


def build_review_stream_id(review_id: int) -> str:
    """Return canonical stream identifier for one review workflow."""
    return f"{_REVIEW_STREAM_PREFIX}:{int(review_id)}"


def replay_review_workflow_stream(
    *,
    review_id: int,
    events: list[EventEnvelope],
) -> ReviewWorkflowProjection:
    """Rebuild workflow projection from an ordered list of events."""

    state = ReviewWorkflowProjection(review_id=int(review_id))
    stream_id = build_review_stream_id(review_id)
    for event in sorted(events, key=lambda item: item.stream_version):
        if event.stream_id != stream_id:
            raise ValueError(f"Unexpected stream id {event.stream_id}; expected {stream_id}")
        state = _apply_review_workflow_event(state=state, event=event)
    return state


def _apply_review_workflow_event(
    *,
    state: ReviewWorkflowProjection,
    event: EventEnvelope,
) -> ReviewWorkflowProjection:
    event_type = event.event_type
    payload = event.payload

    if event_type == REVIEW_EVENT_SUBMITTED:
        if state.status != "not_started":
            raise ValueError("Review submission event is only valid for not_started state")
        return replace(
            state,
            status="pending",
            document_id=int(payload["document_id"]),
            version_id=int(payload["version_id"])
            if payload.get("version_id") is not None
            else None,
            submitted_by=int(payload["submitted_by"]),
            submitted_at=str(payload.get("submitted_at") or event.occurred_at),
            comments=str(payload["comments"]) if payload.get("comments") is not None else None,
            event_version=event.stream_version,
        )

    if event_type in {REVIEW_EVENT_APPROVED, REVIEW_EVENT_REJECTED, REVIEW_EVENT_CANCELLED}:
        if state.status != "pending":
            raise ValueError("Review decision event is only valid when review is pending")
        next_status: ReviewWorkflowStatus
        if event_type == REVIEW_EVENT_APPROVED:
            next_status = "approved"
        elif event_type == REVIEW_EVENT_REJECTED:
            next_status = "rejected"
        else:
            next_status = "cancelled"

        return replace(
            state,
            status=next_status,
            reviewer_id=int(payload["reviewer_id"]),
            reviewed_at=str(payload.get("reviewed_at") or event.occurred_at),
            comments=str(payload["comments"])
            if payload.get("comments") is not None
            else state.comments,
            event_version=event.stream_version,
        )

    raise ValueError(f"Unsupported review workflow event type: {event_type}")


class ReviewWorkflowEventSourcingPilot:
    """Feature-flagged shadow event-sourcing pilot for review transitions."""

    def __init__(
        self,
        *,
        event_store: InMemoryEventStore | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._event_store = event_store or InMemoryEventStore()
        if enabled is None:
            enabled = is_backend_feature_enabled(BackendFeatureFlag.EVENT_SOURCING_REVIEW_PILOT)
        self._enabled = bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def events(self, review_id: int) -> list[EventEnvelope]:
        return self._event_store.read_stream(build_review_stream_id(review_id))

    def replay(self, review_id: int) -> ReviewWorkflowProjection:
        return replay_review_workflow_stream(review_id=review_id, events=self.events(review_id))

    def append_submission(
        self,
        *,
        review_id: int,
        document_id: int,
        version_id: int | None,
        submitted_by: int,
        comments: str | None = None,
        submitted_at: str | None = None,
        expected_version: int | None = None,
    ) -> EventEnvelope | None:
        if not self.enabled:
            return None

        current = self.replay(review_id)
        if current.status != "not_started":
            raise ValueError("Review workflow stream already started")

        return self._event_store.append(
            stream_id=build_review_stream_id(review_id),
            event_type=REVIEW_EVENT_SUBMITTED,
            payload={
                "document_id": int(document_id),
                "version_id": int(version_id) if version_id is not None else None,
                "submitted_by": int(submitted_by),
                "submitted_at": submitted_at or _utc_iso_now(),
                "comments": comments,
            },
            expected_version=current.event_version
            if expected_version is None
            else int(expected_version),
        )

    def append_decision(
        self,
        *,
        review_id: int,
        outcome: ReviewOutcome,
        reviewer_id: int,
        comments: str | None = None,
        reviewed_at: str | None = None,
        expected_version: int | None = None,
    ) -> EventEnvelope | None:
        if not self.enabled:
            return None

        current = self.replay(review_id)
        if current.status != "pending":
            raise ValueError("Review workflow decision requires pending state")

        event_type = {
            "approved": REVIEW_EVENT_APPROVED,
            "rejected": REVIEW_EVENT_REJECTED,
            "cancelled": REVIEW_EVENT_CANCELLED,
        }[outcome]

        return self._event_store.append(
            stream_id=build_review_stream_id(review_id),
            event_type=event_type,
            payload={
                "reviewer_id": int(reviewer_id),
                "reviewed_at": reviewed_at or _utc_iso_now(),
                "comments": comments,
            },
            expected_version=current.event_version
            if expected_version is None
            else int(expected_version),
        )


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
