"""Fault-injection resilience coverage for infrastructure adapters."""

from __future__ import annotations

import io

import pytest

from app.infrastructure.adapters.collaboration import SqlAlchemyCollaborationStateAdapter
from app.infrastructure.adapters.email import SmtpEmailAdapter
from app.infrastructure.adapters.storage import StorageBackendAdapter
from app.models import Document


class _TimeoutEmailService:
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        _ = (to_email, subject, html_content, text_content)
        raise TimeoutError("SMTP timeout")


class _BooleanEmailService:
    def __init__(self, *, result: bool):
        self._result = result

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        _ = (to_email, subject, html_content, text_content)
        return self._result


class _RaisingStorageBackend:
    def upload(self, file_data, filename: str, content_type: str) -> str:
        _ = (content_type,)
        return f"{filename}:{len(file_data.read())}"

    def download(self, storage_key: str) -> bytes:
        return storage_key.encode("utf-8")

    def delete(self, storage_key: str) -> bool:
        raise TimeoutError(f"Delete timeout for {storage_key}")

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return f"https://storage.example/{storage_key}?exp={expires_in}"

    def exists(self, storage_key: str) -> bool:
        raise RuntimeError(f"Head check failed for {storage_key}")


@pytest.mark.anyio
async def test_smtp_email_adapter_returns_false_on_transport_timeout():
    adapter = SmtpEmailAdapter(service=_TimeoutEmailService())

    result = await adapter.send_email(
        to_email="ops@example.com",
        subject="Timeout probe",
        html_content="<p>hello</p>",
    )

    assert result is False


@pytest.mark.anyio
async def test_smtp_email_adapter_preserves_underlying_boolean_result():
    success_adapter = SmtpEmailAdapter(service=_BooleanEmailService(result=True))
    failure_adapter = SmtpEmailAdapter(service=_BooleanEmailService(result=False))

    assert await success_adapter.send_email(
        to_email="ok@example.com",
        subject="ok",
        html_content="<p>ok</p>",
    )
    assert (
        await failure_adapter.send_email(
            to_email="fail@example.com",
            subject="fail",
            html_content="<p>fail</p>",
        )
        is False
    )


def test_storage_backend_adapter_falls_back_for_bool_checks_on_backend_failures():
    adapter = StorageBackendAdapter(_RaisingStorageBackend())

    assert adapter.delete("documents/a.docx") is False
    assert adapter.exists("documents/a.docx") is False


def test_storage_backend_adapter_keeps_pass_through_for_core_read_write_methods():
    adapter = StorageBackendAdapter(_RaisingStorageBackend())
    payload = io.BytesIO(b"abc123")

    storage_key = adapter.upload(
        payload,
        "demo.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    downloaded = adapter.download("documents/demo.docx")
    url = adapter.get_url("documents/demo.docx", expires_in=120)

    assert storage_key == "demo.docx:6"
    assert downloaded == b"documents/demo.docx"
    assert url == "https://storage.example/documents/demo.docx?exp=120"


def test_sqlalchemy_collaboration_state_adapter_rolls_back_on_save_commit_failure(
    db,
    test_document,
    monkeypatch,
):
    adapter = SqlAlchemyCollaborationStateAdapter(db)
    original_rollback = db.rollback
    rollback_calls = {"count": 0}

    def _failing_commit() -> None:
        raise TimeoutError("commit timeout")

    def _tracked_rollback() -> None:
        rollback_calls["count"] += 1
        original_rollback()

    monkeypatch.setattr(db, "commit", _failing_commit)
    monkeypatch.setattr(db, "rollback", _tracked_rollback)

    result = adapter.save_document_state(test_document.id, b"\x01\x02")

    assert result is False
    assert rollback_calls["count"] == 1

    db.expire_all()
    reloaded = db.get(Document, test_document.id)
    assert reloaded is not None
    assert reloaded.yjs_state is None


def test_sqlalchemy_collaboration_state_adapter_rolls_back_on_clear_commit_failure(
    db,
    test_document,
    monkeypatch,
):
    test_document.yjs_state = b"\x09\x09"
    db.commit()

    adapter = SqlAlchemyCollaborationStateAdapter(db)
    original_rollback = db.rollback
    rollback_calls = {"count": 0}

    def _failing_commit() -> None:
        raise TimeoutError("commit timeout")

    def _tracked_rollback() -> None:
        rollback_calls["count"] += 1
        original_rollback()

    monkeypatch.setattr(db, "commit", _failing_commit)
    monkeypatch.setattr(db, "rollback", _tracked_rollback)

    result = adapter.clear_document_state(test_document.id)

    assert result is False
    assert rollback_calls["count"] == 1

    db.expire_all()
    reloaded = db.get(Document, test_document.id)
    assert reloaded is not None
    assert reloaded.yjs_state == b"\x09\x09"
