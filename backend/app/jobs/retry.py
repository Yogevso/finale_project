"""Shared retry policy and DLQ decision helpers for async job workers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


class AsyncJobDisposition(str, Enum):
    """Normalized async-job outcome categories."""

    COMPLETED = "completed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry delay policy shared by worker domains."""

    base_delay_seconds: int = 30
    max_delay_seconds: int = 300
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Decision describing next action for a failed async job attempt."""

    disposition: AsyncJobDisposition
    next_delay_seconds: int | None
    reason: str


def compute_retry_delay_seconds(*, attempt_number: int, policy: RetryPolicy) -> int:
    """Compute exponential-backoff delay for a retry attempt number (1-based)."""
    bounded_attempt = max(1, int(attempt_number))
    base = max(0, int(policy.base_delay_seconds))
    cap = max(base, int(policy.max_delay_seconds))
    multiplier = max(1.0, float(policy.backoff_multiplier))
    jitter_ratio = max(0.0, float(policy.jitter_ratio))

    delay = base * (multiplier ** (bounded_attempt - 1))
    if delay > 0 and jitter_ratio > 0:
        jitter_window = delay * jitter_ratio
        delay += random.uniform(-jitter_window, jitter_window)

    bounded_delay = int(round(delay))
    return min(cap, max(0, bounded_delay))


def evaluate_retry(
    *,
    attempts: int,
    max_attempts: int,
    error: str,
    policy: RetryPolicy,
) -> RetryDecision:
    """Resolve whether a failed attempt should retry or transition to DLQ."""
    normalized_error = (error or "").strip().lower()
    bounded_attempts = max(0, int(attempts))
    bounded_max = max(1, int(max_attempts))

    if "poison" in normalized_error:
        return RetryDecision(
            disposition=AsyncJobDisposition.DEAD_LETTER,
            next_delay_seconds=None,
            reason="poison_message_detected",
        )

    if bounded_attempts >= bounded_max:
        return RetryDecision(
            disposition=AsyncJobDisposition.DEAD_LETTER,
            next_delay_seconds=None,
            reason=f"attempt_limit_reached({bounded_attempts}/{bounded_max})",
        )

    return RetryDecision(
        disposition=AsyncJobDisposition.RETRY,
        next_delay_seconds=compute_retry_delay_seconds(
            attempt_number=max(1, bounded_attempts),
            policy=policy,
        ),
        reason=f"retry_scheduled({bounded_attempts}/{bounded_max})",
    )
