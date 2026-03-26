"""PDF-to-DOCX converter.

Extracts text, images, and basic structure from a PDF using PyMuPDF (fitz),
then builds a DOCX file via python-docx.  The resulting DOCX bytes are fed
through the existing DocxExtractor pipeline so upstreamed PDFs behave *exactly*
like natively uploaded DOCX files.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

logger = logging.getLogger(__name__)

# Image dimension cap inside the generated DOCX (inches).
_MAX_IMG_WIDTH_IN = 6.0
_MAX_IMG_HEIGHT_IN = 8.0
# Minimum text length to consider a block meaningful.
_MIN_BLOCK_TEXT_LEN = 1
# Font-size threshold: text larger than this (pt) is treated as a heading.
_HEADING_FONT_SIZE_PT = 15.0
_SUBHEADING_FONT_SIZE_PT = 13.0


@dataclass
class _ExtractedBlock:
    """Intermediate representation of a content block from a PDF page."""

    kind: str  # "text" | "image"
    text: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    image_bytes: bytes = b""
    image_ext: str = "png"


@dataclass
class PdfConversionResult:
    """Result of converting a PDF to DOCX bytes."""

    docx_bytes: bytes = b""
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def convert_pdf_to_docx(pdf_bytes: bytes) -> PdfConversionResult:
    """Convert raw PDF bytes into DOCX bytes.

    The generated DOCX preserves:
    - Text paragraphs with basic heading detection (by font size)
    - Embedded images (raster only, capped at page width)
    - Page breaks between PDF pages

    Returns a ``PdfConversionResult`` with the DOCX bytes or an error.
    """
    result = PdfConversionResult()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # policy: FAIL_FAST — invalid PDF input returns a stable conversion error
        result.error = f"Failed to open PDF: {exc}"
        return result

    result.page_count = len(doc)
    if result.page_count == 0:
        result.error = "PDF has no pages"
        doc.close()
        return result

    blocks_by_page: list[list[_ExtractedBlock]] = []
    ocr_enabled = _is_ocr_enabled()

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_blocks: list[_ExtractedBlock] = []

        # --- text blocks via dict extraction ---
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        text_found = False
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    line_text_parts: list[str] = []
                    max_font_size = 0.0
                    has_bold = False
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text.strip():
                            line_text_parts.append(span_text)
                            max_font_size = max(max_font_size, span.get("size", 0))
                            if "bold" in (span.get("font", "") or "").lower():
                                has_bold = True
                    full_text = "".join(line_text_parts).strip()
                    if len(full_text) >= _MIN_BLOCK_TEXT_LEN:
                        text_found = True
                        page_blocks.append(
                            _ExtractedBlock(
                                kind="text",
                                text=full_text,
                                font_size=max_font_size,
                                is_bold=has_bold,
                            )
                        )

        # AH-004: OCR fallback for image-only pages (scanned PDFs)
        if not text_found and ocr_enabled:
            ocr_text = _ocr_page(page, page_idx, result.warnings)
            if ocr_text:
                page_blocks.append(
                    _ExtractedBlock(kind="text", text=ocr_text, font_size=11.0)
                )

        # --- images ---
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image.get("image"):
                    page_blocks.append(
                        _ExtractedBlock(
                            kind="image",
                            image_bytes=base_image["image"],
                            image_ext=base_image.get("ext", "png"),
                        )
                    )
            except Exception as exc:  # policy: LOSSY — image extraction failure should not abort page conversion
                result.warnings.append(f"Page {page_idx + 1}: image extraction failed: {exc}")

        blocks_by_page.append(page_blocks)

    doc.close()

    # --- build DOCX ---
    docx_doc = DocxDocument()
    style = docx_doc.styles["Normal"]
    style.font.size = Pt(11)

    for page_idx, page_blocks in enumerate(blocks_by_page):
        if page_idx > 0:
            docx_doc.add_page_break()

        for blk in page_blocks:
            if blk.kind == "text":
                _add_text_block(docx_doc, blk)
            elif blk.kind == "image":
                _add_image_block(docx_doc, blk, result.warnings, page_idx)

    buf = io.BytesIO()
    docx_doc.save(buf)
    result.docx_bytes = buf.getvalue()
    return result


def _add_text_block(docx_doc: DocxDocument, blk: _ExtractedBlock) -> None:
    """Add a text block as a paragraph with heading detection."""
    if blk.font_size >= _HEADING_FONT_SIZE_PT:
        para = docx_doc.add_heading(blk.text, level=1)
    elif blk.font_size >= _SUBHEADING_FONT_SIZE_PT:
        para = docx_doc.add_heading(blk.text, level=2)
    else:
        para = docx_doc.add_paragraph()
        run = para.add_run(blk.text)
        if blk.is_bold:
            run.bold = True


def _add_image_block(
    docx_doc: DocxDocument,
    blk: _ExtractedBlock,
    warnings: list[str],
    page_idx: int,
) -> None:
    """Embed an image into the DOCX, capping width to page margins."""
    try:
        stream = io.BytesIO(blk.image_bytes)
        para = docx_doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(stream, width=Inches(_MAX_IMG_WIDTH_IN))
    except Exception as exc:  # policy: LOSSY — image embedding failure should not abort page conversion
        warnings.append(f"Page {page_idx + 1}: failed to embed image: {exc}")


# ---------------------------------------------------------------------------
# AH-004: OCR helpers (behind FEATURE_FLAG_PDF_OCR)
# ---------------------------------------------------------------------------

def _is_ocr_enabled() -> bool:
    """Check if OCR is enabled via feature flag."""
    try:
        from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
        return is_backend_feature_enabled(BackendFeatureFlag.PDF_OCR)
    except Exception:  # policy: DEGRADED — OCR feature-flag lookup failure disables OCR safely
        return False


def _ocr_page(page, page_idx: int, warnings: list[str]) -> str:
    """Run OCR on a rendered page image.  Returns extracted text or empty string."""
    try:
        import pytesseract
        from PIL import Image

        _OCR_DPI = 150
        _OCR_MAX_PIXELS = 25_000_000  # ~5000x5000

        pix = page.get_pixmap(dpi=_OCR_DPI)
        if pix.width * pix.height > _OCR_MAX_PIXELS:
            warnings.append(f"Page {page_idx + 1}: OCR skipped, page image too large ({pix.width}x{pix.height})")
            return ""
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        text = pytesseract.image_to_string(img).strip()
        if text:
            logger.info("OCR extracted %d chars from page %d", len(text), page_idx + 1)
        return text
    except ImportError:
        warnings.append(f"Page {page_idx + 1}: pytesseract not installed, OCR skipped")
        return ""
    except Exception as exc:  # policy: LOSSY — OCR failure should not abort the core PDF conversion
        warnings.append(f"Page {page_idx + 1}: OCR failed: {exc}")
        return ""
