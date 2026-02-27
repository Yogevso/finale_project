#!/usr/bin/env python3
"""Validate and report architecture debt register status."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = [
    "id",
    "title",
    "owner",
    "risk",
    "due date",
    "status",
    "mitigation plan",
    "link",
]

OPEN_STATUSES = {"open", "in_progress", "blocked"}
CLOSED_STATUSES = {"closed", "accepted", "mitigated", "resolved"}
ALL_STATUSES = OPEN_STATUSES | CLOSED_STATUSES


@dataclass
class DebtItem:
    item_id: str
    title: str
    owner: str
    risk: int
    due_date: dt.date
    status: str
    mitigation: str
    link: str


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def parse_table(markdown: str) -> tuple[list[DebtItem], list[str]]:
    lines = markdown.splitlines()
    errors: list[str] = []
    header_index = -1

    for i, line in enumerate(lines):
        cells = [c.lower() for c in split_row(line)]
        if cells == REQUIRED_COLUMNS:
            header_index = i
            break

    if header_index == -1:
        errors.append(
            "Could not find architecture debt table with required columns: "
            + ", ".join(REQUIRED_COLUMNS)
        )
        return [], errors

    items: list[DebtItem] = []
    for line in lines[header_index + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = split_row(line)
        if not cells:
            continue
        if len(cells) != len(REQUIRED_COLUMNS):
            errors.append(f"Invalid row shape: {line.strip()}")
            continue

        item_id, title, owner, risk_raw, due_raw, status_raw, mitigation, link = cells
        if not item_id:
            continue

        status = status_raw.strip().lower()
        if status not in ALL_STATUSES:
            errors.append(
                f"{item_id}: invalid status '{status_raw}'. Allowed: {sorted(ALL_STATUSES)}"
            )
            continue

        try:
            risk = int(risk_raw)
        except ValueError:
            errors.append(f"{item_id}: risk must be integer (got '{risk_raw}')")
            continue

        if risk < 1 or risk > 5:
            errors.append(f"{item_id}: risk must be between 1 and 5")
            continue

        try:
            due_date = dt.date.fromisoformat(due_raw)
        except ValueError:
            errors.append(f"{item_id}: due date must be YYYY-MM-DD (got '{due_raw}')")
            continue

        if not owner:
            errors.append(f"{item_id}: owner is required")
            continue

        if not mitigation:
            errors.append(f"{item_id}: mitigation plan is required")
            continue

        items.append(
            DebtItem(
                item_id=item_id,
                title=title,
                owner=owner,
                risk=risk,
                due_date=due_date,
                status=status,
                mitigation=mitigation,
                link=link,
            )
        )

    return items, errors


def write_summary(message: str) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="docs/architecture-debt.md")
    args = parser.parse_args()

    source = Path(args.file)
    if not source.exists():
        print(f"ERROR: file not found: {source}")
        return 1

    items, errors = parse_table(source.read_text(encoding="utf-8"))
    if errors:
        print("Architecture debt register validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    today = dt.date.today()
    overdue_high_risk = [
        item
        for item in items
        if item.risk >= 4 and item.due_date < today and item.status in OPEN_STATUSES
    ]

    print(f"Architecture debt items: {len(items)}")
    print(f"Overdue high-risk items: {len(overdue_high_risk)}")

    summary_lines = [
        "## Architecture Debt Report\n",
        f"- Total items: {len(items)}\n",
        f"- Overdue high-risk items: {len(overdue_high_risk)}\n",
    ]

    if overdue_high_risk:
        summary_lines.append("\n### Overdue high-risk items\n")
        for item in overdue_high_risk:
            line = (
                f"- {item.item_id}: {item.title} (owner={item.owner}, "
                f"risk={item.risk}, due={item.due_date.isoformat()})\n"
            )
            summary_lines.append(line)
            print(
                "::warning title=Overdue high-risk architecture debt::"
                f"{item.item_id} due {item.due_date.isoformat()} owner {item.owner}"
            )
    else:
        summary_lines.append("\nNo overdue high-risk architecture debt items.\n")

    write_summary("".join(summary_lines))

    fail_on_overdue = os.getenv("FAIL_ON_OVERDUE_HIGH_RISK", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if fail_on_overdue and overdue_high_risk:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
