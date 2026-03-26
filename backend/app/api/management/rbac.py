"""RBAC Policy Management API - System Admin Only"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, require_system_admin
from app.models import ActionType, User, UserRole
from app.security import verify_password
from app.services.audit_helper import write_audit_log
from app.schemas.rbac import RbacPoliciesResponse, RbacPoliciesUpdate, RbacPolicyResponse
from app.services.permissions import ROLE_PERMISSIONS, Permission
from app.services.rbac_service import RbacService

router = APIRouter(prefix="/rbac/policies", tags=["rbac"])

# H-25: Permission guardrails — ceiling and floor per role.
# Ceiling: no role can exceed its default permission set.
_ROLE_MAX_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    role: frozenset(perms) for role, perms in ROLE_PERMISSIONS.items()
}

# Floor: minimum permissions that cannot be removed from a role.
_ROLE_MIN_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.SYSTEM_ADMIN: frozenset({Permission.SYSTEM_SETTINGS, Permission.MANAGE_ADMINS}),
    UserRole.ADMIN: frozenset({Permission.MANAGE_USERS, Permission.VIEW_PUBLIC_DOCS}),
    UserRole.MANAGER: frozenset({Permission.VIEW_PUBLIC_DOCS}),
    UserRole.EDITOR: frozenset({Permission.VIEW_PUBLIC_DOCS}),
    UserRole.VIEWER: frozenset({Permission.VIEW_PUBLIC_DOCS}),
    UserRole.CUSTOMER: frozenset({Permission.VIEW_PUBLIC_DOCS}),
}


def _validate_policy_invariants(policy_map: dict[UserRole, set[Permission]]) -> None:
    """Reject policy updates that violate role permission boundaries."""
    errors: list[str] = []
    for role, requested in policy_map.items():
        ceiling = _ROLE_MAX_PERMISSIONS.get(role, frozenset())
        overflow = requested - ceiling
        if overflow:
            errors.append(
                f"{role.value}: cannot grant [{', '.join(p.value for p in sorted(overflow, key=lambda p: p.value))}]"
            )
        floor = _ROLE_MIN_PERMISSIONS.get(role, frozenset())
        missing = floor - requested
        if missing:
            errors.append(
                f"{role.value}: cannot remove required [{', '.join(p.value for p in sorted(missing, key=lambda p: p.value))}]"
            )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "RBAC policy invariant violation", "violations": errors},
        )


def _policies_response(policies: dict[UserRole, set[Permission]]) -> RbacPoliciesResponse:
    return RbacPoliciesResponse(
        policies=[
            RbacPolicyResponse(role=role, permissions=sorted(policies[role], key=lambda p: p.value))
            for role in sorted(policies.keys(), key=lambda r: r.value)
        ]
    )


@router.get("", response_model=RbacPoliciesResponse)
def list_policies(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    policies = RbacService.get_policies(db)
    if not policies:
        policies = ROLE_PERMISSIONS
    return _policies_response(policies)


@router.put("", response_model=RbacPoliciesResponse, status_code=status.HTTP_200_OK)
def update_policies(
    payload: RbacPoliciesUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    # M-06: Re-authenticate admin before RBAC policy override
    admin_user = db.query(User).filter(User.id == tenant_ctx.user_id).first()
    if not admin_user or not verify_password(payload.confirm_password, admin_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password confirmation failed",
        )

    policy_map: dict[UserRole, set[Permission]] = {
        policy.role: set(policy.permissions) for policy in payload.policies
    }
    _validate_policy_invariants(policy_map)
    RbacService.upsert_policies(db, policy_map, updated_by=tenant_ctx.user_id)
    published = RbacService.publish_policies(db)

    write_audit_log(
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {
                "event": "rbac_policies_updated",
                "roles": sorted([role.value for role in policy_map.keys()]),
            }
        ),
    )
    db.commit()

    return _policies_response(published)


@router.post("/publish", response_model=RbacPoliciesResponse, status_code=status.HTTP_200_OK)
def publish_policies(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    published = RbacService.publish_policies(db)
    return _policies_response(published)
