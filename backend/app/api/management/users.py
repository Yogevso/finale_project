"""User Management API Routes"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context, require_super_admin
from app.models import User, UserRole
from app.schemas import UserResponse, MessageResponse
from app.security import get_current_active_user

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get list of users.
    
    - Admins see users from their own tenant only
    - Super admins see all users
    """
    # Only admins and super_admins can list users
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    query = db.query(User)
    
    # Filter by tenant unless super admin
    if not tenant_ctx.is_super_admin:
        query = query.filter(User.tenant_id == tenant_ctx.tenant_id)
    
    users = query.order_by(User.created_at.desc()).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID.
    
    Users can view their own profile.
    Admins can view users from their tenant.
    Super admins can view all users.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Allow users to view their own profile
    if user.id == current_user.id:
        return user
    
    # Only admins can view other users
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Check tenant access
    if not tenant_ctx.is_super_admin and user.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
