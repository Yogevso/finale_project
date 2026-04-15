"""Reader-artifact storage tests for structured DOCX/PPTX extraction payloads."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import BackgroundTasks
from sqlalchemy.orm import sessionmaker

from app.models import Attachment, AttachmentArtifact
from app.services.attachment_service import AttachmentService

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def build_attachment(**overrides) -> Attachment:
    defaults = {
        "id": 1,
        "document_id": 1,
        "filename": "wave-y.docx",
        "original_filename": "wave-y.docx",
        "file_size": 128,
        "size_bytes": 128,
        "mime_type": DOCX_MIME_TYPE,
        "storage_path": "doc_1/wave-y.docx",
        "storage_key": "doc_1/wave-y.docx",
        "uploaded_by": 1,
        "reader_html_status": AttachmentService.READER_STATUS_PENDING,
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


def test_generate_docx_reader_artifact_uses_canonical_docx_request(monkeypatch):
    calls = {}

    class _FakeWrapper:
        def convert_document_to_reader_artifact(self, content, mime_type, filename):
            calls["content"] = content
            calls["mime_type"] = mime_type
            calls["filename"] = filename
            return {"status": "ready", "html_content": "<article />"}

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )

    artifact = AttachmentService.generate_docx_reader_artifact(
        b"docx-bytes",
        build_attachment(filename="", original_filename=""),
    )

    assert artifact == {"status": "ready", "html_content": "<article />"}
    assert calls == {
        "content": b"docx-bytes",
        "mime_type": DOCX_MIME_TYPE,
        "filename": "document.docx",
    }


def test_generate_pptx_reader_artifact_uses_canonical_pptx_request(monkeypatch):
    calls = {}

    class _FakeWrapper:
        def convert_document_to_reader_artifact(self, content, mime_type, filename):
            calls["content"] = content
            calls["mime_type"] = mime_type
            calls["filename"] = filename
            return {"status": "ready", "html_content": "<section />"}

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )

    artifact = AttachmentService.generate_pptx_reader_artifact(
        b"pptx-bytes",
        build_attachment(
            filename="slides.pptx",
            original_filename="slides.pptx",
            mime_type=PPTX_MIME_TYPE,
            storage_path="doc_1/slides.pptx",
            storage_key="doc_1/slides.pptx",
        ),
    )

    assert artifact == {"status": "ready", "html_content": "<section />"}
    assert calls == {
        "content": b"pptx-bytes",
        "mime_type": PPTX_MIME_TYPE,
        "filename": "slides.pptx",
    }


def test_schedule_reader_artifact_generation_queues_background_task(monkeypatch):
    tasks = BackgroundTasks()
    enqueue_calls = []

    monkeypatch.setattr(
        AttachmentService,
        "enqueue_conversion",
        staticmethod(
            lambda attachment_id,
            *,
            db=None,
            background_tasks=None,
            force=False: enqueue_calls.append(
                {
                    "attachment_id": attachment_id,
                    "db": db,
                    "background_tasks": background_tasks,
                    "force": force,
                }
            )
        ),
    )

    AttachmentService.schedule_reader_artifact_generation(
        99,
        background_tasks=tasks,
        force=True,
    )

    assert enqueue_calls == [
        {
            "attachment_id": 99,
            "db": None,
            "background_tasks": tasks,
            "force": True,
        }
    ]


def test_schedule_reader_artifact_generation_enqueues_durable_job_without_background_tasks(
    monkeypatch,
):
    enqueue_calls = []

    monkeypatch.setattr(
        AttachmentService,
        "enqueue_conversion",
        staticmethod(
            lambda attachment_id,
            *,
            db=None,
            background_tasks=None,
            force=False: enqueue_calls.append(
                {
                    "attachment_id": attachment_id,
                    "db": db,
                    "background_tasks": background_tasks,
                    "force": force,
                }
            )
        ),
    )

    AttachmentService.schedule_reader_artifact_generation(101, force=False)

    assert enqueue_calls == [
        {
            "attachment_id": 101,
            "db": None,
            "background_tasks": None,
            "force": False,
        }
    ]


def test_reader_payload_helpers_normalize_lists_and_invalid_json(caplog):
    attachment = build_attachment(
        id=8,
        reader_toc_json=json.dumps(
            [
                {
                    "title": "Overview",
                    "level": "2",
                    "page_start": "3",
                    "page_end": "1",
                }
            ]
        ),
    )

    assert AttachmentService._get_stored_reader_payload(attachment) == {
        "toc_items": [
            {
                "title": "Overview",
                "level": "2",
                "page_start": "3",
                "page_end": "1",
            }
        ]
    }
    assert AttachmentService._get_stored_reader_toc_items(attachment) == [
        {
            "id": "toc-0",
            "title": "Overview",
            "level": 2,
            "page": 3,
            "page_start": 3,
            "page_end": 3,
            "anchor_id": "page-3",
        }
    ]

    attachment.reader_toc_json = "{not-json"
    from app.services.attachment_service import reader_view as _rv_mod

    _rv_logger = _rv_mod.logger
    _rv_logger.disabled = False
    _rv_logger.addHandler(caplog.handler)
    _rv_logger.setLevel(logging.WARNING)

    try:
        assert AttachmentService._get_stored_reader_payload(attachment) == {}
    finally:
        _rv_logger.removeHandler(caplog.handler)

    assert "Invalid reader_toc_json for attachment 8" in caplog.text


def test_reader_warning_normalization_skips_incomplete_entries():
    assert AttachmentService._normalize_reader_warnings(
        [
            {"code": "MISSING_IMAGES", "message": "2 images failed", "count": "2"},
            {"code": "BLANK_MESSAGE", "message": ""},
            "noise",
            {"message": "missing code"},
            {"code": "BAD_COUNT", "message": "ignored count", "count": "NaN"},
        ]
    ) == [
        {"code": "MISSING_IMAGES", "message": "2 images failed", "count": 2},
        {"code": "BAD_COUNT", "message": "ignored count", "count": None},
    ]


def test_generate_structured_reader_artifact_dispatches_by_attachment_kind(monkeypatch):
    docx_calls = []
    pptx_calls = []

    monkeypatch.setattr(
        AttachmentService,
        "generate_docx_reader_artifact",
        staticmethod(
            lambda content, attachment: docx_calls.append((content, attachment.id))
            or {"status": "ready"}
        ),
    )
    monkeypatch.setattr(
        AttachmentService,
        "generate_pptx_reader_artifact",
        staticmethod(
            lambda content, attachment: pptx_calls.append((content, attachment.id))
            or {"status": "ready"}
        ),
    )

    docx_attachment = build_attachment(id=11)
    pptx_attachment = build_attachment(
        id=12,
        filename="slides.pptx",
        original_filename="slides.pptx",
        mime_type=PPTX_MIME_TYPE,
        storage_path="doc_1/slides.pptx",
        storage_key="doc_1/slides.pptx",
    )
    unsupported_attachment = build_attachment(
        id=13,
        filename="legacy.bin",
        original_filename="legacy.bin",
        mime_type="application/octet-stream",
        storage_path="doc_1/legacy.bin",
        storage_key="doc_1/legacy.bin",
    )

    assert (
        AttachmentService._generate_structured_reader_artifact(b"docx", docx_attachment)["status"]
        == "ready"
    )
    assert (
        AttachmentService._generate_structured_reader_artifact(b"pptx", pptx_attachment)["status"]
        == "ready"
    )
    assert (
        AttachmentService._generate_structured_reader_artifact(
            b"legacy",
            unsupported_attachment,
        )
        is None
    )

    assert docx_calls == [(b"docx", 11)]
    assert pptx_calls == [(b"pptx", 12)]


def test_map_status_to_response_normalizes_reader_payload():
    attachment = build_attachment(id=7)
    generated_at = datetime(2026, 3, 13, 12, 0, 0)
    reader_artifact = AttachmentArtifact(
        attachment_id=attachment.id,
        kind=AttachmentService.ARTIFACT_KIND_READER_HTML,
        status=AttachmentService.READER_STATUS_READY,
        content_text="<article>Wave Y</article>",
        content_json=json.dumps({"toc_items": []}),
        source="headings",
        error=None,
        generated_at=generated_at,
    )

    response = AttachmentService.map_status_to_response(
        attachment,
        reader_artifact,
        toc_items=[
            {
                "id": "toc-0",
                "title": "Wave Y",
                "level": 1,
                "page": 1,
                "page_start": 1,
                "page_end": None,
                "anchor_id": "heading-wave-y",
            }
        ],
        reader_payload={
            "warnings": [{"code": "MISSING_IMAGES", "message": "1 images failed", "count": "1"}],
            "confidence": "0.97",
        },
    )

    assert response == {
        "attachment_id": 7,
        "status": AttachmentService.READER_STATUS_READY,
        "html_content": "<article>Wave Y</article>",
        "toc_items": [
            {
                "id": "toc-0",
                "title": "Wave Y",
                "level": 1,
                "page": 1,
                "page_start": 1,
                "page_end": None,
                "anchor_id": "heading-wave-y",
            }
        ],
        "toc_source": "headings",
        "warnings": [{"code": "MISSING_IMAGES", "message": "1 images failed", "count": 1}],
        "confidence": 0.97,
        "error": None,
        "generated_at": generated_at,
    }


def test_map_status_to_response_reads_stored_payload_when_not_explicit():
    attachment = build_attachment(
        id=9,
        reader_toc_json=json.dumps(
            {
                "toc_items": [
                    {
                        "title": "Reader section",
                        "level": 1,
                        "page_start": 1,
                        "anchor_id": "reader-section",
                    }
                ],
                "warnings": [{"code": "LOW_CONFIDENCE", "message": "Review suggested"}],
                "confidence": "not-a-number",
            }
        ),
    )
    generated_at = datetime(2026, 3, 13, 13, 0, 0)
    reader_artifact = AttachmentArtifact(
        attachment_id=attachment.id,
        kind=AttachmentService.ARTIFACT_KIND_READER_HTML,
        status=AttachmentService.READER_STATUS_FAILED,
        content_text=None,
        content_json=None,
        source="headings",
        error="Reader failed",
        generated_at=generated_at,
    )

    response = AttachmentService.map_status_to_response(attachment, reader_artifact)

    assert response["toc_items"] == [
        {
            "id": "toc-0",
            "title": "Reader section",
            "level": 1,
            "page": 1,
            "page_start": 1,
            "page_end": None,
            "anchor_id": "reader-section",
        }
    ]
    assert response["warnings"] == [
        {"code": "LOW_CONFIDENCE", "message": "Review suggested", "count": None}
    ]
    assert response["confidence"] is None
    assert response["error"] == "Reader failed"


def test_generate_reader_artifact_stores_structured_payload_for_docx(
    db, test_document, test_user, test_admin, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
    )

    local_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())

    class _FakeWrapper:
        def convert_document_to_reader_artifact(self, *_args, **_kwargs):
            return {
                "status": "ready",
                "html_content": (
                    '<article class="docx-document"><h1 id="heading-wave-y">Wave Y</h1></article>'
                ),
                "toc_items": [
                    {
                        "id": "toc-0",
                        "title": "Wave Y",
                        "level": 1,
                        "page": 1,
                        "page_start": 1,
                        "page_end": None,
                        "anchor_id": "heading-wave-y",
                    }
                ],
                "toc_source": "headings",
                "payload": {
                    "status": "ready",
                    "metadata": {"title": "Wave Y"},
                    "warnings": [],
                    "confidence": 0.97,
                    "element_counts": {"document": 1, "heading": 1},
                    "toc_items": [
                        {
                            "id": "toc-0",
                            "title": "Wave Y",
                            "level": 1,
                            "page": 1,
                            "page_start": 1,
                            "page_end": None,
                            "anchor_id": "heading-wave-y",
                        }
                    ],
                    "ir": {
                        "type": "document",
                        "content": "",
                        "styles": {"classes": ["docx-document"]},
                        "children": [],
                    },
                },
                "error": None,
            }

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.SessionLocal", local_session_factory
    )
    monkeypatch.setattr(
        AttachmentService,
        "_load_original_bytes_for_attachment",
        staticmethod(lambda _attachment: b"docx-bytes"),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )

    AttachmentService.generate_reader_artifact(attachment.id)

    db.expire_all()
    refreshed_attachment = db.query(Attachment).filter(Attachment.id == attachment.id).one()
    reader_artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment.id,
            AttachmentArtifact.kind == AttachmentService.ARTIFACT_KIND_READER_HTML,
        )
        .one()
    )
    payload = json.loads(reader_artifact.content_json)
    reader_view = AttachmentService.get_reader_view(
        db,
        test_document.id,
        attachment.id,
        test_admin,
    )

    assert reader_artifact.status == AttachmentService.READER_STATUS_READY
    assert reader_artifact.content_text == refreshed_attachment.reader_html_content
    assert reader_artifact.source == "headings"
    assert payload["confidence"] == 0.97
    assert payload["element_counts"]["heading"] == 1
    assert payload["toc_items"][0]["anchor_id"] == "heading-wave-y"
    assert json.loads(refreshed_attachment.reader_toc_json)["metadata"]["title"] == "Wave Y"
    assert reader_view["warnings"] == []
    assert reader_view["confidence"] == 0.97


def test_generate_reader_artifact_marks_unsupported_attachment_failed(
    db, test_document, test_user, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
        filename="legacy.bin",
        original_filename="legacy.bin",
        mime_type="application/octet-stream",
        storage_path="doc_1/legacy.bin",
        storage_key="doc_1/legacy.bin",
        reader_html_status=None,
    )
    local_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.SessionLocal",
        local_session_factory,
    )

    AttachmentService.generate_reader_artifact(attachment.id)

    db.expire_all()
    refreshed_attachment = db.query(Attachment).filter(Attachment.id == attachment.id).one()
    reader_artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment.id,
            AttachmentArtifact.kind == AttachmentService.ARTIFACT_KIND_READER_HTML,
        )
        .one()
    )

    assert reader_artifact.status == AttachmentService.READER_STATUS_FAILED
    assert reader_artifact.error == "Reader View is only available for DOCX and PPTX attachments"
    assert refreshed_attachment.reader_html_status == AttachmentService.READER_STATUS_FAILED


def test_generate_reader_artifact_keeps_existing_ready_payload_when_not_forced(
    db, test_document, test_user, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
        reader_html_status=AttachmentService.READER_STATUS_READY,
        reader_html_content="<article>Ready</article>",
        reader_toc_json=json.dumps({"toc_items": []}),
        reader_toc_source="headings",
    )
    local_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.SessionLocal",
        local_session_factory,
    )

    def _unexpected_load(_attachment):
        raise AssertionError("ready attachments should not be regenerated without force")

    monkeypatch.setattr(
        AttachmentService,
        "_load_original_bytes_for_attachment",
        staticmethod(_unexpected_load),
    )

    AttachmentService.generate_reader_artifact(attachment.id)

    db.expire_all()
    refreshed_attachment = db.query(Attachment).filter(Attachment.id == attachment.id).one()
    assert refreshed_attachment.reader_html_status == AttachmentService.READER_STATUS_READY
    assert refreshed_attachment.reader_html_content == "<article>Ready</article>"


def test_generate_reader_artifact_records_converter_failure(
    db, test_document, test_user, monkeypatch
):
    attachment = persist_attachment(db, test_document, test_user.id)
    local_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())

    class _FakeWrapper:
        def convert_document_to_reader_artifact(self, *_args, **_kwargs):
            return {
                "status": "failed",
                "html_content": "",
                "toc_items": [],
                "payload": {},
                "error": "Structured extraction failed",
            }

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.SessionLocal",
        local_session_factory,
    )
    monkeypatch.setattr(
        AttachmentService,
        "_load_original_bytes_for_attachment",
        staticmethod(lambda _attachment: b"docx-bytes"),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )

    AttachmentService.generate_reader_artifact(attachment.id)

    db.expire_all()
    reader_artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment.id,
            AttachmentArtifact.kind == AttachmentService.ARTIFACT_KIND_READER_HTML,
        )
        .one()
    )

    assert reader_artifact.status == AttachmentService.READER_STATUS_FAILED
    assert reader_artifact.error == "Structured extraction failed"
    assert reader_artifact.content_text is None


def test_generate_reader_artifact_does_not_treat_error_like_html_text_as_failure(
    db, test_document, test_user, monkeypatch
):
    attachment = persist_attachment(db, test_document, test_user.id)
    local_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())

    class _FakeWrapper:
        def convert_document_to_reader_artifact(self, *_args, **_kwargs):
            return {
                "status": "ready",
                "html_content": "<article><p>Error converting Word document: example text</p></article>",
                "toc_items": [],
                "payload": {"toc_items": []},
                "error": None,
            }

    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.SessionLocal",
        local_session_factory,
    )
    monkeypatch.setattr(
        AttachmentService,
        "_load_original_bytes_for_attachment",
        staticmethod(lambda _attachment: b"docx-bytes"),
    )
    monkeypatch.setattr(
        "app.services.attachment_service.reader_view.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )

    AttachmentService.generate_reader_artifact(attachment.id)

    db.expire_all()
    reader_artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment.id,
            AttachmentArtifact.kind == AttachmentService.ARTIFACT_KIND_READER_HTML,
        )
        .one()
    )

    assert reader_artifact.status == AttachmentService.READER_STATUS_READY
    assert "Error converting Word document" in reader_artifact.content_text
    assert reader_artifact.error is None


def test_get_reader_view_marks_unsupported_attachments_failed_without_scheduling(
    db, test_document, test_user, test_admin, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
        filename="legacy.bin",
        original_filename="legacy.bin",
        mime_type="application/octet-stream",
        storage_path="doc_1/legacy.bin",
        storage_key="doc_1/legacy.bin",
        reader_html_status=None,
    )
    schedule_calls = []

    monkeypatch.setattr(
        AttachmentService,
        "schedule_reader_artifact_generation",
        staticmethod(lambda *args, **kwargs: schedule_calls.append((args, kwargs))),
    )

    response = AttachmentService.get_reader_view(
        db,
        test_document.id,
        attachment.id,
        test_admin,
    )

    assert response["status"] == AttachmentService.READER_STATUS_FAILED
    assert response["toc_items"] == []
    assert response["error"] == "Reader View is only available for DOCX and PPTX attachments"
    assert schedule_calls == []


def test_get_reader_view_schedules_pending_supported_attachments(
    db, test_document, test_user, test_admin, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
        reader_html_status=AttachmentService.READER_STATUS_PENDING,
        reader_html_content=None,
        reader_toc_json=None,
    )
    schedule_calls = []

    monkeypatch.setattr(
        AttachmentService,
        "schedule_reader_artifact_generation",
        staticmethod(
            lambda attachment_id,
            *,
            db=None,
            background_tasks=None,
            force=False: schedule_calls.append(
                {
                    "attachment_id": attachment_id,
                    "db": db,
                    "background_tasks": background_tasks,
                    "force": force,
                }
            )
        ),
    )

    response = AttachmentService.get_reader_view(
        db,
        test_document.id,
        attachment.id,
        test_admin,
    )

    assert response["status"] == AttachmentService.READER_STATUS_PENDING
    assert schedule_calls == [
        {
            "attachment_id": attachment.id,
            "db": db,
            "background_tasks": None,
            "force": False,
        }
    ]


def test_retry_reader_view_generation_resets_ready_payload_before_rescheduling(
    db, test_document, test_user, test_admin, monkeypatch
):
    attachment = persist_attachment(
        db,
        test_document,
        test_user.id,
        reader_html_status=AttachmentService.READER_STATUS_READY,
        reader_html_content="<article>Ready</article>",
        reader_toc_json=json.dumps({"toc_items": []}),
        reader_toc_source="headings",
        reader_html_error="old error",
        reader_html_generated_at=datetime(2026, 3, 13, 11, 0, 0),
    )
    schedule_calls = []
    background_tasks = BackgroundTasks()

    monkeypatch.setattr(
        AttachmentService,
        "schedule_reader_artifact_generation",
        staticmethod(
            lambda attachment_id,
            *,
            db=None,
            background_tasks=None,
            force=False: schedule_calls.append(
                {
                    "attachment_id": attachment_id,
                    "db": db,
                    "background_tasks": background_tasks,
                    "force": force,
                }
            )
        ),
    )

    response = AttachmentService.retry_reader_view_generation(
        db,
        test_document.id,
        attachment.id,
        test_admin,
        background_tasks=background_tasks,
    )

    db.refresh(attachment)
    assert response["status"] == AttachmentService.READER_STATUS_PENDING
    assert attachment.reader_html_status == AttachmentService.READER_STATUS_PENDING
    assert attachment.reader_html_content is None
    assert attachment.reader_html_error is None
    assert attachment.reader_html_generated_at is None
    assert schedule_calls == [
        {
            "attachment_id": attachment.id,
            "db": db,
            "background_tasks": background_tasks,
            "force": True,
        }
    ]
