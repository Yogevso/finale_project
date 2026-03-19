"""Backend-for-frontend endpoints for document detail experiences."""

from __future__ import annotations

import json
import logging

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
from app.models import DocumentVisibility, ReviewRequest, User, Version
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
    published_visibility_snapshot: str | None = None,
    published_company_ids_snapshot: list[int] | None = None,
) -> AudienceAccessPreviewResponse:
    # Detect drift between current audience state and last published snapshot
    audience_changed = False
    if published_visibility_snapshot is not None:
        current_vis = visibility.value if visibility else None
        if current_vis != published_visibility_snapshot:
            audience_changed = True
        elif published_company_ids_snapshot is not None:
            current_ids = sorted(c.id for c in assigned_companies)
            if current_ids != sorted(published_company_ids_snapshot):
                audience_changed = True

    if visibility == DocumentVisibility.PUBLIC:
        return AudienceAccessPreviewResponse(
            visibility=visibility,
            is_public=True,
            includes_internal_users=True,
            target_companies=[],
            access_summary="Visible to the public (including anonymous users) and all internal users.",
            published_visibility_snapshot=published_visibility_snapshot,
            published_company_ids_snapshot=published_company_ids_snapshot,
            audience_changed_since_publish=audience_changed,
        )
    if visibility == DocumentVisibility.INTERNAL:
        return AudienceAccessPreviewResponse(
            visibility=visibility,
            is_public=False,
            includes_internal_users=True,
            target_companies=[],
            access_summary="Visible to internal users only.",
            published_visibility_snapshot=published_visibility_snapshot,
            published_company_ids_snapshot=published_company_ids_snapshot,
            audience_changed_since_publish=audience_changed,
        )
    return AudienceAccessPreviewResponse(
        visibility=visibility,
        is_public=False,
        includes_internal_users=True,
        target_companies=assigned_companies,
        access_summary="Visible to internal users and explicitly assigned companies.",
        published_visibility_snapshot=published_visibility_snapshot,
        published_company_ids_snapshot=published_company_ids_snapshot,
        audience_changed_since_publish=audience_changed,
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
    logger = logging.getLogger(__name__)

    # Document fetch is the only hard failure
    result = document_query_handler.execute(GetDocumentQuery(document_id=document_id))
    if result.is_err:
        raise NotFoundError(result.error.message)
    document = result.value

    partial_errors: list[str] = []

    # --- Attachments (soft failure) ---
    try:
        attachments = AttachmentService.get_attachments(db, document_id, current_user)
    except Exception:  # policy: LOSSY — optional section, page still usable
        logger.exception("BFF: failed to load attachments for document %s", document_id)
        attachments = []
        partial_errors.append("attachments")

    # --- Assigned companies (soft failure) ---
    try:
        assigned_companies = [
            TenantSummary(id=company.id, name=company.name, slug=company.slug)
            for company in document.assigned_companies
        ]
    except Exception:  # policy: LOSSY — optional section, page still usable
        logger.exception("BFF: failed to load assigned companies for document %s", document_id)
        assigned_companies = []
        partial_errors.append("assigned_companies")

    # --- Audience access preview with snapshot (soft failure) ---
    try:
        published_visibility_snapshot = None
        published_company_ids_snapshot = None
        latest_published_version = (
            db.query(Version)
            .filter(
                Version.document_id == document_id,
                Version.is_published.is_(True),
            )
            .order_by(Version.version_number.desc())
            .first()
        )
        if latest_published_version:
            published_visibility_snapshot = latest_published_version.audience_visibility_snapshot
            raw_ids = latest_published_version.audience_company_ids_snapshot
            if raw_ids:
                try:
                    published_company_ids_snapshot = json.loads(raw_ids)
                except (json.JSONDecodeError, TypeError):
                    published_company_ids_snapshot = None

        audience_access_preview = _build_audience_access_preview(
            visibility=document.visibility,
            assigned_companies=assigned_companies,
            published_visibility_snapshot=published_visibility_snapshot,
            published_company_ids_snapshot=published_company_ids_snapshot,
        )
    except Exception:  # policy: LOSSY — optional section, page still usable
        logger.exception("BFF: failed to build audience preview for document %s", document_id)
        audience_access_preview = AudienceAccessPreviewResponse(
            visibility=document.visibility,
            is_public=document.visibility == DocumentVisibility.PUBLIC,
            includes_internal_users=True,
            target_companies=[],
            access_summary="Unable to compute full audience preview.",
        )
        partial_errors.append("audience_access_preview")

    # --- Review history (soft failure) ---
    try:
        review_history = _load_document_review_history(db=db, document_id=document_id)
    except Exception:  # policy: LOSSY — optional section, page still usable
        logger.exception("BFF: failed to load review history for document %s", document_id)
        review_history = ReviewListResponse(
            items=[], total=0, page=1, per_page=20, has_more=False,
        )
        partial_errors.append("review_history")

    return DocumentDetailPageBundleResponse(
        document=document,
        attachments=attachments,
        assigned_companies=assigned_companies,
        audience_access_preview=audience_access_preview,
        review_history=review_history,
        partial_errors=partial_errors if partial_errors else None,
    )
