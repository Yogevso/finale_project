"""Document Tests"""

from app.models import Document, DocumentStatus


def test_create_document(client, auth_headers):
    """Test document creation"""
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={
            "title": "Test Document",
            "description": "This is a test document",
            "category": "Testing",
            "tags": "test,sample",
            "status": "draft",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Document"
    assert data["status"] == "draft"
    assert "document_number" in data
    assert data["document_number"].startswith("DOC-")


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
        )
        db.add(doc)
    db.commit()

    # Get page 1
    response = client.get("/api/v1/documents?page=1&page_size=10", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["pages"] == 3
    assert data["page"] == 1


def test_get_document(client, auth_headers, db, test_user):
    """Test getting a single document"""
    # Create document
    doc = Document(
        title="Test Document",
        document_number="DOC-TEST-0001",
        description="Test description",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
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
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Update document
    response = client.put(
        f"/api/v1/documents/{doc.id}",
        headers=auth_headers,
        json={"title": "Updated Title", "status": "active"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "active"


def test_delete_document(client, auth_headers, db, test_user):
    """Test deleting a document"""
    # Create document
    doc = Document(
        title="To Delete",
        document_number="DOC-TEST-0001",
        status=DocumentStatus.DRAFT,
        created_by=test_user.id,
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id

    # Delete document
    response = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)

    assert response.status_code == 200

    # Verify deletion
    get_response = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_search_documents(client, auth_headers, db, test_user):
    """Test document search"""
    # Create documents with different titles
    documents = [
        Document(
            title="Python Programming Guide",
            document_number="DOC-TEST-0001",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        ),
        Document(
            title="JavaScript Tutorial",
            document_number="DOC-TEST-0002",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        ),
        Document(
            title="Python Best Practices",
            document_number="DOC-TEST-0003",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
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
            )
            db.add(doc)
    db.commit()

    # Filter by ACTIVE status
    response = client.get("/api/v1/documents?status=active", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["status"] == "active" for item in data["items"])
