"""Unit tests for Analytics API"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient


class TestAnalyticsOverview:
    """Tests for /analytics/overview endpoint"""

    def test_get_overview_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get analytics overview"""
        response = client.get("/api/v1/analytics/overview", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "total_documents" in data
        assert "total_users" in data
        assert "total_views" in data
        assert "total_downloads" in data
        assert "pending_reviews" in data
        assert "documents_by_status" in data
        assert "documents_by_category" in data
        assert "period_start" in data
        assert "period_end" in data

    def test_get_overview_as_manager(self, client: TestClient, manager_headers):
        """Manager should be able to get analytics overview"""
        response = client.get("/api/v1/analytics/overview", headers=manager_headers)
        assert response.status_code == 200

    def test_get_overview_as_editor(self, client: TestClient, auth_headers):
        """Editor should NOT be able to get analytics overview"""
        response = client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert response.status_code == 403

    def test_get_overview_as_viewer(self, client: TestClient, viewer_auth_headers):
        """Viewer should NOT be able to get analytics overview"""
        response = client.get("/api/v1/analytics/overview", headers=viewer_auth_headers)
        assert response.status_code == 403

    def test_get_overview_as_customer(self, client: TestClient, customer_headers):
        """Customer should NOT be able to get analytics overview"""
        response = client.get("/api/v1/analytics/overview", headers=customer_headers)
        assert response.status_code == 403

    def test_get_overview_unauthenticated(self, client: TestClient):
        """Unauthenticated users should get 401"""
        response = client.get("/api/v1/analytics/overview")
        assert response.status_code == 401

    def test_get_overview_with_date_range(self, client: TestClient, admin_headers):
        """Analytics should support date range filtering"""
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        response = client.get(
            "/api/v1/analytics/overview",
            headers=admin_headers,
            params={"date_from": week_ago.isoformat(), "date_to": today.isoformat()},
        )
        assert response.status_code == 200


class TestAnalyticsRecentActivity:
    """Tests for /analytics/recent-activity endpoint"""

    def test_get_recent_activity_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get recent activity"""
        response = client.get("/api/v1/analytics/recent-activity", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_recent_activity_with_limit(self, client: TestClient, admin_headers):
        """Recent activity should respect limit parameter"""
        response = client.get(
            "/api/v1/analytics/recent-activity",
            headers=admin_headers,
            params={"limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_get_recent_activity_invalid_limit(self, client: TestClient, admin_headers):
        """Invalid limit should return validation error"""
        response = client.get(
            "/api/v1/analytics/recent-activity",
            headers=admin_headers,
            params={"limit": 100},  # Exceeds max of 50
        )
        assert response.status_code == 422


class TestEngagementAnalytics:
    """Tests for /analytics/engagement endpoint"""

    def test_get_engagement_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get engagement analytics"""
        response = client.get("/api/v1/analytics/engagement", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "views_over_time" in data
        assert "downloads_over_time" in data
        assert "unique_visitors" in data
        assert "avg_reading_progress" in data
        assert "completion_rate" in data

    def test_get_engagement_as_manager(self, client: TestClient, manager_headers):
        """Manager should be able to get engagement analytics"""
        response = client.get("/api/v1/analytics/engagement", headers=manager_headers)
        assert response.status_code == 200

    def test_get_engagement_with_granularity(self, client: TestClient, admin_headers):
        """Engagement should support granularity parameter"""
        response = client.get(
            "/api/v1/analytics/engagement",
            headers=admin_headers,
            params={"granularity": "weekly"},
        )
        assert response.status_code == 200


class TestTopDocuments:
    """Tests for /analytics/engagement/top-documents endpoint"""

    def test_get_top_documents_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get top documents"""
        response = client.get("/api/v1/analytics/engagement/top-documents", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "by_views" in data
        assert "by_downloads" in data

    def test_get_top_documents_with_limit(self, client: TestClient, admin_headers):
        """Top documents should respect limit parameter"""
        response = client.get(
            "/api/v1/analytics/engagement/top-documents",
            headers=admin_headers,
            params={"limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["by_views"]) <= 5
        assert len(data["by_downloads"]) <= 5


class TestUserAnalytics:
    """Tests for /analytics/users endpoint"""

    def test_get_users_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get user analytics"""
        response = client.get("/api/v1/analytics/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "users_by_role" in data
        assert "new_users_over_time" in data

    def test_get_users_as_manager(self, client: TestClient, manager_headers):
        """Manager should NOT be able to get user analytics (admin only)"""
        response = client.get("/api/v1/analytics/users", headers=manager_headers)
        assert response.status_code == 403

    def test_get_users_as_editor(self, client: TestClient, auth_headers):
        """Editor should NOT be able to get user analytics"""
        response = client.get("/api/v1/analytics/users", headers=auth_headers)
        assert response.status_code == 403


class TestContentAnalytics:
    """Tests for /analytics/content endpoint"""

    def test_get_content_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get content analytics"""
        response = client.get("/api/v1/analytics/content", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_documents_created" in data
        assert "total_versions_published" in data
        assert "total_comments" in data
        assert "documents_created_over_time" in data
        assert "approval_rate" in data

    def test_get_content_as_manager(self, client: TestClient, manager_headers):
        """Manager should be able to get content analytics"""
        response = client.get("/api/v1/analytics/content", headers=manager_headers)
        assert response.status_code == 200


class TestFeedbackAnalytics:
    """Tests for /analytics/feedback endpoint"""

    def test_get_feedback_as_admin(self, client: TestClient, admin_headers):
        """Admin should be able to get feedback analytics"""
        response = client.get("/api/v1/analytics/feedback", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_feedback" in data
        assert "pending_feedback" in data
        assert "responded_feedback" in data
        assert "feedback_by_type" in data

    def test_get_feedback_as_manager(self, client: TestClient, manager_headers):
        """Manager should be able to get feedback analytics"""
        response = client.get("/api/v1/analytics/feedback", headers=manager_headers)
        assert response.status_code == 200


class TestTenantAnalytics:
    """Tests for /analytics/tenants endpoint (system admin only)"""

    def test_get_tenants_as_admin(self, client: TestClient, admin_headers):
        """Regular admin should NOT be able to get tenant analytics"""
        response = client.get("/api/v1/analytics/tenants", headers=admin_headers)
        assert response.status_code == 403

    def test_get_tenants_as_manager(self, client: TestClient, manager_headers):
        """Manager should NOT be able to get tenant analytics"""
        response = client.get("/api/v1/analytics/tenants", headers=manager_headers)
        assert response.status_code == 403

    def test_get_tenants_unauthenticated(self, client: TestClient):
        """Unauthenticated users should get 401"""
        response = client.get("/api/v1/analytics/tenants")
        assert response.status_code == 401


class TestExportCSV:
    """Tests for /analytics/export/csv endpoint"""

    def test_export_overview_csv(self, client: TestClient, admin_headers):
        """Admin should be able to export overview as CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "overview"},
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_export_engagement_csv(self, client: TestClient, admin_headers):
        """Admin should be able to export engagement as CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "engagement"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_users_csv(self, client: TestClient, admin_headers):
        """Admin should be able to export users as CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "users"},
        )
        assert response.status_code == 200

    def test_export_content_csv(self, client: TestClient, admin_headers):
        """Admin should be able to export content as CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "content"},
        )
        assert response.status_code == 200

    def test_export_feedback_csv(self, client: TestClient, admin_headers):
        """Admin should be able to export feedback as CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "feedback"},
        )
        assert response.status_code == 200

    def test_export_csv_as_editor(self, client: TestClient, auth_headers):
        """Editor should NOT be able to export CSV"""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=auth_headers,
            params={"report": "overview"},
        )
        assert response.status_code == 403

    def test_export_csv_missing_report(self, client: TestClient, admin_headers):
        """Missing report parameter should return validation error"""
        response = client.get("/api/v1/analytics/export/csv", headers=admin_headers)
        assert response.status_code == 422


