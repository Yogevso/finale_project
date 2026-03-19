"""Cleanup worker for expired sessions, tokens, and stale records.

Purges:
  - UserSession rows that have been revoked OR inactive > SESSION_INACTIVITY_DAYS
  - PasswordReset tokens that are expired AND used (or just expired > 7 days)
  - IdempotencyKeyRecord entries older than 7 days

Run:
  python -m app.workers.cleanup_worker          # one-shot
  python -m app.workers.cleanup_worker --loop   # hourly loop
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timedelta

from app.config import settings
from app.db import SessionLocal
from app.models import IdempotencyKeyRecord, PasswordReset, UserSession

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_DAYS = 7
EXPIRED_RESET_GRACE_DAYS = 7


def purge_expired_sessions(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete revoked sessions and sessions inactive beyond threshold."""
    db = SessionLocal()
    try:
        query = db.query(UserSession).filter(
            (UserSession.revoked_at.isnot(None))
            | (UserSession.last_active_at < cutoff)
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d expired/revoked sessions (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_expired_password_resets(now: datetime, *, dry_run: bool = False) -> int:
    """Delete password reset tokens that are expired and either used or past grace period."""
    db = SessionLocal()
    try:
        grace_cutoff = now - timedelta(days=EXPIRED_RESET_GRACE_DAYS)
        query = db.query(PasswordReset).filter(
            (PasswordReset.expires_at < now)
            & (
                (PasswordReset.used_at.isnot(None))
                | (PasswordReset.expires_at < grace_cutoff)
            )
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d expired password resets (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_stale_idempotency_records(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete idempotency records older than TTL."""
    db = SessionLocal()
    try:
        query = db.query(IdempotencyKeyRecord).filter(
            IdempotencyKeyRecord.created_at < cutoff
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d stale idempotency records (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def run_cleanup(*, dry_run: bool = False) -> dict[str, int]:
    """Execute all cleanup tasks. Returns counts of purged records."""
    now = datetime.utcnow()
    session_cutoff = now - timedelta(days=settings.SESSION_INACTIVITY_DAYS)
    idempotency_cutoff = now - timedelta(days=IDEMPOTENCY_TTL_DAYS)

    return {
        "sessions": purge_expired_sessions(session_cutoff, dry_run=dry_run),
        "password_resets": purge_expired_password_resets(now, dry_run=dry_run),
        "idempotency_records": purge_stale_idempotency_records(idempotency_cutoff, dry_run=dry_run),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(description="Cleanup expired sessions/tokens")
    parser.add_argument("--loop", action="store_true", help="Run hourly in a loop")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't delete")
    parser.add_argument("--interval", type=int, default=3600, help="Loop interval in seconds")
    args = parser.parse_args()

    if args.loop:
        logger.info("Starting cleanup worker loop (interval=%ds)", args.interval)
        while True:
            try:
                result = run_cleanup(dry_run=args.dry_run)
                logger.info("Cleanup complete: %s", result)
            except Exception:
                logger.exception("Cleanup cycle failed")
            time.sleep(args.interval)
    else:
        result = run_cleanup(dry_run=args.dry_run)
        logger.info("Cleanup complete: %s", result)


if __name__ == "__main__":
    main()
