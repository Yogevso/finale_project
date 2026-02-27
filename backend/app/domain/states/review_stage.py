"""Review workflow stage objects."""

from __future__ import annotations

from typing import Protocol

from app.errors import ConflictError
from app.models import ReviewStatus


class VersionReviewStage(Protocol):
    """Behavior needed by version publish/update guards."""

    def ensure_publishable_for_version(self) -> None: ...

    def ensure_version_mutable(self) -> None: ...


class ReviewStage:
    """Behavior for a concrete review lifecycle stage."""

    status: ReviewStatus
    allowed_targets: frozenset[ReviewStatus] = frozenset()

    def can_transition_to(self, target: ReviewStatus) -> bool:
        if target == self.status:
            return True
        return target in self.allowed_targets

    def transition_to(self, target: ReviewStatus) -> ReviewStatus:
        if self.can_transition_to(target):
            return target
        raise ConflictError(
            "Invalid review status transition: "
            f"{self.status.value} -> {target.value}"
        )

    def ensure_publishable_for_version(self) -> None:
        raise ConflictError(
            "Cannot publish version that is not approved. Submit and approve review first."
        )

    def ensure_version_mutable(self) -> None:
        return None


class PendingReviewStage(ReviewStage):
    status = ReviewStatus.PENDING
    allowed_targets = frozenset(
        {
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.CANCELLED,
        }
    )

    def ensure_publishable_for_version(self) -> None:
        raise ConflictError("Cannot publish version while review is pending")

    def ensure_version_mutable(self) -> None:
        raise ConflictError("Cannot modify version while it has a pending review")


class ApprovedReviewStage(ReviewStage):
    status = ReviewStatus.APPROVED

    def ensure_publishable_for_version(self) -> None:
        return None

    def ensure_version_mutable(self) -> None:
        raise ConflictError("Cannot modify an approved version. Create a new version instead.")


class RejectedReviewStage(ReviewStage):
    status = ReviewStatus.REJECTED


class CancelledReviewStage(ReviewStage):
    status = ReviewStatus.CANCELLED


class NoReviewStage:
    """Represents a version that has no review submitted yet."""

    def ensure_publishable_for_version(self) -> None:
        raise ConflictError("Cannot publish without an approved review for this version")

    def ensure_version_mutable(self) -> None:
        return None


_REVIEW_STAGES_BY_STATUS: dict[ReviewStatus, ReviewStage] = {
    ReviewStatus.PENDING: PendingReviewStage(),
    ReviewStatus.APPROVED: ApprovedReviewStage(),
    ReviewStatus.REJECTED: RejectedReviewStage(),
    ReviewStatus.CANCELLED: CancelledReviewStage(),
}
_NO_REVIEW_STAGE = NoReviewStage()


def review_stage_for(status: ReviewStatus) -> ReviewStage:
    return _REVIEW_STAGES_BY_STATUS[status]


def version_review_stage_for(status: ReviewStatus | None) -> VersionReviewStage:
    if status is None:
        return _NO_REVIEW_STAGE
    return review_stage_for(status)
