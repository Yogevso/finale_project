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
    BACKEND_APP / "application" / "contexts" / "portal",
    BACKEND_APP / "application" / "contexts" / "users",
]

REQUIRED_FILES = [
    BACKEND_APP / "application" / "contexts" / "documents" / "api.py",
    BACKEND_APP / "application" / "contexts" / "reviews" / "api.py",
    BACKEND_APP / "application" / "contexts" / "collaboration" / "api.py",
    BACKEND_APP / "application" / "contexts" / "tenants" / "api.py",
    BACKEND_APP / "application" / "contexts" / "notifications" / "api.py",
    BACKEND_APP / "application" / "contexts" / "portal" / "api.py",
    BACKEND_APP / "application" / "contexts" / "users" / "api.py",
    REPO_ROOT / "docs" / "adr" / "ADR-0003-backend-context-first-architecture.md",
    REPO_ROOT / "docs" / "adr" / "ADR-0004-aggregate-repository-boundaries.md",
    REPO_ROOT / "docs" / "adr" / "ADR-0005-error-boundary-policy.md",
    BACKEND_APP / "repositories" / "support_ticket_repository.py",
]
MODEL_PACKAGE_FILES = {
    BACKEND_APP / "models" / "enums.py",
    BACKEND_APP / "models" / "content.py",
    BACKEND_APP / "models" / "engagement.py",
    BACKEND_APP / "models" / "audit.py",
    BACKEND_APP / "models" / "collaboration.py",
    BACKEND_APP / "models" / "support.py",
    BACKEND_APP / "models" / "operations.py",
    BACKEND_APP / "models" / "assistant.py",
    BACKEND_APP / "models" / "growth.py",
}
MAX_MODEL_INIT_LINES = 250
REPOSITORY_BOUNDARY_TARGETS = {
    BACKEND_APP / "application" / "contexts" / "users" / "api.py": [
        "UserRepository",
    ],
    BACKEND_APP / "services" / "support_service.py": [
        "SupportTicketRepository",
        "UserRepository",
    ],
    BACKEND_APP / "services" / "comment_service.py": [
        "CommentRepository",
        "DocumentRepository",
        "VersionRepository",
    ],
    BACKEND_APP / "services" / "version_service.py": [
        "DocumentRepository",
        "VersionRepository",
    ],
    BACKEND_APP / "services" / "auth_service.py": [
        "UserRepository",
    ],
}

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import|import\s+([a-zA-Z_][a-zA-Z0-9_\.]*))"
)
ROUTE_GUARD_DEF_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+([_a-zA-Z][_a-zA-Z0-9]*)\s*\(",
    re.MULTILINE,
)
SHARED_ROUTE_GUARD_NAMES = {
    "require_admin",
    "require_customer",
    "require_editor",
    "require_internal_user",
    "require_manager",
    "require_system_admin",
}
ERROR_BOUNDARY_HTTP_EXCEPTION_ROOTS = [
    BACKEND_APP / "services",
    BACKEND_APP / "application",
    BACKEND_APP / "collaboration",
]
RESULT_ALLOWED_ROOTS = [
    BACKEND_APP / "application" / "commands",
    BACKEND_APP / "application" / "queries",
]
RESULT_ALLOWED_FILES = {
    BACKEND_APP / "domain" / "result.py",
    BACKEND_APP / "domain" / "__init__.py",
}


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


def check_route_boundary_rules(errors: list[str]) -> None:
    routes_root = BACKEND_APP / "api"
    if not routes_root.exists():
        return

    for path in iter_python_files(routes_root):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line_no, module in extract_imports(path):
            if starts_with_any(module, ["app.web.controllers"]):
                errors.append(
                    f"{rel}:{line_no} route layer must not import '{module}'; "
                    "use app.application.contexts.*.api or dependency providers instead"
                )
            if module.startswith("app.application.contexts."):
                module_parts = module.split(".")
                if len(module_parts) > 4 and module_parts[4] != "api":
                    errors.append(
                        f"{rel}:{line_no} route layer must import context public APIs only, got "
                        f"'{module}'"
                    )


