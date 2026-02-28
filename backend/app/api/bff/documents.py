"""Backend-for-frontend endpoints for document detail experiences."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.application.queries.dependencies import get_document_query_handler
from app.application.queries.document_queries import (
    GetDocumentQuery,
    GetDocumentQueryHandler,
)
from app.db import get_db
from app.dependencies.permissions import require_internal_user
from app.errors import NotFoundError
from app.models import DocumentVisibility, ReviewRequest, User
from app.schemas import (
    AudienceAccessPreviewResponse,
    DocumentDetailPageBundleResponse,
    ReviewListResponse,
    TenantSummary,
)
from app.services.attachment_service import AttachmentService

router = APIRouter(prefix="/bff")

DEFAULT_REVIEW_HISTORY_PAGE = 1
DEFAULT_REVIEW_HISTORY_PER_PAGE = 20


def _build_audience_access_preview(
    *,
    visibility: DocumentVisibility,
    assigned_companies: list[TenantSummary],
) -> AudienceAccessPreviewResponse:
    if visibility == DocumentVisibility.PUBLIC:
        return AudienceAccessPreviewResponse(
            visibility=visibility,
            is_public=True,
            includes_internal_users=True,
            target_companies=[],
            access_summary="Visible to the public (including anonymous users) and all internal users.",
        )
    if visibility == DocumentVisibility.INTERNAL:
        return AudienceAccessPreviewResponse(
            visibility=visibility,
            is_public=False,
            includes_internal_users=True,
            target_companies=[],
            access_summary="Visible to internal users only.",
        )
    return AudienceAccessPreviewResponse(
        visibility=visibility,
        is_public=False,
        includes_internal_users=True,
        target_companies=assigned_companies,
        access_summary="Visible to internal users and explicitly assigned companies.",
    )


def _load_document_review_history(
    *,
    db: Session,
    document_id: int,
    page: int = DEFAULT_REVIEW_HISTORY_PAGE,
    per_page: int = DEFAULT_REVIEW_HISTORY_PER_PAGE,
) -> ReviewListResponse:
    query = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.submitter),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.document_id == document_id)
        .order_by(ReviewRequest.submitted_at.desc())
    )

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.get(
    "/documents/{document_id}/detail-page",
    response_model=DocumentDetailPageBundleResponse,
)
def get_document_detail_page_bundle(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
    document_query_handler: GetDocumentQueryHandler = Depends(get_document_query_handler),
):
    """Return an aggregated payload for the internal document detail page."""
    result = document_query_handler.execute(GetDocumentQuery(document_id=document_id))
    if result.is_err:
        raise NotFoundError(result.error.message)
    document = result.value

    attachments = AttachmentService.get_attachments(db, document_id, current_user)
    assigned_companies = [
        TenantSummary(id=company.id, name=company.name, slug=company.slug)
        for company in document.assigned_companies
    ]
    audience_access_preview = _build_audience_access_preview(
        visibility=document.visibility,
        assigned_companies=assigned_companies,
    )
    review_history = _load_document_review_history(db=db, document_id=document_id)

    return DocumentDetailPageBundleResponse(
        document=document,
        attachments=attachments,
        assigned_companies=assigned_companies,
        audience_access_preview=audience_access_preview,
        review_history=review_history,
    )
