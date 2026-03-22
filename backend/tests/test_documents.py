"""Document Tests"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    ActionType,
    AuditLog,
    Document,
    DocumentNumberSequence,
    DocumentStatus,
    DocumentVisibility,
    Platform,
    Tenant,
    Topic,
    User,
    UserRole,
)
from app.schemas import DocumentCreate, DocumentUpdate
from app.security import get_password_hash
from app.services.document_service import DocumentService

DEFAULT_PLATFORM = "Core Platform"


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _document_create_payload(**overrides):
    payload = {
        "title": "Test Document",
        "platform": DEFAULT_PLATFORM,
        "status": "draft",
    }
    payload.update(overrides)
    return payload


def test_create_document(client, auth_headers):
    """Test document creation"""
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json=_document_create_payload(
            description="This is a test document",
            category="Testing",
            tags="test,sample",
        ),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Document"
    assert data["status"] == "draft"
    assert "document_number" in data
    assert data["document_number"].startswith("DOC-")


def test_create_company_visible_document_requires_company_assignment(client, auth_headers):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json=_document_create_payload(
            title="Company Scoped Doc",
            visibility="company",
        ),
    )

    assert response.status_code == 400
    assert "at least one assigned company" in response.json()["detail"]


def test_create_document_requires_platform(client, auth_headers):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={"title": "Missing Platform", "status": "draft"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Platform is required"


def test_create_company_visible_document_with_assignment(
    client, auth_headers, test_tenant
):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json=_document_create_payload(
            title="Company Scoped Doc",
            visibility="company",
            company_ids=[test_tenant.id],
        ),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["visibility"] == "company"
    assert sorted(company["id"] for company in payload["assigned_companies"]) == [test_tenant.id]


def test_create_non_company_document_rejects_company_assignments(client, auth_headers, test_tenant):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json=_document_create_payload(
            title="Internal Doc With Invalid Company Assignments",
            visibility="internal",
            company_ids=[test_tenant.id],
        ),
    )

    assert response.status_code == 400
    assert "Company assignments require company visibility" in response.json()["detail"]
    assert response.json()["error_code"] == "invalid_company_set"


def test_create_company_visible_document_rejects_inactive_companies(
    client, auth_headers, db, test_tenant
):
    test_tenant.is_active = False
    db.commit()

    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json=_document_create_payload(
            title="Company Doc With Inactive Assignment",
            visibility="company",
            company_ids=[test_tenant.id],
        ),
    )

    assert response.status_code == 400
    assert "Inactive companies cannot be assigned to documents" in response.json()["detail"]
    assert response.json()["error_code"] == "inactive_company_assignment"


def test_update_document_rejects_company_visibility_without_assignments(
    client, admin_headers, db, test_admin
):
    doc = Document(
        title="Visibility Transition Target",
        document_number="DOC-VIS-TRANS-0001",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.put(
        f"/api/v1/documents/{doc.id}",
        headers={**admin_headers, "If-Match": doc.etag},
        json={
            "visibility": "company",
            "reason": "Move to company visibility for customer rollout",
        },
    )

    assert response.status_code == 400
    assert "at least one assigned company" in response.json()["detail"]


def test_update_document_allows_company_visibility_with_assignments(
    client, admin_headers, db, test_admin, test_tenant
):
    doc = Document(
        title="Visibility Transition With Assignment",
        document_number="DOC-VIS-TRANS-0002",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.put(
        f"/api/v1/documents/{doc.id}",
        headers={**admin_headers, "If-Match": doc.etag},
        json={
            "visibility": "company",
            "reason": "Limit access to assigned companies",
            "company_ids": [test_tenant.id],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["visibility"] == "company"
    assert sorted(company["id"] for company in payload["assigned_companies"]) == [test_tenant.id]


def test_update_document_transition_away_from_company_clears_assignments(
    client, admin_headers, db, test_admin, test_tenant
):
    doc = Document(
        title="Visibility Transition Away",
        document_number="DOC-VIS-TRANS-0003",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    doc.assigned_companies = [test_tenant]
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.put(
        f"/api/v1/documents/{doc.id}",
        headers={**admin_headers, "If-Match": doc.etag},
        json={
            "visibility": "internal",
            "reason": "Revert to internal audience",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["visibility"] == "internal"
    assert payload["assigned_companies"] == []


def test_list_documents(client, auth_headers, db, test_user):
    """Test listing documents"""
    # Create some test documents
    for i in range(5):
        doc = Document(
            title=f"Document {i}",
            document_number=f"DOC-TEST-{i:04d}",
            description=f"Description {i}",
            status=DocumentStatus.ACTIVE,
            category="Test",
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
    db.commit()

    # Get documents
    response = client.get("/api/v1/documents", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["page"] == 1


def test_list_documents_with_pagination(client, auth_headers, db, test_user):
    """Test document listing with pagination"""
    # Create 25 documents
    for i in range(25):
        doc = Document(
            title=f"Document {i}",
            document_number=f"DOC-TEST-{i:04d}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
    db.commit()

    # Get page 1
    response = client.get("/api/v1/documents?page=1&page_size=10", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["total_pages"] == 3
    assert data["page"] == 1


def test_get_document_stats(client, auth_headers, db, test_user):
    """Test dashboard document stats endpoint."""
    statuses = [
        DocumentStatus.ACTIVE,
        DocumentStatus.ACTIVE,
        DocumentStatus.ACTIVE,
        DocumentStatus.APPROVED,
        DocumentStatus.APPROVED,
        DocumentStatus.DRAFT,
        DocumentStatus.ARCHIVED,
    ]
    for index, doc_status in enumerate(statuses, start=1):
        db.add(
            Document(
                title=f"Stats doc {index}",
                document_number=f"DOC-STATS-{index:04d}",
                status=doc_status,
                created_by=test_user.id,
                tenant_id=test_user.tenant_id,
            )
        )
    db.commit()

    response = client.get("/api/v1/documents/stats", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "total": 7,
        "published": 3,
        "approved": 2,
        "draft": 1,
    }


def test_get_document(client, auth_headers, db, test_user):
    """Test getting a single document"""
    # Create document
    doc = Document(
        title="Test Document",
        document_number="DOC-TEST-0001",
        description="Test description",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=test_user.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Get document
    response = client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["title"] == "Test Document"


def test_document_detail_payload_budget_under_50kb(client, admin_headers, db, test_admin, test_tenant):
    """Guardrail: keep /api/v1/documents/{id} payload under the 50KB budget."""
    doc = Document(
        title="Payload Budget Document",
        document_number="DOC-PAYLOAD-0001",
        description="payload-check " * 80,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        category="Performance",
        tags=",".join(f"tag-{index:02d}" for index in range(40)),
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    doc.assigned_companies = [test_tenant]
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.get(f"/api/v1/documents/{doc.id}", headers=admin_headers)

    assert response.status_code == 200
    payload_size_bytes = len(response.content)
    assert payload_size_bytes <= 50 * 1024


def test_get_nonexistent_document(client, auth_headers):
    """Test getting nonexistent document"""
    response = client.get("/api/v1/documents/99999", headers=auth_headers)

    assert response.status_code == 404


def test_update_document(client, auth_headers, db, test_user):
    """Test updating a document"""
    # Create document
    doc = Document(
        title="Original Title",
        document_number="DOC-TEST-0001",
        status=DocumentStatus.DRAFT,
        created_by=test_user.id,
        tenant_id=test_user.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Update document
    headers = {**auth_headers, "If-Match": doc.etag}
    response = client.put(
        f"/api/v1/documents/{doc.id}",
        headers=headers,
        json={"title": "Updated Title", "status": "active"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "active"


def test_delete_document(client, admin_headers, db, test_admin):
    """Test deleting a document (requires manager role or above)"""
    # Create document
    doc = Document(
        title="To Delete",
        document_number="DOC-TEST-0001",
        status=DocumentStatus.DRAFT,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id

    # Delete document - requires MANAGER+ role
    response = client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)

    assert response.status_code == 200

    # Verify deletion
    get_response = client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    assert get_response.status_code == 404


def test_delete_document_forbidden_for_editor(client, auth_headers, db, test_user):
    """Test that EDITOR cannot delete documents"""
    # Create document
    doc = Document(
        title="Cannot Delete",
        document_number="DOC-TEST-0002",
        status=DocumentStatus.DRAFT,
        created_by=test_user.id,
        tenant_id=test_user.tenant_id,
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id

    # Editor should get 403
    response = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert response.status_code == 403
    assert "manager" in response.json()["detail"].lower()


def test_search_documents(client, auth_headers, db, test_user):
    """Test document search"""
    # Create documents with different titles
    documents = [
        Document(
            title="Python Programming Guide",
            document_number="DOC-TEST-0001",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
        Document(
            title="JavaScript Tutorial",
            document_number="DOC-TEST-0002",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
        Document(
            title="Python Best Practices",
            document_number="DOC-TEST-0003",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
    ]
    for doc in documents:
        db.add(doc)
    db.commit()

    # Search for "Python"
    response = client.get("/api/v1/documents?search=Python", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Python" in item["title"] for item in data["items"])


def test_filter_by_status(client, auth_headers, db, test_user):
    """Test filtering documents by status"""
    # Create documents with different statuses
    for status in [DocumentStatus.DRAFT, DocumentStatus.ACTIVE, DocumentStatus.ARCHIVED]:
        for i in range(2):
            doc = Document(
                title=f"{status.value} Document {i}",
                document_number=f"DOC-{status.value.upper()}-{i:04d}",
                status=status,
                created_by=test_user.id,
                tenant_id=test_user.tenant_id,
            )
            db.add(doc)
    db.commit()

    # Filter by ACTIVE status
    response = client.get("/api/v1/documents?status=active", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["status"] == "active" for item in data["items"])


def test_filter_by_visibility(client, auth_headers, db, test_user):
    """Test filtering documents by visibility"""
    docs = [
        Document(
            title="Public document",
            document_number="DOC-VIS-0001",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
        Document(
            title="Internal document",
            document_number="DOC-VIS-0002",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
        Document(
            title="Company document",
            document_number="DOC-VIS-0003",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        ),
    ]
    for doc in docs:
        db.add(doc)
    db.commit()

    response = client.get("/api/v1/documents?visibility=company", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["visibility"] == "company"


def test_create_document_rolls_back_when_initial_version_creation_fails(db, test_user, monkeypatch):
    """Document row should not persist if initial version/audit creation fails."""
    service = DocumentService(db)
    document_data = DocumentCreate(
        title="Atomic rollback doc",
        description="Should rollback on failure",
        platform=DEFAULT_PLATFORM,
    )

    original_add = db.add

    def fail_on_version(instance):
        from app.models import Version

        if isinstance(instance, Version):
            raise RuntimeError("forced version creation failure")
        return original_add(instance)

    monkeypatch.setattr(db, "add", fail_on_version)

    with pytest.raises(RuntimeError, match="forced version creation failure"):
        service.create_document(document_data, test_user)

    assert db.query(Document).filter(Document.title == "Atomic rollback doc").count() == 0


def test_create_document_with_parent_inherits_platform_when_missing(db, test_user):
    service = DocumentService(db)
    parent = service.create_document(
        DocumentCreate(
            title="Parent With Platform",
            description="parent",
            platform="Meteor Lake",
        ),
        test_user,
    )

    child = service.create_document(
        DocumentCreate(
            title="Child Inherits Platform",
            description="child",
            parent_id=parent.id,
        ),
        test_user,
    )

    assert child.parent_id == parent.id
    assert child.platform == parent.platform
    assert child.platform_id == parent.platform_id


def test_generate_document_number_seeds_from_existing_daily_documents(db, test_user):
    service = DocumentService(db)
    today_key = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"DOC-{today_key}"

    existing_numbers = [f"{prefix}-0001", f"{prefix}-0002", f"{prefix}-0003"]
    for index, document_number in enumerate(existing_numbers, start=1):
        db.add(
            Document(
                title=f"Existing {index}",
                document_number=document_number,
                status=DocumentStatus.DRAFT,
                created_by=test_user.id,
            )
        )
    db.commit()

    generated_first = service.generate_document_number()
    generated_second = service.generate_document_number()
    db.commit()

    assert generated_first == f"{prefix}-0004"
    assert generated_second == f"{prefix}-0005"

    sequence_row = db.get(DocumentNumberSequence, today_key)
    assert sequence_row is not None
    assert sequence_row.next_value == 5


def test_delete_document_rolls_back_audit_when_delete_fails(db, test_admin, monkeypatch):
    doc = Document(
        title="Delete rollback document",
        document_number="DOC-DEL-ROLLBACK-0001",
        status=DocumentStatus.DRAFT,
        created_by=test_admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    service = DocumentService(db)
    original_delete = db.delete

    def fail_document_delete(instance):
        if isinstance(instance, Document):
            raise RuntimeError("forced delete failure")
        return original_delete(instance)

    monkeypatch.setattr(db, "delete", fail_document_delete)

    with pytest.raises(RuntimeError, match="forced delete failure"):
        service.delete_document(doc.id, test_admin)

    db.expire_all()
    assert db.query(Document).filter(Document.id == doc.id).count() == 1
    assert (
        db.query(AuditLog)
        .filter(
            AuditLog.document_id == doc.id,
            AuditLog.action == ActionType.DELETE,
        )
        .count()
        == 0
    )


def test_create_document_concurrent_generation_uses_unique_sequences(tmp_path):
    sqlite_path = tmp_path / "doc_number_sequence_contention.db"
    engine = create_engine(
        f"sqlite:///{sqlite_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    today_key = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"DOC-{today_key}"

    with SessionLocal() as setup_db:
        user = User(
            email="sequence@example.com",
            username="sequence-user",
            full_name="Sequence User",
            hashed_password="not-used-in-test",
            role=UserRole.EDITOR,
            is_active=True,
            is_email_verified=True,
        )
        platform = Platform(name="Unspecified", slug="unspecified")
        setup_db.add(user)
        setup_db.add(platform)
        setup_db.flush()

        user_id = user.id
        platform_id = platform.id
        for suffix in (1, 2, 3):
            setup_db.add(
                Document(
                    title=f"Seeded {suffix}",
                    document_number=f"{prefix}-{suffix:04d}",
                    status=DocumentStatus.DRAFT,
                    created_by=user_id,
                    platform=platform.name,
                    platform_id=platform_id,
                )
            )
        setup_db.commit()

    worker_count = 6
    start_barrier = threading.Barrier(worker_count)

    def create_document_in_worker(worker_index: int) -> str:
        with SessionLocal() as worker_db:
            service = DocumentService(worker_db)
            worker_user = worker_db.query(User).filter(User.id == user_id).one()
            start_barrier.wait(timeout=10)
            created = service.create_document(
                DocumentCreate(
                    title=f"Concurrent Document {worker_index}",
                    description="contention test",
                    platform_id=platform_id,
                ),
                worker_user,
            )
            return created.document_number

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        generated_numbers = list(executor.map(create_document_in_worker, range(worker_count)))

    assert len(generated_numbers) == worker_count
    assert len(set(generated_numbers)) == worker_count
    assert all(number.startswith(f"{prefix}-") for number in generated_numbers)

    suffixes = sorted(int(number.split("-")[-1]) for number in generated_numbers)
    assert suffixes == list(range(4, 4 + worker_count))

    with SessionLocal() as verify_db:
        sequence_row = verify_db.get(DocumentNumberSequence, today_key)
        assert sequence_row is not None
        assert sequence_row.next_value == 3 + worker_count


def test_assign_companies_replaces_existing_set_on_each_request(
    client, db, admin_headers, test_admin, test_tenant, test_tenant_2
):
    tenant_three = Tenant(
        name="Assignment Tenant Three",
        slug="assignment-tenant-three",
        is_active=True,
        company_type="customer",
    )
    db.add(tenant_three)
    db.flush()

    document = Document(
        title="Set Semantics Document",
        document_number="DOC-ASG-SET-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    db.refresh(tenant_three)

    first_assign = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": document.etag},
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert first_assign.status_code == 200
    next_etag = first_assign.headers.get("ETag")
    assert next_etag is not None

    first_state = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert first_state.status_code == 200
    assert sorted(company["id"] for company in first_state.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )

    second_assign = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": next_etag},
        json={"company_ids": [test_tenant_2.id, tenant_three.id]},
    )
    assert second_assign.status_code == 200

    second_state = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert second_state.status_code == 200
    assert sorted(company["id"] for company in second_state.json()) == sorted(
        [test_tenant_2.id, tenant_three.id]
    )


def test_assign_companies_is_idempotent_and_rejects_clear_set_for_company_visibility(
    client, db, admin_headers, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="Set Semantics Idempotent Document",
        document_number="DOC-ASG-SET-0002",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    assign_with_duplicates = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": document.etag},
        json={"company_ids": [test_tenant.id, test_tenant.id, test_tenant_2.id]},
    )
    assert assign_with_duplicates.status_code == 200
    next_etag = assign_with_duplicates.headers.get("ETag")
    assert next_etag is not None

    state_after_first_assign = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert state_after_first_assign.status_code == 200
    assert sorted(company["id"] for company in state_after_first_assign.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )

    etag_before_replay = next_etag
    idempotent_assign = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": next_etag},
        json={"company_ids": [test_tenant_2.id, test_tenant.id]},
    )
    assert idempotent_assign.status_code == 200
    next_etag = idempotent_assign.headers.get("ETag")
    assert next_etag is not None
    assert next_etag == etag_before_replay

    state_after_idempotent_assign = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert state_after_idempotent_assign.status_code == 200
    assert sorted(company["id"] for company in state_after_idempotent_assign.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )

    clear_assignments = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": next_etag},
        json={"company_ids": []},
    )
    assert clear_assignments.status_code == 400
    assert "at least one assigned company" in clear_assignments.json()["detail"]

    state_after_clear = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert state_after_clear.status_code == 200
    assert sorted(company["id"] for company in state_after_clear.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )


def test_assign_companies_requires_if_match_header(
    client, db, admin_headers, test_admin, test_tenant
):
    document = Document(
        title="If-Match Required Document",
        document_number="DOC-ASG-PREC-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers=admin_headers,
        json={"company_ids": [test_tenant.id]},
    )

    assert response.status_code == 428
    assert "If-Match header is required" in response.json()["detail"]


def test_assign_companies_rejects_stale_if_match_conflict(
    client, db, admin_headers, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="If-Match Conflict Document",
        document_number="DOC-ASG-CONFLICT-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    stale_etag = document.etag
    first_assign = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": stale_etag},
        json={"company_ids": [test_tenant.id]},
    )
    assert first_assign.status_code == 200

    stale_retry = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers={**admin_headers, "If-Match": stale_etag},
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert stale_retry.status_code == 409
    assert "Write conflict detected" in stale_retry.json()["detail"]


def test_bulk_assign_companies_endpoint_updates_set_and_emits_schema_header(
    client, db, admin_headers, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="Bulk assignment endpoint document",
        document_number="DOC-ASG-BULK-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    document.assigned_companies = [test_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.put(
        f"/api/v1/documents/{document.id}/companies/batch",
        headers={
            **admin_headers,
            "If-Match": document.etag,
            "Idempotency-Key": f"bulk-set-{uuid4().hex}",
        },
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )

    assert response.status_code == 200
    assert response.headers.get("X-API-Schema-Version")
    assert response.headers.get("ETag")

    assigned = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    assert sorted(company["id"] for company in assigned.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )


def test_batch_assign_companies_put_endpoint_updates_set_in_single_request(
    client, db, admin_headers, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="Batch assignment endpoint document",
        document_number="DOC-ASG-BATCH-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    document.assigned_companies = [test_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.put(
        f"/api/v1/documents/{document.id}/companies/batch",
        headers={
            **admin_headers,
            "If-Match": document.etag,
            "Idempotency-Key": f"batch-set-{uuid4().hex}",
        },
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )

    assert response.status_code == 200
    assert response.headers.get("X-API-Schema-Version")
    assert response.headers.get("ETag")
    assert "Batch company assignment updated" in response.json()["message"]

    assigned = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    assert sorted(company["id"] for company in assigned.json()) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )


def test_assign_company_endpoints_require_document_in_same_tenant(client, db):
    owner_tenant = Tenant(
        name="Owner Tenant",
        slug="owner-tenant",
        is_active=True,
        company_type="customer",
    )
    other_tenant = Tenant(
        name="Other Tenant",
        slug="other-tenant",
        is_active=True,
        company_type="customer",
    )
    db.add_all([owner_tenant, other_tenant])
    db.flush()

    owner_manager = User(
        email="owner-manager@example.com",
        username="owner_manager",
        full_name="Owner Manager",
        hashed_password=get_password_hash("ownerpass123"),
        role=UserRole.MANAGER,
        tenant_id=owner_tenant.id,
        is_active=True,
        is_email_verified=True,
    )
    other_manager = User(
        email="other-manager@example.com",
        username="other_manager",
        full_name="Other Manager",
        hashed_password=get_password_hash("otherpass123"),
        role=UserRole.MANAGER,
        tenant_id=other_tenant.id,
        is_active=True,
        is_email_verified=True,
    )
    other_viewer = User(
        email="other-viewer@example.com",
        username="other_viewer",
        full_name="Other Viewer",
        hashed_password=get_password_hash("viewpass123"),
        role=UserRole.VIEWER,
        tenant_id=other_tenant.id,
        is_active=True,
        is_email_verified=True,
    )
    db.add_all([owner_manager, other_manager, other_viewer])
    db.flush()

    document = Document(
        title="Tenant scoped assignment document",
        document_number="DOC-ASG-SCOPE-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=owner_manager.id,
        tenant_id=owner_tenant.id,
    )
    document.assigned_companies = [owner_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)

    other_manager_headers = _login_headers(client, "other_manager", "otherpass123")
    other_viewer_headers = _login_headers(client, "other_viewer", "viewpass123")

    assign_response = client.post(
        f"/api/v1/documents/{document.id}/assign-companies",
        headers=other_manager_headers,
        json={"company_ids": [other_tenant.id]},
    )
    assert assign_response.status_code == 404

    list_response = client.get(
        f"/api/v1/documents/{document.id}/assigned-companies",
        headers=other_viewer_headers,
    )
    assert list_response.status_code == 404

    remove_response = client.delete(
        f"/api/v1/documents/{document.id}/assign-companies/{owner_tenant.id}",
        headers=other_manager_headers,
    )
    assert remove_response.status_code == 404


def test_create_document_normalizes_topic_to_canonical_slug(db, test_user):
    db.add(Topic(name="SDKs & Tools", slug="sdk-tools"))
    db.commit()

    service = DocumentService(db)
    created = service.create_document(
        DocumentCreate(
            title="Topic Normalized Create",
            description="Topic should normalize to canonical slug",
            topic="SDKs & Tools",
            platform=DEFAULT_PLATFORM,
        ),
        test_user,
    )

    assert created.topic == "sdk-tools"


def test_update_document_normalizes_topic_to_canonical_slug(db, test_user):
    db.add(Topic(name="SDKs & Tools", slug="sdk-tools"))
    db.commit()

    service = DocumentService(db)
    document = service.create_document(
        DocumentCreate(
            title="Topic Normalized Update",
            description="Topic update normalization",
            topic="platform",
            platform=DEFAULT_PLATFORM,
        ),
        test_user,
    )

    updated = service.update_document(
        document.id,
        DocumentUpdate(topic="sdks-tools"),
        test_user,
        if_match=document.etag,
    )

    assert updated.topic == "sdk-tools"
