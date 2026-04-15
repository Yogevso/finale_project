"""Run backend performance regression gates and enforce budget thresholds."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

TEST_TARGETS = [
    "tests/scenarios/audience_benchmarks.py",
    "tests/scenarios/assistant_benchmarks.py",
    "tests/scenarios/conversion_benchmarks.py",
    "tests/test_write_contention.py",
]

PROPERTY_THRESHOLDS = {
    "audience_benchmark_metrics_json": {
        "assignment_list.p95_ms": 500.0,
        "document_detail_with_companies.p95_ms": 500.0,
        "search_with_audience_filter.p95_ms": 1_200.0,
    },
    "assistant_benchmark_metrics_json": {
        "assistant_chat_sse.p95_ms": 500.0,
    },
    "conversion_benchmark_metrics_json": {
        "docx_reader_artifact.p95_ms": 1_500.0,
        "pdf_export.p95_ms": 1_500.0,
        "pdf_to_reader_artifact.p95_ms": 2_500.0,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run backend perf-gate scenarios and enforce thresholds."
    )
    parser.add_argument(
        "--junit-file",
        type=Path,
        default=None,
        help="Optional path to write the raw pytest JUnit XML report.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help="Optional path to write the summarized perf-gate JSON report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    temp_root = BACKEND_DIR / ".tmp" / "perf-gate"
    junit_file = args.junit_file.resolve() if args.junit_file else temp_root / "backend-perf-gate.xml"
    report_file = args.report_file.resolve() if args.report_file else temp_root / "backend-perf-gate.json"

    junit_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    run_pytest(junit_file)
    report = evaluate_report(junit_file)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report, report_file)

    if report["passed"]:
        return 0
    return 1


def run_pytest(junit_file: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "pytest",
        *TEST_TARGETS,
        "-q",
        f"--junitxml={junit_file}",
    ]
    result = subprocess.run(command, cwd=BACKEND_DIR, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def evaluate_report(junit_file: Path) -> dict[str, Any]:
    tree = ET.parse(junit_file)
    properties = extract_properties(tree.getroot())
    failures: list[str] = []
    metrics: dict[str, Any] = {}

    for property_name, thresholds in PROPERTY_THRESHOLDS.items():
        raw_value = properties.get(property_name)
        if raw_value is None:
            failures.append(f"Missing benchmark property: {property_name}")
            continue

        payload = json.loads(raw_value)
        metrics[property_name] = payload
        for path, budget in thresholds.items():
            actual = float(resolve_metric(payload, path))
            if actual > budget:
                failures.append(
                    f"{property_name}:{path} {actual:.2f}ms exceeded budget {budget:.2f}ms"
                )

    return {
        "passed": not failures,
        "benchmarks": metrics,
        "thresholds": PROPERTY_THRESHOLDS,
        "failures": failures,
    }


def extract_properties(root: ET.Element) -> dict[str, str]:
    properties: dict[str, str] = {}
    for testcase in root.findall(".//testcase"):
        for prop in testcase.findall("./properties/property"):
            name = prop.attrib.get("name")
            value = prop.attrib.get("value")
            if name and value is not None:
                properties[name] = value
    return properties


def resolve_metric(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        current = current[segment]
    return current


def print_report(report: dict[str, Any], report_file: Path) -> None:
    print("Backend performance gate summary:")
    print(f"- report_file: {report_file}")
    for benchmark_name, payload in report["benchmarks"].items():
        print(f"- {benchmark_name}:")
        print(json.dumps(payload, indent=2))
    if report["failures"]:
        print("Performance gate failed:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    else:
        print("Performance gate passed.")


if __name__ == "__main__":
    raise SystemExit(main())
