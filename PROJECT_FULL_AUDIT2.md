# Project Full Audit — Deep End-to-End Review

**Date:** 2026-03-21  
**Scope:** Full-stack audit — backend, frontend, infrastructure, collab-server, CI/CD  
**Branch:** `audit` (based on `main` + security remediation phases 1-7)

---

## 1. Executive Summary

### System Overview
Multi-tenant documentation management platform: FastAPI backend, React/TypeScript frontend, Node.js collaboration server, SQLite database, Ollama-powered AI assistant, ChromaDB vector store. Docker Compose orchestration for 4+ services.

### Main Strengths
- **Solid auth architecture** — JWT + httpOnly cookie session, in-memory token storage (AD-004), token rotation on refresh, concurrent session limits, automatic session revocation
- **Comprehensive RBAC** — 6-tier role system (SYSTEM_ADMIN → CUSTOMER) with backend-driven permissions pushed to frontend via `/auth/me`
- **Strong tenant isolation pattern** — TenantContext dependency, middleware-level context propagation, service-layer tenant scoping on most queries
- **Audit logging with HMAC signatures** — Tamper-evident audit trail for sensitive operations
- **Optimistic concurrency** — `row_version` / ETag support on documents and versions
- **Well-structured codebase** — Clear separation into policies, commands, services, repositories, domain layer
- **Review/publish workflow** — Audience snapshots, drift detection, stale-company checks at publish time

### Main Risks
- **Cross-tenant leaks in chat, AI tools, and analytics** — Tenant boundary enforcement is inconsistent across newer features (chat, RAG tools, analytics export)
- **Race conditions in publish/review pipeline** — Audience drift between approval and publish not locked; optimistic concurrency not applied to audience state
- **Public attack surface lacks rate limiting** — Public search, registration, and viewer endpoints have no throughput caps
- **AI assistant tools bypass document access policies** — SummarizeDocumentTool and AskAboutDocumentTool do not call DocumentAccessPolicy before retrieving content
- **SQLite in production** — Single-writer, no MVCC, no replication, file-lock contention under concurrent load
- **HTML sanitization is regex-based** — Bypassable via encoding tricks; no DOMPurify on frontend

### Most Urgent Issues
1. RAG tools bypass document access checks (CUSTOMER can summarize INTERNAL docs)
2. Chat service allows cross-tenant direct messaging via internal user bridge
3. Public endpoints lack rate limiting (anonymous DoS vector)
4. Analytics CSV export unbounded (memory exhaustion DoS)
5. VectorStore defaults tenant_id to 0 instead of rejecting None

### Overall Verdict
The core platform (auth, documents, versions, reviews) is **~75% production-ready**. Security remediation phases 1-7 addressed the most critical issues from the first audit. However, newer features (chat, AI assistant, analytics, experimentation) have **weaker tenant isolation and access control**. The system is suitable for staging/beta with a trusted user base but NOT for adversarial production traffic without addressing the critical items below.

---

## 2. Critical Problems

### C-NEW-1: RAG Tools Bypass Document Access Policies
- **Severity:** Critical
- **Area:** Backend / Security / AI Assistant
- **Affected files:** `backend/app/assistant/tools/rag_tools.py`, `backend/app/assistant/engine.py`
- **Description:** `SummarizeDocumentTool` and `AskAboutDocumentTool` fetch document content without calling `DocumentAccessPolicy.can_view_document()`. They only perform a weak tenant_id comparison that passes when either `tenant_id` is None. `SemanticSearchTool` declares `required_role = "EDITOR"` but enforcement depends on the tool executor actually checking this field.
- **Why it is a problem:** A CUSTOMER user can call `ask_about_document(document_id=<internal_doc_id>)` and receive AI-generated answers about internal/restricted documents. The tenant check fails open (`if tenant_id and doc.tenant_id and ...` — both None → passes).
- **Example scenario:** Customer sends "Summarize document 42" to AI assistant. Document 42 is INTERNAL visibility, belongs to another tenant. Tool loads content, sends it to Ollama, and returns a summary to the customer.
- **Recommended fix:** (a) Add `DocumentAccessPolicy.can_view_document(user, document)` check in every RAG tool before loading content. (b) Enforce `required_role` in the tool execution loop in `engine.py`. (c) Replace `if tenant_id and doc.tenant_id` with `if doc.tenant_id != tenant_id: reject`.

### C-NEW-2: Chat Cross-Tenant Isolation Bypass
- **Severity:** Critical
- **Area:** Backend / Security / Multi-Tenancy
- **Affected files:** `backend/app/services/chat_service.py` (L38-55, L97-108, L523-535)
- **Description:** `create_direct_chat()` allows cross-tenant chats if at least one user is "internal staff." `_get_chat_with_permission()` validates participation but not tenant boundary. `create_document_chat()` does not verify the creator has access to the referenced document.
- **Why it is a problem:** Internal user in Tenant A can create a direct chat with a customer in Tenant B. The customer then has a communication channel that crosses tenant boundaries. Document chats can reference documents the creator cannot access.
- **Example scenario:** Internal editor at "Company Alpha" creates direct chat with customer at "Company Beta." Customer Beta sees messages from Alpha's internal team, potentially exposing operational details.
- **Recommended fix:** (a) Reject all cross-tenant direct chats unconditionally. (b) Add `DocumentAccessPolicy.can_view_document()` before creating document chats. (c) Add `Chat.tenant_id` validation in `_get_chat_with_permission()`.

### C-NEW-3: VectorStore Defaults tenant_id to 0
- **Severity:** Critical
- **Area:** Backend / Security / AI
- **Affected files:** `backend/app/assistant/rag/vector_store.py` (~L70-90)
- **Description:** When indexing or querying ChromaDB, if `tenant_id` is None, the code defaults it to `0`. This means documents without a tenant get the synthetic tenant 0, and queries without a tenant match tenant 0 — creating a hidden cross-tenant bucket.
- **Why it is a problem:** If any document is indexed with `tenant_id=None` (now 0), it becomes queryable by any user whose tenant_id is also None/0.
- **Example scenario:** SYSTEM_ADMIN (no tenant) indexes a document. Later, any SYSTEM_ADMIN query — or any user with broken tenant context — retrieves that document regardless of true ownership.
- **Recommended fix:** Reject None tenant_id at index and query time. Require explicit tenant_id on all operations. If SYSTEM_ADMIN needs cross-tenant access, use a separate flag.

