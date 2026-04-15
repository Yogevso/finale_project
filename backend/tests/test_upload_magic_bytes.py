"""FIX-005c: End-to-end upload validation tests proving mismatched magic bytes are rejected.

These tests call the actual POST /documents/{id}/attachments endpoint (not
internal helpers) so every layer of validation runs – mime checks, extension
allow-list, and AD-017 magic-byte verification.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
PNG_MIME = "image/png"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"


def _fixture_bytes(name: str = "wave_y_empty.docx") -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


# ── Real DOCX bytes labeled DOCX → should 201 ───────────────────────────
class TestUploadMagicBytesAccept:
    def test_valid_docx_accepted(self, client: TestClient, auth_headers: dict, test_document):
        """A proper .docx file (ZIP/PK header) passes magic-byte guard."""
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("report.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME)},
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == "report.docx"

    def test_valid_pdf_accepted(self, client: TestClient, auth_headers: dict, test_document):
        """Minimal valid PDF passes magic-byte guard."""
        pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 0\ntrailer<</Root 1 0 R>>\nstartxref\n0\n%%EOF"
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("manual.pdf", io.BytesIO(pdf), PDF_MIME)},
        )
        assert resp.status_code == 201

    def test_valid_png_accepted(self, client: TestClient, auth_headers: dict, test_document):
        """Minimal PNG header passes magic-byte guard."""
        # Minimal valid 1×1 PNG
        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("screenshot.png", io.BytesIO(png), PNG_MIME)},
        )
        assert resp.status_code == 201


# ── Mismatched content → should 400 ─────────────────────────────────────
class TestUploadMagicBytesReject:
    def test_exe_renamed_to_docx_rejected(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """An EXE (MZ header) renamed to .docx must be caught by magic-byte check."""
        exe_bytes = b"MZ\x90\x00" + b"\x00" * 100  # PE stub header
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("payload.docx", io.BytesIO(exe_bytes), DOCX_MIME)},
        )
        assert resp.status_code == 400
        assert "does not match extension" in resp.json()["detail"]

    def test_png_data_as_pdf_rejected(self, client: TestClient, auth_headers: dict, test_document):
        """PNG bytes served as .pdf must be rejected."""
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("photo.pdf", io.BytesIO(png_header), PDF_MIME)},
        )
        assert resp.status_code == 400
        assert "does not match extension" in resp.json()["detail"]

    def test_random_bytes_as_docx_rejected(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Random bytes named .docx must be rejected (no PK header)."""
        garbage = bytes(range(256)) * 4  # 1 KB of sequential bytes
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("report.docx", io.BytesIO(garbage), DOCX_MIME)},
        )
        assert resp.status_code == 400

    def test_pdf_header_as_docx_rejected(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """PDF content named .docx must be rejected (%PDF != PK header)."""
        pdf = b"%PDF-1.4\n%EOF"
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("sneaky.docx", io.BytesIO(pdf), DOCX_MIME)},
        )
        assert resp.status_code == 400
        assert "does not match extension" in resp.json()["detail"]

    def test_too_small_file_rejected(self, client: TestClient, auth_headers: dict, test_document):
        """A file under 4 bytes named as a binary format must be rejected."""
        tiny = b"AB"
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("small.png", io.BytesIO(tiny), PNG_MIME)},
        )
        assert resp.status_code == 400
        assert "too small" in resp.json()["detail"].lower()

    def test_docx_bytes_as_png_rejected(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Real DOCX bytes (PK\\x03\\x04) labeled as .png must be rejected."""
        docx_bytes = _fixture_bytes()
        resp = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("tricky.png", io.BytesIO(docx_bytes), PNG_MIME)},
        )
        assert resp.status_code == 400
        assert "does not match extension" in resp.json()["detail"]
