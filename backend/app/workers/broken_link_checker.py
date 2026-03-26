"""Standalone worker for broken link detection.

Run:
  python -m app.workers.broken_link_checker
  python -m app.workers.broken_link_checker --once
"""

from __future__ import annotations

import argparse
import logging

from app.db import SessionLocal, init_db
from app.jobs.runtime import AsyncJobBatchReport, run_polling_worker
from app.services.broken_link_service import scan_broken_links

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

WORKER_NAME = "broken-link-checker"


def process_batch(batch_size: int) -> AsyncJobBatchReport:
    report = AsyncJobBatchReport(worker_name=WORKER_NAME)
    report.attempted = 1
    db = SessionLocal()
    try:
        broken_count = scan_broken_links(db, batch_size=batch_size)
        report.completed = 1
        if broken_count > 0:
            logger.info("Found %d broken links", broken_count)
    except Exception:  # policy: LOSSY — worker loop records failure and continues polling
        logger.exception("Broken link scan failed")
        report.dead_lettered = 1
    finally:
        db.close()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run broken link checker worker")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3600.0,
        help="Polling interval in seconds (default: 1 hour)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum documents to scan per iteration",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one scan and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()
    run_polling_worker(
        worker_name=WORKER_NAME,
        logger=logger,
        process_batch=process_batch,
        poll_interval_seconds=args.poll_interval,
        batch_size=args.batch_size,
        once=args.once,
    )


if __name__ == "__main__":
    main()
