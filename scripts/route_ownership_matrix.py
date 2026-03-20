#!/usr/bin/env python3
"""AH-016: Route ownership matrix generator.

Introspects FastAPI routes and generates a CSV/JSON matrix with:
  - endpoint path
  - HTTP method
  - audience (portal, viewer, management, public)
  - auth dependency (require_admin, require_customer, etc.)
  - router file location

Usage:
  cd backend
  python -c "from scripts.route_ownership_matrix import generate_matrix; generate_matrix()"

Or run directly:
  python scripts/route_ownership_matrix.py --format csv > routes.csv
  python scripts/route_ownership_matrix.py --format json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RouteEntry:
    path: str
    method: str
    audience: str
    auth_dependency: str
    operation_id: str
    tags: str


def detect_audience(path: str, tags: list[str]) -> str:
    """Infer audience from path prefix or tags."""
    path_lower = path.lower()
    if "/portal/" in path_lower:
        return "customer"
    if "/viewer/" in path_lower:
        return "public"
    if any(t.lower() in ("public",) for t in tags):
        return "public"
    if any(t.lower() in ("customer portal",) for t in tags):
        return "customer"
    return "internal"


def detect_auth(dependencies: list[Any]) -> str:
    """Extract auth dependency name from route dependencies."""
    auth_names = []
    for dep in dependencies or []:
        dep_name = getattr(dep, "__name__", None) or str(dep)
        if "require" in dep_name.lower() or "current_user" in dep_name.lower():
            auth_names.append(dep_name)
    return ", ".join(auth_names) if auth_names else "none"


def generate_matrix() -> list[RouteEntry]:
    """Generate route matrix by introspecting the running app."""
    # Import here to ensure app is loadable
    from app.main import app

    entries = []
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        path = getattr(route, "path", "")
        methods = list(getattr(route, "methods", []))
        tags = list(getattr(route, "tags", []))
        operation_id = getattr(route, "operation_id", "") or ""
        deps = getattr(route, "dependencies", []) or []
        # Also check endpoint dependencies
        endpoint = getattr(route, "endpoint", None)
        if endpoint:
            endpoint_deps = getattr(endpoint, "__wrapped__", endpoint)
            extra_deps = getattr(endpoint_deps, "dependencies", []) or []
            deps = list(deps) + list(extra_deps)

        audience = detect_audience(path, tags)
        auth_dep = detect_auth(deps)

        for method in methods:
            if method == "HEAD":
                continue
            entries.append(RouteEntry(
                path=path,
                method=method,
                audience=audience,
                auth_dependency=auth_dep,
                operation_id=operation_id,
                tags=", ".join(tags),
            ))

    # Sort by path then method
    entries.sort(key=lambda e: (e.path, e.method))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate route ownership matrix")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    entries = generate_matrix()

    if args.format == "json":
        print(json.dumps([asdict(e) for e in entries], indent=2))
    else:
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=["path", "method", "audience", "auth_dependency", "operation_id", "tags"],
        )
        writer.writeheader()
        for e in entries:
            writer.writerow(asdict(e))

    return 0


if __name__ == "__main__":
    sys.exit(main())
