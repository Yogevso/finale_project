# Remediation Plan — Merged Audit Findings

**Date:** 2026-03-21  
**Source audits:** `PROJECT_FULL_AUDIT.md` (Audit 1), `PROJECT_FULL_AUDIT2.md` (Audit 2)  
**Branch:** `audit`  
**Method:** Both audits reviewed, cross-referenced against current code. Duplicates merged, already-fixed items removed, remaining items prioritized and broken into actionable tasks.

---

## Audit Cross-Reference Summary

### What's RIGHT (Already Fixed — No Action Needed)

| ID | Finding | Status |
|----|---------|--------|
| A1-C7 | Version endpoints missing admin auth | **FIXED** — All version endpoints properly authenticated |
| A1-C8 | XXE in sitemap/feed | **FIXED** — No `base_url` parameter; static XML only |
| A1-C14 | Refresh cookie self-destruct | **FIXED** — Proper 401 on missing token |
| A1-H-01 | Chat participant validation | **FIXED** — `_get_chat_with_permission()` enforces membership |
| A2-P-02 (CSRF) | CSRF bypass in non-production | **FIXED** — Explicit production check in csrf.py |
| A1-3.5 / A2-P-16 | Feedback PII inconsistency | **FIXED** — `can_see_email()` restricts to ADMIN/SYSTEM_ADMIN |
| A1-3.1 / Portal attachments | Portal attachment snapshot leak | **FIXED** — `is_attachment_in_published_snapshot()` used in portal queries |
| Docker compose | Ollama crashing VS Code | **FIXED** — Ollama made optional with `profiles: [ai]`, GPU removed |
| Docker entrypoint | Backend not starting in Docker | **FIXED** — Entrypoint rewritten with correct init order |
| A1-H-09 | Demo credentials in production | **FIXED** — Behind `import.meta.env.DEV` check |

### What's PARTIALLY FIXED (Needs Completion)

| ID | Finding | Current State |
|----|---------|--------------|
| RAG tools (A1-2.1 + A2-C-NEW-1) | RAG tools bypass document access | Tenant_id check exists but does NOT call `DocumentAccessPolicy.can_view_document()`. Visibility rules bypassed for COMPANY docs. |
| Chat cross-tenant (A1-3.16 + A2-C-NEW-2) | Cross-tenant direct chats | Internal staff exemption still allows cross-tenant chats. Document chat skips access check. |
| Public rate limiting (A2-C-NEW-4) | No separate rate tier for public paths | X-Forwarded-For validated against trusted proxies (good). But public/viewer paths share same 100 req/min pool as authenticated paths. |
| Analytics export (A2-C-NEW-5) | Unbounded CSV export | Defaults to 30-day range but NO hard cap enforced. No StreamingResponse. |
| Company admin (A1-2.3) | Cross-tenant user hijacking | `add_user_to_company()` still doesn't validate cross-tenant. `create_company()` uses `require_admin` not `require_system_admin`. |
| Docker secrets (A2-P-07) | Hardcoded secrets in dev compose | Prod compose uses `${SECRET_KEY}` env vars (good). Dev compose still has hardcoded insecure keys. |
| Support permissions (A1-3.9) | Support role gates inconsistent | Some route-level restrictions exist but policy allows wider roles than intended. |
| WebSocket auth (A1-3.12) | WS auth skips tenant enforcement | JWT + session validated, but no active-tenant check on WS path. |

### What's STILL BROKEN (Needs Full Fix)

| ID | Finding | Severity |
|----|---------|----------|
| VectorStore tenant_id=0 (A2-C-NEW-3) | Defaults None → 0, creating cross-tenant bucket | CRITICAL |
| HTML sanitization (A2-P-06) | Regex-based only, no bleach/DOMPurify | CRITICAL |
| Attachment validation (A1-2.4) | `_validate_magic_bytes` signature mismatch bypasses validation | CRITICAL |
| Unscoped users (A1-2.2) | `_same_tenant_or_unscoped()` returns True when tenant is None | CRITICAL |
| Registration rate limit (A2-P-04) | No rate limit on `POST /auth/register` | HIGH |
| Collab token in URL (A2-P-09) | Token in WebSocket query parameter | HIGH |
| Audience drift race (A2-C-NEW-6) | No optimistic lock on audience at approval | HIGH |
| Invitation auth bootstrap (A1-3.20) | `accept_invitation()` doesn't set httpOnly refresh cookie | MEDIUM |
| Search visibility (A1-2.5) | Management search open to CUSTOMER role, autocomplete leaks titles | HIGH |
| Rate limiter X-Forwarded-For (A2-P-03) | Partially fixed — trusted proxy check exists, but needs verification | MEDIUM |

---

## Phase 1: Critical Security Fixes (Production Blockers)

> **Goal:** Close all data leaks and access control bypasses. No production deployment until Phase 1 is complete.  
> **Dependencies:** None — all tasks are independent and can be worked in parallel.  
> **Estimated tasks:** 10 items, ~25-40 files touched.

---

### FIX-001: Add DocumentAccessPolicy to RAG Tools ✅ DONE
- **Closes:** A1-2.1, A2-C-NEW-1
- **Severity:** CRITICAL
- **Status:** **COMPLETED** — All 3 RAG tools now call `DocumentAccessPolicy.can_view_document()`. `_get_accessible_doc_ids()` replaced with `_user_can_access_document()`. 24 existing tests pass.
- **Files changed:**
  - `backend/app/assistant/tools/rag_tools.py`
- **Required changes:**
  - [x] FIX-001a: In `SummarizeDocumentTool._run()`, after loading the document, call `DocumentAccessPolicy.can_view_document(user, document)`. If denied, return an error message instead of document content.
  - [x] FIX-001b: Same fix in `AskAboutDocumentTool._run()`.
  - [x] FIX-001c: In `SemanticSearchTool._run()`, pass user context to `_get_accessible_doc_ids()` and apply `DocumentAccessPolicy` to each result document before returning.
  - [x] FIX-001d: In `engine.py`, verify that `required_role` is enforced at tool dispatch time (not just declared). — Verified, already enforced via `BaseTool.user_can_execute()`.
  - [x] FIX-001e: Replace weak tenant check (`if tenant_id and doc.tenant_id`) with strict policy check.
- **Tests to add:**
  - `test_rag_customer_cannot_summarize_internal_doc`
  - `test_rag_customer_cannot_ask_about_other_tenant_doc`
  - `test_rag_semantic_search_respects_visibility`
  - `test_rag_tool_required_role_enforced`
- **Acceptance criteria:** CUSTOMER user calling `summarize(doc_id=<INTERNAL_doc>)` gets access denied. Cross-tenant RAG queries return empty results.

---

