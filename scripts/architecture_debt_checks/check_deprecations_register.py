#!/usr/bin/env python3
"""Validate deprecation register and publish active deprecations summary."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = [
    "id",
    "component",
    "replacement",
    "stage",
    "owner",
    "announced",
    "warn from",
    "removal target",
    "notes",
]

ACTIVE_STAGES = {"proposed", "deprecated", "warned"}
VALID_STAGES = ACTIVE_STAGES | {"removed"}


@dataclass
class Deprecation:
    dep_id: str
    component: str
    replacement: str
    stage: str
    owner: str
    announced: dt.date
    warn_from: dt.date
    removal_target: dt.date
    notes: str


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def parse_table(markdown: str) -> tuple[list[Deprecation], list[str]]:
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
            "Could not find deprecations table with required columns: "
            + ", ".join(REQUIRED_COLUMNS)
        )
        return [], errors

    entries: list[Deprecation] = []
    for line in lines[header_index + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = split_row(line)
        if not cells:
            continue
        if len(cells) != len(REQUIRED_COLUMNS):
            errors.append(f"Invalid row shape: {line.strip()}")
            continue

        dep_id, component, replacement, stage_raw, owner, announced_raw, warn_raw, removal_raw, notes = (
            cells
        )
        if not dep_id:
            continue

        stage = stage_raw.lower()
        if stage not in VALID_STAGES:
            errors.append(f"{dep_id}: invalid stage '{stage_raw}'")
            continue

        # For documented deprecations, owner and removal target are mandatory.
        if stage in ACTIVE_STAGES and not owner:
            errors.append(f"{dep_id}: owner is required for active deprecations")
            continue

        def parse_date(name: str, raw_value: str) -> dt.date:
            try:
                return dt.date.fromisoformat(raw_value)
            except ValueError as exc:
                raise ValueError(f"{dep_id}: {name} must be YYYY-MM-DD (got '{raw_value}')") from exc

        try:
            announced = parse_date("announced", announced_raw)
            warn_from = parse_date("warn from", warn_raw)
            removal_target = parse_date("removal target", removal_raw)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if removal_target < warn_from:
            errors.append(f"{dep_id}: removal target cannot be before warn from date")
            continue

        entries.append(
            Deprecation(
                dep_id=dep_id,
                component=component,
                replacement=replacement,
                stage=stage,
                owner=owner,
                announced=announced,
                warn_from=warn_from,
                removal_target=removal_target,
                notes=notes,
            )
        )

    return entries, errors


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
    parser.add_argument("file", nargs="?", default="docs/deprecations.md")
    args = parser.parse_args()

    source = Path(args.file)
    if not source.exists():
        print(f"ERROR: file not found: {source}")
        return 1

    text = source.read_text(encoding="utf-8")
    entries, errors = parse_table(text)

    # Allow empty register explicitly.
    if "No active deprecations are currently registered." in text and not entries and not errors:
        write_summary("## Deprecation Report\n- No active deprecations are currently registered.\n")
        print("No active deprecations are currently registered.")
        return 0

    if errors:
        print("Deprecation register validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    today = dt.date.today()
    active = [entry for entry in entries if entry.stage in ACTIVE_STAGES]
    near_removal = [
        entry
        for entry in active
        if entry.stage == "warned" and 0 <= (entry.removal_target - today).days <= 30
    ]

    print(f"Total deprecations: {len(entries)}")
    print(f"Active deprecations: {len(active)}")

    summary_lines = [
        "## Deprecation Report\n",
        f"- Total deprecations: {len(entries)}\n",
        f"- Active deprecations: {len(active)}\n",
    ]

    if active:
        summary_lines.append("\n### Active deprecations\n")
        for entry in active:
            summary_lines.append(
                f"- {entry.dep_id}: {entry.component} ({entry.stage}), owner={entry.owner}, "
                f"target={entry.removal_target.isoformat()}\n"
            )
    else:
        summary_lines.append("\nNo active deprecations.\n")

    if near_removal:
        summary_lines.append("\n### Warned deprecations nearing removal\n")
        for entry in near_removal:
            summary_lines.append(
                f"- {entry.dep_id}: removal target {entry.removal_target.isoformat()}\n"
            )
            print(
                "::warning title=Deprecation nearing removal::"
                f"{entry.dep_id} target {entry.removal_target.isoformat()}"
            )

    write_summary("".join(summary_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
