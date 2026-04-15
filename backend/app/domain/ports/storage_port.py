"""Storage access port."""

from __future__ import annotations

from typing import BinaryIO, Protocol


class StoragePort(Protocol):
    """Abstract storage contract used by application services."""

    def upload(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file and return storage key."""

    def download(self, storage_key: str) -> bytes:
        """Download file by storage key."""

    def delete(self, storage_key: str) -> bool:
        """Delete file by storage key."""

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get signed/temporary access URL."""

    def exists(self, storage_key: str) -> bool:
        """Check if storage key exists."""