### C-NEW-4: Public Endpoints Have No Rate Limiting
- **Severity:** Critical
- **Area:** Backend / Security / Infrastructure
- **Affected files:** `backend/app/api/public/documents.py`, `backend/app/api/viewer/documents.py`, `backend/app/middleware/rate_limit.py`
- **Description:** The `RateLimitMiddleware` applies 10 req/min to auth paths and 100 req/min to authenticated paths. Public/viewer paths (`/api/v1/public/*`, `/api/v1/viewer/*`) are accessible without authentication, and anonymous requests share the same per-IP 100 req/min pool. Public search has no query length limit.
- **Why it is a problem:** Anonymous users can send unbounded requests, exhausting server resources. Search queries with no max_length can trigger expensive full-text scans.
- **Example scenario:** Attacker sends 10,000 search requests per minute from rotating IPs with 10KB query strings, causing memory pressure and DB locks.
- **Recommended fix:** (a) Lower rate limit for unauthenticated requests (30 req/min). (b) Add `max_length=500` on query parameters. (c) Add separate rate tier for `/public` and `/viewer` prefixes.

### C-NEW-5: Analytics CSV Export Unbounded
- **Severity:** Critical
- **Area:** Backend / Security / DoS
- **Affected files:** `backend/app/api/management/analytics.py` (~L310-340)
- **Description:** `GET /analytics/export/csv` accepts arbitrary date ranges with no maximum span, no pagination, and no size cap. The endpoint streams all matching records into memory before generating CSV.
- **Why it is a problem:** A manager can request 10 years of analytics, generating a CSV that exhausts server memory.
- **Example scenario:** `GET /analytics/export/csv?report=engagement&date_from=2016-01-01&date_to=2026-01-01` → backend loads millions of rows → OOM kill.
- **Recommended fix:** (a) Cap date range to 90 days. (b) Use streaming CSV generation (`StreamingResponse`). (c) Add per-user rate limit on exports.

### C-NEW-6: Audience Drift Race Condition Between Approval and Publish
- **Severity:** Critical
- **Area:** Backend / Data Integrity
- **Affected files:** `backend/app/application/commands/review_commands.py` (L89-180), `backend/app/services/version_service.py` (L509-590)
- **Description:** At review approval time, `_resolve_audience_drift()` detects stale companies but does NOT block approval. At publish time, stale companies are blocked if `enforce_company_audience=true`. Between approval and publish, there's no optimistic lock on the audience state — another request can modify `assigned_companies` without detection.
- **Why it is a problem:** Two reviewers can approve the same version concurrently with different audience snapshots. The publish then applies whichever snapshot was written last, with no auditing of which took effect.
- **Example scenario:** Reviewer A approves with companies [1,2,3]. Simultaneously, admin removes company 3 and reviewer B approves with [1,2]. Version publishes with [1,2] — reviewer A's approval is silently invalidated.
- **Recommended fix:** (a) Add `row_version` check on document audience at approval time. (b) Reject approval if audience changed since submission. (c) Add pessimistic lock during publish.

---

## 3. Problems

### P-01: Demo Credentials Hardcoded in Frontend
- **Severity:** High
- **Category:** Security
- **Affected files:** `frontend/src/pages/LoginPage.tsx` (L337-379), `backend/seed_data.py`
- **Description:** Login page renders demo credential buttons with passwords like `sysadmin123`, `admin123`. Protected by `import.meta.env.DEV` check.
- **Expected behavior:** Demo credentials never ship in production builds.
- **Current behavior:** If build misconfigures `DEV=true`, credentials render in production.
- **Recommendation:** Move demo credential UI to a separate component loaded only via dynamic import in dev builds. Remove credentials from seed_data in production images.

### P-02: CSRF Middleware Bypassed in Non-Production Environments
- **Severity:** High
- **Category:** Security
- **Affected files:** `backend/app/middleware/csrf.py` (~L84-88)
- **Description:** When `APP_ENV != "production"`, requests with no `Origin` or `Referer` header are accepted. Staging environments typically run with `APP_ENV=staging`.
- **Expected behavior:** CSRF validation should be enforced in all publicly-accessible environments.
- **Current behavior:** Staging/QA environments vulnerable to CSRF from any origin.
- **Recommendation:** Only bypass CSRF for `APP_ENV == "testing"` (pytest). Enforce in all other environments.

### P-03: Rate Limiter Trusts X-Forwarded-For Without Proxy Validation
- **Severity:** High
- **Category:** Security
- **Affected files:** `backend/app/middleware/rate_limit.py` (L33-38)
- **Description:** `_get_client_ip()` reads X-Forwarded-For without validating it came from a trusted proxy.
- **Expected behavior:** Only accept forwarded headers from known proxy IPs.
- **Current behavior:** Attacker can spoof IP, defeating all rate limiting.
- **Recommendation:** Add `TRUSTED_PROXIES` setting; only accept X-Forwarded-For from listed IPs.

### P-04: Registration Endpoint Has No Rate Limiting
- **Severity:** High
- **Category:** Security
- **Affected files:** `backend/app/api/management/auth.py`
- **Description:** `POST /auth/register` is public and has no rate limit.
- **Expected behavior:** Public registration should be rate limited to prevent automated account creation.
- **Current behavior:** Attacker can create unlimited accounts programmatically.
- **Recommendation:** Add 5 registrations/hour per IP.

