"""Unit tests for CQRS-lite command/query handlers."""

from datetime import date

from app.application.commands.document_commands import (
    CreateDocumentCommand,
    CreateDocumentCommandHandler,
    DeleteDocumentCommand,
    DeleteDocumentCommandHandler,
    DocumentCommandErrorCode,
    UpdateDocumentCommand,
    UpdateDocumentCommandHandler,
)
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
    ListDocumentsQuery,
    ListDocumentsQueryHandler,
)
from app.errors import NotFoundError, ValidationError
from app.schemas import DocumentCreate, DocumentUpdate


def test_create_document_command_handler_records_pipeline_trace(test_user):
    expected = object()

    class StubDocumentService:
        def create_document(self, _document_data, _user):
            return expected

    handler = CreateDocumentCommandHandler(StubDocumentService())
    result = handler.execute(
        CreateDocumentCommand(
            document_data=DocumentCreate(title="Doc"),
            current_user=test_user,
        )
    )

    assert result.is_ok
    assert result.value is expected
    assert handler.last_trace is not None
    assert handler.last_trace.command_name == "CreateDocumentCommand"
    assert handler.last_trace.stage_order == ("validate", "authorize", "execute", "publish")


def test_create_document_command_handler_maps_validation_error(test_user):
    class StubDocumentService:
        def create_document(self, _document_data, _user):
            raise ValidationError("Document ID already exists")

    handler = CreateDocumentCommandHandler(StubDocumentService())
    result = handler.execute(
        CreateDocumentCommand(
            document_data=DocumentCreate(title="Doc", document_number="DOC-1"),
            current_user=test_user,
        )
    )

    assert result.is_err
    assert result.error.code == DocumentCommandErrorCode.VALIDATION


def test_update_document_command_handler_maps_not_found(test_user):
    class StubDocumentService:
        def update_document(self, _document_id, _document_data, _user):
            raise NotFoundError("Document not found")

    handler = UpdateDocumentCommandHandler(StubDocumentService())
    result = handler.execute(
        UpdateDocumentCommand(
            document_id=7,
            document_data=DocumentUpdate(title="Updated"),
            current_user=test_user,
        )
    )

    assert result.is_err
    assert result.error.code == DocumentCommandErrorCode.NOT_FOUND


def test_delete_document_command_handler_records_pipeline_trace(test_user):
    class StubDocumentService:
        def __init__(self):
            self.calls = []

        def delete_document(self, document_id, user):
            self.calls.append((document_id, user.id))

    service = StubDocumentService()
    handler = DeleteDocumentCommandHandler(service)
    result = handler.execute(DeleteDocumentCommand(document_id=9, current_user=test_user))

    assert result.is_ok
    assert service.calls == [(9, test_user.id)]
    assert handler.last_trace is not None
    assert handler.last_trace.command_name == "DeleteDocumentCommand"
    assert handler.last_trace.stage_order == ("validate", "authorize", "execute", "publish")


def test_list_documents_query_handler_delegates_to_service():
    expected_items = [object(), object()]

    class StubDocumentService:
        def __init__(self):
            self.calls = []

        def get_documents(self, **kwargs):
            self.calls.append(kwargs)
            return expected_items, 2

    service = StubDocumentService()
    handler = ListDocumentsQueryHandler(service)
    result = handler.execute(
        ListDocumentsQuery(
            skip=10,
            limit=20,
            category="Guides",
            search="release",
        )
    )

    assert result.items == expected_items
    assert result.total == 2
    assert service.calls == [
        {
            "skip": 10,
            "limit": 20,
            "status": None,
            "visibility": None,
            "category": "Guides",
            "search": "release",
        }
    ]


def test_analytics_query_handler_delegates_to_service():
    class StubAnalyticsService:
        def get_overview(self, date_from, date_to):
            return {"kind": "overview", "from": date_from, "to": date_to}

        def get_recent_activity(self, limit):
            return [{"limit": limit}]

        def get_engagement(self, date_from, date_to, granularity):
            return {"kind": "engagement", "granularity": granularity}

        def get_top_documents(self, date_from, date_to, limit):
            return {"kind": "top", "limit": limit}

        def get_user_analytics(self, date_from, date_to, granularity):
            return {"kind": "users", "granularity": granularity}

        def get_content_analytics(self, date_from, date_to, granularity):
            return {"kind": "content", "granularity": granularity}

        def get_feedback_analytics(self, date_from, date_to, granularity):
            return {"kind": "feedback", "granularity": granularity}

        def get_tenant_analytics(self, date_from, date_to):
            return {"kind": "tenants", "from": date_from, "to": date_to}

    handler = AnalyticsQueryHandler(StubAnalyticsService())
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)

    assert handler.execute_overview(AnalyticsOverviewQuery(start, end))["kind"] == "overview"
    assert handler.execute_recent_activity(RecentActivityQuery(limit=5)) == [{"limit": 5}]
    assert (
        handler.execute_engagement(EngagementAnalyticsQuery(start, end))["kind"] == "engagement"
    )
    assert handler.execute_top_documents(TopDocumentsQuery(start, end, limit=3))["limit"] == 3
    assert handler.execute_user_analytics(UserAnalyticsQuery(start, end))["kind"] == "users"
    assert handler.execute_content_analytics(ContentAnalyticsQuery(start, end))["kind"] == "content"
    assert (
        handler.execute_feedback_analytics(FeedbackAnalyticsQuery(start, end))["kind"] == "feedback"
    )
    assert (
        handler.execute_tenant_analytics(TenantAnalyticsQuery(start, end))["kind"] == "tenants"
    )
