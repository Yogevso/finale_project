#!/usr/bin/env python3
"""Refactor budget guardrails for CI."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "scripts" / "architecture_checks" / "refactor_budget_config.json"
OVERRIDES_PATH = REPO_ROOT / "scripts" / "architecture_checks" / "refactor_budget_overrides.json"

BRANCHING_RE = re.compile(r"\b(if|elif|for|while|except|case|catch|switch)\b|(&&|\|\|)")


@dataclass
class Override:
    glob: str
    owner: str
    reason: str
    expires_on: date

    def matches(self, path: str) -> bool:
        return self.glob == "__GLOBAL__" or fnmatch.fnmatch(path, self.glob)

    def active(self) -> bool:
        return self.expires_on >= date.today()


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8")


def choose_base_sha() -> str:
    candidates = [
        os.getenv("GITHUB_BASE_SHA", "").strip(),
        os.getenv("GITHUB_BEFORE_SHA", "").strip(),
    ]
    for candidate in candidates:
        if candidate and candidate != "0000000000000000000000000000000000000000":
            return candidate
    return run_git(["rev-parse", "HEAD~1"]).strip()


def choose_head_sha() -> str:
    return os.getenv("GITHUB_HEAD_SHA", "").strip() or "HEAD"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_overrides() -> list[Override]:
    if not OVERRIDES_PATH.exists():
        return []
    raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    overrides: list[Override] = []
    for entry in raw.get("overrides", []):
        try:
            expires = date.fromisoformat(entry["expires_on"])
        except Exception:
            continue
        overrides.append(
            Override(
                glob=entry.get("glob", ""),
                owner=entry.get("owner", ""),
                reason=entry.get("reason", ""),
                expires_on=expires,
            )
        )
    return overrides


def parse_numstat(base_sha: str, head_sha: str) -> list[tuple[str, int]]:
    diff = run_git(["diff", "--numstat", base_sha, head_sha])
    rows: list[tuple[str, int]] = []
    for line in diff.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add_raw, del_raw, path = parts
        if add_raw == "-" or del_raw == "-":
            continue
        try:
            delta = int(add_raw) + int(del_raw)
        except ValueError:
            continue
        rows.append((path, delta))
    return rows


def calculate_branching_additions(
    base_sha: str,
    head_sha: str,
    code_paths: list[str],
) -> int:
    total = 0
    for path in code_paths:
        patch = run_git(["diff", "--unified=0", base_sha, head_sha, "--", path])
        for line in patch.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            if BRANCHING_RE.search(line[1:]):
                total += 1
    return total


def find_override(path: str, overrides: list[Override]) -> Override | None:
    for override in overrides:
        if override.active() and override.matches(path):
            return override
    return None


def main() -> int:
    config = load_config()
    overrides = load_overrides()
    base_sha = choose_base_sha()
    head_sha = choose_head_sha()

    rows = parse_numstat(base_sha, head_sha)
    code_exts = set(config["code_extensions"])
    code_rows = [(path, delta) for path, delta in rows if Path(path).suffix in code_exts]

    total_changes = sum(delta for _, delta in code_rows)
    touched_files = len(code_rows)
    over_file_budget = [
        (path, delta)
        for path, delta in code_rows
        if delta > int(config["max_per_file_line_changes"])
    ]

    code_paths = [path for path, _ in code_rows]
    branching_additions = calculate_branching_additions(base_sha, head_sha, code_paths)

    violations: list[str] = []

    if total_changes > int(config["max_total_line_changes"]):
        override = find_override("__GLOBAL__", overrides)
        if override:
            print(
                f"Global total-line-change override applied by {override.owner}: "
                f"{override.reason} (expires {override.expires_on})"
            )
        else:
            violations.append(
                f"Total changed code lines {total_changes} exceeds budget "
                f"{config['max_total_line_changes']}"
            )

    if touched_files > int(config["max_touched_code_files"]):
        override = find_override("__GLOBAL__", overrides)
        if override:
            print(
                f"Global touched-files override applied by {override.owner}: "
                f"{override.reason} (expires {override.expires_on})"
            )
        else:
            violations.append(
                f"Touched code files {touched_files} exceeds budget "
                f"{config['max_touched_code_files']}"
            )

    if branching_additions > int(config["max_branching_line_additions"]):
        override = find_override("__GLOBAL__", overrides)
        if override:
            print(
                f"Global branching-additions override applied by {override.owner}: "
                f"{override.reason} (expires {override.expires_on})"
            )
        else:
            violations.append(
                f"Branching additions {branching_additions} exceeds budget "
                f"{config['max_branching_line_additions']}"
            )

    for path, delta in over_file_budget:
        override = find_override(path, overrides)
        if override:
            print(
                f"Per-file override applied for {path} by {override.owner}: "
                f"{override.reason} (expires {override.expires_on})"
            )
            continue
        violations.append(
            f"{path} changed lines {delta} exceeds per-file budget "
            f"{config['max_per_file_line_changes']}"
        )

    print(f"Refactor budget base: {base_sha}")
    print(f"Refactor budget head: {head_sha}")
    print(f"Total changed code lines: {total_changes}")
    print(f"Touched code files: {touched_files}")
    print(f"Branching additions: {branching_additions}")

    if violations:
        print("Refactor budget check failed:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "Use scripts/architecture_checks/refactor_budget_overrides.json for explicit owner-approved overrides."
        )
        return 1

    print("Refactor budget check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
