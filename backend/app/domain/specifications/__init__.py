"""Domain invariant specifications."""

from app.domain.specifications.invariants import (
    CustomerInvitationTenantSpec,
    DocumentDraftOrActiveSpec,
    DocumentDraftStatusSpec,
    InvitationPendingStatusSpec,
    InvitationResendableSpec,
    ManagerVisibilityRoleSpec,
    ReviewApprovableVersionSpec,
    ReviewPendingStatusSpec,
    ReviewSubmitterMatchesSpec,
)
from app.domain.specifications.queries import (
    DateRangeSpec,
    RoleAccessSpec,
    TenantScopeSpec,
    VisibilitySpec,
)

__all__ = [
    "CustomerInvitationTenantSpec",
    "DocumentDraftOrActiveSpec",
    "DocumentDraftStatusSpec",
    "InvitationPendingStatusSpec",
    "InvitationResendableSpec",
    "ManagerVisibilityRoleSpec",
    "DateRangeSpec",
    "RoleAccessSpec",
    "ReviewApprovableVersionSpec",
    "ReviewPendingStatusSpec",
    "ReviewSubmitterMatchesSpec",
    "TenantScopeSpec",
    "VisibilitySpec",
]
