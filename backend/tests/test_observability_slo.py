"""Tests for use-case SLO and burn-rate alert evaluation."""

from datetime import datetime, timedelta, timezone

from app.observability import (
    BurnRateThreshold,
    UseCaseSLODefinition,
    UseCaseTelemetryEvent,
    evaluate_burn_rate_alerts,
    evaluate_burn_rate_alerts_for_slos,
    evaluate_use_case_slo,
    evaluate_use_case_slos,
)


def _event(
    *,
    use_case_id: str,
    outcome: str,
    duration_ms: float,
    minutes_ago: int,
) -> UseCaseTelemetryEvent:
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return UseCaseTelemetryEvent(
        use_case_id=use_case_id,
        use_case_kind="command",
        outcome=outcome,  # type: ignore[arg-type]
        duration_ms=duration_ms,
        started_at=timestamp.isoformat(),
        dimensions={},
    )


def test_evaluate_use_case_slo_reports_compliance():
    definition = UseCaseSLODefinition(
        use_case_id="command.create_document_command",
        window_minutes=60,
        target_success_ratio=0.99,
        target_p95_latency_ms=250.0,
        owner="platform",
    )
    events = [
        _event(
            use_case_id="command.create_document_command",
            outcome="success",
            duration_ms=120,
            minutes_ago=2,
        ),
        _event(
            use_case_id="command.create_document_command",
            outcome="success",
            duration_ms=150,
            minutes_ago=5,
        ),
        _event(
            use_case_id="command.create_document_command",
            outcome="success",
            duration_ms=180,
            minutes_ago=8,
        ),
    ]

    evaluation = evaluate_use_case_slo(definition=definition, events=events)

    assert evaluation.sample_count == 3
    assert evaluation.success_ratio == 1.0
    assert evaluation.p95_latency_ms <= 250.0
    assert evaluation.overall_compliant is True


def test_evaluate_use_case_slos_and_burn_rate_alerts_detects_critical_state():
    definitions = [
        UseCaseSLODefinition(
            use_case_id="query.analytics_overview_query",
            window_minutes=60,
            target_success_ratio=0.995,
            target_p95_latency_ms=400.0,
            owner="analytics",
        )
    ]
    events = [
        _event(
            use_case_id="query.analytics_overview_query",
            outcome="failure",
            duration_ms=520,
            minutes_ago=3,
        ),
        _event(
            use_case_id="query.analytics_overview_query",
            outcome="failure",
            duration_ms=500,
            minutes_ago=6,
        ),
        _event(
            use_case_id="query.analytics_overview_query",
            outcome="success",
            duration_ms=380,
            minutes_ago=9,
        ),
    ]

    evaluations = evaluate_use_case_slos(definitions=definitions, events=events)
    alerts = evaluate_burn_rate_alerts(
        evaluations=evaluations,
        thresholds=[
            BurnRateThreshold(window_minutes=5, warning_threshold=2.0, critical_threshold=10.0)
        ],
    )

    assert len(evaluations) == 1
    assert evaluations[0].overall_compliant is False
    assert len(alerts) == 1
    assert alerts[0].status == "critical"
    assert alerts[0].burn_rate > 10.0


def test_burn_rate_window_thresholds_use_threshold_specific_lookback():
    definition = UseCaseSLODefinition(
        use_case_id="command.publish_approved_version_command",
        window_minutes=60,
        target_success_ratio=0.99,
        target_p95_latency_ms=300.0,
        owner="docs-platform",
    )
    events = [
        _event(
            use_case_id="command.publish_approved_version_command",
            outcome="failure",
            duration_ms=450,
            minutes_ago=45,
        ),
        _event(
            use_case_id="command.publish_approved_version_command",
            outcome="success",
            duration_ms=180,
            minutes_ago=2,
        ),
        _event(
            use_case_id="command.publish_approved_version_command",
            outcome="success",
            duration_ms=200,
            minutes_ago=1,
        ),
    ]

    alerts = evaluate_burn_rate_alerts_for_slos(
        definitions=[definition],
        events=events,
        thresholds=[
            BurnRateThreshold(window_minutes=5, warning_threshold=1.0, critical_threshold=2.0),
            BurnRateThreshold(window_minutes=60, warning_threshold=1.0, critical_threshold=2.0),
        ],
    )

    by_window = {alert.window_minutes: alert for alert in alerts}
    assert by_window[5].status == "ok"
    assert by_window[60].status == "critical"
