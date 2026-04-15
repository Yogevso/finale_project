"""Wave AE — AI Assistant Security & Audit Trail tests.

AE-012: Editor asks AI to publish → denied (requires MANAGER+).
AE-013: Editor asks AI to approve own submission → denied (self-approval blocked).
AE-014: Editor asks AI to set document status to 'active' → denied (status removed).
AE-015: AI write operation creates audit log entry attributed to requesting user.
AE-016: Editor's AI tool cannot read/modify versions from another tenant.
AE-017: Manager's AI tool cannot cancel scheduled publish from another tenant.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.assistant.tools.document_tools import EditDocumentTool
from app.assistant.tools.review_tools import SubmitReviewTool
from app.assistant.tools.version_tools import PublishDocumentTool
from app.assistant.tools.version_tools_ext import (
    CancelScheduledPublishTool,
    GetDocumentVersionStatsTool,
    GetVersionDetailsTool,
)
from app.models import (
    AuditLog,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReviewRequest,
    ReviewStatus,
    UserRole,
    Version,
    VersionBumpType,
)
from tests.factories import create_document, create_tenant, create_user


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _create_doc_with_version(
    db,
    *,
    tenant_id: int | None = None,
    created_by: int,
    status: DocumentStatus = DocumentStatus.DRAFT,
    published: bool = False,
) -> tuple[Document, Version]:
    """Helper to create a document with a single version."""
    doc = create_document(
        db,
        created_by=created_by,
        tenant_id=tenant_id,
        status=status,
        visibility=DocumentVisibility.INTERNAL,
    )
    v = Version(
        document_id=doc.id,
        version_number=1,
        semantic_version="1.0.0",
        bump_type=VersionBumpType.PATCH,
        content="<p>Hello world</p>",
        changes_summary="Initial content",
        is_published=published,
        published_at=datetime.utcnow() if published else None,
        published_by=created_by if published else None,
        created_by=created_by,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return doc, v


# ---------------------------------------------------------------------------
# AE-012: Editor asks AI to publish → denied (requires MANAGER+)
# ---------------------------------------------------------------------------


class TestAE012EditorCannotPublish:
    """PublishDocumentTool should deny editors since publishing requires MANAGER+."""

    def test_editor_role_check(self, db):
        """The tool's required_role blocks editors from even executing."""
        tool = PublishDocumentTool()
        # After AE-001, required_role should be MANAGER
        assert tool.required_role == "MANAGER"

    def test_editor_user_can_execute_returns_false(self, db):
        """user_can_execute() must return False for EDITOR role."""
        t = create_tenant(db, name="AE12 Co", slug="ae12")
        editor = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t.id,
            email="ae12-ed@test.com",
            username="ae12_editor",
        )
        tool = PublishDocumentTool()
        assert tool.user_can_execute(editor) is False

    def test_manager_can_execute(self, db):
        """Managers should pass the role check."""
        t = create_tenant(db, name="AE12b Co", slug="ae12b")
        manager = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t.id,
            email="ae12-mgr@test.com",
            username="ae12_mgr",
        )
        tool = PublishDocumentTool()
        assert tool.user_can_execute(manager) is True


# ---------------------------------------------------------------------------
# AE-013: Editor asks AI to approve own submission → denied
# ---------------------------------------------------------------------------


