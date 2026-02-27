"""Document lifecycle workflow state machine."""

from __future__ import annotations

from app.domain.states import document_stage_for
from app.domain.workflows.models import WorkflowModel
from app.errors import InvalidStateError
from app.models import DocumentStatus


class DocumentWorkflow:
    """Centralized transition rules for document lifecycle states."""

    @staticmethod
    def model() -> WorkflowModel[DocumentStatus]:
        statuses = tuple(DocumentStatus)
        transitions = {
            status: tuple(candidate for candidate in statuses if candidate in document_stage_for(status).allowed_targets)
            for status in statuses
        }
        return WorkflowModel(
            name="document_lifecycle",
            states=statuses,
            transitions=transitions,
            initial_states=(DocumentStatus.DRAFT,),
        )

    def can_transition(self, current: DocumentStatus, target: DocumentStatus) -> bool:
        return self.model().can_transition(current, target)

    def transition(self, current: DocumentStatus, target: DocumentStatus) -> DocumentStatus:
        if self.can_transition(current, target):
            return target
        raise InvalidStateError(
            "Invalid document status transition: "
            f"{current.value} -> {target.value}"
        )

    def normalize_for_new_version_candidate(self, current: DocumentStatus) -> DocumentStatus:
        return document_stage_for(current).normalize_for_new_version_candidate()
