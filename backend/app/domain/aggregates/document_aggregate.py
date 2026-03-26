"""Document aggregate root with lifecycle invariants."""

from __future__ import annotations

from app.domain.specifications import (
    DocumentDraftStatusSpec,
    DocumentVisibilityCompanyAssignmentSpec,
    ManagerVisibilityRoleSpec,
)
from app.domain.workflows import DocumentWorkflow
from app.models import Document, DocumentStatus, DocumentVisibility, UserRole


class DocumentAggregate:
    """Encapsulates document lifecycle transitions and guard checks."""

    _submittable_spec = DocumentDraftStatusSpec()
    _visibility_change_spec = ManagerVisibilityRoleSpec()
    _company_visibility_assignment_spec = DocumentVisibilityCompanyAssignmentSpec()
    _workflow = DocumentWorkflow()

    def __init__(self, document: Document):
        self.document = document

    def ensure_submittable_for_review(self) -> None:
        self._submittable_spec.assert_satisfied(self.document)

    def ensure_audience_ready_for_submit(self) -> None:
        """Ensure audience configuration is valid before submitting for review."""
        company_ids = [c.id for c in (self.document.assigned_companies or [])]
        self._company_visibility_assignment_spec.assert_satisfied(
            visibility=self.document.visibility,
            company_ids=company_ids,
        )

    def ensure_visibility_change_allowed(self, actor_role: UserRole) -> None:
        self._visibility_change_spec.assert_satisfied(actor_role)

    def ensure_visibility_assignment_invariants(
        self,
        *,
        visibility: DocumentVisibility,
        company_ids: list[int],
    ) -> None:
        self._company_visibility_assignment_spec.assert_satisfied(
            visibility=visibility,
            company_ids=company_ids,
        )

    def transition_to_pending_review(self) -> None:
        self.document.status = self._workflow.transition(
            self.document.status,
            DocumentStatus.PENDING_REVIEW,
        )

    def transition_to_approved(self) -> None:
        self.document.status = self._workflow.transition(
            self.document.status,
            DocumentStatus.APPROVED,
        )

    def transition_to_draft(self) -> None:
        self.document.status = self._workflow.transition(
            self.document.status,
            DocumentStatus.DRAFT,
        )

    def transition_to_active(self) -> None:
        self.document.status = self._workflow.transition(
            self.document.status,
            DocumentStatus.ACTIVE,
        )

    def transition_to_archived(self) -> None:
        self.document.status = self._workflow.transition(
            self.document.status,
            DocumentStatus.ARCHIVED,
        )

    def restore_from_archive(self, *, has_published_version: bool) -> None:
        target_status = DocumentStatus.ACTIVE if has_published_version else DocumentStatus.DRAFT
        self.document.status = self._workflow.transition(
            self.document.status,
            target_status,
        )

    def enter_review_submission(self) -> None:
        """Keep active docs public while a new draft version moves through review."""
        if self.document.status == DocumentStatus.ACTIVE:
            return
        self.transition_to_pending_review()

    def finalize_review_approval(self) -> None:
        """Active docs stay active until the approved draft version is explicitly published."""
        if self.document.status == DocumentStatus.ACTIVE:
            return
        self.transition_to_approved()

    def revert_review_submission(self) -> None:
        """Rejecting/cancelling a review should not unpublish an already active document."""
        if self.document.status == DocumentStatus.ACTIVE:
            return
        self.transition_to_draft()

    def prepare_for_new_version_candidate(self) -> None:
        """Keep already-active docs public; normalize other states back to draft."""
        self.document.status = self._workflow.normalize_for_new_version_candidate(
            self.document.status
        )
