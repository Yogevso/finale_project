"""Portal Documents API - Customer authenticated document access."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.application.queries.dependencies import get_portal_documents_query_handler
from app.application.queries.portal_queries import PortalDocumentsQueryHandler
from app.models import User
from app.schemas.portal import (
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
)
from app.security import get_current_active_user
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
