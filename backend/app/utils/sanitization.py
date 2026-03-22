"""Input sanitization utilities for defense-in-depth security."""

from __future__ import annotations

import html
import re
from typing import Optional

import bleach

# Allowed tags for rich-text content (matches frontend htmlSanitizer.ts allowlist)
ALLOWED_TAGS = [
    "a", "article", "b", "blockquote", "br", "caption", "code",
    "col", "colgroup", "del", "details", "div", "em", "figure",
    "figcaption", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
    "i", "img", "li", "ol", "p", "pre", "s", "section", "span",
    "strong", "sub", "summary", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "u", "ul",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "role", "aria-label", "aria-expanded"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "table": ["summary"],
    "th": ["colspan", "rowspan", "scope"],
    "td": ["colspan", "rowspan"],
    "col": ["span", "width"],
    "colgroup": ["span", "width"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]


def strip_dangerous_html_patterns(content: str) -> str:
    """
    Sanitize HTML content using bleach with an explicit allowlist.

    Strips all tags/attributes/protocols not in the allowlists.
    """
    if not content:
        return content

    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def sanitize_html_content(content: Optional[str]) -> Optional[str]:
    """Sanitize HTML content before storage using bleach."""
    if content is None:
        return None

    return strip_dangerous_html_patterns(content)


def escape_html(value: str) -> str:
    """Escape HTML special characters for safe display in non-HTML contexts."""
    return html.escape(value, quote=True)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other issues.
    
    Removes or replaces dangerous characters while preserving the basic filename.
    """
    if not filename:
        return "unnamed"
    
    # Remove path separators and null bytes
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    
    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip(".")
    
    # Remove or replace other dangerous characters
    filename = re.sub(r'[<>:"|?*]', "_", filename)
    
    # Limit length
    if len(filename) > 255:
        # Preserve extension
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_len = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_len] + ("." + ext if ext else "")
    
    return filename or "unnamed"


def validate_storage_reference(storage_ref: str) -> bool:
    """
    Validate a storage reference to prevent path traversal attacks.
    
    Returns True if the reference is safe, False otherwise.
    """
    if not storage_ref:
        return False
    
    # Check for path traversal attempts
    if ".." in storage_ref:
        return False
    
    # Check for absolute paths
    if storage_ref.startswith("/") or storage_ref.startswith("\\"):
        return False
    
    # Check for Windows drive letters
    if len(storage_ref) > 1 and storage_ref[1] == ":":
        return False
    
    # Check for null bytes
    if "\x00" in storage_ref:
        return False
    
    return True
