"""Standalone worker process for orphaned assignment reconciliation.

Run:
  python -m app.workers.assignment_reconciler
"""

from __future__ import annotations

import argparse
import logging

from app.db import init_db
from app.services.assignment_reconciler import run_assignment_reconciler_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run assignment reconciliation worker",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds when no orphaned assignments are found",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum orphaned assignment rows to process per iteration",
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
    run_assignment_reconciler_worker(
        poll_interval_seconds=args.poll_interval,
        batch_size=args.batch_size,
        once=args.once,
    )


if __name__ == "__main__":
    main()
