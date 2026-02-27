"""FastAPI dependency providers for application use-case interfaces."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.interfaces.use_cases import AssignCompanySet, PublishApprovedVersion
from app.container import AppContainer, build_container, get_container
from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context


def get_publish_approved_version_use_case(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> PublishApprovedVersion:
    """Resolve the publish-approved-version use-case implementation."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.publish_approved_version_use_case(db)


def get_assign_company_set_use_case(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> AssignCompanySet:
    """Resolve the assign-company-set use-case implementation."""
    if not isinstance(container, AppContainer):
        container = build_container()
    return container.assign_company_set_use_case(db, tenant_ctx)
