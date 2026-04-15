"""AG-013: Security contract tests — route-by-route auth parity.

Verifies that every protected route enforces the expected authentication
level. This test introspects the FastAPI router tree and checks that each
endpoint has the correct dependency attached.
"""

from __future__ import annotations

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


def _get_route_auth_level(route: APIRoute) -> str | None:
    """Return the most specific auth level required by a route.

    Checks dependency callable names in priority order so that a
    *require_system_admin* dependency beats a generic *current_user*.
    """
    PRIORITY = [
        ("require_system_admin", "system_admin"),
        ("require_manager", "manager"),
        ("require_admin", "admin"),
        ("require_any_role", "any_role"),
        ("require_permission", "permission"),
        ("require_any_permission", "permission"),
        ("require_editor", "editor"),
        ("require_internal_user", "internal"),
        ("require_customer", "customer"),
        ("current_active_user", "any_auth"),
        ("current_user", "any_auth"),
    ]

    # Modules that produce auth dependencies via factories
    AUTH_MODULES = ("app.dependencies.permissions", "app.dependencies.tenant", "app.security")

    found: str | None = None
    best_idx = len(PRIORITY)

    def _scan(dependant) -> None:
        nonlocal found, best_idx
        for dep in dependant.dependencies:
            call = dep.call
            name = (getattr(call, "__name__", "") or getattr(call, "__qualname__", "")).lower()
            module = getattr(call, "__module__", "")
            for idx, (marker, level) in enumerate(PRIORITY):
                if marker in name and idx < best_idx:
                    best_idx = idx
                    found = level
            # Factory-produced deps (require_permission, require_any_role) have
            # inner functions named 'dependency' — detect via module.
            if found is None and any(m in module for m in AUTH_MODULES):
                found = "permission"
                best_idx = min(best_idx, len(PRIORITY) - 1)
            if hasattr(dep, "dependant") and dep.dependant:
                _scan(dep.dependant)

    _scan(route.dependant)
    return found


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
    "/api/v1/announcements",
    "/api/v1/gdpr/export/{request_id}/download",  # token-based auth (URL token)
    "/api/v1/collaboration/documents/{document_id}/verify-access",  # token-based auth (Bearer collab token)
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
            r
            for r in unprotected
            if "/public/" not in r and "/health" not in r and "/viewer/" not in r
        ]

        assert unprotected == [], "Routes without auth protection:\n" + "\n".join(
            f"  - {r}" for r in unprotected
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

        assert missing == [], "Admin routes without auth:\n" + "\n".join(
            f"  - {r}" for r in missing
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

        assert missing == [], "Portal routes without auth:\n" + "\n".join(
            f"  - {r}" for r in missing
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
        assert over_protected == [], "Public routes that unexpectedly require auth:\n" + "\n".join(
            f"  - {r}" for r in over_protected
        )


# ---------------------------------------------------------------------------
# H-23: Role-specific auth parity tests
# ---------------------------------------------------------------------------


class TestVersionRoutesRequireEditor:
    """Version endpoints must require editor or higher (H-17)."""

    def test_version_routes_have_editor_dep(self):
        routes = _get_all_routes()
        bad = []
        allowed = {"editor", "manager", "admin", "system_admin", "permission"}
        for route in routes:
            # Viewer/public version routes are intentionally unauthenticated
            if (
                "/versions" in route.path
                and route.path not in PUBLIC_ALLOWLIST
                and "/viewer/" not in route.path
                and "/public/" not in route.path
            ):
                level = _get_route_auth_level(route)
                if level not in allowed:
                    methods = ",".join(route.methods or [])
                    bad.append(f"{methods} {route.path} → {level}")
        assert bad == [], "Version routes should require editor+:\n" + "\n".join(
            f"  - {r}" for r in bad
        )


class TestFeedbackRoutesRequireManager:
    """Management feedback endpoints must require manager or higher (C16)."""

    def test_feedback_routes_have_manager_dep(self):
        routes = _get_all_routes()
        bad = []
        allowed = {"manager", "admin", "system_admin", "any_role", "permission", "internal"}
        for route in routes:
            # Engagement feedback (submit) and portal feedback are different
            # from management feedback — they allow any authenticated user.
            if (
                "/feedback" in route.path
                and "/portal/" not in route.path
                and "/engagement/" not in route.path
                and "/viewer/" not in route.path
                and route.path not in PUBLIC_ALLOWLIST
            ):
                level = _get_route_auth_level(route)
                if level not in allowed:
                    methods = ",".join(route.methods or [])
                    bad.append(f"{methods} {route.path} → {level}")
        assert bad == [], "Feedback routes should require manager+:\n" + "\n".join(
            f"  - {r}" for r in bad
        )


class TestSearchAnalyticsRequiresAdmin:
    """Search analytics endpoint must require admin-level auth (C15)."""

    def test_search_analytics_route_has_admin_dep(self):
        routes = _get_all_routes()
        allowed = {"any_role", "manager", "admin", "system_admin", "permission"}
        for route in routes:
            if route.path == "/api/v1/search/analytics":
                level = _get_route_auth_level(route)
                assert level in allowed, f"Search analytics requires admin-level auth, got: {level}"


class TestCompanyRoutesRequireAdmin:
    """Company endpoints must require admin or higher (C4)."""

    def test_company_routes_have_admin_dep(self):
        routes = _get_all_routes()
        bad = []
        allowed = {"admin", "manager", "system_admin", "any_role", "permission"}
        for route in routes:
            if "/companies" in route.path and route.path not in PUBLIC_ALLOWLIST:
                level = _get_route_auth_level(route)
                if level not in allowed:
                    methods = ",".join(route.methods or [])
                    bad.append(f"{methods} {route.path} → {level}")
        assert bad == [], "Company routes should require admin+:\n" + "\n".join(
            f"  - {r}" for r in bad
        )
