"""Tests for Versions API"""

from fastapi.testclient import TestClient


class TestVersionsAPI:
    """Tests for version management endpoints"""

    def test_list_versions(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test listing versions for a document"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            f"/api/v1/documents/{sample_document['id']}/versions", headers=headers
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
            json={"content": "Version 2 content", "changes_summary": "Added new section"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 2
        assert data["content"] == "Version 2 content"
        assert data["is_published"] is False

    def test_update_unpublished_version(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Test updating an unpublished version"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create a new version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Original", "changes_summary": "Initial"},
        )
        version_id = create_resp.json()["id"]

        # Update it
        response = client.patch(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
            json={"content": "Updated content"},
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    def test_publish_version(
        self,
        client: TestClient,
        admin_token: str,
        manager_headers: dict,
        sample_document: dict,
    ):
        """Test publishing a version"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create a new version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "To be published", "changes_summary": "Ready for release"},
        )
        version_id = create_resp.json()["id"]

        # Submit and approve review before publishing
        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "Ready for approval"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "Approved"},
        )
        assert approve_resp.status_code == 200

        # Publish it
        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_published"] is True
        assert data["published_at"] is not None

    def test_cannot_modify_published_version(
        self,
        client: TestClient,
        admin_token: str,
        manager_headers: dict,
        sample_document: dict,
    ):
        """Test that published versions are immutable"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create and publish version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Immutable", "changes_summary": "Final"},
        )
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "Ready for approval"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "Approved"},
        )
        assert approve_resp.status_code == 200

        client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers,
        )

        # Try to update - should fail
        response = client.patch(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
            json={"content": "Trying to modify"},
        )
        assert response.status_code == 400

    def test_cannot_publish_without_approved_review(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Publishing should fail when the version has no approved review yet."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "No approval", "changes_summary": "Should be blocked"},
        )
        version_id = create_resp.json()["id"]

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers,
        )
        assert publish_resp.status_code == 409

    def test_cannot_publish_version_with_pending_review(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Publishing should be blocked while a review is pending for the same version."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Needs review", "changes_summary": "Pending approval"},
        )
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "Please review"},
        )
        assert submit_resp.status_code in [200, 201]

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=headers,
        )
        assert publish_resp.status_code == 409

    def test_cannot_update_version_with_pending_review(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Updating should be blocked while a review is pending for the same version."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Review me", "changes_summary": "Draft for approval"},
        )
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "Please review"},
        )
        assert submit_resp.status_code in [200, 201]

        update_resp = client.patch(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
            json={"content": "Changed after submit"},
        )
        assert update_resp.status_code == 409

    def test_cannot_create_new_version_while_review_pending(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Creating a new version should fail while a review is pending."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "v2", "changes_summary": "candidate"},
        )
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "Please review"},
        )
        assert submit_resp.status_code in [200, 201]

        create_blocked_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "v3", "changes_summary": "should be blocked"},
        )
        assert create_blocked_resp.status_code == 409

    def test_delete_unpublished_version(
        self, client: TestClient, admin_token: str, sample_document: dict
    ):
        """Test deleting an unpublished version"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create version
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "To delete", "changes_summary": "Temp"},
        )
        version_id = create_resp.json()["id"]

        # Delete it
        response = client.delete(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}", headers=headers
        )
        assert response.status_code == 200
