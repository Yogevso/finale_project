"""Tenant Context Dependency for Multi-Tenancy"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.security import get_current_active_user


@dataclass
class TenantContext:
    """Container for tenant context information"""
    tenant_id: Optional[int]
    user_id: int
    user_role: UserRole
    is_super_admin: bool
    
    def can_access_tenant(self, target_tenant_id: int) -> bool:
        """Check if user can access a specific tenant"""
        if self.is_super_admin:
            return True
        return self.tenant_id == target_tenant_id


async def get_tenant_context(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TenantContext:
    """
    Dependency to get tenant context from the current authenticated user.
    
    - SUPER_ADMIN users have is_super_admin=True and can access all tenants
    - Regular users are scoped to their tenant_id
    """
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    
    return TenantContext(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        is_super_admin=is_super_admin
    )


def require_super_admin(
    tenant_ctx: TenantContext = Depends(get_tenant_context)
) -> TenantContext:
    """Dependency that requires SUPER_ADMIN role"""
    if not tenant_ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return tenant_ctx


def require_tenant(
    tenant_ctx: TenantContext = Depends(get_tenant_context)
) -> TenantContext:
    """Dependency that requires a valid tenant_id (rejects super admins without tenant scope)"""
    if tenant_ctx.tenant_id is None and not tenant_ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a tenant"
        )
    return tenant_ctx