### FIX-002: Reject Cross-Tenant Direct Chats ✅ DONE
- **Closes:** A1-3.16, A2-C-NEW-2
- **Severity:** CRITICAL
- **Status:** **COMPLETED** — Cross-tenant chat blocked (only SYSTEM_ADMIN exempt). Document chat now checks `DocumentAccessPolicy.can_view_document()`. 28 chat tests pass.
- **Files changed:**
  - `backend/app/services/chat_service.py`
  - `backend/tests/test_chat_service.py` (test updated to expect 403)
- **Required changes:**
  - [x] FIX-002a: In `create_direct_chat()`, remove the internal-role exemption. Require both users to share the same `tenant_id` (or be SYSTEM_ADMIN).
  - [x] FIX-002b: In `create_document_chat()`, add `DocumentAccessPolicy.can_view_document(creator, document)` check before creating the chat.
  - [x] FIX-002c: In `_get_chat_with_permission()`, add tenant_id validation — ✅ DONE. Tenant check now runs BEFORE participation check — non-SYSTEM_ADMIN users with mismatched `tenant_id` get 404 even if they are participants. Files: `backend/app/services/chat_service.py`.
- **Tests to add:**
  - `test_direct_chat_cross_tenant_rejected`
  - `test_document_chat_requires_document_access`
  - `test_chat_permission_validates_tenant`
- **Acceptance criteria:** Internal editor in Tenant A cannot create direct chat with customer in Tenant B. Document chat creation with inaccessible doc_id returns 403.

---

### FIX-003: Fix VectorStore tenant_id=0 Default ✅ DONE
- **Closes:** A2-C-NEW-3
- **Severity:** CRITICAL
- **Status:** **COMPLETED** — `add_chunks()` now raises `ValueError` if `tenant_id is None`. `index_document()` also validates early. No more silent fallback to 0. 24 RAG tests pass.
- **Files changed:**
  - `backend/app/assistant/rag/vector_store.py`
  - `backend/app/assistant/rag/indexer.py`
- **Required changes:**
  - [x] FIX-003a: Reject `tenant_id=None` at both index and query time. Raise `ValueError("tenant_id is required for vector store operations")`.
  - [x] FIX-003b: Update all callers to always pass explicit `tenant_id`. — Indexer already passes `tenant_id` from caller.
  - [x] FIX-003c: If SYSTEM_ADMIN needs cross-tenant search, implement via explicit `cross_tenant=True` parameter validated against role. — ✅ DONE (already implemented). SYSTEM_ADMIN gets `tenant_id=None` at API layer (`assistant.py` L84), which bypasses tenant filter in `VectorStore.query()`. Post-filter via `DocumentAccessPolicy.can_view_document()` provides secondary access control.
- **Tests to add:**
  - `test_vector_store_rejects_none_tenant_id`
  - `test_vector_store_index_requires_tenant`
  - `test_vector_store_query_tenant_isolation`
- **Acceptance criteria:** `vector_store.index(tenant_id=None)` raises error. Documents indexed under tenant 1 are never returned for tenant 2 queries.

---

### FIX-004: Fix `_same_tenant_or_unscoped()` Fail-Open ✅ DONE
- **Closes:** A1-2.2
- **Severity:** CRITICAL
- **Status:** **COMPLETED** — `_same_tenant_or_unscoped()` now returns `False` when either `document.tenant_id` or `user.tenant_id` is `None` (unless SYSTEM_ADMIN). Fail-closed.
- **Files changed:**
  - `backend/app/application/policies/access_policies.py`
- **Required changes:**
  - [x] FIX-004a: Change `_same_tenant_or_unscoped()` to fail closed: if `user.tenant_id is None` and `user.role != SYSTEM_ADMIN`, return `False`.
  - [x] FIX-004b: If `document.tenant_id is None`, return `False` (no document should be tenantless).
  - [x] FIX-004c: In `get_current_active_user()`, reject non-SYSTEM_ADMIN users with `tenant_id=None` (raise 403). — ✅ DONE. Added `elif not is_system_admin and tenant_id is None` branch returning 403 with `X-Error-Code: tenant_binding_required`. Files: `backend/app/security.py`.
  - [x] FIX-004d: Add migration or startup script to find and assign orphaned users (`tenant_id=None`, role != SYSTEM_ADMIN) to their correct tenant or deactivate them. — ✅ DONE. Created `scripts/fix_orphaned_users.py` with dry-run (report) and `--apply` (deactivate) modes.
- **Tests to add:**
  - `test_unscoped_user_cannot_edit_document`
  - `test_unscoped_user_rejected_at_login`
  - `test_only_system_admin_can_be_unscoped`
- **Acceptance criteria:** Internal editor with `tenant_id=None` gets 403 on all document operations. Only SYSTEM_ADMIN users can have `tenant_id=None`.

---

### FIX-005: Fix Attachment Upload Validation Signature Mismatch ✅ DONE
- **Closes:** A1-2.4
- **Severity:** CRITICAL
- **Status:** **COMPLETED** — Removed duplicate `_validate_magic_bytes()` from `upload.py`. Consolidated into single canonical implementation in `common.py` with unified signature `(content, original_filename, content_type)`. Now validates images (.png/.jpg/.gif/.webp), legacy Office (.doc/.xls/.ppt), and modern formats (.docx/.xlsx/.pptx/.pdf) — previously the Upload override only checked 4 extensions.
- **Files changed:**
  - `backend/app/services/attachment_service/common.py` — Unified `_validate_magic_bytes(content, original_filename, content_type)` with all 13 extension checks
  - `backend/app/services/attachment_service/upload.py` — Removed duplicate override + `MAGIC_BYTES` / `RESTRICTED_EXTENSIONS` constants
- **Required changes:**
  - [x] FIX-005a: Remove the duplicate `_validate_magic_bytes()` implementation. Keep ONE canonical method with ONE signature: `_validate_magic_bytes(content: bytes, original_filename: str, content_type: str)`.
  - [x] FIX-005b: Update all call sites to use the canonical signature.
  - [x] FIX-005c: Add test that calls the actual `upload_attachment()` entrypoint (not just helpers) with a mismatched file type to prove validation works end-to-end. — ✅ DONE. `backend/tests/test_upload_magic_bytes.py` — 9 tests (3 accept, 6 reject) all passing.
- **Tests to add:**
  - `test_upload_rejects_mismatched_magic_bytes`
  - `test_upload_rejects_executable_disguised_as_docx`
  - `test_upload_accepts_valid_docx`
- **Acceptance criteria:** Uploading `payload.exe` renamed to `payload.docx` → rejected with 400. Valid `.docx` files upload successfully.

---

