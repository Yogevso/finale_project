"""Storage adapter for existing storage backend implementations."""

from __future__ import annotations

from typing import BinaryIO

from app.domain.ports import StoragePort
from app.services.storage_service import StorageBackend


class StorageBackendAdapter(StoragePort):
    """Adapter over the current StorageBackend interface."""

    def __init__(self, backend: StorageBackend):
        self._backend = backend

    def upload(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        return self._backend.upload(file_data, filename, content_type)

    def download(self, storage_key: str) -> bytes:
        return self._backend.download(storage_key)

    def delete(self, storage_key: str) -> bool:
        return self._backend.delete(storage_key)

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return self._backend.get_url(storage_key, expires_in)

    def exists(self, storage_key: str) -> bool:
        return self._backend.exists(storage_key)

