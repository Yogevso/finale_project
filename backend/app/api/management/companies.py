"""
Companies API - Admin management of companies/tenants
"""

import re
from datetime import datetime
from typing import Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_context.refresh_token_service import RefreshTokenService
from app.db import get_db
from app.dependencies.permissions import require_admin, require_system_admin
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Invitation,
    InvitationStatus,
    PasswordReset,
    Tenant,
    User,
    UserRole,
    UserSession,
    document_company_assignments,
)
from app.schemas.company import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
    CompanyUserAdd,
    CompanyUserInfo,
)

router = APIRouter(prefix="/companies", tags=["Companies"])


def _encode_documents_cursor(*, updated_at: datetime, document_id: int) -> str:
    return f"{updated_at.isoformat()}|{document_id}"


def _decode_documents_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        updated_at_raw, document_id_raw = cursor.rsplit("|", 1)
        return datetime.fromisoformat(updated_at_raw), int(document_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor format") from exc

def _enforce_tenant_scope(current_user: User, company_id: int) -> None:
    """Non-system-admins can only access their own tenant's company."""
    if current_user.role != UserRole.SYSTEM_ADMIN and current_user.tenant_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from company name"""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _empty_company_stats() -> dict[str, int]:
    return {
        "user_count": 0,
        "owned_document_count": 0,
        "assigned_document_count": 0,
        "customer_visible_document_count": 0,
        "document_count": 0,
    }


def get_company_stats_map(db: Session, tenant_ids: Sequence[int]) -> dict[int, dict[str, int]]:
    """Get company stats in bulk keyed by tenant_id."""
    unique_tenant_ids = list(dict.fromkeys(tenant_ids))
    if not unique_tenant_ids:
        return {}

    user_counts = dict(
        db.query(User.tenant_id, func.count(User.id))
        .filter(User.tenant_id.in_(unique_tenant_ids))
        .group_by(User.tenant_id)
        .all()
    )

    owned_doc_counts = dict(
        db.query(Document.tenant_id, func.count(Document.id))
        .filter(Document.tenant_id.in_(unique_tenant_ids))
        .group_by(Document.tenant_id)
        .all()
    )

    assigned_doc_counts = dict(
        db.query(
            document_company_assignments.c.tenant_id,
            func.count(document_company_assignments.c.document_id),
        )
        .filter(document_company_assignments.c.tenant_id.in_(unique_tenant_ids))
        .group_by(document_company_assignments.c.tenant_id)
        .all()
    )

    active_assigned_doc_counts = dict(
        db.query(
            document_company_assignments.c.tenant_id,
            func.count(document_company_assignments.c.document_id),
        )
        .join(
            Document,
            Document.id == document_company_assignments.c.document_id,
        )
        .filter(
            document_company_assignments.c.tenant_id.in_(unique_tenant_ids),
            Document.status == DocumentStatus.ACTIVE,
            Document.visibility == DocumentVisibility.COMPANY,
        )
        .group_by(document_company_assignments.c.tenant_id)
        .all()
    )

    public_active_count = (
        db.query(func.count(Document.id))
        .filter(
            Document.status == DocumentStatus.ACTIVE,
            Document.visibility == DocumentVisibility.PUBLIC,
        )
        .scalar()
        or 0
    )

    stats: dict[int, dict[str, int]] = {}
    for tenant_id in unique_tenant_ids:
        assigned_count = int(assigned_doc_counts.get(tenant_id, 0))
        stats[tenant_id] = {
            "user_count": int(user_counts.get(tenant_id, 0)),
            "owned_document_count": int(owned_doc_counts.get(tenant_id, 0)),
            "assigned_document_count": assigned_count,
            "customer_visible_document_count": int(public_active_count)
            + int(active_assigned_doc_counts.get(tenant_id, 0)),
            # Backward-compatible alias now mapped to assigned semantics.
            "document_count": assigned_count,
        }
    return stats


def get_company_stats(db: Session, tenant_id: int) -> dict[str, int]:
    """Get user and document stats for a single company."""
    return get_company_stats_map(db, [tenant_id]).get(tenant_id, _empty_company_stats())


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    company_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List all companies with pagination and filtering.
    Admin access required.
    """
    query = db.query(Tenant)

    # AD-006: scope non-system-admins to their own tenant only
    if current_user.role != UserRole.SYSTEM_ADMIN:
        query = query.filter(Tenant.id == current_user.tenant_id)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Tenant.name.ilike(search_term),
                Tenant.slug.ilike(search_term),
                Tenant.contact_email.ilike(search_term),
            )
        )

    if company_type:
        query = query.filter(Tenant.company_type == company_type)

    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)

    # Get total count
    total = query.count()

    # Pagination
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # Get companies
    companies = query.order_by(Tenant.name).offset(offset).limit(per_page).all()
    company_ids = [company.id for company in companies]
    stats_by_company_id = get_company_stats_map(db, company_ids)

    # Build response with stats
    items = []
    for company in companies:
        stats = stats_by_company_id.get(company.id, _empty_company_stats())
        items.append(
            CompanyResponse(
                id=company.id,
                name=company.name,
                slug=company.slug,
                contact_email=company.contact_email,
                company_type=company.company_type or "customer",
                company_logo=company.company_logo,
                is_active=company.is_active,
                user_count=stats["user_count"],
                owned_document_count=stats["owned_document_count"],
                assigned_document_count=stats["assigned_document_count"],
                customer_visible_document_count=stats["customer_visible_document_count"],
                document_count=stats["document_count"],
                created_at=company.created_at,
                updated_at=company.updated_at,
            )
        )

    return CompanyListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=pages,
    )


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Create a new company.
    Admin access required.
    """
    # Generate slug if not provided
    slug = company_data.slug or generate_slug(company_data.name)

    # Check if slug already exists
    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company with this slug already exists")

    # Create company
    company = Tenant(
        name=company_data.name,
        slug=slug,
        contact_email=company_data.contact_email,
        company_type=company_data.company_type,
        company_logo=company_data.company_logo,
        is_active=company_data.is_active,
    )

    db.add(company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Company with this slug already exists")
    db.refresh(company)

    return CompanyResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        contact_email=company.contact_email,
        company_type=company.company_type or "customer",
        company_logo=company.company_logo,
        is_active=company.is_active,
        user_count=0,
        owned_document_count=0,
        assigned_document_count=0,
        customer_visible_document_count=0,
        document_count=0,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get company details including users.
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    # Get users
    users = db.query(User).filter(User.tenant_id == company_id).all()
    user_infos = [
        CompanyUserInfo(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if u.role else "viewer",
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]

    stats = get_company_stats(db, company_id)

    return CompanyDetailResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        contact_email=company.contact_email,
        company_type=company.company_type or "customer",
        company_logo=company.company_logo,
        is_active=company.is_active,
        user_count=stats["user_count"],
        owned_document_count=stats["owned_document_count"],
        assigned_document_count=stats["assigned_document_count"],
        customer_visible_document_count=stats["customer_visible_document_count"],
        document_count=stats["document_count"],
        users=user_infos,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_data: CompanyUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a company.
    Admin access required.
    If deactivating (is_active=False), cascades: cancels pending invitations.
    If reactivating (is_active=True), returns company state info in headers.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    # Check slug uniqueness if changing
    if company_data.slug and company_data.slug != company.slug:
        existing = (
            db.query(Tenant)
            .filter(Tenant.slug == company_data.slug, Tenant.id != company_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Company with this slug already exists")

    # Detect deactivation event
    was_active = company.is_active
    is_deactivating = (
        company_data.is_active is False
        and was_active is True
    )
    is_reactivating = (
        company_data.is_active is True
        and was_active is False
    )

    # Update fields
    update_data = company_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    # Company deactivation cascade events
    cancelled_invitations = 0
    revoked_sessions = 0
    invalidated_tokens = 0
    if is_deactivating:
        # Cancel all pending invitations for this company
        cancelled_invitations = db.query(Invitation).filter(
            Invitation.tenant_id == company_id,
            Invitation.status == InvitationStatus.PENDING,
        ).update({"status": InvitationStatus.CANCELLED})

        # FIX-016: Revoke all active sessions for users in this company
        company_user_ids = db.query(User.id).filter(User.tenant_id == company_id).subquery()
        now = datetime.utcnow()
        revoked_sessions = db.query(UserSession).filter(
            UserSession.user_id.in_(company_user_ids),
            UserSession.revoked_at.is_(None),
        ).update({"revoked_at": now}, synchronize_session=False)

        # FIX-016: Invalidate all refresh tokens for users in this company
        invalidated_tokens = db.query(PasswordReset).filter(
            PasswordReset.user_id.in_(company_user_ids),
            PasswordReset.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)

    # Company reactivation events - log and validate state
    reactivation_info = None
    if is_reactivating:
        # Count active and inactive users for this company
        active_users = db.query(User).filter(
            User.tenant_id == company_id,
            User.is_active.is_(True),
        ).count()
        inactive_users = db.query(User).filter(
            User.tenant_id == company_id,
            User.is_active.is_(False),
        ).count()
        # Get count of cancelled invitations that could be re-sent
        cancelled_invite_count = db.query(Invitation).filter(
            Invitation.tenant_id == company_id,
            Invitation.status == InvitationStatus.CANCELLED,
        ).count()
        reactivation_info = {
            "active_users": active_users,
            "inactive_users": inactive_users,
            "cancelled_invitations": cancelled_invite_count,
        }

    db.commit()
    db.refresh(company)

    # Set lifecycle event headers
    if is_deactivating:
        response.headers["X-Company-Event"] = "deactivated"
        response.headers["X-Invitations-Cancelled"] = str(cancelled_invitations)
        response.headers["X-Sessions-Revoked"] = str(revoked_sessions)
        response.headers["X-Tokens-Invalidated"] = str(invalidated_tokens)
    elif is_reactivating and reactivation_info:
        response.headers["X-Company-Event"] = "reactivated"
        response.headers["X-Active-Users"] = str(reactivation_info["active_users"])
        response.headers["X-Inactive-Users"] = str(reactivation_info["inactive_users"])
        response.headers["X-Cancelled-Invitations"] = str(reactivation_info["cancelled_invitations"])

    stats = get_company_stats(db, company_id)

    return CompanyResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        contact_email=company.contact_email,
        company_type=company.company_type or "customer",
        company_logo=company.company_logo,
        is_active=company.is_active,
        user_count=stats["user_count"],
        owned_document_count=stats["owned_document_count"],
        assigned_document_count=stats["assigned_document_count"],
        customer_visible_document_count=stats["customer_visible_document_count"],
        document_count=stats["document_count"],
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.delete("/{company_id}")
async def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Soft delete a company (set is_active=False).
    Admin access required.
    Cascades: cancels pending invitations for the company.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check if it's the current user's tenant
    if company_id == current_user.tenant_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own company")

    # Y15-016: Only SYSTEM_ADMIN can delete other companies
    # Regular ADMINs should only manage their own company
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="Only system administrators can delete companies")

    # Company deactivation cascade events:
    # 1. Cancel all pending invitations for this company
    cancelled_invitations = db.query(Invitation).filter(
        Invitation.tenant_id == company_id,
        Invitation.status == InvitationStatus.PENDING,
    ).update({"status": InvitationStatus.CANCELLED})

    # 2. Revoke all active sessions for users in this company
    company_user_ids = db.query(User.id).filter(User.tenant_id == company_id).subquery()
    revoked_sessions = db.query(UserSession).filter(
        UserSession.user_id.in_(company_user_ids),
        UserSession.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()}, synchronize_session=False)

    # 3. Invalidate all refresh tokens for users in this company
    now = datetime.utcnow()
    invalidated_tokens = db.query(PasswordReset).filter(
        PasswordReset.user_id.in_(company_user_ids),
        PasswordReset.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    # Y15-024: Clean up orphaned company assignments from documents
    # Remove this company from document assignee lists to prevent ghost assignments
    from app.models import document_company_assignments
    removed_assignments = db.execute(
        document_company_assignments.delete().where(
            document_company_assignments.c.tenant_id == company_id
        )
    ).rowcount

    # Soft delete
    company.is_active = False
    db.commit()

    return {
        "message": "Company deactivated successfully",
        "cascade_actions": {
            "invitations_cancelled": cancelled_invitations,
            "sessions_revoked": revoked_sessions,
            "tokens_invalidated": invalidated_tokens,
            "document_assignments_removed": removed_assignments,
        },
    }


@router.get("/{company_id}/users", response_model=list[CompanyUserInfo])
async def list_company_users(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List all users in a company.
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    users = db.query(User).filter(User.tenant_id == company_id).order_by(User.full_name).all()

    return [
        CompanyUserInfo(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if u.role else "viewer",
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/{company_id}/users")
async def add_user_to_company(
    company_id: int,
    user_data: CompanyUserAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Add an existing user to a company.
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    # Find user by id or email
    user = None
    if user_data.user_id:
        user = db.query(User).filter(User.id == user_data.user_id).first()
    elif user_data.email:
        user = db.query(User).filter(User.email == user_data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cross-tenant check: only SYSTEM_ADMIN can reassign users from other tenants
    if (
        user.tenant_id is not None
        and user.tenant_id != company_id
        and current_user.role != UserRole.SYSTEM_ADMIN
    ):
        raise HTTPException(status_code=403, detail="Cannot add users from other tenants")

    # Update user's tenant
    user.tenant_id = company_id
    db.commit()

    return {"message": f"User {user.email} added to company {company.name}"}


@router.delete("/{company_id}/users/{user_id}")
async def remove_user_from_company(
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Remove a user from a company (sets tenant_id to None).
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Y15-016: Only SYSTEM_ADMIN can manage users in other companies
    if current_user.role != UserRole.SYSTEM_ADMIN and current_user.tenant_id != company_id:
        raise HTTPException(status_code=403, detail="Cannot manage users in other companies")

    user = db.query(User).filter(User.id == user_id, User.tenant_id == company_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in this company")

    # Cannot remove yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from a company")

    if user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=400,
            detail="Customers must be assigned to a company; reassign role before removal",
        )

    # Only SYSTEM_ADMIN can detach internal users (setting tenant_id to None)
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only system administrators can remove users from companies",
        )

    # Remove from company
    user.tenant_id = None
    db.commit()

    return {"message": f"User {user.email} removed from company {company.name}"}


@router.get("/{company_id}/documents")
async def list_company_documents(
    company_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    scope: str = Query("assigned", pattern="^(assigned|owned|customer_visible)$"),
    cursor: Optional[str] = Query(
        default=None,
        description="Keyset cursor in the format '<updated_at_iso>|<document_id>'",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List company documents by scope:
    - assigned: documents explicitly assigned to the company
    - owned: documents owned by the company tenant
    - customer_visible: documents visible in customer portal for the company
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    if scope == "owned":
        query = db.query(Document).filter(Document.tenant_id == company_id)
    elif scope == "customer_visible":
        query = db.query(Document).filter(
            Document.status == DocumentStatus.ACTIVE,
            or_(
                Document.visibility == DocumentVisibility.PUBLIC,
                (Document.visibility == DocumentVisibility.COMPANY)
                & (Document.assigned_companies.any(id=company_id)),
            ),
        )
    else:
        query = db.query(Document).filter(Document.assigned_companies.any(id=company_id))

    total = query.count()
    pages = (total + per_page - 1) // per_page

    if cursor:
        cursor_updated_at, cursor_document_id = _decode_documents_cursor(cursor)
        query = query.filter(
            or_(
                Document.updated_at < cursor_updated_at,
                and_(
                    Document.updated_at == cursor_updated_at,
                    Document.id < cursor_document_id,
                ),
            )
        )

    ordered = query.order_by(Document.updated_at.desc(), Document.id.desc()).limit(per_page + 1).all()
    has_more = len(ordered) > per_page
    documents = ordered[:per_page]
    next_cursor = None
    if has_more and documents:
        tail = documents[-1]
        next_cursor = _encode_documents_cursor(updated_at=tail.updated_at, document_id=tail.id)

    return {
        "items": [
            {
                "id": doc.id,
                "title": doc.title,
                "category": doc.category,
                "status": doc.status.value if doc.status else "draft",
                "visibility": doc.visibility.value if doc.visibility else "internal",
                "updated_at": doc.updated_at.isoformat(),
            }
            for doc in documents
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "scope": scope,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.get("/{company_id}/audience-blockers")
async def get_audience_blockers(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get audience dependency graph showing what blocks company deactivation.

    Returns documents that depend on this company for audience visibility,
    along with statistics showing the impact of deactivating this company.

    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _enforce_tenant_scope(current_user, company_id)

    # Get documents assigned to this company
    assigned_docs = (
        db.query(Document)
        .filter(Document.assigned_companies.any(id=company_id))
        .all()
    )

    # Get documents owned by this company
    owned_docs = (
        db.query(Document)
        .filter(Document.tenant_id == company_id)
        .all()
    )

    # Get users in this company
    users = db.query(User).filter(User.tenant_id == company_id).all()

    # Compute blockers
    blockers = {
        "company_id": company_id,
        "company_name": company.name,
        "is_active": company.is_active,
        "summary": {
            "can_deactivate": len(assigned_docs) == 0 and len(owned_docs) == 0 and len(users) == 0,
            "total_blocking_documents": len(assigned_docs) + len(owned_docs),
            "assigned_document_count": len(assigned_docs),
            "owned_document_count": len(owned_docs),
            "user_count": len(users),
        },
        "blocking_documents": {
            "assigned": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "status": doc.status.value if doc.status else "draft",
                    "visibility": doc.visibility.value if doc.visibility else "internal",
                    "reason": "Document has company visibility and is assigned to this company",
                }
                for doc in assigned_docs[:20]
            ],
            "owned": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "status": doc.status.value if doc.status else "draft",
                    "visibility": doc.visibility.value if doc.visibility else "internal",
                    "reason": "Document is owned by this company",
                }
                for doc in owned_docs[:20]
            ],
        },
        "blocking_users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if u.role else "viewer",
                "is_active": u.is_active,
            }
            for u in users[:20]
        ],
        "deactivation_impact": {
            "documents_losing_audience": len(assigned_docs),
            "users_losing_access": len([u for u in users if u.is_active]),
            "warning": (
                "Deactivating this company will remove it from all document assignments "
                "and prevent company users from accessing the platform."
                if len(assigned_docs) > 0 or len(users) > 0
                else "No blocking dependencies found."
            ),
        },
    }

    return blockers
