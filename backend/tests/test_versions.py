"""Tests for Versions API"""

import json
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    Version,
)
from app.services.outbox import OutboxDomainEventDispatcher
from app.services.version_service import VersionService


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
        created_payload = create_resp.json()
        version_id = created_payload["id"]
        headers = {**headers, "If-Match": created_payload["etag"]}

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

    def test_publish_chaos_failure_rolls_back_mid_transaction(
        self,
        client: TestClient,
        db,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        monkeypatch,
    ):
        """Simulate publish crash and verify state remains at pre-publish values."""
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Chaos publish candidate", "changes_summary": "chaos"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "ready for chaos approval"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        document_before = db.query(Document).filter(Document.id == sample_document["id"]).first()
        version_before = db.query(Version).filter(Version.id == version_id).first()
        assert document_before is not None
        assert version_before is not None
        assert document_before.status == DocumentStatus.APPROVED
        assert version_before.is_published is False

        def _raise_mid_publish(_self, _event) -> None:  # noqa: ANN001
            raise RuntimeError("chaos publish failure")

        monkeypatch.setattr(OutboxDomainEventDispatcher, "dispatch", _raise_mid_publish)

        with pytest.raises(RuntimeError, match="chaos publish failure"):
            client.post(
                f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
                headers=system_admin_headers,
            )

        document_after = db.query(Document).filter(Document.id == sample_document["id"]).first()
        version_after = db.query(Version).filter(Version.id == version_id).first()
        assert document_after is not None
        assert version_after is not None
        assert document_after.status == DocumentStatus.APPROVED
        assert version_after.is_published is False
        assert version_after.published_at is None
        assert version_after.published_by is None

    def test_publish_blocks_on_invalid_company_audience_when_enforcement_enabled(
        self,
        client: TestClient,
        db,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", True)

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Kill-switch control", "changes_summary": "pre-enforcement"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "review for enforcement-on test"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        document = db.query(Document).filter(Document.id == sample_document["id"]).first()
        assert document is not None
        document.visibility = DocumentVisibility.COMPANY
        document.assigned_companies = []
        db.commit()

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=system_admin_headers,
        )
        assert publish_resp.status_code == 400
        assert (
            "Company visibility requires at least one assigned company"
            in publish_resp.json()["detail"]
        )

    def test_publish_returns_advisory_warning_when_audience_enforcement_disabled(
        self,
        client: TestClient,
        db,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", False)

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Kill-switch advisory", "changes_summary": "enforcement off"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "review for enforcement-off test"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        document = db.query(Document).filter(Document.id == sample_document["id"]).first()
        assert document is not None
        document.visibility = DocumentVisibility.COMPANY
        document.assigned_companies = []
        db.commit()

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=system_admin_headers,
        )
        assert publish_resp.status_code == 200
        payload = publish_resp.json()
        assert payload["is_published"] is True
        assert payload["warnings"]
        assert any("Audience enforcement disabled" in warning for warning in payload["warnings"])

    def test_publish_blocks_when_audience_validation_service_unreachable_and_safe_mode_disabled(
        self,
        client: TestClient,
        db,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", True)
        monkeypatch.setattr(settings, "AUDIENCE_VALIDATION_SAFE_MODE_ENABLED", False)

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Safe mode off", "changes_summary": "unreachable validation"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "ready for safe-mode off check"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        def _raise_unreachable(_document) -> None:  # noqa: ANN001
            raise ConnectionError("audience validation unavailable")

        monkeypatch.setattr(
            VersionService,
            "_run_publish_audience_validation_gate",
            staticmethod(_raise_unreachable),
        )

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=system_admin_headers,
        )
        assert publish_resp.status_code == 400
        assert "Audience validation service is unavailable" in publish_resp.json()["detail"]

        version_after = db.query(Version).filter(Version.id == version_id).first()
        assert version_after is not None
        assert version_after.is_published is False

    def test_publish_safe_mode_allows_when_audience_validation_service_unreachable(
        self,
        client: TestClient,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", True)
        monkeypatch.setattr(settings, "AUDIENCE_VALIDATION_SAFE_MODE_ENABLED", True)

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Safe mode on", "changes_summary": "unreachable validation fallback"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "ready for safe-mode on check"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        def _raise_unreachable(_document) -> None:  # noqa: ANN001
            raise TimeoutError("audience validation timeout")

        monkeypatch.setattr(
            VersionService,
            "_run_publish_audience_validation_gate",
            staticmethod(_raise_unreachable),
        )

        publish_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
            headers=system_admin_headers,
        )
        assert publish_resp.status_code == 200
        payload = publish_resp.json()
        assert payload["is_published"] is True
        assert payload["warnings"]
        assert any(
            "safe-mode fallback allowed publish" in warning for warning in payload["warnings"]
        )

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

    def test_schedule_publish_rejects_when_latest_review_is_not_approved(
        self,
        client: TestClient,
        db,
        admin_token: str,
        sample_document: dict,
        test_admin,
    ):
        """Scheduling should fail when latest review record is pending/rejected."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Schedule candidate", "changes_summary": "ready"},
        )
        version_id = create_resp.json()["id"]

        approved_review = ReviewRequest(
            document_id=sample_document["id"],
            version_id=version_id,
            submitted_by=test_admin.id,
            status=ReviewStatus.APPROVED,
            submitted_at=datetime.utcnow() - timedelta(minutes=5),
            reviewed_at=datetime.utcnow() - timedelta(minutes=4),
        )
        latest_pending_review = ReviewRequest(
            document_id=sample_document["id"],
            version_id=version_id,
            submitted_by=test_admin.id,
            status=ReviewStatus.PENDING,
            submitted_at=datetime.utcnow(),
        )
        db.add_all([approved_review, latest_pending_review])
        db.commit()

        schedule_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/schedule-publish",
            headers=headers,
            json={"scheduled_publish_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat()},
        )
        assert schedule_resp.status_code == 400
        assert "latest review is not approved" in schedule_resp.json()["detail"]

    def test_schedule_publish_and_cancel_manage_audience_snapshots(
        self,
        client: TestClient,
        system_admin_headers: dict,
        manager_headers: dict,
        sample_document: dict,
        test_tenant,
    ):
        """Scheduling captures audience snapshots and cancelling clears them."""
        headers = system_admin_headers

        update_doc_resp = client.put(
            f"/api/v1/documents/{sample_document['id']}",
            headers={**headers, "If-Match": sample_document["etag"]},
            json={
                "visibility": "company",
                "reason": "Restrict scheduled publish to customer audience",
                "company_ids": [test_tenant.id],
            },
        )
        assert update_doc_resp.status_code == 200

        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Scheduled company release", "changes_summary": "v2"},
        )
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=headers,
            json={"version_id": version_id, "message": "approve for schedule"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        scheduled_at = (datetime.utcnow() + timedelta(minutes=45)).isoformat()
        schedule_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/schedule-publish",
            headers=headers,
            json={"scheduled_publish_at": scheduled_at},
        )
        assert schedule_resp.status_code == 200

        version_after_schedule = client.get(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
        )
        assert version_after_schedule.status_code == 200
        schedule_payload = version_after_schedule.json()
        assert schedule_payload["audience_visibility_snapshot"] == "company"
        assert sorted(json.loads(schedule_payload["audience_company_ids_snapshot"])) == [
            test_tenant.id
        ]

        cancel_resp = client.delete(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/schedule-publish",
            headers=headers,
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["version_id"] == version_id

        version_after_cancel = client.get(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}",
            headers=headers,
        )
        assert version_after_cancel.status_code == 200
        cancel_payload = version_after_cancel.json()
        assert cancel_payload["audience_visibility_snapshot"] is None
        assert cancel_payload["audience_company_ids_snapshot"] is None

    def test_process_scheduled_publish_blocks_when_latest_review_becomes_pending(
        self,
        client: TestClient,
        db,
        system_admin_headers: dict,
        manager_headers: dict,
        test_admin,
        sample_document: dict,
    ):
        """Processor must refuse scheduled publish if latest review is no longer approved."""
        create_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=system_admin_headers,
            json={"content": "Scheduled candidate", "changes_summary": "v2"},
        )
        assert create_resp.status_code == 201
        version_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/v1/reviews/documents/{sample_document['id']}/submit",
            headers=system_admin_headers,
            json={"version_id": version_id, "message": "approve this for scheduler"},
        )
        assert submit_resp.status_code in [200, 201]
        review_id = submit_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/reviews/{review_id}/approve",
            headers=manager_headers,
            json={"comments": "approved"},
        )
        assert approve_resp.status_code == 200

        schedule_resp = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/schedule-publish",
            headers=system_admin_headers,
            json={"scheduled_publish_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()},
        )
        assert schedule_resp.status_code == 200

        newer_pending_review = ReviewRequest(
            document_id=sample_document["id"],
            version_id=version_id,
            submitted_by=test_admin.id,
            status=ReviewStatus.PENDING,
            submitted_at=datetime.utcnow(),
        )
        db.add(newer_pending_review)

        version = db.query(Version).filter(Version.id == version_id).first()
        assert version is not None
        version.scheduled_publish_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()

        process_resp = client.post(
            "/api/v1/scheduled-publishes/process",
            headers=system_admin_headers,
            params={"batch_size": 10},
        )
        assert process_resp.status_code == 200
        report = process_resp.json()
        assert report["processed"] == 1
        assert report["published"] == 0
        assert report["failed_validation"] == 1
        assert any(
            "Latest review is not approved at scheduled execution time" in error["reason"]
            for error in report["errors"]
        )

        db.refresh(version)
        assert version.is_published is False

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

    def test_create_version_keeps_active_public_document_available(
        self,
        client: TestClient,
        db,
        admin_token: str,
        customer_headers: dict,
        public_document: Document,
    ):
        """Creating a draft candidate should not unpublish an already active document."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        before_public = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert before_public.status_code == 200
        before_portal = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert before_portal.status_code == 200

        create_resp = client.post(
            f"/api/v1/documents/{public_document.id}/versions",
            headers=headers,
            json={"content": "Drafting next release", "changes_summary": "WIP vNext"},
        )
        assert create_resp.status_code == 201

        db.refresh(public_document)
        assert public_document.status == DocumentStatus.ACTIVE

        after_public = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert after_public.status_code == 200
        after_portal = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert after_portal.status_code == 200

    def test_create_version_uses_version_number_fallback_for_invalid_semver(
        self, client: TestClient, db, admin_token: str, sample_document: dict
    ):
        """Malformed semantic versions should fall back to version_number.0.0 before bumping."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        existing = (
            db.query(Version)
            .filter(Version.document_id == sample_document["id"])
            .order_by(Version.version_number.desc())
            .first()
        )
        assert existing is not None
        existing.version_number = 3
        existing.semantic_version = "bad-value"
        db.commit()

        response = client.post(
            f"/api/v1/documents/{sample_document['id']}/versions",
            headers=headers,
            json={"content": "Fallback semver content", "changes_summary": "fallback"},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["version_number"] == 4
        assert payload["semantic_version"] == "3.0.1"

    def test_versions_endpoints_are_tenant_scoped(
        self, client: TestClient, auth_headers: dict, db, test_user
    ):
        """Non-system users should not access versions of cross-tenant documents."""
        tenant_a = Tenant(
            name="Versions Tenant A",
            slug=f"versions-tenant-a-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        tenant_b = Tenant(
            name="Versions Tenant B",
            slug=f"versions-tenant-b-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        db.add_all([tenant_a, tenant_b])
        db.commit()
        db.refresh(tenant_a)
        db.refresh(tenant_b)

        test_user.tenant_id = tenant_a.id
        db.commit()

        cross_tenant_doc = Document(
            title="Cross Tenant Version Doc",
            document_number=f"DOC-XTV-{uuid.uuid4().hex[:6].upper()}",
            description="Should be hidden by tenant scope",
            status=DocumentStatus.DRAFT,
            created_by=test_user.id,
            tenant_id=tenant_b.id,
        )
        db.add(cross_tenant_doc)
        db.commit()
        db.refresh(cross_tenant_doc)

        list_response = client.get(
            f"/api/v1/documents/{cross_tenant_doc.id}/versions", headers=auth_headers
        )
        assert list_response.status_code == 404
