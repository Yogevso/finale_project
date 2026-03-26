from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from app.conversion.archive_safety import (
    ArchiveSafetyLimits,
    UnsafeArchiveError,
    validate_ooxml_zip_archive,
)


def _build_zip(entries: dict[str, str | bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_validate_ooxml_zip_archive_rejects_extracted_size_limit():
    archive_bytes = _build_zip(
        {
            "word/document.xml": "<w:document/>",
            "word/chunk-a.txt": "A" * 80,
            "word/chunk-b.txt": "B" * 80,
        }
    )
    limits = ArchiveSafetyLimits(
        max_members=10,
        max_total_uncompressed_bytes=100,
        max_member_uncompressed_bytes=1_000,
        max_compression_ratio=1_000,
    )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        with pytest.raises(UnsafeArchiveError, match="extracted-size limit"):
            validate_ooxml_zip_archive(
                archive,
                archive_label="DOCX",
                compressed_size_bytes=len(archive_bytes),
                limits=limits,
            )


def test_validate_ooxml_zip_archive_rejects_compression_ratio_limit():
    archive_bytes = _build_zip(
        {
            "word/document.xml": "<w:document/>",
            "word/repeated.txt": "A" * 20_000,
        }
    )
    limits = ArchiveSafetyLimits(
        max_members=10,
        max_total_uncompressed_bytes=100_000,
        max_member_uncompressed_bytes=100_000,
        max_compression_ratio=10,
    )

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        with pytest.raises(UnsafeArchiveError, match="compression ratio limit"):
            validate_ooxml_zip_archive(
                archive,
                archive_label="DOCX",
                compressed_size_bytes=len(archive_bytes),
                limits=limits,
            )
