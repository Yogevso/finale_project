"""Tests for shared async-job retry/runtime framework."""

from __future__ import annotations

import logging

from app.jobs import (
    AsyncJobBatchReport,
    AsyncJobDisposition,
    RetryPolicy,
    compute_retry_delay_seconds,
    evaluate_retry,
    run_polling_worker,
)


def test_evaluate_retry_schedules_retry_with_backoff():
    policy = RetryPolicy(base_delay_seconds=10, max_delay_seconds=60, backoff_multiplier=2.0)
    decision = evaluate_retry(
        attempts=2,
        max_attempts=5,
        error="temporary failure",
        policy=policy,
    )
    assert decision.disposition == AsyncJobDisposition.RETRY
    assert decision.next_delay_seconds == 20


def test_evaluate_retry_transitions_to_dead_letter_on_attempt_limit():
    policy = RetryPolicy(base_delay_seconds=10, max_delay_seconds=60, backoff_multiplier=2.0)
    decision = evaluate_retry(
        attempts=5,
        max_attempts=5,
        error="still failing",
        policy=policy,
    )
    assert decision.disposition == AsyncJobDisposition.DEAD_LETTER
    assert decision.next_delay_seconds is None


def test_evaluate_retry_treats_poison_messages_as_dead_letter():
    policy = RetryPolicy(base_delay_seconds=10, max_delay_seconds=60, backoff_multiplier=2.0)
    decision = evaluate_retry(
        attempts=1,
        max_attempts=5,
        error="poison payload shape mismatch",
        policy=policy,
    )
    assert decision.disposition == AsyncJobDisposition.DEAD_LETTER
    assert decision.reason == "poison_message_detected"


def test_compute_retry_delay_applies_configured_jitter(monkeypatch):
    policy = RetryPolicy(
        base_delay_seconds=10,
        max_delay_seconds=60,
        backoff_multiplier=2.0,
        jitter_ratio=0.25,
    )

    monkeypatch.setattr("app.jobs.retry.random.uniform", lambda low, high: high)
    high_delay = compute_retry_delay_seconds(attempt_number=3, policy=policy)
    assert high_delay == 50

    monkeypatch.setattr("app.jobs.retry.random.uniform", lambda low, high: low)
    low_delay = compute_retry_delay_seconds(attempt_number=3, policy=policy)
    assert low_delay == 30


def test_run_polling_worker_once_executes_single_batch():
    calls: list[int] = []

    def process_batch(batch_size: int) -> AsyncJobBatchReport:
        calls.append(batch_size)
        return AsyncJobBatchReport(worker_name="test", attempted=1, completed=1)

    run_polling_worker(
        worker_name="test",
        logger=logging.getLogger("app.tests.jobs"),
        process_batch=process_batch,
        poll_interval_seconds=0.1,
        batch_size=7,
        once=True,
    )

    assert calls == [7]
