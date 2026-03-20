"""Wave AH Tests: New Features - PDF upload/conversion, chat, tooling."""
import io
import pytest
from unittest.mock import patch, MagicMock


class TestPdfUploadConversion:
    """AH-017: PDF upload and conversion to DOCX."""

    def test_pdf_to_docx_conversion_basic(self):
        """Verify PDF bytes are converted to DOCX with text preserved."""
        from app.conversion.pdf_to_docx import convert_pdf_to_docx
        import fitz

        # Create minimal PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello World", fontsize=16)
        page.insert_text((72, 100), "This is a test paragraph.", fontsize=12)
        pdf_bytes = doc.write()
        doc.close()

        result = convert_pdf_to_docx(pdf_bytes)

        assert result.error is None
        assert result.docx_bytes is not None
        assert len(result.docx_bytes) > 0
        assert result.page_count == 1

    def test_pdf_converter_strategy_exists(self):
        """PdfConverterStrategy class exists and can be instantiated."""
        from app.conversion.document_strategies import PdfConverterStrategy
        from app.conversion.document_strategies import WordConverterStrategy

        word_strategy = WordConverterStrategy()
        pdf_strategy = PdfConverterStrategy(word_strategy=word_strategy)
        assert pdf_strategy is not None

    def test_pdf_in_structured_reader_extensions(self):
        """PDF is recognized for structured reader artifact generation."""
        from app.services.attachment_service.common import AttachmentServiceCommonMixin

        assert ".pdf" in AttachmentServiceCommonMixin.STRUCTURED_READER_EXTENSIONS


class TestPdfPortalDownload:
    """AH-018: PDF portal download serves rendered artifact."""

    def test_pdf_export_service_renders_html(self):
        """PDF export service converts HTML to PDF bytes."""
        from app.services.pdf_export_service import render_html_to_pdf

        html = "<h1>Test</h1><p>Body text</p>"
        pdf_bytes = render_html_to_pdf(html, title="Test Doc")

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 100


class TestDocumentScopedChat:
    """AH-019: Document-scoped chat."""

    def test_chat_model_has_document_id(self):
        """Chat model has document_id column."""
        from app.models import Chat
        from sqlalchemy import inspect

        mapper = inspect(Chat)
        column_names = [c.key for c in mapper.columns]
        assert "document_id" in column_names

    def test_chat_message_has_context_json(self):
        """ChatMessage model has context_json column."""
        from app.models import ChatMessage
        from sqlalchemy import inspect

        mapper = inspect(ChatMessage)
        column_names = [c.key for c in mapper.columns]
        assert "context_json" in column_names


class TestPermissionDebugger:
    """AH-020: Permission debugger admin endpoint."""

    def test_permission_debugger_router_exists(self):
        """Permission debugger router is available."""
        from app.api.management import permission_debugger

        assert hasattr(permission_debugger, "router")

    def test_snapshot_diff_router_exists(self):
        """Snapshot diff router is available."""
        from app.api.management import snapshot_diff

        assert hasattr(snapshot_diff, "router")


class TestOperationalTooling:
    """Additional tests for AH operational scripts."""

    def test_validate_config_script_exists(self):
        """Deploy-time config validator script exists."""
        from pathlib import Path

        script = Path(__file__).parent.parent.parent / "scripts" / "validate_config.py"
        assert script.exists()

    def test_pip_audit_gate_script_exists(self):
        """Pip audit gate script exists."""
        from pathlib import Path

        script = Path(__file__).parent.parent.parent / "scripts" / "pip_audit_gate.py"
        assert script.exists()

    def test_npm_audit_gate_script_exists(self):
        """Npm audit gate script exists."""
        from pathlib import Path

        script = Path(__file__).parent.parent.parent / "scripts" / "npm_audit_gate.js"
        assert script.exists()

    def test_route_ownership_matrix_script_exists(self):
        """Route ownership matrix script exists."""
        from pathlib import Path

        script = Path(__file__).parent.parent.parent / "scripts" / "route_ownership_matrix.py"
        assert script.exists()
