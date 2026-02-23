"""Attachment service facade composed from focused mixins."""

from __future__ import annotations

import os
import shutil

from app.config import settings

from . import artifacts as _artifacts
from . import common as _common
from . import preview_pdf as _preview_pdf
from . import reader_view as _reader_view
from . import streams as _streams
from . import upload as _upload
from .artifacts import AttachmentServiceArtifactsMixin
from .common import AttachmentServiceCommonMixin, get_storage_backend
from .preview_pdf import AttachmentServicePreviewPdfMixin
from .reader_view import AttachmentServiceReaderViewMixin
from .streams import AttachmentServiceStreamsMixin
from .upload import AttachmentServiceUploadMixin


class AttachmentService(
    AttachmentServiceUploadMixin,
    AttachmentServicePreviewPdfMixin,
    AttachmentServiceReaderViewMixin,
    AttachmentServiceStreamsMixin,
    AttachmentServiceArtifactsMixin,
    AttachmentServiceCommonMixin,
):
    """Facade preserving the historical AttachmentService API."""


for _module in (_common, _upload, _preview_pdf, _artifacts, _reader_view, _streams):
    _module.AttachmentService = AttachmentService


__all__ = ["AttachmentService", "get_storage_backend", "settings", "os", "shutil"]

