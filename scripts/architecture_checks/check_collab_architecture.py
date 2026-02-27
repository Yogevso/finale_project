#!/usr/bin/env python3
"""Collaboration server architecture fitness checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COLLAB_SRC = REPO_ROOT / "collab-server" / "src"

REQUIRED_DIRS = [
    COLLAB_SRC / "ports",
    COLLAB_SRC / "adapters",
    COLLAB_SRC / "layers" / "domain",
    COLLAB_SRC / "layers" / "application",
    COLLAB_SRC / "layers" / "infrastructure",
    COLLAB_SRC / "layers" / "web",
]

IMPORT_RE = re.compile(
    r"^\s*import(?:[\s\w{},*]+from\s+)?['\"]([^'\"]+)['\"];?"
)


def extract_imports(path: Path) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = IMPORT_RE.match(line)
        if match:
            imports.append((idx, match.group(1)))
    return imports


def main() -> int:
    errors: list[str] = []

    for directory in REQUIRED_DIRS:
        if not directory.exists():
            errors.append(f"Missing required directory: {directory.relative_to(REPO_ROOT)}")

    persistence_file = COLLAB_SRC / "persistence.ts"
    if persistence_file.exists():
        imports = extract_imports(persistence_file)
        for line_no, module in imports:
            if module == "axios":
                rel = persistence_file.relative_to(REPO_ROOT).as_posix()
                errors.append(
                    f"{rel}:{line_no} direct axios import is forbidden; use adapter via ports"
                )

    # Layer rule baseline: layer modules should not import adapters directly.
    for layer_file in (COLLAB_SRC / "layers").rglob("*.ts"):
        rel = layer_file.relative_to(REPO_ROOT).as_posix()
        for line_no, module in extract_imports(layer_file):
            if "/adapters/" in module or module.startswith("../adapters"):
                errors.append(f"{rel}:{line_no} layer module must not import adapter module '{module}'")

    if errors:
        print("Collab architecture checks failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Collab architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
