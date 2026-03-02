"""Portal Documents API - Customer authenticated document access."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.queries.dependencies import get_portal_documents_query_handler
from app.application.queries.portal_queries import PortalDocumentsQueryHandler
from app.domain.specifications import ExternalEmbedPolicySpec, LinkSharingPolicySpec
from app.models import Document, User
from app.schemas.portal import (
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
)
from app.security import get_current_active_user
from app.services.attachment_service import AttachmentService
from app.utils.http_headers import build_content_disposition
from app.web.controllers.portal import PortalDocumentsController

router = APIRouter(prefix="/portal", tags=["Customer Portal"])
portal_documents_controller = PortalDocumentsController()


def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    return portal_documents_controller.require_customer(current_user=current_user)


@router.get("/documents", response_model=PortalDocumentListResponse)
async def list_customer_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
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


@router.get("/documents/{document_id}/attachments/{attachment_id}/preview")
async def preview_customer_attachment(
    document_id: int,
    attachment_id: int,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    """Preview (PDF) an attachment through the portal's own access checks."""
    db: Session = portal_documents_query_handler.db
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    portal_documents_query_handler._ensure_customer_document_access(doc, current_user)

    attachment, content_stream, media_type, content_length = AttachmentService.open_preview_stream(
        db, document_id, attachment_id, current_user=current_user,
    )
    original_name = attachment.original_filename or attachment.filename or "preview"
    base_name = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
    preview_filename = f"{base_name}.pdf"
    embed = ExternalEmbedPolicySpec.for_document(doc)
    sharing = LinkSharingPolicySpec.for_document(doc)
    headers = {
        "Content-Disposition": build_content_disposition(preview_filename, inline=True),
        "Content-Length": str(content_length),
        "X-Frame-Options": embed.x_frame_options_header,
        "X-Sharing-Policy": ",".join(sorted(a.value for a in sharing.allowed_actions)),
    }
    return StreamingResponse(
        content=content_stream,
        media_type=media_type,
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
