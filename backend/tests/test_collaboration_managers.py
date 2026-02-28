"""Unit coverage for collaboration manager service objects."""

from app.collaboration import CollabStateManager, SessionManager, SnapshotManager
from app.models import CollaborationSession


def test_collab_state_manager_returns_status_payload(db, test_user, test_document):
    test_document.yjs_state = b"\x01\x02\x03"
    db.commit()

    manager = CollabStateManager(db)
    payload = manager.get_collaboration_status(
        document_id=test_document.id,
        current_user=test_user,
    )

    assert payload["document_id"] == test_document.id
    assert payload["is_collaborative_mode"] is True
    assert isinstance(payload["active_collaborators"], list)


def test_session_manager_start_and_end_session(db, test_user, test_document):
    manager = SessionManager(db)
    start_payload = manager.start_collaboration_session(
        document_id=test_document.id,
        current_user=test_user,
    )

    assert start_payload["document_id"] == test_document.id
    session_id = start_payload["session_id"]

    end_payload = manager.end_collaboration_session(
        session_id=session_id,
        edits_count=7,
        current_user=test_user,
    )

    assert end_payload["session_id"] == session_id

    session = db.query(CollaborationSession).filter_by(session_id=session_id).first()
    assert session is not None
    assert session.is_active is False
    assert session.edits_count == 7


def test_snapshot_manager_create_and_list_snapshots(db, test_user, test_document):
    test_document.yjs_state = b"\x01\x02\x03\x04"
    db.commit()

    manager = SnapshotManager(db)
    created = manager.create_snapshot(
        document_id=test_document.id,
        current_user=test_user,
        name="Manager Snapshot",
        description="created by manager unit test",
        session_id=None,
    )

    assert created["snapshot_type"] == "manual_save"
    assert created["name"] == "Manager Snapshot"

    listed = manager.list_snapshots(
        document_id=test_document.id,
        current_user=test_user,
        limit=20,
        offset=0,
        include_expired=False,
    )
    assert listed["total"] >= 1
    assert any(snapshot["id"] == created["id"] for snapshot in listed["snapshots"])
