"""Reusable invariant specifications shared by runtime checks and tests."""

from __future__ import annotations

from dataclasses import dataclass

from app.errors import ConflictError, InvalidStateError, PermissionDeniedError, ValidationError
from app.errors.audience_errors import AudienceErrorCode
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Invitation,
    InvitationStatus,
    ReviewRequest,
    ReviewStatus,
    UserRole,
    Version,
)


class DocumentDraftStatusSpec:
    """Document must be in a submittable status to enter review submission flow."""

    _SUBMITTABLE = {DocumentStatus.DRAFT, DocumentStatus.PENDING_REVIEW, DocumentStatus.APPROVED}

    def is_satisfied_by(self, document: Document) -> bool:
        return document.status in self._SUBMITTABLE

    def assert_satisfied(self, document: Document) -> None:
        if not self.is_satisfied_by(document):
            raise InvalidStateError(
                "Document must be in draft status (or pending-review/approved) to submit for review. "
                f"Current status: {document.status.value}"
            )


class ManagerVisibilityRoleSpec:
    """Visibility mutations require manager/admin/system_admin role."""

    _ALLOWED_ROLES = {UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER}

    def is_satisfied_by(self, actor_role: UserRole) -> bool:
        return actor_role in self._ALLOWED_ROLES

    def assert_satisfied(self, actor_role: UserRole) -> None:
        if not self.is_satisfied_by(actor_role):
            raise PermissionDeniedError("Only managers can change document visibility")


class DocumentDraftOrActiveSpec:
    """Version-candidate prep allows only draft/active without status normalization."""

    _ALLOWED_STATUSES = {DocumentStatus.DRAFT, DocumentStatus.ACTIVE}

    def is_satisfied_by(self, document: Document) -> bool:
        return document.status in self._ALLOWED_STATUSES


class DocumentVisibilityCompanyAssignmentSpec:
    """Company visibility requires assignments; non-company visibility must not carry assignments."""

    def is_satisfied_by(
        self,
        *,
        visibility: DocumentVisibility,
        company_ids: list[int],
    ) -> bool:
        if visibility == DocumentVisibility.COMPANY:
            return len(company_ids) > 0
        return len(company_ids) == 0

    def assert_satisfied(
        self,
        *,
        visibility: DocumentVisibility,
        company_ids: list[int],
    ) -> None:
        if visibility == DocumentVisibility.COMPANY and not company_ids:
            raise ValidationError(
                "Company visibility requires at least one assigned company",
                error_code=AudienceErrorCode.AUDIENCE_001.value,
            )
        if visibility != DocumentVisibility.COMPANY and company_ids:
            raise ValidationError(
                "Company assignments require company visibility",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )


class ReviewPendingStatusSpec:
    """Workflow actions may execute only on pending review requests."""

    def is_satisfied_by(self, review: ReviewRequest) -> bool:
        return review.status == ReviewStatus.PENDING

    def assert_satisfied(self, review: ReviewRequest) -> None:
        if not self.is_satisfied_by(review):
            raise ConflictError(f"Review is not pending. Current status: {review.status.value}")


@dataclass(frozen=True)
class ReviewSubmitterMatchesSpec:
    """Only the original submitter may execute submitter-owned actions."""

    expected_user_id: int

    def is_satisfied_by(self, review: ReviewRequest) -> bool:
        return review.submitted_by == self.expected_user_id

    def assert_satisfied(self, review: ReviewRequest) -> None:
        if not self.is_satisfied_by(review):
            raise PermissionDeniedError("You can only cancel your own submissions")


class ReviewApprovableVersionSpec:
    """Review-linked version must exist, be latest, and remain unpublished."""

    def is_satisfied_by(
        self,
        *,
        review: ReviewRequest,
        review_version: Version | None,
        latest_version: Version | None,
    ) -> bool:
        if review.version_id is None:
            return True
        if review_version is None:
            return False
        if latest_version and latest_version.id != review.version_id:
            return False
        if review_version.is_published:
            return False
        return True

    def assert_satisfied(
        self,
        *,
        review: ReviewRequest,
        review_version: Version | None,
        latest_version: Version | None,
    ) -> None:
        if review.version_id is None:
            return
        if review_version is None:
            raise ConflictError("Review refers to a version that no longer exists")
        if latest_version and latest_version.id != review.version_id:
            raise ConflictError("Cannot approve outdated review because a newer version exists")
        if review_version.is_published:
            raise ConflictError("Version is already published")


class CustomerInvitationTenantSpec:
    """Customer invitations must always be tenant-scoped."""

    def is_satisfied_by(self, role: UserRole, tenant_id: int | None) -> bool:
        if role != UserRole.CUSTOMER:
            return True
        return tenant_id is not None

    def assert_satisfied(self, role: UserRole, tenant_id: int | None) -> None:
        if not self.is_satisfied_by(role, tenant_id):
            raise ValidationError("Customers must be assigned to a company")


class InvitationPendingStatusSpec:
    """Cancellation only applies to pending invitations."""

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return invitation.status == InvitationStatus.PENDING

    def assert_satisfied(self, invitation: Invitation) -> None:
        if not self.is_satisfied_by(invitation):
            raise ValidationError("Can only cancel pending invitations")


class InvitationResendableSpec:
    """Accepted invitations cannot be resent."""

    def is_satisfied_by(self, invitation: Invitation) -> bool:
        return invitation.status != InvitationStatus.ACCEPTED

    def assert_satisfied(self, invitation: Invitation) -> None:
        if not self.is_satisfied_by(invitation):
            raise ValidationError("Cannot resend an accepted invitation")