### P-05: Invitation Endpoint Has No Rate Limiting
- **Severity:** High
- **Category:** Security
- **Affected files:** `backend/app/api/management/invitations.py` (L73)
- **Description:** `POST /invitations` accepts unlimited invitation creation per admin.
- **Expected behavior:** Rate limited to prevent invitation spam.
- **Current behavior:** Compromised admin account can send hundreds of invitations.
- **Recommendation:** Add 20 invitations/hour per user.

### P-06: HTML Sanitization Uses Regex Instead of Parser
- **Severity:** High
- **Category:** Security / XSS
- **Affected files:** `backend/app/utils/sanitization.py` (L14-47)
- **Description:** HTML sanitization relies on regex patterns that can be bypassed via UTF-8 encoding, nested tags, CSS injection, and alternate URI schemes. Frontend does not have DOMPurify or equivalent.
- **Expected behavior:** Use a proper HTML parser (bleach/lxml on backend, DOMPurify on frontend).
- **Current behavior:** Stored XSS possible via crafted document content or comments.
- **Recommendation:** Replace regex sanitization with `bleach.clean()` on backend. Add DOMPurify to frontend for all user-generated HTML rendering.

### P-07: Insecure Docker Compose Defaults
- **Severity:** High
- **Category:** Infrastructure / Security
- **Affected files:** `docker-compose.yml`, `docker-compose.prod.yml`
- **Description:** `SECRET_KEY` and `JWT_SECRET` have hardcoded fallback values in compose files. Redis exposed without authentication on dev compose. Environment variable fallbacks mean missing env vars silently use insecure defaults.
- **Expected behavior:** Missing secrets should cause startup failure, not default to insecure values.
- **Current behavior:** `docker-compose up` works without `.env` file but uses insecure keys.
- **Recommendation:** Remove default values; require explicit env vars. Add startup validation that rejects default keys.

### P-08: SQLite in Production — Single Writer / No Replication
- **Severity:** High
- **Category:** Architecture / Reliability
- **Affected files:** `backend/app/config.py`, `backend/app/db.py`
- **Description:** Production runs on SQLite with single-writer semantics. Concurrent writes trigger `SQLITE_BUSY` errors. No connection pooling beyond SQLAlchemy's `StaticPool`. No read replicas possible. Database is a single file with no streaming backup.
- **Expected behavior:** Production database should handle concurrent writes, support backups, and scale reads.
- **Current behavior:** Under moderate load (>10 concurrent writers), write failures will occur.
- **Recommendation:** Migrate to PostgreSQL. SQLite is acceptable for development and testing only.

### P-09: Collab-Server Token Extraction from WebSocket URL
- **Severity:** High
- **Category:** Security
- **Affected files:** `collab-server/src/auth.ts` (L39)
- **Description:** WebSocket connection extracts auth token from URL query parameter (`?token=...`). Tokens in URLs leak into server logs, browser history, CDN logs, and proxy caches.
- **Expected behavior:** Token sent via first WebSocket message or `Sec-WebSocket-Protocol` header.
- **Current behavior:** H-21 annotation exists acknowledging this; not yet migrated.
- **Recommendation:** Implement the H-21 fix: accept token in first WS message only, reject query-param tokens.

### P-10: @Mention Silently Skips Unauthorized Documents
- **Severity:** Medium
- **Category:** Backend / UX / Security
- **Affected files:** `backend/app/assistant/engine.py` (L376-415)
- **Description:** When a user @mentions a document they can't access, the engine logs a warning and silently continues without injecting the content or notifying the user.
- **Expected behavior:** Either reject the entire request or inform the user that specific @mentions were denied.
- **Current behavior:** User gets no feedback — they don't know their @mention was blocked, and might think the AI just ignored it.
- **Recommendation:** Return per-mention access status in the response metadata.

### P-11: Support Ticket Tenant Scoping Fails When tenant_id is None
- **Severity:** Medium
- **Category:** Backend / Multi-Tenancy
- **Affected files:** `backend/app/services/support_service.py` (~L56-80)
- **Description:** `list_tickets()` filters by `SupportTicket.tenant_id == current_user.tenant_id`. If `current_user.tenant_id` is None (possible for internal staff without explicit tenant assignment), the SQL filter becomes `WHERE tenant_id IS NULL`, which may match no tickets or match incorrectly.
- **Expected behavior:** Internal staff without tenant see only tickets they're explicitly assigned to.
- **Current behavior:** May silently return empty results or cross-tenant matches.
- **Recommendation:** Handle `tenant_id=None` explicitly: if SYSTEM_ADMIN, show all; otherwise, show assigned tickets only.

### P-12: Reading Progress Allows Non-Monotonic Updates
- **Severity:** Medium
- **Category:** Backend / Business Logic
- **Affected files:** `backend/app/api/management/engagement.py` (~L410-430)
- **Description:** `update_reading_progress()` validates 0-100 range but allows progress to decrease (e.g., from 80% to 30%).
- **Expected behavior:** Progress should only increase (monotonically).
- **Current behavior:** Any value 0-100 accepted, making analytics unreliable.
- **Recommendation:** Add `if data.progress_percent < existing.progress_percent: ignore or reject`.

### P-13: Notification Marking Lacks Tenant Validation
- **Severity:** Medium
- **Category:** Backend / Multi-Tenancy
- **Affected files:** `backend/app/api/management/notifications.py` (L57-90)
- **Description:** `mark_notifications_read()` filters by `user_id` but not `tenant_id`. If a notification references a cross-tenant resource (created by a bug elsewhere), the user can mark it as read.
- **Expected behavior:** Only mark notifications for resources within user's tenant.
- **Current behavior:** Minor — notifications are user-scoped, but no secondary tenant check.
- **Recommendation:** Add tenant validation on bulk mark-read operations.

### P-14: Document Chat Creation Skips Document Access Check
- **Severity:** Medium
- **Category:** Backend / Security
- **Affected files:** `backend/app/services/chat_service.py` (L97-108)
- **Description:** `create_document_chat()` queries the document by ID but does not verify the creator has `can_view_document` access.
- **Expected behavior:** Only users who can view a document should create document-scoped chats.
- **Current behavior:** Any authenticated user can create chats referencing any document ID.
- **Recommendation:** Add `DocumentAccessPolicy.can_view_document(creator, doc)` check.

