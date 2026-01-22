"""Storage Service - Local and S3 storage backends"""

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy import boto3 only when S3 is enabled
if TYPE_CHECKING:
    pass


class StorageBackend(ABC):
    """Abstract storage backend interface"""

    @abstractmethod
    def upload(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file and return storage key"""
        pass

    @abstractmethod
    def download(self, storage_key: str) -> bytes:
        """Download file contents"""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get URL for file access"""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, base_path: str = "data/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, storage_key: str) -> Path:
        return self.base_path / storage_key

    def upload(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file to local storage"""
        # Generate unique key
        ext = Path(filename).suffix
        storage_key = f"{uuid.uuid4().hex}{ext}"

        file_path = self._get_path(storage_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_data.read())

        logger.info(f"Uploaded file to local storage: {storage_key}")
        return storage_key

    def download(self, storage_key: str) -> bytes:
        """Download file from local storage"""
        file_path = self._get_path(storage_key)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        with open(file_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        """Delete file from local storage"""
        file_path = self._get_path(storage_key)
        try:
            file_path.unlink()
            logger.info(f"Deleted file from local storage: {storage_key}")
            return True
        except FileNotFoundError:
            return False

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get local file path (for local serving)"""
        return f"/files/{storage_key}"

    def exists(self, storage_key: str) -> bool:
        """Check if file exists locally"""
        return self._get_path(storage_key).exists()


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend"""

    def __init__(self):
        # Lazy import boto3 only when actually used
        import boto3
        from botocore.exceptions import ClientError

        self._ClientError = ClientError

        self.bucket = settings.S3_BUCKET
        self.region = settings.S3_REGION

        # Initialize S3 client
        client_kwargs = {
            "region_name": self.region,
        }

        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        if settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
            client_kwargs["aws_access_key_id"] = settings.S3_ACCESS_KEY
            client_kwargs["aws_secret_access_key"] = settings.S3_SECRET_KEY

        self.client = boto3.client("s3", **client_kwargs)
        logger.info(f"Initialized S3 storage: bucket={self.bucket}, region={self.region}")

    def upload(self, file_data: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file to S3"""
        # Generate unique key with folder structure
        ext = Path(filename).suffix
        storage_key = f"documents/{uuid.uuid4().hex}{ext}"

        try:
            self.client.upload_fileobj(
                file_data,
                self.bucket,
                storage_key,
                ExtraArgs={
                    "ContentType": content_type,
                },
            )
            logger.info(f"Uploaded file to S3: {storage_key}")
            return storage_key
        except self._ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def download(self, storage_key: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
            return response["Body"].read()
        except self._ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {storage_key}") from e
            raise

    def delete(self, storage_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_key)
            logger.info(f"Deleted file from S3: {storage_key}")
            return True
        except self._ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for S3 object"""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": storage_key},
                ExpiresIn=expires_in,
            )
            return url
        except self._ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def exists(self, storage_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except self._ClientError:
            return False


def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend"""
    if settings.S3_ENABLED:
        return S3StorageBackend()
    else:
        return LocalStorageBackend()


# Default storage instance
storage = get_storage_backend()
