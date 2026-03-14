"""Input sanitization utilities for defense-in-depth security."""

from __future__ import annotations

import html
import re
from typing import Optional

# Patterns for dangerous HTML content
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\s+on\w+\s*=", re.IGNORECASE)
JAVASCRIPT_URI_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
DATA_URI_PATTERN = re.compile(r"data\s*:[^,]*;base64", re.IGNORECASE)


def strip_dangerous_html_patterns(content: str) -> str:
    """
    Remove dangerous HTML patterns from content.
    
    This is a lightweight sanitizer for defense-in-depth. The frontend
    uses DOMPurify for comprehensive sanitization, but this catches
    obvious attack vectors at the backend layer.
    
    For full HTML sanitization, consider using the 'bleach' library.
    """
    if not content:
        return content
    
    # Remove <script> tags and their content
    content = SCRIPT_PATTERN.sub("", content)
    
    # Remove event handlers (onclick, onerror, etc.)
    content = EVENT_HANDLER_PATTERN.sub(" ", content)
    
    # Remove javascript: URIs
    content = JAVASCRIPT_URI_PATTERN.sub("blocked:", content)
    
    return content


def sanitize_html_content(content: Optional[str]) -> Optional[str]:
    """
    Sanitize HTML content before storage.
    
    This provides a basic security layer. Rich HTML editing should
    use a proper HTML sanitization library like bleach for comprehensive
    protection while preserving legitimate formatting.
    """
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
