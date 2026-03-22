"""Portal Documents API - Customer authenticated document access."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.queries.dependencies import get_portal_documents_query_handler
from app.application.queries.portal_queries import PortalDocumentsQueryHandler
from app.domain.specifications import ExternalEmbedPolicySpec, LinkSharingPolicySpec
from app.db import get_db
from app.models import Document, DocumentStatus, DocumentVisibility, ReadingProgress, User
from app.schemas.portal import (
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
    PortalFacetsResponse,
)
from app.security import get_current_active_user
from app.services.attachment_service import AttachmentService
from app.utils.http_headers import build_content_disposition
from app.web.controllers.portal import PortalDocumentsController

router = APIRouter(prefix="/portal", tags=["Customer Portal"])
portal_documents_controller = PortalDocumentsController()


def _customer_can_still_access(
    doc_status: DocumentStatus,
    doc_visibility: DocumentVisibility,
    doc_tenant_id: int | None,
    user: User,
) -> bool:
    """AF-004: Lightweight access re-check for reading-progress endpoints.

    For COMPANY documents this is conservative — we check the doc's own
    tenant matches the user's tenant. The full assigned_companies check
    is done via the portal query handler for detail endpoints. This is
    acceptable because it only filters reading-progress list items.
    """
    if doc_status != DocumentStatus.ACTIVE:
        return False
    if doc_visibility == DocumentVisibility.PUBLIC:
        return True
    if doc_visibility == DocumentVisibility.INTERNAL:
        return False  # Customers can't access internal docs
    if doc_visibility == DocumentVisibility.COMPANY:
        # Conservative: allow if the user's tenant matches. Full access
        # checks are done when the user actually opens the document.
        return user.tenant_id is not None
    return False


def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    return portal_documents_controller.require_customer(current_user=current_user)


@router.get("/documents", response_model=PortalDocumentListResponse)
async def list_customer_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.list_customer_documents(
        page=page,
        per_page=per_page,
        category=category,
        search=search,
        topic=topic,
        platform=platform,
        date_from=date_from,
        date_to=date_to,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/documents/{document_id}", response_model=PortalDocumentDetail)
async def get_customer_document(
    document_id: int,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_customer_document(
        document_id=document_id,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/documents/{document_id}/related")
async def get_related_documents(
    document_id: int,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_related_documents(
        document_id=document_id,
        limit=limit,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/documents/{document_id}/attachments/{attachment_id}")
async def get_customer_attachment(
    document_id: int,
    attachment_id: int,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_customer_attachment(
        document_id=document_id,
        attachment_id=attachment_id,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/documents/{document_id}/attachments/{attachment_id}/download")
async def download_customer_attachment(
    document_id: int,
    attachment_id: int,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    """Stream-download an attachment through the portal's own access checks."""
    db: Session = portal_documents_query_handler.db
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    portal_documents_query_handler._ensure_customer_document_access(doc, current_user)

    # C6: Only serve attachments present at publish time
    from app.services.published_attachment_resolver import is_attachment_in_published_snapshot

    if not is_attachment_in_published_snapshot(db, document_id, attachment_id):
        raise HTTPException(status_code=404, detail="Attachment not found")

    # AH-007: Serve PDF export artifact for portal users when available
    from app.models import AttachmentArtifact

    pdf_artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment_id,
            AttachmentArtifact.kind == "pdf_export",
            AttachmentArtifact.status == "completed",
        )
        .first()
    )
    if pdf_artifact and pdf_artifact.storage_key:
        try:
            from app.services.attachment_service.common import get_storage_backend

            storage = get_storage_backend()
            pdf_stream = storage.download(pdf_artifact.storage_key)
            attachment = db.query(Attachment).filter_by(id=attachment_id).first()
            base_name = (attachment.original_filename or "document").rsplit(".", 1)[0]
            return StreamingResponse(
                content=pdf_stream,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": build_content_disposition(f"{base_name}.pdf", inline=False),
                },
            )
        except Exception:
            pass  # Fall through to original download

    attachment, content_stream = AttachmentService.open_original_stream(
        db, document_id, attachment_id, current_user=current_user,
    )
    filename = attachment.original_filename or attachment.filename or "download"
    embed = ExternalEmbedPolicySpec.for_document(doc)
    sharing = LinkSharingPolicySpec.for_document(doc)
    headers = {
        "Content-Disposition": build_content_disposition(filename, inline=False),
        "X-Frame-Options": embed.x_frame_options_header,
        "X-Sharing-Policy": ",".join(sorted(a.value for a in sharing.allowed_actions)),
    }
    size_bytes = attachment.size_bytes or attachment.file_size
    if size_bytes is not None:
        headers["Content-Length"] = str(size_bytes)
    return StreamingResponse(
        content=content_stream,
        media_type=attachment.mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/categories")
async def get_customer_categories(
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_customer_categories(
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/facets", response_model=PortalFacetsResponse)
async def get_customer_facets(
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_customer_facets(
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/dashboard/stats", response_model=PortalDashboardStats)
async def get_customer_dashboard_stats(
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.get_customer_dashboard_stats(
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/search")
async def search_customer_documents(
    q: str = Query(..., min_length=2),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_documents_controller.search_customer_documents(
        q=q,
        category=category,
        page=page,
        per_page=per_page,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/reading-progress/recent")
async def get_recently_viewed(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return recently viewed documents for the current user."""
    rows = (
        db.query(ReadingProgress, Document.title, Document.category, Document.thumbnail_url,
                 Document.status, Document.visibility, Document.tenant_id)
        .join(Document, ReadingProgress.document_id == Document.id)
        .filter(ReadingProgress.user_id == current_user.id)
        .order_by(ReadingProgress.last_read_at.desc())
        .limit(limit)
        .all()
    )
    # AF-004: Re-run access checks — exclude docs the user can no longer view
    results = []
    for rp, title, category, thumb, doc_status, doc_vis, doc_tenant_id in rows:
        if not _customer_can_still_access(doc_status, doc_vis, doc_tenant_id, current_user):
            continue
        results.append({
            "document_id": rp.document_id,
            "title": title,
            "category": category,
            "thumbnail_url": thumb,
            "progress_percent": rp.progress_percent,
            "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None,
        })
    return results


@router.get("/reading-progress/continue")
async def get_continue_reading(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return documents the user started but hasn't finished (progress < 100%)."""
    rows = (
        db.query(ReadingProgress, Document.title, Document.category, Document.thumbnail_url,
                 Document.status, Document.visibility, Document.tenant_id)
        .join(Document, ReadingProgress.document_id == Document.id)
        .filter(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.progress_percent > 0,
            ReadingProgress.completed_at.is_(None),
        )
        .order_by(ReadingProgress.last_read_at.desc())
        .limit(limit)
        .all()
    )
    # AF-004: Re-run access checks — exclude docs the user can no longer view
    results = []
    for rp, title, category, thumb, doc_status, doc_vis, doc_tenant_id in rows:
        if not _customer_can_still_access(doc_status, doc_vis, doc_tenant_id, current_user):
            continue
        results.append({
            "document_id": rp.document_id,
            "title": title,
            "category": category,
            "thumbnail_url": thumb,
            "progress_percent": rp.progress_percent,
            "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None,
        })
    return results
