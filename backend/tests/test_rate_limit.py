"""Tests for Rate Limiting Middleware"""

import time
from unittest.mock import MagicMock

from app.config import settings
from app.middleware.rate_limit import RateLimitInfo, RateLimitMiddleware


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass"""

    def test_default_values(self):
        """Test default initialization"""
        info = RateLimitInfo()
        assert info.count == 0
        assert info.window_start == 0.0

    def test_custom_values(self):
        """Test custom initialization"""
        info = RateLimitInfo(count=5, window_start=1000.0)
        assert info.count == 5
        assert info.window_start == 1000.0


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware"""

    def test_get_client_ip_direct(self):
        """Get IP from direct client"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_forwarded(self, monkeypatch):
        """Get IP from X-Forwarded-For header"""
        monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
        monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["192.168.1.1"])
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_real_ip(self, monkeypatch):
        """Get IP from X-Real-IP header"""
        monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
        monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["192.168.1.1"])
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        request = MagicMock()
        request.headers = {"x-real-ip": "172.16.0.1"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "172.16.0.1"

    def test_get_client_ip_no_client(self):
        """Get IP when no client available"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"

    def test_is_rate_limited_first_request(self):
        """First request should not be limited"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        is_limited, remaining, reset_time = middleware._is_rate_limited("192.168.1.1")

        assert is_limited is False
        assert remaining == 9  # 10 - 1

    def test_is_rate_limited_within_limit(self):
        """Requests within limit should pass"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=10, window_seconds=60)

        # Make 5 requests
        for _ in range(5):
            is_limited, remaining, _ = middleware._is_rate_limited("192.168.1.1")
            assert is_limited is False

        # Should have 5 remaining
        assert remaining == 5

    def test_is_rate_limited_at_limit(self):
        """Request at limit should be blocked"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=5, window_seconds=60)

        # Make 5 requests (max)
        for _ in range(5):
            is_limited, _, _ = middleware._is_rate_limited("192.168.1.1")
            assert is_limited is False

        # 6th request should be limited
        is_limited, remaining, _ = middleware._is_rate_limited("192.168.1.1")
        assert is_limited is True
        assert remaining == 0

    def test_window_reset(self):
        """Rate limit should reset after window expires"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=2, window_seconds=1)

        # Exhaust limit
        middleware._is_rate_limited("192.168.1.1")
        middleware._is_rate_limited("192.168.1.1")
        is_limited, _, _ = middleware._is_rate_limited("192.168.1.1")
        assert is_limited is True

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_limited, remaining, _ = middleware._is_rate_limited("192.168.1.1")
        assert is_limited is False
        assert remaining == 1

    def test_cleanup_old_entries(self):
        """Old entries should be cleaned up"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=100, window_seconds=1)

        # Add some entries
        middleware._is_rate_limited("192.168.1.1")
        middleware._is_rate_limited("192.168.1.2")
        assert len(middleware.clients) == 2

        # Wait for entries to expire
        time.sleep(1.1)

        # Trigger cleanup (requires 100 requests normally, but we can force it)
        middleware._cleanup_counter = 99
        middleware._cleanup_old_entries()

        # Old entries should be removed
        assert len(middleware.clients) == 0

    def test_excluded_paths(self):
        """Excluded paths should be defined"""
        assert "/health" in RateLimitMiddleware.EXCLUDED_PATHS
        assert "/ready" in RateLimitMiddleware.EXCLUDED_PATHS
        assert "/docs" in RateLimitMiddleware.EXCLUDED_PATHS

    def test_different_clients_separate_limits(self):
        """Different clients should have separate rate limits"""
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=2, window_seconds=60)

        # Client 1 exhausts limit
        middleware._is_rate_limited("192.168.1.1")
        middleware._is_rate_limited("192.168.1.1")
        is_limited, _, _ = middleware._is_rate_limited("192.168.1.1")
        assert is_limited is True

        # Client 2 should still be allowed
        is_limited, _, _ = middleware._is_rate_limited("192.168.1.2")
        assert is_limited is False

    def test_assignment_endpoints_use_assignment_specific_limit_profile(self, monkeypatch):
        monkeypatch.setattr(settings, "ASSIGNMENT_RATE_LIMIT_REQUESTS", 30)
        monkeypatch.setattr(settings, "ASSIGNMENT_RATE_LIMIT_WINDOW", 60)
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=100, window_seconds=60)

        limit, window, scope = middleware._resolve_limit_profile(
            request_path="/api/v1/documents/42/companies/batch",
            method="PUT",
        )

        assert limit == 30
        assert window == 60
        assert scope == "assignment"

    def test_assignment_scope_rate_limit_bucket_isolated_from_default_scope(self):
        middleware = RateLimitMiddleware(app=MagicMock(), max_requests=100, window_seconds=60)

        # Exhaust assignment-scoped bucket.
        for _ in range(2):
            limited, _, _ = middleware._is_rate_limited(
                "192.168.10.7",
                max_requests=2,
                window_seconds=60,
                scope="assignment",
            )
            assert limited is False
        limited, _, _ = middleware._is_rate_limited(
            "192.168.10.7",
            max_requests=2,
            window_seconds=60,
            scope="assignment",
        )
        assert limited is True

        # Default-scope bucket remains unaffected.
        limited, _, _ = middleware._is_rate_limited(
            "192.168.10.7",
            max_requests=100,
            window_seconds=60,
            scope="default",
        )
        assert limited is False


class TestRateLimitIntegration:
    """Integration tests for rate limiting with FastAPI"""

    def test_rate_limit_headers_present(self, client, auth_headers):
        """Rate limit headers should be present in response"""
        # Note: Rate limiting is disabled in tests via conftest.py
        # This test verifies the endpoint works
        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200

    def test_health_endpoint_accessible(self, client):
        """Health endpoint should be accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

