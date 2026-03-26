"""Tests for assistant admission control and saturation metrics."""

from __future__ import annotations

import asyncio

import pytest

from app.services.assistant_capacity_service import (
    AssistantCapacityExceeded,
    get_assistant_capacity_service,
)


def test_chat_capacity_records_queue_wait_and_completion(monkeypatch):
    service = get_assistant_capacity_service()
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_CONCURRENT", 1)
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_QUEUE", 1)
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_QUEUE_TIMEOUT_SECONDS", 1.0)

    async def run_case():
        first = await service.acquire("chat")

        async def queued_request():
            permit = await service.acquire("chat")
            await asyncio.sleep(0.02)
            await permit.release()

        task = asyncio.create_task(queued_request())
        await asyncio.sleep(0.05)

        mid_snapshot = service.snapshot()
        assert mid_snapshot.chat.active == 1
        assert mid_snapshot.chat.queued == 1
        assert mid_snapshot.chat.status == "saturated"

        await first.release()
        await asyncio.wait_for(task, timeout=1.0)

        snapshot = service.snapshot()
        assert snapshot.chat.total_admitted == 2
        assert snapshot.chat.total_completed == 2
        assert snapshot.chat.p95_queue_wait_ms > 0.0
        assert snapshot.chat.p95_duration_ms > 0.0

    asyncio.run(run_case())


def test_chat_capacity_rejects_when_queue_is_full(monkeypatch):
    service = get_assistant_capacity_service()
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_CONCURRENT", 1)
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_QUEUE", 0)
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_QUEUE_TIMEOUT_SECONDS", 1.0)

    async def run_case():
        first = await service.acquire("chat")
        with pytest.raises(AssistantCapacityExceeded) as exc_info:
            await service.acquire("chat")
        await first.release()

        assert exc_info.value.lane == "chat"
        assert exc_info.value.reason == "queue_full"

        snapshot = service.snapshot()
        assert snapshot.chat.total_rejected == 1
        assert snapshot.chat.last_rejection_reason == "queue_full"

    asyncio.run(run_case())


def test_embedding_capacity_is_separate_from_chat(monkeypatch):
    service = get_assistant_capacity_service()
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_CONCURRENT", 1)
    monkeypatch.setattr("app.config.settings.ASSISTANT_CHAT_MAX_QUEUE", 0)
    monkeypatch.setattr("app.config.settings.ASSISTANT_EMBEDDING_MAX_CONCURRENT", 1)
    monkeypatch.setattr("app.config.settings.ASSISTANT_EMBEDDING_MAX_QUEUE", 0)

    async def run_case():
        chat = await service.acquire("chat")
        embedding = await service.acquire("embedding")
        snapshot = service.snapshot()

        assert snapshot.chat.active == 1
        assert snapshot.embedding.active == 1
        assert snapshot.total_rejections == 0

        await chat.release()
        await embedding.release()

    asyncio.run(run_case())