### P-15: Company Lookup Snapshot Cache — 5-Minute Stale Window
- **Severity:** Medium
- **Category:** Backend / Data Integrity
- **Affected files:** `backend/app/services/document_service.py` (L146-156)
- **Description:** Company active/inactive status is cached for 300 seconds. If a company is deactivated, up to 5 minutes of requests will see it as active.
- **Expected behavior:** Company status changes should take effect within seconds.
- **Current behavior:** Stale cache allows operations on deactivated companies for up to 5 minutes.
- **Recommendation:** Reduce TTL to 30 seconds, or add immediate cache invalidation on company status change.

### P-16: Chat File Storage Has No Per-Chat Isolation
- **Severity:** Medium
- **Category:** Backend / Security
- **Affected files:** `backend/app/api/management/chat.py` (L245-265)
- **Description:** Chat file uploads are stored in a single flat directory (`CHAT_UPLOAD_DIR`). File download verifies chat participation but serves any file in the directory by filename.
- **Expected behavior:** Files should be stored in per-chat subdirectories to prevent cross-chat access.
- **Current behavior:** If UUID filename collision occurs (extremely unlikely but possible), files from different chats could be mixed.
- **Recommendation:** Store in `CHAT_UPLOAD_DIR / chat_id /` subdirectories. Verify file belongs to chat via message record lookup.

### P-17: PDF Export in Daemon Thread — No Retry, No Status
- **Severity:** Medium
- **Category:** Backend / Reliability
- **Affected files:** `backend/app/services/version_service.py` (~L280-330)
- **Description:** PDF generation runs in a daemon thread. If it fails, the exception is logged but not retried. The user receives no notification. If the process crashes, the work is lost.
- **Expected behavior:** Use a message queue (Celery/RQ) with retry policy and status tracking.
- **Current behavior:** Silent failure; user may wait indefinitely.
- **Recommendation:** Replace daemon thread with job queue. Write status to DB so frontend can poll.

### P-18: Magic Byte Validation Duplicated
- **Severity:** Low
- **Category:** Backend / Code Quality
- **Affected files:** `backend/app/services/attachment_service/upload.py` (L28, L57, L191)
- **Description:** File magic byte validation logic appears twice in the same file with slightly different implementations.
- **Expected behavior:** Single source of truth for file type validation.
- **Current behavior:** Potential divergence between two implementations.
- **Recommendation:** Consolidate into a single utility function.

### P-19: context_json in Chat Messages Has No Schema Validation
- **Severity:** Medium
- **Category:** Backend / Input Validation
- **Affected files:** `backend/app/services/chat_service.py` (L294)
- **Description:** `context_json` field on chat messages accepts arbitrary JSON without schema validation.
- **Expected behavior:** Validate against expected schema (document_id, comment_id, etc.).
- **Current behavior:** Attacker can store XSS payloads or misleading references in context_json.
- **Recommendation:** Add Pydantic schema validation for context_json contents.

### P-20: Storage Fallback Not Audit-Logged
- **Severity:** Low
- **Category:** Backend / Observability
- **Affected files:** `backend/app/services/attachment_service/upload.py` (L50-75)
- **Description:** When S3 upload fails and `ALLOW_LOCAL_STORAGE_FALLBACK=True`, the system silently falls back to local storage. This is only logged as a warning, not recorded in the audit trail.
- **Expected behavior:** All storage mode changes should be audited.
- **Current behavior:** Ops team has no way to know which files are on local disk vs S3.
- **Recommendation:** Add audit log entry when storage fallback occurs.

### P-21: Role Enum Coercion Crashes on Invalid DB Value
- **Severity:** Low
- **Category:** Backend / Error Handling
- **Affected files:** `backend/app/application/policies/access_policies.py` (L18-22)
- **Description:** `UserRole(user.role)` raises `ValueError` if `user.role` contains an invalid string.
- **Expected behavior:** Graceful error handling that denies access and logs.
- **Current behavior:** Uncaught exception → 500 Internal Server Error.
- **Recommendation:** Catch `ValueError` and return access denied.

---

## 4. Improvement Suggestions

### I-01: Migrate to PostgreSQL
- **Area:** Architecture / Database
- **Why it would help:** Eliminates single-writer bottleneck, enables proper connection pooling, row-level locking, streaming replication, and online backups.
- **Suggested direction:** Use Alembic to generate PostgreSQL-compatible migrations. Update `DATABASE_URL` in config. Test with `pg8000` or `psycopg2`.
- **Priority:** High (production blocker for any serious traffic)

### I-02: Replace In-Memory Rate Limiting with Redis
- **Area:** Infrastructure / Scalability
- **Why it would help:** Current rate limiter state is per-process. Multiple workers or containers don't share state, so limits are effectively multiplied.
- **Suggested direction:** Already have `REDIS_URL` config. Implement `RedisRateLimitBackend` as drop-in replacement for `self.clients` dict.
- **Priority:** High

### I-03: Add Request-ID Correlation Across Services
- **Area:** Observability
- **Why it would help:** Currently no way to trace a request from frontend → backend → collab-server → Ollama.
- **Suggested direction:** Generate UUID request-id in middleware, propagate via headers, include in all log entries.
- **Priority:** Medium

### I-04: Add OpenTelemetry Instrumentation
- **Area:** Observability
- **Why it would help:** Structured traces, metrics, and spans replace ad-hoc logging.
- **Suggested direction:** FastAPI has auto-instrumentation. Add spans to DB queries, external calls.
- **Priority:** Medium

### I-05: Implement Proper Job Queue
- **Area:** Architecture / Reliability
- **Why it would help:** PDF generation, email sending, analytics aggregation currently use daemon threads or fire-and-forget patterns.
- **Suggested direction:** Add Celery with Redis broker. Move background work to worker process.
- **Priority:** Medium

