"""Reader-artifact storage tests for structured DOCX/PPTX extraction payloads."""

from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from app.models import Attachment, AttachmentArtifact
from app.services.attachment_service import AttachmentService

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_generate_reader_artifact_stores_structured_payload_for_docx(
    db, test_document, test_user, test_admin, monkeypatch
):
    attachment = Attachment(
        document_id=test_document.id,
        filename="wave-y.docx",
        original_filename="wave-y.docx",
        file_size=128,
        size_bytes=128,
        mime_type=DOCX_MIME_TYPE,
        storage_path="doc_1/wave-y.docx",
        storage_key="doc_1/wave-y.docx",
        uploaded_by=test_user.id,
        reader_html_status=AttachmentService.READER_STATUS_PENDING,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

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

    monkeypatch.setattr("app.services.attachment_service.reader_view.SessionLocal", local_session_factory)
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