def check_route_guard_redefinitions(errors: list[str]) -> None:
    routes_root = BACKEND_APP / "api"
    if not routes_root.exists():
        return

    for path in iter_python_files(routes_root):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Failed reading {rel}: {exc}")
            continue

        for match in ROUTE_GUARD_DEF_RE.finditer(source):
            guard_name = match.group(1)
            normalized_name = guard_name.lstrip("_")
            if normalized_name == "require_enabled":
                continue
            if not normalized_name.startswith("require_"):
                continue

            line_no = source.count("\n", 0, match.start()) + 1
            if normalized_name in SHARED_ROUTE_GUARD_NAMES:
                errors.append(
                    f"{rel}:{line_no} route layer must use app.dependencies.permissions."
                    f"{normalized_name} instead of redefining local guard '{guard_name}'"
                )
            else:
                errors.append(
                    f"{rel}:{line_no} route layer must not define local auth guard '{guard_name}'; "
                    "compose shared dependencies/policies from app.dependencies.* instead"
                )


def check_models_package_structure(errors: list[str]) -> None:
    models_root = BACKEND_APP / "models"
    init_path = models_root / "__init__.py"
    if not init_path.exists():
        errors.append(f"Missing required file: {init_path.relative_to(REPO_ROOT)}")
        return

    missing = [path for path in sorted(MODEL_PACKAGE_FILES) if not path.exists()]
    for path in missing:
        errors.append(f"Missing split model module: {path.relative_to(REPO_ROOT)}")

    try:
        init_lines = len(init_path.read_text(encoding="utf-8").splitlines())
    except OSError as exc:
        errors.append(f"Failed reading {init_path.relative_to(REPO_ROOT)}: {exc}")
        return

    if init_lines > MAX_MODEL_INIT_LINES:
        errors.append(
            f"{init_path.relative_to(REPO_ROOT)} exceeds {MAX_MODEL_INIT_LINES} lines "
            f"({init_lines})"
        )


def check_repository_boundary_rules(errors: list[str]) -> None:
    for path, required_tokens in REPOSITORY_BOUNDARY_TARGETS.items():
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(REPO_ROOT)}")
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Failed reading {path.relative_to(REPO_ROOT)}: {exc}")
            continue
        for token in required_tokens:
            if token not in source:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)} must reference repository boundary token "
                    f"'{token}'"
                )


def check_error_boundary_rules(errors: list[str]) -> None:
    for root in ERROR_BOUNDARY_HTTP_EXCEPTION_ROOTS:
        if not root.exists():
            continue
        for path in iter_python_files(root):
            rel = path.relative_to(REPO_ROOT).as_posix()
            try:
                source = path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"Failed reading {rel}: {exc}")
                continue

            if "HTTPException" in source:
                errors.append(
                    f"{rel} must not reference HTTPException; "
                    "raise app.errors.DomainError subclasses and let transport layers map them"
                )

            if "Result" not in source:
                continue
            if path in RESULT_ALLOWED_FILES:
                continue
            if any(path.is_relative_to(allowed_root) for allowed_root in RESULT_ALLOWED_ROOTS):
                continue
            if (
                "from app.domain.result import Result" in source
                or "Result[" in source
                or "Result.ok(" in source
                or "Result.err(" in source
            ):
                errors.append(
                    f"{rel} must not use Result; keep Result at command/query boundaries only"
                )


def main() -> int:
    errors: list[str] = []
    check_required_structure(errors)
    check_layer_import_rules(errors)
    check_context_cross_import_rules(errors)
    check_route_boundary_rules(errors)
    check_route_guard_redefinitions(errors)
    check_models_package_structure(errors)
    check_repository_boundary_rules(errors)
    check_error_boundary_rules(errors)

    if errors:
        print("Backend architecture checks failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Backend architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
