"""Application commands for document workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, status

from app.application.interfaces.use_cases import AssignCompanySet
from app.application.pipeline import (
    CommandContext,
    CommandExecutionTrace,
    CommandPipeline,
    FunctionCommandAuthorizer,
    FunctionCommandExecutor,
    FunctionCommandPublisher,
    FunctionCommandValidator,
)
from app.domain.result import Result
from app.errors import NotFoundError, ValidationError
from app.models import Document, User
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.document_service import DocumentService


class AssignCompanySetCommandErrorCode(str, Enum):
    """Expected assignment command failure categories."""

    DOCUMENT_NOT_FOUND = "document_not_found"
    INVALID_COMPANY_SET = "invalid_company_set"


class DocumentCommandErrorCode(str, Enum):
    """Expected document command failure categories."""

    NOT_FOUND = "not_found"
    VALIDATION = "validation"


@dataclass(frozen=True, slots=True)
class DocumentCommandError:
    """Typed document command error payload."""

    code: DocumentCommandErrorCode
    message: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class AssignCompanySetCommandError:
    """Typed assignment command error payload."""

    code: AssignCompanySetCommandErrorCode
    message: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class AssignCompanySetCommand:
    """Replace the full company assignment set for a document."""

    document_id: int
    company_ids: tuple[int, ...]
    if_match: str | None = None

    def __post_init__(self) -> None:
        # Normalize inbound mutable sequences (e.g. request lists) to an immutable tuple.
        object.__setattr__(self, "company_ids", tuple(self.company_ids))


@dataclass(frozen=True, slots=True)
class CreateDocumentCommand:
    """Create a document write command."""

    document_data: DocumentCreate
    current_user: User


@dataclass(frozen=True, slots=True)
class UpdateDocumentCommand:
    """Update a document write command."""

    document_id: int
    document_data: DocumentUpdate
    current_user: User
    if_match: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDocumentCommand:
    """Delete a document write command."""

    document_id: int
    current_user: User


class AssignCompanySetCommandHandler:
    """Converts expected assignment command failures into typed Result errors."""

    def __init__(self, use_case: AssignCompanySet):
        self.use_case = use_case
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[AssignCompanySetCommand, int](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_use_case),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[AssignCompanySetCommand]) -> None:
        _ = context

    def _authorize(self, context: CommandContext[AssignCompanySetCommand]) -> None:
        _ = context

    def _execute_use_case(self, context: CommandContext[AssignCompanySetCommand]) -> int:
        command = context.command
        return self.use_case.assign_company_set(
            command.document_id,
            command.company_ids,
            if_match=command.if_match,
        )

    def _publish(self, context: CommandContext[AssignCompanySetCommand], result: int) -> None:
        _ = (context, result)

    def execute(
        self, command: AssignCompanySetCommand
    ) -> Result[int, AssignCompanySetCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                AssignCompanySetCommandError(
                    code=AssignCompanySetCommandErrorCode.DOCUMENT_NOT_FOUND,
                    message=exc.message,
                )
            )
        except ValidationError as exc:
            return Result.err(
                AssignCompanySetCommandError(
                    code=AssignCompanySetCommandErrorCode.INVALID_COMPANY_SET,
                    message=exc.message,
                    error_code=exc.error_code,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    AssignCompanySetCommandError(
                        code=AssignCompanySetCommandErrorCode.DOCUMENT_NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return Result.err(
                    AssignCompanySetCommandError(
                        code=AssignCompanySetCommandErrorCode.INVALID_COMPANY_SET,
                        message=str(exc.detail),
                        error_code="invalid_company_set",
                    )
                )
            raise


class CreateDocumentCommandHandler:
    """Converts expected create-document command failures into typed Result errors."""

    def __init__(self, service: DocumentService):
        self.service = service
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[CreateDocumentCommand, Document](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_use_case),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[CreateDocumentCommand]) -> None:
        _ = context

    def _authorize(self, context: CommandContext[CreateDocumentCommand]) -> None:
        _ = context

    def _execute_use_case(self, context: CommandContext[CreateDocumentCommand]) -> Document:
        command = context.command
        return self.service.create_document(command.document_data, command.current_user)

    def _publish(self, context: CommandContext[CreateDocumentCommand], result: Document) -> None:
        _ = (context, result)

    def execute(self, command: CreateDocumentCommand) -> Result[Document, DocumentCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                DocumentCommandError(code=DocumentCommandErrorCode.NOT_FOUND, message=exc.message)
            )
        except ValidationError as exc:
            return Result.err(
                DocumentCommandError(
                    code=DocumentCommandErrorCode.VALIDATION,
                    message=exc.message,
                    error_code=exc.error_code,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.VALIDATION,
                        message=str(exc.detail),
                        error_code="validation_error",
                    )
                )
            raise


class UpdateDocumentCommandHandler:
    """Converts expected update-document command failures into typed Result errors."""

    def __init__(self, service: DocumentService):
        self.service = service
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[UpdateDocumentCommand, Document](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_use_case),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[UpdateDocumentCommand]) -> None:
        _ = context

    def _authorize(self, context: CommandContext[UpdateDocumentCommand]) -> None:
        _ = context

    def _execute_use_case(self, context: CommandContext[UpdateDocumentCommand]) -> Document:
        command = context.command
        return self.service.update_document(
            command.document_id,
            command.document_data,
            command.current_user,
            if_match=command.if_match,
        )

    def _publish(self, context: CommandContext[UpdateDocumentCommand], result: Document) -> None:
        _ = (context, result)

    def execute(self, command: UpdateDocumentCommand) -> Result[Document, DocumentCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                DocumentCommandError(code=DocumentCommandErrorCode.NOT_FOUND, message=exc.message)
            )
        except ValidationError as exc:
            return Result.err(
                DocumentCommandError(
                    code=DocumentCommandErrorCode.VALIDATION,
                    message=exc.message,
                    error_code=exc.error_code,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.VALIDATION,
                        message=str(exc.detail),
                        error_code="validation_error",
                    )
                )
            raise


class DeleteDocumentCommandHandler:
    """Converts expected delete-document command failures into typed Result errors."""

    def __init__(self, service: DocumentService):
        self.service = service
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[DeleteDocumentCommand, None](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_use_case),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[DeleteDocumentCommand]) -> None:
        _ = context

    def _authorize(self, context: CommandContext[DeleteDocumentCommand]) -> None:
        _ = context

    def _execute_use_case(self, context: CommandContext[DeleteDocumentCommand]) -> None:
        command = context.command
        self.service.delete_document(command.document_id, command.current_user)

    def _publish(self, context: CommandContext[DeleteDocumentCommand], result: None) -> None:
        _ = (context, result)

    def execute(self, command: DeleteDocumentCommand) -> Result[None, DocumentCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                DocumentCommandError(code=DocumentCommandErrorCode.NOT_FOUND, message=exc.message)
            )
        except ValidationError as exc:
            return Result.err(
                DocumentCommandError(
                    code=DocumentCommandErrorCode.VALIDATION,
                    message=exc.message,
                    error_code=exc.error_code,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return Result.err(
                    DocumentCommandError(
                        code=DocumentCommandErrorCode.VALIDATION,
                        message=str(exc.detail),
                        error_code="validation_error",
                    )
                )
            raise
