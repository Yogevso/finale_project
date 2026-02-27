"""Tests for Versions API"""

import uuid

from fastapi.testclient import TestClient

from app.models import Document, DocumentStatus, Tenant, Version


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
