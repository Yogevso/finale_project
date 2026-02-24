"""
Companies API - Admin management of companies/tenants
"""

import re
from typing import Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
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
from app.security import get_current_active_user

router = APIRouter(prefix="/companies", tags=["Companies"])


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin or system_admin role"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


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
        pages=pages,
    )


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
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
    db.commit()
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a company.
    Admin access required.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check slug uniqueness if changing
    if company_data.slug and company_data.slug != company.slug:
        existing = (
            db.query(Tenant)
            .filter(Tenant.slug == company_data.slug, Tenant.id != company_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Company with this slug already exists")

    # Update fields
    update_data = company_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

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
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check if it's the current user's tenant
    if company_id == current_user.tenant_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own company")

    # Soft delete
    company.is_active = False
    db.commit()

    return {"message": "Company deactivated successfully"}


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

    # Find user by id or email
    user = None
    if user_data.user_id:
        user = db.query(User).filter(User.id == user_data.user_id).first()
    elif user_data.email:
        user = db.query(User).filter(User.email == user_data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
    offset = (page - 1) * per_page

    documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(per_page).all()

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
    }
