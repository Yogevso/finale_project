"""Tests for Health Check API endpoints"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_basic_health(self, client: TestClient):
        """Test basic health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_readiness_check(self, client: TestClient):
        """Test readiness endpoint with component checks"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "components" in data
        assert "database" in data["components"]
        assert "storage" in data["components"]

    def test_readiness_database_status(self, client: TestClient):
        """Test that database status is reported correctly"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        db_status = data["components"]["database"]
        assert db_status["status"] == "healthy"
        assert "latency_ms" in db_status

    def test_readiness_storage_status(self, client: TestClient):
        """Test that storage status is reported correctly"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        storage_status = data["components"]["storage"]
        assert storage_status["status"] == "healthy"
        # In dev mode, should be local storage
        assert storage_status["type"] == "local"

    def test_detailed_health(self, client: TestClient):
        """Test detailed health endpoint"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "components" in data
        assert "system" in data
        assert "configuration" in data

    def test_detailed_health_system_info(self, client: TestClient):
        """Test that system info is included"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        system = data["system"]
        assert "python_version" in system
        assert "platform" in system

    def test_detailed_health_configuration(self, client: TestClient):
        """Test that configuration is included"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        config = data["configuration"]
        assert "rate_limiting_enabled" in config
        assert "email_enabled" in config
        assert "s3_enabled" in config
        assert "debug_mode" in config
