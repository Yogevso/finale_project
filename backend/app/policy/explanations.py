"""Policy explanation objects for authorization outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.policy.pdp import AuthorizationDecision

_REASON_DESCRIPTIONS = {
    "granted": "Authorization granted",
    "missing_subject": "No authenticated subject was provided",
    "inactive_subject": "The subject account is inactive",
    "invalid_subject_role": "The subject role is not valid",
    "missing_permission": "The subject does not have the required permission",
    "missing_any_permission": "The subject does not have any required permission",
    "missing_permissions": "No permissions were provided for evaluation",
    "role_not_allowed": "The subject role is not allowed for this action",
    "internal_user_required": "Internal staff access is required",
    "customer_user_required": "Customer role is required",
    "document_missing": "The target document does not exist",
    "document_view_denied": "The subject cannot view this document",
    "document_edit_permission_denied": "The subject lacks edit permission",
    "document_delete_permission_denied": "The subject lacks delete permission",
    "document_publish_permission_denied": "The subject lacks publish permission",
    "document_tenant_boundary_denied": "Tenant-boundary rules denied access",
    "self_review_forbidden": "Submitting user cannot review their own submission",
    "missing_review_permission": "The subject lacks review permissions",
    "review_policy_denied": "Review policy denied this action",
    "target_role_not_manageable": "The target role cannot be managed by this subject",
}


@dataclass(frozen=True)
class PolicyExplanation:
    """Human-readable and machine-readable explanation of a policy decision."""

    action: str
    reason_code: str
    summary: str
    reason_description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def message(self) -> str:
        """Compact human-facing message with stable reason code."""
        return (
            f"{self.summary} "
            f"(reason_code={self.reason_code}; reason={self.reason_description})"
        )

    def to_http_headers(self) -> dict[str, str]:
        """Response headers used for fast policy-denial diagnostics."""
        return {
            "X-Policy-Reason": self.reason_code,
            "X-Policy-Action": self.action,
        }

    def to_log_context(self) -> dict[str, Any]:
        """Structured context suitable for log payloads."""
        return {
            "policy_action": self.action,
            "policy_reason_code": self.reason_code,
            "policy_reason_description": self.reason_description,
            "policy_metadata": self.metadata,
        }

    @classmethod
    def from_decision(
        cls,
        decision: AuthorizationDecision,
        *,
        summary: str,
    ) -> PolicyExplanation:
        """Build explanation from PDP decision + endpoint summary text."""
        description = _REASON_DESCRIPTIONS.get(
            decision.reason_code,
            "Authorization decision reason is available in reason_code",
        )
        return cls(
            action=decision.action,
            reason_code=decision.reason_code,
            summary=summary,
            reason_description=description,
            metadata=dict(decision.metadata),
        )


def explain_decision(decision: AuthorizationDecision, *, summary: str) -> PolicyExplanation:
    """Create a policy explanation object for an authorization decision."""
    return PolicyExplanation.from_decision(decision, summary=summary)

