"""Application composition root and dependency container."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.application.bus import (
    AuthorizationMiddleware,
    CommandBus,
    QueryBus,
    TracingMiddleware,
    ValidationMiddleware,
)
from app.application.commands.document_commands import (
    AssignCompanySetCommandHandler,
    CreateDocumentCommandHandler,
    DeleteDocumentCommandHandler,
    UpdateDocumentCommandHandler,
)
from app.application.commands.review_commands import ApproveReviewCommandHandler
from app.application.commands.version_commands import PublishApprovedVersionCommandHandler
from app.application.interfaces.use_cases import AssignCompanySet, PublishApprovedVersion
from app.application.policies import DocumentAccessPolicy, InvitationPolicy, ReviewPolicy
from app.application.queries.analytics_queries import AnalyticsQueryHandler
from app.application.queries.document_queries import (
    GetDocumentQueryHandler,
    ListDocumentsQueryHandler,
)
from app.application.queries.portal_queries import PortalDocumentsQueryHandler
from app.application.queries.search_queries import SearchQueryHandler
from app.auth_context import CollaborationAuthService
from app.conversion.contracts import DocumentConversionService
from app.conversion.document_pipeline import get_document_conversion_pipeline
from app.dependencies.tenant import TenantContext
from app.domain.ports import CollaborationStatePort, EmailPort, StoragePort
from app.infrastructure.composition import (
    get_collaboration_state_port,
    get_email_port,
    get_storage_port,
)
from app.legacy_wrappers import AnalyticsServiceStranglerWrapper
from app.models import UserRole
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.collaboration_service import CollaborationService
from app.services.comment_service import CommentService
from app.services.document_service import DocumentService
from app.services.support_service import SupportTicketService
from app.services.version_service import VersionService


class AppContainer:
    """Central constructor registry for app services, use-cases, and handlers."""

    def __init__(self) -> None:
        self.document_access_policy = DocumentAccessPolicy()
        self.review_policy = ReviewPolicy()
        self.invitation_policy = InvitationPolicy()

    # -------- Buses --------
    @staticmethod
    def command_bus() -> CommandBus:
        return CommandBus(
            middlewares=[
                ValidationMiddleware(),
                AuthorizationMiddleware(),
                TracingMiddleware(),
            ]
        )

    @staticmethod
    def query_bus() -> QueryBus:
        return QueryBus(
            middlewares=[
                ValidationMiddleware(),
                AuthorizationMiddleware(),
                TracingMiddleware(),
            ]
        )

    # -------- Infrastructure ports --------
    def email_port(self) -> EmailPort:
        return get_email_port()

    def storage_port(self) -> StoragePort:
        return get_storage_port()

    def collaboration_state_port(self, db: Session) -> CollaborationStatePort:
        return get_collaboration_state_port(db)

    @staticmethod
    def collaboration_auth_service() -> CollaborationAuthService:
        return CollaborationAuthService()

    # -------- Services --------
    def analytics_service(
        self,
        db: Session,
        tenant_ctx: TenantContext | None = None,
        analytics_db: Session | None = None,
        *,
        system_scope: bool = False,
    ) -> AnalyticsServiceStranglerWrapper:
        resolved_tenant_ctx = tenant_ctx
        if system_scope:
            resolved_tenant_ctx = TenantContext(
                tenant_id=None,
                user_id=0,
                user_role=UserRole.SYSTEM_ADMIN,
                is_system_admin=True,
            )
        return AnalyticsServiceStranglerWrapper(
            AnalyticsService(db, resolved_tenant_ctx, analytics_db=analytics_db)
        )

    def auth_service(self, db: Session) -> AuthService:
        return AuthService(db)

    def comment_service(self, db: Session, chat_db: Session | None = None) -> CommentService:
        return CommentService(db, chat_db=chat_db)

    def document_service(
        self,
        db: Session,
        tenant_ctx: TenantContext | None = None,
        chat_db: Session | None = None,
    ) -> DocumentService:
        return DocumentService(db, tenant_ctx, chat_db=chat_db)

    def version_service(self, db: Session, chat_db: Session | None = None) -> VersionService:
        return VersionService(db, chat_db=chat_db)

    def support_ticket_service(self, db: Session) -> SupportTicketService:
        return SupportTicketService(db)

    def collaboration_service(self, db: Session | None = None) -> CollaborationService:
        state_port = self.collaboration_state_port(db) if db else None
        return CollaborationService(
            state_port=state_port,
            document_policy=self.document_access_policy,
        )

    def document_conversion_service(self) -> DocumentConversionService:
        """Resolve the shared conversion pipeline behind a stable abstraction."""
        return get_document_conversion_pipeline()

    # -------- Use-cases --------
    def publish_approved_version_use_case(self, db: Session) -> PublishApprovedVersion:
        return self.version_service(db)

    def assign_company_set_use_case(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> AssignCompanySet:
        return self.document_service(db, tenant_ctx)

    # -------- Handlers --------
    def assign_company_set_command_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> AssignCompanySetCommandHandler:
        return AssignCompanySetCommandHandler(self.assign_company_set_use_case(db, tenant_ctx))

    def create_document_command_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> CreateDocumentCommandHandler:
        return CreateDocumentCommandHandler(self.document_service(db, tenant_ctx))

    def update_document_command_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> UpdateDocumentCommandHandler:
        return UpdateDocumentCommandHandler(self.document_service(db, tenant_ctx))

    def delete_document_command_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> DeleteDocumentCommandHandler:
        return DeleteDocumentCommandHandler(self.document_service(db, tenant_ctx))

    def publish_approved_version_command_handler(
        self,
        db: Session,
    ) -> PublishApprovedVersionCommandHandler:
        return PublishApprovedVersionCommandHandler(self.publish_approved_version_use_case(db))

    def approve_review_command_handler(self, db: Session) -> ApproveReviewCommandHandler:
        return ApproveReviewCommandHandler(
            db,
            review_policy=self.review_policy,
            document_access_policy=self.document_access_policy,
        )

    def document_query_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> GetDocumentQueryHandler:
        return GetDocumentQueryHandler(self.document_service(db, tenant_ctx))

    def list_documents_query_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
    ) -> ListDocumentsQueryHandler:
        return ListDocumentsQueryHandler(self.document_service(db, tenant_ctx))

    def analytics_query_handler(
        self,
        db: Session,
        tenant_ctx: TenantContext,
        analytics_db: Session | None = None,
    ) -> AnalyticsQueryHandler:
        return AnalyticsQueryHandler(self.analytics_service(db, tenant_ctx, analytics_db=analytics_db))

    def system_analytics_query_handler(self, db: Session, analytics_db: Session | None = None) -> AnalyticsQueryHandler:
        return AnalyticsQueryHandler(
            self.analytics_service(
                db,
                None,
                analytics_db=analytics_db,
                system_scope=True,
            )
        )

    def search_query_handler(self, db: Session) -> SearchQueryHandler:
        return SearchQueryHandler(db)

    def portal_documents_query_handler(self, db: Session) -> PortalDocumentsQueryHandler:
        return PortalDocumentsQueryHandler(db)


def build_container() -> AppContainer:
    """Build the default application container."""
    return AppContainer()


def get_container(request: Request) -> AppContainer:
    """Resolve container from app state with safe lazy fallback."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        container = build_container()
        request.app.state.container = container
    return container