class TestAE013SelfApprovalBlocked:
    """SubmitReviewTool must block self-approval (submitter == reviewer)."""

    def test_self_approval_rejected(self, db):
        t = create_tenant(db, name="AE13 Co", slug="ae13")
        editor = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t.id,
            email="ae13-ed@test.com",
            username="ae13_editor",
        )
        doc, version = _create_doc_with_version(
            db,
            tenant_id=t.id,
            created_by=editor.id,
            status=DocumentStatus.PENDING_REVIEW,
        )
        # Create review where editor is the submitter
        review = ReviewRequest(
            document_id=doc.id,
            version_id=version.id,
            submitted_by=editor.id,
            reviewed_by=editor.id,
            status=ReviewStatus.PENDING,
            submitted_at=datetime.utcnow(),
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        tool = SubmitReviewTool()
        result = _run(
            tool.execute(
                editor,
                tenant_id=t.id,
                params={"review_id": review.id, "decision": "approve"},
                db=db,
            )
        )
        # The ApproveReviewCommandHandler should block self-approval
        assert result["success"] is False
        assert (
            "cannot approve" in result.get("error", "").lower()
            or "own" in result.get("error", "").lower()
        )

    def test_self_rejection_also_blocked(self, db):
        """Reject path should also block self-rejection."""
        t = create_tenant(db, name="AE13b Co", slug="ae13b")
        editor = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t.id,
            email="ae13b-ed@test.com",
            username="ae13b_editor",
        )
        doc, version = _create_doc_with_version(
            db,
            tenant_id=t.id,
            created_by=editor.id,
            status=DocumentStatus.PENDING_REVIEW,
        )
        review = ReviewRequest(
            document_id=doc.id,
            version_id=version.id,
            submitted_by=editor.id,
            reviewed_by=editor.id,
            status=ReviewStatus.PENDING,
            submitted_at=datetime.utcnow(),
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        tool = SubmitReviewTool()
        result = _run(
            tool.execute(
                editor,
                tenant_id=t.id,
                params={"review_id": review.id, "decision": "reject"},
                db=db,
            )
        )
        assert result["success"] is False
        assert (
            "own" in result.get("error", "").lower() or "cannot" in result.get("error", "").lower()
        )


# ---------------------------------------------------------------------------
# AE-014: Editor asks AI to set document status to 'active' → denied
# ---------------------------------------------------------------------------


class TestAE014StatusFieldRemoved:
    """EditDocumentTool should reject status changes entirely."""

    def test_status_not_in_parameters(self, db):
        """The 'status' property must be absent from the tool parameter schema."""
        tool = EditDocumentTool()
        props = tool.parameters.get("properties", {})
        assert "status" not in props

    def test_status_param_rejected_at_runtime(self, db):
        """Even if a status param is somehow passed, it must be rejected."""
        t = create_tenant(db, name="AE14 Co", slug="ae14")
        editor = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t.id,
            email="ae14-ed@test.com",
            username="ae14_editor",
        )
        doc = create_document(
            db,
            created_by=editor.id,
            tenant_id=t.id,
            status=DocumentStatus.DRAFT,
        )

        tool = EditDocumentTool()
        result = _run(
            tool.execute(
                editor,
                tenant_id=t.id,
                params={"document_id": doc.id, "status": "active"},
                db=db,
            )
        )
        assert result["success"] is False
        assert (
            "status" in result.get("error", "").lower()
            or "workflow" in result.get("error", "").lower()
        )

        # Verify the status wasn't changed
        db.refresh(doc)
        assert doc.status == DocumentStatus.DRAFT


# ---------------------------------------------------------------------------
# AE-015: AI write operation creates audit log entry
# ---------------------------------------------------------------------------


class TestAE015AuditLogCreated:
    """Write tools must create AuditLog entries attributed to the requesting user."""

    def test_document_edit_creates_audit(self, db):
        t = create_tenant(db, name="AE15 Co", slug="ae15")
        editor = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t.id,
            email="ae15-ed@test.com",
            username="ae15_editor",
        )
        doc = create_document(
            db,
            created_by=editor.id,
            tenant_id=t.id,
        )

        # Count existing audit logs
        before = db.query(AuditLog).filter(AuditLog.user_id == editor.id).count()

        tool = EditDocumentTool()
        result = _run(
            tool.execute(
                editor,
                tenant_id=t.id,
                params={"document_id": doc.id, "title": "Updated Title"},
                db=db,
            )
        )
        assert result["success"] is True

        after = db.query(AuditLog).filter(AuditLog.user_id == editor.id).count()
        assert after > before, "Expected an AuditLog entry to be created"

        # Verify the audit log details
        log = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == editor.id)
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert log is not None
        assert "AI assistant" in (log.details or "")

    def test_document_create_creates_audit(self, db):
        from app.assistant.tools.document_tools import CreateDocumentTool

        t = create_tenant(db, name="AE15b Co", slug="ae15b")
        editor = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t.id,
            email="ae15b-ed@test.com",
            username="ae15b_editor",
        )
        before = db.query(AuditLog).filter(AuditLog.user_id == editor.id).count()

        tool = CreateDocumentTool()
        result = _run(
            tool.execute(
                editor,
                tenant_id=t.id,
                params={"title": "New Doc via AI"},
                db=db,
            )
        )
        assert result["success"] is True

        after = db.query(AuditLog).filter(AuditLog.user_id == editor.id).count()
        assert after > before


# ---------------------------------------------------------------------------
# AE-016: Editor's AI tool cannot read/modify versions from another tenant
# ---------------------------------------------------------------------------


