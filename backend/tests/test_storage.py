"""Tests for Storage Service"""
import io
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.storage_service import (
    LocalStorageBackend,
    StorageBackend,
    get_storage_backend,
)
from app.config import settings


class TestLocalStorageBackend:
    """Test local file storage backend"""

    def test_upload_file(self, tmp_path):
        """Test uploading a file to local storage"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        content = b"Test file content"
        file_data = io.BytesIO(content)
        
        storage_key = storage.upload(file_data, "test.txt", "text/plain")
        
        assert storage_key is not None
        assert storage_key.endswith(".txt")

    def test_download_file(self, tmp_path):
        """Test downloading a file from local storage"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        # First upload
        content = b"Download test content"
        file_data = io.BytesIO(content)
        storage_key = storage.upload(file_data, "download_test.txt", "text/plain")
        
        # Then download
        downloaded = storage.download(storage_key)
        assert downloaded == content

    def test_delete_file(self, tmp_path):
        """Test deleting a file from local storage"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        # Upload first
        content = b"Delete test content"
        file_data = io.BytesIO(content)
        storage_key = storage.upload(file_data, "delete_test.txt", "text/plain")
        
        # Verify exists
        assert storage.exists(storage_key)
        
        # Delete
        result = storage.delete(storage_key)
        assert result is True
        
        # Verify gone
        assert not storage.exists(storage_key)

    def test_file_exists(self, tmp_path):
        """Test checking if file exists"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        # Check non-existent file
        assert not storage.exists("nonexistent.txt")
        
        # Upload and check
        content = b"Exists test"
        file_data = io.BytesIO(content)
        storage_key = storage.upload(file_data, "exists_test.txt", "text/plain")
        
        assert storage.exists(storage_key)

    def test_get_url(self, tmp_path):
        """Test getting URL for a file"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        url = storage.get_url("test_key.txt")
        assert url == "/files/test_key.txt"

    def test_download_nonexistent_file(self, tmp_path):
        """Test downloading a file that doesn't exist"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        with pytest.raises(FileNotFoundError):
            storage.download("nonexistent_file.txt")

    def test_delete_nonexistent_file(self, tmp_path):
        """Test deleting a file that doesn't exist"""
        storage = LocalStorageBackend(base_path=str(tmp_path))
        
        result = storage.delete("nonexistent_file.txt")
        assert result is False


class TestGetStorageBackend:
    """Test storage backend factory"""

    def test_returns_local_by_default(self):
        """Test that local storage is returned when S3 is disabled"""
        with patch.object(settings, 'S3_ENABLED', False):
            backend = get_storage_backend()
            assert isinstance(backend, LocalStorageBackend)

    def test_local_storage_creates_directory(self, tmp_path):
        """Test that local storage creates upload directory"""
        storage = LocalStorageBackend(base_path=str(tmp_path / "uploads"))
        
        content = b"Directory test"
        file_data = io.BytesIO(content)
        storage_key = storage.upload(file_data, "dir_test.txt", "text/plain")
        
        assert storage_key is not None
