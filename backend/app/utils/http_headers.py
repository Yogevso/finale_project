"""Helpers for safe HTTP response headers."""

import re
import unicodedata
from urllib.parse import quote


def _ascii_filename_fallback(filename: str) -> str:
    """Build an ASCII-only filename fallback for Content-Disposition."""
    normalized = unicodedata.normalize("NFKD", filename or "")
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.replace('"', "").replace("\\", "_")
    ascii_name = re.sub(r"[\r\n]+", "", ascii_name)
    ascii_name = re.sub(r"[^\x20-\x7E]+", "", ascii_name).strip()
    return ascii_name or "download"


def build_content_disposition(filename: str, inline: bool = False) -> str:
    """Build RFC 6266 compatible header with UTF-8 name + ASCII fallback."""
    disposition_type = "inline" if inline else "attachment"
    cleaned = (filename or "download").replace("\r", "").replace("\n", "")
    ascii_filename = _ascii_filename_fallback(cleaned)
    utf8_filename = quote(cleaned, safe="")
    return (
        f'{disposition_type}; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{utf8_filename}"
    )
