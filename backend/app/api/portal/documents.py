"""
Portal Documents API - Customer authenticated document access
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Attachment, Document, DocumentStatus, DocumentVisibility, User, UserRole
from app.schemas.portal import (
    PortalAttachment,
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
    PortalDocumentSummary,
)
from app.security import get_current_active_user

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency to ensure user is a customer"""
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for customer users. Use /api/v1/documents for internal access.",
        )
    return current_user


def get_customer_documents_query(db: Session, user: User):
    """
    Build query for documents visible to customer:
    - All PUBLIC + PUBLISHED documents (regardless of tenant)
    - COMPANY + PUBLISHED documents assigned to customer's tenant
    """
    query = db.query(Document).filter(
        Document.status == DocumentStatus.PUBLISHED,
    )

    # Customer can see:
    # 1. PUBLIC docs (available to everyone)
    # 2. COMPANY docs that are assigned to their tenant
    from sqlalchemy import and_

    query = query.filter(
        or_(
            Document.visibility == DocumentVisibility.PUBLIC,
            and_(
                Document.visibility == DocumentVisibility.COMPANY,
                Document.assigned_companies.any(id=user.tenant_id),
            ),
        )
    )

    return query


@router.get("/documents", response_model=PortalDocumentListResponse)
async def list_customer_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    List documents accessible to the customer.
    Includes PUBLIC published docs and COMPANY docs assigned to their company.
    """
    query = get_customer_documents_query(db, current_user)

    # Apply filters
    if category:
        query = query.filter(Document.category == category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Document.title.ilike(search_term),
                Document.description.ilike(search_term),
                Document.tags.ilike(search_term),
            )
        )

    # Get total count
    total = query.count()

    # Calculate pagination
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # Get documents
    documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(per_page).all()

    # Build response
    items = []
    for doc in documents:
        attachment_count = (
            db.query(func.count(Attachment.id)).filter(Attachment.document_id == doc.id).scalar()
        )

        # Get latest version number
        latest_version = (
            max((v.version_number for v in doc.versions), default=1) if doc.versions else 1
        )

        items.append(
            PortalDocumentSummary(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                category=doc.category,
                visibility=doc.visibility.value if doc.visibility else "internal",
                version=latest_version,
                updated_at=doc.updated_at,
                has_attachments=attachment_count > 0,
            )
        )

    return PortalDocumentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/documents/{document_id}", response_model=PortalDocumentDetail)
async def get_customer_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Get a specific document if accessible to the customer.
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access - document must be published (active)
    if document.status not in [DocumentStatus.PUBLISHED, DocumentStatus.ACTIVE]:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check visibility - must be PUBLIC or COMPANY assigned to customer's tenant
    if document.visibility == DocumentVisibility.INTERNAL:
        raise HTTPException(status_code=403, detail="You don't have access to this document")

    if document.visibility == DocumentVisibility.COMPANY:
        # Check if document is assigned to customer's company
        company_ids = [c.id for c in document.assigned_companies]
        if current_user.tenant_id not in company_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this document")

    # Get attachments
    attachments = db.query(Attachment).filter(Attachment.document_id == document_id).all()

    # Parse tags
    tags = []
    if document.tags:
        tags = [t.strip() for t in document.tags.split(",") if t.strip()]

    # Get latest published version
    latest_version = None
    if document.versions:
        published_versions = [v for v in document.versions if v.is_published]
        if published_versions:
            latest_version = max(published_versions, key=lambda v: v.version_number)
        else:
            latest_version = max(document.versions, key=lambda v: v.version_number)

    content = latest_version.content if latest_version else ""
    version_number = latest_version.version_number if latest_version else 1

    return PortalDocumentDetail(
        id=document.id,
        title=document.title,
        description=document.description,
        content=content,
        category=document.category,
        tags=tags,
        visibility=document.visibility.value if document.visibility else "internal",
        version=version_number,
        created_at=document.created_at,
        updated_at=document.updated_at,
        attachments=[
            PortalAttachment(
                id=att.id,
                filename=att.filename,
                file_size=att.file_size,
                mime_type=att.mime_type,
                created_at=att.created_at,
            )
            for att in attachments
        ],
    )


@router.get("/documents/{document_id}/attachments/{attachment_id}")
async def get_customer_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Get attachment info for download (customer must have document access).
    """
    # First verify document access
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status not in [DocumentStatus.PUBLISHED, DocumentStatus.ACTIVE]:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.visibility == DocumentVisibility.INTERNAL:
        raise HTTPException(status_code=403, detail="You don't have access to this document")

    if document.visibility == DocumentVisibility.COMPANY:
        company_ids = [c.id for c in document.assigned_companies]
        if current_user.tenant_id not in company_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this document")

    # Get attachment
    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.document_id == document_id,
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "file_size": attachment.file_size,
        "mime_type": attachment.mime_type,
        "download_url": f"/api/v1/attachments/{attachment.id}/download",
    }


