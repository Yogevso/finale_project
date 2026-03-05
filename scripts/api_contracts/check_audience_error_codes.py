"""Validate audience error catalog against the lockfile contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.errors.audience_errors import AUDIENCE_ERROR_CATALOG  # noqa: E402

LOCKFILE_PATH = ROOT / "docs" / "contracts" / "audience-error-codes.json"
ID_PATTERN = re.compile(r"^AUDIENCE_(\d{3})$")


def _fail(message: str) -> int:
    print(f"[audience-error-codes] {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not LOCKFILE_PATH.exists():
        return _fail(f"lockfile missing: {LOCKFILE_PATH}")

    lockfile = json.loads(LOCKFILE_PATH.read_text(encoding="utf-8"))
    rows = lockfile.get("codes")
    if not isinstance(rows, list):
        return _fail("lockfile 'codes' must be a list")

    lock_by_id: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            return _fail("each lockfile entry must be an object")
        code_id = row.get("id")
        if not isinstance(code_id, str):
            return _fail("lockfile entry missing string 'id'")
        if code_id in lock_by_id:
            return _fail(f"duplicate lockfile id: {code_id}")
        lock_by_id[code_id] = row

    catalog_ids = [entry.id for entry in AUDIENCE_ERROR_CATALOG]
    if len(catalog_ids) != 20:
        return _fail(f"catalog must define exactly 20 codes, got {len(catalog_ids)}")

    for expected_index, code_id in enumerate(catalog_ids, start=1):
        match = ID_PATTERN.match(code_id)
        if not match:
            return _fail(f"invalid catalog id format: {code_id}")
        if int(match.group(1)) != expected_index:
            return _fail(
                "catalog ids must be continuous AUDIENCE_001..AUDIENCE_020 "
                f"(got out-of-sequence id: {code_id})"
            )

    lock_ids = sorted(lock_by_id.keys())
    if sorted(catalog_ids) != lock_ids:
        missing_in_lock = sorted(set(catalog_ids) - set(lock_ids))
        missing_in_catalog = sorted(set(lock_ids) - set(catalog_ids))
        return _fail(
            "catalog/lockfile id mismatch. "
            f"missing_in_lock={missing_in_lock} missing_in_catalog={missing_in_catalog}"
        )

    for entry in AUDIENCE_ERROR_CATALOG:
        locked = lock_by_id[entry.id]
        if locked.get("slug") != entry.slug:
            return _fail(
                f"{entry.id} slug mismatch: catalog='{entry.slug}' lockfile='{locked.get('slug')}'"
            )
        if int(locked.get("http_status", -1)) != int(entry.http_status):
            return _fail(
                f"{entry.id} http_status mismatch: "
                f"catalog={entry.http_status} lockfile={locked.get('http_status')}"
            )

    print(
        f"[audience-error-codes] OK - {len(AUDIENCE_ERROR_CATALOG)} entries match {LOCKFILE_PATH.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

