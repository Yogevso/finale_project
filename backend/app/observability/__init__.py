"""Use-case observability primitives (telemetry, SLO, burn-rate alerts)."""

from app.observability.burn_rate import (
    BurnRateAlert,
    BurnRateAlertStatus,
    BurnRateThreshold,
    evaluate_burn_rate_alerts,
    evaluate_burn_rate_alerts_for_slos,
)
from app.observability.request_tracing import (
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    current_request_id,
    current_trace_id,
    generate_request_id,
    generate_trace_id,
    normalize_trace_value,
    resolve_request_tracing,
)
from app.observability.slo import (
    UseCaseSLODefinition,
    UseCaseSLOEvaluation,
    evaluate_use_case_slo,
    evaluate_use_case_slos,
)
from app.observability.telemetry import (
    InMemoryUseCaseTelemetrySink,
    UseCaseKind,
    UseCaseOutcome,
    UseCaseTelemetryEvent,
    UseCaseTelemetrySink,
    UseCaseTimer,
    build_use_case_id,
    get_use_case_telemetry_sink,
    record_use_case_telemetry,
    reset_use_case_telemetry_sink,
)

__all__ = [
    "BurnRateAlert",
    "BurnRateAlertStatus",
    "BurnRateThreshold",
    "InMemoryUseCaseTelemetrySink",
    "REQUEST_ID_HEADER",
    "TRACE_ID_HEADER",
    "UseCaseKind",
    "UseCaseOutcome",
    "UseCaseSLODefinition",
    "UseCaseSLOEvaluation",
    "UseCaseTelemetryEvent",
    "UseCaseTelemetrySink",
    "UseCaseTimer",
    "build_use_case_id",
    "current_request_id",
    "current_trace_id",
    "evaluate_burn_rate_alerts",
    "evaluate_burn_rate_alerts_for_slos",
    "evaluate_use_case_slo",
    "evaluate_use_case_slos",
    "generate_request_id",
    "generate_trace_id",
    "get_use_case_telemetry_sink",
    "normalize_trace_value",
    "record_use_case_telemetry",
    "resolve_request_tracing",
    "reset_use_case_telemetry_sink",
]
