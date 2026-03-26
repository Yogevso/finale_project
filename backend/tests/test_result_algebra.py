"""Tests for typed Result algebra and command/query handlers."""

import pytest

from app.application.commands.document_commands import (
    AssignCompanySetCommand,
    AssignCompanySetCommandErrorCode,
    AssignCompanySetCommandHandler,
)
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandErrorCode,
    PublishApprovedVersionCommandHandler,
)
from app.application.queries.document_queries import (
    GetDocumentQuery,
    GetDocumentQueryErrorCode,
    GetDocumentQueryHandler,
)
from app.domain.result import Result
from app.errors import ConflictError, NotFoundError, ValidationError
from app.services.document_service import DocumentService


def test_result_ok_container():
    result: Result[int, str] = Result.ok(42)

    assert result.is_ok
    assert not result.is_err
    assert result.value == 42
    with pytest.raises(RuntimeError):
        _ = result.error


def test_result_err_container():
    result: Result[int, str] = Result.err("nope")

    assert result.is_err
    assert not result.is_ok
    assert result.error == "nope"
    with pytest.raises(RuntimeError):
        _ = result.value


def test_result_requires_exactly_one_of_value_or_error():
    with pytest.raises(ValueError):
        _ = Result[int, str]()
    with pytest.raises(ValueError):
        _ = Result[int, str](_value=1, _error="bad")


def test_assign_company_set_handler_success():
    class StubAssignCompanySetUseCase:
        def __init__(self):
            self.calls = []

        def assign_company_set(self, document_id, company_ids):
            self.calls.append((document_id, list(company_ids)))
            return len(set(company_ids))

    use_case = StubAssignCompanySetUseCase()
    handler = AssignCompanySetCommandHandler(use_case)

    result = handler.execute(AssignCompanySetCommand(document_id=12, company_ids=[1, 1, 2]))

    assert result.is_ok
    assert result.value == 2
    assert use_case.calls == [(12, [1, 1, 2])]


def test_assign_company_set_handler_maps_expected_errors():
    class StubNotFoundUseCase:
        def assign_company_set(self, _document_id, _company_ids):
            raise NotFoundError("Document not found")

    class StubInvalidSetUseCase:
        def assign_company_set(self, _document_id, _company_ids):
            raise ValidationError("Some company IDs are invalid")

    not_found_result = AssignCompanySetCommandHandler(StubNotFoundUseCase()).execute(
        AssignCompanySetCommand(document_id=1, company_ids=[])
    )
    assert not_found_result.is_err
    assert not_found_result.error.code == AssignCompanySetCommandErrorCode.DOCUMENT_NOT_FOUND

    invalid_set_result = AssignCompanySetCommandHandler(StubInvalidSetUseCase()).execute(
        AssignCompanySetCommand(document_id=1, company_ids=[99])
    )
    assert invalid_set_result.is_err
    assert invalid_set_result.error.code == AssignCompanySetCommandErrorCode.INVALID_COMPANY_SET


def test_publish_approved_version_handler_maps_expected_errors(test_user):
    class StubPublishConflictUseCase:
        def publish_approved_version(self, _document_id, _version_id, _current_user):
            raise ConflictError("Cannot publish without an approved review for this version")

    handler = PublishApprovedVersionCommandHandler(StubPublishConflictUseCase())
    result = handler.execute(
        PublishApprovedVersionCommand(document_id=1, version_id=2, current_user=test_user)
    )

    assert result.is_err
    assert result.error.code == PublishApprovedVersionCommandErrorCode.CONFLICT


def test_publish_approved_version_handler_re_raises_unexpected_error(test_user):
    class StubUnexpectedUseCase:
        def publish_approved_version(self, _document_id, _version_id, _current_user):
            raise RuntimeError("boom")

    handler = PublishApprovedVersionCommandHandler(StubUnexpectedUseCase())
    with pytest.raises(RuntimeError) as exc_info:
        _ = handler.execute(
            PublishApprovedVersionCommand(document_id=1, version_id=2, current_user=test_user)
        )

    assert str(exc_info.value) == "boom"


def test_get_document_query_handler_returns_typed_result(db, test_document):
    query_handler = GetDocumentQueryHandler(DocumentService(db))

    found_result = query_handler.execute(GetDocumentQuery(document_id=test_document.id))
    assert found_result.is_ok
    assert found_result.value.id == test_document.id

    missing_result = query_handler.execute(GetDocumentQuery(document_id=999999))
    assert missing_result.is_err
    assert missing_result.error.code == GetDocumentQueryErrorCode.NOT_FOUND
