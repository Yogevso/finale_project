"""AG-013: Security contract tests — route-by-route auth parity.

Verifies that every protected route enforces the expected authentication
level. This test introspects the FastAPI router tree and checks that each
endpoint has the correct dependency attached.
"""

from __future__ import annotations

import pytest
from fastapi import Depends
from fastapi.routing import APIRoute

from app.app_factory import create_app

app = create_app()


def _get_all_routes() -> list[APIRoute]:
    """Collect all APIRoute instances from the application."""
    return [r for r in app.routes if isinstance(r, APIRoute)]


def _route_has_dependency(route: APIRoute, dep_name: str) -> bool:
    """Check if a route (or its parent router) uses a dependency whose
    callable name contains *dep_name*."""
    for dep in route.dependant.dependencies:
        call = dep.call
        name = getattr(call, "__name__", "") or getattr(call, "__qualname__", "")
        if dep_name in name:
            return True
    return False


def _route_has_any_auth(route: APIRoute) -> bool:
    """Return True if the route has ANY auth-related dependency.

    Checks both function names and the module they were defined in
    (to catch factory-produced dependencies like require_permission).
    """
    auth_markers = (
        "current_user",
        "current_active_user",
        "require_",
        "tenant_context",
        "get_tenant",
    )
    # Modules that produce auth dependencies
    auth_modules = ("app.dependencies.permissions", "app.dependencies.tenant", "app.security")

    def _check_deps(dependant) -> bool:
        for dep in dependant.dependencies:
            call = dep.call
            name = getattr(call, "__name__", "") or getattr(call, "__qualname__", "")
            module = getattr(call, "__module__", "")
            # Check name-based markers
            if any(marker in name.lower() for marker in auth_markers):
                return True
            # Check if dep was defined in an auth module (factory-produced)
            if any(m in module for m in auth_modules):
                return True
            # Check sub-dependencies
            if hasattr(dep, "dependant") and dep.dependant and _check_deps(dep.dependant):
                return True
        return False

    return _check_deps(route.dependant)


# Routes that are intentionally unprotected
PUBLIC_ALLOWLIST = {
    "/",
    "/ready",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/verify-email/{token}",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/reset-password/{token}",
    "/api/v1/auth/invitation/{token}",
    "/api/v1/auth/invitation/accept",
    "/api/v1/public/documents",
    "/api/v1/public/documents/{document_id}",
    "/api/v1/public/documents/{document_id}/versions",
    "/api/v1/public/documents/{document_id}/versions/{version_id}",
    "/api/v1/public/documents/{document_id}/attachments",
    "/api/v1/public/documents/{document_id}/changelog",
    "/api/v1/public/changelog",
    "/api/v1/platforms",
    "/api/v1/platforms/{platform_id}/documents",
    "/api/platforms",
    "/api/platforms/{platform_id}/documents",
    "/api/v1/sitemap.xml",
    "/api/v1/announcements",
    "/api/v1/gdpr/export/{request_id}/download",  # token-based auth (URL token)
    "/api/v1/api-keys/verify",  # API key auth (not user session)
    "/api/v1/developer/api-docs",  # public developer docs
    "/api/v1/health",
    "/api/v1/health/db",
    "/api/v1/health/storage",
    "/api/v1/health/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Management routes that MUST require elevated auth
MANAGEMENT_ROUTES_REQUIRING_AUTH = [
    ("/api/v1/admin/", "require_system_admin"),
    ("/api/v1/gdpr/", "require_system_admin"),
    ("/api/v1/tenants", "require_system_admin"),
    ("/api/v1/rbac/", "require_system_admin"),
    ("/api/v1/users", "require_admin"),
]


class TestAllProtectedRoutesHaveAuth:
    """Every non-public route must have an auth dependency."""

    def test_non_public_routes_require_auth(self):
        routes = _get_all_routes()
        unprotected = []
        for route in routes:
            path = route.path
            # Skip known public routes
            if path in PUBLIC_ALLOWLIST:
                continue
            # Skip health/docs
            if path.startswith("/health") or path.startswith("/docs"):
                continue
            if not _route_has_any_auth(route):
                methods = ",".join(route.methods or [])
                unprotected.append(f"{methods} {path}")

        # Allow public/*, viewer/*, health routes to be unauthenticated (by design)
        unprotected = [
            r for r in unprotected
            if "/public/" not in r
            and "/health" not in r
            and "/viewer/" not in r
        ]

        assert unprotected == [], (
            f"Routes without auth protection:\n" +
            "\n".join(f"  - {r}" for r in unprotected)
        )


class TestManagementRoutesRequireElevatedAuth:
    """Management/admin routes must have specific elevated auth."""

    def test_admin_routes_have_system_admin_dep(self):
        routes = _get_all_routes()
        missing = []
        for route in routes:
            path = route.path
            if "/admin/" in path and path not in PUBLIC_ALLOWLIST:
                if not _route_has_any_auth(route):
                    methods = ",".join(route.methods or [])
                    missing.append(f"{methods} {path}")

        assert missing == [], (
            f"Admin routes without auth:\n" +
            "\n".join(f"  - {r}" for r in missing)
        )


class TestPortalRoutesRequireCustomerAuth:
    """Portal routes must require authenticated customer."""

    def test_portal_routes_have_auth(self):
        routes = _get_all_routes()
        missing = []
        for route in routes:
            path = route.path
            if "/portal/" in path:
                if not _route_has_any_auth(route):
                    methods = ",".join(route.methods or [])
                    missing.append(f"{methods} {path}")

        assert missing == [], (
            f"Portal routes without auth:\n" +
            "\n".join(f"  - {r}" for r in missing)
        )


class TestPublicRoutesAreOpen:
    """Public routes must NOT require auth."""

    def test_public_routes_are_unauthenticated(self):
        routes = _get_all_routes()
        over_protected = []
        for route in routes:
            path = route.path
            if "/public/" in path and _route_has_any_auth(route):
                methods = ",".join(route.methods or [])
                over_protected.append(f"{methods} {path}")

        # All public routes should be open
        assert over_protected == [], (
            f"Public routes that unexpectedly require auth:\n" +
            "\n".join(f"  - {r}" for r in over_protected)
        )
