"""Document chunker — splits HTML content into overlapping text chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from io import StringIO

from app.config import settings


@dataclass
class Chunk:
    """A single chunk of document text with metadata."""

    text: str
    chunk_index: int
    section: str | None = None
    char_start: int = 0
    char_end: int = 0


class _HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and extract plain text with section headings."""

    def __init__(self) -> None:
        super().__init__()
        self._text = StringIO()
        self._sections: list[tuple[str, int]] = []  # (heading_text, char_offset)
        self._in_heading = False
        self._heading_text = ""
        self._skip_tags = {"script", "style", "head"}
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._skip_tags:
            self._skip_depth += 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = True
            self._heading_text = ""
        elif tag == "br":
            self._text.write("\n")
        elif tag in ("p", "div", "li", "tr", "blockquote"):
            self._text.write("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = False
            heading = self._heading_text.strip()
            if heading:
                offset = self._text.tell()
                self._sections.append((heading, offset))
                self._text.write(f"\n{heading}\n")
        elif tag in ("p", "div", "ul", "ol", "table"):
            self._text.write("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        # Skip base64 data fragments that may leak from malformed HTML
        if len(data) > 200 and re.match(r"^[A-Za-z0-9+/=\s]+$", data[:200]):
            return
        if self._in_heading:
            self._heading_text += data
        self._text.write(data)

    def get_text(self) -> str:
        return self._text.getvalue()

    def get_sections(self) -> list[tuple[str, int]]:
        return self._sections


class DocumentChunker:
    """Split document HTML content into overlapping text chunks."""

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self._chunk_size = chunk_size or settings.ASSISTANT_CHUNK_SIZE
        self._overlap = overlap or settings.ASSISTANT_CHUNK_OVERLAP

    def chunk_html(self, html_content: str) -> list[Chunk]:
        """Parse HTML, extract text, and split into overlapping chunks."""
        if not html_content or not html_content.strip():
            return []

        text = self.strip_html(html_content)
        if not text.strip():
            return []

        sections = self._extract_sections(html_content)
        return self._split_into_chunks(text, sections)

    def chunk_text(self, plain_text: str) -> list[Chunk]:
        """Split plain text into overlapping chunks (no HTML parsing)."""
        if not plain_text or not plain_text.strip():
            return []
        return self._split_into_chunks(plain_text, [])

    @staticmethod
    def strip_html(html: str) -> str:
        """Remove HTML tags and return plain text."""
        extractor = _HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        # Collapse multiple whitespace/newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def _extract_sections(html: str) -> list[tuple[str, int]]:
        """Extract section headings with their character offsets."""
        extractor = _HTMLTextExtractor()
        extractor.feed(html)
        return extractor.get_sections()

    def _split_into_chunks(
        self,
        text: str,
        sections: list[tuple[str, int]],
    ) -> list[Chunk]:
        """Split text into chunks at sentence boundaries with overlap."""
        # Approximate tokens as chars / 4
        chars_per_chunk = self._chunk_size * 4
        chars_overlap = self._overlap * 4

        if len(text) <= chars_per_chunk:
            section = sections[0][0] if sections else None
            return [
                Chunk(text=text, chunk_index=0, section=section, char_start=0, char_end=len(text))
            ]

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[Chunk] = []
        current_text = ""
        current_start = 0
        char_pos = 0

        for sentence in sentences:
            if current_text and len(current_text) + len(sentence) + 1 > chars_per_chunk:
                # Find which section this chunk belongs to
                section = self._find_section(current_start, sections)
                chunks.append(
                    Chunk(
                        text=current_text.strip(),
                        chunk_index=len(chunks),
                        section=section,
                        char_start=current_start,
                        char_end=current_start + len(current_text),
                    )
                )
                # Overlap: keep last chars_overlap characters
                if chars_overlap > 0 and len(current_text) > chars_overlap:
                    overlap_text = current_text[-chars_overlap:]
                    current_start = current_start + len(current_text) - chars_overlap
                    current_text = overlap_text
                else:
                    current_start = char_pos
                    current_text = ""

            if current_text:
                current_text += " " + sentence
            else:
                current_text = sentence
            char_pos += len(sentence) + 1

        # Last chunk
        if current_text.strip():
            section = self._find_section(current_start, sections)
            chunks.append(
                Chunk(
                    text=current_text.strip(),
                    chunk_index=len(chunks),
                    section=section,
                    char_start=current_start,
                    char_end=current_start + len(current_text),
                )
            )

        return chunks

    @staticmethod
    def _find_section(
        char_offset: int,
        sections: list[tuple[str, int]],
    ) -> str | None:
        """Find the section heading that covers the given character offset."""
        current_section = None
        for heading, offset in sections:
            if offset <= char_offset:
                current_section = heading
            else:
                break
        return current_section
