"""Review aggregate root with workflow invariants."""

from __future__ import annotations

from datetime import datetime

from app.domain.specifications import (
    ReviewApprovableVersionSpec,
    ReviewPendingStatusSpec,
    ReviewSubmitterMatchesSpec,
)
from app.domain.workflows import ReviewWorkflow
from app.models import ReviewRequest, ReviewStatus, Version


class ReviewAggregate:
    """Encapsulates review-request state transitions and invariant guards."""

    _pending_spec = ReviewPendingStatusSpec()
    _approvable_version_spec = ReviewApprovableVersionSpec()
    _workflow = ReviewWorkflow()

    def __init__(self, review: ReviewRequest):
        self.review = review

    def ensure_pending(self) -> None:
        self._pending_spec.assert_satisfied(self.review)

    def ensure_submitter(self, user_id: int) -> None:
        ReviewSubmitterMatchesSpec(expected_user_id=user_id).assert_satisfied(self.review)

    def ensure_approvable_version(
        self,
        *,
        review_version: Version | None,
        latest_version: Version | None,
    ) -> None:
        self._approvable_version_spec.assert_satisfied(
            review=self.review,
            review_version=review_version,
            latest_version=latest_version,
        )

    def approve(self, *, reviewer_id: int, comments: str | None, reviewed_at: datetime) -> None:
        self.ensure_pending()
        self.review.status = self._workflow.transition(
            self.review.status,
            ReviewStatus.APPROVED,
        )
        self.review.reviewed_by = reviewer_id
        self.review.review_comments = comments
        self.review.reviewed_at = reviewed_at

    def reject(self, *, reviewer_id: int, comments: str, reviewed_at: datetime) -> None:
        self.ensure_pending()
        self.review.status = self._workflow.transition(
            self.review.status,
            ReviewStatus.REJECTED,
        )
        self.review.reviewed_by = reviewer_id
        self.review.review_comments = comments
        self.review.reviewed_at = reviewed_at

    def cancel(self, *, reviewed_at: datetime) -> None:
        self.ensure_pending()
        self.review.status = self._workflow.transition(
            self.review.status,
            ReviewStatus.CANCELLED,
        )
        self.review.reviewed_at = reviewed_at
