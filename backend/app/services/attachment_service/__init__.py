"""Attachment service facade composed from focused mixins.

Historically these mixins relied on a module-level ``AttachmentService = None`` placeholder
that this package patched after import. The facade now uses classmethod dispatch, so imports
are safe without post-import mutation and helper calls always resolve through the active class.
"""

from __future__ import annotations

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


__all__ = ["AttachmentService", "get_storage_backend"]
