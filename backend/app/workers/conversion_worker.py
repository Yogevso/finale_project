"""Standalone worker process for preview PDF conversions.

Run:
  python -m app.workers.conversion_worker
"""

from __future__ import annotations

import argparse
import logging

from app.db import init_db
from app.services.conversion_jobs import run_conversion_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run preview PDF conversion worker")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds when no pending jobs are found",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of pending conversion jobs to process per iteration",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one batch and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even when preview_pdf is already ready",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()
    run_conversion_worker(
        poll_interval_seconds=args.poll_interval,
        batch_size=args.batch_size,
        once=args.once,
        force=args.force,
    )


if __name__ == "__main__":
    main()
