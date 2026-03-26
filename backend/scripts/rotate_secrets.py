#!/usr/bin/env python3
"""AA-005: Secret key rotation script with runtime-backed grace period.

Rotates JWT secret key and HMAC audit signing key. JWT rotation now supports a
24-hour grace period during which the old key remains accepted for token
verification through `SECRET_KEY_OLD`.

Usage:
    python -m scripts.rotate_secrets --type jwt
    python -m scripts.rotate_secrets --type hmac
    python -m scripts.rotate_secrets --type all
    python -m scripts.rotate_secrets --show-current
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

# State file for tracking rotations
ROTATION_STATE_FILE = Path("data/key_rotation_state.json")


def generate_secure_key(length: int = 64) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_urlsafe(length)


def load_rotation_state() -> dict:
    """Load rotation state from disk."""
    if ROTATION_STATE_FILE.exists():
        return json.loads(ROTATION_STATE_FILE.read_text())
    return {"rotations": [], "current_keys": {}}


def save_rotation_state(state: dict) -> None:
    """Persist rotation state to disk."""
    ROTATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ROTATION_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def rotate_jwt_secret() -> dict:
    """Rotate JWT secret key with 24-hour grace period.

    Instructions:
    1. Set SECRET_KEY to the new key across backend and collab-server
    2. Set SECRET_KEY_OLD to the previous key for the grace period
    3. After 24 hours, remove SECRET_KEY_OLD everywhere
    """
    new_key = generate_secure_key(48)
    current_key = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")

    state = load_rotation_state()
    rotation_entry = {
        "type": "jwt",
        "rotated_at": datetime.utcnow().isoformat(),
        "grace_expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "old_key_fingerprint": hashlib.sha256(current_key.encode()).hexdigest()[:16],
        "new_key_fingerprint": hashlib.sha256(new_key.encode()).hexdigest()[:16],
    }
    state["rotations"].append(rotation_entry)
    state["current_keys"]["jwt"] = {
        "fingerprint": rotation_entry["new_key_fingerprint"],
        "rotated_at": rotation_entry["rotated_at"],
    }
    save_rotation_state(state)

    return {
        "type": "jwt",
        "new_key": new_key,
        "old_key_fingerprint": rotation_entry["old_key_fingerprint"],
        "new_key_fingerprint": rotation_entry["new_key_fingerprint"],
        "grace_period_hours": 24,
        "instructions": [
            f"1. Set SECRET_KEY={new_key} on backend and collab-server",
            f"2. Set SECRET_KEY_OLD={current_key} on backend and collab-server",
            "3. Restart backend and collab-server so both runtimes accept the grace window",
            "4. After 24 hours, remove SECRET_KEY_OLD from both runtimes",
        ],
    }


def rotate_hmac_key() -> dict:
    """Rotate HMAC audit signing key.

    Adds a new key to the keyring while keeping old keys for verification.
    The active key ID is updated to the new key.
    """
    new_key_id = f"v{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    new_secret = generate_secure_key(48)

    current_keyring = os.environ.get(
        "AUDIENCE_AUDIT_HMAC_KEYS", "v1:dev-audience-audit-signing-key"
    )

    # Append new key to existing keyring
    new_keyring = f"{current_keyring},{new_key_id}:{new_secret}"

    state = load_rotation_state()
    rotation_entry = {
        "type": "hmac",
        "rotated_at": datetime.utcnow().isoformat(),
        "new_key_id": new_key_id,
        "new_key_fingerprint": hashlib.sha256(new_secret.encode()).hexdigest()[:16],
    }
    state["rotations"].append(rotation_entry)
    state["current_keys"]["hmac"] = {
        "active_key_id": new_key_id,
        "fingerprint": rotation_entry["new_key_fingerprint"],
        "rotated_at": rotation_entry["rotated_at"],
    }
    save_rotation_state(state)

    return {
        "type": "hmac",
        "new_key_id": new_key_id,
        "instructions": [
            f"1. Set AUDIENCE_AUDIT_HMAC_KEYS={new_keyring}",
            f"2. Set AUDIENCE_AUDIT_ACTIVE_KEY_ID={new_key_id}",
            "3. Restart the application",
            "4. Old keys remain in keyring for signature verification",
        ],
    }


def show_current_state() -> None:
    """Display current key rotation state."""
    state = load_rotation_state()
    print(json.dumps(state, indent=2))
    if state.get("rotations"):
        last = state["rotations"][-1]
        print(f"\nLast rotation: {last['type']} at {last['rotated_at']}")
    else:
        print("\nNo rotations recorded yet.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate application secret keys")
    parser.add_argument(
        "--type",
        choices=["jwt", "hmac", "all"],
        help="Type of key to rotate",
    )
    parser.add_argument(
        "--show-current",
        action="store_true",
        help="Show current rotation state",
    )
    args = parser.parse_args()

    if args.show_current:
        show_current_state()
        return

    if not args.type:
        parser.print_help()
        sys.exit(1)

    results = []
    if args.type in ("jwt", "all"):
        result = rotate_jwt_secret()
        results.append(result)
        print("=== JWT Key Rotation ===")
        for instruction in result["instructions"]:
            print(f"  {instruction}")
        print()

    if args.type in ("hmac", "all"):
        result = rotate_hmac_key()
        results.append(result)
        print("=== HMAC Key Rotation ===")
        for instruction in result["instructions"]:
            print(f"  {instruction}")
        print()

    print("Rotation state saved to:", ROTATION_STATE_FILE)


if __name__ == "__main__":
    main()