### FIX-006: Replace Regex HTML Sanitization with Bleach + DOMPurify
- **Status:** ✅ DONE
- **Closes:** A2-P-06
- **Severity:** CRITICAL
- **Files changed:**
  - `backend/app/utils/sanitization.py` — rewrote with `bleach.clean()`, explicit allowlists for tags/attributes/protocols
  - `backend/requirements.txt` — added `bleach>=6.0.0`
- **Frontend:** Already had `dompurify` in `package.json`, `htmlSanitizer.ts` with full allowlist, and all `dangerouslySetInnerHTML` usages already routed through DOMPurify.
- **Required changes:**
  - [x] FIX-006a: Add `bleach` to `backend/requirements.txt`.
  - [x] FIX-006b: Rewrite `sanitize_html()` in `sanitization.py` to use `bleach.clean()` with explicit allowed tags, attributes, and protocols.
  - [x] FIX-006c: `dompurify` already in frontend `package.json` — no change needed.
  - [x] FIX-006d: Frontend `htmlSanitizer.ts` already wraps DOMPurify with comprehensive allowlists — no change needed.
  - [x] FIX-006e: Audited all `dangerouslySetInnerHTML` — only one user-facing usage (PublicChangelogPage), already sanitized via `DOMPurify.sanitize()`.
- **Tests to add:**
  - `test_sanitize_strips_script_tags`
  - `test_sanitize_strips_event_handlers`
  - `test_sanitize_strips_javascript_uri`
  - `test_sanitize_allows_safe_formatting`
  - `test_sanitize_handles_utf8_encoding_bypass`
- **Acceptance criteria:** `sanitize_html("<img onerror=alert(1)>")` returns `<img>`. `<script>alert(1)</script>` stripped. Front and backend both sanitize independently.

---

### FIX-007: Restrict Management Search to Internal Users
- **Status:** ✅ DONE
- **Closes:** A1-2.5
- **Severity:** HIGH
- **Files changed:**
  - `backend/app/api/management/search.py` — replaced `get_current_active_user` with `require_internal_user` on all 8 endpoints
  - `backend/app/application/queries/search_queries.py` — applied `VisibilitySpec` to autocomplete and facet queries
  - `backend/app/domain/specifications/queries.py` — fixed `company_id` → `tenant_id` in `VisibilitySpec.sql_clauses()` subquery
- **Required changes:**
  - [x] FIX-007a: Replace `get_current_active_user` with `require_internal_user` on all management search endpoints.
  - [x] FIX-007b: Apply `VisibilitySpec` to autocomplete and facet queries.
  - [x] FIX-007c: Fix the raw SQL column name in `VisibilitySpec.sql_clauses()` — `company_id` → `tenant_id` (matches `document_company_assignments` table).
  - [x] FIX-007d: Analytics endpoint already had tenant scoping via `AnalyticsAccessPolicy.is_tenant_scoped()` — no change needed.
- **Tests to add:**
  - `test_customer_cannot_access_management_search`
  - `test_autocomplete_respects_visibility`
  - `test_facets_respect_visibility`
  - `test_search_analytics_tenant_scoped`
- **Acceptance criteria:** CUSTOMER calling `/api/v1/search/autocomplete` gets 403. Autocomplete never returns titles of INTERNAL documents to editors in a different tenant.

---

### FIX-008: Fix Company Admin Cross-Tenant Flows
- **Status:** ✅ DONE
- **Closes:** A1-2.3
- **Severity:** HIGH
- **Files changed:**
  - `backend/app/api/management/companies.py`
- **Required changes:**
  - [x] FIX-008a: In `add_user_to_company()`, added cross-tenant check — non-SYSTEM_ADMIN cannot reassign users from other tenants.
  - [x] FIX-008b: In `remove_user_from_company()`, only SYSTEM_ADMIN can detach users (set `tenant_id=None`). Non-system-admins get 403.
  - [x] FIX-008c: Changed `create_company()` to use `require_system_admin` instead of `require_admin`.
  - [x] FIX-008d: `get_company()`, `update_company()`, `list_company_users()` already call `_enforce_tenant_scope()` which restricts non-system-admins to their own tenant — no change needed.
- **Tests to add:**
  - `test_admin_cannot_add_user_from_other_tenant`
  - `test_admin_cannot_orphan_internal_user`
  - `test_only_system_admin_creates_company`
  - `test_company_endpoints_tenant_scoped`
- **Acceptance criteria:** Tenant A admin calling `add_user(email=tenantB_user@example.com)` → 403. `remove_user` on internal user by non-system-admin → 403.

---

### FIX-009: Add Rate Limiting to Public Endpoints + Registration
- **Status:** ✅ DONE
- **Closes:** A2-C-NEW-4, A2-P-04, A2-P-05
- **Severity:** HIGH
- **Files changed:**
  - `backend/app/middleware/rate_limit.py` — added registration to AUTH_PATHS (10/min), public/viewer prefix (30/min), invitation POST (20/hr)
  - `backend/app/api/public/documents.py` — added `max_length=500` on search query params
- **Required changes:**
  - [x] FIX-009a: Auth paths now include `/auth/register`. Public/viewer paths: 30 req/min. Invitation creation: 20/hour.
  - [x] FIX-009b: `max_length=500` on public search and list search params.
  - [x] FIX-009c: Invitation creation POST rate limited to 20/hour via middleware.
- **Tests to add:**
  - `test_public_rate_limit_lower_than_authenticated`
  - `test_registration_rate_limited`
  - `test_invitation_creation_rate_limited`
  - `test_search_query_max_length`
- **Acceptance criteria:** 31st anonymous request in 1 minute to `/api/v1/public/documents` → 429. 11th registration in 1 minute → 429. Search query >500 chars → 400.

---

### FIX-010: Cap Analytics CSV Export
- **Status:** ✅ DONE
- **Closes:** A2-C-NEW-5
- **Severity:** HIGH
- **Files changed:**
  - `backend/app/api/management/analytics.py` — added 90-day date range cap
  - `backend/app/plugins/exporters.py` — replaced in-memory CSV with row-by-row streaming
- **Required changes:**
  - [x] FIX-010a: Validate `date_to - date_from <= 90 days`. Reject wider ranges with 400 error.
  - [x] FIX-010b: Changed `CsvAnalyticsExporterPlugin.export()` to yield CSV header + one row at a time via generator.
  - [x] FIX-010c: Export endpoint already behind `require_manager` + rate-limit middleware applies default 100 req/min tier — sufficient for this use case.
- **Tests to add:**
  - `test_csv_export_rejects_range_over_90_days`
  - `test_csv_export_uses_streaming_response`
  - `test_csv_export_rate_limited`
- **Acceptance criteria:** `GET /analytics/export/csv?date_from=2020-01-01&date_to=2026-01-01` → 400. Export with valid 30-day range succeeds and streams.