class TestAE016CrossTenantVersionDenied:
    """Tenant-scoped tools must not allow cross-tenant version reads."""

    def test_get_version_details_cross_tenant(self, db):
        t1 = create_tenant(db, name="AE16 A", slug="ae16a")
        t2 = create_tenant(db, name="AE16 B", slug="ae16b")
        user1 = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t1.id,
            email="ae16-u1@test.com",
            username="ae16_user1",
        )
        user2 = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t2.id,
            email="ae16-u2@test.com",
            username="ae16_user2",
        )
        # Create document in tenant 2
        doc2, v2 = _create_doc_with_version(
            db,
            tenant_id=t2.id,
            created_by=user2.id,
        )

        # User from tenant 1 tries to read version from tenant 2
        tool = GetVersionDetailsTool()
        result = _run(
            tool.execute(
                user1,
                tenant_id=t1.id,
                params={"version_id": v2.id},
                db=db,
            )
        )
        assert result["success"] is False
        assert "not found" in result["result"].lower()

    def test_get_version_stats_cross_tenant(self, db):
        t1 = create_tenant(db, name="AE16c A", slug="ae16ca")
        t2 = create_tenant(db, name="AE16c B", slug="ae16cb")
        user1 = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t1.id,
            email="ae16c-u1@test.com",
            username="ae16c_user1",
        )
        user2 = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t2.id,
            email="ae16c-u2@test.com",
            username="ae16c_user2",
        )
        doc2, _ = _create_doc_with_version(
            db,
            tenant_id=t2.id,
            created_by=user2.id,
        )

        tool = GetDocumentVersionStatsTool()
        result = _run(
            tool.execute(
                user1,
                tenant_id=t1.id,
                params={"document_id": doc2.id},
                db=db,
            )
        )
        assert result["success"] is False
        assert "not found" in result["result"].lower()

    def test_same_tenant_version_access_allowed(self, db):
        """Sanity check: same tenant user CAN read version details."""
        t = create_tenant(db, name="AE16d Co", slug="ae16d")
        user = create_user(
            db,
            role=UserRole.EDITOR,
            tenant_id=t.id,
            email="ae16d-u@test.com",
            username="ae16d_user",
        )
        doc, v = _create_doc_with_version(
            db,
            tenant_id=t.id,
            created_by=user.id,
        )

        tool = GetVersionDetailsTool()
        result = _run(
            tool.execute(
                user,
                tenant_id=t.id,
                params={"version_id": v.id},
                db=db,
            )
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# AE-017: Manager's AI tool cannot cancel scheduled publish from another tenant
# ---------------------------------------------------------------------------


class TestAE017CrossTenantScheduledPublishDenied:
    """CancelScheduledPublishTool must not allow cross-tenant cancellation."""

    def test_cross_tenant_cancel_denied(self, db):
        t1 = create_tenant(db, name="AE17 A", slug="ae17a")
        t2 = create_tenant(db, name="AE17 B", slug="ae17b")
        mgr1 = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t1.id,
            email="ae17-m1@test.com",
            username="ae17_mgr1",
        )
        user2 = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t2.id,
            email="ae17-m2@test.com",
            username="ae17_mgr2",
        )
        # Create document with scheduled publish in tenant 2
        doc2, v2 = _create_doc_with_version(
            db,
            tenant_id=t2.id,
            created_by=user2.id,
        )
        v2.scheduled_publish_at = datetime.utcnow() + timedelta(days=1)
        db.commit()
        db.refresh(v2)

        # Manager from tenant 1 tries to cancel
        tool = CancelScheduledPublishTool()
        result = _run(
            tool.execute(
                mgr1,
                tenant_id=t1.id,
                params={"version_id": v2.id},
                db=db,
            )
        )
        assert result["success"] is False
        assert "not found" in result["result"].lower()

        # Verify the scheduled publish wasn't cancelled
        db.refresh(v2)
        assert v2.scheduled_publish_at is not None

    def test_same_tenant_cancel_allowed(self, db):
        """Sanity check: same-tenant manager CAN cancel scheduled publish."""
        t = create_tenant(db, name="AE17b Co", slug="ae17b2")
        mgr = create_user(
            db,
            role=UserRole.MANAGER,
            tenant_id=t.id,
            email="ae17b-mgr@test.com",
            username="ae17b_mgr",
        )
        doc, v = _create_doc_with_version(
            db,
            tenant_id=t.id,
            created_by=mgr.id,
        )
        v.scheduled_publish_at = datetime.utcnow() + timedelta(days=1)
        db.commit()
        db.refresh(v)

        tool = CancelScheduledPublishTool()
        result = _run(
            tool.execute(
                mgr,
                tenant_id=t.id,
                params={"version_id": v.id},
                db=db,
            )
        )
        assert result["success"] is True
        db.refresh(v)
        assert v.scheduled_publish_at is None
