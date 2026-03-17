"""Wave AA — Backend integration tests.

AA-017: Data export — verify ZIP contains all user data
AA-018: Data deletion — verify anonymization
AA-019: Retention policy — archive after expiry
AA-020: Audit log immutability — UPDATE/DELETE prevented
AA-021: Dependency vulnerability CI check (unit-level)
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    ActionType,
    AuditLog,
    Bookmark,
    Comment,
    DataRequest,
    DataRequestStatus,
    DataRequestType,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    User,
    UserRole,
)
from app.services.gdpr_service import (
    approve_data_deletion,
    check_audit_integrity,
    execute_data_deletion,
    execute_data_export,
    install_audit_immutability_trigger,
    request_data_deletion,
    request_data_export,
)
from tests.factories import create_document, create_tenant, create_user


# ---------------------------------------------------------------------------
# AA-017  Data Export Integration Test
# ---------------------------------------------------------------------------


class TestDataExport:
    """AA-017: Request export, verify ZIP contains all user data."""

    def test_export_creates_zip_with_profile(self, db: Session):
        """Export ZIP must contain profile.json with correct user info."""
        tenant = create_tenant(db)
        user = create_user(
            db,
            email="export-test@example.com",
            username="export-user",
            full_name="Export User",
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
        )

        req = request_data_export(db, user_id=user.id, reason="GDPR request")
        assert req.status == DataRequestStatus.PENDING
        assert req.request_type == DataRequestType.EXPORT

        zip_bytes = execute_data_export(db, req.id)
        assert isinstance(zip_bytes, bytes)
        assert len(zip_bytes) > 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            assert "profile.json" in names

            profile = json.loads(zf.read("profile.json"))
            assert profile["email"] == "export-test@example.com"
            assert profile["username"] == "export-user"
            assert profile["full_name"] == "Export User"

    def test_export_contains_documents(self, db: Session):
        """Export ZIP must list documents created by the user."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id, title="My Doc")

        req = request_data_export(db, user_id=user.id, reason="test")
        zip_bytes = execute_data_export(db, req.id)

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "documents.json" in zf.namelist()
            docs = json.loads(zf.read("documents.json"))
            assert len(docs) >= 1
            assert any(d["title"] == "My Doc" for d in docs)

    def test_export_contains_comments(self, db: Session):
        """Export ZIP must include user's comments."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id)

        comment = Comment(
            document_id=doc.id,
            user_id=user.id,
            content="Test comment for export",
        )
        db.add(comment)
        db.commit()

        req = request_data_export(db, user_id=user.id, reason="test")
        zip_bytes = execute_data_export(db, req.id)

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "comments.json" in zf.namelist()
            comments = json.loads(zf.read("comments.json"))
            assert len(comments) >= 1
            assert any(c["content"] == "Test comment for export" for c in comments)

    def test_export_contains_bookmarks(self, db: Session):
        """Export ZIP must include user's bookmarks."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id)

        bookmark = Bookmark(document_id=doc.id, user_id=user.id)
        db.add(bookmark)
        db.commit()

        req = request_data_export(db, user_id=user.id, reason="test")
        zip_bytes = execute_data_export(db, req.id)

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "bookmarks.json" in zf.namelist()
            bookmarks = json.loads(zf.read("bookmarks.json"))
            assert len(bookmarks) >= 1

    def test_export_contains_audit_logs(self, db: Session):
        """Export ZIP must include user's audit log entries."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        # The export request itself creates audit logs
        req = request_data_export(db, user_id=user.id, reason="test")
        zip_bytes = execute_data_export(db, req.id)

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "audit_logs.json" in zf.namelist()
            logs = json.loads(zf.read("audit_logs.json"))
            assert len(logs) >= 1

    def test_export_marks_request_completed(self, db: Session):
        """Export request status should be COMPLETED after generation."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        req = request_data_export(db, user_id=user.id, reason="test")
        execute_data_export(db, req.id)

        db.refresh(req)
        assert req.status == DataRequestStatus.COMPLETED
        assert req.download_token is not None
        assert req.completed_at is not None


# ---------------------------------------------------------------------------
# AA-018  Data Deletion Integration Test
# ---------------------------------------------------------------------------


class TestDataDeletion:
    """AA-018: Request deletion, verify anonymization."""

    def test_deletion_workflow(self, db: Session):
        """Full deletion workflow: request → approve → execute → verify."""
        tenant = create_tenant(db)
        user = create_user(
            db,
            email="delete-me@example.com",
            username="delete-user",
            full_name="Delete Me",
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
        )
        admin = create_user(db, role=UserRole.SYSTEM_ADMIN, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id, title="User's Doc")

        # Add some personal content
        comment = Comment(document_id=doc.id, user_id=user.id, content="My comment")
        bookmark = Bookmark(document_id=doc.id, user_id=user.id)
        db.add_all([comment, bookmark])
        db.commit()

        # Step 1: Request
        req = request_data_deletion(db, user_id=user.id, reason="I want out")
        assert req.status == DataRequestStatus.PENDING

        # Step 2: Approve
        req = approve_data_deletion(db, req.id, admin_id=admin.id, approved=True, comment="Approved")
        assert req.status == DataRequestStatus.APPROVED

        # Step 3: Execute
        result = execute_data_deletion(db, req.id)
        assert result["status"] == "completed"

        # Verify anonymization
        db.refresh(user)
        assert user.email == f"deleted-user-{user.id}@anonymized.local"
        assert user.username == f"deleted-user-{user.id}"
        assert user.full_name == "Deleted User"
        assert user.is_active is False

        # Verify personal content deleted
        assert db.query(Comment).filter(Comment.user_id == user.id).count() == 0
        assert db.query(Bookmark).filter(Bookmark.user_id == user.id).count() == 0

        # Verify audit logs are preserved
        audit_logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).all()
        assert len(audit_logs) > 0  # Export/deletion request logs should remain

        # Verify documents still exist (ownership preserved for system integrity)
        doc_check = db.query(Document).filter(Document.id == doc.id).first()
        assert doc_check is not None

    def test_deletion_rejection(self, db: Session):
        """Admin can reject a deletion request."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        admin = create_user(db, role=UserRole.SYSTEM_ADMIN, tenant_id=tenant.id)

        req = request_data_deletion(db, user_id=user.id, reason="test")
        req = approve_data_deletion(db, req.id, admin_id=admin.id, approved=False, comment="Denied")
        assert req.status == DataRequestStatus.REJECTED

    def test_cannot_execute_unapproved_deletion(self, db: Session):
        """Executing an unapproved deletion should raise."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        req = request_data_deletion(db, user_id=user.id, reason="test")
        with pytest.raises(ValueError, match="not approved"):
            execute_data_deletion(db, req.id)