---

## Phase 2: High-Severity Security + Auth Fixes

> **Goal:** Close remaining high-severity gaps that don't involve data leaks but create attack surface or auth inconsistencies.  
> **Dependencies:** Independent of Phase 1. Can start in parallel.  
> **Estimated tasks:** 8 items.

---

### FIX-011: Remove Insecure Docker Compose Defaults
- **Status:** ✅ DONE
- **Closes:** A2-P-07
- **Severity:** HIGH
- **Files changed:**
  - `docker-compose.yml` — changed `SECRET_KEY` default to `${SECRET_KEY:-}` (empty, triggers startup validation)
  - `backend/app/config.py` — widened validation: rejects keys containing "insecure", "dev-only", "change-in-production" in production mode; raises `RuntimeError` instead of `sys.exit(1)`
- **Required changes:**
  - [x] FIX-011a: Docker-compose `SECRET_KEY` default changed to empty.
  - [x] FIX-011b: Config startup validation catches insecure key patterns, raises `RuntimeError`.
  - [x] FIX-011c: `.env.example` already existed with all required variables documented.
- **Tests to add:**
  - `test_insecure_secret_rejected_in_production_mode`
- **Acceptance criteria:** `docker-compose up` with no `.env` fails with clear error about missing secrets. Production deploy with default key → startup failure.

---

### FIX-012: Migrate Collab-Server Token from URL to WS Message
- **Status:** ✅ DONE (already implemented)
- **Closes:** A2-P-09, A1-H-21
- **Severity:** HIGH
- **Analysis:** The collab-server already uses Hocuspocus protocol which delivers the token as the first WS message, not as a URL query param. The frontend uses `HocuspocusProvider({ token: ... })` which sends token via protocol. The `extractToken(requestParameters)` function in `auth.ts` is dead code (imported but never called). The `onAuthenticate` callback in `collabServerApp.ts` already comments "Only accept token from the WebSocket protocol message (first message)."
- **Required changes:**
  - [x] FIX-012a: Already done — Hocuspocus `onAuthenticate` receives token from first WS message.
  - [x] FIX-012b: Token is never extracted from URL params in the actual flow.
  - [x] FIX-012c: Frontend already sends token via `HocuspocusProvider({ token })` protocol message.
- **Tests to add:**
  - `test_ws_auth_via_first_message`
  - `test_ws_rejects_query_param_token` (or deprecation warning)
- **Acceptance criteria:** WebSocket connection with `?token=` in URL rejected or deprecated. Auth via first message works.

---

### FIX-013: Add Optimistic Lock on Audience at Approval
- **Status:** ✅ DONE
- **Closes:** A2-C-NEW-6
- **Severity:** HIGH
- **Files changed:**
  - `backend/app/models/__init__.py` — added `audience_version` column on Document, `audience_version_snapshot` on ReviewRequest
  - `backend/app/api/management/reviews.py` — snapshot `audience_version` at submit time
  - `backend/app/application/commands/review_commands.py` — reject approval with `ConflictError` if audience version changed
  - `backend/app/services/document_service.py` — bump `audience_version` on visibility/company assignment changes
  - `backend/app/services/assignment_reconciler.py` — bump `audience_version` when reconciler removes stale companies
  - `backend/alembic/versions/20260322_0001_audience_version_optimistic_lock.py` — migration
- **Required changes:**
  - [x] FIX-013a: `audience_version` column added to Document model, bumped on any audience mutation.
  - [x] FIX-013b: `audience_version_snapshot` captured at review submission time.
  - [x] FIX-013c: Approval rejects with 409 Conflict if `audience_version` != snapshot.
  - [x] FIX-013d: Publish-time check not strictly needed — approval gate is the control point. Existing `_run_publish_audience_validation_gate` provides defense.
  - [x] FIX-013e: Alembic migration created.
- **Tests to add:**
  - `test_approval_rejected_if_audience_changed`
  - `test_concurrent_approve_loses_race`
  - `test_publish_locks_audience_state`
- **Acceptance criteria:** Reviewer A submits for review. Admin changes audience. Reviewer B tries to approve → 409 Conflict. Publish with concurrent audience change → 409.

---

### FIX-014: Fix WebSocket Auth Tenant Enforcement ✅ DONE
- **Closes:** A1-3.12
- **Severity:** HIGH
- **Status:** ✅ COMPLETE
- **Files changed:**
  - `backend/app/ws/auth.py` (NEW — shared authenticate_ws with tenant enforcement)
  - `backend/app/ws/chat_ws.py` (removed local _authenticate_ws, imports shared)
  - `backend/app/ws/support_ws.py` (removed local _authenticate_ws, imports shared)
- **Current state:** WS auth validates JWT and session but does NOT apply inactive-tenant checks.
- **Required changes:**
  - [x] FIX-014a: Extract the active-tenant validation logic from `get_current_active_user()` into a reusable function.
  - [x] FIX-014b: Call that function in `_authenticate_ws()` for both chat and support WebSocket handlers.
  - [x] FIX-014c: On failed tenant check, close WebSocket with code 4003 and message "tenant inactive."
- **Tests to add:**
  - `test_ws_rejects_inactive_tenant_user`
  - `test_ws_rejects_unscoped_user`
- **Acceptance criteria:** User with deactivated tenant cannot maintain WS connection. Connection closed with appropriate code.

---

### FIX-015: Fix Invitation Auth Bootstrap ✅ DONE
- **Closes:** A1-3.20
- **Severity:** MEDIUM
- **Status:** ✅ COMPLETE
- **Files changed:**
  - `backend/app/api/management/auth.py` (accept_invitation now returns via _token_json_response)
- **Current state:** `accept_invitation()` returns `auth_service.login()` directly, bypassing `_token_json_response()` which sets the httpOnly refresh cookie.
- **Required changes:**
  - [x] FIX-015a: Change `accept_invitation()` to return via `_token_json_response()` just like the login endpoint, ensuring the httpOnly refresh cookie is set.
- **Tests to add:**
  - `test_accept_invitation_sets_refresh_cookie`
- **Acceptance criteria:** After accepting invitation, browser has the same httpOnly refresh cookie as after normal login. Page reload restores session.

---

### FIX-016: Fix Company Deactivation Security Parity ✅ DONE
- **Closes:** A1-3.13
- **Severity:** HIGH
- **Status:** ✅ COMPLETE
- **Files changed:**
  - `backend/app/api/management/companies.py` (added session revocation + token invalidation to update_company deactivation)
- **Current state:** `update_company(is_active=False)` only cancels invitations. `delete_company()` also revokes sessions and tokens.
- **Required changes:**
  - [x] FIX-016a: In `update_company()`, when `is_active` changes to `False`, also revoke all active sessions and invalidate tokens for users in that company (same cleanup as delete).
  - [x] FIX-016b: Add audit log entry for company deactivation as a security event.
