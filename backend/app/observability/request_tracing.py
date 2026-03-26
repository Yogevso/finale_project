"""Request tracing helpers shared across HTTP and service boundaries."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
_TRACE_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)


@dataclass(frozen=True)
class RequestTracingContext:
    trace_id: str
    request_id: str


def generate_request_id() -> str:
    return uuid.uuid4().hex[:16]


def generate_trace_id() -> str:
    return uuid.uuid4().hex


def normalize_trace_value(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if not _TRACE_VALUE_RE.fullmatch(candidate):
        return None
    return candidate


def resolve_request_tracing(
    *,
    incoming_trace_id: str | None = None,
    incoming_request_id: str | None = None,
) -> RequestTracingContext:
    trace_id = (
        normalize_trace_value(incoming_trace_id)
        or normalize_trace_value(incoming_request_id)
        or generate_trace_id()
    )
    return RequestTracingContext(
        trace_id=trace_id,
        request_id=generate_request_id(),
    )

