"""User Management API Routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_admin
from app.dependencies.services import get_auth_service
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import User, UserRole
from app.schemas import MessageResponse, UserCreate, UserUpdate, UserWithCompanyResponse
from app.security import get_current_active_user
from app.services.auth_service import AuthService
from app.web.controllers.management import UsersController

router = APIRouter()
users_controller = UsersController()


@router.get("/users", response_model=list[UserWithCompanyResponse])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    company_id: Optional[int] = Query(None, description="Filter by company"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.list_users(
        role=role,
        company_id=company_id,
        is_active=is_active,
        search=search,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.post("/users", response_model=UserWithCompanyResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.create_user(
        user_data=user_data,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.get("/users/{user_id}", response_model=UserWithCompanyResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.get_user(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.put("/users/{user_id}", response_model=UserWithCompanyResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.update_user(
        user_id=user_id,
        user_data=user_data,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    users_controller.delete_user(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )
    return None


@router.get("/users/{user_id}/company-binding")
def check_company_binding(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Check a user's company binding status.
    Returns validation info about the user-company relationship.
    Admin+ or self access required.
    """
    return users_controller.check_company_binding(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.post("/admin/users/{user_id}/unlock", response_model=MessageResponse)
def unlock_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Admin unlock endpoint for account lockout recovery."""
    _ = current_user
    auth_service.unlock_user_account(user_id)
    return MessageResponse(message="User account unlocked")
