"""Invitation aggregate root with lifecycle invariants."""

from __future__ import annotations

from datetime import datetime

from app.domain.specifications import (
    CustomerInvitationTenantSpec,
    InvitationPendingStatusSpec,
    InvitationResendableSpec,
)
from app.models import Invitation, InvitationStatus, UserRole


class InvitationAggregate:
    """Encapsulates invitation-state invariants and transitions."""

    _customer_tenant_spec = CustomerInvitationTenantSpec()
    _pending_status_spec = InvitationPendingStatusSpec()
    _resendable_spec = InvitationResendableSpec()

    def __init__(self, invitation: Invitation):
        self.invitation = invitation

    @staticmethod
    def ensure_customer_has_tenant(role: UserRole, tenant_id: int | None) -> None:
        InvitationAggregate._customer_tenant_spec.assert_satisfied(role, tenant_id)

    def ensure_pending_for_cancel(self) -> None:
        self._pending_status_spec.assert_satisfied(self.invitation)

    def ensure_resendable(self) -> None:
        self._resendable_spec.assert_satisfied(self.invitation)

    def cancel(self) -> None:
        self.ensure_pending_for_cancel()
        self.invitation.status = InvitationStatus.CANCELLED

    def resend(self, *, new_token: str, new_expires_at: datetime) -> None:
        self.ensure_resendable()
        self.invitation.token = new_token
        self.invitation.expires_at = new_expires_at
        self.invitation.status = InvitationStatus.PENDING
