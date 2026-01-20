"""Tenant Management API - Super Admin Only"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, require_super_admin
from app.models import Tenant, User
from app.schemas.tenant import TenantCreate, TenantListResponse, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new tenant (Super Admin only).
    """
    # Check for duplicate slug
    existing = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists"
        )

    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        is_active=tenant_data.is_active
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


@router.get("", response_model=TenantListResponse)
def list_tenants(
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List all tenants (Super Admin only).
    """
    tenants = db.query(Tenant).order_by(Tenant.name).all()
    return TenantListResponse(items=tenants, total=len(tenants))


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get tenant by ID (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update tenant (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Check slug uniqueness if changing
    if tenant_data.slug and tenant_data.slug != tenant.slug:
        existing = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with slug '{tenant_data.slug}' already exists"
            )
        tenant.slug = tenant_data.slug

    if tenant_data.name is not None:
        tenant.name = tenant_data.name

    if tenant_data.is_active is not None:
        tenant.is_active = tenant_data.is_active

    if tenant_data.settings is not None:
        tenant.settings = tenant_data.settings

    db.commit()
    db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete tenant (Super Admin only).

    Warning: This will fail if there are users or documents in this tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Check for users in this tenant
    user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete tenant with {user_count} users. Reassign or delete users first."
        )

    db.delete(tenant)
    db.commit()

    return {"message": f"Tenant '{tenant.name}' deleted successfully"}


@router.get("/{tenant_id}/users", response_model=List[dict])
def get_tenant_users(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get users in a tenant (Super Admin only).
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active
        }
        for u in users
    ]
