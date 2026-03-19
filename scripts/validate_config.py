#!/usr/bin/env python3
"""AH-014: Deploy-time configuration validator.

Validates environment variables across backend, frontend, and collab-server.
Exit code 0 = all required vars are set.
Exit code 1 = one or more required vars missing or invalid.

Usage:
  python scripts/validate_config.py [--env production|staging|development]
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# -------------------------------------------------------------------
# Define required vars per component
# -------------------------------------------------------------------

BACKEND_REQUIRED = [
    "DATABASE_URL",
    "SECRET_KEY",
    "JWT_SECRET_KEY",
]

BACKEND_PRODUCTION = [
    "APP_ENV",
    "CORS_ORIGINS",
]

FRONTEND_REQUIRED = [
    "VITE_API_URL",
]

FRONTEND_PRODUCTION = [
    "VITE_AUTH_COOKIE_SECURE",
]

COLLAB_REQUIRED = [
    "PORT",
]

COLLAB_PRODUCTION = [
    "BACKEND_URL",
]


@dataclass
class ValidationResult:
    component: str
    missing: list[str]
    warnings: list[str]


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv-style file into a dict."""
    if not path.exists():
        return {}
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip("\"'")
    return env


def validate_component(
    name: str,
    required: list[str],
    prod_required: list[str],
    env: dict[str, str],
    is_prod: bool,
) -> ValidationResult:
    missing = []
    warnings = []
    all_required = required + (prod_required if is_prod else [])
    for var in all_required:
        if var not in env or not env[var]:
            missing.append(var)

    # Warn about insecure defaults in production
    if is_prod and name == "backend":
        if env.get("SECRET_KEY", "").lower() in ("changeme", "dev-secret"):
            warnings.append("SECRET_KEY appears to be a dev placeholder")
        if env.get("JWT_SECRET_KEY", "").lower() in ("changeme", "dev-secret"):
            warnings.append("JWT_SECRET_KEY appears to be a dev placeholder")

    return ValidationResult(component=name, missing=missing, warnings=warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deploy config")
    parser.add_argument(
        "--env",
        choices=["production", "staging", "development"],
        default="production",
    )
    args = parser.parse_args()

    is_prod = args.env in ("production", "staging")
    root = Path(__file__).resolve().parent.parent

    # Merge os.environ with any .env files (os.environ takes precedence)
    backend_env = {**load_env_file(root / "backend" / ".env"), **os.environ}
    frontend_env = {**load_env_file(root / "frontend" / ".env"), **os.environ}
    collab_env = {**load_env_file(root / "collab-server" / ".env"), **os.environ}

    results = [
        validate_component("backend", BACKEND_REQUIRED, BACKEND_PRODUCTION, backend_env, is_prod),
        validate_component("frontend", FRONTEND_REQUIRED, FRONTEND_PRODUCTION, frontend_env, is_prod),
        validate_component("collab-server", COLLAB_REQUIRED, COLLAB_PRODUCTION, collab_env, is_prod),
    ]

    has_error = False
    for r in results:
        if r.missing:
            has_error = True
            print(f"[ERROR] {r.component}: missing {r.missing}")
        if r.warnings:
            for w in r.warnings:
                print(f"[WARN] {r.component}: {w}")
        if not r.missing and not r.warnings:
            print(f"[OK] {r.component}")

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