### I-06: Add Frontend E2E Tests
- **Area:** QA / Reliability
- **Why it would help:** Playwright config exists but no E2E test coverage found. Critical user flows (login, document CRUD, review workflow, customer portal) have no automated verification.
- **Suggested direction:** Write 10-15 core E2E tests covering happy paths for each user role.
- **Priority:** Medium

### I-07: Implement Proper API Versioning
- **Area:** Architecture / API
- **Why it would help:** Breaking changes to API will impact frontend and CLI consumers. Currently all endpoints share `/api/v1/` prefix with no actual versioning strategy.
- **Suggested direction:** Plan for v2 via content negotiation or URL prefix.
- **Priority:** Low

### I-08: Add useReducer for Complex Page State
- **Area:** Frontend / Code Quality
- **Why it would help:** Pages like DocumentDetailPage have 50+ `useState` declarations. Single state object with reducer is easier to reason about and test.
- **Suggested direction:** Extract page state into `useReducer` with typed actions.
- **Priority:** Low

---

## 5. Ideas

### Product Ideas
- **Document versioning diff viewer** — Side-by-side comparison of version content changes (similar to git diff)
- **Scheduled publish with notification** — Publish version at a future date/time with email notification to assigned companies
- **Customer document request workflow** — Allow customers to request new documents, tracked as support tickets
- **Reading analytics dashboard for customers** — Show which team members have read required documents

### Architecture Ideas
- **Event-driven architecture** — The outbox pattern exists but isn't connected to real consumers. Wire it to send domain events to a message bus for decoupled processing.
- **CQRS read models** — Heavy aggregate queries (analytics, document lists) could use pre-computed read models
- **Multi-region deployment** — Add read replica support for geo-distributed viewers

### Developer Experience Ideas
- **API documentation portal** — Use the OpenAPI spec to generate interactive docs with examples
- **Local development seed script** — Improve `seed_data.py` to create realistic multi-tenant test data
- **Monorepo build tool** — Use Turborepo or Nx for coordinated builds across frontend/backend/collab-server

---

## 6. Helpful Notes

### Architecture Patterns Found
- **Strangler wrappers** — `legacy_wrappers/` contains adapter classes for migrating old interfaces. Good pattern, but some wrappers now wrap only one call, adding overhead.
- **Policy-based authorization** — `DocumentAccessPolicy`, `ReviewPolicy`, `FeedbackAccessPolicy`, `InvitationPolicy`, `AnalyticsAccessPolicy` centralize access decisions. This is the strongest architectural element.
- **Command/query separation** — `application/commands/` and `application/queries/` exist but aren't fully adopted. Some services mix command and query logic.
- **Feature flags** — Both config-level (`FEATURE_FLAG_*` settings) and DB-level (`FeatureFlag` model) flags exist. Two parallel systems with no clear migration path.
- **Mixin API composition** — Frontend API modules use class mixins for feature composition. Unusual pattern but works for this codebase size.

### Key Dependencies
- **pydantic v2** — Used for settings and schemas. Validation decorators are v2 syntax.
- **SQLAlchemy 2.0** — Modern session/query patterns used.
- **React Query (TanStack)** — All data fetching uses query/mutation hooks.
- **Yjs** — Real-time collaboration via Yjs binary state stored in Document model.

### Technical Debt Indicators
- **20+ Alembic migrations** — Some migrations have hardcoded values (`tenant_id=1`), some patch previous migration mistakes
- **Two rate limiting systems** — `AuthRateLimitService` (application-level) and `RateLimitMiddleware` (ASGI middleware) operate independently
- **Two feature flag systems** — Config settings + DB model
- **Frontend test infrastructure** — `playwright.config.ts` exists but no `*.spec.ts` files found
- **Backend test count** — 1384 tests collected, but many are structural/parametric (RBAC matrix = 53 tests alone)

---

## 7. Review by Feature

### 7.1 Document Management
- **What it does:** CRUD for documents with metadata, categories, tags, visibility, versioning
- **Strengths:** Optimistic concurrency via row_version, duplicate detection, hierarchical docs (parent_id), multi-format upload
- **Problems:** (a) No max title/description length enforced on frontend. (b) Tags have no count or length limit. (c) `COMPANY` visibility with empty company list creates invisible documents. (d) Category and topic are free-text — no taxonomy enforcement.
- **Missing:** Soft-delete/archive undo, document templates, category management UI

### 7.2 Version & Publish Workflow
- **What it does:** Semantic versioning (MAJOR/MINOR/PATCH), review submission, approval, audience snapshot, publish
- **Strengths:** Audience drift detection, stale company checks at publish, immutable published versions, published_attachment_ids_snapshot
- **Problems:** (a) C-NEW-6: Race condition between approval and publish. (b) Peer approval only allows EDITOR submissions — unclear product intent. (c) No rollback mechanism for published versions.
- **Missing:** Version comparison/diff, bulk publish, scheduled auto-publish

### 7.3 Review System
- **What it does:** Submit → Approve/Reject workflow with audience snapshots
- **Strengths:** Self-approval prevention, audience snapshot at submission, policy-based authorization
- **Problems:** (a) No SLA enforcement — reviews can sit indefinitely. (b) `reviewer_reminded_at` and `manager_escalated_at` fields exist but no automation found. (c) No partial approval (approve content but flag audience issues).
- **Missing:** Review assignment rules, auto-assignment to least-busy reviewer, review SLA dashboard

### 7.4 Authentication & Sessions
- **What it does:** JWT login, refresh token rotation, session tracking, account lockout, password reset
- **Strengths:** Token rotation on refresh (M-10), concurrent session limits (AD-013), httpOnly cookie storage, timing-safe password comparison
- **Problems:** (a) P-04: No rate limit on registration. (b) Account lockout returns 401 (good for anti-enumeration but confusing UX). (c) No MFA support.
- **Missing:** MFA (TOTP/WebAuthn), SSO/SAML integration, session activity log for users