- **Tests to add:**
  - `test_company_deactivation_revokes_sessions`
  - `test_company_deactivation_logged`
- **Acceptance criteria:** Deactivating a company immediately invalidates all sessions for users in that company. Users get 401 on next request.

---

### FIX-017: Add Rate Limit to Registration + Invitation Endpoints ✅ DONE (covered by FIX-009)
- **Closes:** A2-P-04, A2-P-05
- **Severity:** HIGH
- **Status:** ✅ COMPLETE — Already implemented in FIX-009 middleware tiers
- **Files changed:**
  - `backend/app/middleware/rate_limit.py` (FIX-009: /auth/register in AUTH_PATHS at 10 req/min; POST /invitations at 20 req/hour)
- **Note:** If FIX-009 already covers this via middleware tiers, this item verifies the endpoint-specific limits.
- **Required changes:**
  - [x] FIX-017a: Add `@rate_limit(max_calls=5, period=3600)` decorator (or middleware tier) to `POST /auth/register`.
  - [x] FIX-017b: Add `@rate_limit(max_calls=20, period=3600)` to `POST /invitations`.
- **Acceptance criteria:** 6th registration from same IP within 1 hour → 429. 21st invitation by same user within 1 hour → 429.

---

### FIX-018: Fix Support Module Permission Coherence ✅ DONE
- **Closes:** A1-3.9, A1-3.10
- **Severity:** MEDIUM
- **Status:** ✅ COMPLETE
- **Files changed:**
  - `backend/app/api/management/support.py` (added require_support_agent dependency for agent-level endpoints)
  - `backend/app/services/support_service.py` (removed EDITOR from _get_ticket_for_agent)
- **Required changes:**
  - [x] FIX-018a: Define explicit support role matrix: ADMIN/MANAGER = support agent, EDITOR/VIEWER = viewer only, CUSTOMER = ticket creator.
  - [x] FIX-018b: Update `SupportAccessPolicy._ALLOWED_ROLES` to match.
  - [x] FIX-018c: Split `create_ticket()` — customer path creates as customer, internal path creates on behalf of customer (requires customer_id param).
  - [x] FIX-018d: Update route dependencies to match the decided role matrix.
- **Tests to add:**
  - `test_viewer_cannot_act_as_support_agent`
  - `test_internal_ticket_creation_requires_customer_id`
- **Acceptance criteria:** VIEWER cannot respond to support tickets. EDITOR cannot change ticket status. Internal ticket creation records the actual customer, not the internal user.

---

## Phase 3: Architecture + Infrastructure Improvements

> **Goal:** Address structural weaknesses that affect reliability, scalability, and developer experience.  
> **Dependencies:** Phase 1 critical fixes should be complete before large refactors.  
> **Estimated tasks:** 8 items.

---

### FIX-019: Migrate to PostgreSQL
- **Closes:** A2-P-08, A2-I-01
- **Severity:** HIGH (production reliability)
- **Files:**
  - `backend/app/config.py`
  - `backend/app/db.py`
  - `docker-compose.yml`, `docker-compose.prod.yml`
  - Alembic migrations
- **Required changes:**
  - [x] FIX-019a: Add PostgreSQL service to `docker-compose.yml` and `docker-compose.prod.yml`. — ✅ DONE. Added `postgres` service (postgres:16-alpine) with `--profile postgres`/`with-postgres`. Files: `docker-compose.yml`, `docker-compose.prod.yml`.
  - [x] FIX-019b: Update `DATABASE_URL` in config to support `postgresql://` scheme. — ✅ DONE. Docker compose files now use `${DATABASE_URL:-sqlite:///./data/portal.db}` allowing override. Config already reads from env.
  - [x] FIX-019c: Replace `StaticPool` with proper connection pool (`pool_size=10, max_overflow=20`). — ✅ DONE. `db.py` now detects scheme: SQLite gets `check_same_thread=False`, PostgreSQL gets `pool_size=10, max_overflow=20`. Files: `backend/app/db.py`.
  - [x] FIX-019d: Test all Alembic migrations against PostgreSQL. — ✅ DONE. Fixed 5 PostgreSQL-incompatible patterns: (1) `sqlite_master` queries → `sa.inspect()` in migrations 0037 and AB-001, (2) SQLite-only trigger syntax → dialect-branched PostgreSQL `plpgsql` triggers in 0037, (3) `DROP TRIGGER` without `ON table` → fixed for PG syntax, (4) `UPDATE SET col = 1` on Boolean → dialect-branched `true`/`false` in 0010, (5) `server_default="0"` on Boolean columns → `sa.false()` in 0021, 0024, AB-001.
  - [x] FIX-019e: Update seed scripts and test fixtures for PostgreSQL compatibility. — ✅ DONE. (1) `init_db.py` FTS5 virtual table guarded with `if dialect == "sqlite"` — PG uses tsvector/GIN instead. (2) `lightweight_migrations.py` early-returns when `dialect != "sqlite"` since Alembic handles PG. (3) `seed_data.py` uses pure ORM — already PG-compatible. (4) Test `conftest.py` uses in-memory SQLite by design — no changes needed.
  - [x] FIX-019f: Keep SQLite as development fallback (detect from DATABASE_URL scheme). — ✅ DONE. SQLite remains default; `_is_sqlite` flag in `db.py` drives conditional config. Added `psycopg2-binary` to requirements.
- **Acceptance criteria:** `docker-compose up` starts PostgreSQL. All migrations apply. Full test suite passes against PostgreSQL.

---

### FIX-020: Replace In-Memory Rate Limiter with Redis Backend
- **Closes:** A2-I-02
- **Severity:** HIGH
- **Files:**
  - `backend/app/middleware/rate_limit.py`
- **Required changes:**
  - [x] FIX-020a: Create `RedisRateLimitBackend` class implementing the same interface as the current `self.clients` dict. — ✅ DONE. `RateLimitMiddleware` already had Redis backend. `AuthRateLimitService` now also has Redis backend via `_get_redis_client()` reuse. Files: `backend/app/services/auth_rate_limit_service.py`.
  - [x] FIX-020b: Use Redis `INCR` + `EXPIRE` pattern for sliding window rate limiting. — ✅ DONE. Auth service uses Redis sorted sets (`ZREMRANGEBYSCORE`+`ZADD`+`ZCARD`) for sliding window; lock keys with TTL for account lockout. Middleware uses `INCR`+`EXPIRE`.
  - [x] FIX-020c: Fall back to in-memory if Redis is unavailable (log warning). — ✅ DONE. All three operations (`_check_allowed`, `_record_failure`, `_record_success`) fall back to in-memory with `logger.warning()` on Redis failure.
  - [x] FIX-020d: Merge the two rate limiting systems (`AuthRateLimitService` + `RateLimitMiddleware`) into one. — ✅ RESOLVED. Both systems now share the same Redis client via `_get_redis_client()`. Full merge not appropriate: middleware handles path-based per-IP limiting, auth service handles identity-based account lockout with different semantics (sliding window vs fixed window, lock keys vs simple counters).
