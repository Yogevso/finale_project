"""Reusable command handler pipeline primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Protocol, TypeVar

CommandT = TypeVar("CommandT")
ResultT = TypeVar("ResultT")


@dataclass(slots=True)
class CommandContext(Generic[CommandT]):
    """Mutable execution context shared across pipeline stages."""

    command: CommandT
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CommandExecutionTrace:
    """Execution trace for a command pipeline run."""

    command_name: str
    stage_order: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandPipelineRun(Generic[ResultT]):
    """Pipeline run output including result value and stage trace."""

    value: ResultT
    trace: CommandExecutionTrace


class CommandValidator(Protocol[CommandT]):
    """Validate a command before authorization/execution."""

    def validate(self, context: CommandContext[CommandT]) -> None: ...


class CommandAuthorizer(Protocol[CommandT]):
    """Authorize a command before execution."""

    def authorize(self, context: CommandContext[CommandT]) -> None: ...


class CommandExecutor(Protocol[CommandT, ResultT]):
    """Execute command domain/application behavior."""

    def execute(self, context: CommandContext[CommandT]) -> ResultT: ...


class CommandPublisher(Protocol[CommandT, ResultT]):
    """Publish side effects/events after successful execution."""

    def publish(self, context: CommandContext[CommandT], result: ResultT) -> None: ...


class NoOpCommandValidator(Generic[CommandT]):
    """Default no-op command validator."""

    def validate(self, context: CommandContext[CommandT]) -> None:
        _ = context


class NoOpCommandAuthorizer(Generic[CommandT]):
    """Default no-op command authorizer."""

    def authorize(self, context: CommandContext[CommandT]) -> None:
        _ = context


class NoOpCommandPublisher(Generic[CommandT, ResultT]):
    """Default no-op command publisher."""

    def publish(self, context: CommandContext[CommandT], result: ResultT) -> None:
        _ = (context, result)


class FunctionCommandValidator(Generic[CommandT]):
    """Adapter turning a callable into a validator stage."""

    def __init__(self, validator: Callable[[CommandContext[CommandT]], None]):
        self._validator = validator

    def validate(self, context: CommandContext[CommandT]) -> None:
        self._validator(context)


class FunctionCommandAuthorizer(Generic[CommandT]):
    """Adapter turning a callable into an authorizer stage."""

    def __init__(self, authorizer: Callable[[CommandContext[CommandT]], None]):
        self._authorizer = authorizer

    def authorize(self, context: CommandContext[CommandT]) -> None:
        self._authorizer(context)


class FunctionCommandExecutor(Generic[CommandT, ResultT]):
    """Adapter turning a callable into an executor stage."""

    def __init__(self, executor: Callable[[CommandContext[CommandT]], ResultT]):
        self._executor = executor

    def execute(self, context: CommandContext[CommandT]) -> ResultT:
        return self._executor(context)


class FunctionCommandPublisher(Generic[CommandT, ResultT]):
    """Adapter turning a callable into a publisher stage."""

    def __init__(self, publisher: Callable[[CommandContext[CommandT], ResultT], None]):
        self._publisher = publisher

    def publish(self, context: CommandContext[CommandT], result: ResultT) -> None:
        self._publisher(context, result)


class CommandPipeline(Generic[CommandT, ResultT]):
    """Runs command stages in a consistent validate/authorize/execute/publish flow."""

    def __init__(
        self,
        *,
        executor: CommandExecutor[CommandT, ResultT],
        validator: CommandValidator[CommandT] | None = None,
        authorizer: CommandAuthorizer[CommandT] | None = None,
        publisher: CommandPublisher[CommandT, ResultT] | None = None,
    ) -> None:
        self._validator = validator or NoOpCommandValidator()
        self._authorizer = authorizer or NoOpCommandAuthorizer()
        self._executor = executor
        self._publisher = publisher or NoOpCommandPublisher()

    def run(self, command: CommandT) -> CommandPipelineRun[ResultT]:
        context = CommandContext(command=command)
        stage_order: list[str] = []

        self._validator.validate(context)
        stage_order.append("validate")

        self._authorizer.authorize(context)
        stage_order.append("authorize")

        value = self._executor.execute(context)
        stage_order.append("execute")

        self._publisher.publish(context, value)
        stage_order.append("publish")

        return CommandPipelineRun(
            value=value,
            trace=CommandExecutionTrace(
                command_name=type(command).__name__,
                stage_order=tuple(stage_order),
            ),
        )
