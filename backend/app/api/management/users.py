"""User Management API Routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import User, UserRole
from app.schemas import UserCreate, UserUpdate, UserWithCompanyResponse
from app.security import get_current_active_user
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