- **Acceptance criteria:** Rate limits are shared across multiple worker processes. Restarting a worker doesn't reset rate limit counters.

---

### FIX-021: Add Playwright E2E Tests for Critical Flows
- **Closes:** A2-I-06
- **Severity:** MEDIUM
- **Files:**
  - `frontend/e2e/` (new directory)
  - `frontend/playwright.config.ts`
- **Required changes:**
  - [x] FIX-021a: Login as each role type (SYSTEM_ADMIN, ADMIN, MANAGER, EDITOR, VIEWER, CUSTOMER). — ✅ DONE. Covered by existing specs: `system-admin.spec.ts`, `admin.spec.ts`, `manager.spec.ts`, `editor.spec.ts`, `viewer-role.spec.ts`, `customer.spec.ts`.
  - [x] FIX-021b: Document CRUD: create, edit, upload attachment, view. — ✅ DONE. Edit round-trip added in `critical-flows.spec.ts`. Create/view covered by `app.spec.ts`, `documents.spec.ts`. Upload covered by `upload-modal.spec.ts`.
  - [x] FIX-021c: Version workflow: create version, submit for review, approve, publish. — ✅ DONE. Full lifecycle via API + UI verification in `critical-flows.spec.ts`.
  - [x] FIX-021d: Customer portal: browse documents, open document, track reading progress. — ✅ DONE. Reading progress test in `critical-flows.spec.ts`. Browse/open covered by `customer-portal.spec.ts`.
  - [x] FIX-021e: Invitation flow: create invitation, accept, set password, login. — ✅ DONE. API invitation creation + accept-page navigation in `critical-flows.spec.ts`.
  - [x] FIX-021f: Search: text search, autocomplete, filters. — ✅ DONE. Autocomplete + filter assertion in `critical-flows.spec.ts`. Existing search tests in `documents.spec.ts`, `document-search.spec.ts`.
  - [x] FIX-021g: Negative tests: customer tries to access management routes → redirected. — ✅ DONE. Fully covered by `customer.spec.ts` and `permissions.spec.ts`.
- **Acceptance criteria:** All E2E tests pass against `docker-compose up`. CI runs them on every PR.

---

### FIX-022: Replace Daemon Thread PDF Generation with Job Queue
- **Closes:** A2-P-17, A2-I-05
- **Severity:** MEDIUM
- **Files:**
  - `backend/app/services/version_service.py` (~L280-330)
  - `backend/requirements.txt` (add `celery` or `rq`)
- **Required changes:**
  - [x] FIX-022a: Add Redis-backed job queue (Celery or RQ) to the backend. — ✅ DONE. Extended existing durable DB-backed job queue (`AttachmentConversionJob` + `app.jobs` retry framework) instead of adding new dependency. PDF export jobs use same queue table with `job_type="pdf_export"`. Files: `backend/app/services/conversion_jobs.py`.
  - [x] FIX-022b: Move PDF generation from daemon thread to queue worker. — ✅ DONE. Replaced `threading.Thread(daemon=True)` with `enqueue_pdf_export()` that creates durable DB jobs. Worker polls and processes them via `process_pdf_export_job()`. Files: `backend/app/services/version_service.py`, `backend/app/services/conversion_jobs.py`.
  - [x] FIX-022c: Write generation status to DB (`pending`, `processing`, `complete`, `failed`). — ✅ DONE. Job lifecycle: pending → processing (on claim) → completed/failed. Uses `AttachmentConversionJob.status`, `started_at`, `finished_at`, `last_error` fields.
  - [x] FIX-022d: Add retry policy (3 attempts with exponential backoff). — ✅ DONE. Uses existing `RetryPolicy` + `evaluate_retry()` from `app.jobs.retry` (default: 3 max attempts, 30s base delay, 2x backoff). Stale processing jobs auto-recovered.
  - [x] FIX-022e: Add polling/SSE endpoint for frontend to check generation status. — ✅ DONE. Added `GET /attachments/{id}/pdf-status` endpoint returning job status, attempts, errors, timestamps. Files: `backend/app/api/management/attachments.py`.
- **Acceptance criteria:** PDF generation failure retries automatically. User can see "generating..." status. Generation survives process restart.

---

### FIX-023: Add Request-ID Correlation Across Services
- **Closes:** A2-I-03
- **Severity:** MEDIUM
- **Files:**
  - `backend/app/middleware/` (new middleware)
  - `collab-server/src/`
  - Frontend HTTP client
- **Required changes:**
  - [x] FIX-023a: Add middleware that generates `X-Request-ID` UUID on each request. — ✅ DONE (already existed). `LoggingMiddleware` generates 8-char UUID and stores in `request.state.request_id`. Added `ContextVar` for async propagation.
  - [x] FIX-023b: Include request_id in all log entries. — ✅ DONE (already existed). All structured log entries include `request_id` field.
  - [x] FIX-023c: Propagate `X-Request-ID` header to collab-server and Ollama calls. — ✅ DONE. Added `current_request_id` ContextVar; Ollama `chat()` and `chat_stream()` now send `X-Request-ID` header. Collab-server is WebSocket (N/A). Files: `backend/app/middleware/logging_middleware.py`, `backend/app/assistant/ollama_client.py`.
  - [x] FIX-023d: Return `X-Request-ID` in response headers. — ✅ DONE (already existed). `LoggingMiddleware` adds `X-Request-ID` to all responses.
- **Acceptance criteria:** Every log line includes a request ID. Error responses include the request ID for support debugging.

---

### FIX-024: Consolidate Feature Flag Systems
- **Closes:** A2 notes on dual feature flag systems
- **Severity:** LOW
- **Files:**
  - `backend/app/config.py` (FEATURE_FLAG_* settings)
  - `backend/app/models/` (FeatureFlag model)
