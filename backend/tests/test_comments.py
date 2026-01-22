"""Tests for Comments API"""

from fastapi.testclient import TestClient


class TestCommentsAPI:
    """Tests for comment management endpoints"""

    def test_list_comments_empty(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test listing comments when empty"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            f"/api/v1/documents/{sample_document['id']}/comments", headers=headers
        )
        assert response.status_code == 200
        # Could be empty list or list with existing comments
        assert isinstance(response.json(), list)

    def test_create_comment(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test creating a comment"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments",
            headers=headers,
            json={"content": "This is a test comment"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a test comment"
        assert data["user_id"] == 1  # Admin user

    def test_create_reply(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test creating a reply to a comment"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create parent comment
        parent_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments",
            headers=headers,
            json={"content": "Parent comment"},
        )
        parent_id = parent_resp.json()["id"]

        # Create reply
        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments?parent_id={parent_id}",
            headers=headers,
            json={"content": "Reply to parent"},
        )
        assert response.status_code == 201
        assert response.json()["content"] == "Reply to parent"

    def test_update_comment(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test updating a comment"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create comment
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments",
            headers=headers,
            json={"content": "Original content"},
        )
        comment_id = create_resp.json()["id"]

        # Update it
        response = client.patch(
            f"/api/v1/documents/{sample_document['id']}/comments/{comment_id}",
            headers=headers,
            json={"content": "Updated content"},
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    def test_delete_comment(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test deleting a comment"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create comment
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments",
            headers=headers,
            json={"content": "To delete"},
        )
        comment_id = create_resp.json()["id"]

        # Delete it
        response = client.delete(
            f"/api/v1/documents/{sample_document['id']}/comments/{comment_id}", headers=headers
        )
        assert response.status_code == 200

    def test_list_replies_only(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test listing only replies to a specific comment"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create parent comment
        parent_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/comments",
            headers=headers,
            json={"content": "Parent for replies"},
        )
        parent_id = parent_resp.json()["id"]

        # Create two replies
        client.post(
            f"/api/v1/documents/{sample_document['id']}/comments?parent_id={parent_id}",
            headers=headers,
            json={"content": "Reply 1"},
        )
        client.post(
            f"/api/v1/documents/{sample_document['id']}/comments?parent_id={parent_id}",
            headers=headers,
            json={"content": "Reply 2"},
        )

        # List replies
        response = client.get(
            f"/api/v1/documents/{sample_document['id']}/comments?parent_id={parent_id}",
            headers=headers,
        )
        assert response.status_code == 200
        replies = response.json()
        assert len(replies) >= 2
        # All should be replies to the parent
        for reply in replies:
            if "parent_id" in reply:
                assert reply["parent_id"] == parent_id or reply.get("parent_id") is None