@router.get("/categories")
async def get_customer_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Get categories with document counts for customer-accessible documents.
    """
    query = get_customer_documents_query(db, current_user)

    # Group by category
    results = (
        query.with_entities(Document.category, func.count(Document.id).label("count"))
        .filter(Document.category.isnot(None), Document.category != "")
        .group_by(Document.category)
        .all()
    )

    return [{"category": cat, "count": count} for cat, count in results if cat]


@router.get("/dashboard/stats", response_model=PortalDashboardStats)
async def get_customer_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Get dashboard statistics for customer portal.
    """
    from app.models import Feedback, FeedbackStatus

    # Count accessible documents
    base_query = db.query(Document).filter(
        Document.tenant_id == current_user.tenant_id,
        Document.status == DocumentStatus.PUBLISHED,
    )

    public_count = base_query.filter(Document.visibility == DocumentVisibility.PUBLIC).count()

    company_count = base_query.filter(Document.visibility == DocumentVisibility.COMPANY).count()

    total_documents = public_count + company_count

    # Count feedback
    pending_feedback = (
        db.query(Feedback)
        .filter(
            Feedback.user_id == current_user.id,
            Feedback.status == FeedbackStatus.PENDING,
        )
        .count()
    )

    responded_feedback = (
        db.query(Feedback)
        .filter(
            Feedback.user_id == current_user.id,
            Feedback.status == FeedbackStatus.RESPONDED,
        )
        .count()
    )

    return PortalDashboardStats(
        total_documents=total_documents,
        public_documents=public_count,
        company_documents=company_count,
        pending_feedback=pending_feedback,
        responded_feedback=responded_feedback,
    )


@router.get("/search")
async def search_customer_documents(
    q: str = Query(..., min_length=2),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Search documents accessible to the customer.
    """
    query = get_customer_documents_query(db, current_user)

    # Apply search
    search_term = f"%{q}%"
    query = query.filter(
        or_(
            Document.title.ilike(search_term),
            Document.description.ilike(search_term),
            Document.tags.ilike(search_term),
        )
    )

    if category:
        query = query.filter(Document.category == category)

    # Get total
    total = query.count()
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # Get results
    documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(per_page).all()

    results = []
    for doc in documents:
        # Create snippet from content (get from latest version)
        snippet = ""
        content = ""
        if doc.versions:
            published_versions = [v for v in doc.versions if v.is_published]
            if published_versions:
                latest_version = max(published_versions, key=lambda v: v.version_number)
                content = latest_version.content or ""
            elif doc.versions:
                latest_version = max(doc.versions, key=lambda v: v.version_number)
                content = latest_version.content or ""

        if content:
            content_lower = content.lower()
            q_lower = q.lower()
            pos = content_lower.find(q_lower)
            if pos >= 0:
                start = max(0, pos - 50)
                end = min(len(content), pos + len(q) + 100)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
            else:
                snippet = content[:150] + "..." if len(content) > 150 else content

        results.append(
            {
                "id": doc.id,
                "title": doc.title,
                "description": doc.description,
                "category": doc.category,
                "snippet": snippet,
                "updated_at": doc.updated_at.isoformat(),
            }
        )

    return {
        "query": q,
        "results": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }
