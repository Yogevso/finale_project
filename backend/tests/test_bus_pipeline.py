"""Tests for command/query bus middleware pipelines."""

from dataclasses import dataclass

import pytest

from app.application.bus import (
    AuthorizationMiddleware,
    CommandBus,
    CommandBusHandlerAdapter,
    QueryBus,
    QueryBusHandlerAdapter,
    TracingMiddleware,
    ValidationMiddleware,
)
from app.errors import PermissionDeniedError


@dataclass(frozen=True, slots=True)
class DummyCommand:
    value: int


@dataclass(frozen=True, slots=True)
class DummyQuery:
    value: int


def test_command_bus_runs_middleware_chain_and_records_trace():
    bus = CommandBus(
        middlewares=[ValidationMiddleware(), AuthorizationMiddleware(), TracingMiddleware()]
    )
    bus.register(DummyCommand, lambda command: command.value * 2)

    result = bus.dispatch(DummyCommand(value=3))

    assert result == 6
    assert bus.last_trace is not None
    assert bus.last_trace.bus_name == "command_bus"
    assert bus.last_trace.request_name == "DummyCommand"
    assert bus.last_trace.middleware_order == ("validate", "authorize", "trace")
    assert "duration_ms" in bus.last_trace.metadata
    assert "started_at" in bus.last_trace.metadata


def test_authorization_middleware_blocks_inactive_current_user():
    @dataclass(frozen=True, slots=True)
    class InactiveUser:
        is_active: bool = False

    @dataclass(frozen=True, slots=True)
    class CommandWithActor:
        current_user: InactiveUser

    bus = CommandBus(
        middlewares=[ValidationMiddleware(), AuthorizationMiddleware(), TracingMiddleware()]
    )
    bus.register(CommandWithActor, lambda _command: "should-not-run")

    with pytest.raises(PermissionDeniedError, match="Inactive users"):
        bus.dispatch(CommandWithActor(current_user=InactiveUser()))


def test_query_bus_adapter_executes_registered_query_and_exposes_trace():
    bus = QueryBus(
        middlewares=[ValidationMiddleware(), AuthorizationMiddleware(), TracingMiddleware()]
    )
    bus.register(DummyQuery, lambda query: {"value": query.value})
    adapter = QueryBusHandlerAdapter[DummyQuery, dict](bus)

    payload = adapter.execute(DummyQuery(value=9))

    assert payload == {"value": 9}
    assert adapter.last_trace is not None
    assert adapter.last_trace.bus_name == "query_bus"
    assert adapter.last_trace.request_name == "DummyQuery"
    assert adapter.last_trace.middleware_order == ("validate", "authorize", "trace")


def test_command_bus_handler_adapter_dispatches_registered_command():
    bus = CommandBus(
        middlewares=[ValidationMiddleware(), AuthorizationMiddleware(), TracingMiddleware()]
    )
    bus.register(DummyCommand, lambda command: command.value + 1)
    adapter = CommandBusHandlerAdapter[DummyCommand, int](bus)

    assert adapter.execute(DummyCommand(value=10)) == 11
    assert adapter.last_trace is not None
    assert adapter.last_trace.request_name == "DummyCommand"
