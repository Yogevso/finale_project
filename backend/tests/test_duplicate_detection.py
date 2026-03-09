"""Integration tests for duplicate-title detection warnings."""

from tests.factories import create_document


def test_duplicate_check_returns_similar_title_warning(client, auth_headers, db, test_user):
    create_document(
        db,
        created_by=test_user.id,
        title="Quarterly Release Notes",
        document_number="DOC-DUPE-001",
    )
    similar_document = create_document(
        db,
        created_by=test_user.id,
        title="Quarterly Release Note",
        document_number="DOC-DUPE-002",
    )

    response = client.get(
        "/api/v1/documents/duplicate-check",
        headers=auth_headers,
        params={"title": "Quarterly Release Notes", "threshold": 0.7},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["title"] == "Quarterly Release Notes"
    assert payload["has_matches"] is True
    assert any(
        match["document_id"] == similar_document.id and match["similarity"] >= 0.7
        for match in payload["matches"]
    )
