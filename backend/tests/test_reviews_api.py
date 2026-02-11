"""Tests for the Review/Approval Workflow API"""

import pytest


class TestSubmitForReview:
    """Test submitting documents for review"""

    def test_editor_can_submit_own_document(self, client, auth_headers, test_document):
        """Editor should be able to submit their own document for review"""
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review this document"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "pending"

    def test_cannot_submit_already_pending_document(self, client, auth_headers, test_document):
        """Cannot submit a document that's already pending review"""
        # First submission
        client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "First submission"},
        )
        # Second submission should fail
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Second submission"},
        )
        assert response.status_code in [400, 409]

    def test_viewer_cannot_submit_for_review(self, client, viewer_auth_headers, test_document):
        """Viewer should not be able to submit documents for review"""
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=viewer_auth_headers,
            json={"message": "Please review"},
        )
        assert response.status_code == 403

    def test_customer_cannot_submit_for_review(self, client, customer_headers, public_document):
        """Customer should not be able to submit documents for review"""
        response = client.post(
            f"/api/v1/reviews/documents/{public_document.id}/submit",
            headers=customer_headers,
            json={"message": "Please review"},
        )
        assert response.status_code == 403

    def test_submit_with_invalid_version_for_document(self, client, auth_headers, test_document):
        """Submitting with a version_id not belonging to the document should fail."""
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"version_id": 999999, "message": "Please review this exact version"},
        )
        assert response.status_code == 404


class TestPendingReviews:
    """Test listing pending reviews"""

    def test_manager_can_list_pending_reviews(self, client, manager_headers):
        """Manager should be able to list pending reviews"""
        response = client.get("/api/v1/reviews/pending", headers=manager_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_editor_can_list_pending_reviews(self, client, auth_headers):
        """Editor should be able to list pending reviews (for peer review)"""
        response = client.get("/api/v1/reviews/pending", headers=auth_headers)
        assert response.status_code == 200

    def test_viewer_cannot_list_pending_reviews(self, client, viewer_auth_headers):
        """Viewer should not be able to list pending reviews"""
        response = client.get("/api/v1/reviews/pending", headers=viewer_auth_headers)
        assert response.status_code == 403

    def test_customer_cannot_list_pending_reviews(self, client, customer_headers):
        """Customer should not be able to list pending reviews"""
        response = client.get("/api/v1/reviews/pending", headers=customer_headers)
        assert response.status_code == 403


class TestMySubmissions:
    """Test listing own review submissions"""

    def test_editor_can_list_own_submissions(self, client, auth_headers, test_document):
        """Editor should be able to list their own submissions"""
        # First submit a document
        client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review"},
        )
        # Then list submissions
        response = client.get("/api/v1/reviews/my-submissions", headers=auth_headers)
        assert response.status_code == 200


class TestApproveReview:
    """Test approving reviews"""

    @pytest.fixture
    def pending_review(self, client, db, auth_headers, test_document, test_manager):
        """Create a pending review for testing"""
        # Submit document for review
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review"},
        )
        return response.json()

    def test_manager_can_approve_review(self, client, manager_headers, pending_review):
        """Manager should be able to approve a review"""
        review_id = pending_review["id"]
        response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "Looks good!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_submitter_cannot_approve_own_review(self, client, auth_headers, pending_review):
        """User cannot approve their own review submission"""
        review_id = pending_review["id"]
        response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=auth_headers,
            json={"comments": "Self-approval"},
        )
        assert response.status_code in [400, 403]

    def test_viewer_cannot_approve_review(self, client, viewer_auth_headers, pending_review):
        """Viewer should not be able to approve reviews"""
        review_id = pending_review["id"]
        response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=viewer_auth_headers,
            json={"comments": "Approved"},
        )
        assert response.status_code == 403

    def test_cannot_approve_outdated_review_when_newer_version_exists(
        self,
        client,
        db,
        auth_headers,
        manager_headers,
        test_document,
        test_user,
    ):
        """Approval should fail if a newer version was created after review submission."""
        from app.models import Version

        v1 = Version(
            document_id=test_document.id,
            version_number=1,
            content="v1",
            changes_summary="init",
            created_by=test_user.id,
        )
        v2 = Version(
            document_id=test_document.id,
            version_number=2,
            content="v2",
            changes_summary="candidate",
            created_by=test_user.id,
        )
        db.add_all([v1, v2])
        db.commit()
        db.refresh(v2)

        submit_response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"version_id": v2.id, "message": "Approve v2"},
        )
        assert submit_response.status_code in [200, 201]
        review_id = submit_response.json()["id"]

        v3 = Version(
            document_id=test_document.id,
            version_number=3,
            content="v3",
            changes_summary="newer version",
            created_by=test_user.id,
        )
        db.add(v3)
        db.commit()

        approve_response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "Looks good"},
        )
        assert approve_response.status_code == 409

    def test_approve_marks_document_approved_but_not_published(
        self,
        client,
        db,
        auth_headers,
        manager_headers,
        test_document,
        test_user,
    ):
        """Approval should move document to approved state and keep version unpublished."""
        from app.models import Version

        version = Version(
            document_id=test_document.id,
            version_number=1,
            content="candidate",
            changes_summary="ready",
            created_by=test_user.id,
            is_published=False,
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        submit_response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"version_id": version.id, "message": "Please approve"},
        )
        assert submit_response.status_code in [200, 201]
        review_id = submit_response.json()["id"]

        approve_response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "Approved for publish"},
        )
        assert approve_response.status_code == 200

        doc_response = client.get(f"/api/v1/documents/{test_document.id}", headers=manager_headers)
        assert doc_response.status_code == 200
        assert doc_response.json()["status"] == "approved"

        version_response = client.get(
            f"/api/v1/documents/{test_document.id}/versions/{version.id}",
            headers=manager_headers,
        )
        assert version_response.status_code == 200
        assert version_response.json()["is_published"] is False


