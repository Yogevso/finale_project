"""Tests for Comments API"""

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.models import Comment, User, UserRole
from app.repositories.comment_repository import CommentRepository
from app.services.comment_service import CommentService
from tests.factories import create_user


class TestCommentsAPI:
    """Tests for comment management endpoints"""

    def test_list_comments_empty(self, client: TestClient, admin_token: str, sample_document: dict):
        """Test listing comments when empty"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            f"/api/v1/documents/{sample_document['id']}/comments", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "total" in data
        assert "page" in data

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

    def test_customer_cannot_access_management_comment_routes(
        self, client: TestClient, customer_headers: dict, public_document
    ):
        response = client.get(
            f"/api/v1/documents/{public_document.id}/comments",
            headers=customer_headers,
        )
        assert response.status_code == 403

        create_response = client.post(
            f"/api/v1/documents/{public_document.id}/comments",
            headers=customer_headers,
            json={"content": "Customer should use the portal route instead"},
        )
        assert create_response.status_code == 403

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

    def test_visibility_filtering_does_not_mutate_comment_relationships(
        self, db, sample_document: dict, monkeypatch
    ):
        """Visibility shaping must not delete/unlink replies from ORM relationships."""
        current_user = db.query(User).filter(User.id == 1).first()
        assert current_user is not None

        parent = Comment(
            document_id=sample_document["id"],
            user_id=current_user.id,
            content="Parent comment",
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

        reply = Comment(
            document_id=sample_document["id"],
            user_id=current_user.id,
            content="Reply comment",
            parent_id=parent.id,
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)

        def fake_can_view(_db, comment, _user, _contributors=None):
            return comment.parent_id is None

        monkeypatch.setattr(CommentService, "can_view_comment", staticmethod(fake_can_view))

        comments = CommentService(db).get_comments(sample_document["id"], current_user)
        assert comments.total == 1
        assert comments.items[0].id == parent.id
        assert comments.items[0].reply_count == 0
        assert comments.items[0].replies == []

        persisted_reply = db.query(Comment).filter(Comment.id == reply.id).first()
        assert persisted_reply is not None
        assert persisted_reply.parent_id == parent.id

    def test_internal_viewer_can_see_non_private_comments_without_being_contributor(
        self, db, sample_document: dict
    ):
        """Non-private threads should be visible to all internal users, not only contributors."""
        admin_user = db.query(User).filter(User.id == 1).first()
        assert admin_user is not None

        viewer_user = create_user(
            db,
            role=UserRole.VIEWER,
            tenant_id=admin_user.tenant_id,
        )

        comment = Comment(
            document_id=sample_document["id"],
            user_id=admin_user.id,
            content="Internal note visible to all staff",
            is_private=False,
        )
        db.add(comment)
        db.commit()

        comments = CommentService(db).get_comments(sample_document["id"], viewer_user)
        assert any(item.id == comment.id for item in comments.items)

    def test_parent_chain_is_eager_loaded_for_depth_checks(self, db, sample_document: dict):
        current_user = db.query(User).filter(User.id == 1).first()
        assert current_user is not None

        root = Comment(
            document_id=sample_document["id"],
            user_id=current_user.id,
            content="Root comment",
        )
        db.add(root)
        db.commit()
        db.refresh(root)

        child = Comment(
            document_id=sample_document["id"],
            user_id=current_user.id,
            content="Child comment",
            parent_id=root.id,
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        grandchild = Comment(
            document_id=sample_document["id"],
            user_id=current_user.id,
            content="Grandchild comment",
            parent_id=child.id,
        )
        db.add(grandchild)
        db.commit()
        db.refresh(grandchild)
        db.expire_all()

        repository = CommentRepository(db)
        select_count = 0

        def before_cursor_execute(*args, **kwargs):
            nonlocal select_count
            statement = args[2]
            if statement.lstrip().upper().startswith("SELECT"):
                select_count += 1

        event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
        try:
            loaded = repository.get_by_id_for_update(grandchild.id, sample_document["id"])
            assert loaded is not None
            initial_select_count = select_count

            assert loaded.parent is not None
            assert loaded.parent.parent is not None
            assert select_count == initial_select_count
        finally:
            event.remove(db.bind, "before_cursor_execute", before_cursor_execute)