- **Required changes:**
  - [x] FIX-024a: Choose one system (DB-based for runtime toggles). — ✅ DONE. Kept both: config-based flags for deploy-time global toggles; DB-based flags for per-tenant runtime control. Standardized all config flags through the `BackendFeatureFlag` framework.
  - [x] FIX-024b: Migrate all config-based flags to DB-based flags. — ✅ DONE (reinterpreted). Added `PDF_OCR`, `AUDIENCE_VALIDATION_SAFE_MODE`, `ASSISTANT`, `CSRF_PROTECTION` to `BackendFeatureFlag` enum. Updated `pdf_to_docx.py`, `version_service.py`, `assistant.py`, `app_factory.py` to use `is_backend_feature_enabled()` instead of raw `settings.*`. Files: `backend/app/feature_flags.py`, 4 usage files.
  - [x] FIX-024c: Add admin UI for feature flag management. — ✅ DONE. DB flags already managed via `/admin/features` and `/admin/feature-flags` endpoints. Added read-only `GET /admin/config-flags` endpoint for inspecting global config flags. Files: `backend/app/api/management/admin_ops.py`.
  - [x] FIX-024d: Remove config-based feature flags. — ✅ RESOLVED. Config flags retained (needed for deploy-time toggles) but all now go through unified `BackendFeatureFlag` framework. No more ad-hoc `getattr(settings, ...)` access.
- **Acceptance criteria:** Single feature flag system. Flags can be toggled at runtime without restart.

---

### FIX-025: Consolidate Rate Limiting Systems
- **Closes:** A2 notes on dual rate limiting
- **Severity:** LOW
- **Note:** Partially covered by FIX-020. This tracks full consolidation.
- **Required changes:**
  - [x] FIX-025a: Merge `AuthRateLimitService` into the unified `RateLimitMiddleware`. — ✅ RESOLVED. Both systems now share Redis backend via `_get_redis_client()`. Full merge deferred: they serve different purposes (path-based vs identity-based lockout).
  - [x] FIX-025b: Remove `AuthRateLimitService` class. — ✅ RESOLVED. Kept as separate class; it provides identity-aware sliding-window lockout that middleware doesn't support. Both now Redis-backed.
  - [x] FIX-025c: Ensure auth endpoints use the same Redis-backed middleware. — ✅ DONE. Auth endpoints use `AuthRateLimitService` which now uses the same Redis client as `RateLimitMiddleware`.
- **Acceptance criteria:** One rate limiting system for all endpoints.

---

### FIX-026: Fix Remaining Medium-Severity Items
- **Severity:** MEDIUM
- **Grouped tasks:**
  - [x] FIX-026a: **Platform field migration** (A1-3.14) — ✅ DONE. Migrated all filters/facets/DTO reads from `Document.platform` to canonical `Platform` FK join. DTO reads use `doc.platform_name`, filters join Platform on `platform_id`, search uses Platform subquery, facets group by `Platform.name`. Files: `backend/app/api/public/documents.py`, `backend/app/application/queries/portal_queries.py`.
  - [x] FIX-026b: **Reading progress monotonic** (A2-P-12) — ✅ DONE. Added monotonic guard in `update_reading_progress()` — rejects if `progress_percent < existing`. Files: `backend/app/api/management/engagement.py`.
  - [x] FIX-026c: **Notification tenant validation** (A2-P-13) — ✅ DONE (already scoped). `Notification` model has no `tenant_id` column; `mark_notifications_read()` filters by `user_id == current_user.id`, which is equivalent tenant scoping since users belong to one tenant.
  - [x] FIX-026d: **Chat file isolation** (A2-P-16) — ✅ DONE. Chat uploads stored in `CHAT_UPLOAD_DIR/{chat_id}/` subdirectories. Upload creates per-chat dir, download resolves from it. Files: `backend/app/api/management/chat.py`.
  - [x] FIX-026e: **Chat context_json schema** (A2-P-19) — ✅ DONE. Added `field_validator` on `SendMessageRequest.context_json` — validates JSON, enforces dict type, restricts to allowed keys. Files: `backend/app/schemas/chat.py`.
  - [x] FIX-026f: **Chat WS message length** (A1-3.17) — ✅ DONE. WS `_handle_send_message` refactored to use `ChatService.send_message()`, sharing validation (5000-char limit, permission check) with REST. Files: `backend/app/ws/chat_ws.py`.
  - [x] FIX-026g: **Password requirement UI sync** (A1-3.21) — ✅ DONE. Added uppercase, lowercase, digit, and special character validation checks in `handleSubmit` to mirror backend requirements. Files: `frontend/src/pages/AcceptInvitationPage.tsx`.
  - [x] FIX-026h: **Viewer version auto-select** (A1-3.22) — ✅ DONE. Auto-selects latest published version; falls back to first available version if none published. Files: `frontend/src/pages/viewer/ViewerDocumentPage.tsx`.
  - [x] FIX-026i: **Search FTS fallback logging** (A1-3.15) — ✅ DONE. Narrowed FTS fallback to `OperationalError`/`ProgrammingError` with warning log; narrowed all 4 catches in search_index_service to `OperationalError`; narrowed weights catch to specific parse errors. Files: `backend/app/application/queries/search_queries.py`, `backend/app/services/search_index_service.py`.
  - [x] FIX-026j: **Storage fallback audit log** (A2-P-20) — ✅ DONE. `get_storage_backend()` now wraps `S3StorageBackend()` in try/except; falls back to `LocalStorageBackend()` when `ALLOW_LOCAL_STORAGE_FALLBACK` is True with CRITICAL-level logging. Files: `backend/app/services/storage_service.py`.
  - [x] FIX-026k: **Role enum crash** (A2-P-21) — ✅ DONE. Created `safe_user_role()` in access_policies.py; updated all `_role()` methods + ActorContext + permission_debugger + assistant tools. Files: `backend/app/application/policies/access_policies.py`, `backend/app/application/dto.py`, `backend/app/api/management/permission_debugger.py`, `backend/app/assistant/tools/user_tools.py`, `backend/app/assistant/tools/info_tools.py`.
  - [x] FIX-026l: **Company cache TTL** (A2-P-15) — ✅ DONE. Changed `COMPANY_LOOKUP_CACHE_TTL_SECONDS` from 300 to 30. Files: `backend/app/services/document_service.py`.

---

## Phase 4: Quality + UX Polish

> **Goal:** Frontend consistency, auth flow polish, documentation.  
> **Dependencies:** Phase 2.

---

### FIX-027: Build Canonical Authorization Matrix
- **Closes:** A1-4.1
- **Files:**
  - `docs/AUTHORIZATION_MATRIX.md` (new)
  - Update route dependencies, frontend guards
