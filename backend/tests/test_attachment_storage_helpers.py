from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.models import Attachment, AttachmentArtifact, AttachmentConversionJob
from app.services.attachment_service import AttachmentService

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def build_attachment(**overrides) -> Attachment:
    defaults = {
        "id": 1,
        "document_id": 1,
        "filename": "attachment.docx",
        "original_filename": "attachment.docx",
        "file_size": 128,
        "size_bytes": 128,
        "mime_type": DOCX_MIME_TYPE,
        "storage_path": "doc_1/attachment.docx",
        "storage_key": "doc_1/attachment.docx",
        "uploaded_by": 1,
    }
    defaults.update(overrides)
    return Attachment(**defaults)


def persist_attachment(db, test_document, uploaded_by: int, **overrides) -> Attachment:
    attachment = build_attachment(
        document_id=test_document.id,
        uploaded_by=uploaded_by,
        **overrides,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def test_load_original_bytes_reads_from_local_path(tmp_path, monkeypatch):
    local_file = tmp_path / "local.docx"
    local_file.write_bytes(b"local-docx")
    attachment = build_attachment()

    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: str(local_file)),
    )

    assert AttachmentService._load_original_bytes_for_attachment(attachment) == b"local-docx"


def test_load_original_bytes_falls_back_between_storage_refs(caplog, monkeypatch):
    attachment = build_attachment(
        id=7,
        storage_key="doc_1/primary.docx",
        storage_path="doc_1/secondary.docx",
    )
    download_calls: list[str] = []

    class _FakeStorage:
        def download(self, ref: str) -> bytes:
            download_calls.append(ref)
            if ref == "doc_1/primary.docx":
                raise RuntimeError("primary missing")
            return b"secondary-docx"

    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.artifacts.get_storage_backend",
        lambda: _FakeStorage(),
    )

    with caplog.at_level(logging.WARNING):
        content = AttachmentService._load_original_bytes_for_attachment(attachment)

    assert content == b"secondary-docx"
    assert download_calls == ["doc_1/primary.docx", "doc_1/secondary.docx"]
    assert "Failed loading attachment bytes from storage (attachment=7, ref=doc_1/primary.docx)" in caplog.text


def test_load_original_bytes_raises_when_no_source_succeeds(monkeypatch):
    attachment = build_attachment(storage_key=None, storage_path=None)

    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: None),
    )

    with pytest.raises(FileNotFoundError, match="Original attachment bytes not found"):
        AttachmentService._load_original_bytes_for_attachment(attachment)


def test_delete_attachment_rejects_non_admin(db, test_document, test_user):
    attachment = persist_attachment(db, test_document, test_user.id)

    with pytest.raises(Exception) as exc_info:
        AttachmentService.delete_attachment(db, test_document.id, attachment.id, test_user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only admins can delete attachments"


def test_delete_attachment_removes_storage_refs_and_related_rows(
    db, test_document, test_admin, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_admin.id,
        storage_key="attachments/primary.docx",
        storage_path="attachments/original.docx",
    )
    db.add(
        AttachmentArtifact(
            attachment_id=attachment.id,
            kind=AttachmentService.ARTIFACT_KIND_READER_HTML,
            status=AttachmentService.READER_STATUS_READY,
        )
    )
    db.add(
        AttachmentConversionJob(
            attachment_id=attachment.id,
            job_type=AttachmentService.ARTIFACT_KIND_READER_HTML,
            status="pending",
        )
    )
    db.commit()

    deleted_refs: list[str] = []

    class _FakeStorage:
        def delete(self, ref: str) -> bool:
            deleted_refs.append(ref)
            return True

    monkeypatch.setattr(
        "app.services.attachment_service.streams.get_storage_backend",
        lambda: _FakeStorage(),
    )

    AttachmentService.delete_attachment(db, test_document.id, attachment.id, test_admin)

    assert deleted_refs == ["attachments/primary.docx", "attachments/original.docx"]
    assert db.query(Attachment).filter(Attachment.id == attachment.id).first() is None
    assert (
        db.query(AttachmentArtifact)
        .filter(AttachmentArtifact.attachment_id == attachment.id)
        .count()
        == 0
    )
    assert (
        db.query(AttachmentConversionJob)
        .filter(AttachmentConversionJob.attachment_id == attachment.id)
        .count()
        == 0
    )


def test_delete_attachment_falls_back_to_local_remove_when_storage_delete_fails(
    db, test_document, test_admin, tmp_path, monkeypatch
):
    local_file = tmp_path / "delete-me.docx"
    local_file.write_bytes(b"delete me")
    attachment = persist_attachment(
        db,
        test_document,
        test_admin.id,
        storage_key="broken/storage-key.docx",
        storage_path=str(local_file),
    )

    class _BrokenStorage:
        def delete(self, _ref: str) -> bool:
            raise RuntimeError("storage offline")

    monkeypatch.setattr(
        "app.services.attachment_service.streams.get_storage_backend",
        lambda: _BrokenStorage(),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: str(local_file)),
    )

    AttachmentService.delete_attachment(db, test_document.id, attachment.id, test_admin)

    assert not local_file.exists()
    assert db.query(Attachment).filter(Attachment.id == attachment.id).first() is None


