"""Tests for use-case telemetry instrumentation across command/query paths."""

from dataclasses import dataclass

import pytest

from app.application.bus import AuthorizationMiddleware, CommandBus, QueryBus, TracingMiddleware
from app.application.pipeline import (
    CommandPipeline,
    FunctionCommandExecutor,
)
from app.observability import get_use_case_telemetry_sink, reset_use_case_telemetry_sink


@dataclass(frozen=True, slots=True)
class _TelemetryCommand:
    value: int


@dataclass(frozen=True, slots=True)
class _TelemetryQuery:
    value: int


def test_command_pipeline_emits_success_telemetry():
    reset_use_case_telemetry_sink()
    sink = get_use_case_telemetry_sink()
    pipeline = CommandPipeline[_TelemetryCommand, int](
        executor=FunctionCommandExecutor(lambda context: context.command.value + 1),
        telemetry_sink=sink,
    )

    run = pipeline.run(_TelemetryCommand(value=4))

    assert run.value == 5
    assert run.trace.metadata["outcome"] == "success"
    assert run.trace.metadata["use_case_id"] == "command.telemetrycommand"
    events = sink.snapshot()
    assert len(events) == 1
    assert events[0].use_case_id == "command.telemetrycommand"
    assert events[0].outcome == "success"
    assert events[0].duration_ms >= 0.0


def test_command_pipeline_emits_failure_telemetry():
    reset_use_case_telemetry_sink()
    sink = get_use_case_telemetry_sink()

    def _explode(_context):
        raise RuntimeError("boom")

    pipeline = CommandPipeline[_TelemetryCommand, int](
        executor=FunctionCommandExecutor(_explode),
        telemetry_sink=sink,
    )

    with pytest.raises(RuntimeError, match="boom"):
        pipeline.run(_TelemetryCommand(value=1))

    events = sink.snapshot()
    assert len(events) == 1
    event = events[0]
    assert event.use_case_id == "command.telemetrycommand"
    assert event.outcome == "failure"
    assert event.dimensions["error_type"] == "RuntimeError"


def test_command_and_query_bus_emit_use_case_telemetry():
    reset_use_case_telemetry_sink()
    sink = get_use_case_telemetry_sink()

    command_bus = CommandBus(
        middlewares=[AuthorizationMiddleware(), TracingMiddleware()],
        telemetry_sink=sink,
    )
    query_bus = QueryBus(
        middlewares=[AuthorizationMiddleware(), TracingMiddleware()],
        telemetry_sink=sink,
    )
    command_bus.register(_TelemetryCommand, lambda command: command.value * 2)
    query_bus.register(_TelemetryQuery, lambda query: {"value": query.value})

    assert command_bus.dispatch(_TelemetryCommand(value=3)) == 6
    assert query_bus.dispatch(_TelemetryQuery(value=9)) == {"value": 9}

    events = sink.snapshot()
    assert len(events) == 2
    assert events[0].use_case_id == "command.telemetrycommand"
    assert events[1].use_case_id == "query.telemetryquery"
    assert all(event.outcome == "success" for event in events)

