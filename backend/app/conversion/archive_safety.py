"""ZIP archive safety guards for OOXML extractors."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass

MAX_OOXML_ARCHIVE_MEMBERS = 4096
MAX_OOXML_TOTAL_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_OOXML_MEMBER_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_OOXML_COMPRESSION_RATIO = 100.0


@dataclass(frozen=True, slots=True)
class ArchiveSafetyLimits:
    """Metadata-based ZIP expansion limits enforced before archive reads."""

    max_members: int = MAX_OOXML_ARCHIVE_MEMBERS
    max_total_uncompressed_bytes: int = MAX_OOXML_TOTAL_UNCOMPRESSED_BYTES
    max_member_uncompressed_bytes: int = MAX_OOXML_MEMBER_UNCOMPRESSED_BYTES
    max_compression_ratio: float = MAX_OOXML_COMPRESSION_RATIO


DEFAULT_OOXML_ARCHIVE_LIMITS = ArchiveSafetyLimits()


class UnsafeArchiveError(ValueError):
    """Raised when ZIP metadata exceeds the allowed extraction envelope."""


def validate_ooxml_zip_archive(
    archive: zipfile.ZipFile,
    *,
    archive_label: str,
    compressed_size_bytes: int | None = None,
    limits: ArchiveSafetyLimits = DEFAULT_OOXML_ARCHIVE_LIMITS,
) -> None:
    """Reject OOXML ZIP archives with suspicious expansion characteristics."""

    file_members = [member for member in archive.infolist() if not member.is_dir()]
    if len(file_members) > limits.max_members:
        raise UnsafeArchiveError(
            f"{archive_label} archive has too many members "
            f"({len(file_members)} > {limits.max_members})"
        )

    total_uncompressed_bytes = 0
    for member in file_members:
        if member.file_size > limits.max_member_uncompressed_bytes:
            raise UnsafeArchiveError(
                f"{archive_label} archive member {member.filename!r} exceeds the per-file "
                f"limit ({member.file_size} > {limits.max_member_uncompressed_bytes})"
            )
        total_uncompressed_bytes += member.file_size
        if total_uncompressed_bytes > limits.max_total_uncompressed_bytes:
            raise UnsafeArchiveError(
                f"{archive_label} archive exceeds the extracted-size limit "
                f"({total_uncompressed_bytes} > {limits.max_total_uncompressed_bytes})"
            )

    effective_compressed_size = compressed_size_bytes
    if effective_compressed_size is None:
        effective_compressed_size = sum(member.compress_size for member in file_members)
    effective_compressed_size = max(1, effective_compressed_size)
    compression_ratio = total_uncompressed_bytes / effective_compressed_size
    if compression_ratio > limits.max_compression_ratio:
        raise UnsafeArchiveError(
            f"{archive_label} archive exceeds the compression ratio limit "
            f"({compression_ratio:.2f} > {limits.max_compression_ratio:.2f})"
        )


__all__ = [
    "ArchiveSafetyLimits",
    "DEFAULT_OOXML_ARCHIVE_LIMITS",
    "MAX_OOXML_ARCHIVE_MEMBERS",
    "MAX_OOXML_COMPRESSION_RATIO",
    "MAX_OOXML_MEMBER_UNCOMPRESSED_BYTES",
    "MAX_OOXML_TOTAL_UNCOMPRESSED_BYTES",
    "UnsafeArchiveError",
    "validate_ooxml_zip_archive",
]
