"""Utilities for structured review feedback payloads."""

from __future__ import annotations

import json
from typing import Any

GENERAL_FEEDBACK_LABEL = "General feedback:"
SECTION_SUGGESTIONS_LABEL = "Section suggestions:"
ALLOWED_SEVERITIES = {"low", "medium", "high", "blocker"}
DEFAULT_SEVERITY = "medium"


def _normalize_text(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _normalize_optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.isdigit():
            return int(normalized)
    return None


def parse_legacy_review_comments(review_comments: str | None) -> dict[str, Any] | None:
    """Parse the legacy free-text review feedback format into structured payload."""
    text = (review_comments or "").strip()
    if not text:
        return None

    section_index = text.find(SECTION_SUGGESTIONS_LABEL)
    general_index = text.find(GENERAL_FEEDBACK_LABEL)

    general_comment = ""
    section_block = text

    if general_index >= 0:
        general_start = general_index + len(GENERAL_FEEDBACK_LABEL)
        general_end = section_index if section_index >= 0 else len(text)
        general_comment = text[general_start:general_end].strip()

    if section_index >= 0:
        section_block = text[section_index + len(SECTION_SUGGESTIONS_LABEL) :].strip()
    else:
        section_block = ""

    section_comments: list[dict[str, Any]] = []
    if section_block:
        chunks = [chunk.strip() for chunk in section_block.split("## ") if chunk.strip()]
        for chunk in chunks:
            lines = chunk.splitlines()
            if not lines:
                continue
            title = (lines[0] or "").strip()
            comment = "\n".join(lines[1:]).strip()
            if not title or not comment:
                continue
            section_comments.append(
                {
                    "title": title,
                    "comment": comment,
                    "severity": DEFAULT_SEVERITY,
                    "anchor_id": None,
                    "action_item_assignee": None,
                }
            )

    if general_index < 0 and section_index < 0:
        general_comment = text

    payload = normalize_review_feedback(
        {
            "general_comment": general_comment,
            "section_comments": section_comments,
        }
    )
    if payload:
        return payload

    fallback_comment = _normalize_text(text)
    if not fallback_comment:
        return None
    return {"general_comment": fallback_comment, "section_comments": []}


def normalize_review_feedback(
    payload: dict[str, Any] | None,
    *,
    fallback_comments: str | None = None,
) -> dict[str, Any] | None:
    """Validate/coerce structured feedback payload into canonical JSON shape."""
    raw_payload = payload if isinstance(payload, dict) else {}

    general_comment = _normalize_text(raw_payload.get("general_comment"))
    section_comments_raw = raw_payload.get("section_comments")
    section_comments: list[dict[str, Any]] = []
    if isinstance(section_comments_raw, list):
        for item in section_comments_raw:
            if not isinstance(item, dict):
                continue

            comment = _normalize_text(item.get("comment"))
            if not comment:
                continue

            title = _normalize_text(item.get("title"))
            anchor_id = _normalize_text(item.get("anchor_id"))
            severity = (_normalize_text(item.get("severity")) or DEFAULT_SEVERITY).lower()
            if severity not in ALLOWED_SEVERITIES:
                severity = DEFAULT_SEVERITY
            action_item_assignee = _normalize_optional_int(item.get("action_item_assignee"))

            section_payload: dict[str, Any] = {
                "comment": comment,
                "severity": severity,
            }
            if title:
                section_payload["title"] = title
            if anchor_id:
                section_payload["anchor_id"] = anchor_id
            if action_item_assignee is not None:
                section_payload["action_item_assignee"] = action_item_assignee

            section_comments.append(section_payload)

    if not general_comment:
        general_comment = _normalize_text(fallback_comments)

    if not general_comment and not section_comments:
        return None

    return {
        "general_comment": general_comment or "",
        "section_comments": section_comments,
    }


def serialize_review_feedback(
    payload: dict[str, Any] | None,
    *,
    fallback_comments: str | None = None,
) -> str | None:
    normalized = normalize_review_feedback(payload, fallback_comments=fallback_comments)
    if not normalized:
        return None
    return json.dumps(normalized, ensure_ascii=False)


def deserialize_review_feedback(
    review_feedback_json: str | None,
    *,
    fallback_comments: str | None = None,
) -> dict[str, Any] | None:
    if review_feedback_json:
        try:
            parsed = json.loads(review_feedback_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        normalized = normalize_review_feedback(parsed, fallback_comments=fallback_comments)
        if normalized:
            return normalized

    legacy = parse_legacy_review_comments(fallback_comments)
    if legacy:
        return legacy
    return None
