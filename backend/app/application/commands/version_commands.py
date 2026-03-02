"""Application commands for version workflow operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, status

from app.application.dto import ActorContext
from app.application.interfaces.use_cases import PublishApprovedVersion
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
from app.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models import User


class PublishApprovedVersionCommandErrorCode(str, Enum):
    """Expected publish command failure categories."""

    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_STATE = "invalid_state"
    CONFLICT = "conflict"
    VALIDATION = "validation"


@dataclass(frozen=True, slots=True)
class PublishApprovedVersionCommandError:
    """Typed publish command error payload."""

    code: PublishApprovedVersionCommandErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class PublishApprovedVersionCommand:
    """Publish a reviewed version for a document."""

    document_id: int
    version_id: int
    current_user: ActorContext | User

    def __post_init__(self) -> None:
        if isinstance(self.current_user, ActorContext):
            return
        object.__setattr__(self, "current_user", ActorContext.from_user(self.current_user))


class PublishApprovedVersionCommandHandler:
    """Converts expected publish command failures into typed Result errors."""

    def __init__(self, use_case: PublishApprovedVersion):
        self.use_case = use_case
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[PublishApprovedVersionCommand, dict](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_use_case),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[PublishApprovedVersionCommand]) -> None:
        _ = context

    def _authorize(self, context: CommandContext[PublishApprovedVersionCommand]) -> None:
        _ = context

    def _execute_use_case(self, context: CommandContext[PublishApprovedVersionCommand]) -> dict:
        command = context.command
        return self.use_case.publish_approved_version(
            command.document_id,
            command.version_id,
            command.current_user,
        )

    def _publish(self, context: CommandContext[PublishApprovedVersionCommand], result: dict) -> None:
        _ = (context, result)

    def execute(
        self, command: PublishApprovedVersionCommand
    ) -> Result[dict, PublishApprovedVersionCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                PublishApprovedVersionCommandError(
                    code=PublishApprovedVersionCommandErrorCode.NOT_FOUND,
                    message=exc.message,
                )
            )
        except PermissionDeniedError as exc:
            return Result.err(
                PublishApprovedVersionCommandError(
                    code=PublishApprovedVersionCommandErrorCode.PERMISSION_DENIED,
                    message=exc.message,
                )
            )
        except InvalidStateError as exc:
            return Result.err(
                PublishApprovedVersionCommandError(
                    code=PublishApprovedVersionCommandErrorCode.INVALID_STATE,
                    message=exc.message,
                )
            )
        except ConflictError as exc:
            return Result.err(
                PublishApprovedVersionCommandError(
                    code=PublishApprovedVersionCommandErrorCode.CONFLICT,
                    message=exc.message,
                )
            )
        except ValidationError as exc:
            return Result.err(
                PublishApprovedVersionCommandError(
                    code=PublishApprovedVersionCommandErrorCode.VALIDATION,
                    message=exc.message,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    PublishApprovedVersionCommandError(
                        code=PublishApprovedVersionCommandErrorCode.NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                return Result.err(
                    PublishApprovedVersionCommandError(
                        code=PublishApprovedVersionCommandErrorCode.PERMISSION_DENIED,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return Result.err(
                    PublishApprovedVersionCommandError(
                        code=PublishApprovedVersionCommandErrorCode.INVALID_STATE,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_409_CONFLICT:
                return Result.err(
                    PublishApprovedVersionCommandError(
                        code=PublishApprovedVersionCommandErrorCode.CONFLICT,
                        message=str(exc.detail),
                    )
                )
            raise
