"""Broken internal link detection for published documents.

Scans the HTML content of active/published document versions for internal links
(e.g., /portal/documents/123, /api/v1/documents/456) and verifies that the
target documents exist and are accessible.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import List, NamedTuple

from sqlalchemy.orm import Session

from app.models import BrokenLinkReport, Document, DocumentStatus

logger = logging.getLogger(__name__)

# Patterns for internal document links
_INTERNAL_DOC_PATTERNS = [
    re.compile(r"/(?:portal/)?documents/(\d+)"),
    re.compile(r"/api/v\d+/(?:portal/)?documents/(\d+)"),
]


class _ExtractedLink(NamedTuple):
    url: str
    text: str


class _LinkExtractor(HTMLParser):
    """Extract href values and link text from anchor tags."""

    def __init__(self) -> None:
        super().__init__()
        self.links: List[_ExtractedLink] = []
        self._current_href: str | None = None
        self._current_text: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._current_href = href
                self._current_text = ""

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            self.links.append(
                _ExtractedLink(url=self._current_href, text=self._current_text.strip())
            )
            self._current_href = None
            self._current_text = ""


def _extract_links(html: str) -> List[_ExtractedLink]:
    parser = _LinkExtractor()
    parser.feed(html)
    return parser.links


def _extract_document_id(url: str) -> int | None:
    for pattern in _INTERNAL_DOC_PATTERNS:
        match = pattern.search(url)
        if match:
            return int(match.group(1))
    return None


def scan_broken_links(db: Session, *, batch_size: int = 50) -> int:
    """Scan all active documents for broken internal links.

    Clears previous reports and rescans. Returns the number of broken links found.
    """
    # Get all published versions with content
    published_docs = db.query(Document).filter(Document.status == DocumentStatus.ACTIVE).all()

    # Build a set of all active document IDs for fast lookups
    active_doc_ids: set[int] = {d.id for d in published_docs}

    # Also load archived/draft IDs to distinguish "not found" from "not accessible"
    all_doc_ids: set[int] = set(row[0] for row in db.query(Document.id).all())

    # Clear old reports
    db.query(BrokenLinkReport).delete()
    db.flush()

    broken_count = 0
    now = datetime.utcnow()

    for doc in published_docs:
        # Get the latest published version
        published_versions = [v for v in doc.versions if v.is_published]
        if not published_versions:
            continue
        latest_version = max(published_versions, key=lambda v: v.version_number)
        if not latest_version.content:
            continue

        links = _extract_links(latest_version.content)
        for link in links:
            target_id = _extract_document_id(link.url)
            if target_id is None:
                continue  # Not an internal document link

            if target_id == doc.id:
                continue  # Self-link, skip

            if target_id not in all_doc_ids:
                reason = "target_not_found"
            elif target_id not in active_doc_ids:
                reason = "target_not_published"
            else:
                continue  # Link is valid

            db.add(
                BrokenLinkReport(
                    document_id=doc.id,
                    version_id=latest_version.id,
                    broken_url=link.url[:1000],
                    link_text=link.text[:500] if link.text else None,
                    reason=reason,
                    scanned_at=now,
                )
            )
            broken_count += 1

    db.commit()
    logger.info(
        "Broken link scan complete: %d broken links found across %d documents",
        broken_count,
        len(published_docs),
    )
    return broken_count
