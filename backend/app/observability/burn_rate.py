"""Burn-rate alert evaluation for use-case SLO compliance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.observability.slo import (
    UseCaseSLODefinition,
    UseCaseSLOEvaluation,
    evaluate_use_case_slo,
)
from app.observability.telemetry import UseCaseTelemetryEvent

BurnRateAlertStatus = Literal["ok", "warning", "critical", "no_data"]


@dataclass(frozen=True, slots=True)
class BurnRateThreshold:
    """Burn-rate threshold over one lookback window."""

    window_minutes: int
    warning_threshold: float
    critical_threshold: float


@dataclass(frozen=True, slots=True)
class BurnRateAlert:
    """Burn-rate alert result for one use-case and threshold window."""

    use_case_id: str
    window_minutes: int
    burn_rate: float
    status: BurnRateAlertStatus
    sample_count: int
    message: str


def _allowed_error_rate(target_success_ratio: float) -> float:
    return max(1e-9, 1.0 - max(0.0, min(1.0, target_success_ratio)))


def _build_alert(
    *,
    evaluation: UseCaseSLOEvaluation,
    threshold: BurnRateThreshold,
) -> BurnRateAlert:
    if evaluation.sample_count == 0:
        return BurnRateAlert(
            use_case_id=evaluation.use_case_id,
            window_minutes=threshold.window_minutes,
            burn_rate=0.0,
            status="no_data",
            sample_count=0,
            message="No telemetry samples in lookback window",
        )

    allowed_error_rate = _allowed_error_rate(evaluation.target_success_ratio)
    actual_error_rate = 1.0 - evaluation.success_ratio
    burn_rate = actual_error_rate / allowed_error_rate

    if burn_rate >= threshold.critical_threshold:
        status: BurnRateAlertStatus = "critical"
    elif burn_rate >= threshold.warning_threshold:
        status = "warning"
    else:
        status = "ok"

    return BurnRateAlert(
        use_case_id=evaluation.use_case_id,
        window_minutes=threshold.window_minutes,
        burn_rate=round(burn_rate, 4),
        status=status,
        sample_count=evaluation.sample_count,
        message=(
            f"Burn rate {burn_rate:.4f} for {evaluation.use_case_id} "
            f"(window={threshold.window_minutes}m)"
        ),
    )


def evaluate_burn_rate_alerts(
    *,
    evaluations: list[UseCaseSLOEvaluation],
    thresholds: list[BurnRateThreshold],
) -> list[BurnRateAlert]:
    """Evaluate burn-rate statuses from SLO evaluation snapshots."""
    alerts: list[BurnRateAlert] = []
    for evaluation in evaluations:
        for threshold in thresholds:
            alerts.append(_build_alert(evaluation=evaluation, threshold=threshold))
    return alerts


def evaluate_burn_rate_alerts_for_slos(
    *,
    definitions: list[UseCaseSLODefinition],
    events: list[UseCaseTelemetryEvent],
    thresholds: list[BurnRateThreshold],
    now: datetime | None = None,
) -> list[BurnRateAlert]:
    """Evaluate burn-rate alerts using threshold-specific lookback windows."""

    alerts: list[BurnRateAlert] = []
    for definition in definitions:
        for threshold in thresholds:
            threshold_definition = UseCaseSLODefinition(
                use_case_id=definition.use_case_id,
                window_minutes=threshold.window_minutes,
                target_success_ratio=definition.target_success_ratio,
                target_p95_latency_ms=definition.target_p95_latency_ms,
                owner=definition.owner,
            )
            threshold_evaluation = evaluate_use_case_slo(
                definition=threshold_definition,
                events=events,
                now=now,
            )
            alerts.append(_build_alert(evaluation=threshold_evaluation, threshold=threshold))
    return alerts