def test_get_file_path_returns_local_metadata_tuple(tmp_path, monkeypatch):
    local_file = tmp_path / "download.docx"
    local_file.write_bytes(b"download")
    attachment = build_attachment(
        original_filename="download.docx",
        mime_type=DOCX_MIME_TYPE,
    )

    monkeypatch.setattr(
        AttachmentService,
        "get_attachment",
        staticmethod(lambda *_args, **_kwargs: attachment),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: str(local_file)),
    )

    path, filename, mime_type = AttachmentService.get_file_path(None, 1, 1, None)

    assert Path(path) == local_file
    assert filename == "download.docx"
    assert mime_type == DOCX_MIME_TYPE


def test_get_file_path_raises_404_when_local_file_missing(monkeypatch):
    attachment = build_attachment(
        id=9,
        storage_key="missing/storage-key.docx",
        storage_path="missing/storage-path.docx",
    )

    monkeypatch.setattr(
        AttachmentService,
        "get_attachment",
        staticmethod(lambda *_args, **_kwargs: attachment),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: None),
    )

    with pytest.raises(Exception) as exc_info:
        AttachmentService.get_file_path(None, 1, attachment.id, None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "File not found on disk"


def test_open_original_stream_prefers_local_file(tmp_path, monkeypatch):
    local_file = tmp_path / "stream.docx"
    local_file.write_bytes(b"stream-local")
    attachment = build_attachment()

    monkeypatch.setattr(
        AttachmentService,
        "get_attachment",
        staticmethod(lambda *_args, **_kwargs: attachment),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: str(local_file)),
    )

    returned_attachment, stream = AttachmentService.open_original_stream(None, 1, 1, None)

    assert returned_attachment is attachment
    assert b"".join(stream) == b"stream-local"


def test_open_original_stream_falls_back_to_storage_download(caplog, monkeypatch):
    attachment = build_attachment(
        id=12,
        storage_key="missing-primary.docx",
        storage_path="secondary.docx",
    )
    download_calls: list[str] = []

    class _FakeStorage:
        def download(self, ref: str) -> bytes:
            download_calls.append(ref)
            if ref == "missing-primary.docx":
                raise RuntimeError("missing")
            return b"storage-bytes"

    monkeypatch.setattr(
        AttachmentService,
        "get_attachment",
        staticmethod(lambda *_args, **_kwargs: attachment),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.streams.get_storage_backend",
        lambda: _FakeStorage(),
    )

    with caplog.at_level(logging.WARNING):
        returned_attachment, stream = AttachmentService.open_original_stream(None, 1, 12, None)

    assert returned_attachment is attachment
    assert b"".join(stream) == b"storage-bytes"
    assert download_calls == ["missing-primary.docx", "secondary.docx"]
    assert "Storage download failed for attachment 12 (ref=missing-primary.docx)" in caplog.text


def test_open_original_stream_raises_404_when_storage_downloads_fail(monkeypatch):
    attachment = build_attachment(
        id=15,
        storage_key="missing-primary.docx",
        storage_path="missing-secondary.docx",
    )

    class _BrokenStorage:
        def download(self, _ref: str) -> bytes:
            raise RuntimeError("still missing")

    monkeypatch.setattr(
        AttachmentService,
        "get_attachment",
        staticmethod(lambda *_args, **_kwargs: attachment),
    )
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_local_attachment_path",
        staticmethod(lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.streams.get_storage_backend",
        lambda: _BrokenStorage(),
    )

    with pytest.raises(Exception) as exc_info:
        AttachmentService.open_original_stream(None, 1, 15, None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Original file not found in storage"
