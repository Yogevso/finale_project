"""Tests for strangler wrappers around legacy-heavy modules."""

from pathlib import Path

from app.container import build_container
from app.legacy_wrappers import (
    AnalyticsServiceStranglerWrapper,
    DocumentConverterStranglerWrapper,
    get_document_converter_wrapper,
    get_legacy_wrapper_tracker,
)


def _status_map():
    tracker = get_legacy_wrapper_tracker()
    return {status.wrapper_name: status for status in tracker.statuses()}


def test_container_analytics_service_resolves_strangler_wrapper(db):
    container = build_container()

    service = container.analytics_service(db, None)

    assert isinstance(service, AnalyticsServiceStranglerWrapper)


def test_analytics_wrapper_tracks_legacy_call_volume():
    class StubAnalyticsService:
        tenant_ctx = None

        def get_overview(self, date_from, date_to):
            return {"from": date_from, "to": date_to}

    tracker = get_legacy_wrapper_tracker()
    tracker.reset()
    wrapper = AnalyticsServiceStranglerWrapper(StubAnalyticsService())

    payload = wrapper.get_overview("2026-01-01", "2026-01-31")
    assert payload["from"] == "2026-01-01"

    status = _status_map()["analytics_service"]
    assert status.call_volume >= 1
    assert status.migration_completion_percent == 0


def test_document_converter_wrapper_tracks_call_volume(monkeypatch):
    tracker = get_legacy_wrapper_tracker()
    tracker.reset()
    wrapper = get_document_converter_wrapper()

    monkeypatch.setattr(
        "app.utils.document_converter.convert_text_to_html",
        lambda *_args, **_kwargs: "<p>wrapped</p>",
    )

    output = wrapper.convert_document_to_html(b"content", "text/plain", "sample.txt")
    assert output == "<p>wrapped</p>"

    status = _status_map()["document_converter"]
    assert status.call_volume >= 1
    assert status.migration_completion_percent == 0


def test_document_converter_wrapper_tracks_reader_artifact_call_volume(monkeypatch):
    tracker = get_legacy_wrapper_tracker()
    tracker.reset()
    wrapper = get_document_converter_wrapper()

    monkeypatch.setattr(
        "app.conversion.document_pipeline.DocumentConversionPipeline.convert_document_to_reader_artifact",
        lambda _self, *_args, **_kwargs: {"html_content": "<article>wrapped</article>"},
    )

    output = wrapper.convert_document_to_reader_artifact(
        b"content",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "sample.docx",
    )
    assert output == {"html_content": "<article>wrapped</article>"}

    status = _status_map()["document_converter"]
    assert status.call_volume >= 1


def test_document_converter_wrapper_can_use_injected_conversion_service():
    tracker = get_legacy_wrapper_tracker()
    tracker.reset()

    class StubConversionService:
        def convert_word_to_html(self, content):
            return f"word:{content.decode('utf-8')}"

        def convert_document_to_html(self, content, mime_type, filename=""):
            return f"{mime_type}:{filename}:{content.decode('utf-8')}"

        def convert_document_to_reader_artifact(self, content, mime_type, filename=""):
            return {
                "mime_type": mime_type,
                "filename": filename,
                "size": len(content),
            }

        def describe_strategy_capabilities(self):
            return {"stub": ("html", "reader_artifact")}

    wrapper = DocumentConverterStranglerWrapper(StubConversionService())

    assert wrapper.convert_word_to_html(b"hello") == "word:hello"
    assert (
        wrapper.convert_document_to_html(b"body", "text/plain", "note.txt")
        == "text/plain:note.txt:body"
    )
    assert wrapper.convert_document_to_reader_artifact(
        b"abc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "wave.docx",
    ) == {
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename": "wave.docx",
        "size": 3,
    }

    status = _status_map()["document_converter"]
    assert status.call_volume == 3


def test_attachment_service_modules_do_not_import_legacy_converter_directly():
    project_root = Path(__file__).resolve().parents[1]
    target_files = [
        project_root / "app" / "services" / "attachment_service" / "artifacts.py",
        project_root / "app" / "services" / "attachment_service" / "reader_view.py",
        project_root / "app" / "services" / "attachment_service" / "upload.py",
    ]

    for file_path in target_files:
        content = file_path.read_text(encoding="utf-8")
        assert "from app.utils.document_converter import" not in content
