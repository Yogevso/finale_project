"""
Portal Documents API - Customer authenticated document access
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.queries.dependencies import get_portal_documents_query_handler
from app.application.queries.portal_queries import (
    GetPortalAttachmentQuery,
    GetPortalDocumentQuery,
    ListPortalCategoriesQuery,
    ListPortalDocumentsQuery,
    PortalDashboardStatsQuery,
    PortalDocumentsQueryHandler,
    SearchPortalDocumentsQuery,
)
from app.domain.specifications import RoleAccessSpec
from app.models import User
from app.schemas.portal import (
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentListResponse,
)
from app.security import get_current_active_user

router = APIRouter(prefix="/portal", tags=["Customer Portal"])
CUSTOMER_ROLE_ACCESS_SPEC = RoleAccessSpec.customer_only()


def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency to ensure user is a customer"""
    if not CUSTOMER_ROLE_ACCESS_SPEC.is_satisfied_by(current_user):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for customer users. Use /api/v1/documents for internal access.",
        )
    return current_user


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
    """
    List documents accessible to the customer.
    Includes PUBLIC published docs and COMPANY docs assigned to their company.
    """
    return portal_documents_query_handler.execute_list_documents(
        ListPortalDocumentsQuery(
            page=page,
            per_page=per_page,
            category=category,
            search=search,
            current_user=current_user,
        )
    )


@router.get("/documents/{document_id}", response_model=PortalDocumentDetail)
async def get_customer_document(
    document_id: int,
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    """
    Get a specific document if accessible to the customer.
    """
    return portal_documents_query_handler.execute_get_document(
        GetPortalDocumentQuery(
            document_id=document_id,
            current_user=current_user,
        )
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
    """
    Get attachment info for download (customer must have document access).
    """
    return portal_documents_query_handler.execute_get_attachment(
        GetPortalAttachmentQuery(
            document_id=document_id,
            attachment_id=attachment_id,
            current_user=current_user,
        )
    )


@router.get("/categories")
async def get_customer_categories(
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    """
    Get categories with document counts for customer-accessible documents.
    """
    return portal_documents_query_handler.execute_categories(
        ListPortalCategoriesQuery(current_user=current_user)
    )


@router.get("/dashboard/stats", response_model=PortalDashboardStats)
async def get_customer_dashboard_stats(
    current_user: User = Depends(require_customer),
    portal_documents_query_handler: PortalDocumentsQueryHandler = Depends(
        get_portal_documents_query_handler
    ),
):
    """
    Get dashboard statistics for customer portal.
    """
    return portal_documents_query_handler.execute_dashboard_stats(
        PortalDashboardStatsQuery(current_user=current_user)
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
    """
    Search documents accessible to the customer.
    """
    return portal_documents_query_handler.execute_search_documents(
        SearchPortalDocumentsQuery(
            q=q,
            category=category,
            page=page,
            per_page=per_page,
            current_user=current_user,
        )
    )
