"""Scheduled-publish executor worker.

Polls for versions where ``scheduled_publish_at <= now()`` and triggers the
publish flow via :meth:`VersionService.process_scheduled_publishes`.

Run:
  python -m app.workers.scheduled_publish_worker          # one-shot
  python -m app.workers.scheduled_publish_worker --loop   # every 60s
"""

from __future__ import annotations

import argparse
import logging
import time

from app.container import build_container
from app.db import SessionLocal

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_BATCH_SIZE = 10


def run_scheduled_publishes(batch_size: int = DEFAULT_BATCH_SIZE) -> dict:
    """Execute pending scheduled publishes. Returns the publish report."""
    db = SessionLocal()
    try:
        svc = build_container().version_service(db)
        report = svc.process_scheduled_publishes(batch_size=batch_size)
        logger.info(
            "Scheduled publish run: published=%d, failed_validation=%d, errors=%d",
            report.get("published", 0),
            report.get("failed_validation", 0),
            len(report.get("errors", [])),
        )
        return report
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(description="Scheduled-publish executor worker")
    parser.add_argument("--loop", action="store_true", help="Run in a continuous loop")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help="Polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Max versions to process per cycle",
    )
    args = parser.parse_args()

    if args.loop:
        logger.info(
            "Starting scheduled-publish worker loop (interval=%ds, batch=%d)",
            args.interval,
            args.batch_size,
        )
        while True:
            try:
                run_scheduled_publishes(batch_size=args.batch_size)
            except Exception:  # policy: LOSSY — worker loop records failure and continues polling
                logger.exception("Scheduled-publish cycle failed")
            time.sleep(args.interval)
    else:
        report = run_scheduled_publishes(batch_size=args.batch_size)
        logger.info("Report: %s", report)


if __name__ == "__main__":
    main()
