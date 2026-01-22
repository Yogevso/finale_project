"""User Management API Routes"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import Tenant, User, UserRole
from app.schemas import UserCreate, UserUpdate, UserWithCompanyResponse
from app.security import get_current_active_user, get_password_hash

router = APIRouter()


# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    UserRole.SYSTEM_ADMIN: 6,
    UserRole.ADMIN: 5,
    UserRole.MANAGER: 4,
    UserRole.EDITOR: 3,
    UserRole.VIEWER: 2,
    UserRole.CUSTOMER: 1,
}


def can_manage_role(manager_role: UserRole, target_role: UserRole) -> bool:
    """Check if a manager can create/edit users with the target role"""
    # System admins can manage all
    if manager_role == UserRole.SYSTEM_ADMIN:
        return True
    # Admins can manage all except system_admin
    if manager_role == UserRole.ADMIN:
        return target_role != UserRole.SYSTEM_ADMIN
    # Managers can only manage editors, viewers, and customers
    if manager_role == UserRole.MANAGER:
        return target_role in [UserRole.EDITOR, UserRole.VIEWER, UserRole.CUSTOMER]
    return False


@router.get("/users", response_model=List[UserWithCompanyResponse])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    company_id: Optional[int] = Query(None, description="Filter by company"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get list of users with optional filters.

    - Admins see users from their own tenant only
    - System admins see all users
    """
    # Only admins and system_admins can list users
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    query = db.query(User)

    # Filter by tenant unless system admin
    if not tenant_ctx.is_system_admin:
        query = query.filter(User.tenant_id == tenant_ctx.tenant_id)

    # Apply filters
    if role:
        query = query.filter(User.role == role)
    if company_id:
        query = query.filter(User.tenant_id == company_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_term))
            | (User.email.ilike(search_term))
            | (User.username.ilike(search_term))
        )

    users = query.order_by(User.created_at.desc()).all()

    # Build response with company info
    result = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "company_name": None,
            "company_slug": None,
        }
        if user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                user_dict["company_name"] = tenant.name
                user_dict["company_slug"] = tenant.slug
        result.append(user_dict)

    return result


@router.post("/users", response_model=UserWithCompanyResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Create a new user.

    - Admins can create users in their tenant
    - Managers can only create editors, viewers, and customers
    - Customers MUST have a company (tenant_id)
    """
    # Only admins, managers, and system_admins can create users
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check role hierarchy
    if not can_manage_role(current_user.role, user_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot create users with role '{user_data.role.value}'",
        )

    # Customers must have a company
    if user_data.role == UserRole.CUSTOMER and not user_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customers must be assigned to a company",
        )

    # Validate tenant exists if provided
    if user_data.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user_data.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        # Non-system admins can only assign to their own tenant
        if not tenant_ctx.is_system_admin and tenant.id != tenant_ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign users to other companies",
            )

    # Check for duplicate email/username
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        tenant_id=user_data.tenant_id or tenant_ctx.tenant_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Build response
    result = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "tenant_id": user.tenant_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "company_name": None,
        "company_slug": None,
    }
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant:
            result["company_name"] = tenant.name
            result["company_slug"] = tenant.slug

    return result


@router.get("/users/{user_id}", response_model=UserWithCompanyResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.

    Users can view their own profile.
    Admins can view users from their tenant.
    System admins can view all users.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Allow users to view their own profile
    if user.id != current_user.id:
        # Only admins can view other users
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )

        # Check tenant access
        if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Build response
    result = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "tenant_id": user.tenant_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "company_name": None,
        "company_slug": None,
    }
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant:
            result["company_name"] = tenant.name
            result["company_slug"] = tenant.slug

    return result


@router.put("/users/{user_id}", response_model=UserWithCompanyResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Update a user.

    - Users can update their own profile (limited fields)
    - Admins can update users in their tenant
    - Role changes follow hierarchy rules
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_self = user.id == current_user.id
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]

    # Non-admins can only update their own profile
    if not is_self and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check tenant access for admins
    if not is_self and not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Apply updates
    if user_data.email is not None:
        # Check for duplicate email
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )
        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    # Role change - only admins can do this
    if user_data.role is not None and is_admin:
        if not can_manage_role(current_user.role, user_data.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot assign role '{user_data.role.value}'",
            )
        # Can't demote yourself
        if is_self and ROLE_HIERARCHY.get(user_data.role, 0) < ROLE_HIERARCHY.get(user.role, 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot demote yourself"
            )
        user.role = user_data.role

    # Active status - only admins can change
    if user_data.is_active is not None and is_admin:
        # Can't deactivate yourself
        if is_self and not user_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself"
            )
        user.is_active = user_data.is_active

    # Tenant change - only admins can change
    if user_data.tenant_id is not None and is_admin:
        # Customers must have a company
        if user.role == UserRole.CUSTOMER and not user_data.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers must be assigned to a company",
            )
        if user_data.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user_data.tenant_id).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
                )
        user.tenant_id = user_data.tenant_id

    db.commit()
    db.refresh(user)

    # Build response
    result = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "tenant_id": user.tenant_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "company_name": None,
        "company_slug": None,
    }
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant:
            result["company_name"] = tenant.name
            result["company_slug"] = tenant.slug

    return result


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Delete a user (soft delete by deactivating).

    - Admins can delete users in their tenant
    - Cannot delete yourself
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check tenant access
    if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete yourself"
        )

    # Check role hierarchy - can't delete higher roles
    if not can_manage_role(current_user.role, user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete users with higher roles"
        )

    # Soft delete
    user.is_active = False
    db.commit()

    return None
