"""Detect audience error-code removals versus main and emit PR-comment markdown."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCKFILE = ROOT / "docs" / "contracts" / "audience-error-codes.json"


def _load_codes_from_blob(text: str) -> set[str]:
    payload = json.loads(text)
    rows = payload.get("codes", [])
    return {str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id")}


def _load_current_codes() -> set[str]:
    if not LOCKFILE.exists():
        raise FileNotFoundError(f"Missing lockfile: {LOCKFILE}")
    return _load_codes_from_blob(LOCKFILE.read_text(encoding="utf-8"))


def _load_base_codes(base_ref: str) -> set[str]:
    git_object = f"{base_ref}:docs/contracts/audience-error-codes.json"
    result = subprocess.run(
        ["git", "show", git_object],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        missing_messages = [
            "exists on disk, but not in",
            "path 'docs/contracts/audience-error-codes.json' does not exist",
            "invalid object name",
        ]
        if any(message in stderr for message in missing_messages):
            print(
                f"[audience-contract-drift] Base lockfile missing in {base_ref}; skipping removal check.",
            )
            return set()
        raise RuntimeError(f"Unable to load base lockfile from {git_object}: {stderr}")
    return _load_codes_from_blob(result.stdout)


def _build_comment_markdown(removed: list[str], *, base_ref: str) -> str:
    lines = [
        "### Audience Contract Drift Detected",
        "",
        f"Compared against `{base_ref}`, the following audience error codes were removed:",
        "",
    ]
    lines.extend(f"- `{code}`" for code in removed)
    lines.extend(
        [
            "",
            "Removing error codes is a breaking contract change.",
            "Restore the removed codes or explicitly coordinate a contract version bump.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main", help="Git ref to compare against")
    parser.add_argument(
        "--comment-output",
        default="",
        help="Optional path to write markdown comment body when drift is detected",
    )
    args = parser.parse_args()

    current_codes = _load_current_codes()
    base_codes = _load_base_codes(args.base_ref)
    removed_codes = sorted(base_codes - current_codes)

    if not removed_codes:
        print(
            f"[audience-contract-drift] OK - no removed codes compared to {args.base_ref}",
        )
        return 0

    print(
        "[audience-contract-drift] FAIL - removed code IDs: "
        + ", ".join(removed_codes),
        file=sys.stderr,
    )

    if args.comment_output:
        comment_path = Path(args.comment_output)
        comment_path.parent.mkdir(parents=True, exist_ok=True)
        comment_path.write_text(
            _build_comment_markdown(removed_codes, base_ref=args.base_ref),
            encoding="utf-8",
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
