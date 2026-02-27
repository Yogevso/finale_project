#!/usr/bin/env python3
"""Backend architecture fitness checks for layer/context boundaries."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"

REQUIRED_DIRS = [
    BACKEND_APP / "domain",
    BACKEND_APP / "application",
    BACKEND_APP / "infrastructure",
    BACKEND_APP / "web",
    BACKEND_APP / "application" / "contexts" / "documents",
    BACKEND_APP / "application" / "contexts" / "reviews",
    BACKEND_APP / "application" / "contexts" / "collaboration",
    BACKEND_APP / "application" / "contexts" / "tenants",
    BACKEND_APP / "application" / "contexts" / "notifications",
]

REQUIRED_FILES = [
    BACKEND_APP / "application" / "contexts" / "documents" / "api.py",
    BACKEND_APP / "application" / "contexts" / "reviews" / "api.py",
    BACKEND_APP / "application" / "contexts" / "collaboration" / "api.py",
    BACKEND_APP / "application" / "contexts" / "tenants" / "api.py",
    BACKEND_APP / "application" / "contexts" / "notifications" / "api.py",
]

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import|import\s+([a-zA-Z_][a-zA-Z0-9_\.]*))"
)


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def extract_imports(path: Path) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        match = IMPORT_RE.match(line)
        if not match:
            continue
        module = match.group(1) or match.group(2)
        if module:
            imports.append((idx, module))
    return imports


def check_required_structure(errors: list[str]) -> None:
    for directory in REQUIRED_DIRS:
        if not directory.exists():
            errors.append(f"Missing required directory: {directory.relative_to(REPO_ROOT)}")
    for file in REQUIRED_FILES:
        if not file.exists():
            errors.append(f"Missing required file: {file.relative_to(REPO_ROOT)}")


def starts_with_any(value: str, prefixes: list[str]) -> bool:
    return any(value == prefix or value.startswith(f"{prefix}.") for prefix in prefixes)


def check_layer_import_rules(errors: list[str]) -> None:
    # Only enforce on new layer packages to avoid blocking current legacy tree.
    checks = [
        ("domain", ["app.application", "app.infrastructure", "app.web", "app.api"]),
        ("application", ["app.web", "app.api"]),
        ("infrastructure", ["app.web", "app.api"]),
        ("web", ["app.infrastructure"]),
    ]

    for layer, forbidden in checks:
        layer_root = BACKEND_APP / layer
        if not layer_root.exists():
            continue
        for path in iter_python_files(layer_root):
            rel = path.relative_to(REPO_ROOT).as_posix()
            for line_no, module in extract_imports(path):
                if starts_with_any(module, forbidden):
                    errors.append(
                        f"{rel}:{line_no} forbidden import '{module}' for layer '{layer}'"
                    )


def check_context_cross_import_rules(errors: list[str]) -> None:
    contexts_root = BACKEND_APP / "application" / "contexts"
    if not contexts_root.exists():
        return

    for path in iter_python_files(contexts_root):
        rel_parts = path.relative_to(contexts_root).parts
        if len(rel_parts) < 2:
            continue
        current_ctx = rel_parts[0]
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line_no, module in extract_imports(path):
            if not module.startswith("app.application.contexts."):
                continue
            module_parts = module.split(".")
            if len(module_parts) < 4:
                continue
            target_ctx = module_parts[3]
            if target_ctx == current_ctx:
                continue

            # Allow cross-context imports only via context public API surface.
            allowed = (
                module == f"app.application.contexts.{target_ctx}"
                or module == f"app.application.contexts.{target_ctx}.api"
            )
            if not allowed:
                errors.append(
                    f"{rel}:{line_no} cross-context import must use public API, got '{module}'"
                )


def main() -> int:
    errors: list[str] = []
    check_required_structure(errors)
    check_layer_import_rules(errors)
    check_context_cross_import_rules(errors)

    if errors:
        print("Backend architecture checks failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Backend architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
