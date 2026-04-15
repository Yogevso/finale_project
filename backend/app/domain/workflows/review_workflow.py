"""Review lifecycle workflow state machine."""

from __future__ import annotations

from app.domain.states import review_stage_for
from app.domain.workflows.models import WorkflowModel
from app.errors import ConflictError
from app.models import ReviewStatus


class ReviewWorkflow:
    """Centralized transition rules for review request lifecycle states."""

    @staticmethod
    def model() -> WorkflowModel[ReviewStatus]:
        statuses = tuple(ReviewStatus)
        transitions = {
            status: tuple(
                candidate
                for candidate in statuses
                if candidate in review_stage_for(status).allowed_targets
            )
            for status in statuses
        }
        return WorkflowModel(
            name="review_lifecycle",
            states=statuses,
            transitions=transitions,
            initial_states=(ReviewStatus.PENDING,),
        )

    def can_transition(self, current: ReviewStatus, target: ReviewStatus) -> bool:
        return self.model().can_transition(current, target)

    def transition(self, current: ReviewStatus, target: ReviewStatus) -> ReviewStatus:
        if self.can_transition(current, target):
            return target
        raise ConflictError(
            "Invalid review status transition: " f"{current.value} -> {target.value}"
        )