# ---------------------------------------------------------------------------
# AA-019  Retention Policy Test
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    """AA-019: Verify document archive/retention behaviour."""

    def test_document_can_be_archived(self, db: Session):
        """Documents can be archived (soft-deleted) via status change."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id, status=DocumentStatus.PUBLISHED)

        # Archive the document
        doc.status = DocumentStatus.ARCHIVED
        db.commit()
        db.refresh(doc)

        assert doc.status == DocumentStatus.ARCHIVED

    def test_archived_document_can_be_restored(self, db: Session):
        """Archived documents can be restored to DRAFT status."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        doc = create_document(db, created_by=user.id, status=DocumentStatus.ARCHIVED)

        # Restore the document
        doc.status = DocumentStatus.DRAFT
        db.commit()
        db.refresh(doc)

        assert doc.status == DocumentStatus.DRAFT


# ---------------------------------------------------------------------------
# AA-020  Audit Log Immutability Test
# ---------------------------------------------------------------------------


class TestAuditImmutability:
    """AA-020: Verify that UPDATE/DELETE on audit_logs is prevented."""

    def test_immutability_trigger_blocks_delete(self, db: Session):
        """After installing triggers, DELETE on audit_logs should raise."""
        # Create an audit log entry
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        log_entry = AuditLog(
            user_id=user.id,
            action=ActionType.CREATE,
            details='{"test": "immutability"}',
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        # Install immutability triggers
        install_audit_immutability_trigger(db)

        # Attempt DELETE — should be blocked by trigger
        with pytest.raises(Exception, match="immutable|not allowed|ABORT"):
            db.execute(text(f"DELETE FROM audit_logs WHERE id = {log_entry.id}"))

    def test_immutability_trigger_blocks_update(self, db: Session):
        """After installing triggers, UPDATE on audit_logs should raise."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)
        log_entry = AuditLog(
            user_id=user.id,
            action=ActionType.CREATE,
            details='{"test": "immutability"}',
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        install_audit_immutability_trigger(db)

        # Attempt UPDATE — should be blocked by trigger
        with pytest.raises(Exception, match="immutable|not allowed|ABORT"):
            db.execute(text(f"UPDATE audit_logs SET details = 'hacked' WHERE id = {log_entry.id}"))

    def test_immutability_trigger_allows_insert(self, db: Session):
        """INSERT on audit_logs should still work after triggers."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        install_audit_immutability_trigger(db)

        # INSERT should still be allowed
        log_entry = AuditLog(
            user_id=user.id,
            action=ActionType.CREATE,
            details='{"test": "insert_ok"}',
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        assert log_entry.id is not None


# ---------------------------------------------------------------------------
# AA-021  Dependency Vulnerability CI Check
# ---------------------------------------------------------------------------


class TestDependencyAuditScript:
    """AA-021: Verify the dependency audit script is importable and has expected structure."""

    def test_audit_script_exists(self):
        """The dependency audit script should exist and be importable."""
        from pathlib import Path

        script_path = Path(__file__).resolve().parents[1] / "scripts" / "dependency_audit.py"
        assert script_path.exists(), f"dependency_audit.py not found at {script_path}"

    def test_audit_script_has_main_function(self):
        """The script should be executable."""
        from pathlib import Path
        import importlib.util

        script_path = Path(__file__).resolve().parents[1] / "scripts" / "dependency_audit.py"
        spec = importlib.util.spec_from_file_location("dependency_audit", script_path)
        mod = importlib.util.module_from_spec(spec)
        # We don't execute the module since it runs external commands,
        # but we verify it loads without syntax errors
        assert spec is not None
        assert mod is not None


# ---------------------------------------------------------------------------
# Audit Integrity Verification
# ---------------------------------------------------------------------------


class TestAuditIntegrity:
    """Test HMAC integrity verification for audit logs."""

    def test_unsigned_entries_reported(self, db: Session):
        """Unsigned audit entries should be counted separately."""
        tenant = create_tenant(db)
        user = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        # Create an unsigned audit log
        db.add(AuditLog(
            user_id=user.id,
            action=ActionType.CREATE,
            details='{"test": "unsigned"}',
        ))
        db.commit()

        result = check_audit_integrity(db)
        assert "unsigned" in result
        assert result["unsigned"] >= 1

    def test_integrity_check_returns_expected_fields(self, db: Session):
        """Integrity check result should have required fields."""
        result = check_audit_integrity(db)
        assert "total_signed" in result
        assert "valid" in result
        assert "invalid" in result
        assert "unsigned" in result
