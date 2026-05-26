"""Portal Documents API - Customer authenticated document access."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.contexts.portal.api import PortalContextAPI
from app.application.queries.dependencies import get_portal_documents_query_handler
from app.application.queries.portal_queries import PortalDocumentsQueryHandler
from app.db import get_db
from app.dependencies.permissions import require_customer
from app.dependencies.services import get_comment_service
from app.domain.specifications import ExternalEmbedPolicySpec, LinkSharingPolicySpec
from app.models import (
    Attachment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReadingProgress,
    User,
)
from app.schemas import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.portal import (
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
    PortalFacetsResponse,
)
from app.services.attachment_service import AttachmentService
from app.services.comment_service import CommentService, PaginatedComments
from app.utils.http_headers import build_content_disposition

router = APIRouter(prefix="/portal", tags=["Customer Portal"])
logger = logging.getLogger(__name__)
portal_context_api = PortalContextAPI()


class PortalReadingProgressUpdate(BaseModel):
    progress_percent: int


class PortalReadingProgressResponse(BaseModel):
    id: int
    document_id: int
    document_title: str
    progress_percent: int
    last_read_at: datetime
    completed_at: datetime | None


class PortalDocumentProgressResponse(BaseModel):
    has_progress: bool
    progress_percent: int
    is_completed: bool
    last_read_at: datetime | None = None


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
        # Conservative: allow if the user's tenant matches the doc's tenant.
        # Full access checks are done when the user actually opens the document.
        return (
            user.tenant_id is not None
            and doc_tenant_id is not None
            and user.tenant_id == doc_tenant_id
        )
    return False


def _get_customer_progress_document_or_404(
    db: Session,
    *,
    document_id: int,
    current_user: User,
) -> Document:
    document = (
        db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status != DocumentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.visibility == DocumentVisibility.PUBLIC:
        return document

    if document.visibility == DocumentVisibility.INTERNAL:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.visibility == DocumentVisibility.COMPANY:
        assigned_ids = {company.id for company in (document.assigned_companies or [])}
        if current_user.tenant_id in assigned_ids:
            return document

    raise HTTPException(status_code=404, detail="Document not found")


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
    return portal_context_api.list_customer_documents(
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
    return portal_context_api.get_customer_document(
        document_id=document_id,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/documents/{document_id}/comments")
def list_customer_document_comments(
    document_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Comments per page"),
    review_id: int | None = Query(None, description="Filter comments by review session"),
    current_user: User = Depends(require_customer),
    comment_service: CommentService = Depends(get_comment_service),
) -> PaginatedComments:
    """List comments for a customer-visible portal document."""
    return comment_service.get_comments(
        document_id,
        current_user,
        page=page,
        page_size=page_size,
        review_id=review_id,
    )


@router.post(
    "/documents/{document_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_document_comment(
    document_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(require_customer),
    comment_service: CommentService = Depends(get_comment_service),
) -> CommentResponse:
    """Create a comment thread or reply on a customer-visible portal document."""
    return comment_service.create_comment(document_id, comment_data, current_user)


@router.patch("/documents/{document_id}/comments/{comment_id}", response_model=CommentResponse)
def update_customer_document_comment(
    document_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(require_customer),
    comment_service: CommentService = Depends(get_comment_service),
) -> CommentResponse:
    """Update a comment on a customer-visible portal document."""
    return comment_service.update_comment(document_id, comment_id, comment_data, current_user)


@router.get("/documents/{document_id}/related")
async def get_related_documents(
    document_id: int,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    return portal_context_api.get_related_documents(
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
    return portal_context_api.get_customer_attachment(
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
    doc = (
        db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    )
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
                    "Content-Disposition": build_content_disposition(
                        f"{base_name}.pdf", inline=False
                    ),
                },
            )
        except (
            Exception
        ):  # policy: LOSSY — PDF preview is optional; serve original attachment instead
            logger.debug(
                "PDF conversion unavailable for attachment %s, serving original",
                attachment_id,
                exc_info=True,
            )

    attachment, content_stream = AttachmentService.open_original_stream(
        db,
        document_id,
        attachment_id,
        current_user=current_user,
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
    # M-28: Prevent browser content-sniffing on download responses
    headers["X-Content-Type-Options"] = "nosniff"

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
    return portal_context_api.get_customer_categories(
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
    return portal_context_api.get_customer_facets(
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
    return portal_context_api.get_customer_dashboard_stats(
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
    return portal_context_api.search_customer_documents(
        q=q,
        category=category,
        page=page,
        per_page=per_page,
        current_user=current_user,
        portal_documents_query_handler=portal_documents_query_handler,
    )


@router.get("/reading-progress", response_model=list[PortalReadingProgressResponse])
async def list_reading_progress(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return the current customer's reading progress list."""
    rows = (
        db.query(
            ReadingProgress,
            Document.title,
            Document.status,
            Document.visibility,
            Document.tenant_id,
        )
        .join(Document, ReadingProgress.document_id == Document.id)
        .filter(ReadingProgress.user_id == current_user.id)
        .order_by(ReadingProgress.last_read_at.desc())
        .all()
    )

    results: list[PortalReadingProgressResponse] = []
    for progress, title, doc_status, doc_visibility, doc_tenant_id in rows:
        if not _customer_can_still_access(doc_status, doc_visibility, doc_tenant_id, current_user):
            continue
        results.append(
            PortalReadingProgressResponse(
                id=progress.id,
                document_id=progress.document_id,
                document_title=title,
                progress_percent=progress.progress_percent,
                last_read_at=progress.last_read_at,
                completed_at=progress.completed_at,
            )
        )

    return results


