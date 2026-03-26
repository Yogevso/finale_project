"""Unit tests for Analytics API"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.analytics_service import AnalyticsService


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

    def test_user_analytics_most_active_scopes_tenant_before_ranking_limit(
        self,
        client: TestClient,
        db,
        admin_headers,
        test_admin,
        test_tenant,
        test_tenant_2,
    ):
        """Tenant filter must be applied in SQL before top-N ranking/limit."""
        from app.models import ActionType, AuditLog, User, UserRole
        from app.security import get_password_hash

        test_admin.tenant_id = test_tenant.id
        db.flush()

        cross_tenant_users = []
        for index in range(12):
            user = User(
                email=f"tenant-b-heavy-{index}@example.com",
                username=f"tenant_b_heavy_{index}",
                full_name=f"Tenant B Heavy {index}",
                hashed_password=get_password_hash("tenant-b-pass"),
                role=UserRole.EDITOR,
                tenant_id=test_tenant_2.id,
                is_active=True,
            )
            cross_tenant_users.append(user)
            db.add(user)

        tenant_top_user = User(
            email="tenant-a-top@example.com",
            username="tenant_a_top",
            full_name="Tenant A Top",
            hashed_password=get_password_hash("tenant-a-pass"),
            role=UserRole.EDITOR,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        tenant_second_user = User(
            email="tenant-a-second@example.com",
            username="tenant_a_second",
            full_name="Tenant A Second",
            hashed_password=get_password_hash("tenant-a-pass"),
            role=UserRole.EDITOR,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db.add_all([tenant_top_user, tenant_second_user])
        db.flush()

        for user in cross_tenant_users:
            for offset in range(5):
                db.add(
                    AuditLog(
                        user_id=user.id,
                        action=ActionType.VIEW,
                        created_at=datetime(2026, 1, 20, 10, offset, 0),
                    )
                )

        for offset in range(3):
            db.add(
                AuditLog(
                    user_id=tenant_top_user.id,
                    action=ActionType.VIEW,
                    created_at=datetime(2026, 1, 21, 9, offset, 0),
                )
            )
        for offset in range(2):
            db.add(
                AuditLog(
                    user_id=tenant_second_user.id,
                    action=ActionType.VIEW,
                    created_at=datetime(2026, 1, 21, 8, offset, 0),
                )
            )
        db.commit()

        response = client.get(
            "/api/v1/analytics/users",
            headers=admin_headers,
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        assert response.status_code == 200
        payload = response.json()

        most_active_user_ids = [item["user_id"] for item in payload["most_active_users"]]
        assert most_active_user_ids == [tenant_top_user.id, tenant_second_user.id]

    def test_user_analytics_most_active_uses_deterministic_tie_breakers(
        self, client: TestClient, db, admin_headers, test_admin, test_tenant
    ):
        """Tie ordering should use last-active desc then user_id asc for stable results."""
        from app.models import ActionType, AuditLog, User, UserRole
        from app.security import get_password_hash

        test_admin.tenant_id = test_tenant.id
        db.flush()

        tie_first = User(
            email="tie-first@example.com",
            username="tie_first",
            full_name="Tie First",
            hashed_password=get_password_hash("tie-pass"),
            role=UserRole.EDITOR,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        tie_second = User(
            email="tie-second@example.com",
            username="tie_second",
            full_name="Tie Second",
            hashed_password=get_password_hash("tie-pass"),
            role=UserRole.EDITOR,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        more_recent = User(
            email="tie-recent@example.com",
            username="tie_recent",
            full_name="Tie Recent",
            hashed_password=get_password_hash("tie-pass"),
            role=UserRole.EDITOR,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db.add_all([tie_first, tie_second, more_recent])
        db.flush()

        tie_timestamps = [datetime(2026, 1, 20, 10, 0, 0), datetime(2026, 1, 20, 11, 0, 0)]
        recent_timestamps = [datetime(2026, 1, 22, 10, 0, 0), datetime(2026, 1, 22, 11, 0, 0)]

        for timestamp in tie_timestamps:
            db.add(AuditLog(user_id=tie_first.id, action=ActionType.VIEW, created_at=timestamp))
            db.add(AuditLog(user_id=tie_second.id, action=ActionType.VIEW, created_at=timestamp))
        for timestamp in recent_timestamps:
            db.add(AuditLog(user_id=more_recent.id, action=ActionType.VIEW, created_at=timestamp))
        db.commit()

        response = client.get(
            "/api/v1/analytics/users",
            headers=admin_headers,
            params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        )
        assert response.status_code == 200
        payload = response.json()

        most_active_user_ids = [item["user_id"] for item in payload["most_active_users"]]
        assert most_active_user_ids[:3] == [more_recent.id, tie_first.id, tie_second.id]


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

    def test_content_published_over_time_uses_published_at_dates(
        self, client: TestClient, db, admin_headers, test_admin
    ):
        """Published-version buckets should be based on published_at, not created_at."""
        from app.models import Document, DocumentStatus, Version

        document = Document(
            title="Publish Timestamp Source",
            document_number="DOC-ANL-PUB-0001",
            status=DocumentStatus.ACTIVE,
            created_by=test_admin.id,
            tenant_id=test_admin.tenant_id,
        )
        db.add(document)
        db.flush()

        version = Version(
            document_id=document.id,
            version_number=1,
            is_published=True,
            created_by=test_admin.id,
            created_at=datetime(2026, 1, 2, 8, 0, 0),
            published_at=datetime(2026, 1, 12, 15, 30, 0),
        )
        db.add(version)
        db.commit()

        response = client.get(
            "/api/v1/analytics/content",
            headers=admin_headers,
            params={
                "date_from": "2026-01-12",
                "date_to": "2026-01-12",
                "granularity": "daily",
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["total_versions_published"] == 1
        assert payload["versions_published_over_time"] == [{"date": "2026-01-12", "value": 1}]

    def test_content_published_over_time_excludes_published_without_published_at(
        self, client: TestClient, db, admin_headers, test_admin
    ):
        """Rows missing published_at should not appear in published timeline aggregates."""
        from app.models import Document, DocumentStatus, Version

        document = Document(
            title="Null Publish Timestamp",
            document_number="DOC-ANL-PUB-0002",
            status=DocumentStatus.ACTIVE,
            created_by=test_admin.id,
            tenant_id=test_admin.tenant_id,
        )
        db.add(document)
        db.flush()

        version_missing_publish_ts = Version(
            document_id=document.id,
            version_number=1,
            is_published=True,
            created_by=test_admin.id,
            created_at=datetime(2026, 1, 12, 9, 0, 0),
            published_at=None,
        )
        db.add(version_missing_publish_ts)
        db.commit()

        response = client.get(
            "/api/v1/analytics/content",
            headers=admin_headers,
            params={
                "date_from": "2026-01-12",
                "date_to": "2026-01-12",
                "granularity": "daily",
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["total_versions_published"] == 0
        assert payload["versions_published_over_time"] == []


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

    def test_export_csv_invalid_report_returns_client_error(self, client: TestClient, admin_headers):
        """Unknown report should return explicit client error status."""
        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "unknown-report"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported analytics export request"

    def test_export_csv_internal_errors_are_generic(
        self,
        client: TestClient,
        admin_headers,
        monkeypatch,
    ):
        class BrokenExporter:
            supported_reports = ("overview",)

            def export(self, **_kwargs):
                raise RuntimeError("database stack trace should not leak")

        monkeypatch.setattr(
            "app.api.management.analytics._EXPORT_PLUGIN_REGISTRY.resolve",
            lambda _format_name: BrokenExporter(),
        )

        response = client.get(
            "/api/v1/analytics/export/csv",
            headers=admin_headers,
            params={"report": "overview"},
        )
        assert response.status_code == 500
        assert response.json()["detail"] == "Analytics export is temporarily unavailable"


class TestAnalyticsServiceScope:
    def test_analytics_service_requires_explicit_scope(self, db):
        with pytest.raises(ValueError, match="explicit scope"):
            AnalyticsService(db)

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
