"""Shared runtime loop and observability report for async job workers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class AsyncJobBatchReport:
    """Worker-batch execution counters for operational visibility."""

    worker_name: str
    attempted: int = 0
    completed: int = 0
    retried: int = 0
    dead_lettered: int = 0
    skipped: int = 0
    recovered: int = 0

    @property
    def has_activity(self) -> bool:
        return any(
            (
                self.attempted > 0,
                self.completed > 0,
                self.retried > 0,
                self.dead_lettered > 0,
                self.skipped > 0,
                self.recovered > 0,
            )
        )


BatchProcessor = Callable[[int], AsyncJobBatchReport]


def run_polling_worker(
    *,
    worker_name: str,
    logger: logging.Logger,
    process_batch: BatchProcessor,
    poll_interval_seconds: float,
    batch_size: int,
    once: bool = False,
) -> None:
    """Run a polling worker loop using a shared batch report contract."""
    logger.info(
        "Starting %s worker (poll=%ss batch=%s once=%s)",
        worker_name,
        poll_interval_seconds,
        batch_size,
        once,
    )

    while True:
        report = process_batch(max(1, int(batch_size)))
        if report.has_activity:
            logger.info(
                "%s batch attempted=%s completed=%s retried=%s dead_lettered=%s skipped=%s recovered=%s",
                report.worker_name,
                report.attempted,
                report.completed,
                report.retried,
                report.dead_lettered,
                report.skipped,
                report.recovered,
            )

        if once:
            return

        if not report.has_activity:
            time.sleep(max(0.5, float(poll_interval_seconds)))