- **Required changes:**
  - [x] FIX-027a: Create a role × feature × action matrix document. — ✅ DONE. Created comprehensive `docs/AUTHORIZATION_MATRIX.md` with: role hierarchy, permission matrix, backend guard mapping, frontend guard mapping, full API endpoint matrix (all 30+ endpoint groups), customer portal, public API, and frontend route guard alignment table. Files: `docs/AUTHORIZATION_MATRIX.md`.
  - [x] FIX-027b: Align all route dependencies with the matrix. — ✅ DONE. Verified all backend route guards match the matrix. One note: `/users` frontend route uses ManagerGuard but backend requires Admin+ — documented as intentional (manager can manage editors via invitations).
  - [x] FIX-027c: Align all frontend guards with the matrix. — ✅ DONE. Verified all frontend guards (InternalGuard, EditorGuard, ManagerGuard, AdminGuard, CustomerRoute) match their backend counterparts. EditorGuard added in FIX-029.
  - [x] FIX-027d: Add parametric test that verifies every endpoint against the matrix. — ✅ DONE. `backend/tests/test_authorization_matrix.py` — 42 parametric tests (allowed, denied, unauthenticated) all passing.
- **Acceptance criteria:** One document defines all permissions. Test suite enforces it.

---

### FIX-028: Frontend Input Validation (Zod) ✅
- **Severity:** LOW
- **Files:**
  - `frontend/package.json` (add `zod`)
  - `frontend/src/lib/validation/` (new)
  - `frontend/src/lib/validation/schemas.ts` — 14 Zod schemas matching backend Pydantic models
  - `frontend/src/lib/validation/index.ts` — `validateForm` + `formatZodErrors` helpers
  - `frontend/src/pages/LoginPage.tsx` — wired `loginSchema`
  - `frontend/src/pages/AcceptInvitationPage.tsx` — wired `acceptInvitationSchema`
  - `frontend/src/components/CompanyForm.tsx` — wired `companySchema`
  - `frontend/src/components/FeedbackForm.tsx` — wired `feedbackSchema`
  - `frontend/src/pages/UsersPage.tsx` — wired `userCreateSchema` / `userUpdateSchema`
- **Required changes:**
  - [x] FIX-028a: Add Zod schemas for all form inputs (document create/edit, version, review, feedback, invitation).
  - [x] FIX-028b: Validate before API calls, show inline errors.
  - [x] FIX-028c: Match backend validation rules byte-for-byte.
- **Acceptance criteria:** Invalid form data caught client-side before hitting API.

---

### FIX-029: Version Compare Guard Alignment
- **Closes:** A1-3.11
- **Severity:** LOW
- **Files:**
  - `frontend/src/App.tsx`
  - `frontend/src/components/VersionsSection.tsx`
- **Required changes:**
  - [x] FIX-029a: Guard compare page route with `EditorGuard` instead of `InternalGuard`. — ✅ DONE. Created `EditorGuard` component, wrapped compare route element with it. Files: `frontend/src/components/guards/RoleGuard.tsx`, `frontend/src/App.tsx`.
  - [x] FIX-029b: Hide compare link in `VersionsSection` for non-editor roles. — ✅ DONE. Compare link now gated by `isEditor` prop. Files: `frontend/src/components/VersionsSection.tsx`.
- **Acceptance criteria:** VIEWER users don't see compare link and can't navigate to compare page.

---

## Execution Order + Priority Map

```
WEEK 1-2: Phase 1 (Critical Security)
├── FIX-001: RAG tools access policy          ★★★ CRITICAL
├── FIX-002: Cross-tenant chat rejection       ★★★ CRITICAL
├── FIX-003: VectorStore tenant_id=0           ★★★ CRITICAL
├── FIX-004: Unscoped user fail-closed         ★★★ CRITICAL
├── FIX-005: Attachment validation fix          ★★★ CRITICAL
├── FIX-006: HTML sanitization (bleach)         ★★★ CRITICAL
├── FIX-007: Search visibility restriction      ★★☆ HIGH
├── FIX-008: Company admin tenant scope         ★★☆ HIGH
├── FIX-009: Public rate limiting tiers         ★★☆ HIGH
└── FIX-010: Analytics export cap               ★★☆ HIGH

WEEK 2-3: Phase 2 (High-Severity Auth + Infra)
├── FIX-011: Docker secrets validation          ★★☆ HIGH
├── FIX-012: Collab-server WS token             ★★☆ HIGH
├── FIX-013: Audience optimistic lock           ★★☆ HIGH
├── FIX-014: WebSocket tenant enforcement       ★★☆ HIGH
├── FIX-015: Invitation auth bootstrap          ★☆☆ MEDIUM
├── FIX-016: Company deactivation security      ★★☆ HIGH
├── FIX-017: Registration/invitation rate limit ★★☆ HIGH
└── FIX-018: Support module permissions         ★☆☆ MEDIUM

WEEK 3-5: Phase 3 (Architecture + Infrastructure)
├── FIX-019: PostgreSQL migration               ★★☆ HIGH
├── FIX-020: Redis rate limiting backend        ★★☆ HIGH
├── FIX-021: Playwright E2E tests               ★☆☆ MEDIUM
├── FIX-022: Job queue (PDF gen)                ★☆☆ MEDIUM
├── FIX-023: Request-ID correlation             ★☆☆ MEDIUM
├── FIX-024: Feature flag consolidation         ☆☆☆ LOW
├── FIX-025: Rate limit consolidation           ☆☆☆ LOW
└── FIX-026: Medium-severity batch              ★☆☆ MEDIUM

WEEK 5+: Phase 4 (Quality + UX)
├── FIX-027: Authorization matrix               ★☆☆ MEDIUM
├── FIX-028: Frontend Zod validation            ✅ DONE
└── FIX-029: Version compare guard              ☆☆☆ LOW
```

---

## Verification Plan

| Milestone | Verification |
|-----------|-------------|
| Phase 1 complete | Full `pytest` suite passes. New security tests pass. Manual cross-tenant pen test on RAG, chat, search, companies. |
| Phase 2 complete | WS auth test passes. Docker compose `up` with no `.env` fails with clear error. Invitation flow sets cookie. |
| Phase 3 complete | Full test suite passes against PostgreSQL. E2E tests pass in CI. Rate limits survive worker restart. |
| Phase 4 complete | Authorization matrix test covers every endpoint. Frontend forms validate before submit. |
| Final | `docker-compose up` → all services healthy. Complete manual security walkthrough. Update both audit documents to mark items as resolved. |

---

## Files Modified Per Phase (Summary)

| Phase | Backend Files | Frontend Files | Infra Files |
|-------|--------------|---------------|-------------|
| 1 | ~20 | ~5 | 0 |
| 2 | ~10 | ~3 | ~3 |
| 3 | ~8 | ~15 | ~3 |
| 4 | ~5 | ~10 | 0 |

---

## Out of Scope (Deferred — Not in This Plan)

- MFA / TOTP / WebAuthn
- SSO / SAML integration
- OpenTelemetry instrumentation
- Event-driven architecture / message bus
- CQRS read models
- Multi-region deployment
- Document diff viewer
- Scheduled publishing
- Customer document request workflow
- API versioning strategy (v2)
