# Audit Remediation — Full-Stack Security Fix Plan

The `PROJECT_FULL_AUDIT.md` lists **16 CRITICAL + 24 HIGH + 29 MEDIUM + 15 LOW** findings. I verified the top findings against actual code and discovered a key discrepancy: **4 findings are already fixed or were never vulnerable** (C7, C8, C14, H-01), while **12 CRITICALs are confirmed still open**. The PRD marks Waves AD/AE/AF as "100% complete" but the code contradicts this.

---

## Audit Accuracy: What's Real vs What's Already Fixed

### Confirmed STILL OPEN (Must Fix)

| ID   | Finding                        | Code Evidence |
|------|--------------------------------|---------------|
| C1   | RAG queries all tenants        | `vector_store.py` — no `tenant_id` in where clause |
| C2   | @mention bypasses RBAC         | `engine.py` — only filters by title match, no visibility/role check |
| C3   | Attachment HMAC broken         | `attachments.py` — 5-part token vs 4-part verifier, sig comparison is meaningless |
| C4   | Company endpoints cross-tenant | `companies.py` — only `list_companies()` scoped, all others unscoped |
| C5   | Support tickets global         | `support_service.py` — `_check_ticket_access()` skips tenant check entirely |
| C13  | Document.tenant_id nullable    | `models/__init__.py` — `nullable=True` on line ~356 |
| C15  | Search analytics exposed       | `search.py` — only `get_current_active_user`, no role/tenant |
| C16  | Feedback PII leak              | `feedback.py` — `require_internal_staff`, returns `user_email` |
| C9   | CD skips tests                 | `cd.yml` — `skip_tests` boolean input present |
| C10  | Security scans soft-fail       | `security.yml` — 7× `continue-on-error: true` |
| H-11 | Auth rate limit exempt         | `rate_limit.py` — login in `EXCLUDED_PATHS` |

### Confirmed FIXED (Update the Audit)

| ID   | Finding                        | Status |
|------|--------------------------------|--------|
| C7   | Version endpoints missing admin | All endpoints properly authenticated |
| C8   | XXE in sitemap/feed            | No `base_url` parameter exists; static XML only |
| C14  | Refresh cookie deleted          | Proper 401 on missing token, no self-destruct |
| H-01 | Chat participant validation     | `_get_chat_with_permission()` enforces checks |

---

## Steps

### Phase 1: Security-Critical Fixes (Production Blockers)

All steps in Phase 1 are independent and can run in parallel.

1. **Fix RAG tenant isolation (C1)** — In `vector_store.py`, add `tenant_id` to the `where` filter on every ChromaDB query. In `rag_tools.py`, pass `tenant_id` from executor context into the query. Verify documents are indexed with `tenant_id` in metadata. **Test:** tenant A search never returns tenant B results.

2. **Fix @mention injection (C2)** — In `engine.py` ~L376-410, after finding the document by title, call `DocumentAccessPolicy.can_view_document(user, document)` from `access_policies.py` before injecting content. Also check `document.status`. **Test:** CUSTOMER @mentions INTERNAL doc → rejected.

3. **Fix attachment HMAC (C3)** — In `attachments.py`, change verifier to expect 5 parts, parse the signature from the token, use `hmac.compare_digest()`, reject future timestamps, add max-age (5 min). **Test:** tampered ticket → 401, expired → 401, valid → works.

4. **Fix company tenant scope (C4)** — In `companies.py`, add `TenantContext` dependency to `get_company()`, `update_company()`, `list_company_users()`, `add_user_to_company()`, `list_company_documents()`, `get_audience_blockers()`. Verify `company.tenant_id` matches. Pattern: replicate what `list_companies()` already does.

5. **Fix support cross-tenant (C5)** — In `support_service.py`: add `.filter(SupportTicket.tenant_id == user.tenant_id)` to `list_tickets()`, add tenant check to `_check_ticket_access()` and `_get_ticket_for_agent()`. At route level in `support.py`, replace `require_internal_user` with `require_role(["ADMIN", "MANAGER"])`.

6. **Fix search analytics (C15)** — In `search.py`, replace `get_current_active_user` with `require_role(["ADMIN", "MANAGER", "SYSTEM_ADMIN"])`. Add tenant scoping for non-sysadmin.

7. **Fix feedback PII (C16)** — In `feedback.py`, replace `require_internal_staff` with `require_role(["ADMIN", "MANAGER"])`. Add tenant scoping. Strip `user_email` from responses for non-admin roles.

8. **Fix Document.tenant_id nullable (C13)** — In `models/__init__.py`, change to `nullable=False`. Create Alembic migration to assign orphaned documents to a default tenant or delete them first.

### Phase 2: CI/CD & Infrastructure (parallel with Phase 1)

9. **Remove CD skip_tests (C9)** — Delete `skip_tests` input from `cd.yml`. Make test step unconditional.

10. **Enforce security scans (C10)** — Remove `continue-on-error: true` from secret detection and dependency audit steps in `security.yml`.

11. **Configure HTTPS (C11)** — In `nginx.conf`: add SSL listener, HTTP→HTTPS redirect, HSTS header. Mount certs in `docker-compose.prod.yml`.

