"""
Document Converter Utility

Converts various document types (PDF, Word, etc.) to HTML for editing.
"""

import io
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def convert_pdf_to_html(content: bytes) -> str:
    """
    Convert PDF content to HTML.
    Uses PyMuPDF (fitz) to extract text with formatting.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed")
        return "<p>PDF conversion not available. Please install PyMuPDF.</p>"
    
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        html_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text blocks with positioning info
            blocks = page.get_text("dict")["blocks"]
            
            page_html = []
            current_paragraph = []
            last_y = None
            last_size = None
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            
                            size = span.get("size", 12)
                            flags = span.get("flags", 0)
                            y_pos = span.get("origin", [0, 0])[1]
                            
                            # Detect headings by font size
                            is_heading = size >= 16
                            is_bold = flags & 2 ** 4  # Bold flag
                            is_italic = flags & 2 ** 1  # Italic flag
                            
                            # Check for new paragraph (significant Y change)
                            if last_y is not None and abs(y_pos - last_y) > 20:
                                if current_paragraph:
                                    para_text = " ".join(current_paragraph)
                                    if last_size and last_size >= 18:
                                        page_html.append(f"<h1>{para_text}</h1>")
                                    elif last_size and last_size >= 16:
                                        page_html.append(f"<h2>{para_text}</h2>")
                                    elif last_size and last_size >= 14:
                                        page_html.append(f"<h3>{para_text}</h3>")
                                    else:
                                        page_html.append(f"<p>{para_text}</p>")
                                    current_paragraph = []
                            
                            # Apply formatting
                            formatted_text = text
                            if is_bold:
                                formatted_text = f"<strong>{formatted_text}</strong>"
                            if is_italic:
                                formatted_text = f"<em>{formatted_text}</em>"
                            
                            current_paragraph.append(formatted_text)
                            last_y = y_pos
                            last_size = size
            
            # Flush remaining paragraph
            if current_paragraph:
                para_text = " ".join(current_paragraph)
                if last_size and last_size >= 18:
                    page_html.append(f"<h1>{para_text}</h1>")
                elif last_size and last_size >= 16:
                    page_html.append(f"<h2>{para_text}</h2>")
                elif last_size and last_size >= 14:
                    page_html.append(f"<h3>{para_text}</h3>")
                else:
                    page_html.append(f"<p>{para_text}</p>")
            
            if page_html:
                html_parts.extend(page_html)
                # Add page break marker (optional)
                if page_num < len(doc) - 1:
                    html_parts.append("<hr class='page-break'>")
        
        doc.close()
        
        result = "\n".join(html_parts)
        if not result.strip():
            result = "<p>No text content could be extracted from this PDF.</p>"
        
        return result
        
    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        return f"<p>Error converting PDF: {str(e)}</p>"


def convert_word_to_html(content: bytes) -> str:
    """
    Convert Word document (docx) to HTML.
    Uses mammoth for better HTML conversion.
    """
    try:
        import mammoth
    except ImportError:
        logger.error("mammoth not installed")
        return "<p>Word conversion not available. Please install mammoth.</p>"
    
    try:
        result = mammoth.convert_to_html(io.BytesIO(content))
        html = result.value
        
        # Clean up the HTML a bit
        if not html.strip():
            html = "<p>No content could be extracted from this document.</p>"
        
        return html
        
    except Exception as e:
        logger.error(f"Word conversion error: {e}")
        # Try python-docx as fallback
        return convert_word_to_html_fallback(content)


def convert_word_to_html_fallback(content: bytes) -> str:
    """
    Fallback Word conversion using python-docx.
    """
    try:
        from docx import Document
    except ImportError:
        return "<p>Word conversion not available.</p>"
    
    try:
        doc = Document(io.BytesIO(content))
        html_parts = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # Check for heading styles
            if para.style and para.style.name:
                style = para.style.name.lower()
                if "heading 1" in style:
                    html_parts.append(f"<h1>{text}</h1>")
                elif "heading 2" in style:
                    html_parts.append(f"<h2>{text}</h2>")
                elif "heading 3" in style:
                    html_parts.append(f"<h3>{text}</h3>")
                elif "title" in style:
                    html_parts.append(f"<h1>{text}</h1>")
                else:
                    html_parts.append(f"<p>{text}</p>")
            else:
                html_parts.append(f"<p>{text}</p>")
        
        return "\n".join(html_parts) if html_parts else "<p>No content found.</p>"
        
    except Exception as e:
        logger.error(f"Word fallback conversion error: {e}")
        return f"<p>Error converting Word document: {str(e)}</p>"


def convert_text_to_html(content: bytes) -> str:
    """
    Convert plain text to HTML.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except:
            text = content.decode("utf-8", errors="replace")
    
    # Convert newlines to paragraphs
    paragraphs = text.split("\n\n")
    html_parts = []
    
    for para in paragraphs:
        para = para.strip()
        if para:
            # Escape HTML characters
            para = para.replace("&", "&amp;")
            para = para.replace("<", "&lt;")
            para = para.replace(">", "&gt;")
            # Convert single newlines to <br>
            para = para.replace("\n", "<br>")
            html_parts.append(f"<p>{para}</p>")
    
    return "\n".join(html_parts) if html_parts else "<p>No content.</p>"


def convert_document_to_html(content: bytes, mime_type: str, filename: str = "") -> Optional[str]:
    """
    Convert a document to HTML based on its MIME type.
    
    Returns HTML string or None if conversion is not supported.
    """
    mime_type = mime_type.lower()
    filename = filename.lower()
    
    # PDF
    if mime_type == "application/pdf" or filename.endswith(".pdf"):
        return convert_pdf_to_html(content)
    
    # Word documents
    if mime_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ] or filename.endswith(".docx") or filename.endswith(".doc"):
        return convert_word_to_html(content)
    
    # Plain text
    if mime_type.startswith("text/") or filename.endswith(".txt"):
        return convert_text_to_html(content)
    
    # RTF - treat as text for now
    if mime_type == "application/rtf" or filename.endswith(".rtf"):
        return convert_text_to_html(content)
    
    logger.info(f"No converter for mime_type={mime_type}, filename={filename}")
    return None


__all__ = ["convert_document_to_html", "convert_pdf_to_html", "convert_word_to_html"]
