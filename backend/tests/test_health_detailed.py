"""Tests for Health Check API endpoints"""

from fastapi.testclient import TestClient

from app.infrastructure.degradation import (
    DegradationPolicy,
    record_degradation,
    reset_degradation_metrics,
)
from app.services.document_audience_service import _company_cache


class TestHealthEndpoints:
    """Test health check endpoints"""

    def setup_method(self):
        _company_cache.clear(reset_metrics=True)
        reset_degradation_metrics()

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

    def test_detailed_health_includes_company_cache_metrics(self, client: TestClient):
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "caches" in data
        cache = data["caches"]["document_company_lookup"]
        assert cache["entry_count"] == 0
        assert "hits" in cache
        assert "misses" in cache
        assert "expired" in cache
        assert "writes" in cache
        assert "evictions" in cache

    def test_detailed_health_includes_search_runtime_metrics(self, client: TestClient):
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        search_runtime = data["runtime"]["search"]
        assert search_runtime["configured_mode"] == "auto"
        assert search_runtime["effective_mode"] == "sqlite_fts5"
        assert search_runtime["dialect"] == "sqlite"
        assert search_runtime["degraded_fallbacks"] == 0
        assert search_runtime["total_search_requests"] == 0
        assert data["configuration"]["search_backend_mode"] == "auto"

    def test_detailed_health_includes_assistant_runtime_metrics(self, client: TestClient):
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assistant_runtime = data["runtime"]["assistant"]
        assert assistant_runtime["status"] == "ready"
        assert assistant_runtime["chat"]["active"] == 0
        assert assistant_runtime["chat"]["queued"] == 0
        assert assistant_runtime["embedding"]["active"] == 0
        assert "assistant_chat_max_concurrent" in data["configuration"]
        assert "assistant_embedding_max_concurrent" in data["configuration"]

    def test_detailed_health_includes_runtime_degradation_metrics(self, client: TestClient):
        record_degradation(
            DegradationPolicy.LOSSY,
            "support.notifications",
            RuntimeError("smtp unavailable"),
        )

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        degradation = data["runtime"]["degradation"]
        assert degradation["total_events"] == 1
        assert degradation["by_policy"]["lossy"] == 1
        assert degradation["by_key"]["lossy:support.notifications"] == 1
        component = degradation["components"]["support.notifications"]
        assert component["total_events"] == 1
        assert component["last_error_type"] == "RuntimeError"
        assert component["last_error_message"] == "smtp unavailable"
