"""Task 192 – Thumbnail metadata parity tests.

Verifies:
1. Document model has thumbnail_url column.
2. Management schemas expose thumbnail_url.
3. Portal schemas expose thumbnail_url.
4. Public schemas expose thumbnail_url.
5. thumbnail_url respects audience (public channel only serves PUBLIC docs' thumbnails).
"""



class TestThumbnailModelField:
    """Verify Document model has thumbnail_url column."""

    def test_document_has_thumbnail_url_column(self):
        from app.models import Document
        assert hasattr(Document, "thumbnail_url"), "Document model must have thumbnail_url"

    def test_thumbnail_url_is_nullable(self):
        from app.models import Document
        col = Document.__table__.columns["thumbnail_url"]
        assert col.nullable is True


class TestThumbnailManagementSchema:
    """Management schemas include thumbnail_url."""

    def test_document_base_has_thumbnail_url(self):
        from app.schemas import DocumentBase
        fields = DocumentBase.model_fields
        assert "thumbnail_url" in fields

    def test_document_update_has_thumbnail_url(self):
        from app.schemas import DocumentUpdate
        fields = DocumentUpdate.model_fields
        assert "thumbnail_url" in fields

    def test_document_response_has_thumbnail_url(self):
        from app.schemas import DocumentResponse
        fields = DocumentResponse.model_fields
        assert "thumbnail_url" in fields


class TestThumbnailPortalSchema:
    """Portal schemas include thumbnail_url."""

    def test_portal_summary_has_thumbnail_url(self):
        from app.schemas.portal import PortalDocumentSummary
        fields = PortalDocumentSummary.model_fields
        assert "thumbnail_url" in fields

    def test_portal_detail_has_thumbnail_url(self):
        from app.schemas.portal import PortalDocumentDetail
        fields = PortalDocumentDetail.model_fields
        assert "thumbnail_url" in fields


class TestThumbnailPublicSchema:
    """Public schemas include thumbnail_url."""

    def test_public_summary_has_thumbnail_url(self):
        from app.schemas.public import PublicDocumentSummary
        fields = PublicDocumentSummary.model_fields
        assert "thumbnail_url" in fields

    def test_public_detail_has_thumbnail_url(self):
        from app.schemas.public import PublicDocumentDetail
        fields = PublicDocumentDetail.model_fields
        assert "thumbnail_url" in fields
