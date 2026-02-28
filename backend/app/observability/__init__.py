"""Use-case observability primitives (telemetry, SLO, burn-rate alerts)."""

from app.observability.burn_rate import (
    BurnRateAlert,
    BurnRateAlertStatus,
    BurnRateThreshold,
    evaluate_burn_rate_alerts,
    evaluate_burn_rate_alerts_for_slos,
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
    "UseCaseKind",
    "UseCaseOutcome",
    "UseCaseSLODefinition",
    "UseCaseSLOEvaluation",
    "UseCaseTelemetryEvent",
    "UseCaseTelemetrySink",
    "UseCaseTimer",
    "build_use_case_id",
    "evaluate_burn_rate_alerts",
    "evaluate_burn_rate_alerts_for_slos",
    "evaluate_use_case_slo",
    "evaluate_use_case_slos",
    "get_use_case_telemetry_sink",
    "record_use_case_telemetry",
    "reset_use_case_telemetry_sink",
]
