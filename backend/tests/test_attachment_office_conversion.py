import pytest

from app.services import attachment_service
from app.services.attachment_service import AttachmentService


def test_resolve_soffice_binary_finds_macos_bundle_path(monkeypatch):
    expected_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

    monkeypatch.setattr(attachment_service.settings, "LIBREOFFICE_BIN", None, raising=False)
    monkeypatch.setenv("LIBREOFFICE_BIN", "")
    monkeypatch.setenv("SOFFICE_PATH", "")
    monkeypatch.setattr(attachment_service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        attachment_service.os.path,
        "isfile",
        lambda path: path == expected_path,
    )
    monkeypatch.setattr(
        attachment_service.os,
        "access",
        lambda path, _mode: path == expected_path,
    )

    assert AttachmentService._resolve_soffice_binary() == expected_path


def test_convert_office_to_pdf_bytes_word_fallback_without_libreoffice(monkeypatch):
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_soffice_binary",
        staticmethod(lambda: None),
    )
    monkeypatch.setattr(
        "app.utils.document_converter.convert_word_to_html",
        lambda _content: "<h1>Sample</h1><p>Fallback conversion works.</p>",
    )

    output = AttachmentService._convert_office_to_pdf_bytes(
        b"fake-docx-content",
        filename="sample.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert output.startswith(b"%PDF")
    assert len(output) > 100


def test_convert_office_to_pdf_bytes_non_word_still_requires_libreoffice(monkeypatch):
    monkeypatch.setattr(
        AttachmentService,
        "_resolve_soffice_binary",
        staticmethod(lambda: None),
    )

    with pytest.raises(ValueError, match="LibreOffice headless is required for Office conversion"):
        AttachmentService._convert_office_to_pdf_bytes(
            b"fake-xlsx-content",
            filename="sample.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
