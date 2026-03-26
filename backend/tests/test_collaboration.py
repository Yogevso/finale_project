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
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
)
from app.observability import get_use_case_telemetry_sink, reset_use_case_telemetry_sink
from app.security import get_password_hash
from app.services.collaboration_service import CollaborationService
from tests.scenarios import create_collaboration_access_scenario


def _login(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
        assert decoded["type"] == "collaboration"
        assert decoded["document_id"] == str(test_document.id)
        assert "permissions" in decoded
        assert response.headers["X-Trace-ID"] == decoded["trace_id"]
        assert response.headers["X-Request-ID"]

    def test_get_collab_token_preserves_incoming_trace_id(
        self, client, auth_headers, test_document
    ):
        response = client.post(
            "/api/v1/auth/collab-token",
            headers={**auth_headers, "X-Trace-ID": "trace-collab-client-123"},
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        decoded = jwt.decode(
            response.json()["token"],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        assert response.headers["X-Trace-ID"] == "trace-collab-client-123"
        assert decoded["trace_id"] == "trace-collab-client-123"

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
        """Test that viewers receive read-only collab tokens."""
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=viewer_auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == ["read"]

    def test_editor_receives_write_permission_for_draft_when_standard_edit_policy_allows(
        self, client, db
    ):
        """Draft documents should issue read/write tokens for same-tenant editors."""
        tenant = Tenant(name="Collab Edit Tenant", slug="collab-edit-tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        owner = User(
            email="collab-owner-2@example.com",
            username="collab_owner_2",
            full_name="Collab Owner Two",
            hashed_password=get_password_hash("owner123"),
            role=UserRole.ADMIN,
            tenant_id=tenant.id,
            is_active=True,
            is_email_verified=True,
        )
        editor = User(
            email="collab-editor-2@example.com",
            username="collab_editor_2",
            full_name="Collab Editor Two",
            hashed_password=get_password_hash("editor123"),
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([owner, editor])
        db.commit()
        db.refresh(owner)
        db.refresh(editor)

        document = Document(
            title="Collab edit parity doc",
            document_number="DOC-COLLAB-EDIT-001",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.INTERNAL,
            tenant_id=tenant.id,
            created_by=editor.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        editor_headers = _login(client, "collab_editor_2", "editor123")
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=editor_headers,
            json={"document_id": document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "read" in data["permissions"]
        assert "write" in data["permissions"]

    def test_collab_token_denied_for_cross_tenant_internal_user(self, client, db):
        """Cross-tenant internal users cannot obtain collaboration tokens."""
        scenario = create_collaboration_access_scenario(db)

        outsider_headers = _login(client, scenario.outsider.username, scenario.outsider_password)
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=outsider_headers,
            json={"document_id": scenario.document.id},
        )
        assert response.status_code == 403

    def test_collab_token_denied_for_cross_tenant_system_admin(self, client, db):
        """System admins must stay within the document tenant for collaboration."""
        scenario = create_collaboration_access_scenario(db)

        system_admin = User(
            email="collab-sysadmin-tenant-b@example.com",
            username="collab_sysadmin_tenant_b",
            full_name="Cross Tenant Sysadmin",
            hashed_password=get_password_hash("sysadmin123"),
            role=UserRole.SYSTEM_ADMIN,
            tenant_id=scenario.outsider.tenant_id,
            is_active=True,
            is_email_verified=True,
        )
        db.add(system_admin)
        db.commit()

        system_admin_headers = _login(client, system_admin.username, "sysadmin123")
        response = client.post(
            "/api/v1/auth/collab-token",
            headers=system_admin_headers,
            json={"document_id": scenario.document.id},
        )

        assert response.status_code == 403


class TestDocumentState:
    """Tests for Yjs document state persistence"""

    def test_put_document_state(self, client, system_admin_headers, test_document):
        """Test saving Yjs state to a document"""
        # Binary Yjs state (mock data)
        yjs_state = b"\x01\x02\x03\x04\x05"

        response = client.put(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers={**system_admin_headers, "Content-Type": "application/octet-stream"},
            content=yjs_state,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "size" in data  # API returns message and size

    def test_put_document_state_emits_collaboration_telemetry(
        self, client, system_admin_headers, test_document
    ):
        reset_use_case_telemetry_sink()

        response = client.put(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers={**system_admin_headers, "Content-Type": "application/octet-stream"},
            content=b"\x01\x02\x03",
        )

        assert response.status_code == 200
        events = get_use_case_telemetry_sink().snapshot()
        assert any(
            event.use_case_id == "collab.save_document_state" and event.outcome == "success"
            for event in events
        )

    def test_get_document_state(self, client, system_admin_headers, test_document, db):
        """Test retrieving Yjs state from a document"""
        # First, save some state
        yjs_state = b"\x01\x02\x03\x04\x05"
        test_document.yjs_state = yjs_state
        db.commit()

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=system_admin_headers,
        )

        assert response.status_code == 200
        assert response.content == yjs_state

    def test_get_document_state_empty(self, client, system_admin_headers, test_document):
        """Test retrieving state from document with no Yjs state"""
        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=system_admin_headers,
        )

        # No state returns 404 (not found)
        assert response.status_code == 404

    def test_delete_document_state(self, client, system_admin_headers, test_document, db):
        """Test clearing Yjs state from a document"""
        # First, save some state
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.delete(
            f"/api/v1/collaboration/documents/{test_document.id}/state",
            headers=system_admin_headers,
        )

        assert response.status_code == 200

        # Verify state is cleared
        db.refresh(test_document)
        assert test_document.yjs_state is None

    def test_verify_collaboration_access_accepts_valid_same_tenant_token(
        self, client, auth_headers, test_document
    ):
        reset_use_case_telemetry_sink()
        token_response = client.post(
            "/api/v1/auth/collab-token",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )
        assert token_response.status_code == 200
        token = token_response.json()["token"]

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/verify-access",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
        assert data["user_id"] > 0
        assert data["tenant_id"] == test_document.tenant_id
        assert "write" in data["permissions"]
        events = get_use_case_telemetry_sink().snapshot()
        assert any(
            event.use_case_id == "collab.verify_collaboration_access"
            and event.outcome == "success"
            for event in events
        )

    def test_verify_collaboration_access_accepts_read_only_viewer_token(
        self, client, viewer_auth_headers, test_document
    ):
        token_response = client.post(
            "/api/v1/auth/collab-token",
            headers=viewer_auth_headers,
            json={"document_id": test_document.id},
        )
        assert token_response.status_code == 200
        token = token_response.json()["token"]

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/verify-access",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
        assert data["permissions"] == ["read"]

    def test_verify_collaboration_access_rejects_cross_tenant_system_admin_token(
        self, client, db
    ):
        scenario = create_collaboration_access_scenario(db)
        foreign_system_admin = User(
            email="collab-verify-sysadmin@example.com",
            username="collab_verify_sysadmin",
            full_name="Foreign Verify Sysadmin",
            hashed_password=get_password_hash("verify123"),
            role=UserRole.SYSTEM_ADMIN,
            tenant_id=scenario.outsider.tenant_id,
            is_active=True,
            is_email_verified=True,
        )
        db.add(foreign_system_admin)
        db.commit()
        db.refresh(foreign_system_admin)

        forged_token = CollaborationService().issue_collab_token(
            user=foreign_system_admin,
            document_id=scenario.document.id,
            permissions=["read", "write"],
        )

        response = client.get(
            f"/api/v1/collaboration/documents/{scenario.document.id}/verify-access",
            headers={"Authorization": f"Bearer {forged_token}"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Cross-tenant collaboration is not allowed"


class TestCollaborationSessions:
    """Tests for collaboration session tracking"""

    def test_start_session(self, client, auth_headers, test_document):
        """Test starting a collaboration session"""
        reset_use_case_telemetry_sink()
        response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=auth_headers,
            json={"document_id": test_document.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["document_id"] == test_document.id
        events = get_use_case_telemetry_sink().snapshot()
        assert any(
            event.use_case_id == "collab.start_collaboration_session"
            and event.outcome == "success"
            for event in events
        )

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
        self, client, auth_headers, system_admin_headers, test_document
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
            headers=system_admin_headers,
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

    def test_create_manual_snapshot(self, client, system_admin_headers, test_document, db):
        """Test creating a manual snapshot"""
        # First add some Yjs state
        test_document.yjs_state = b"\x01\x02\x03\x04\x05"
        db.commit()

        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
            json={"name": "Test Snapshot", "description": "A test snapshot"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Snapshot"
        assert data["snapshot_type"] == "manual_save"

    def test_create_auto_snapshot(self, client, system_admin_headers, test_document, db):
        """Test creating an auto-save snapshot (API endpoint creates manual_save)"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
            json={"name": "Auto-triggered snapshot"},
        )

        assert response.status_code == 200
        data = response.json()
        # API endpoint always creates manual_save type
        assert data["snapshot_type"] == "manual_save"

    def test_list_snapshots(self, client, system_admin_headers, test_document, db):
        """Test listing snapshots for a document"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        # Create some snapshots
        for i in range(3):
            client.post(
                f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
                headers=system_admin_headers,
                json={"name": f"Snapshot {i}"},
            )

        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) >= 3
        assert all(snapshot["created_by_username"] for snapshot in data["snapshots"])

    def test_get_snapshot(self, client, system_admin_headers, test_document, db):
        """Test getting a specific snapshot"""
        test_document.yjs_state = b"\x01\x02\x03\x04\x05"
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
            json={"name": "Specific Snapshot"},
        )
        snapshot_id = create_response.json()["id"]

        # Get the snapshot
        response = client.get(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}",
            headers=system_admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Specific Snapshot"

    def test_restore_snapshot(self, client, system_admin_headers, test_document, db):
        """Test restoring a snapshot"""
        # Set initial state
        original_state = b"\x01\x02\x03"
        test_document.yjs_state = original_state
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
            json={"name": "Restore Point"},
        )
        snapshot_id = create_response.json()["id"]

        # Change the document state
        test_document.yjs_state = b"\x04\x05\x06"
        db.commit()

        # Restore the snapshot
        response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}/restore",
            headers=system_admin_headers,
            json={},  # Empty body, session_id is optional
        )

        assert response.status_code == 200

        # Verify state is restored
        db.refresh(test_document)
        assert test_document.yjs_state == original_state

    def test_delete_snapshot(self, client, system_admin_headers, test_document, db):
        """Test deleting a snapshot"""
        test_document.yjs_state = b"\x01\x02\x03"
        db.commit()

        # Create a snapshot
        create_response = client.post(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots",
            headers=system_admin_headers,
            json={"name": "To Delete"},
        )
        snapshot_id = create_response.json()["id"]

        # Delete the snapshot
        response = client.delete(
            f"/api/v1/collaboration/documents/{test_document.id}/snapshots/{snapshot_id}",
            headers=system_admin_headers,
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

    def test_cross_tenant_internal_user_denied_across_collaboration_endpoints(self, client, db):
        """Cross-tenant internal access is denied for state/session/activity/snapshot endpoints."""
        scenario = create_collaboration_access_scenario(db)
        scenario.document.yjs_state = b"\x01\x02\x03"
        db.commit()
        db.refresh(scenario.document)

        outsider_headers = _login(client, scenario.outsider.username, scenario.outsider_password)

        state_response = client.get(
            f"/api/v1/collaboration/documents/{scenario.document.id}/state",
            headers=outsider_headers,
        )
        assert state_response.status_code == 403

        session_response = client.post(
            "/api/v1/collaboration/sessions/start",
            headers=outsider_headers,
            json={"document_id": scenario.document.id},
        )
        assert session_response.status_code == 403

        activity_response = client.post(
            "/api/v1/collaboration/activity",
            headers=outsider_headers,
            json={
                "document_id": scenario.document.id,
                "activity_type": "cursor_moved",
                "details": {"position": 7},
            },
        )
        assert activity_response.status_code == 403

        snapshot_response = client.get(
            f"/api/v1/collaboration/documents/{scenario.document.id}/snapshots",
            headers=outsider_headers,
        )
        assert snapshot_response.status_code == 403
