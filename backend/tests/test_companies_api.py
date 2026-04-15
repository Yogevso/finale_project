"""Regression tests for company document semantics in management APIs."""

from app.models import Document, DocumentStatus, DocumentVisibility, Version


def _create_document(
    db,
    *,
    title: str,
    document_number: str,
    created_by: int,
    status: DocumentStatus = DocumentStatus.ACTIVE,
    visibility: DocumentVisibility = DocumentVisibility.INTERNAL,
    tenant_id: int | None = None,
) -> Document:
    doc = Document(
        title=title,
        document_number=document_number,
        description=f"{title} description",
        status=status,
        visibility=visibility,
        created_by=created_by,
        tenant_id=tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestCompanyDocumentSemantics:
    def test_company_detail_exposes_owned_assigned_and_customer_visible_counts(
        self, client, db, system_admin_headers, test_admin, test_tenant, test_tenant_2
    ):
        _create_document(
            db,
            title="Owned Internal Doc",
            document_number="DOC-OWN-001",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            tenant_id=test_tenant.id,
        )
        assigned_active_doc = _create_document(
            db,
            title="Assigned Active Company Doc",
            document_number="DOC-ASG-001",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )
        assigned_draft_doc = _create_document(
            db,
            title="Assigned Draft Company Doc",
            document_number="DOC-ASG-002",
            created_by=test_admin.id,
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )
        _create_document(
            db,
            title="Public Active Doc",
            document_number="DOC-PUB-001",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=test_tenant_2.id,
        )

        assigned_active_doc.assigned_companies.append(test_tenant)
        assigned_draft_doc.assigned_companies.append(test_tenant)
        db.commit()

        response = client.get(f"/api/v1/companies/{test_tenant.id}", headers=system_admin_headers)
        assert response.status_code == 200
        payload = response.json()

        assert payload["owned_document_count"] == 1
        assert payload["assigned_document_count"] == 2
        # ACTIVE public + ACTIVE company assigned
        assert payload["customer_visible_document_count"] == 2
        # Backward-compatible alias maps to assigned semantics.
        assert payload["document_count"] == payload["assigned_document_count"] == 2

    def test_company_documents_default_scope_returns_assigned_documents(
        self, client, db, system_admin_headers, test_admin, test_tenant, test_tenant_2
    ):
        _create_document(
            db,
            title="Owned Only Doc",
            document_number="DOC-OWN-010",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            tenant_id=test_tenant.id,
        )
        assigned_doc = _create_document(
            db,
            title="Assigned Doc",
            document_number="DOC-ASG-010",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )
        assigned_doc.assigned_companies.append(test_tenant)
        db.commit()

        response = client.get(
            f"/api/v1/companies/{test_tenant.id}/documents", headers=system_admin_headers
        )
        assert response.status_code == 200
        payload = response.json()
        titles = [item["title"] for item in payload["items"]]

        assert payload["scope"] == "assigned"
        assert "Assigned Doc" in titles
        assert "Owned Only Doc" not in titles

    def test_customer_visible_count_matches_portal_documents_total(
        self,
        client,
        db,
        system_admin_headers,
        customer_headers,
        test_admin,
        test_tenant,
        test_tenant_2,
    ):
        public_doc = _create_document(
            db,
            title="Portal Public Doc",
            document_number="DOC-PUB-100",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=test_tenant_2.id,
        )
        assigned_active_doc = _create_document(
            db,
            title="Portal Assigned Active Doc",
            document_number="DOC-ASG-100",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )
        assigned_draft_doc = _create_document(
            db,
            title="Portal Assigned Draft Doc",
            document_number="DOC-ASG-101",
            created_by=test_admin.id,
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )
        other_company_assigned_doc = _create_document(
            db,
            title="Other Company Assigned Doc",
            document_number="DOC-ASG-102",
            created_by=test_admin.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            tenant_id=test_tenant_2.id,
        )

        # H-23: Portal filter requires at least one published version
        for doc in [public_doc, assigned_active_doc]:
            db.add(
                Version(
                    document_id=doc.id,
                    version_number=1,
                    content="published content",
                    changes_summary="Initial",
                    created_by=test_admin.id,
                    is_published=True,
                    semantic_version="1.0.0",
                    bump_type="MAJOR",
                )
            )

        assigned_active_doc.assigned_companies.append(test_tenant)
        assigned_draft_doc.assigned_companies.append(test_tenant)
        other_company_assigned_doc.assigned_companies.append(test_tenant_2)
        db.commit()

        portal_response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert portal_response.status_code == 200
        portal_total = portal_response.json()["total"]

        company_response = client.get(
            f"/api/v1/companies/{test_tenant.id}", headers=system_admin_headers
        )
        assert company_response.status_code == 200
        company_payload = company_response.json()

        assert portal_total == 2
        assert company_payload["customer_visible_document_count"] == portal_total

    def test_company_documents_supports_keyset_cursor_pagination(
        self, client, db, system_admin_headers, test_admin, test_tenant, test_tenant_2
    ):
        for index in range(5):
            doc = _create_document(
                db,
                title=f"Assigned Cursor Doc {index}",
                document_number=f"DOC-ASG-CURSOR-{index:03d}",
                created_by=test_admin.id,
                status=DocumentStatus.ACTIVE,
                visibility=DocumentVisibility.COMPANY,
                tenant_id=test_tenant_2.id,
            )
            doc.assigned_companies.append(test_tenant)
        db.commit()

        first_page = client.get(
            f"/api/v1/companies/{test_tenant.id}/documents?per_page=2",
            headers=system_admin_headers,
        )
        assert first_page.status_code == 200
        first_payload = first_page.json()
        assert len(first_payload["items"]) == 2
        assert first_payload["has_more"] is True
        assert first_payload["next_cursor"] is not None

        second_page = client.get(
            f"/api/v1/companies/{test_tenant.id}/documents?per_page=2&cursor={first_payload['next_cursor']}",
            headers=system_admin_headers,
        )
        assert second_page.status_code == 200
        second_payload = second_page.json()
        assert len(second_payload["items"]) == 2

        first_ids = {item["id"] for item in first_payload["items"]}
        second_ids = {item["id"] for item in second_payload["items"]}
        assert first_ids.isdisjoint(second_ids)