12. **Fix hardcoded secrets (C12)** — In `docker-compose.yml`: use `${SECRET_KEY}` env var. Add startup validation in `config.py` rejecting insecure defaults in production.

13. **Add auth rate limiting (H-11)** — Remove auth paths from `EXCLUDED_PATHS` in `rate_limit.py`. Add 10/min limit for auth endpoints.

14. **Gate demo credentials (H-09)** — In `LoginPage.tsx`: wrap demo creds behind env check.

### Phase 3: HIGH Severity Fixes (depends on Phase 1)

15. **Attachment access check (H-02)** — Verify document access before serving attachments
16. **Collab token ownership (H-03)** — Check edit permission before issuing collab tokens
17. **SemanticSearchTool RBAC (H-04)** — Block CUSTOMER role from semantic search
18. **Redis rate limiting (H-05)** — Replace in-memory counters with Redis backend
19. **Sanitize tool errors (H-06)** — Never expose stack traces to users
20. **Fix CSRF production bypass (H-07)** — Reject missing Origin/Referer in production
21. **Timing-safe user enumeration (H-08)** — Constant-time response for password reset
22. **Path traversal fix (H-10)** — Strip directory components from uploaded filenames
23. **Collab-server timeout (H-12)** — Add 10s timeout to backend HTTP requests
24. **Add 12+ database indexes (H-13)** — New Alembic migration for frequent query columns
25. **Publish tool confirmation (H-15)** — Add `requires_confirmation = True`
26. **Dev JWT key enforcement (H-16)** — Enforce minimum key length in collab-server
27. **Version endpoint role tightening (H-17)** — Restrict to EDITOR+
28. **Word generation sanitization (H-18)** — Sanitize HTML before word generation
29. **Session restore on public routes (H-19)** — Call `tryRestoreSession()` unconditionally
30. **Portal reading-progress fix (H-20)** — Check actual company assignment
31. **WS token auth pattern (H-21)** — Move token from query string to first message
32. **Collab URL unification (H-22)** — Single source of truth for WS URL
33. **Rewrite stale tests (H-23)** — Fix 5 auth failures, extend tenant harness, build RBAC matrix

### Phase 4: MEDIUM Severity Fixes (depends on Phase 3)

34-62. 29 items grouped by area:
- **Input validation:** sort_by whitelist, file size limits, AI tool max_length
- **Auth hardening:** token rotation, session timeout, password consistency
- **Chat fixes:** cross-tenant block, pagination
- **API consistency:** status naming, RSS route, type sync
- **Infrastructure:** CORS, CSP, Docker port binding
- **Frontend:** permission checks for dialogs, prop drilling refactor

### Phase 5: LOW Severity & Cleanup (depends on Phase 4)

63-77. 15 items: Pin Docker images, add `.dockerignore`, configure axios timeout, add `aria-current`, add cache eviction, add token TTL, timezone-aware datetimes, error monitoring integration

### Phase 6: Audit Document Correction

- **Update `PROJECT_FULL_AUDIT.md`:** mark C7, C8, C14, H-01 as fixed. Reduce CRITICAL count from 16 to 12. Update overall rating after remediation.

---

## Relevant Files

| File | Purpose |
|------|---------|
| `permissions.py` | Reuse `require_role()`, `require_permission()` for all auth fixes |
| `tenant.py` | Reuse `TenantContext.can_access_tenant()` for tenant scope fixes |
| `access_policies.py` | Reuse `DocumentAccessPolicy` for @mention and attachment access |
| `test_attack_harness.py` | Extend with company, support, feedback, analytics tests |

---

## Verification

| After     | Action |
|-----------|--------|
| Phase 1   | `pytest backend/tests/ -x` — full suite passes; run extended tenant isolation harness covering companies, support, feedback, analytics |
| Phase 2   | Push branch → verify security scan failure blocks merge; trigger CD → verify no `skip_tests` option |
| Phase 3   | Full test suite + Playwright E2E passes; manual cross-tenant penetration test on all fixed surfaces |
| Phase 4   | Full regression suite; frontend unit tests pass |
| Final     | `docker-compose up` → all 4 services healthy; complete manual security walk-through |

---

## Decisions

1. **C7, C8, C14, H-01 are already fixed** in code — the audit overstates 4 findings. Plan includes correcting the audit document.
2. **PRD Waves AD-AH show checkboxes as complete** but code doesn't reflect this for ~12 findings — implementation takes priority over checkbox status. After fixes, sync PRD checkboxes to reality.
3. **Phase 1 + Phase 2 are the deployment blockers.** No production deployment until both complete.
4. **SQLite → PostgreSQL migration** is mentioned as improvement but deferred from this plan.
5. **C6 (Published Attachment Snapshot)** needs investigation during Phase 1 — if confirmed, it's a medium-effort architectural change.

---

## Further Considerations

- **RBAC Test Matrix** (recommended in Phase 3): Building a systematic endpoint × role test early in Phase 3 gives ongoing regression protection for everything fixed in Phase 1.
- **C6 — Published Attachment Snapshot:** Not yet code-verified. If confirmed, requires creating a centralized `PublishedSnapshotService`. Investigate before starting Phase 3.
- **PRD Cleanup:** After all phases, audit every Wave AD-AH checkbox against code reality and uncheck items that regressed. This prevents future confusion.
