#!/usr/bin/env python3
"""Run adapter-boundary chaos suites and enforce recovery-duration thresholds."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CommandScenario:
    """Executable chaos scenario command with timing thresholds."""

    name: str
    command: tuple[str, ...]
    max_duration_seconds: float
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class CommandScenarioResult:
    """Execution result for one chaos command scenario."""

    name: str
    command: str
    exit_code: int | None
    duration_seconds: float
    max_duration_seconds: float
    timed_out: bool
    passed: bool
    failure_reason: str | None
    stdout_tail: str
    stderr_tail: str


def _parse_args() -> argparse.Namespace:
    default_repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Execute adapter-boundary chaos suites and generate a machine-readable report."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root,
        help="Repository root used as working directory for scenario commands.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=default_repo_root / "docs/chaos/evidence/latest-adapter-chaos-report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--skip-backend",
        action="store_true",
        help="Skip backend adapter-chaos scenarios.",
    )
    parser.add_argument(
        "--skip-collab",
        action="store_true",
        help="Skip collab-server adapter-chaos scenarios.",
    )
    parser.add_argument(
        "--backend-max-seconds",
        type=float,
        default=180.0,
        help="Maximum acceptable runtime for backend chaos command.",
    )
    parser.add_argument(
        "--collab-max-seconds",
        type=float,
        default=180.0,
        help="Maximum acceptable runtime for collab-server chaos command.",
    )
    parser.add_argument(
        "--output-tail-chars",
        type=int,
        default=1600,
        help="Number of trailing stdout/stderr characters retained per scenario.",
    )
    return parser.parse_args()


def _tail(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _run_scenario(
    scenario: CommandScenario,
    *,
    repo_root: Path,
    output_tail_chars: int,
) -> CommandScenarioResult:
    started = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    failure_reason: str | None = None

    try:
        completed = subprocess.run(
            list(scenario.command),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=scenario.timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        failure_reason = (
            f"Timed out after {scenario.timeout_seconds}s while running {scenario.name}"
        )
    except Exception as exc:
        failure_reason = f"Failed to execute scenario: {exc}"

    duration_seconds = round(time.monotonic() - started, 3)
    threshold_breached = duration_seconds > scenario.max_duration_seconds
    command_failed = exit_code not in {0, None}

    if not failure_reason and command_failed:
        failure_reason = f"Command exited with code {exit_code}"
    if not failure_reason and threshold_breached:
        failure_reason = (
            f"Duration {duration_seconds}s exceeded threshold "
            f"{scenario.max_duration_seconds:.3f}s"
        )

    passed = (not timed_out) and (not command_failed) and (not threshold_breached) and not failure_reason

    return CommandScenarioResult(
        name=scenario.name,
        command=shlex.join(scenario.command),
        exit_code=exit_code,
        duration_seconds=duration_seconds,
        max_duration_seconds=scenario.max_duration_seconds,
        timed_out=timed_out,
        passed=passed,
        failure_reason=failure_reason,
        stdout_tail=_tail(stdout, max_chars=output_tail_chars),
        stderr_tail=_tail(stderr, max_chars=output_tail_chars),
    )


def _build_scenarios(args: argparse.Namespace) -> list[CommandScenario]:
    scenarios: list[CommandScenario] = []
    npm_executable = "npm.cmd" if os.name == "nt" else "npm"

    if not args.skip_backend:
        scenarios.append(
            CommandScenario(
                name="backend_adapter_boundary_fault_injection",
                command=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "backend/tests/test_adapter_resilience.py",
                    "backend/tests/test_collaboration_managers.py",
                    "-q",
                ),
                max_duration_seconds=float(args.backend_max_seconds),
                timeout_seconds=max(int(args.backend_max_seconds * 2), 120),
            )
        )

    if not args.skip_collab:
        scenarios.append(
            CommandScenario(
                name="collab_adapter_boundary_fault_injection",
                command=(
                    npm_executable,
                    "--prefix",
                    "collab-server",
                    "run",
                    "test",
                    "--",
                    "--runInBand",
                    "src/__tests__/persistence.test.ts",
                    "src/__tests__/documentStateContractAdapter.test.ts",
                ),
                max_duration_seconds=float(args.collab_max_seconds),
                timeout_seconds=max(int(args.collab_max_seconds * 2), 180),
            )
        )

    return scenarios


def _write_report(
    *,
    report_file: Path,
    results: Sequence[CommandScenarioResult],
    total_duration_seconds: float,
) -> None:
    report_file.parent.mkdir(parents=True, exist_ok=True)
    overall_passed = all(result.passed for result in results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if overall_passed else "fail",
        "total_duration_seconds": round(total_duration_seconds, 3),
        "scenario_count": len(results),
        "failed_count": sum(1 for result in results if not result.passed),
        "results": [asdict(result) for result in results],
    }
    report_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()
    scenarios = _build_scenarios(args)
    if not scenarios:
        print("No chaos scenarios selected (both backend and collab were skipped).", file=sys.stderr)
        return 2

    started = time.monotonic()
    results = [
        _run_scenario(
            scenario,
            repo_root=repo_root,
            output_tail_chars=max(200, int(args.output_tail_chars)),
        )
        for scenario in scenarios
    ]
    total_duration = time.monotonic() - started

    _write_report(
        report_file=args.report_file,
        results=results,
        total_duration_seconds=total_duration,
    )

    failed = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.name} in {result.duration_seconds:.3f}s "
            f"(threshold {result.max_duration_seconds:.3f}s)"
        )
        if result.failure_reason:
            print(f"  reason: {result.failure_reason}")

    if failed:
        print(f"Chaos suite failed: {len(failed)} of {len(results)} scenario(s) failed.", file=sys.stderr)
        print(f"Report: {args.report_file}", file=sys.stderr)
        return 1

    print(f"Chaos suite passed ({len(results)} scenarios). Report: {args.report_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

