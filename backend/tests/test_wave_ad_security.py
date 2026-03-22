"""Wave AD — Security Hardening Invariant Tests (AD-019 through AD-025)

These tests verify the security fixes introduced in Wave AD remain intact.
"""

import pytest
from app.models import (
    ChangelogEntry,
    Comment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
    UserSession,
)
from tests.factories import create_document, create_tenant, create_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
STRONG_PASSWORD = "Test@1234!"


def _login(client, username, password):
    """Login helper that returns (status_code, json_body)."""
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return r.status_code, r.json()


def _register(client, *, username, email, password, role="system_admin", tenant_id=99):
    """Attempt self-registration with arbitrary role/tenant."""
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Attacker",
            "password": password,
            "role": role,
            "tenant_id": tenant_id,
        },
    )


def _headers_for(client, username, password):
    """Obtain Bearer headers for an existing user."""
    code, data = _login(client, username, password)
    assert code == 200, f"Login failed for {username}: {data}"
    return {"Authorization": f"Bearer {data['access_token']}"}


# ===================================================================
# AD-019 — Self-registration always yields CUSTOMER role
# ===================================================================
class TestAD019SelfRegistration:
    """AD-001 invariant: register endpoint must force role=customer."""

    def test_register_ignores_role_payload(self, client, db):
        """Attempting to register as system_admin should still yield CUSTOMER."""
        r = _register(
            client,
            username="attacker1",
            email="attacker1@evil.com",
            password=STRONG_PASSWORD,
            role="system_admin",
            tenant_id=9999,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["role"] == "customer"
        # tenant_id must be None — self-registration should not assign a tenant
        assert data.get("tenant_id") is None

    def test_register_ignores_admin_role(self, client, db):
        r = _register(
            client,
            username="attacker2",
            email="attacker2@evil.com",
            password=STRONG_PASSWORD,
            role="admin",
        )
        assert r.status_code == 201
        assert r.json()["role"] == "customer"

    def test_register_ignores_editor_role(self, client, db):
        r = _register(
            client,
            username="attacker3",
            email="attacker3@evil.com",
            password=STRONG_PASSWORD,
            role="editor",
        )
        assert r.status_code == 201
        assert r.json()["role"] == "customer"


# ===================================================================
# AD-020 — Revoked sessions cannot be reused
# ===================================================================
class TestAD020RevokedSession:
    """AD-003 invariant: revoked sessions must not be accepted."""

    def test_revoked_session_rejected(self, client, db, default_tenant):
        """After logout (session revocation), the old token must fail."""
        user = create_user(
            db,
            username="revoke_user",
            email="revoke@test.com",
            plain_password="revokepass1",
            role=UserRole.EDITOR,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        # Login
        code, data = _login(client, "revoke_user", "revokepass1")
        assert code == 200
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        # Verify token works
        r = client.get("/api/v1/auth/me", headers=headers)
        assert r.status_code == 200

        # Logout (revokes all sessions)
        client.post("/api/v1/auth/logout", headers=headers)

        # Old token should now be rejected
        r = client.get("/api/v1/auth/me", headers=headers)
        assert r.status_code == 401


# ===================================================================
# AD-021 — Customer cannot see private comments
# ===================================================================
class TestAD021PrivateComments:
    """AD-005 invariant: private comments hidden from customers/viewers."""

    def test_customer_cannot_see_private_comment(self, client, db):
        tenant = create_tenant(db, name="CommentCo", slug="commentco")
        editor = create_user(
            db,
            username="comment_editor",
            email="ceditor@test.com",
            plain_password="editpass1",
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
            is_active=True,
        )
        customer = create_user(
            db,
            username="comment_cust",
            email="ccust@test.com",
            plain_password="custpass1",
            role=UserRole.CUSTOMER,
            tenant_id=tenant.id,
            is_active=True,
        )
        doc = create_document(
            db,
            title="PrivComDoc",
            created_by=editor.id,
            tenant_id=tenant.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        # Editor creates a private comment directly in DB
        private_comment = Comment(
            document_id=doc.id,
            user_id=editor.id,
            content="Secret internal note",
            is_private=True,
        )
        public_comment = Comment(
            document_id=doc.id,
            user_id=editor.id,
            content="Public note",
            is_private=False,
        )
        db.add_all([private_comment, public_comment])
        db.commit()

        # Customer lists comments
        cust_headers = _headers_for(client, "comment_cust", "custpass1")
        r = client.get(f"/api/v1/documents/{doc.id}/comments", headers=cust_headers)
        assert r.status_code == 200
        comments = r.json()

        # Customer should NOT see the private comment
        contents = [c["content"] for c in comments]
        assert "Secret internal note" not in contents
        # But CAN see the public one (needs contributor access or to be author)
        # The customer is NOT a contributor, so they shouldn't see any

    def test_customer_cannot_create_private_comment(self, client, db):
        """AD-005: customers cannot set is_private=True."""
        tenant = create_tenant(db, name="CommentCo2", slug="commentco2")
        editor = create_user(
            db,
            username="c2editor",
            email="c2editor@test.com",
            plain_password="editpass1",
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
            is_active=True,
        )
        customer = create_user(
            db,
            username="c2cust",
            email="c2cust@test.com",
            plain_password="custpass1",
            role=UserRole.CUSTOMER,
            tenant_id=tenant.id,
            is_active=True,
        )
        doc = create_document(
            db,
            title="CustPrivDoc",
            created_by=editor.id,
            tenant_id=tenant.id,
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        cust_headers = _headers_for(client, "c2cust", "custpass1")
        r = client.post(
            f"/api/v1/documents/{doc.id}/comments",
            headers=cust_headers,
            json={"content": "I want this private", "is_private": True},
        )
        # Even if accepted, is_private should be forced to False
        if r.status_code in (200, 201):
            assert r.json()["is_private"] is False


# ===================================================================
# AD-022 — Company listing scoped to caller's tenant
# ===================================================================
class TestAD022CompanyScoping:
    """AD-006 invariant: non-system-admins only see their own tenant."""

    def test_admin_sees_only_own_tenant(self, client, db):
        t1 = create_tenant(db, name="TenantA", slug="tenant-a")
        t2 = create_tenant(db, name="TenantB", slug="tenant-b")
        admin = create_user(
            db,
            username="scoped_admin",
            email="scoped@a.com",
            plain_password="adminpass1",
            role=UserRole.ADMIN,
            tenant_id=t1.id,
            is_active=True,
        )
        headers = _headers_for(client, "scoped_admin", "adminpass1")
        r = client.get("/api/v1/companies", headers=headers)
        assert r.status_code == 200
        data = r.json()
        tenant_ids = [c["id"] for c in data["items"]]
        assert t1.id in tenant_ids
        assert t2.id not in tenant_ids

    def test_system_admin_sees_all_tenants(self, client, db):
        t1 = create_tenant(db, name="TenantC", slug="tenant-c")
        t2 = create_tenant(db, name="TenantD", slug="tenant-d")
        sa = create_user(
            db,
            username="sa_scope",
            email="sa@scope.com",
            plain_password="sapass123",
            role=UserRole.SYSTEM_ADMIN,
            is_active=True,
        )
        headers = _headers_for(client, "sa_scope", "sapass123")
        r = client.get("/api/v1/companies", headers=headers)
        assert r.status_code == 200
        data = r.json()
        tenant_ids = [c["id"] for c in data["items"]]
        assert t1.id in tenant_ids
        assert t2.id in tenant_ids


# ===================================================================
# AD-023 — Changelog defaults to published-only
# ===================================================================
class TestAD023ChangelogDefault:
    """AD-007 invariant: public changelog hides unpublished entries."""

    def test_default_hides_unpublished(self, client, db):
        admin = create_user(
            db,
            username="cl_admin",
            email="cl@admin.com",
            plain_password="clpass123",
            role=UserRole.ADMIN,
            is_active=True,
        )
        published = ChangelogEntry(
            title="Released Feature",
            content="Details here",
            published=True,
            created_by=admin.id,
        )
        draft = ChangelogEntry(
            title="Secret Draft",
            content="Not ready yet",
            published=False,
            created_by=admin.id,
        )
        db.add_all([published, draft])
        db.commit()

        # Public call (no auth, default published_only=True)
        r = client.get("/api/v1/public/changelog")
        assert r.status_code == 200
        data = r.json()
        titles = [e["title"] for e in data["items"]]
        assert "Released Feature" in titles
        assert "Secret Draft" not in titles

    def test_explicit_unpublished_shows_all(self, client, db, admin_headers, test_admin):
        """Explicitly passing published_only=false shows drafts (admin/management flow)."""
        draft = ChangelogEntry(
            title="Draft Entry",
            content="WIP",
            published=False,
            created_by=test_admin.id,
        )
        db.add(draft)
        db.commit()

        r = client.get("/api/v1/changelog", params={"published_only": "false"}, headers=admin_headers)
        assert r.status_code == 200
        titles = [e["title"] for e in r.json()["items"]]
        assert "Draft Entry" in titles


# ===================================================================
# AD-024 — Password complexity enforcement
# ===================================================================
class TestAD024PasswordComplexity:
    """AD-011 invariant: weak passwords are rejected at registration."""

    @pytest.mark.parametrize(
        "password,reason",
        [
            ("alllower1!", "no uppercase"),
            ("ALLUPPER1!", "no lowercase"),
            ("NoDigits!!", "no digit"),
            ("NoSpecial1", "no special char"),
            ("Short1!", "too short"),
        ],
    )
    def test_weak_password_rejected(self, client, db, password, reason):
        r = _register(
            client,
            username=f"weak_{reason.replace(' ', '_')}",
            email=f"weak_{reason.replace(' ', '_')}@test.com",
            password=password,
        )
        assert r.status_code == 422, f"Expected 422 for {reason}, got {r.status_code}"

    def test_strong_password_accepted(self, client, db):
        r = _register(
            client,
            username="strong_user",
            email="strong@test.com",
            password=STRONG_PASSWORD,
        )
        assert r.status_code == 201


# ===================================================================
# AD-025 — Concurrent session limit
# ===================================================================
class TestAD025ConcurrentSessions:
    """AD-013 invariant: oldest sessions are revoked when limit exceeded."""

    def test_session_limit_revokes_oldest(self, client, db, default_tenant):
        from app.config import settings

        max_sessions = settings.MAX_CONCURRENT_SESSIONS  # default 5

        user = create_user(
            db,
            username="session_user",
            email="session@test.com",
            plain_password="sesspass1",
            role=UserRole.EDITOR,
            is_active=True,
            tenant_id=default_tenant.id,
        )

        tokens = []
        for i in range(max_sessions + 1):
            code, data = _login(client, "session_user", "sesspass1")
            assert code == 200, f"Login {i} failed"
            tokens.append(data["access_token"])

        # The very first token should now be revoked
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens[0]}"})
        assert r.status_code == 401, "Oldest session should have been revoked"

        # The latest token should still work
        r = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens[-1]}"}
        )
        assert r.status_code == 200, "Newest session should still be valid"


# ===================================================================
# AD-Extra — Login returns httpOnly cookie
# ===================================================================
class TestADLoginCookie:
    """AD-004 invariant: login sets an httpOnly refresh cookie."""

    def test_login_sets_refresh_cookie(self, client, db):
        create_user(
            db,
            username="cookie_user",
            email="cookie@test.com",
            plain_password="cookiepass1",
            role=UserRole.EDITOR,
            is_active=True,
        )
        r = client.post(
            "/api/v1/auth/login",
            json={"username": "cookie_user", "password": "cookiepass1"},
        )
        assert r.status_code == 200
        # TestClient exposes cookies set on the response
        cookies = r.cookies
        # The refresh_token cookie is path-scoped to /api/v1/auth/refresh
        # so it may or may not show in r.cookies depending on client path.
        # At minimum, the Set-Cookie header must be present.
        set_cookie_headers = r.headers.get_list("set-cookie") if hasattr(r.headers, "get_list") else [
            v for k, v in r.headers.items() if k.lower() == "set-cookie"
        ]
        cookie_str = "; ".join(set_cookie_headers)
        assert "refresh_token" in cookie_str, "Login response must set refresh_token cookie"
        assert "httponly" in cookie_str.lower(), "Refresh cookie must be httpOnly"