@router.get("/reading-progress/recent")
async def get_recently_viewed(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return recently viewed documents for the current user."""
    rows = (
        db.query(
            ReadingProgress,
            Document.title,
            Document.category,
            Document.thumbnail_url,
            Document.status,
            Document.visibility,
            Document.tenant_id,
        )
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
        results.append(
            {
                "document_id": rp.document_id,
                "title": title,
                "category": category,
                "thumbnail_url": thumb,
                "progress_percent": rp.progress_percent,
                "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None,
            }
        )
    return results


@router.get("/reading-progress/continue")
async def get_continue_reading(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return documents the user started but hasn't finished (progress < 100%)."""
    rows = (
        db.query(
            ReadingProgress,
            Document.title,
            Document.category,
            Document.thumbnail_url,
            Document.status,
            Document.visibility,
            Document.tenant_id,
        )
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
        results.append(
            {
                "document_id": rp.document_id,
                "title": title,
                "category": category,
                "thumbnail_url": thumb,
                "progress_percent": rp.progress_percent,
                "last_read_at": rp.last_read_at.isoformat() if rp.last_read_at else None,
            }
        )
    return results


@router.put("/reading-progress/{document_id}", response_model=PortalReadingProgressResponse)
async def update_reading_progress(
    document_id: int,
    data: PortalReadingProgressUpdate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Update reading progress for a portal-accessible document."""
    if data.progress_percent < 0 or data.progress_percent > 100:
        raise HTTPException(status_code=400, detail="Progress must be 0-100")

    document = _get_customer_progress_document_or_404(
        db,
        document_id=document_id,
        current_user=current_user,
    )

    progress = (
        db.query(ReadingProgress)
        .filter(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.document_id == document_id,
        )
        .first()
    )

    now = datetime.utcnow()
    if progress:
        if data.progress_percent < progress.progress_percent:
            raise HTTPException(status_code=400, detail="Progress cannot decrease")
        progress.progress_percent = data.progress_percent
        progress.last_read_at = now
        if data.progress_percent >= 100 and not progress.completed_at:
            progress.completed_at = now
    else:
        progress = ReadingProgress(
            user_id=current_user.id,
            document_id=document_id,
            progress_percent=data.progress_percent,
            last_read_at=now,
            completed_at=now if data.progress_percent >= 100 else None,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)

    return PortalReadingProgressResponse(
        id=progress.id,
        document_id=progress.document_id,
        document_title=document.title,
        progress_percent=progress.progress_percent,
        last_read_at=progress.last_read_at,
        completed_at=progress.completed_at,
    )


@router.get("/reading-progress/{document_id}", response_model=PortalDocumentProgressResponse)
async def get_document_progress(
    document_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Return reading progress for a single portal-accessible document."""
    _get_customer_progress_document_or_404(
        db,
        document_id=document_id,
        current_user=current_user,
    )

    progress = (
        db.query(ReadingProgress)
        .filter(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.document_id == document_id,
        )
        .first()
    )

    if not progress:
        return PortalDocumentProgressResponse(
            has_progress=False,
            progress_percent=0,
            is_completed=False,
        )

    return PortalDocumentProgressResponse(
        has_progress=True,
        progress_percent=progress.progress_percent,
        is_completed=progress.completed_at is not None,
        last_read_at=progress.last_read_at,
    )
