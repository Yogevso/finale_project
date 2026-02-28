#!/usr/bin/env python3
"""Evaluate use-case SLO compliance and burn-rate alerts from telemetry snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_backend_import_path() -> None:
    backend_dir = _repo_root() / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def _parse_args() -> argparse.Namespace:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Evaluate configured use-case SLOs and burn-rate alerts."
    )
    parser.add_argument(
        "--telemetry-file",
        type=Path,
        default=root / "docs/slo/samples/sample-telemetry.json",
        help="Telemetry JSON file containing a list of use-case telemetry events.",
    )
    parser.add_argument(
        "--slo-file",
        type=Path,
        default=root / "docs/slo/use-case-slos.json",
        help="SLO + burn-rate configuration JSON file.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=root / "docs/slo/evidence/latest-slo-burn-rate-report.json",
        help="Output report path.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero when any critical burn-rate alert is produced.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    # Accept UTF-8 with or without BOM to stay robust across editors/platforms.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_started_at(item: dict[str, Any], *, now: datetime) -> str:
    if item.get("minutes_ago") is not None:
        try:
            minutes_ago = max(0.0, float(item["minutes_ago"]))
        except (TypeError, ValueError):
            minutes_ago = 0.0
        return (now - timedelta(minutes=minutes_ago)).isoformat()
    if item.get("started_at"):
        return str(item["started_at"])
    return now.isoformat()


def main() -> int:
    args = _parse_args()
    _ensure_backend_import_path()

    from app.observability import (  # pylint: disable=import-outside-toplevel
        BurnRateThreshold,
        UseCaseSLODefinition,
        UseCaseTelemetryEvent,
        evaluate_burn_rate_alerts_for_slos,
        evaluate_use_case_slos,
    )

    telemetry_raw = _load_json(args.telemetry_file)
    config_raw = _load_json(args.slo_file)
    current_time = datetime.now(timezone.utc)

    events = [
        UseCaseTelemetryEvent(
            use_case_id=str(item["use_case_id"]),
            use_case_kind=str(item["use_case_kind"]),  # type: ignore[arg-type]
            outcome=str(item["outcome"]),  # type: ignore[arg-type]
            duration_ms=float(item["duration_ms"]),
            started_at=_resolve_started_at(dict(item), now=current_time),
            dimensions={str(k): str(v) for k, v in dict(item.get("dimensions", {})).items()},
        )
        for item in telemetry_raw
    ]
    definitions = [
        UseCaseSLODefinition(
            use_case_id=str(item["use_case_id"]),
            window_minutes=int(item["window_minutes"]),
            target_success_ratio=float(item["target_success_ratio"]),
            target_p95_latency_ms=float(item["target_p95_latency_ms"]),
            owner=str(item["owner"]),
        )
        for item in config_raw["use_case_slos"]
    ]
    thresholds = [
        BurnRateThreshold(
            window_minutes=int(item["window_minutes"]),
            warning_threshold=float(item["warning_threshold"]),
            critical_threshold=float(item["critical_threshold"]),
        )
        for item in config_raw["burn_rate_thresholds"]
    ]

    evaluations = evaluate_use_case_slos(
        definitions=definitions,
        events=events,
        now=current_time,
    )
    alerts = evaluate_burn_rate_alerts_for_slos(
        definitions=definitions,
        events=events,
        thresholds=thresholds,
        now=current_time,
    )

    critical_alerts = [alert for alert in alerts if alert.status == "critical"]
    warning_alerts = [alert for alert in alerts if alert.status == "warning"]
    report_payload = {
        "generated_at": current_time.isoformat(),
        "telemetry_file": str(args.telemetry_file),
        "slo_file": str(args.slo_file),
        "summary": {
            "slo_count": len(definitions),
            "event_count": len(events),
            "critical_alert_count": len(critical_alerts),
            "warning_alert_count": len(warning_alerts),
        },
        "evaluations": [asdict(item) for item in evaluations],
        "alerts": [asdict(item) for item in alerts],
    }

    args.report_file.parent.mkdir(parents=True, exist_ok=True)
    args.report_file.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    print(
        f"SLO evaluation complete: {len(evaluations)} use-cases, "
        f"{len(critical_alerts)} critical alerts, {len(warning_alerts)} warnings."
    )
    print(f"Report: {args.report_file}")

    if args.fail_on_critical and critical_alerts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
