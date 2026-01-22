"""Tests for health check and root endpoints."""


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, client):
        """Test that health check returns status healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test that root endpoint returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert "Document Portal" in data["message"]


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON is available."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_swagger_docs_available(self, client):
        """Test that Swagger UI is available."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
