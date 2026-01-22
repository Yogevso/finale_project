"""Invitation Management API Routes"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import (
    Invitation,
    InvitationStatus,
    Tenant,
    User,
    UserRole,
)
from app.security import get_current_active_user

router = APIRouter()

# Invitation expiration in days
INVITATION_EXPIRY_DAYS = 7


# ========== Schemas ==========
class InvitationCreate(BaseModel):
    """Create invitation request"""

    email: EmailStr
    role: UserRole = UserRole.CUSTOMER
    tenant_id: Optional[int] = None
    message: Optional[str] = Field(None, max_length=1000)


class InvitationResponse(BaseModel):
    """Invitation response"""

    id: int
    email: str
    role: UserRole
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    invited_by: int
    inviter_name: str
    status: InvitationStatus
    message: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None


class InvitationListResponse(BaseModel):
    """Paginated invitation list"""

    items: List[InvitationResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    UserRole.SYSTEM_ADMIN: 6,
    UserRole.ADMIN: 5,
    UserRole.MANAGER: 4,
    UserRole.EDITOR: 3,
    UserRole.VIEWER: 2,
    UserRole.CUSTOMER: 1,
}


def can_invite_role(inviter_role: UserRole, target_role: UserRole) -> bool:
    """Check if an inviter can invite users with the target role"""
    if inviter_role == UserRole.SYSTEM_ADMIN:
        return True
    if inviter_role == UserRole.ADMIN:
        return target_role != UserRole.SYSTEM_ADMIN
    if inviter_role == UserRole.MANAGER:
        return target_role in [UserRole.EDITOR, UserRole.VIEWER, UserRole.CUSTOMER]
    return False


def generate_invitation_token() -> str:
    """Generate a secure random token for invitation"""
    return secrets.token_urlsafe(32)


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitation_data: InvitationCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Create a new invitation to invite a user.

    - Admins can invite users to their tenant
    - Managers can only invite editors, viewers, and customers
    - Customers MUST have a tenant assigned
    """
    # Only admins, managers, and system_admins can invite
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check role hierarchy
    if not can_invite_role(current_user.role, invitation_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot invite users with role '{invitation_data.role.value}'",
        )

    # Customers must have a tenant
    if invitation_data.role == UserRole.CUSTOMER and not invitation_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customers must be assigned to a company",
        )

    # Validate tenant exists if provided
    tenant = None
    if invitation_data.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation_data.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        # Non-system admins can only assign to their own tenant (for non-customers)
        if not tenant_ctx.is_system_admin and invitation_data.role != UserRole.CUSTOMER:
            if tenant.id != tenant_ctx.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot invite users to other companies",
                )

    # Check if email is already registered
    if db.query(User).filter(User.email == invitation_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists"
        )

    # Check for existing pending invitation
    existing = (
        db.query(Invitation)
        .filter(
            Invitation.email == invitation_data.email, Invitation.status == InvitationStatus.PENDING
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation is already pending for this email",
        )

    # Create invitation
    invitation = Invitation(
        email=invitation_data.email,
        token=generate_invitation_token(),
        role=invitation_data.role,
        tenant_id=invitation_data.tenant_id or tenant_ctx.tenant_id,
        invited_by=current_user.id,
        message=invitation_data.message,
        expires_at=datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS),
        status=InvitationStatus.PENDING,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Get tenant name for response
    tenant_name = None
    if invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            tenant_name = tenant.name

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        tenant_id=invitation.tenant_id,
        tenant_name=tenant_name,
        invited_by=invitation.invited_by,
        inviter_name=current_user.full_name,
        status=invitation.status,
        message=invitation.message,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
    )


@router.get("/invitations", response_model=InvitationListResponse)
def list_invitations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[InvitationStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    List invitations.

    - Admins see invitations for their tenant
    - System admins see all invitations
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    query = db.query(Invitation)

    # Filter by tenant unless system admin
    if not tenant_ctx.is_system_admin:
        query = query.filter(Invitation.tenant_id == tenant_ctx.tenant_id)

    # Apply status filter
    if status_filter:
        query = query.filter(Invitation.status == status_filter)

    # Get total
    total = query.count()

    # Paginate
    invitations = (
        query.order_by(Invitation.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Build response
    items = []
    for inv in invitations:
        inviter = db.query(User).filter(User.id == inv.invited_by).first()
        tenant_name = None
        if inv.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == inv.tenant_id).first()
            if tenant:
                tenant_name = tenant.name

        items.append(
            InvitationResponse(
                id=inv.id,
                email=inv.email,
                role=inv.role,
                tenant_id=inv.tenant_id,
                tenant_name=tenant_name,
                invited_by=inv.invited_by,
                inviter_name=inviter.full_name if inviter else "Unknown",
                status=inv.status,
                message=inv.message,
                expires_at=inv.expires_at,
                created_at=inv.created_at,
                accepted_at=inv.accepted_at,
            )
        )

    return InvitationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.get("/invitations/{invitation_id}", response_model=InvitationResponse)
def get_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Get a specific invitation"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not tenant_ctx.is_system_admin and invitation.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    inviter = db.query(User).filter(User.id == invitation.invited_by).first()
    tenant_name = None
    if invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            tenant_name = tenant.name

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        tenant_id=invitation.tenant_id,
        tenant_name=tenant_name,
        invited_by=invitation.invited_by,
        inviter_name=inviter.full_name if inviter else "Unknown",
        status=invitation.status,
        message=invitation.message,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
    )


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Cancel a pending invitation"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not tenant_ctx.is_system_admin and invitation.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Can only cancel pending invitations"
        )

    invitation.status = InvitationStatus.CANCELLED
    db.commit()

    return None


@router.post("/invitations/{invitation_id}/resend", response_model=InvitationResponse)
def resend_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Resend an invitation by generating a new token and extending expiration.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not tenant_ctx.is_system_admin and invitation.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if invitation.status == InvitationStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot resend an accepted invitation"
        )

    # Check if user already exists
    if db.query(User).filter(User.email == invitation.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists"
        )

    # Generate new token and extend expiration
    invitation.token = generate_invitation_token()
    invitation.expires_at = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)
    invitation.status = InvitationStatus.PENDING
    db.commit()
    db.refresh(invitation)

    inviter = db.query(User).filter(User.id == invitation.invited_by).first()
    tenant_name = None
    if invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            tenant_name = tenant.name

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        tenant_id=invitation.tenant_id,
        tenant_name=tenant_name,
        invited_by=invitation.invited_by,
        inviter_name=inviter.full_name if inviter else "Unknown",
        status=invitation.status,
        message=invitation.message,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
    )
