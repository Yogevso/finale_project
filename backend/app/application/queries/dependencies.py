"""Dependency providers for query handlers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.bus import QueryBusHandlerAdapter
from app.application.queries.analytics_queries import (
    AnalyticsOverviewQuery,
    AnalyticsQueryHandler,
    ContentAnalyticsQuery,
    EngagementAnalyticsQuery,
    FeedbackAnalyticsQuery,
    RecentActivityQuery,
    TenantAnalyticsQuery,
    TopDocumentsQuery,
    UserAnalyticsQuery,
)
from app.application.queries.document_queries import (
    GetDocumentQuery,
    GetDocumentQueryHandler,
    ListDocumentsQuery,
    ListDocumentsQueryHandler,
)
from app.application.queries.portal_queries import (
    GetPortalAttachmentQuery,
    GetPortalDocumentQuery,
    ListPortalCategoriesQuery,
    ListPortalDocumentsQuery,
    PortalDashboardStatsQuery,
    PortalDocumentsQueryHandler,
    SearchPortalDocumentsQuery,
)
from app.application.queries.search_queries import (
    ListSavedSearchesQuery,
    SearchAutocompleteQuery,
    SearchDocumentsQuery,
    SearchFacetsQuery,
    SearchQueryHandler,
)
from app.container import AppContainer, build_container, get_container
from app.db import get_analytics_db, get_db
from app.dependencies.tenant import TenantContext, get_tenant_context


def get_document_query_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> GetDocumentQueryHandler:
    """Resolve the tenant-scoped document query handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.document_query_handler(db, tenant_ctx)
    bus = container.query_bus()
    bus.register(GetDocumentQuery, handler.execute)
    return QueryBusHandlerAdapter(bus)


def get_list_documents_query_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> ListDocumentsQueryHandler:
    """Resolve the tenant-scoped document-list query handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.list_documents_query_handler(db, tenant_ctx)
    bus = container.query_bus()
    bus.register(ListDocumentsQuery, handler.execute)
    return QueryBusHandlerAdapter(bus)


def get_analytics_query_handler(
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> AnalyticsQueryHandler:
    """Resolve tenant-scoped analytics query handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.analytics_query_handler(db, tenant_ctx, analytics_db=analytics_db)
    bus = container.query_bus()
    bus.register(AnalyticsOverviewQuery, handler.execute_overview)
    bus.register(RecentActivityQuery, handler.execute_recent_activity)
    bus.register(EngagementAnalyticsQuery, handler.execute_engagement)
    bus.register(TopDocumentsQuery, handler.execute_top_documents)
    bus.register(UserAnalyticsQuery, handler.execute_user_analytics)
    bus.register(ContentAnalyticsQuery, handler.execute_content_analytics)
    bus.register(FeedbackAnalyticsQuery, handler.execute_feedback_analytics)
    bus.register(TenantAnalyticsQuery, handler.execute_tenant_analytics)
    return QueryBusHandlerAdapter(bus)


def get_system_analytics_query_handler(
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
    container: AppContainer = Depends(get_container),
) -> AnalyticsQueryHandler:
    """Resolve system-scope analytics query handler (no tenant filter)."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.system_analytics_query_handler(db, analytics_db=analytics_db)
    bus = container.query_bus()
    bus.register(AnalyticsOverviewQuery, handler.execute_overview)
    bus.register(RecentActivityQuery, handler.execute_recent_activity)
    bus.register(EngagementAnalyticsQuery, handler.execute_engagement)
    bus.register(TopDocumentsQuery, handler.execute_top_documents)
    bus.register(UserAnalyticsQuery, handler.execute_user_analytics)
    bus.register(ContentAnalyticsQuery, handler.execute_content_analytics)
    bus.register(FeedbackAnalyticsQuery, handler.execute_feedback_analytics)
    bus.register(TenantAnalyticsQuery, handler.execute_tenant_analytics)
    return QueryBusHandlerAdapter(bus)


def get_search_query_handler(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> SearchQueryHandler:
    """Resolve search read-model query handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.search_query_handler(db)
    bus = container.query_bus()
    bus.register(SearchDocumentsQuery, handler.execute_search_documents)
    bus.register(SearchAutocompleteQuery, handler.execute_autocomplete)
    bus.register(SearchFacetsQuery, handler.execute_facets)
    bus.register(ListSavedSearchesQuery, handler.execute_list_saved_searches)
    return QueryBusHandlerAdapter(bus)


def get_portal_documents_query_handler(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> PortalDocumentsQueryHandler:
    """Resolve portal document read-model query handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.portal_documents_query_handler(db)
    bus = container.query_bus()
    bus.register(ListPortalDocumentsQuery, handler.execute_list_documents)
    bus.register(GetPortalDocumentQuery, handler.execute_get_document)
    bus.register(GetPortalAttachmentQuery, handler.execute_get_attachment)
    bus.register(ListPortalCategoriesQuery, handler.execute_categories)
    bus.register(PortalDashboardStatsQuery, handler.execute_dashboard_stats)
    bus.register(SearchPortalDocumentsQuery, handler.execute_search_documents)
    return QueryBusHandlerAdapter(bus)
