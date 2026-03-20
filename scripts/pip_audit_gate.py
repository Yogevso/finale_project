#!/usr/bin/env python3
"""AH-015: Security audit gate for pip packages.

Runs `pip-audit` and exits non-zero if vulnerabilities are found.
Designed to be run in CI/CD pipelines.

Usage:
  pip install pip-audit
  python scripts/pip_audit_gate.py
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    print("[pip-audit] Running security audit on Python dependencies...")
    result = subprocess.run(
        ["pip-audit", "--strict", "--desc"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print("\n[FAIL] pip-audit found vulnerabilities. Fix before deploying.")
        return 1

    print("[PASS] No vulnerabilities found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