### 7.5 Multi-Tenancy
- **What it does:** Tenant isolation via TenantContext dependency, middleware-level propagation, per-query filtering
- **Strengths:** ContextVar for async safety, suspended tenant rejection (Z-009), SYSTEM_ADMIN cross-tenant access
- **Problems:** (a) C-NEW-2: Chat cross-tenant leak. (b) P-11: Support ticket scoping fails on None tenant_id. (c) P-15: Company cache stale window.
- **Missing:** Tenant-level feature flags are partially implemented, tenant-level rate limiting

### 7.6 AI Assistant
- **What it does:** Ollama-powered chat with 29 tools, RAG search via ChromaDB, @mention document injection
- **Strengths:** Smart tool routing (keyword groups), GPU optimization, temperature tuning for tool calls, conversation persistence
- **Problems:** (a) C-NEW-1: RAG tools bypass access policies. (b) C-NEW-3: VectorStore defaults tenant_id to 0. (c) P-10: @mention failures are silent.
- **Missing:** Tool permission matrix documentation, conversation sharing, assistant feedback mechanism

### 7.7 Chat & Collaboration
- **What it does:** Direct/group/document chats, file sharing, real-time collaboration via Yjs
- **Strengths:** Participant-based access, chat types (DIRECT/GROUP/DOCUMENT), optimistic message delivery
- **Problems:** (a) C-NEW-2: Cross-tenant direct chats. (b) P-14: Document chat skips access check. (c) P-16: Flat file storage. (d) P-19: Unvalidated context_json.
- **Missing:** Message editing, message deletion, typing indicators, read receipts, chat search

### 7.8 Customer Portal
- **What it does:** Customer-facing document browser, reading progress, feedback, support tickets
- **Strengths:** Role-specific layout, reading progress tracking, company-scoped document visibility
- **Problems:** (a) P-12: Non-monotonic progress. (b) No error recovery on failed progress saves. (c) No empty state for search results. (d) Date filter allows `dateFrom > dateTo`.
- **Missing:** Bookmark sync across devices, document download for offline reading, notification preferences

### 7.9 Analytics
- **What it does:** Dashboard metrics, engagement tracking, search analytics, CSV export
- **Strengths:** Tenant-scoped via AnalyticsAccessPolicy, time-series data, role-gated
- **Problems:** (a) C-NEW-5: Unbounded CSV export. (b) Analytics service may not re-scope at service layer.
- **Missing:** Real-time dashboard, custom report builder, scheduled reports

### 7.10 Admin Operations
- **What it does:** Tenant provisioning, impersonation, action queue, feature flags, domain verification, maintenance windows
- **Strengths:** Maker-checker pattern (admin action queue), audit logging, system-admin-only gates
- **Problems:** (a) Impersonation doesn't timeout automatically. (b) Feature flags have no rollout history. (c) Maintenance window doesn't actually block writes.
- **Missing:** Admin dashboard health overview, systemic alert configuration, automated backup management

---

## 8. Review by Flow

### 8.1 Login → Dashboard Flow
- **Entry:** `/login` → LoginPage
- **API:** `POST /auth/login` → JWT + refresh token
- **Navigation:** Role-based redirect: CUSTOMER → `/portal`, internal → `/documents`
- **Issues:** (a) Rate limit counter shows but doesn't explain why (no "locked for X minutes" until already locked). (b) Session restore on page reload works but shows brief loading flash.

### 8.2 Document Create → Publish Flow
- **Entry:** Documents page → "New Document" or "Upload"
- **API chain:** `POST /documents` → `POST /documents/{id}/versions` → `POST /reviews/{doc_id}/submit` → `POST /reviews/{id}/approve` → `POST /versions/{id}/publish`
- **Issues:** (a) No validation that document has at least one version before review submission. (b) Upload modal doesn't show progress bar for large files. (c) Publish action requires page refresh to see updated status in some cases.

### 8.3 Customer Document Consumption Flow
- **Entry:** Customer portal → document list → document detail → reading progress
- **API chain:** `GET /public/documents` or BFF → `GET /viewer/documents/{id}` → `PUT /engagement/progress/{id}`
- **Issues:** (a) Public API and viewer API serve the same data through different paths — redundant. (b) If customer's company is removed from audience mid-session, no immediate feedback. (c) Reading progress saves on scroll but no debounce — could generate many API calls.

### 8.4 Review Workflow Flow
- **Entry:** Document detail → "Submit for Review" → Review queue → Approve/Reject
- **API chain:** `POST /reviews/{doc_id}/submit` → `GET /reviews?status=pending` → `POST /reviews/{id}/approve|reject`
- **Issues:** (a) No notification when review is assigned. (b) Reviewer list not filtered by availability. (c) Rejection requires re-submission — no "revise and resubmit" status.

### 8.5 Invitation → Onboarding Flow
- **Entry:** Admin creates invitation → email link → accept page → set password → login
- **API chain:** `POST /invitations` → `GET /auth/invitation/{token}` → `POST /auth/invitation/accept`
- **Issues:** (a) No rate limit on invitation creation. (b) Expired invitation shows generic error instead of "request new invitation" action. (c) No invitation resend functionality.

### 8.6 AI Assistant Chat Flow
- **Entry:** Chat bubble → Send message → SSE response stream → Tool calls → Final response
- **API chain:** `POST /assistant/chat` (SSE) → internal tool execution → streaming tokens
- **Issues:** (a) C-NEW-1: Tools bypass access policies. (b) If Ollama is down, error message is generic ("assistant unavailable"). (c) Long tool execution chains have no progress indication. (d) No cancel/abort mechanism for long-running requests.

---

## 9. Review by User Type / Role

### 9.1 SYSTEM_ADMIN
- **Should be able to:** Full platform control — all tenants, impersonation, feature flags, quotas, GDPR
- **Currently can:** All of the above, correctly gated with `require_system_admin`
- **Permission leaks:** None found at endpoint level
- **Issues:** (a) Impersonation sessions don't auto-expire. (b) No audit log for system admin's own actions (auditing others but not themselves). (c) Can grant SYSTEM_ADMIN role to others via API without maker-checker pattern.

