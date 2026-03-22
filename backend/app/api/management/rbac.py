"""RBAC Policy Management API - System Admin Only"""

import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, require_system_admin
from app.models import ActionType, UserRole
from app.services.audit_helper import write_audit_log
from app.schemas.rbac import RbacPoliciesResponse, RbacPoliciesUpdate, RbacPolicyResponse
from app.services.permissions import ROLE_PERMISSIONS, Permission
from app.services.rbac_service import RbacService

router = APIRouter(prefix="/rbac/policies", tags=["rbac"])


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
    policy_map: dict[UserRole, set[Permission]] = {
        policy.role: set(policy.permissions) for policy in payload.policies
    }
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
