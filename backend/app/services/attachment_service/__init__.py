"""Attachment service facade composed from focused mixins."""

from __future__ import annotations

from . import artifacts as _artifacts
from . import common as _common
from . import reader_view as _reader_view
from . import streams as _streams
from . import upload as _upload
from .artifacts import AttachmentServiceArtifactsMixin
from .common import AttachmentServiceCommonMixin, get_storage_backend
from .reader_view import AttachmentServiceReaderViewMixin
from .streams import AttachmentServiceStreamsMixin
from .upload import AttachmentServiceUploadMixin


class AttachmentService(
    AttachmentServiceUploadMixin,
    AttachmentServiceReaderViewMixin,
    AttachmentServiceStreamsMixin,
    AttachmentServiceArtifactsMixin,
    AttachmentServiceCommonMixin,
):
    """Facade preserving the historical AttachmentService API."""


for _module in (_common, _upload, _artifacts, _reader_view, _streams):
    _module.AttachmentService = AttachmentService


__all__ = ["AttachmentService", "get_storage_backend"]
