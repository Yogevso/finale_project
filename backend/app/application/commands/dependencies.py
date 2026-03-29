"""Dependency providers for command handlers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.bus import CommandBusHandlerAdapter
from app.application.commands.document_commands import (
    AssignCompanySetCommand,
    AssignCompanySetCommandHandler,
    CreateDocumentCommand,
    CreateDocumentCommandHandler,
    DeleteDocumentCommand,
    DeleteDocumentCommandHandler,
    UpdateDocumentCommand,
    UpdateDocumentCommandHandler,
)
from app.application.commands.review_commands import (
    ApproveReviewCommand,
    ApproveReviewCommandHandler,
)
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandHandler,
)
from app.container import AppContainer, build_container, get_container
from app.db import get_chat_db, get_db
from app.dependencies.tenant import TenantContext, get_tenant_context


def get_assign_company_set_command_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> AssignCompanySetCommandHandler:
    """Resolve the assign-company-set command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.assign_company_set_command_handler(db, tenant_ctx)
    bus = container.command_bus()
    bus.register(AssignCompanySetCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)


def get_create_document_command_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> CreateDocumentCommandHandler:
    """Resolve the create-document command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.create_document_command_handler(db, tenant_ctx)
    bus = container.command_bus()
    bus.register(CreateDocumentCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)


def get_update_document_command_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> UpdateDocumentCommandHandler:
    """Resolve the update-document command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.update_document_command_handler(db, tenant_ctx)
    bus = container.command_bus()
    bus.register(UpdateDocumentCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)


def get_delete_document_command_handler(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    container: AppContainer = Depends(get_container),
) -> DeleteDocumentCommandHandler:
    """Resolve the delete-document command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.delete_document_command_handler(db, tenant_ctx)
    bus = container.command_bus()
    bus.register(DeleteDocumentCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)


def get_publish_approved_version_command_handler(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> PublishApprovedVersionCommandHandler:
    """Resolve the publish-approved-version command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.publish_approved_version_command_handler(db)
    bus = container.command_bus()
    bus.register(PublishApprovedVersionCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)


def get_approve_review_command_handler(
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
    container: AppContainer = Depends(get_container),
) -> ApproveReviewCommandHandler:
    """Resolve the approve-review command handler."""
    if not isinstance(container, AppContainer):
        container = build_container()
    handler = container.approve_review_command_handler(db, chat_db=chat_db)
    bus = container.command_bus()
    bus.register(ApproveReviewCommand, handler.execute)
    return CommandBusHandlerAdapter(bus)
