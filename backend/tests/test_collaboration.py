"""
Tests for Real-Time Collaboration API Endpoints

Tests cover:
- Collaboration token generation
- Document state persistence (GET/PUT/DELETE)
- Collaboration sessions tracking
- Activity logging
- Snapshot creation and restoration
"""

import jwt

from app.config import settings
from app.models import (
    CollaborationSession,
    CollaborationSnapshot,
)


class TestCollabToken:
    """Tests for collaboration token generation"""

    def test_get_collab_token_success(self, client, auth_headers, test_document):
        """Test getting a collaboration token for a document"""
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["document_id"] == test_document.id
        assert "permissions" in data
        assert "websocket_url" in data
        assert "expires_in" in data

        # Verify token is valid JWT
        decoded = jwt.decode(data["token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["document_id"] == str(test_document.id)
        assert "permissions" in decoded

    def test_get_collab_token_document_not_found(self, client, auth_headers):
        """Test getting a token for non-existent document"""
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=auth_headers,
            json={"document_id": 99999},
        )

        assert response.status_code == 404

    def test_get_collab_token_unauthorized(self, client, test_document):
        """Test getting a token without authentication"""
        response = client.post(
            "/api/v1/auth/collab-token",
            json={"document_id": test_document.id},
        )

        assert response.status_code == 401

    def test_collab_token_permissions_editor(self, client, auth_headers, test_document):
        """Test that editors get read+write permissions"""
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "read" in data["permissions"]
        assert "write" in data["permissions"]

    def test_collab_token_permissions_viewer(self, client, viewer_auth_headers, test_document):
        """Test that viewers only get read permissions"""
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=viewer_auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "read" in data["permissions"]
        assert "write" not in data["permissions"]


class TestDocumentState:
    """Tests for Yjs document state persistence"""

    def test_put_document_state(self, client, admin_headers, test_document):
        """Test saving Yjs state to a document"""
        # Binary Yjs state (mock data)
        yjs_state = b"\x01\x02\x03\x04\x05"

        response = client.put(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers={**admin_headers, "Content-Type": "application/octet-stream"},
            content=yjs_state,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "size" in data  # API returns message and size

    def test_get_document_state(self, client, admin_headers, test_document, db):
        """Test retrieving Yjs state from a document"""
        # First, save some state
        yjs_state = b"\x01\x02\x03\x04\x05"
        test_document.yjs_state = yjs_state
        db.commit()

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.content == yjs_state

    def test_get_document_state_empty(self, client, admin_headers, test_document):
        """Test retrieving state from document with no Yjs state"""
        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=admin_headers,
        )

        # No state returns 404 (not found)
        assert response.status_code == 404

    def test_delete_document_state(self, client, admin_headers, test_document, db):
        """Test clearing Yjs state from a document"""
        # First, save some state
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.delete(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=admin_headers,
        )

        assert response.status_code == 200

        # Verify state is cleared
        db.refresh(test_document)
        assert test_document.yjs_state is None


class TestCollaborationSessions:
    """Tests for collaboration session tracking"""

    def test_start_session(self, client, auth_headers, test_document):
        """Test starting a collaboration session"""
        response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["document_id"] == test_document.id

    def test_end_session(self, client, auth_headers, test_document, db):
        """Test ending a collaboration session"""
        # First start a session
        start_response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )
        session_id = start_response.json()["session_id"]

        # End the session
        response = client.post(
            "/api/v1/collaboration/sessions/end",
            headers=auth_headers,
            json={"session_id": session_id, "edits_count": 15},
        )

        assert response.status_code == 200

        # Verify session is ended
        session = db.query(CollaborationSession).filter_by(session_id=session_id).first()
        assert session.ended_at is not None
        assert session.edits_count == 15

    def test_get_document_sessions(self, client, auth_headers, test_document, db):
        """Test getting all sessions for a document"""
        # Create some sessions
        for _i in range(3):
            client.post(
                "/api/v1/collaboration/sessions/start",
                headers=auth_headers,
                json={"document_id": test_document.id},
            )

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/sessions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) >= 3