### 9.2 ADMIN (Tenant Admin)
- **Should be able to:** Manage users/companies within own tenant, view analytics, manage invitations
- **Currently can:** All of the above
- **Permission leaks:** (a) Can potentially see analytics for other companies via direct API call if AnalyticsAccessPolicy has gaps. (b) Can delete any company (guarded as system-admin-only at route level, but `require_admin` dep doesn't distinguish).
- **Issues:** Company deletion route uses `require_admin` but then checks `role != SYSTEM_ADMIN` inside — the dependency should be `require_system_admin`.

### 9.3 MANAGER
- **Should be able to:** Manage documents, approve reviews, manage content lifecycle
- **Currently can:** All of the above
- **Permission leaks:** None found
- **Issues:** (a) Cannot be peer-approved by another manager — only ADMIN+ can approve manager submissions. (b) No dashboard showing "pending actions" (reviews awaiting, documents needing attention).

### 9.4 EDITOR
- **Should be able to:** Create/edit documents, submit for review
- **Currently can:** All of the above, plus publish (which is surprising)
- **Issues:** (a) Publish endpoint uses `require_editor` — should this be `require_manager`? The command handler may add additional checks. (b) Can create versions on any document in their tenant (no per-document ownership restriction).

### 9.5 VIEWER
- **Should be able to:** Read internal documents, leave comments and feedback
- **Currently can:** View documents, but comment/feedback permissions unclear
- **Issues:** (a) Viewer can access engagement endpoints — bookmarks, watchlists, reading progress — but no clear restriction on what they can interact with. (b) Can they see COMPANY-restricted documents? Only if `is_internal_user` check passes (it does for VIEWER).

### 9.6 CUSTOMER
- **Should be able to:** See only published documents visible to their company, track reading, submit feedback/support tickets
- **Currently can:** All of the above via portal routes
- **Permission leaks:** (a) C-NEW-1: Can potentially access internal docs via AI assistant tools. (b) C-NEW-2: Can be added to cross-tenant chats by internal users. (c) If assigned company is removed from document audience mid-session, customer still sees cached content until page refresh.
- **Issues:** (a) No clear "access revoked" notification when company assignment changes. (b) Support ticket creation doesn't validate that ticket is about a document the customer can actually access.

---

## 10. Review by Engineering Quality

### 10.1 Code Quality
- **Strengths:** Consistent naming, clear module boundaries, good use of dataclasses and Pydantic
- **Weaknesses:** (a) Some services are >800 lines (document_service.py). (b) Two different approaches to error handling (exceptions vs return codes). (c) Commented code blocks in frontend pages. (d) Unused imports scattered in test files.

### 10.2 Architecture
- **Strengths:** Clean layer separation (API → Service → Domain → Repository), policy-based auth, middleware stack
- **Weaknesses:** (a) Command/query separation is partial — some services mix both. (b) Two feature flag systems. (c) Two rate limiting systems. (d) DI container is a manual class, not a proper IoC framework. (e) Event outbox exists but isn't wired to consumers.

### 10.3 Maintainability
- **Strengths:** Well-organized file structure, clear naming conventions, Alembic migrations
- **Weaknesses:** (a) 120+ test files with varying quality. (b) No API contract tests between frontend and backend. (c) No automated schema validation (OpenAPI spec exists but not enforced).

### 10.4 Testing
- **Strengths:** 1384 tests covering unit, integration, and structural levels. RBAC matrix test (53 parametric cases). Attack harness tests.
- **Weaknesses:** (a) No E2E tests despite Playwright config. (b) Tests use in-memory SQLite — may miss PostgreSQL-specific issues. (c) Some tests are implementation-coupled (mock-heavy). (d) No load testing or performance benchmarks.

### 10.5 Scalability
- **Strengths:** Stateless API design (except rate limiter state), Redis support for caching
- **Weaknesses:** (a) SQLite single-writer. (b) In-memory rate limiter doesn't share state across workers. (c) Daemon threads instead of job queue. (d) ChromaDB is file-based — no horizontal scaling. (e) No CDN configuration for static assets.

### 10.6 Type Safety
- **Strengths:** TypeScript strict mode on frontend, Pydantic on backend, enum-based roles
- **Weaknesses:** (a) Some `Any` types in tool call interfaces. (b) `context_json` is untyped dict. (c) Frontend role hierarchy computed from string comparisons, not discriminated unions.

---

## 11. Priority Action Plan

### Immediate Fixes (Before Any Production Deployment)
1. **C-NEW-1:** Add DocumentAccessPolicy checks to all RAG tools
2. **C-NEW-2:** Reject cross-tenant direct chats
3. **C-NEW-3:** Reject None tenant_id in VectorStore
4. **C-NEW-4:** Add rate limiting to public endpoints
5. **C-NEW-5:** Cap analytics export date range to 90 days
6. **P-06:** Replace regex HTML sanitization with bleach + DOMPurify
7. **P-07:** Remove insecure default secrets from docker-compose

### Short-Term Improvements (Next 2-4 Weeks)
8. **C-NEW-6:** Add optimistic locking on audience state at approval time
9. **P-02:** Enforce CSRF in all non-testing environments
10. **P-03:** Validate X-Forwarded-For against trusted proxies
11. **P-04 + P-05:** Add rate limiting to registration and invitation endpoints
12. **P-09:** Migrate collab-server token to WS message (H-21)
13. **P-14:** Add document access check to chat creation
14. **P-17:** Replace daemon thread PDF generation with job queue

### Medium-Term Refactors (1-3 Months)
15. **I-01:** Migrate to PostgreSQL
16. **I-02:** Redis-based rate limiting
17. **I-06:** Add Playwright E2E tests for critical flows
18. **I-03:** Request-ID correlation across services
19. Consolidate two feature flag systems
20. Consolidate two rate limiting systems
21. Add input validation schemas on frontend (Zod)

### Long-Term Ideas (3-6 Months)
22. MFA support (TOTP/WebAuthn)
23. SSO/SAML integration
24. OpenTelemetry instrumentation
25. Event-driven architecture with real message bus
26. CQRS read models for analytics
27. Document diff viewer

---

## 12. Top 10 Highest-Value Fixes

| Rank | Fix | Impact | Effort | ROI |
|------|-----|--------|--------|-----|
| 1 | **Add DocumentAccessPolicy to RAG tools** (C-NEW-1) | Closes critical data leak | Low | Highest |
| 2 | **Reject cross-tenant chats** (C-NEW-2) | Closes tenant isolation gap | Low | Highest |
| 3 | **Rate limit public endpoints** (C-NEW-4) | Prevents anonymous DoS | Low | Very High |
| 4 | **Cap analytics export** (C-NEW-5) | Prevents OOM DoS | Low | Very High |
| 5 | **Replace regex sanitization with bleach** (P-06) | Closes XSS vector | Medium | Very High |
| 6 | **Fix VectorStore tenant_id=0** (C-NEW-3) | Closes silent cross-tenant leak | Low | High |
| 7 | **Remove insecure Docker defaults** (P-07) | Prevents accidental production misconfiguration | Low | High |
| 8 | **Add optimistic lock on audience at approval** (C-NEW-6) | Prevents review race condition | Medium | High |
| 9 | **Migrate to PostgreSQL** (I-01) | Production reliability foundation | High | High (long-term) |
| 10 | **CSRF enforcement in non-test environments** (P-02) | Closes CSRF in staging | Low | Medium |

---

## Risk Heatmap Summary

| Area | Risk Level | Key Concern |
|------|-----------|-------------|
| **AI Assistant / RAG** | CRITICAL | Access policy bypass, cross-tenant vectors |
| **Chat Service** | CRITICAL | Cross-tenant direct messaging |
| **Public Endpoints** | CRITICAL | No rate limiting, no input bounds |
| **Analytics Export** | CRITICAL | Unbounded memory consumption |
| **Auth / Sessions** | LOW | Well-implemented; minor UX issues |
| **Document CRUD** | MEDIUM | Missing frontend validation, no undo |
| **Review Workflow** | HIGH | Race condition on audience state |
| **Tenant Isolation (core)** | LOW | Strong pattern, well-enforced in core |
| **Tenant Isolation (new features)** | CRITICAL | Chat, AI, analytics have gaps |
| **Frontend Auth** | LOW | Solid multi-layer protection |
| **Frontend UX** | MEDIUM | Inconsistent states, missing validation |
| **Infrastructure** | HIGH | SQLite, insecure defaults, no observability |
| **Collab Server** | MEDIUM | Token in URL, no rate limit on saves |
| **CI/CD** | MEDIUM | No E2E tests, no DAST, no load tests |

---

## Files/Modules — Fragility Assessment

### Most Fragile
1. **`backend/app/assistant/tools/rag_tools.py`** — Bypasses access policies, weak tenant checks, role enforcement gap
2. **`backend/app/services/chat_service.py`** — Cross-tenant leak, missing document access check, unvalidated context_json
3. **`backend/app/services/version_service.py`** — Race conditions in publish flow, daemon thread PDF gen
4. **`backend/app/api/management/analytics.py`** — Unbounded export, potential tenant scope bypass at service layer
5. **`backend/app/middleware/rate_limit.py`** — Trusts X-Forwarded-For, no cross-worker state sharing
6. **`backend/app/utils/sanitization.py`** — Regex-based HTML sanitization

### Strongest
1. **`backend/app/dependencies/permissions.py`** — Clean dependency injection for RBAC, well-tested
2. **`backend/app/dependencies/tenant.py`** — TenantContext with suspended-tenant rejection
3. **`backend/app/application/policies/access_policies.py`** — Centralized policy decisions, well-structured
4. **`backend/app/services/auth_service.py`** — Token rotation, session management, lockout logic
5. **`frontend/src/lib/api/httpClient.ts`** — Proper 401 handling, token refresh queue, in-memory storage
6. **`backend/app/app_factory.py`** — Clean middleware ordering, startup validation

---

## Top Architectural Weaknesses
1. **SQLite as production database** — Fundamental scalability ceiling
2. **Two parallel rate limiting systems** — AuthRateLimitService + RateLimitMiddleware with different scopes and no coordination
3. **Two parallel feature flag systems** — Config settings + DB table
4. **Daemon threads instead of job queue** — No retry, no monitoring, crash-lossy
5. **Event outbox without consumers** — Pattern exists but not wired to anything
6. **Manual DI container** — Stateful policy singletons shared across requests

## Top Logic Risks
1. **Audience drift between approval and publish** — Last-write-wins, no locking
2. **VectorStore tenant_id=0 bucket** — Silent cross-tenant mixing
3. **Company cache 5-minute stale window** — Operations permitted on deactivated companies
4. **Non-monotonic reading progress** — Corrupts analytics data
5. **Silent @mention access denial** — User gets no feedback on blocked mentions

## Top Security/Permission Risks
1. **RAG tools bypass DocumentAccessPolicy** — CUSTOMER can access INTERNAL documents via AI
2. **Cross-tenant chat creation** — Internal user bridges tenant boundary
3. **No rate limiting on public endpoints** — Anonymous DoS vector
4. **X-Forwarded-For spoofing** — All rate limiting defeated
5. **Regex HTML sanitization** — Stored XSS via encoding bypass

---

## Conclusion

**If I were improving this project next, I would start with:**

The five low-effort, high-impact fixes that close real data leaks: (1) Add `DocumentAccessPolicy.can_view_document()` to every RAG tool, (2) reject cross-tenant direct chats in `chat_service.py`, (3) fix VectorStore `tenant_id=0` default, (4) add rate limiting to public endpoints, and (5) cap the analytics export date range. These five changes each require <50 lines of code and close the widest attack surfaces in the system. After those, replace regex HTML sanitization with `bleach` and remove the insecure Docker Compose defaults. Only then would I begin the larger PostgreSQL migration and job queue infrastructure work.
