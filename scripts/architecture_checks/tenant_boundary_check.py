"""Z-016 — Architecture test: verify no cross-tenant data access without tenant_id guard.

Scans service files for direct ORM queries and checks each uses a tenant_id filter.
"""

from __future__ import annotations

import ast
import os
import sys

SERVICES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app", "services")
EXCLUDED = {"quota.py"}  # Quota service is deliberately cross-tenant
TENANT_FILTER_KEYWORDS = {"tenant_id", "tenant_ctx", "Tenant.id"}


def _has_tenant_guard(source: str) -> list[str]:
    """Return list of functions that access DB without a visible tenant_id reference."""
    violations: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body_src = ast.get_source_segment(source, node)
        if body_src is None:
            continue
        # Check if function uses db.query or db.execute
        if "db.query" not in body_src and "db.execute" not in body_src:
            continue
        # Check if any tenant guard keyword exists
        if any(kw in body_src for kw in TENANT_FILTER_KEYWORDS):
            continue
        violations.append(node.name)
    return violations


def main() -> int:
    if not os.path.isdir(SERVICES_DIR):
        print(f"Services directory not found: {SERVICES_DIR}")
        return 1

    total_violations = 0
    for filename in sorted(os.listdir(SERVICES_DIR)):
        if not filename.endswith(".py") or filename in EXCLUDED or filename.startswith("_"):
            continue
        filepath = os.path.join(SERVICES_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        violations = _has_tenant_guard(source)
        if violations:
            print(f"FAIL {filename}: functions without tenant_id guard: {', '.join(violations)}")
            total_violations += len(violations)

    if total_violations:
        print(f"\n{total_violations} cross-tenant boundary violation(s) found")
        return 1

    print("OK — all service methods include tenant_id guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
