"""Document workflow stage objects."""

from __future__ import annotations

from app.errors import InvalidStateError
from app.models import DocumentStatus


class DocumentStage:
    """Behavior for a concrete document lifecycle stage."""

    status: DocumentStatus
    allowed_targets: frozenset[DocumentStatus] = frozenset()

    def can_transition_to(self, target: DocumentStatus) -> bool:
        if target == self.status:
            return True
        return target in self.allowed_targets

    def transition_to(self, target: DocumentStatus) -> DocumentStatus:
        if self.can_transition_to(target):
            return target
        raise InvalidStateError(
            "Invalid document status transition: "
            f"{self.status.value} -> {target.value}"
        )

    def normalize_for_new_version_candidate(self) -> DocumentStatus:
        return DocumentStatus.DRAFT


class DraftDocumentStage(DocumentStage):
    status = DocumentStatus.DRAFT
    allowed_targets = frozenset({DocumentStatus.PENDING_REVIEW, DocumentStatus.ARCHIVED})

    def normalize_for_new_version_candidate(self) -> DocumentStatus:
        return DocumentStatus.DRAFT


class PendingReviewDocumentStage(DocumentStage):
    status = DocumentStatus.PENDING_REVIEW
    allowed_targets = frozenset(
        {DocumentStatus.APPROVED, DocumentStatus.DRAFT, DocumentStatus.ARCHIVED, DocumentStatus.PENDING_REVIEW}
    )


class ApprovedDocumentStage(DocumentStage):
    status = DocumentStatus.APPROVED
    allowed_targets = frozenset({DocumentStatus.ACTIVE, DocumentStatus.ARCHIVED, DocumentStatus.PENDING_REVIEW})


class ActiveDocumentStage(DocumentStage):
    status = DocumentStatus.ACTIVE
    allowed_targets = frozenset({DocumentStatus.DRAFT, DocumentStatus.ARCHIVED})

    def normalize_for_new_version_candidate(self) -> DocumentStatus:
        return DocumentStatus.ACTIVE


class ArchivedDocumentStage(DocumentStage):
    status = DocumentStatus.ARCHIVED
    allowed_targets = frozenset({DocumentStatus.DRAFT, DocumentStatus.ACTIVE})


_DOCUMENT_STAGES_BY_STATUS: dict[DocumentStatus, DocumentStage] = {
    DocumentStatus.DRAFT: DraftDocumentStage(),
    DocumentStatus.PENDING_REVIEW: PendingReviewDocumentStage(),
    DocumentStatus.APPROVED: ApprovedDocumentStage(),
    DocumentStatus.ACTIVE: ActiveDocumentStage(),
    DocumentStatus.ARCHIVED: ArchivedDocumentStage(),
}


def document_stage_for(status: DocumentStatus) -> DocumentStage:
    return _DOCUMENT_STAGES_BY_STATUS[status]
