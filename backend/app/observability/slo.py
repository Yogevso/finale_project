"""Use-case SLO definitions and compliance evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import quantiles

from app.observability.telemetry import UseCaseTelemetryEvent


@dataclass(frozen=True, slots=True)
class UseCaseSLODefinition:
    """SLO targets for one use-case telemetry identifier."""

    use_case_id: str
    window_minutes: int
    target_success_ratio: float
    target_p95_latency_ms: float
    owner: str


@dataclass(frozen=True, slots=True)
class UseCaseSLOEvaluation:
    """One use-case SLO evaluation result."""

    use_case_id: str
    sample_count: int
    success_ratio: float
    p95_latency_ms: float
    target_success_ratio: float
    target_p95_latency_ms: float
    success_ratio_compliant: bool
    latency_compliant: bool
    overall_compliant: bool


def _parse_started_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc) - timedelta(days=3650)


def _calculate_p95_latency_ms(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    # Inclusive method for stable percentile with small sample sizes.
    return float(quantiles(values, n=100, method="inclusive")[94])


def evaluate_use_case_slo(
    *,
    definition: UseCaseSLODefinition,
    events: list[UseCaseTelemetryEvent],
    now: datetime | None = None,
) -> UseCaseSLOEvaluation:
    """Evaluate one SLO definition against telemetry events within its lookback window."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(minutes=max(1, int(definition.window_minutes)))

    scoped = [
        event
        for event in events
        if event.use_case_id == definition.use_case_id
        and _parse_started_at(event.started_at) >= cutoff
    ]

    sample_count = len(scoped)
    success_count = sum(1 for event in scoped if event.outcome == "success")
    success_ratio = (success_count / sample_count) if sample_count else 1.0
    p95_latency_ms = _calculate_p95_latency_ms([event.duration_ms for event in scoped])

    success_ratio_compliant = success_ratio >= definition.target_success_ratio
    latency_compliant = p95_latency_ms <= definition.target_p95_latency_ms

    return UseCaseSLOEvaluation(
        use_case_id=definition.use_case_id,
        sample_count=sample_count,
        success_ratio=round(success_ratio, 6),
        p95_latency_ms=round(p95_latency_ms, 3),
        target_success_ratio=definition.target_success_ratio,
        target_p95_latency_ms=definition.target_p95_latency_ms,
        success_ratio_compliant=success_ratio_compliant,
        latency_compliant=latency_compliant,
        overall_compliant=success_ratio_compliant and latency_compliant,
    )


def evaluate_use_case_slos(
    *,
    definitions: list[UseCaseSLODefinition],
    events: list[UseCaseTelemetryEvent],
    now: datetime | None = None,
) -> list[UseCaseSLOEvaluation]:
    """Evaluate all configured use-case SLO definitions."""
    return [
        evaluate_use_case_slo(definition=definition, events=events, now=now)
        for definition in definitions
    ]
