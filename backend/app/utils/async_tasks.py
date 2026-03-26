"""Helpers for scheduling async coroutines from sync or async code paths."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Awaitable

logger = logging.getLogger(__name__)


def run_async_task(coro: Awaitable[object]) -> None:
    """Schedule a coroutine safely from either sync or async contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        thread = threading.Thread(
            target=lambda: _run_in_new_loop(coro),
            daemon=True,
        )
        thread.start()
        return

    loop.create_task(coro)


def _run_in_new_loop(coro: Awaitable[object]) -> None:
    try:
        asyncio.run(coro)
    except Exception:  # policy: LOSSY — detached background task failure must stay off the caller path; pragma: no cover - defensive logging path
        logger.exception("Background async task failed")
