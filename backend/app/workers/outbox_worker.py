"""Standalone worker process for persisted domain-event outbox.

Run:
  python -m app.workers.outbox_worker
"""

from __future__ import annotations

import argparse
import logging

from app.db import init_db
from app.services.outbox import run_outbox_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run domain-event outbox worker")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds when no pending events are found",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of outbox records to process per iteration",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=30,
        help="Retry delay in seconds for failed event deliveries",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one batch and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()
    run_outbox_worker(
        poll_interval_seconds=args.poll_interval,
        batch_size=args.batch_size,
        retry_delay_seconds=args.retry_delay,
        once=args.once,
    )


if __name__ == "__main__":
    main()
