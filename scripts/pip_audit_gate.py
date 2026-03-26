#!/usr/bin/env python3
"""AH-015: Security audit gate for pip packages.

Runs `pip-audit` against the checked-in backend lockfiles and exits non-zero if
vulnerabilities are found. Designed to be run in CI/CD pipelines.

Usage:
  pip install pip-audit
  python scripts/pip_audit_gate.py
  python scripts/pip_audit_gate.py --include-dev
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
RUNTIME_MANIFEST = BACKEND_DIR / "requirements.txt"
DEV_MANIFEST = BACKEND_DIR / "requirements-dev.txt"
IGNORE_FILE = BACKEND_DIR / "pip-audit.ignore"


def load_ignore_args() -> list[str]:
    ignore_args: list[str] = []
    if not IGNORE_FILE.exists():
        return ignore_args

    for line in IGNORE_FILE.read_text(encoding="utf-8").splitlines():
        advisory_id = line.strip()
        if not advisory_id or advisory_id.startswith("#"):
            continue
        ignore_args.extend(["--ignore-vuln", advisory_id])
    return ignore_args


def run_audit(manifest: Path, label: str) -> int:
    print(f"[pip-audit] Running {label} security audit on {manifest.name}...")
    result = subprocess.run(
        ["pip-audit", "-r", str(manifest), "--strict", "--desc", *load_ignore_args()],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"\n[FAIL] pip-audit found vulnerabilities in {manifest.name}.")
        return 1

    print(f"[PASS] No vulnerabilities found in {manifest.name}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pip-audit against backend lockfiles")
    parser.add_argument(
        "--include-dev",
        action="store_true",
        help="Also audit backend/requirements-dev.txt",
    )
    args = parser.parse_args()

    exit_code = run_audit(RUNTIME_MANIFEST, "runtime")
    if args.include_dev:
        exit_code = max(exit_code, run_audit(DEV_MANIFEST, "development"))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