class TestExportPDF:
    """Tests for /analytics/export/pdf endpoint"""

    def test_export_overview_pdf_without_reportlab(self, client: TestClient, admin_headers):
        """PDF export should gracefully handle missing reportlab"""
        response = client.get(
            "/api/v1/analytics/export/pdf",
            headers=admin_headers,
            params={"report": "overview"},
        )
        # Either 200 (reportlab installed) or 501 (not installed)
        assert response.status_code in [200, 501]

    def test_export_pdf_as_editor(self, client: TestClient, auth_headers):
        """Editor should NOT be able to export PDF"""
        response = client.get(
            "/api/v1/analytics/export/pdf",
            headers=auth_headers,
            params={"report": "overview"},
        )
        assert response.status_code == 403


class TestAnalyticsDataIntegrity:
    """Tests for analytics data accuracy"""

    def test_overview_counts_are_non_negative(self, client: TestClient, admin_headers):
        """All counts in overview should be non-negative"""
        response = client.get("/api/v1/analytics/overview", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_documents"] >= 0
        assert data["total_users"] >= 0
        assert data["total_views"] >= 0
        assert data["total_downloads"] >= 0
        assert data["pending_reviews"] >= 0

    def test_engagement_rates_in_valid_range(self, client: TestClient, admin_headers):
        """Percentage rates should be between 0 and 100"""
        response = client.get("/api/v1/analytics/engagement", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert 0 <= data["avg_reading_progress"] <= 100
        assert 0 <= data["completion_rate"] <= 100

    def test_time_series_data_format(self, client: TestClient, admin_headers):
        """Time series data should have correct format"""
        response = client.get("/api/v1/analytics/engagement", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        for point in data["views_over_time"]:
            assert "date" in point
            assert "value" in point
            assert isinstance(point["value"], int)
