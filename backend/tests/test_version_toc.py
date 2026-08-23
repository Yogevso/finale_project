"""Tests for storing a version's contents beside its HTML.

convert_document_to_html returns a string, so by the time a version row is
written the structure the source declared is gone. build_version_toc reads it
back from the same bytes, and must never fail an upload when a document simply
declares nothing.
"""

from __future__ import annotations

import datetime
import json

from app.conversion import version_toc
from app.conversion.version_toc import build_version_toc
from app.models import Version, VersionBumpType
from app.schemas import VersionResponse

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"


def test_the_format_is_resolved_by_mime_type_or_extension(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(version_toc, "_docx_toc", lambda content: seen.append("docx") or [])
    monkeypatch.setattr(version_toc, "_pdf_toc", lambda content: seen.append("pdf") or [])

    build_version_toc(b"x", DOCX_MIME, "a.bin")
    build_version_toc(b"x", "application/octet-stream", "a.docx")
    build_version_toc(b"x", PDF_MIME, "a.bin")
    build_version_toc(b"x", "application/octet-stream", "a.PDF")

    assert seen == ["docx", "docx", "pdf", "pdf"]


def test_formats_that_declare_nothing_return_nothing():
    assert build_version_toc(b"plain", "text/plain", "notes.txt") == []
    assert build_version_toc(b"", DOCX_MIME, "empty.docx") == []


def test_a_broken_document_never_fails_the_upload():
    """An unreadable file must store no contents rather than raise."""
    assert build_version_toc(b"not a zip archive", DOCX_MIME, "broken.docx") == []
    assert build_version_toc(b"not a pdf", PDF_MIME, "broken.pdf") == []


def test_an_extractor_failure_is_contained(monkeypatch):
    def explode(_content):
        raise RuntimeError("extractor blew up")

    monkeypatch.setattr(version_toc, "_docx_toc", explode)

    assert build_version_toc(b"x", DOCX_MIME, "a.docx") == []


def _version(toc_json: str | None) -> VersionResponse:
    version = Version(
        id=1,
        document_id=1,
        version_number=1,
        content="<h1 id='heading-x'>X</h1>",
        toc_json=toc_json,
        created_by=1,
        is_published=False,
        row_version=1,
        bump_type=VersionBumpType.PATCH,
    )
    version.created_at = datetime.datetime.now()
    return VersionResponse.model_validate(version, from_attributes=True)


def test_stored_contents_are_served_with_their_pages_and_anchors():
    stored = [
        {
            "id": "toc-0",
            "title": "1 Release Kit Summary",
            "level": 1,
            "page": 10,
            "page_start": 10,
            "page_end": None,
            "anchor_id": "heading-release-kit-summary",
        }
    ]

    items = _version(json.dumps(stored)).toc_items

    assert len(items) == 1
    assert items[0].page == 10, "the declared page must survive, not the ordinal"
    assert items[0].anchor_id == "heading-release-kit-summary"


def test_a_version_without_stored_contents_serves_an_empty_list():
    assert _version(None).toc_items == []


def test_malformed_stored_contents_degrade_instead_of_raising():
    assert _version("{not json").toc_items == []