class TestCollaborationActivity:
    """Tests for collaboration activity logging"""

    def test_log_activity(self, client, auth_headers, test_document):
        """Test logging a collaboration activity"""
        response = client.post(
            "/api/v1/collaboration/activity",
            headers=auth_headers,
            json={
                "document_id": test_document.id,
                "activity_type": "cursor_moved",
                "details": {"position": 42},
            },
        )

        assert response.status_code == 200

    def test_get_document_activity(self, client, auth_headers, test_document):
        """Test getting activity feed for a document"""
        # Log some activities with valid activity types
        for activity_type in ["cursor_moved", "content_edited", "selection_changed"]:
            client.post(
                "/api/v1/collaboration/activity",
                headers=auth_headers,
                json={
                    "document_id": test_document.id,
                    "activity_type": activity_type,
                    "details": {},
                },
            )

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/activity",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data

    def test_activity_with_limit(self, client, auth_headers, test_document):
        """Test activity feed with limit parameter"""
        # Log many activities
        for i in range(10):
            client.post(
                "/api/v1/collaboration/activity",
                headers=auth_headers,
                json={
                    "document_id": test_document.id,
                    "activity_type": "cursor_moved",
                    "details": {"position": i},
                },
            )

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/activity",
            headers=auth_headers,
            params={"limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) <= 5

    def test_log_activity_forbidden_without_document_access(
        self, client, customer_2_headers, company_document
    ):
        """User cannot log activity for a document they cannot access."""
        response = client.post(
            "/api/v1/collaboration/activity",
            headers=customer_2_headers,
            json={
                "document_id": company_document.id,
                "activity_type": "cursor_moved",
                "details": {"position": 1},
            },
        )

        assert response.status_code == 403

    def test_log_activity_rejects_other_users_session(
        self, client, auth_headers, admin_headers, test_document
    ):
        """User cannot submit activity to another user's active session."""
        start_response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )
        session_id = start_response.json()["session_id"]

        response = client.post(
            "/api/v1/collaboration/activity",
            headers=admin_headers,
            json={
                "document_id": test_document.id,
                "session_id": session_id,
                "activity_type": "cursor_moved",
                "details": {"position": 9},
            },
        )

        assert response.status_code == 403

    def test_log_activity_rejects_session_document_mismatch(
        self, client, auth_headers, test_document, internal_document
    ):
        """Session IDs are scoped to one document and cannot be reused across documents."""
        start_response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )
        session_id = start_response.json()["session_id"]

        response = client.post(
            "/api/v1/collaboration/activity",
            headers=auth_headers,
            json={
                "document_id": internal_document.id,
                "session_id": session_id,
                "activity_type": "cursor_moved",
                "details": {"position": 9},
            },
        )

        assert response.status_code == 400


class TestSnapshots:
    """Tests for collaboration snapshot system"""

    def test_create_manual_snapshot(self, client, admin_headers, test_document, db):
        """Test creating a manual snapshot"""
        # First add some Yjs state
        test_document.yjs_state = b"\x01\x02\x03\x04\x05"
        db.commit()

        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
            json={"name": "Test Snapshot", "description": "A test snapshot"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Snapshot"
        assert data["snapshot_type"] == "manual_save"

    def test_create_auto_snapshot(self, client, admin_headers, test_document, db):
        """Test creating an auto-save snapshot (API endpoint creates manual_save)"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
            json={"name": "Auto-triggered snapshot"},
        )

        assert response.status_code == 200
        data = response.json()
        # API endpoint always creates manual_save type
        assert data["snapshot_type"] == "manual_save"

    def test_list_snapshots(self, client, admin_headers, test_document, db):
        """Test listing snapshots for a document"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        # Create some snapshots
        for i in range(3):
            client.post(
                f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
                headers=admin_headers,
                json={"name": f"Snapshot {i}"},
            )

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) >= 3

    def test_get_snapshot(self, client, admin_headers, test_document, db):
        """Test getting a specific snapshot"""
        test_document.yjs_state = b"\x01\x02\x03\x04\x05"
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
            json={"name": "Specific Snapshot"},
        )
        snapshot_id = create_response.json()["id"]

        # Get the snapshot
        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Specific Snapshot"

    def test_restore_snapshot(self, client, admin_headers, test_document, db):
        """Test restoring a snapshot"""
        # Set initial state
        original_state = b"\x01\x02\x03"
        test_document.yjs_state = original_state
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
            json={"name": "Restore Point"},
        )
        snapshot_id = create_response.json()["id"]

        # Change the document state
        test_document.yjs_state = b"\x04\x05\x06"
        db.commit()

        # Restore the snapshot
        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}/restore",
            headers=admin_headers,
            json={},  # Empty body, session_id is optional
        )

        assert response.status_code == 200

        # Verify state is restored
        db.refresh(test_document)
        assert test_document.yjs_state == original_state

    def test_delete_snapshot(self, client, admin_headers, test_document, db):
        """Test deleting a snapshot"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=admin_headers,
            json={"name": "To Delete"},
        )
        snapshot_id = create_response.json()["id"]

        # Delete the snapshot
        response = client.delete(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}",
            headers=admin_headers,
        )

        assert response.status_code == 200

        # Verify snapshot is deleted
        snapshot = db.query(CollaborationSnapshot).filter_by(id=snapshot_id).first()
        assert snapshot is None


class TestCollaborationStatus:
    """Tests for document collaboration status"""

    def test_get_collaboration_status(self, client, auth_headers, test_document):
        """Test getting collaboration status for a document"""
        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "active_collaborators" in data
        assert "is_collaborative_mode" in data


class TestCollaborationPermissions:
    """Tests for collaboration permission controls"""

    def test_viewer_cannot_save_state(self, client, viewer_auth_headers, test_document):
        """Test that viewers cannot save document state"""
        response = client.put(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers={**viewer_auth_headers, "Content-Type": "application/octet-stream"},
            content=b"\x01\x02\x03",
        )

        # Should be forbidden for viewers
        assert response.status_code == 403

    def test_viewer_can_read_state(self, client, viewer_auth_headers, test_document, db):
        """Test that viewers can read document state"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=viewer_auth_headers,
        )

        assert response.status_code == 200

    def test_viewer_cannot_create_snapshot(self, client, viewer_auth_headers, test_document, db):
        """Test that viewers cannot create snapshots"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=viewer_auth_headers,
            json={"name": "Viewer Snapshot"},
        )

        assert response.status_code == 403
