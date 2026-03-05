#!/usr/bin/env python3
"""Generate a monthly audience governance report in Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import SessionLocal  # noqa: E402
from app.models import DocumentVisibility  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402


@dataclass(frozen=True, slots=True)
class ReportingWindow:
    month_label: str
    date_from: date
    date_to: date


def _parse_month(raw_month: str | None) -> date:
    if raw_month is None:
        today = date.today()
        first_of_this_month = today.replace(day=1)
        return first_of_this_month - timedelta(days=1)

    try:
        parsed = datetime.strptime(raw_month, "%Y-%m")
    except ValueError as exc:
        raise ValueError("month must use YYYY-MM format") from exc
    return date(year=parsed.year, month=parsed.month, day=1)


def _build_reporting_window(raw_month: str | None) -> ReportingWindow:
    first_of_month = _parse_month(raw_month)
    month_start = first_of_month.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)
    return ReportingWindow(
        month_label=month_start.strftime("%Y-%m"),
        date_from=month_start,
        date_to=month_end,
    )


def _safe_json_loads(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _build_markdown_report(
    *,
    window: ReportingWindow,
    rows: list[dict[str, Any]],
) -> str:
    visibility_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []

    for row in rows:
        event_type = str(row.get("audience_event_type") or "")
        if row.get("assignment_diff"):
            assignment_rows.append(row)
        if event_type == "visibility_changed":
            visibility_rows.append(row)
            details = _safe_json_loads(row.get("details"))
            from_visibility = str(details.get("from_visibility") or "").lower()
            to_visibility = str(details.get("to_visibility") or "").lower()
            if (
                from_visibility == DocumentVisibility.INTERNAL.value
                and to_visibility == DocumentVisibility.PUBLIC.value
            ):
                exposure_rows.append(row)

    churn_by_document: Counter[int] = Counter()
    company_additions_by_document: defaultdict[int, int] = defaultdict(int)
    company_removals_by_document: defaultdict[int, int] = defaultdict(int)
    for row in assignment_rows:
        document_id = row.get("document_id")
        if document_id is None:
            continue
        document_id = int(document_id)
        churn_by_document[document_id] += 1
        diff_payload = _safe_json_loads(row.get("assignment_diff"))
        company_additions_by_document[document_id] += len(diff_payload.get("added_company_ids", []))
        company_removals_by_document[document_id] += len(diff_payload.get("removed_company_ids", []))

    lines: list[str] = [
        f"# Audience Governance Report ({window.month_label})",
        "",
        f"- Reporting window: {window.date_from.isoformat()} to {window.date_to.isoformat()}",
        f"- Generated at: {datetime.utcnow().isoformat()}Z",
        f"- Total audit rows analyzed: {len(rows)}",
        "",
        "## Summary",
        "",
        f"- Visibility changes: {len(visibility_rows)}",
        f"- Assignment churn operations: {len(assignment_rows)}",
        f"- Exposure events (internal -> public): {len(exposure_rows)}",
        "",
    ]

    lines.append("## Visibility Changes")
    lines.append("")
    visibility_table_rows: list[list[str]] = []
    for row in visibility_rows[:25]:
        details = _safe_json_loads(row.get("details"))
        visibility_table_rows.append(
            [
                str(row.get("created_at") or ""),
                str(row.get("document_id") or ""),
                str(row.get("user_email") or row.get("user_id") or ""),
                f"{details.get('from_visibility') or '?'} -> {details.get('to_visibility') or '?'}",
                str(details.get("reason") or "-"),
            ]
        )
    if visibility_table_rows:
        lines.extend(
            _render_table(
                ["Timestamp", "Document", "Actor", "Transition", "Reason"],
                visibility_table_rows,
            )
        )
    else:
        lines.append("No visibility changes in this period.")
    lines.append("")

    lines.append("## Assignment Churn")
    lines.append("")
    churn_table_rows: list[list[str]] = []
    for document_id, churn_count in churn_by_document.most_common(25):
        churn_table_rows.append(
            [
                str(document_id),
                str(churn_count),
                str(company_additions_by_document.get(document_id, 0)),
                str(company_removals_by_document.get(document_id, 0)),
            ]
        )
    if churn_table_rows:
        lines.extend(
            _render_table(
                ["Document", "Operations", "Companies Added", "Companies Removed"],
                churn_table_rows,
            )
        )
    else:
        lines.append("No assignment churn events in this period.")
    lines.append("")

    lines.append("## Exposure Events")
    lines.append("")
    exposure_table_rows: list[list[str]] = []
    for row in exposure_rows[:25]:
        details = _safe_json_loads(row.get("details"))
        exposure_table_rows.append(
            [
                str(row.get("created_at") or ""),
                str(row.get("document_id") or ""),
                str(row.get("user_email") or row.get("user_id") or ""),
                str(details.get("reason") or "-"),
            ]
        )
    if exposure_table_rows:
        lines.extend(
            _render_table(
                ["Timestamp", "Document", "Actor", "Reason"],
                exposure_table_rows,
            )
        )
    else:
        lines.append("No exposure transitions detected in this period.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a monthly audience governance report "
            "(visibility changes, assignment churn, exposure events)."
        )
    )
    parser.add_argument(
        "--month",
        default=None,
        help="Month to report in YYYY-MM format. Default: previous month.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output markdown path. Default: backend/reports/audience-governance-YYYY-MM.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    window = _build_reporting_window(args.month)
    output_path = (
        Path(args.output).resolve()
        if args.output
        else (REPO_ROOT / "reports" / f"audience-governance-{window.month_label}.md").resolve()
    )

    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        rows = service.export_audit_logs(date_from=window.date_from, date_to=window.date_to)
    finally:
        db.close()

    markdown = _build_markdown_report(window=window, rows=rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"[audience-report] wrote {output_path}")
    print(f"[audience-report] window={window.date_from.isoformat()}..{window.date_to.isoformat()}")
    print(f"[audience-report] audit_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

