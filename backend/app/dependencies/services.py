"""Container-backed service dependency providers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.container import AppContainer, build_container, get_container
from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.services.auth_service import AuthService
from app.services.collaboration_service import CollaborationService
from app.services.comment_service import CommentService
from app.services.document_service import DocumentService
from app.services.version_service import VersionService


def get_auth_service(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> AuthService:
    """Resolve auth service from the shared container."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.auth_service(db)


def get_comment_service(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> CommentService:
    """Resolve comment service from the shared container."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.comment_service(db)


def get_document_service(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> DocumentService:
    """Resolve tenant-scoped document service from the shared container."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.document_service(db, tenant_ctx)


def get_version_service(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> VersionService:
    """Resolve version service from the shared container."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.version_service(db)


def get_collaboration_service(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> CollaborationService:
    """Resolve collaboration service from the shared container."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.collaboration_service(db)
