"""
AH-012: Permission Debugger Admin API

Explains why a user can/cannot access a document by showing the access policy
evaluation chain.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_admin
from app.dependencies.tenant import TenantContext
from app.models import Document, DocumentStatus, DocumentVisibility, User, UserRole
from app.services.permissions import ROLE_PERMISSIONS, Permission

router = APIRouter(prefix="/admin/permissions", tags=["permission-debugger"])


class PermissionCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


class AccessExplanation(BaseModel):
    user_id: int
    document_id: int
    user_role: str
    user_tenant_id: Optional[int]
    document_visibility: str
    document_status: str
    document_tenant_id: Optional[int]
    can_view: bool
    can_edit: bool
    can_delete: bool
    can_publish: bool
    checks: list[PermissionCheckResult]


@router.get("/debug/{user_id}/{document_id}", response_model=AccessExplanation)
def debug_access(
    user_id: int,
    document_id: int,
    tenant_ctx: TenantContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AH-012: Explain why a user can/cannot access a document.

    Returns a detailed breakdown of the access policy evaluation chain showing
    each check and its result.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    checks: list[PermissionCheckResult] = []

    # Helper to get role
    def get_role(u: User) -> Optional[UserRole]:
        if not u:
            return None
        if isinstance(u.role, UserRole):
            return u.role
        try:
            return UserRole(u.role)
        except (ValueError, KeyError):
            return None

    role = get_role(user)
    is_active = user.is_active
    is_internal = role != UserRole.CUSTOMER if role else False
    is_system_admin = role == UserRole.SYSTEM_ADMIN

    # Check 1: User active status
    checks.append(
        PermissionCheckResult(
            name="user_is_active",
            passed=is_active,
            reason=f"User active={is_active}. Inactive users cannot access documents.",
        )
    )

    # Check 2: User role classification
    checks.append(
        PermissionCheckResult(
            name="user_role_type",
            passed=True,  # Informational
            reason=f"User role={role.value if role else 'None'}. Internal={is_internal}, SystemAdmin={is_system_admin}",
        )
    )

    # Check 3: Tenant boundary
    same_tenant = False
    if is_system_admin:
        same_tenant = True
        checks.append(
            PermissionCheckResult(
                name="tenant_boundary", passed=True, reason="System admin bypasses tenant boundary."
            )
        )
    elif document.tenant_id and user.tenant_id:
        same_tenant = document.tenant_id == user.tenant_id
        checks.append(
            PermissionCheckResult(
                name="tenant_boundary",
                passed=same_tenant,
                reason=f"User tenant_id={user.tenant_id}, Document tenant_id={document.tenant_id}. Match={same_tenant}",
            )
        )
    else:
        same_tenant = True
        checks.append(
            PermissionCheckResult(
                name="tenant_boundary",
                passed=True,
                reason=f"No strict tenant boundary (user={user.tenant_id}, doc={document.tenant_id}).",
            )
        )

    # Check 4: Document visibility
    visibility = document.visibility
    status = document.status

    can_view = False
    view_reason = ""

    if visibility == DocumentVisibility.PUBLIC:
        if status == DocumentStatus.ACTIVE:
            can_view = True
            view_reason = "Public document is published/active → anyone can view."
        elif is_internal:
            can_view = True
            view_reason = "Public document not yet active, but internal user can still view."
        else:
            view_reason = "Public document not active, and user is external → no view."

    elif visibility == DocumentVisibility.INTERNAL:
        if is_internal:
            can_view = True
            view_reason = "Internal visibility and user is internal → can view."
        else:
            view_reason = "Internal visibility but user is external (customer) → no view."

    elif visibility == DocumentVisibility.COMPANY:
        if is_internal:
            can_view = True
            view_reason = "Company visibility and user is internal → can view."
        elif role == UserRole.CUSTOMER and user.tenant_id:
            assigned_ids = [t.id for t in document.assigned_companies]
            if user.tenant_id in assigned_ids:
                can_view = True
                view_reason = f"Company visibility, customer's tenant {user.tenant_id} in assigned list {assigned_ids} → can view."
            else:
                view_reason = f"Company visibility, customer's tenant {user.tenant_id} NOT in assigned list {assigned_ids} → no view."
        else:
            view_reason = "Company visibility, user has no matching company assignment."

    else:
        view_reason = f"Unknown visibility={visibility}."

    checks.append(
        PermissionCheckResult(name="visibility_check", passed=can_view, reason=view_reason)
    )

    # Check 5: Permission-based editing rights
    perms = ROLE_PERMISSIONS.get(role, set()) if role else set()

    has_edit = Permission.EDIT_DOCUMENT in perms
    has_delete = Permission.DELETE_DOCUMENT in perms
    has_publish = Permission.PUBLISH_DOCUMENT in perms

    checks.append(
        PermissionCheckResult(
            name="role_permissions",
            passed=True,  # Informational
            reason=f"Role {role.value if role else 'None'} permissions: EDIT={has_edit}, DELETE={has_delete}, PUBLISH={has_publish}",
        )
    )

    # Final access decisions
    can_edit = is_active and has_edit and same_tenant
    can_delete = is_active and has_delete and same_tenant
    can_publish = is_active and has_publish and same_tenant

    checks.append(
        PermissionCheckResult(
            name="can_edit_final",
            passed=can_edit,
            reason=f"Can edit = active({is_active}) AND has_edit({has_edit}) AND same_tenant({same_tenant}) → {can_edit}",
        )
    )
    checks.append(
        PermissionCheckResult(
            name="can_delete_final",
            passed=can_delete,
            reason=f"Can delete = active({is_active}) AND has_delete({has_delete}) AND same_tenant({same_tenant}) → {can_delete}",
        )
    )
    checks.append(
        PermissionCheckResult(
            name="can_publish_final",
            passed=can_publish,
            reason=f"Can publish = active({is_active}) AND has_publish({has_publish}) AND same_tenant({same_tenant}) → {can_publish}",
        )
    )

    return AccessExplanation(
        user_id=user_id,
        document_id=document_id,
        user_role=role.value if role else "none",
        user_tenant_id=user.tenant_id,
        document_visibility=visibility.value if visibility else "unknown",
        document_status=status.value if status else "unknown",
        document_tenant_id=document.tenant_id,
        can_view=can_view and is_active,
        can_edit=can_edit,
        can_delete=can_delete,
        can_publish=can_publish,
        checks=checks,
    )
