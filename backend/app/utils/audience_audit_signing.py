"""Helpers for signing and verifying audience-sensitive audit payloads."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.config import settings


def parse_hmac_keyring(raw: str) -> dict[str, str]:
    keyring: dict[str, str] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            continue
        key_id, secret = token.split(":", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            keyring[key_id] = secret
    return keyring


def canonicalize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sign_payload(payload: dict[str, Any]) -> tuple[str, str]:
    keyring = parse_hmac_keyring(settings.AUDIENCE_AUDIT_HMAC_KEYS)
    active_key_id = settings.AUDIENCE_AUDIT_ACTIVE_KEY_ID
    secret = keyring.get(active_key_id)
    if not secret:
        # Fallback keeps signing operational in dev/test even with malformed env values.
        active_key_id = "fallback"
        secret = settings.SECRET_KEY

    message = canonicalize_payload(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return active_key_id, signature


def verify_payload_signature(payload: dict[str, Any], key_id: str, signature: str) -> bool:
    keyring = parse_hmac_keyring(settings.AUDIENCE_AUDIT_HMAC_KEYS)
    secret = keyring.get(key_id)
    if not secret:
        return False
    message = canonicalize_payload(payload).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

