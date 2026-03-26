"""Invitation Management API Routes"""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth_context.invitation_tokens import hash_invitation_token
from app.application.policies import InvitationPolicy
from app.config import settings
from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.domain.aggregates import InvitationAggregate
from app.domain.factories import InvitationFactory
from app.models import (
    InvitationStatus,
    Tenant,
    User,
    UserRole,
)
from app.repositories import InvitationRepository, UserRepository
from app.security import get_current_active_user
from app.services.email_service import email_service
from app.utils.sanitization import sanitize_plain_text

router = APIRouter()

# Invitation expiration in days
INVITATION_EXPIRY_DAYS = 7
invitation_policy = InvitationPolicy()
_INVITATION_CREATE_CONFLICT_DETAIL = "Unable to send an invitation for that email"
_INVITATION_RESEND_CONFLICT_DETAIL = "Unable to resend invitation for that email"


def _run_async_email(coro):
    """Execute async email calls from sync endpoints/background tasks."""
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


def _send_invitation_email_task(
    to_email: str, accept_url: str, inviter_name: str, expires_days: int, message: str | None,
) -> None:
    _run_async_email(
        email_service.send_invitation(
            to_email=to_email,
            accept_url=accept_url,
            inviter_name=inviter_name,
            expires_days=expires_days,
            message=message,
        )
    )


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


def generate_invitation_token() -> str:
    """Generate a secure random token for invitation"""
    return secrets.token_urlsafe(32)


def _sanitize_invitation_message(message: str | None) -> str | None:
    return sanitize_plain_text(message)


def resolve_invitation_tenant_id(
    invitation_data: InvitationCreate, tenant_ctx: TenantContext
) -> Optional[int]:
    """
    Resolve tenant assignment for a new invitation with one consistent rule:
    - SYSTEM_ADMIN may target any tenant (or leave unset for non-customer roles).
    - Non-system users are always constrained to their own tenant.
    """
    target_tenant_id = invitation_policy.resolve_invitation_tenant_id(
        invitation_data.tenant_id,
        tenant_ctx,
    )
    if invitation_data.tenant_id is not None and target_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite users to other companies",
        )
    return target_tenant_id


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
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
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    # Only admins, managers, and system_admins can invite
    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check role hierarchy
    if not invitation_policy.can_invite_role(current_user.role, invitation_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot invite users with role '{invitation_data.role.value}'",
        )

    target_tenant_id = resolve_invitation_tenant_id(invitation_data, tenant_ctx)

    InvitationAggregate.ensure_customer_has_tenant(invitation_data.role, target_tenant_id)

    # Validate tenant exists and is active if provided
    tenant = None
    if target_tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot invite users to an inactive company",
            )

    # Check if email is already registered
    if user_repository.get_by_email(invitation_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVITATION_CREATE_CONFLICT_DETAIL,
        )

    # Check for existing pending invitation
    existing = invitation_repository.get_pending_by_email(invitation_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVITATION_CREATE_CONFLICT_DETAIL,
        )

    raw_token = generate_invitation_token()
    sanitized_message = _sanitize_invitation_message(invitation_data.message)

    invitation = InvitationFactory.create_invitation(
        email=invitation_data.email,
        token=hash_invitation_token(raw_token),
        role=invitation_data.role,
        tenant_id=target_tenant_id,
        invited_by=current_user.id,
        message=sanitized_message,
        expires_at=datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # H-12: Send invitation email in background
    accept_url = f"{settings.BASE_URL}/invitation/accept?token={quote(raw_token)}"
    background_tasks.add_task(
        _send_invitation_email_task,
        to_email=invitation.email,
        accept_url=accept_url,
        inviter_name=current_user.full_name,
        expires_days=INVITATION_EXPIRY_DAYS,
        message=invitation.message,
    )

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
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitations, total = invitation_repository.list_paginated(
        tenant_id=tenant_ctx.tenant_id,
        is_system_admin=tenant_ctx.is_system_admin,
        status_filter=status_filter,
        page=page,
        per_page=per_page,
    )

    # Build response
    inviter_ids = sorted({inv.invited_by for inv in invitations})
    inviters = user_repository.list_by_ids(inviter_ids)
    inviter_map = {user.id: user for user in inviters}

    items = []
    for inv in invitations:
        inviter = inviter_map.get(inv.invited_by)
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
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = invitation_repository.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not invitation_policy.can_access_invitation_tenant(invitation.tenant_id, tenant_ctx):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    inviter = user_repository.get_by_id(invitation.invited_by)
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
    invitation_repository = InvitationRepository(db)

    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = invitation_repository.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not invitation_policy.can_access_invitation_tenant(invitation.tenant_id, tenant_ctx):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    InvitationAggregate(invitation).cancel()
    db.commit()

    return None


@router.post("/invitations/{invitation_id}/resend", response_model=InvitationResponse)
def resend_invitation(
    invitation_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Resend an invitation by generating a new token and extending expiration.
    """
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation = invitation_repository.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check tenant access
    if not invitation_policy.can_access_invitation_tenant(invitation.tenant_id, tenant_ctx):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check company consistency for customer invitations
    if invitation.role == UserRole.CUSTOMER and invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resend: the company for this invitation no longer exists",
            )
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resend: the company for this invitation has been deactivated",
            )

    # Check if user already exists
    if user_repository.get_by_email(invitation.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVITATION_RESEND_CONFLICT_DETAIL,
        )

    # Generate new token and extend expiration
    raw_token = generate_invitation_token()
    InvitationAggregate(invitation).resend(
        new_token=hash_invitation_token(raw_token),
        new_expires_at=datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS),
    )
    db.commit()
    db.refresh(invitation)

    inviter = user_repository.get_by_id(invitation.invited_by)
    tenant_name = None
    if invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            tenant_name = tenant.name

    accept_url = f"{settings.BASE_URL}/invitation/accept?token={quote(raw_token)}"
    background_tasks.add_task(
        _send_invitation_email_task,
        to_email=invitation.email,
        accept_url=accept_url,
        inviter_name=inviter.full_name if inviter else "Unknown",
        expires_days=INVITATION_EXPIRY_DAYS,
        message=invitation.message,
    )

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


@router.get("/invitations/{invitation_id}/company-binding")
def check_invitation_company_binding(
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Check an invitation's company binding status.
    Returns validation info about the invitation-company relationship.
    Admin+ access required.
    """
    if not invitation_policy.can_manage_invitations(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invitation_repository = InvitationRepository(db)
    invitation = invitation_repository.get_by_id(invitation_id)

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if not tenant_ctx.is_system_admin and invitation.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    is_customer_invite = invitation.role == UserRole.CUSTOMER
    requires_company = is_customer_invite

    result = {
        "invitation_id": invitation.id,
        "email": invitation.email,
        "role": invitation.role.value,
        "status": invitation.status.value,
        "is_customer_invite": is_customer_invite,
        "requires_company": requires_company,
        "has_company": invitation.tenant_id is not None,
        "company_id": invitation.tenant_id,
        "company_name": None,
        "company_slug": None,
        "company_is_active": None,
        "binding_valid": True,
        "binding_issues": [],
    }

    issues = []

    if invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            result["company_name"] = tenant.name
            result["company_slug"] = tenant.slug
            result["company_is_active"] = tenant.is_active
            if not tenant.is_active:
                issues.append("Company is deactivated")
        else:
            result["company_is_active"] = False
            issues.append("Company no longer exists")
    elif requires_company:
        issues.append("Customer invitation must be bound to a company")

    result["binding_issues"] = issues
    result["binding_valid"] = len(issues) == 0

    return result
