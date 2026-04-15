"""Tests for the backend composition root and container-backed dependencies."""

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.app_factory import create_app
from app.application.commands.dependencies import (
    get_approve_review_command_handler,
    get_assign_company_set_command_handler,
    get_create_document_command_handler,
    get_delete_document_command_handler,
    get_publish_approved_version_command_handler,
    get_update_document_command_handler,
)
from app.application.contexts.documents.api import DocumentsContextAPI
from app.application.contexts.portal.api import PortalContextAPI
from app.application.contexts.users.api import UsersContextAPI
from app.application.interfaces.dependencies import (
    get_assign_company_set_use_case,
    get_publish_approved_version_use_case,
)
from app.application.queries.dependencies import (
    get_analytics_query_handler,
    get_document_query_handler,
    get_list_documents_query_handler,
    get_portal_documents_query_handler,
    get_search_query_handler,
    get_system_analytics_query_handler,
)
from app.container import AppContainer, build_container, get_container
from app.conversion import DocumentConversionPipeline
from app.dependencies.services import (
    get_auth_service,
    get_collaboration_auth_service,
    get_collaboration_service,
    get_comment_service,
    get_document_conversion_service,
    get_document_service,
    get_support_ticket_service,
    get_version_service,
)
from app.dependencies.tenant import TenantContext
from app.errors import DomainError


def _tenant_ctx_for_user(user) -> TenantContext:
    return TenantContext(
        tenant_id=user.tenant_id,
        user_id=user.id,
        user_role=user.role,
        is_system_admin=False,
    )


def test_create_app_attaches_container():
    app = create_app()

    assert isinstance(app.state.container, AppContainer)


def test_get_container_returns_state_container():
    app = FastAPI()
    app.state.container = build_container()
    request = Request(
        scope={
            "type": "http",
            "app": app,
            "method": "GET",
            "path": "/",
            "headers": [],
        }
    )

    resolved = get_container(request)

    assert resolved is app.state.container


def test_service_dependency_providers_resolve_via_container(db, test_user):
    container = build_container()
    tenant_ctx = _tenant_ctx_for_user(test_user)

    assert get_auth_service(db=db, container=container) is not None
    assert get_collaboration_auth_service(container=container) is not None
    assert get_comment_service(db=db, container=container) is not None
    assert get_version_service(db=db, container=container) is not None
    assert get_collaboration_service(db=db, container=container) is not None
    assert get_document_service(db=db, tenant_ctx=tenant_ctx, container=container) is not None
    assert get_support_ticket_service(db=db, chat_db=db, container=container) is not None
    assert isinstance(
        get_document_conversion_service(container=container), DocumentConversionPipeline
    )


def test_documents_context_api_uses_injected_container(db, test_user):
    tenant_ctx = _tenant_ctx_for_user(test_user)

    class StubDocumentService:
        def __init__(self):
            self.document_ids: list[int] = []

        def get_document(self, document_id: int):
            self.document_ids.append(document_id)
            return {"id": document_id}

    class StubContainer:
        def __init__(self):
            self.last_args = None
            self.service = StubDocumentService()

        def document_service(self, db_session, resolved_tenant_ctx, chat_db=None):
            self.last_args = (db_session, resolved_tenant_ctx, chat_db)
            return self.service

    container = StubContainer()
    api = DocumentsContextAPI(db=db, tenant_ctx=tenant_ctx, container=container)

    assert api.get_document(42) == {"id": 42}
    assert container.last_args == (db, tenant_ctx, None)
    assert container.service.document_ids == [42]


def test_users_context_api_uses_injected_container_for_session_revocation(db, test_user):
    class StubAuthService:
        def __init__(self):
            self.calls: list[tuple[int, bool]] = []

        def revoke_all_user_sessions(self, user_id: int, *, commit: bool) -> None:
            self.calls.append((user_id, commit))

    class StubContainer:
        def __init__(self):
            self.auth = StubAuthService()

        def auth_service(self, db_session):
            assert db_session is db
            return self.auth

    api = UsersContextAPI(container=StubContainer())
    api._cascade_user_deactivation(user=test_user, db=db)

    assert api.container.auth.calls == [(test_user.id, False)]


def test_portal_context_api_requires_customer(test_user, test_customer):
    api = PortalContextAPI()

    assert api.require_customer(current_user=test_customer) == test_customer

    with pytest.raises(DomainError):
        api.require_customer(current_user=test_user)


def test_use_case_and_handler_dependencies_resolve_via_container(db, test_user):
    container = build_container()
    tenant_ctx = _tenant_ctx_for_user(test_user)

    publish_use_case = get_publish_approved_version_use_case(db=db, container=container)
    assign_use_case = get_assign_company_set_use_case(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )

    assert publish_use_case is not None
    assert assign_use_case is not None

    publish_handler = get_publish_approved_version_command_handler(db=db, container=container)
    approve_handler = get_approve_review_command_handler(db=db, chat_db=db, container=container)
    create_document_handler = get_create_document_command_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    update_document_handler = get_update_document_command_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    delete_document_handler = get_delete_document_command_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    assign_handler = get_assign_company_set_command_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    query_handler = get_document_query_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    list_query_handler = get_list_documents_query_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    analytics_query_handler = get_analytics_query_handler(
        db=db,
        tenant_ctx=tenant_ctx,
        container=container,
    )
    search_query_handler = get_search_query_handler(
        db=db,
        container=container,
    )
    portal_documents_query_handler = get_portal_documents_query_handler(
        db=db,
        container=container,
    )
    system_analytics_query_handler = get_system_analytics_query_handler(
        db=db,
        container=container,
    )

    assert publish_handler is not None
    assert approve_handler is not None
    assert create_document_handler is not None
    assert update_document_handler is not None
    assert delete_document_handler is not None
    assert assign_handler is not None
    assert query_handler is not None
    assert list_query_handler is not None
    assert analytics_query_handler is not None
    assert search_query_handler is not None
    assert portal_documents_query_handler is not None
    assert system_analytics_query_handler is not None
