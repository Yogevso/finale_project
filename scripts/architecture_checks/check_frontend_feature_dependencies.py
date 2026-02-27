#!/usr/bin/env python3
"""Frontend dependency boundary checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
IMPORT_RE = re.compile(r"^\s*import(?:[\s\w{},*]+from\s+)?['\"]([^'\"]+)['\"];?")


def iter_ts_files() -> list[Path]:
    return sorted(
        p
        for p in FRONTEND_SRC.rglob("*")
        if p.suffix in {".ts", ".tsx"} and "node_modules" not in p.parts
    )


def extract_imports(path: Path) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = IMPORT_RE.match(line)
        if match:
            imports.append((idx, match.group(1)))
    return imports


def feature_name_from_path(path: Path) -> str | None:
    try:
        rel = path.relative_to(FRONTEND_SRC)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "features":
        return parts[1]
    return None


def main() -> int:
    errors: list[str] = []

    for path in iter_ts_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        imports = extract_imports(path)
        rel_parts = path.relative_to(FRONTEND_SRC).parts
        in_components = len(rel_parts) > 0 and rel_parts[0] == "components"
        in_lib = len(rel_parts) > 0 and rel_parts[0] == "lib"
        current_feature = feature_name_from_path(path)

        for line_no, module in imports:
            normalized = module.replace("\\", "/")

            # Rule: shared layers cannot depend on page layer.
            if in_components or in_lib:
                if normalized.startswith("@/pages") or "/pages/" in normalized or normalized.startswith("../pages"):
                    errors.append(f"{rel}:{line_no} shared module must not import pages ('{module}')")

            # Rule: feature-to-feature deep imports are forbidden.
            if current_feature and normalized.startswith("@/features/"):
                parts = normalized.split("/")
                if len(parts) >= 3:
                    target_feature = parts[2]
                    if target_feature != current_feature and len(parts) > 3:
                        errors.append(
                            f"{rel}:{line_no} cross-feature import must use public entrypoint "
                            f"('@/features/{target_feature}'), got '{module}'"
                        )

    if errors:
        print("Frontend dependency checks failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Frontend dependency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
