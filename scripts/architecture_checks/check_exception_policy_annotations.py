#!/usr/bin/env python3
"""Require explicit policy annotations on broad exception handlers."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"
ALLOWED_POLICIES = {
    "BOUNDARY",
    "COMPENSATING",
    "DEGRADED",
    "FAIL_FAST",
    "LOSSY",
    "RETRYABLE",
}
EXCEPT_EXCEPTION_RE = re.compile(r"except Exception(?:\s+as\s+\w+)?\s*:")
POLICY_RE = re.compile(r"policy:\s*([A-Z_]+)")


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def main() -> int:
    errors: list[str] = []

    for path in iter_python_files(BACKEND_APP):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not EXCEPT_EXCEPTION_RE.search(line):
                continue

            match = POLICY_RE.search(line)
            if match is None:
                errors.append(
                    f"{rel}:{line_no} broad exception catch requires inline "
                    "policy annotation (e.g. '# policy: LOSSY ...')"
                )
                continue

            policy = match.group(1)
            if policy not in ALLOWED_POLICIES:
                errors.append(
                    f"{rel}:{line_no} broad exception catch uses unsupported policy "
                    f"'{policy}' (allowed: {', '.join(sorted(ALLOWED_POLICIES))})"
                )

    if errors:
        print("Broad exception policy checks failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Broad exception policy checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