class TestRejectReview:
    """Test rejecting reviews"""

    @pytest.fixture
    def pending_review_for_reject(self, client, db, auth_headers, test_document, test_manager):
        """Create a pending review for rejection testing"""
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review"},
        )
        return response.json()

    def test_manager_can_reject_review(self, client, manager_headers, pending_review_for_reject):
        """Manager should be able to reject a review"""
        review_id = pending_review_for_reject["id"]
        response = client.post(
            f"/api/v1/reviews/{review_id}/reject",
            headers=manager_headers,
            json={"comments": "Needs more work"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_reject_requires_comments(self, client, manager_headers, pending_review_for_reject):
        """Rejection should require comments"""
        review_id = pending_review_for_reject["id"]
        response = client.post(
            f"/api/v1/reviews/{review_id}/reject",
            headers=manager_headers,
            json={},
        )
        # Should fail without comments
        assert response.status_code in [400, 422]


class TestCancelReview:
    """Test cancelling review submissions"""

    @pytest.fixture
    def pending_review_for_cancel(self, client, db, auth_headers, test_document, test_manager):
        """Create a pending review for cancellation testing"""
        response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review"},
        )
        return response.json()

    def test_submitter_can_cancel_own_review(self, client, auth_headers, pending_review_for_cancel):
        """User should be able to cancel their own review submission"""
        review_id = pending_review_for_cancel["id"]
        response = client.post(f"/api/v1/reviews/{review_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_other_user_cannot_cancel_review(
        self, client, viewer_auth_headers, pending_review_for_cancel
    ):
        """Other users should not be able to cancel someone else's review"""
        review_id = pending_review_for_cancel["id"]
        response = client.post(f"/api/v1/reviews/{review_id}/cancel", headers=viewer_auth_headers)
        assert response.status_code in [403, 404]


class TestPeerReview:
    """Test peer review workflow between editors"""

    @pytest.fixture
    def second_editor(self, db):
        """Create a second editor for peer review testing"""
        from app.models import User, UserRole
        from app.security import get_password_hash

        editor = User(
            email="editor2@example.com",
            username="editor2",
            full_name="Editor Two",
            hashed_password=get_password_hash("editor123"),
            role=UserRole.EDITOR,
            is_active=True,
        )
        db.add(editor)
        db.commit()
        db.refresh(editor)
        return editor

    @pytest.fixture
    def second_editor_headers(self, client, second_editor):
        """Get auth headers for second editor"""
        response = client.post(
            "/api/v1/auth/login", json={"username": "editor2", "password": "editor123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_editor_can_review_peer_submission(
        self, client, auth_headers, second_editor_headers, test_document
    ):
        """Editor should be able to approve peer's submission"""
        # First editor submits
        submit_response = client.post(
            f"/api/v1/reviews/documents/{test_document.id}/submit",
            headers=auth_headers,
            json={"message": "Please review"},
        )
        review_id = submit_response.json()["id"]

        # Second editor approves (peer review)
        response = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=second_editor_headers,
            json={"comments": "Peer approved!"},
        )
        assert response.status_code == 200
