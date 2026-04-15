"""FIX-027d: Parametric authorization matrix test.

Verifies that each endpoint enforces the minimum required role documented in
docs/AUTHORIZATION_MATRIX.md.  A representative set of endpoints is tested for
every role — the test asserts that:
  • roles at or above the required level get ≠ 403
  • roles below the required level get exactly 403
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models import UserRole
from tests.factories import create_document, create_tenant, create_user

# ── Role hierarchy (lowest → highest privilege) ──────────────────────────
ROLE_RANK = {
    UserRole.CUSTOMER: 0,
    UserRole.VIEWER: 1,
    UserRole.EDITOR: 2,
    UserRole.MANAGER: 3,
    UserRole.ADMIN: 4,
    UserRole.SYSTEM_ADMIN: 5,
}

# ── Test matrix: (method, url_template, min_role, description, denied_code) ──
# url_template may contain {doc_id} which is replaced at runtime.
# "min_role" is the lowest role expected to be granted access (≠ denied_code).
# "denied_code" is the HTTP status code returned for insufficient privilege
# (some endpoints return 404 instead of 403 for security through obscurity).
#
# NOTE: Some endpoints return 404 for missing resources even when authorised.
# That's fine — we only treat denied_code as "access denied".
MATRIX = [
    # ── System-admin only ────────────────────────────────────────────────
    ("GET", "/api/v1/admin/config-flags", UserRole.SYSTEM_ADMIN, "Config flags (SA)", 403),
    # ── Admin+ ───────────────────────────────────────────────────────────
    ("GET", "/api/v1/companies", UserRole.ADMIN, "List companies (admin+)", 403),
    # ── Manager+ (controller-level enforcement) ──────────────────────────
    ("GET", "/api/v1/users", UserRole.MANAGER, "User list (manager+)", 403),
    # ── Internal (viewer+, blocks customers) ─────────────────────────────
    ("GET", "/api/v1/documents", UserRole.VIEWER, "Document list (internal)", 403),
    ("GET", "/api/v1/documents/{doc_id}", UserRole.VIEWER, "Get document (internal)", 403),
    # ── Customer-only (portal) ───────────────────────────────────────────
    # Portal require_customer ONLY allows CUSTOMER role; internal users get 403.
    ("GET", "/api/v1/portal/documents", UserRole.CUSTOMER, "Portal doc list (customer-only)", 403),
]

# Roles ordered lowest → highest privilege
_INTERNAL_ROLES = [
    (UserRole.VIEWER, "viewer", "viewer123"),
    (UserRole.EDITOR, "testuser", "testpass123"),
    (UserRole.MANAGER, "manager", "manager123"),
    (UserRole.ADMIN, "admin", "admin123"),
    (UserRole.SYSTEM_ADMIN, "sysadmin", "sysadmin123"),
]

_ALL_ROLES = [
    (UserRole.CUSTOMER, "customer1", "customer123"),
    *_INTERNAL_ROLES,
]


# ── Build parametrized IDs ──────────────────────────────────────────────


def _cases_for_allowed():
    """Generate cases for each role at or above min_role."""
    for method, url, min_role, desc, _ in MATRIX:
        if min_role == UserRole.CUSTOMER:
            # Customer-only endpoints: ONLY customer should pass
            yield pytest.param(
                method,
                url,
                UserRole.CUSTOMER,
                "customer1",
                "customer123",
                id=f"ALLOW-{desc}-customer",
            )
        else:
            for role, uname, pw in _ALL_ROLES:
                if ROLE_RANK[role] >= ROLE_RANK[min_role]:
                    yield pytest.param(
                        method,
                        url,
                        role,
                        uname,
                        pw,
                        id=f"ALLOW-{desc}-{role.value}",
                    )


def _cases_for_denied():
    """Generate cases for each role BELOW min_role."""
    for method, url, min_role, desc, _ in MATRIX:
        if min_role == UserRole.CUSTOMER:
            # Customer-only: all internal roles should be denied
            for role, uname, pw in _INTERNAL_ROLES:
                yield pytest.param(
                    method,
                    url,
                    role,
                    uname,
                    pw,
                    id=f"DENY-{desc}-{role.value}",
                )
        else:
            for role, uname, pw in _ALL_ROLES:
                if ROLE_RANK[role] < ROLE_RANK[min_role]:
                    yield pytest.param(
                        method,
                        url,
                        role,
                        uname,
                        pw,
                        id=f"DENY-{desc}-{role.value}",
                    )


# ── Fixtures ────────────────────────────────────────────────────────────


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_request(client: TestClient, method: str, url: str, headers: dict) -> int:
    """Fire a request and return the status code."""
    if method == "GET":
        return client.get(url, headers=headers).status_code
    if method == "POST":
        return client.post(url, headers=headers, json={}).status_code
    if method == "DELETE":
        return client.delete(url, headers=headers).status_code
    if method == "PUT":
        return client.put(url, headers=headers, json={}).status_code
    if method == "PATCH":
        return client.patch(url, headers=headers, json={}).status_code
    raise ValueError(f"Unsupported method: {method}")


@pytest.fixture
def matrix_env(db, client):
    """Set up all users and a document so URL templates can be resolved."""
    tenant = create_tenant(db, name="Matrix Tenant", slug="matrix-tenant")
    users = {}
    for role, uname, pw in _ALL_ROLES:
        u = create_user(db, username=uname, plain_password=pw, role=role, tenant_id=tenant.id)
        users[role] = u
    doc = create_document(
        db,
        created_by=users[UserRole.EDITOR].id,
        tenant_id=tenant.id,
        title="Auth Matrix Doc",
    )
    return {"tenant": tenant, "users": users, "doc": doc}


def _resolve_url(url_template: str, matrix_env: dict) -> str:
    return url_template.replace("{doc_id}", str(matrix_env["doc"].id))


# ── Tests ───────────────────────────────────────────────────────────────


class TestAuthorizationMatrixAllowed:
    """Roles at or above the minimum should NOT receive 403."""

    @pytest.mark.parametrize("method,url,role,uname,pw", list(_cases_for_allowed()))
    def test_allowed_role_not_forbidden(self, client, matrix_env, method, url, role, uname, pw):
        headers = _login(client, uname, pw)
        resolved = _resolve_url(url, matrix_env)
        code = _make_request(client, method, resolved, headers)
        # Anything other than 401/403 means the authz layer let us through.
        assert code not in (
            401,
            403,
        ), f"{role.value} should access {method} {resolved} but got {code}"


class TestAuthorizationMatrixDenied:
    """Roles below the minimum should receive 403."""

    @pytest.mark.parametrize("method,url,role,uname,pw", list(_cases_for_denied()))
    def test_denied_role_forbidden(self, client, matrix_env, method, url, role, uname, pw):
        headers = _login(client, uname, pw)
        resolved = _resolve_url(url, matrix_env)
        code = _make_request(client, method, resolved, headers)
        assert code in (403,), f"{role.value} should be denied {method} {resolved} but got {code}"


class TestUnauthenticatedRejected:
    """All matrix endpoints should reject unauthenticated requests."""

    @pytest.mark.parametrize(
        "method,url",
        [pytest.param(m, u, id=desc) for m, u, _, desc, _ in MATRIX],
    )
    def test_no_auth_returns_401_or_403(self, client, matrix_env, method, url):
        resolved = _resolve_url(url, matrix_env)
        code = _make_request(client, method, resolved, headers={})
        assert code in (
            401,
            403,
        ), f"Unauthenticated {method} {resolved} → expected 401/403, got {code}"
