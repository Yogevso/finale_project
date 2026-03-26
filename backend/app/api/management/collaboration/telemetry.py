"""Helpers for collaboration use-case telemetry."""

from __future__ import annotations

from app.observability import UseCaseTimer, record_use_case_telemetry


def record_collaboration_telemetry(
    *,
    use_case_name: str,
    timer: UseCaseTimer,
    outcome: str,
    error_type: str | None = None,
    dimensions: dict[str, str] | None = None,
) -> None:
    payload_dimensions = dict(dimensions or {})
    if error_type:
        payload_dimensions["error_type"] = error_type

    record_use_case_telemetry(
        sink=None,
        use_case_kind="collab",
        use_case_name=use_case_name,
        outcome="failure" if outcome == "failure" else "success",
        duration_ms=timer.duration_ms(),
        started_at=timer.started_at,
        dimensions=payload_dimensions,
    )
