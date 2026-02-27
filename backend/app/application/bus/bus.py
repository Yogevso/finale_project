"""Command/query bus with middleware support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Callable, Generic, Protocol, TypeVar

from app.errors import PermissionDeniedError

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


@dataclass(slots=True)
class BusDispatchContext(Generic[RequestT]):
    """Mutable context shared across bus middleware/handler execution."""

    bus_name: str
    request: RequestT
    request_name: str
    middleware_order: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BusDispatchTrace:
    """Trace payload for one bus dispatch execution."""

    bus_name: str
    request_name: str
    middleware_order: tuple[str, ...]
    metadata: dict[str, Any]


class BusMiddleware(Protocol):
    """Bus middleware contract."""

    name: str

    def handle(
        self,
        context: BusDispatchContext[Any],
        next_handler: Callable[[BusDispatchContext[Any]], Any],
    ) -> Any: ...


class ValidationMiddleware:
    """Execute optional request-level validation hooks."""

    name = "validate"

    def handle(
        self,
        context: BusDispatchContext[Any],
        next_handler: Callable[[BusDispatchContext[Any]], Any],
    ) -> Any:
        request = context.request
        if request is None:
            raise ValueError("Bus request cannot be None")
        validate = getattr(request, "validate", None)
        if callable(validate):
            validate()
        context.middleware_order.append(self.name)
        return next_handler(context)


class AuthorizationMiddleware:
    """Enforce common actor authorization preconditions."""

    name = "authorize"

    def handle(
        self,
        context: BusDispatchContext[Any],
        next_handler: Callable[[BusDispatchContext[Any]], Any],
    ) -> Any:
        request = context.request
        current_user = getattr(request, "current_user", None)
        if current_user is not None and hasattr(current_user, "is_active"):
            if not bool(current_user.is_active):
                raise PermissionDeniedError("Inactive users cannot execute this request")
        context.middleware_order.append(self.name)
        return next_handler(context)


class TracingMiddleware:
    """Attach timing metadata to dispatch context."""

    name = "trace"

    def handle(
        self,
        context: BusDispatchContext[Any],
        next_handler: Callable[[BusDispatchContext[Any]], Any],
    ) -> Any:
        started_at = datetime.utcnow()
        start = perf_counter()
        context.middleware_order.append(self.name)
        try:
            return next_handler(context)
        finally:
            context.metadata["started_at"] = started_at.isoformat()
            context.metadata["duration_ms"] = round((perf_counter() - start) * 1000, 3)


class _BaseBus:
    """Shared bus dispatch behavior."""

    def __init__(self, name: str, middlewares: list[BusMiddleware]):
        self.name = name
        self._middlewares = list(middlewares)
        self._handlers: dict[type[Any], Callable[[Any], Any]] = {}
        self._last_trace: BusDispatchTrace | None = None

    @property
    def last_trace(self) -> BusDispatchTrace | None:
        return self._last_trace

    def register(self, request_type: type[Any], handler: Callable[[Any], Any]) -> None:
        self._handlers[request_type] = handler

    def _resolve_handler(self, request: Any) -> Callable[[Any], Any]:
        handler = self._handlers.get(type(request))
        if handler is None:
            raise KeyError(f"No handler registered for {type(request).__name__}")
        return handler

    def _record_trace(self, context: BusDispatchContext[Any]) -> None:
        self._last_trace = BusDispatchTrace(
            bus_name=context.bus_name,
            request_name=context.request_name,
            middleware_order=tuple(context.middleware_order),
            metadata=dict(context.metadata),
        )

    def dispatch(self, request: Any) -> Any:
        handler = self._resolve_handler(request)
        context = BusDispatchContext(
            bus_name=self.name,
            request=request,
            request_name=type(request).__name__,
        )

        def invoke(index: int, ctx: BusDispatchContext[Any]) -> Any:
            if index >= len(self._middlewares):
                return handler(ctx.request)
            middleware = self._middlewares[index]
            return middleware.handle(ctx, lambda next_ctx: invoke(index + 1, next_ctx))

        result = invoke(0, context)
        self._record_trace(context)
        return result


class CommandBus(_BaseBus):
    """Bus for command dispatch."""

    def __init__(self, middlewares: list[BusMiddleware]):
        super().__init__(name="command_bus", middlewares=middlewares)


class QueryBus(_BaseBus):
    """Bus for query dispatch."""

    def __init__(self, middlewares: list[BusMiddleware]):
        super().__init__(name="query_bus", middlewares=middlewares)


CommandRequestT = TypeVar("CommandRequestT")
CommandResponseT = TypeVar("CommandResponseT")
QueryRequestT = TypeVar("QueryRequestT")
QueryResponseT = TypeVar("QueryResponseT")


class CommandBusHandlerAdapter(Generic[CommandRequestT, CommandResponseT]):
    """Adapter exposing a handler-like execute API on top of CommandBus."""

    def __init__(self, bus: CommandBus):
        self.bus = bus

    @property
    def last_trace(self) -> BusDispatchTrace | None:
        return self.bus.last_trace

    def execute(self, command: CommandRequestT) -> CommandResponseT:
        return self.bus.dispatch(command)


class QueryBusHandlerAdapter(Generic[QueryRequestT, QueryResponseT]):
    """Adapter exposing a handler-like execute API on top of QueryBus."""

    def __init__(self, bus: QueryBus):
        self.bus = bus

    @property
    def last_trace(self) -> BusDispatchTrace | None:
        return self.bus.last_trace

    def __getattr__(self, name: str) -> Any:
        """Support legacy query-handler method names (e.g., execute_overview)."""
        if name.startswith("execute_"):
            return self.execute
        raise AttributeError(f"{self.__class__.__name__!s} has no attribute {name!r}")

    def execute(self, query: QueryRequestT) -> QueryResponseT:
        return self.bus.dispatch(query)
