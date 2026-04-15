"""
Cross-channel audience projection parity contract tests.

Verifies that public, portal, and management document responses
all include the canonical audience-related fields.
"""

# Canonical fields that must appear in ALL document list responses
CANONICAL_LIST_FIELDS = {
    "id",
    "title",
    "description",
    "category",
    "visibility",
    "updated_at",
}

# Additional fields expected on list responses for full parity
PARITY_LIST_FIELDS = {
    "document_number",
    "topic",
    "platform",
    "release_branch",
    "tags",
    "created_at",
    "published_at",
}

# Fields expected on detail responses
CANONICAL_DETAIL_FIELDS = CANONICAL_LIST_FIELDS | {
    "document_number",
    "topic",
    "platform",
    "release_branch",
    "visibility",
    "created_at",
}


class TestPublicAudienceProjectionParity:
    """Verify public channel includes canonical audience fields."""

    def test_public_list_canonical_fields(self, client, public_document):
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        item = items[0]
        for field in CANONICAL_LIST_FIELDS | PARITY_LIST_FIELDS:
            assert field in item, f"Public list missing field: {field}"

    def test_public_detail_canonical_fields(self, client, public_document):
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()
        for field in CANONICAL_DETAIL_FIELDS:
            assert field in data, f"Public detail missing field: {field}"

    def test_public_visibility_always_public(self, client, public_document):
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["visibility"] == "public"


class TestPortalAudienceProjectionParity:
    """Verify portal channel includes canonical audience fields."""

    def test_portal_list_canonical_fields(self, client, customer_headers, public_document):
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        item = items[0]
        for field in CANONICAL_LIST_FIELDS | PARITY_LIST_FIELDS:
            assert field in item, f"Portal list missing field: {field}"

    def test_portal_detail_canonical_fields(self, client, customer_headers, public_document):
        response = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert response.status_code == 200
        data = response.json()
        for field in CANONICAL_DETAIL_FIELDS:
            assert field in data, f"Portal detail missing field: {field}"


class TestManagementAudienceProjectionParity:
    """Verify management channel includes canonical audience fields."""

    def test_management_list_canonical_fields(self, client, auth_headers, public_document):
        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        item = items[0]
        for field in CANONICAL_LIST_FIELDS:
            assert field in item, f"Management list missing field: {field}"

    def test_management_detail_canonical_fields(self, client, auth_headers, public_document):
        response = client.get(f"/api/v1/documents/{public_document.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for field in CANONICAL_DETAIL_FIELDS:
            assert field in data, f"Management detail missing field: {field}"
