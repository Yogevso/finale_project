"""Artifact byte loading helpers."""

from __future__ import annotations

import logging

from app.models import Attachment

from .common import AttachmentServiceCommonMixin, get_storage_backend

logger = logging.getLogger(__name__)


class AttachmentServiceArtifactsMixin(AttachmentServiceCommonMixin):
    """Storage internals used by reader-artifact flows."""

    @classmethod
    def _load_original_bytes_for_attachment(cls, attachment: Attachment) -> bytes:
        local_path = cls._resolve_local_attachment_path(attachment, attachment.document_id)
        if local_path:
            with open(local_path, "rb") as file_obj:
                return file_obj.read()

        storage_refs = [attachment.storage_key, attachment.storage_path]
        for storage_ref in storage_refs:
            if not storage_ref:
                continue
            try:
                storage = get_storage_backend()
                return storage.download(storage_ref)
            except Exception as exc:
                logger.warning(
                    "Failed loading attachment bytes from storage (attachment=%s, ref=%s): %s",
                    attachment.id,
                    storage_ref,
                    exc,
                )

        raise FileNotFoundError("Original attachment bytes not found")
