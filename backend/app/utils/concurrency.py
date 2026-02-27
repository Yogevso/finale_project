"""Optimistic-concurrency helpers for ETag generation and precondition checks."""

from __future__ import annotations

from app.errors import ConflictError, PreconditionRequiredError


def build_resource_etag(resource_type: str, resource_id: int, row_version: int) -> str:
    """Build deterministic ETag token for one mutable resource row."""
    return f"{resource_type}:{resource_id}:{row_version}"


def parse_if_match_token(if_match: str | None) -> str:
    """Normalize If-Match value to a bare token."""
    if if_match is None or not if_match.strip():
        raise PreconditionRequiredError(
            "If-Match header is required for update operations. Fetch the latest resource and retry."
        )

    token = if_match.strip()
    if token.startswith("W/"):
        token = token[2:].strip()
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        token = token[1:-1]
    return token


def ensure_if_match_matches(
    *,
    if_match: str | None,
    resource_type: str,
    resource_id: int,
    row_version: int,
) -> None:
    """Enforce optimistic concurrency precondition."""
    token = parse_if_match_token(if_match)
    expected = build_resource_etag(resource_type, resource_id, row_version)
    if token in {expected, str(row_version)}:
        return
    raise ConflictError(
        "Write conflict detected. The resource changed since your last read; refresh and retry."
    )
