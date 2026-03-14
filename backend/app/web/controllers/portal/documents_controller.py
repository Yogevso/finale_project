"""Class-based controller for customer portal document endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.application.queries.portal_queries import (
    GetPortalAttachmentQuery,
    GetPortalDocumentQuery,
    ListPortalCategoriesQuery,
    ListPortalDocumentsQuery,
    ListPortalFacetsQuery,
    PortalDashboardStatsQuery,
    PortalDocumentsQueryHandler,
    RelatedDocumentsQuery,
    SearchPortalDocumentsQuery,
)
from app.domain.specifications import RoleAccessSpec
from app.models import User


class PortalDocumentsController:
    """HTTP-facing orchestration for portal document routes."""

    def __init__(self) -> None:
        self._customer_role_access_spec = RoleAccessSpec.customer_only()

    def require_customer(self, *, current_user: User) -> User:
        if not self._customer_role_access_spec.is_satisfied_by(current_user):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This endpoint is only for customer users. "
                    "Use /api/v1/documents for internal access."
                ),
            )
        return current_user

    def list_customer_documents(
        self,
        *,
        page: int,
        per_page: int,
        category: Optional[str],
        search: Optional[str],
        topic: Optional[str] = None,
        platform: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_list_documents(
            ListPortalDocumentsQuery(
                page=page,
                per_page=per_page,
                category=category,
                search=search,
                current_user=current_user,
                topic=topic,
                platform=platform,
                date_from=date_from,
                date_to=date_to,
            )
        )

    def get_customer_document(
        self,
        *,
        document_id: int,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_get_document(
            GetPortalDocumentQuery(
                document_id=document_id,
                current_user=current_user,
            )
        )

    def get_customer_attachment(
        self,
        *,
        document_id: int,
        attachment_id: int,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_get_attachment(
            GetPortalAttachmentQuery(
                document_id=document_id,
                attachment_id=attachment_id,
                current_user=current_user,
            )
        )

    def get_customer_categories(
        self,
        *,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_categories(
            ListPortalCategoriesQuery(current_user=current_user)
        )

    def get_customer_dashboard_stats(
        self,
        *,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_dashboard_stats(
            PortalDashboardStatsQuery(current_user=current_user)
        )

    def search_customer_documents(
        self,
        *,
        q: str,
        category: Optional[str],
        page: int,
        per_page: int,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_search_documents(
            SearchPortalDocumentsQuery(
                q=q,
                category=category,
                page=page,
                per_page=per_page,
                current_user=current_user,
            )
        )

    def get_customer_facets(
        self,
        *,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_facets(
            ListPortalFacetsQuery(current_user=current_user)
        )

    def get_related_documents(
        self,
        *,
        document_id: int,
        limit: int,
        current_user: User,
        portal_documents_query_handler: PortalDocumentsQueryHandler,
    ):
        return portal_documents_query_handler.execute_related_documents(
            RelatedDocumentsQuery(
                document_id=document_id,
                current_user=current_user,
                limit=limit,
            )
        )
