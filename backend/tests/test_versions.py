"""Tests for Versions API"""
import pytest
from fastapi.testclient import TestClient


class TestVersionsAPI:
    """Tests for version management endpoints"""

    def test_list_versions(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test listing versions for a document"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        # Document creation auto-creates version 1
        assert len(data["items"]) >= 1

    def test_create_version(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test creating a new version"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Version 2 content", "changes_summary": "Added new section"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 2
        assert data["content"] == "Version 2 content"
        assert data["is_published"] is False

    def test_update_unpublished_version(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test updating an unpublished version"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a new version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Original", "changes_summary": "Initial"}
        )
        version_id = create_resp.json()["id"]
        
        # Update it
        response = client.patch(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
            json={"content": "Updated content"}
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    def test_publish_version(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test publishing a version"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a new version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "To be published", "changes_summary": "Ready for release"}
        )
        version_id = create_resp.json()["id"]
        
        # Publish it
        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_published"] is True
        assert data["published_at"] is not None

    def test_cannot_modify_published_version(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test that published versions are immutable"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create and publish version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Immutable", "changes_summary": "Final"}
        )
        version_id = create_resp.json()["id"]
        client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers
        )
        
        # Try to update - should fail
        response = client.patch(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
            json={"content": "Trying to modify"}
        )
        assert response.status_code == 400

    def test_delete_unpublished_version(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test deleting an unpublished version"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "To delete", "changes_summary": "Temp"}
        )
        version_id = create_resp.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers
        )
        assert response.status_code == 200
