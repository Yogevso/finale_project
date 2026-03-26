"""Assistant endpoint benchmark scenario for the production perf gate."""

from __future__ import annotations

import json
from time import perf_counter

import pytest

from app.config import settings
from app.services.distributed_rate_limit_service import DistributedRateLimitService

BENCHMARK_ITERATIONS = 12


def _percentiles(latencies_ms: list[float]) -> tuple[float, float]:
    ordered = sorted(latencies_ms)
    if not ordered:
        return (0.0, 0.0)

    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 0:
        p50 = (ordered[midpoint - 1] + ordered[midpoint]) / 2
    else:
        p50 = ordered[midpoint]
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return p50, ordered[p95_index]


class _PerfAssistantEngine:
    async def chat(self, **_kwargs):
        yield {"event": "message", "data": {"content": "Alpha"}}
        yield {"event": "message", "data": {"content": "Beta"}}
        yield {"event": "done", "data": {"finish_reason": "stop"}}


@pytest.mark.slow
@pytest.mark.integration
def test_assistant_chat_sse_benchmark(client, system_admin_headers, monkeypatch, record_property):
    """Measure the mocked assistant SSE path so regressions fail loudly in CI."""
    DistributedRateLimitService.reset()
    monkeypatch.setattr(settings, "ASSISTANT_RATE_LIMIT_PER_MINUTE", 10_000)
    monkeypatch.setattr(
        "app.api.management.assistant._build_engine",
        lambda *_args, **_kwargs: _PerfAssistantEngine(),
    )

    samples: list[float] = []
    for _ in range(BENCHMARK_ITERATIONS):
        started_at = perf_counter()
        response = client.post(
            "/api/v1/assistant/chat",
            headers=system_admin_headers,
            json={"message": "Performance gate ping"},
        )
        elapsed_ms = (perf_counter() - started_at) * 1000.0
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "event: message" in response.text
        assert "Alpha" in response.text
        samples.append(elapsed_ms)

    p50, p95 = _percentiles(samples)
    metrics = {
        "assistant_chat_sse": {
            "p50_ms": p50,
            "p95_ms": p95,
            "iterations": BENCHMARK_ITERATIONS,
        }
    }
    record_property("assistant_benchmark_metrics_json", json.dumps(metrics, sort_keys=True))

    assert p50 >= 0.0
    assert p95 >= p50
