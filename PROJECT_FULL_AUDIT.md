# Project Full Audit — Combined

> **Date:** 2025-07-10 (merged 2026-03-20)  
> **Auditors:** Two independent deep audits — merged into one definitive document  
> **Branch:** `audit`  
> **Commit:** `e7f2d4b`  
> **Scope:** Full-stack CMS platform — backend (FastAPI), frontend (React/Vite), collab-server (Hocuspocus/Node), Docker/CI/CD, AI assistant (Ollama/ChromaDB)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Problems](#2-critical-problems)
3. [Problems (Bugs & Issues)](#3-problems-bugs--issues)
4. [Improvement Suggestions](#4-improvement-suggestions)
5. [Ideas](#5-ideas)
6. [Helpful Notes](#6-helpful-notes)
7. [Review by Feature](#7-review-by-feature)
8. [Review by Flow](#8-review-by-flow)
9. [Review by User Type / Role](#9-review-by-user-type--role)
10. [Review by Engineering Quality](#10-review-by-engineering-quality)
11. [Priority Action Plan](#11-priority-action-plan)
12. [Top 10 Highest-Value Fixes](#12-top-10-highest-value-fixes)
13. [Risk Heatmap](#13-risk-heatmap)
14. [Fragile & Strong Modules](#14-fragile--strong-modules)
15. [Top Weaknesses & Risks](#15-top-weaknesses--risks)
16. [Conclusion](#16-conclusion)

---

## 1. Executive Summary

This platform is a **multi-tenant content management system** with collaborative editing, AI-assisted content generation, RBAC, customer portals, analytics, versioning, support tickets, and feedback. The technology stack is modern (FastAPI + React + TipTap + Hocuspocus + Ollama), and the architecture shows care: tenant isolation patterns, row-level versioning, role hierarchies, soft-delete, audit logging, and security headers are all present.

However, two independent deep audits uncovered a combined **16 CRITICAL**, **24 HIGH**, **25+ MEDIUM**, and **15+ LOW** severity issues across the full stack. The codebase is stronger in its document-core happy path but significantly weaker in surrounding surfaces — admin, support, analytics, attachments, AI assistant, chat, and CI/CD infrastructure.

**The core problem is not missing infrastructure — it is inconsistent adoption.** The RBAC system is well-designed but applied unevenly. Tenant isolation exists but has critical holes. The security pipeline runs but doesn't enforce. The AI assistant is powerful but acts as an authorization bypass.

**Overall project rating: 6/10** — Good architecture vision with significant security and logic gaps that must be closed before any production deployment.

**Production readiness: NOT READY.** The codebase is beyond prototype stage but contains production-blocking defects across security, authorization, multi-tenancy, session management, and deployment infrastructure.

---

## 2. Critical Problems

### C1. RAG Vector Store — Zero Tenant Isolation

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | AI Assistant / Security |
| **Files** | `backend/app/services/ai/tools/semantic_search_tool.py`, `backend/app/services/ai/rag/vector_store.py` |
| **Description** | The ChromaDB vector store queries ALL documents globally. When a user performs a semantic search via the AI assistant, the query hits the entire corpus across all tenants. A post-filter attempts to remove unauthorized results, but the raw embedding vectors and similarity scores for cross-tenant documents are already computed and potentially cached. |
| **Why Critical** | In a multi-tenant SaaS, a single tenant seeing another tenant's document content (even via embedding similarity) is a **data breach**. This is the single most dangerous finding in the audit. |
| **Example** | Tenant A user asks AI: "Show documents about Project X." ChromaDB returns Tenant B's confidential documents in the initial query set. Even if post-filtered, timing side-channels and embedding proximity reveal information. |
| **Fix** | Add `tenant_id` to ChromaDB collection metadata. Use `where={"tenant_id": current_tenant_id}` on every query. Create separate ChromaDB collections per tenant, or enforce namespace isolation at the vector store layer. |

### C2. Document @Mention Injection Bypasses Visibility/RBAC

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | AI Assistant / Authorization |
| **Files** | `backend/app/services/ai/context_builder.py`, `backend/app/services/ai/tool_executor.py` |
| **Description** | When a user types `@DocumentName` in the AI chat, the system fetches that document's content and injects it into the LLM context. There is **no check** on document visibility status (DRAFT, INTERNAL, ARCHIVED) or the user's RBAC permission to view that document. |
| **Why Critical** | Any authenticated user can access the full text of any document within their tenant by @mentioning it, including DRAFT documents they should never see, INTERNAL documents restricted to specific roles, and ARCHIVED documents removed from circulation. |
| **Example** | A CUSTOMER-role user types `@"Internal Strategy 2025"` and receives the full text injected into their chat context, despite having no permission to view INTERNAL documents. |
| **Fix** | Before injecting @mentioned document content, validate: (1) document status is PUBLISHED/ACTIVE, (2) user has `view` permission via the existing RBAC check, (3) document visibility matches user's role level. |

### C3. Attachment Download Tickets Are Broken and Forgeable

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Security / API / Attachments |
| **Files** | `backend/app/api/management/attachments.py`, `frontend/src/lib/api/attachmentsApi.ts` |
| **Description** | `issue_download_ticket()` emits a five-part token: `user_id:document_id:attachment_id:timestamp:signature`. `_verify_download_ticket()` expects only four parts, so the backend-generated signed token does not match the verifier. Worse, the verifier never parses or compares the provided signature at all — it recomputes both `expected_sig` and `provided_sig` from server-side inputs, making the HMAC check meaningless. It also only rejects old timestamps, not future timestamps. |
| **Why Critical** | This is a broken authorization mechanism on a direct file-download path. Anyone who knows or can guess a valid `user_id`, `document_id`, and `attachment_id` can forge a token. Using a future timestamp makes the token effectively long-lived. |
| **Example** | An attacker crafts `42:100:9:9999999999` and calls `/api/v1/documents/100/attachments/9/download?token=...`. The verifier accepts the forged token. |
| **Fix** | Parse the signature from the token, compare using `hmac.compare_digest`, reject future timestamps, reject malformed part counts, and add regression tests. |

### C4. Company-Admin Endpoints Are Only Partially Tenant-Scoped

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Role Logic / Security / Multi-tenancy |
| **Files** | `backend/app/api/management/companies.py`, `backend/tests/tenant_isolation/test_attack_harness.py` |
| **Description** | `list_companies()` scopes non-system-admins to their own tenant. The rest of the company-management surface does not: `get_company()`, `update_company()`, `list_company_users()`, `add_user_to_company()`, `list_company_documents()`, and `get_audience_blockers()` all accept a `company_id` and trust `require_admin` without re-checking tenant ownership. |
| **Why Critical** | A tenant admin can manage arbitrary companies across tenants. The route surface says "admin" but the data access says "platform-wide." |
| **Example** | An admin from tenant A calls `/api/v1/companies/2/users` and reads tenant B's user list. |
| **Fix** | Centralize tenant ownership checks for every company route, use `TenantContext` consistently, and extend tenant-isolation tests to cover the full companies surface. |

### C5. Support-Ticket REST APIs Expose Cross-Tenant Data

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Security / Role Logic / Support |
| **Files** | `backend/app/api/management/support.py`, `backend/app/services/support_service.py`, `frontend/src/pages/SupportPage.tsx` |
| **Description** | The frontend only exposes support UI to managers and above. The backend does not enforce that. Most support routes depend on `require_internal_user`, not a manager/agent role. `SupportTicketService.list_tickets()` gives all internal staff all tickets, `_check_ticket_access()` allows any admin/manager/editor to access any ticket, and `_get_ticket_for_agent()` grants any admin/manager/editor unrestricted agent-level access. |
| **Why Critical** | Tickets contain customer conversations, internal notes, assignment metadata, and operational context. The REST API makes them effectively global to internal staff, regardless of tenant or assignment. |
| **Example** | An editor from tenant A calls `/api/v1/support/tickets` and inspects tenant B's customer support thread. |
| **Fix** | Enforce role-based access at the route level, scope ticket visibility by tenant and assignment in the service layer, and make REST and WebSocket authorization rules match. |

### C6. Published Attachment Snapshot Bypassed by Direct Endpoints

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Product Logic / Security / Public API / Portal |
| **Files** | `backend/app/application/queries/portal_queries.py`, `backend/app/api/portal/documents.py`, `backend/app/api/public/documents.py`, `backend/app/api/viewer/documents.py`, `backend/app/services/attachment_service/streams.py` |
| **Description** | Public, viewer, and portal listing endpoints try to scope attachments to the published snapshot by cutoff time. Direct metadata and download endpoints do not consistently apply that cutoff. `get_public_attachment()` returns metadata for any attachment on a public document. Viewer and portal download paths stream the live attachment without a centralized published-snapshot check. |
| **Why Critical** | The product semantics say published readers should get an immutable release. The implementation leaks mutable, post-publish attachment state through alternate routes. |
| **Example** | A public document is published. An internal user uploads a new attachment afterward. The direct metadata/download route still serves it to public readers. |
| **Fix** | Move published-attachment resolution into one central service. Prefer the explicit `published_attachment_ids_snapshot` over ad hoc live queries. |

### C7. Version Endpoints Missing Admin Enforcement

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | API / Authorization |
| **Files** | `backend/app/routes/versions.py` |
| **Description** | Three version endpoints — `force-publish`, `delete`, and `restore-audience` — use `get_current_active_user` instead of `require_admin`. Their docstrings say "Only admins can do this" but the code allows **any authenticated user** to execute these operations. |
| **Why Critical** | An EDITOR or VIEWER can force-publish incomplete content, delete version history, or alter audience settings — all admin-only operations. |
| **Example** | `PUT /api/versions/{id}/force-publish` with a regular EDITOR token succeeds when it should return 403. |
| **Fix** | Replace `Depends(get_current_active_user)` with `Depends(require_role(["ADMIN", "SYSADMIN"]))` on all three endpoints. |

### C8. XXE / SSRF in Public Sitemap & Feed

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | API / Input Validation |
| **Files** | `backend/app/routes/public.py` |
| **Description** | The `sitemap.xml` and `feed.xml` endpoints accept a `base_url` query parameter and embed it directly into XML output without any validation or sanitization. An attacker can inject arbitrary XML. |
| **Why Critical** | XXE can lead to server-side file reads, SSRF into internal networks, or denial-of-service via entity expansion. Injecting a malicious base URL poisons search engine crawlers. |
| **Example** | `GET /api/public/sitemap.xml?base_url=]]><evil/>` breaks XML structure. |
| **Fix** | Validate `base_url` against an allowlist. Use proper XML serialization instead of string interpolation. Reject URLs that don't match `^https?://[a-zA-Z0-9.-]+$`. |

### C9. CD Pipeline Allows Skipping Tests

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | CI/CD |
| **Files** | `.github/workflows/cd.yml` (lines 48-51) |
| **Description** | The deployment workflow exposes a `skip_tests` boolean input parameter. The production stage also accepts a skipped staging step as passing. |
| **Why Critical** | Any developer with `workflow_dispatch` permission can deploy untested code directly to production. |
| **Fix** | Remove `skip_tests` entirely. Make staging a hard requirement. |

### C10. Security Scan Failures Don't Block Merge

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | CI/CD |
| **Files** | `.github/workflows/security.yml` |
| **Description** | Gitleaks, TruffleHog, pip-audit, and Safety all use `continue-on-error: true`. Discovered secrets and CVEs are reported but never block the merge or deployment. |
| **Why Critical** | Committed secrets reach production. Known CVEs in dependencies don't prevent deployment. The security pipeline creates a false sense of protection. |
| **Fix** | Remove `continue-on-error: true` from secret detection steps. Make pip-audit/Safety failures block the build. |

### C11. Nginx — No HTTPS Enforcement

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Infrastructure / Deployment |
| **Files** | `frontend/nginx.conf` (line 1) |
| **Description** | Nginx listens only on port 80. No SSL/TLS listener, no HTTPS redirect, no HSTS header. Production docker-compose exposes 443 but nginx has no SSL configuration. |
| **Why Critical** | All traffic travels in plaintext. Session hijacking via network sniffing is trivial. |
| **Fix** | Add `listen 443 ssl http2;`. Add HTTP→HTTPS redirect. Add HSTS header. |

### C12. Hardcoded Secrets in Docker Compose

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Infrastructure / Secrets |
| **Files** | `docker-compose.yml` (lines 18, 82) |
| **Description** | `SECRET_KEY=docker-dev-secret-key-change-in-prod` and `JWT_SECRET=docker-dev-secret-key-change-in-prod` hardcoded in version-controlled file. Same weak secret shared across services. |
| **Why Critical** | Anyone with repo access can forge JWT tokens. If used in production, all authentication is compromised. |
| **Fix** | Replace with `${SECRET_KEY}` referencing `.env`. Add startup validation that rejects the insecure default. |

### C13. Document.tenant_id is Nullable

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Area** | Database / Multi-Tenancy |
| **Files** | `backend/app/models/models.py` |
| **Description** | `Document.tenant_id` is `nullable=True`. Documents can exist without a tenant association, breaking the multi-tenancy invariant. |
| **Why Critical** | Orphaned documents are invisible to tenant-scoped queries or globally accessible if any path doesn't filter by tenant. |
| **Fix** | Set `nullable=False`. Migration to assign or delete orphans. Add CHECK constraint. |

### C14. Successful Refresh Deletes the Refresh Cookie

| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH (functionally critical) |
| **Area** | Auth / Backend / Frontend |
| **Files** | `backend/app/api/management/auth.py`, `backend/app/services/auth_service.py`, `frontend/src/lib/api/httpClient.ts` |
| **Description** | `_token_json_response()` always calls `_set_refresh_cookie()`. `AuthService.refresh_access_token()` returns no `refresh_token`. `_set_refresh_cookie()` treats a missing token as a delete instruction and clears the cookie. This is the main session-resume path. |
| **Why Critical** | User logs in → gets cookie → SPA refreshes access token → cookie deleted → next cold start = logged out. |
| **Fix** | Preserve the existing cookie when the response omits rotation. Add e2e tests for cookie persistence. |

### C15. Search Analytics Globally Exposed

| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Area** | Security / Analytics / API |
| **Files** | `backend/app/api/management/search.py` |
| **Description** | `get_search_analytics()` depends only on `get_current_active_user`. No role/tenant restriction. Aggregates all search and click events globally. |
| **Why Critical** | Leaks internal demand signals, failed searches, and platform behavior to any authenticated caller, including customers. |
| **Fix** | Restrict to staff roles. Scope by tenant unless `system_admin`. |

### C16. Feedback Management Leaks PII

| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Area** | Security / UX Flow / Backend |
| **Files** | `backend/app/api/management/feedback.py`, `frontend/src/pages/admin/FeedbackPage.tsx` |
| **Description** | Frontend limits to managers+. Backend allows all internal staff. Contributor-based visibility exposes `user_name`, `user_email`, `tenant_name`. `get_feedback_stats()` is unscoped (global counts). |
| **Why Critical** | Privacy leak — contributors see customer PII, managers see cross-tenant counts. |
| **Fix** | Replace contributor-based visibility with explicit support/manager policy. Add tenant scoping. Minimize PII by role. |

---

## 3. Problems (Bugs & Issues)

### HIGH Severity

| ID | Title | Area | Files | Description |
|----|-------|------|-------|-------------|
| H-01 | Chat endpoints skip participant validation | API | `routes/chat.py` | GET messages, search, file download don't verify the requestor is a chat participant. Any authenticated user can read any chat. |
| H-02 | Attachment endpoints skip document access check | API | `routes/attachments.py` | Listing, downloading, reader-view endpoints don't validate user's access to the parent document. |
| H-03 | Collab token issued without ownership validation | Auth | `auth_context/collaboration_auth_service.py` | Collaboration tokens are issued to any authenticated user requesting, without checking permission on the target document. |
| H-04 | SemanticSearchTool missing RBAC gate | AI | `services/ai/tools/semantic_search_tool.py` | CUSTOMER-role users can invoke semantic search, which should require VIEWER+ permissions. |
| H-05 | In-memory rate limiting bypassed by multiple workers | Middleware | `middleware/rate_limit.py` | Rate counters are per-process. With 4 Gunicorn workers, effective rate limit is 4×. |
| H-06 | Tool error messages leak internal details | AI | `services/ai/tool_executor.py` | Raw exception messages (table names, column names, stack traces) returned to users. |
| H-07 | Missing CSRF protection in practice | Middleware | `middleware/csrf.py` | CSRF middleware allows requests with missing Origin/Referer in production (silent pass-through). |
| H-08 | Timing attack on user enumeration | Auth | `routes/auth.py` | Password reset returns different response times for existent vs non-existent emails. |
| H-09 | Demo credentials displayed on login page | Frontend | `pages/LoginPage.tsx` | Hardcoded sysadmin/admin/manager/editor/customer credentials shown in production UI. Should gate on `APP_ENV`. |
| H-10 | Path traversal in chat file upload | API | `routes/chat.py` | Filename suffix check without full path sanitization. `../../etc/passwd.pdf` could escape upload dir. |
| H-11 | Auth endpoints excluded from rate limiting | Middleware | `middleware/rate_limit.py` | Login endpoints completely exempt from rate limiting — brute-force friendly. |
| H-12 | Collab-server — no timeout on backend requests | Collab | `adapters/backendDocumentStateTransportAdapter.ts` | HTTP requests from collab-server to backend have no timeout. Network issues = connection hangs. |
| H-13 | Missing 12+ database indexes | Database | `models/models.py` | Frequent query columns (documents.tenant_id, audit_logs.tenant_id+created_at, feedbacks.document_id, user_sessions.user_id) lack indexes. |
| H-14 | Duplicate platform columns (string + FK) | Database | `models/models.py` | `Document.platform` (string) and `Document.platform_id` (FK) — two conflicting sources of truth. |
| H-15 | Publish tool missing confirmation gate | AI | `services/ai/tools/` | `publish_document` executes immediately without confirmation, unlike delete. |
| H-16 | Insecure dev JWT secret in collab-server | Collab | `collab-server/src/authContext/collaborationAuthService.ts` | Hardcoded `INSECURE_DEV_SECRET` accepted in dev without enforcing minimum key length. |
| H-17 | Version endpoints too permissive for viewers | API | `routes/versions.py` | VIEWER-role can list versions and check publish readiness — should require EDITOR+. |
| H-18 | No HTML sanitization in generate-word endpoint | API | document generation | Content injected into Word generation without HTML sanitization. |
| H-19 | SPA auth-restore skips on public-route entry | Frontend | `frontend/src/lib/auth.tsx`, `httpClient.ts` | `AuthProvider` skips `tryRestoreSession()` on public routes, leaving users incorrectly unauthenticated with valid refresh cookie. |
| H-20 | Portal reading-progress check logically wrong for company docs | Portal | `backend/app/api/portal/documents.py` | `_customer_can_still_access()` returns `user.tenant_id is not None` for company docs — never checks company assignment. |
| H-21 | WebSocket auth leaks bearer tokens in query strings | Security | `useChatSocket.ts`, `chat_ws.py`, `support_ws.py` | Chat/support sockets send bearer via `?token=` — leaks into logs, proxies, browser devtools history. |
| H-22 | Collaboration URL handling — contract drift | Frontend/Backend | `auth.py`, `useCollaboration.ts`, `useChatSocket.ts`, collab-server | Backend returns hardcoded `ws://localhost:8002/document/{id}`, frontend ignores it and composes its own URL, chat uses a third default. Three competing assumptions. |
| H-23 | Test suite stale in critical auth and portal areas | Testing | `test_auth.py`, `test_portal_api.py`, `test_route_auth_parity.py` | 5 failures in auth tests. Portal tests have draft-fallback expectations. Route-auth parity tests only check "some auth dependency exists," not which role. Tenant harness doesn't cover companies, support, feedback, search analytics. |

### MEDIUM Severity

| ID | Title | Area | Files |
|----|-------|------|-------|
| M-01 | `sort_by` parameter not validated against column whitelist | API | Multiple route files |
| M-02 | Chat allows cross-tenant user addition | API | `routes/chat.py` |
| M-03 | Public `/categories` filters PUBLISHED but docs use ACTIVE status | API | `routes/public.py` |
| M-04 | Bulk metadata update skips per-document permission check | API | `routes/documents.py` |
| M-05 | No pagination on chat list endpoint | API | `routes/chat.py` |
| M-06 | Refresh token accepts both cookie AND body (no precedence) | Auth | token handling |
| M-07 | Account lockout uses different HTTP status codes (info leak) | Auth | `routes/auth.py` |
| M-08 | Password complexity validator used inconsistently | Auth | registration vs profile |
| M-09 | Avatar upload no size validation | API | `routes/users.py` |
| M-10 | Refresh token rotation never occurs | Auth | token service |
| M-11 | Session revocation race condition on password change | Auth | session management |
| M-12 | Missing security headers (X-Frame-Options) in API responses | Backend | middleware |
| M-13 | Session inactivity timeout 30 days — too long | Config | `config.py` |
| M-14 | CORS origins hardcoded for development | Config | `config.py` |
| M-15 | Insufficient parameter validation in AI tools (no max length) | AI | tool definitions |
| M-16 | Audit logging truncates tool results to 200 chars | AI | tool executor |
| M-17 | Conversation summary doesn't validate LLM response quality | AI | assistant service |
| M-18 | Frontend permission check missing for visibility change dialog | Frontend | `VisibilityDialog.tsx` |
| M-19 | Company assignment permission check missing in UI | Frontend | document detail |
| M-20 | Prop drilling in DocumentDetailPage (>15 props) | Frontend | `DocumentDetailPage.tsx` |
| M-21 | Collab token refresh missing for long edit sessions | Frontend | collaboration hooks |
| M-22 | CSP missing `upgrade-insecure-requests` directive | Nginx | `nginx.conf` |
| M-23 | Collab-server health endpoint exposes document IDs unauthenticated | Collab | `healthServer.ts` |
| M-24 | Docker production backend port exposed to all interfaces | Docker | `docker-compose.prod.yml` |
| M-25 | E2E test bypass header active in development | Middleware | `rate_limit.py` |
| M-26 | Public search claims content search but only does metadata | API | `backend/app/api/public/documents.py` |
| M-27 | RSS feed links to `/docs/{id}` instead of `/doc/{id}` | API | `backend/app/api/public/documents.py` |
| M-28 | Frontend registration types out of sync with backend | Frontend | `auth.tsx`, `authApi.ts` |
| M-29 | Codebase mixes strong abstractions with ad hoc shortcuts | Architecture | multiple |

### LOW Severity

| ID | Title | Area |
|----|-------|------|
| L-01 | Multiple race conditions in document operations (slug, company assignment) | API |
| L-02 | Session identifier validation allows empty/whitespace strings | Auth |
| L-03 | No token versioning for mass revocation | Auth |
| L-04 | Missing `jti` claim in collaboration tokens | Auth |
| L-05 | axios timeout not configured in frontend | Frontend |
| L-06 | Public route prefixes hardcoded/duplicated | Frontend |
| L-07 | Error boundary lacks monitoring integration | Frontend |
| L-08 | Breadcrumb missing `aria-current="page"` | Frontend |
| L-09 | Frontend Dockerfile base image not pinned | Docker |
| L-10 | Backend Dockerfile copies all files (no .dockerignore) | Docker |
| L-11 | Collab-server document cache has no eviction policy | Collab |
| L-12 | Collab-server auth store has no token TTL | Collab |
| L-13 | Token expiry uses naive datetime (no timezone) | Backend |
| L-14 | CI migration safety runs before dependency install | CI |
| L-15 | `.gitignore` missing `.env.*.local` specific pattern | Config |

### Potential Issues

#### Potential Issue A. Assistant tool exposure is only as safe as every individual `user_can_execute()` implementation

- Status: Suspected, not fully exhaustively proven across every tool.
- Why it matters: The assistant endpoints are open to all authenticated users, and the tool registry can expose a wide operational surface instantly if one tool's permission check is wrong.
- What should happen next: Audit every assistant tool class end-to-end instead of trusting the registry abstraction.

#### Potential Issue B. Contributor-based visibility rules for comments and feedback are a brittle substitute for explicit ownership and RBAC

- Status: Partially proven.
- Why it matters: The access model depends on who has "touched" a document, not who operationally owns the workflow.
- What should happen next: Replace contributor-derived visibility with explicit support, reviewer, and moderator policies.

---

## 4. Improvement Suggestions

### Architecture

1. **Build one explicit authorization matrix and enforce it centrally** — The main failures are inconsistent role and tenant rules, not missing auth entirely. Define feature-level policies for companies, support, feedback, search analytics, attachments, and assistant tools. Make routes call those policies instead of hand-rolling checks. *(Immediate)*

2. **Centralize published-release resolution** — Published content is semi-immutable. One service should resolve published version + attachments + audience snapshot, and every public/viewer/portal consumer should use it. *(Immediate)*

3. **Replace SQLite with PostgreSQL for production** — SQLite lacks concurrent write support and row-level locking. Add a startup check that fails hard if `DATABASE_URL` contains `sqlite` when `APP_ENV=production`. *(Immediate)*

4. **Move rate limiting to Redis** — In-memory rate limiting breaks with multiple Gunicorn workers. Use Redis (already optional in prod compose) as a shared backend. *(Short-term)*

5. **Add ChromaDB namespace isolation** — Create per-tenant collections or enforce `where` filters at the vector store layer. *(Immediate)*

6. **Add database connection pooling config** — SQLAlchemy defaults are too small for production. Configure `pool_size`, `max_overflow`, `pool_timeout`. *(Short-term)*

7. **Implement proper secret management** — Replace environment variable secrets with Docker secrets, HashiCorp Vault, or AWS Secrets Manager for production. *(Short-term)*

### Security

8. **Stop treating frontend route guards as security boundaries** — The backend is repeatedly weaker than the UI. For every manager/admin-only screen, create matching backend role tests and route enforcement. *(Immediate)*

9. **Add per-endpoint rate limiting** — Auth endpoints: 10/min. File upload: separate limits. AI chat: token-based limits. *(Short-term)*

10. **Implement RBAC unit test matrix** — Create a permission matrix test validating every endpoint × every role to prevent regression. *(Immediate)*

11. **Re-evaluate privacy boundaries around customer identity data** — Feedback and support expose customer details too broadly. Minimize PII by role and feature. *(Short-term)*

12. **Add request/response audit logging for sensitive endpoints** — Password changes, role assignments, document deletions should log sanitized request payloads. *(Short-term)*

### Frontend

13. **Extract DocumentDetailPage into sub-components with context** — Replace 15+ prop drilling with React Context or a dedicated state container. *(Medium-term)*

14. **Add Sentry or similar error monitoring** — Error boundaries exist but don't send errors to a monitoring service. *(Short-term)*

15. **Implement token refresh for collaboration sessions** — Long editing sessions (>1hr) will fail silently. Add proactive token refresh. *(Short-term)*

16. **Fix session restore to be route-independent** — Restore session on app boot regardless of route, solve log noise at the monitoring layer. *(Immediate)*

### DevOps

17. **Pin all Docker base images to specific tags** — `python:3.11-slim` → `python:3.11.8-slim`, `node:20-alpine` → `node:20.11-alpine`, etc. *(Short-term)*

18. **Add `.dockerignore`** — Prevent `.env`, `.git`, `node_modules`, test files in images. *(Short-term)*

19. **Enforce HTTPS in production nginx** — SSL listener, HSTS header, HTTP→HTTPS redirect. *(Immediate)*

20. **Make WebSocket endpoint discovery a real runtime contract** — Choose one source of truth for WS URLs and remove the rest. *(Short-term)*

### Testing

21. **Replace stale "shape-only" tests with behavior tests** — Add integration tests for auth cookie persistence, tenant-scoped support/feedback/company access, published attachment immutability, and public feed/search contracts. *(Immediate)*

22. **Split monolithic modules** — Files like `companies.py`, `support_service.py`, `feedback.py`, and `models/__init__.py` have too much blast radius. Extract policy, query, serialization, and lifecycle concerns. *(Medium-term)*

---

## 5. Ideas

1. **Platform-level authorization-contract test suite** — Exercise every role against every sensitive endpoint with real tenant fixtures.
2. **Publish artifact manifest** — Record exactly which version, attachments, and audience state were released. Make all reader channels consume it.
3. **Internal admin/debug page** showing effective backend policy for a route or resource.
4. **Structured audit events for support-ticket reads**, not just writes.
5. **Consistent projection layer** for public search, sitemap, and feed generation.
6. **Treat support and feedback as first-class bounded contexts** with explicit ownership, not side-effects of documents.
7. **Tenant-scoped AI models** — Let tenants configure their own AI parameters (temperature, system prompt, allowed tools).
8. **Webhook system for document lifecycle events** (publish, archive, review request).
9. **Document comparison / diff view** — Side-by-side version comparison with TipTap content diff.
10. **Bulk operations API** — Batch endpoints for publish, archive, status change.
11. **API key authentication** for external integrations / CI/CD pipelines.
12. **Offline-capable editor** — Service workers + IndexedDB with sync-on-reconnect via Hocuspocus.
13. **Content workflow templates** — Custom review/approval workflows with configurable gates.
14. **Usage-based AI rate limiting** — Per-tenant AI token budgets to control LLM costs.
15. **Automated accessibility scanning in CI** — axe-core or pa11y with failure thresholds.

---

## 6. Helpful Notes

### What's Working Well

- **Row-level versioning with optimistic locking** — `version_number` on models prevents lost update conflicts.
- **Audit logging** — Most mutations log to `audit_logs` with user, action, and context.
- **Soft-delete pattern** — Documents use `is_active` / `deleted_at` instead of hard deletes.
- **Token refresh queue pattern** — Frontend correctly serializes concurrent token refresh calls to prevent race conditions.
- **HTML sanitization in frontend** — DOMPurify integration for rendering user content prevents stored XSS.
- **Security headers middleware** — Comprehensive headers (CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
- **RBAC role hierarchy** — SYSADMIN > ADMIN > MANAGER > EDITOR > VIEWER > CUSTOMER enforced in hierarchy check utility.
- **Session management** — IP tracking, device fingerprinting, concurrent session limits, inactivity timeouts.
- **CI pipeline breadth** — Tests, linting, type checking, security scanning, dependency review, migration safety, e2e tests.
- **Docker healthchecks** — All four services have health check configurations.
- **Access-policy abstractions** — `VisibilitySpec`, `DocumentAccessPolicy` and query specification objects are well-structured.
- **Self-registration privilege escalation is fixed** — Backend correctly ignores client-provided role/tenant fields.
- **Public changelog/search XSS sinks are hardened** — No longer a concern.

### Architecture Patterns

- **Tenant isolation via TenantContext** — Context variable for automatic tenant filtering in SQLAlchemy queries. Elegant but fragile if any code path forgets to set it.
- **Tool-augmented AI generation** — AI assistant executes registered tools with parameter validation and confirmation gates.
- **Hocuspocus integration** — Real-time collaborative editing via WebSocket with backend persistence adapter.

### Testing Notes

- `pytest backend/tests/test_auth.py -q` yields 5 failures and 16 passes. Failures are contract drift around registration and password validation.
- The existing tenant-isolation harness covers documents, reviews, and collaboration — but NOT companies, support, feedback, or search analytics (exactly where the worst issues are).
- Route-auth parity tests only verify "some auth dependency exists," not that the correct role or tenant restriction is enforced.
- `PasswordReset` doubles as the refresh-token store. Not wrong per se, but misleading name.

### Known Technical Debt (by design)

- SQLite used in development (PostgreSQL support ready)
- Ollama local LLM instead of cloud API (intentional for privacy/cost)
- In-memory caching (no Redis in dev)

---

## 7. Review by Feature

### F1. Authentication and Session Management

| Aspect | Rating | Notes |
|--------|--------|-------|
| Login / registration | ⭐⭐⭐⭐ | Proper password hashing, registration no longer trusts client role/tenant |
| JWT tokens | ⭐⭐⭐ | Short-lived access tokens, refresh flow exists; no rotation (M-10) |
| Session management | ⭐⭐⭐ | IP tracking, concurrent limits, inactivity timeout; timeout too long (M-13) |
| Refresh flow | ⭐ | **Cookie deleted on refresh** (C14), **public routes skip restore** (H-19) |
| Password security | ⭐⭐⭐ | Bcrypt, complexity validator; inconsistently applied (M-08) |

**Verdict:** Not production-ready. The session lifecycle is unreliable.

### F2. Document Authoring, Review, and Publish

| Aspect | Rating | Notes |
|--------|--------|-------|
| CRUD operations | ⭐⭐⭐⭐ | Solid with soft-delete, versioning |
| Review workflow | ⭐⭐⭐ | Reviews, approval, status transitions work |
| Versioning | ⭐⭐ | Admin enforcement missing (C7), viewers too permissive (H-17) |
| Publishing | ⭐⭐ | Force-publish bypass, AI publish lacks confirmation (H-15) |
| Published immutability | ⭐ | **Attachments leak through direct routes** (C6) |
| Bulk operations | ⭐⭐ | Per-document permissions skipped (M-04) |

**Verdict:** The lifecycle model exists but published content is not truly immutable.

### F3. Public Documentation Experience

| Aspect | Rating | Notes |
|--------|--------|-------|
| Rendering | ⭐⭐⭐⭐ | Clean, sanitized, no XSS fallback to drafts |
| Search | ⭐⭐ | Metadata-only despite claiming content search (M-26) |
| RSS/Sitemap | ⭐ | XXE injection (C8), wrong route in feed (M-27) |
| Attachment integrity | ⭐ | Published boundary bypassed (C6) |

**Verdict:** Close for basic browsing, not for trustworthy content publishing.

### F4. Customer Portal

| Aspect | Rating | Notes |
|--------|--------|-------|
| Document access | ⭐⭐⭐ | Company-scoped filtering works |
| Reading progress | ⭐⭐ | Access recheck wrong for company docs (H-20) |
| Feedback | ⭐⭐⭐ | Ratings/comments work |
| Categories | ⭐⭐ | Status mismatch (M-03) |
| Attachment download | ⭐ | **Ticket auth broken** (C3) |

**Verdict:** High risk. Functional on happy path, not reliable under permission changes or adversarial use.

### F5. Company and User Administration

| Aspect | Rating | Notes |
|--------|--------|-------|
| Listing | ⭐⭐⭐ | Scoped for non-system-admins |
| Detail/mutations | ⭐ | **Cross-tenant access** (C4) |
| Assignment workflows | ⭐⭐⭐ | Domain model expects tenant ownership |

**Verdict:** Not production-ready for multi-tenant administration.

### F6. Search and Analytics

| Aspect | Rating | Notes |
|--------|--------|-------|
| Search queries | ⭐⭐⭐⭐ | Good filtering, visibility, tenant scope |
| Analytics | ⭐ | **Globally exposed** (C15), no tenant/role restriction |

**Verdict:** Unsafe until analytics are scoped.

### F7. Feedback

| Aspect | Rating | Notes |
|--------|--------|-------|
| Customer submission | ⭐⭐⭐ | Works with statuses |
| Staff visibility | ⭐ | **PII leak, wrong access model** (C16) |
| Stats | ⭐ | Unscoped global counts |

**Verdict:** Not acceptable for customer trust or privacy-sensitive environments.

### F8. Support

| Aspect | Rating | Notes |
|--------|--------|-------|
| Customer flows | ⭐⭐⭐ | Submission, canned responses, service methods exist |
| Staff access | ⭐ | **Global cross-tenant access** (C5) — worst confidentiality issue |
| WS/REST parity | ⭐⭐ | WebSocket is slightly narrower than REST |

**Verdict:** Not safe for production.

### F9. Collaboration and Chat

| Aspect | Rating | Notes |
|--------|--------|-------|
| Real-time sync | ⭐⭐⭐⭐ | Hocuspocus CRDT-based, works well |
| Chat participant enforcement | ⭐ | **No validation** (H-01), cross-tenant addition (M-02) |
| Token management | ⭐⭐ | Issued without ownership check (H-03), no timeout (H-12) |
| URL contracts | ⭐ | Three competing assumptions (H-22), WS tokens in querystring (H-21) |

**Verdict:** Not ready without security and deployment cleanup.

### F10. AI Assistant

| Aspect | Rating | Notes |
|--------|--------|-------|
| Chat interface | ⭐⭐⭐ | Functional, tool-augmented |
| RAG / semantic search | ⭐ | **Zero tenant isolation** (C1) — unusable in multi-tenant |
| @mention references | ⭐ | **Authorization bypass** (C2) |
| Tool execution | ⭐⭐⭐ | Confirmation gates, parameter validation; error leak (H-06) |
| Rate limiting | ⭐⭐ | Exists but per-process only (H-05) |

**Verdict:** Potentially acceptable only after dedicated tool audit and tenant isolation fix.

### F11. Analytics & Dashboard

| Aspect | Rating | Notes |
|--------|--------|-------|
| View tracking | ⭐⭐⭐ | Page/document views tracked |
| Charts | ⭐⭐⭐ | Recharts integration |
| Data accuracy | ⭐⭐⭐ | Tenant-scoped queries |

**Verdict:** Functional.

---

## 8. Review by Flow

### Flow 1. Login → Refresh → Restore → Logout

```
Login → JWT + refresh cookie issued → Session created → SPA refreshes access token → Cookie deleted (!) → Public routes skip restore (!) → Logout
```

| Step | Status | Issues |
|------|--------|--------|
| Login | ⚠️ | No rate limiting (H-11), user enumeration timing (H-08) |
| JWT issuance | ✅ | Short-lived access tokens |
| Session creation | ✅ | IP + device tracked |
| Refresh | ❌ | **Cookie deleted** (C14), no rotation (M-10) |
| Session restore | ❌ | **Skipped on public routes** (H-19) |
| Logout | ✅ | Session revoked |

**Risk:** Random-seeming logout behavior, support churn, confusion about which session state is authoritative.

### Flow 2. Draft → Review → Publish → Public/Viewer/Portal Read

```
Create draft → Collaborative edit → Request review → Approve → Publish → Version
```

| Step | Status | Issues |
|------|--------|--------|
| Create draft | ✅ | Proper tenant assignment |
| Collaborative edit | ⚠️ | Token issued without access check (H-03) |
| Request review | ✅ | Notification to reviewers |
| Approval | ✅ | Status transitions correct |
| Publish | ❌ | Force-publish lacks admin check (C7), AI publish lacks confirmation (H-15) |
| Published reading | ❌ | **Attachment snapshot bypassed** (C6), direct routes serve live attachments |
| Version access | ⚠️ | Viewers can list versions (H-17) |

**Risk:** Document appears published and stable while still leaking post-publish changes.

### Flow 3. Company Admin → Company Detail → Users → Documents

```
Admin lists companies → Selects company → Views users → Manages documents → Audience decisions
```

| Step | Status | Issues |
|------|--------|--------|
| List companies | ✅ | Scoped for non-system-admin |
| Company detail | ❌ | **Cross-tenant access** (C4) |
| Company users | ❌ | **Cross-tenant access** (C4) |
| Company documents | ❌ | **Cross-tenant access** (C4) |

**Risk:** Direct cross-tenant data exposure and unauthorized mutations.

### Flow 4. Customer Read → Download → Progress → Feedback → Support

```
Customer logs in → Views company content → Downloads attachment → Feedback → Support ticket
```

| Step | Status | Issues |
|------|--------|--------|
| Login | ✅ | Company validation enforced |
| Company content | ✅ | Scoped correctly |
| Attachment download | ❌ | **Ticket auth broken** (C3) |
| Reading progress | ⚠️ | Recheck wrong for company docs (H-20) |
| Feedback | ✅ | Works, but staff side leaks PII (C16) |
| Support | ✅ | Works, but staff side globally exposed (C5) |

**Risk:** Trust-breaking privacy incidents across customer-facing and staff-facing sides.

### Flow 5. AI Assistant Interaction

```
User sends message → Context built (@mentions) → Tools selected → Tool executed → Response
```

| Step | Status | Issues |
|------|--------|--------|
| Message received | ✅ | Validated, tenant context set |
| @mention resolution | ❌ | **No authorization check** (C2) |
| Tool selection | ✅ | Registry-based with role filtering |
| Semantic search | ❌ | **No tenant isolation** (C1) |
| Tool execution | ⚠️ | Error messages leak internals (H-06) |
| Response generation | ⚠️ | No quality validation of LLM output (M-17) |

### Flow 6. Search → Analytics

| Step | Status | Issues |
|------|--------|--------|
| Search results | ✅ | Good filtering, visibility, tenant scope |
| Search analytics | ❌ | **Globally exposed** (C15) |

### Flow 7. Collaboration Token → WS Connect → Session

| Step | Status | Issues |
|------|--------|--------|
| Token issuance | ⚠️ | No ownership check (H-03) |
| WS connect | ⚠️ | Bearer in query string (H-21), URL contract drift (H-22) |
| Session activity | ✅ | Tracked |
| Reconnect | ⚠️ | Token refresh missing (M-21) |

### Flow 8. CI/CD Pipeline

```
PR → Lint + Tests → Security Scans → Merge → Staging → Production
```

| Step | Status | Issues |
|------|--------|--------|
| PR checks | ✅ | Comprehensive |
| Security scans | ❌ | **Failures don't block** (C10) |
| Merge | ⚠️ | Can merge with scan failures |
| Staging | ⚠️ | Can be skipped |
| Production | ❌ | **Can skip tests** (C9) |

---

## 9. Review by User Type / Role

### System Admin

| Capability | Status | Risk |
|-----------|--------|------|
| Platform management | ✅ | Working correctly |
| Tenant management | ✅ | Proper isolation |
| **Risk** | ⚠️ | Lower roles are often treated too similarly in sensitive services |

### Admin

| Capability | Status | Risk |
|-----------|--------|------|
| Document management | ⚠️ | Force-publish accessible to non-admins (C7) |
| Company management | ❌ | **Cross-tenant access** (C4) |
| Support access | ❌ | Backend grants near-global access (C5) |
| Version management | ⚠️ | Admin actions not admin-restricted |

### Manager

| Capability | Status | Risk |
|-----------|--------|------|
| Reviews/publishing | ✅ | Review flow works |
| Team oversight | ✅ | Can view team activity |
| Support | ⚠️ | Gets near-agent-level access to all tickets |
| Feedback | ⚠️ | Sees customer PII from contributor-based rule (C16) |

### Editor

| Capability | Status | Risk |
|-----------|--------|------|
| Document editing | ✅ | Core workflow solid |
| Collaboration | ⚠️ | Token without proper access check |
| Publishing | ❌ | Can force-publish via API (C7) |
| Support tickets | ❌ | Inherits global access via `require_internal_user` (C5) |
| AI assistant | ⚠️ | @mention exposes unauthorized docs (C2) |

### Viewer

| Capability | Status | Risk |
|-----------|--------|------|
| Read documents | ✅ | Works |
| Version access | ⚠️ | Can list versions (H-17) |
| Attachments | ⚠️ | Can read without doc access (H-02) |
| Search analytics | ❌ | Can see global analytics (C15) |

### Customer

| Capability | Status | Risk |
|-----------|--------|------|
| Company content | ✅ | Scoped correctly |
| Attachment download | ❌ | Ticket auth broken (C3) |
| Reading progress | ⚠️ | Access recheck wrong (H-20) |
| Feedback | ✅ | Works |
| AI assistant | ⚠️ | Can invoke semantic search (H-04) |
| Chat | ⚠️ | Can read any chat (H-01) |

### Anonymous / Public

| Capability | Status | Risk |
|-----------|--------|------|
| Public documents | ✅ | Filtered by visibility |
| Sitemap/RSS | ❌ | XXE injection vector (C8), wrong route (M-27) |
| Collab health | ⚠️ | Exposes document IDs (M-23) |

### Role-System Verdict

The role set is not inherently bad. The enforcement model is bad because it is inconsistent by feature. UI guards are frequently stronger than backend guards. Tenant scope is treated as optional where it should be mandatory. Ownership is often inferred indirectly instead of modeled explicitly.

---

## 10. Review by Engineering Quality

### Code Quality and Maintainability

| Metric | Rating | Notes |
|--------|--------|-------|
| Code organization | ⭐⭐⭐⭐ | Clean separation: routes, services, models, middleware |
| Naming conventions | ⭐⭐⭐⭐ | Consistent Python/TypeScript naming |
| DRY principle | ⭐⭐⭐ | Some duplication in route permission checks |
| Type safety | ⭐⭐⭐ | TypeScript strict mode, Python type hints; mypy not enforced |
| Error handling | ⭐⭐⭐ | Custom exceptions, error boundaries; AI tool errors leak (H-06) |

**Weakness:** The repository is in a half-migrated state. Some areas use strong abstractions (query specs, access policies) while others bypass them. Mixed architecture increases cognitive load and hides risk.

### Separation of Concerns

| Metric | Rating | Notes |
|--------|--------|-------|
| Domain separation | ⭐⭐⭐ | Several domains attempt API/service/policy separation |
| Module blast radius | ⭐⭐ | Large modules combine transport, authorization, business rules, query assembly |

**Weakness:** Small feature changes have large blast radii because policy, data access, and serialization aren't separated.

### Authorization and Security Engineering

| Metric | Rating | Notes |
|--------|--------|-------|
| Auth infrastructure | ⭐⭐⭐⭐ | Permission helpers, tenant concepts, policy objects exist |
| Auth enforcement | ⭐⭐ | Critical features ignore shared primitives and hand-roll checks |
| Transport security | ⭐ | No HTTPS enforcement (C11) |
| Secret management | ⭐⭐ | Validation exists but defaults insecure (C12) |

**Verdict:** The biggest security failures are not from missing infrastructure but from uneven adoption and local shortcuts.

### Testing

| Metric | Rating | Notes |
|--------|--------|-------|
| Unit test coverage | ⭐⭐⭐ | Core services tested |
| Integration tests | ⭐⭐⭐ | API routes have coverage |
| E2E tests | ⭐⭐⭐ | Cypress/Playwright exist |
| RBAC test matrix | ⭐ | No systematic endpoint × role test |
| Security tests | ⭐⭐ | Some auth tests; no injection/tenant isolation tests |
| Test currency | ⭐⭐ | 5 auth test failures, stale portal expectations (H-23) |

**Verdict:** The test suite gives too much false confidence and too little actual protection.

### Database Design

| Metric | Rating | Notes |
|--------|--------|-------|
| Schema | ⭐⭐⭐ | Reasonable normalization, soft-delete, versioning |
| Indexes | ⭐⭐ | Missing 12+ critical indexes (H-13) |
| Constraints | ⭐⭐ | Missing unique constraints, nullable tenant_id (C13) |
| Migrations | ⭐⭐⭐⭐ | Alembic managed, CI safety check |

### API Design

| Metric | Rating | Notes |
|--------|--------|-------|
| RESTful conventions | ⭐⭐⭐⭐ | Proper HTTP methods, status codes |
| Input validation | ⭐⭐ | Pydantic used but gaps (sort_by, base_url) |
| Response consistency | ⭐⭐⭐ | Standard envelope pattern |
| Pagination | ⭐⭐⭐ | Present on most list endpoints; missing on chat (M-05) |
| Frontend/Backend contract | ⭐⭐ | Several contracts drift (registration types, RSS routes, collaboration URLs) |

### DevOps & CI/CD

| Metric | Rating | Notes |
|--------|--------|-------|
| CI breadth | ⭐⭐⭐⭐ | Tests, lint, types, security, migration safety |
| CI enforcement | ⭐ | Security failures don't block (C10), tests skippable (C9) |
| Docker security | ⭐⭐⭐ | Non-root users, multi-stage builds |
| Monitoring | ⭐⭐ | Health checks present; no APM or error tracking |

### Frontend Quality

| Metric | Rating | Notes |
|--------|--------|-------|
| Component architecture | ⭐⭐⭐ | Reasonable; some prop drilling (M-20) |
| State management | ⭐⭐⭐ | Context + hooks |
| Accessibility | ⭐⭐⭐ | Skip nav, ARIA roles, focus management; gaps (L-08) |
| Performance | ⭐⭐⭐ | Memoization, lazy loading, code splitting |
| Error resilience | ⭐⭐⭐ | Error boundaries, loading states; no monitoring (L-07) |

### Engineering Verdict

This is not a bad codebase in the sense of random spaghetti. It is worse in a more subtle way: it contains enough good structure to look safer than it is. The core problem is **false confidence** created by partial architecture, partial policy reuse, and stale tests. Reviewers cannot trust patterns to hold across modules.

---

## 11. Priority Action Plan

### 🔴 IMMEDIATE (Block Production Deployment)

| # | Action | Issues Addressed | Effort |
|---|--------|-----------------|--------|
| 1 | Fix RAG tenant isolation in ChromaDB | C1 | Medium |
| 2 | Add authorization check to @mention resolution | C2 | Small |
| 3 | Fix attachment download-ticket HMAC verification | C3 | Small |
| 4 | Apply tenant-scope to all company-management endpoints | C4 | Medium |
| 5 | Lock support REST/service access to correct roles + tenants | C5 | Medium |
| 6 | Centralize published-attachment resolution | C6 | Medium |
| 7 | Replace `get_current_active_user` → `require_role` on 3 version endpoints | C7 | Small |
| 8 | Validate/sanitize `base_url` in sitemap.xml and feed.xml | C8 | Small |
| 9 | Remove `skip_tests` from CD workflow | C9 | Small |
| 10 | Remove `continue-on-error` from secret detection CI steps | C10 | Small |
| 11 | Set `Document.tenant_id` to `nullable=False` + migration | C13 | Medium |
| 12 | Fix refresh-cookie persistence | C14 | Small |
| 13 | Restrict search analytics by role and tenant | C15 | Small |
| 14 | Fix feedback PII exposure and access model | C16 | Medium |
| 15 | Add chat participant validation to all chat endpoints | H-01 | Medium |
| 16 | Add document access validation to attachment endpoints | H-02 | Small |

### 🟠 HIGH (Pre-Production)

| # | Action | Issues Addressed | Effort |
|---|--------|-----------------|--------|
| 1 | Configure HTTPS in nginx | C11 | Medium |
| 2 | Move secrets to env vars / Docker secrets | C12 | Medium |
| 3 | Add collab token ownership validation | H-03 | Small |
| 4 | Add RBAC gate to SemanticSearchTool | H-04 | Small |
| 5 | Move rate limiting to Redis | H-05 | Medium |
| 6 | Sanitize tool error messages | H-06 | Small |
| 7 | Apply rate limits to auth endpoints (10/min) | H-11 | Small |
| 8 | Gate demo credentials behind `APP_ENV` | H-09 | Small |
| 9 | Fix path traversal in chat file upload | H-10 | Small |
| 10 | Add confirmation gate to publish tool | H-15 | Small |
| 11 | Add missing database indexes (12+) | H-13 | Medium |
| 12 | Fix SPA session restore on public routes | H-19 | Small |
| 13 | Fix portal reading-progress entitlement check | H-20 | Small |
| 14 | Replace WS query-token auth with safer mechanism | H-21 | Medium |
| 15 | Unify WebSocket endpoint contract | H-22 | Small |
| 16 | Rewrite stale auth/portal/tenant-scope tests | H-23 | Large |

### 🟡 MEDIUM (Post-Launch Sprint)

| # | Action | Issues Addressed | Effort |
|---|--------|-----------------|--------|
| 1 | Add `sort_by` column whitelist | M-01 | Small |
| 2 | Fix cross-tenant user addition in chat | M-02 | Small |
| 3 | Fix public categories status mismatch | M-03 | Small |
| 4 | Add per-document permission to bulk update | M-04 | Medium |
| 5 | Implement refresh token rotation | M-10 | Medium |
| 6 | Reduce session inactivity to 7 days | M-13 | Small |
| 7 | Add timing-safe comparison for password reset | H-08 | Small |
| 8 | Fix CSRF middleware production bypass | H-07 | Small |
| 9 | Build RBAC unit test matrix | — | Large |
| 10 | Add pagination to chat list | M-05 | Small |
| 11 | Fix RSS feed route | M-27 | Small |
| 12 | Fix public search claims vs behavior | M-26 | Medium |
| 13 | Align frontend registration types | M-28 | Small |
| 14 | Minimize PII in feedback/support by role | M-09, C16 | Small |

### 🟢 LOW (Backlog)

| # | Action | Issues Addressed | Effort |
|---|--------|-----------------|--------|
| 1 | Pin Docker base image tags | L-09 | Small |
| 2 | Add `.dockerignore` | L-10 | Small |
| 3 | Collab-server cache eviction | L-11 | Medium |
| 4 | Add `jti` claim to collaboration tokens | L-04 | Small |
| 5 | Configure axios timeout | L-05 | Small |
| 6 | Add error monitoring (Sentry) | L-07 | Medium |
| 7 | Fix breadcrumb `aria-current` | L-08 | Small |
| 8 | Resolve duplicate platform columns | H-14 | Large |
| 9 | Policy-debug tooling for devs | — | Medium |
| 10 | Split monolithic modules | M-29 | Large |

---

## 12. Top 10 Highest-Value Fixes

These deliver **maximum security and stability improvement per unit of effort**:

| Rank | Fix | Severity | Effort | Impact |
|------|-----|----------|--------|--------|
| **1** | Add tenant filter to ChromaDB vector queries | CRITICAL | 2-4 hrs | Eliminates cross-tenant data leakage via AI |
| **2** | Fix attachment ticket HMAC verification | CRITICAL | 1-2 hrs | Closes direct download-path forgery |
| **3** | Replace `get_current_active_user` → `require_role` on 3 version endpoints | CRITICAL | 30 min | Closes privilege escalation |
| **4** | Validate `base_url` in sitemap.xml / feed.xml | CRITICAL | 30 min | Eliminates XXE/SSRF |
| **5** | Apply tenant-scope to company-management endpoints | CRITICAL | 2-3 hrs | Removes cross-tenant admin access |
| **6** | Lock support authorization to correct roles + tenants | CRITICAL | 3-4 hrs | Closes broadest confidentiality breach |
| **7** | Add authorization check to @mention resolution | CRITICAL | 1-2 hrs | Prevents AI-mediated doc access bypass |
| **8** | Remove `skip_tests` from CD + `continue-on-error` from security scans | CRITICAL | 15 min | Enforces quality and secret gates |
| **9** | Fix refresh-cookie persistence + session restore on public routes | HIGH | 2-3 hrs | Stabilizes user session lifecycle |
| **10** | Gate demo credentials behind environment check + restrict search analytics by role | HIGH | 30 min | Prevents credential and analytics exposure |

**Total estimated effort for top 10: ~14-20 hours of focused work, eliminating 13 CRITICAL and 4 HIGH issues.**

---

## 13. Risk Heatmap

```
                    LOW IMPACT          MEDIUM IMPACT        HIGH IMPACT
                ┌─────────────────┬──────────────────┬──────────────────┐
   HIGH         │                 │ • Auth rate limit │ • RAG tenant     │
   LIKELIHOOD   │                 │   bypass (H-11)  │   leak (C1)      │
                │                 │ • Worker bypass  │ • @mention inject│
                │                 │   (H-05)         │   (C2)           │
                │                 │ • Demo creds     │ • Skip tests CD  │
                │                 │   (H-09)         │   (C9)           │
                │                 │ • Cookie deleted │ • Scan !block    │
                │                 │   (C14)          │   (C10)          │
                ├─────────────────┼──────────────────┼──────────────────┤
   MEDIUM       │ • No pagination │ • Chat no partic │ • Attachment     │
   LIKELIHOOD   │   (M-05)        │   check (H-01)   │   ticket (C3)    │
                │ • Sort_by       │ • Attachment no  │ • Company cross- │
                │   (M-01)        │   access (H-02)  │   tenant (C4)    │
                │ • Session 30d   │ • CSRF bypass    │ • Support cross- │
                │   (M-13)        │   (H-07)         │   tenant (C5)    │
                │                 │ • Token no rotate│ • Version admin  │
                │                 │   (M-10)         │   bypass (C7)    │
                │                 │ • WS tokens in   │ • XXE sitemap    │
                │                 │   query (H-21)   │   (C8)           │
                │                 │                  │ • No HTTPS (C11) │
                │                 │                  │ • Publish attach  │
                │                 │                  │   bypass (C6)    │
                ├─────────────────┼──────────────────┼──────────────────┤
   LOW          │ • aria-current  │ • Error info leak│ • Hardcoded      │
   LIKELIHOOD   │   (L-08)        │   (H-06)         │   secrets (C12)  │
                │ • Docker pin    │ • Path traversal │ • tenant_id null │
                │   (L-09)        │   (H-10)         │   (C13)          │
                │ • Cache evict   │ • Cross-tenant   │ • Feedback PII   │
                │   (L-11)        │   chat (M-02)    │   (C16)          │
                │                 │ • Stale tests    │ • Search analytics│
                │                 │   (H-23)         │   (C15)          │
                └─────────────────┴──────────────────┴──────────────────┘
```

### By Area

| Area | Risk | Key Issues |
|------|------|------------|
| AI Assistant | 🔴 Critical | C1, C2, H-04, H-05, H-06, H-15 |
| Attachments | 🔴 Critical | C3, C6, H-02 |
| Company Management | 🔴 Critical | C4 |
| Support | 🔴 Critical | C5 |
| CI/CD Pipeline | 🔴 Critical | C9, C10 |
| Infrastructure | 🔴 Critical | C11, C12, C13 |
| Version Management | 🔴 Critical | C7, H-17 |
| Public Surface | 🔴 Critical | C8, M-26, M-27 |
| Authentication | 🟠 High | C14, H-08, H-11, H-19 |
| Search/Analytics | 🟠 High | C15 |
| Feedback | 🟠 High | C16 |
| Customer Portal | 🟠 High | H-20, M-03 |
| Collaboration / Chat | 🟠 High | H-01, H-03, H-21, H-22, M-02 |
| Testing | 🟠 High | H-23, stale tests |
| Frontend | 🟡 Medium | H-09, M-18, M-19, M-20 |
| Database | 🟡 Medium | H-13, H-14 |

---

## 14. Fragile & Strong Modules

### 🔴 Fragile Modules (High Risk, Need Attention)

| Module | Why Fragile |
|--------|-------------|
| `backend/app/services/ai/` (entire subsystem) | Zero tenant isolation in vector store, @mention injection, error leakage. The AI subsystem is the single most dangerous component. |
| `backend/app/api/management/attachments.py` | Broken HMAC ticket verification and publish-boundary leakage |
| `backend/app/api/management/companies.py` | Cross-tenant detail and mutation exposure |
| `backend/app/api/management/support.py` + `support_service.py` | REST/service authorization far too broad, global cross-tenant access |
| `backend/app/api/management/feedback.py` | Over-broad staff access and excessive PII exposure |
| `backend/app/api/management/search.py` | Analytics globally exposed without role/tenant restriction |
| `backend/app/routes/versions.py` | Admin enforcement missing, viewers too permissive |
| `backend/app/routes/chat.py` | No participant validation, cross-tenant addition, path traversal, no pagination |
| `backend/app/routes/public.py` | XXE vector in sitemap/feed, status mismatch in categories |
| `backend/app/middleware/rate_limit.py` | Per-process counters, auth exemption, e2e bypass header |
| `backend/app/api/portal/documents.py` + `portal_queries.py` | Wrong entitlement recheck, attachment snapshot bypass |
| `frontend/src/lib/auth.tsx` + `httpClient.ts` | Refresh cookie deleted, public route skip, contract drift |
| `frontend/src/lib/useCollaboration.ts` + `useChatSocket.ts` | URL contract drift, bearer in query string |
| `.github/workflows/cd.yml` | `skip_tests`, skippable staging |
| `.github/workflows/security.yml` | All scans `continue-on-error` |
| `backend/tests/test_auth.py` + `test_route_auth_parity.py` | Stale, shallow — defend old behavior not current |

### 🟢 Strong Modules (Well-Built, Low Risk)

| Module | Why Strong |
|--------|------------|
| `backend/app/security.py` | Central auth gate, session checking, tenant injection |
| `backend/app/dependencies/permissions.py` | Permission helpers, role hierarchy |
| `backend/app/application/policies/access_policies.py` | Clean access-policy abstractions |
| `backend/app/domain/specifications/queries.py` | Well-structured query specifications |
| `backend/app/middleware/security_headers.py` | Comprehensive headers with proper prod/dev differentiation |
| `backend/app/auth_context/token_service.py` | Clean JWT generation with proper claims |
| `backend/app/models/models.py` (except tenant_id nullable) | Good schema with versioning, soft-delete, audit trails, row locking |
| `backend/alembic/` | Clean migration history, CI safety checks |
| `frontend/src/hooks/` | Well-structured custom hooks with cleanup and memoization |
| `frontend/src/components/ErrorBoundary/` | Proper error boundaries with fallback UI |
| `frontend/nginx.conf` (except HTTPS) | Good headers, gzip, caching, SPA fallback |
| `frontend/src/pages/public/PublicChangelogPage.tsx` | Clean, sanitized public rendering |
| `frontend/src/pages/public/PublicSearchPage.tsx` | Well-structured search UI |
| `collab-server/src/server/collabServerApp.ts` | Well-structured Hocuspocus integration |

---

## 15. Top Weaknesses & Risks

### 1. Authorization Enforcement is Inconsistent
The RBAC system is well-designed but applied unevenly. Some endpoints check `require_role()`, others use `get_current_active_user` (any authenticated user). There is no automated test matrix. The AI assistant bypasses normal authorization entirely through @mention and semantic search.

### 2. Multi-Tenancy Has Gaps
Tenant isolation depends on `TenantContext` being correctly set on every request. `Document.tenant_id` is nullable. ChromaDB has no tenant filtering. Company management is partially unscoped. Chat allows cross-tenant user addition. Support tickets are globally exposed. Any single gap creates a data breach.

### 3. AI Subsystem is a Backdoor
The AI assistant bypasses normal authorization — @mention resolves documents without permission checks, semantic search queries the global vector store, and tool errors leak internal schema. This is essentially an unprotected secondary API.

### 4. Security Pipeline is Decorative
CI runs security scans but none block merges or deployments. Combined with skippable tests in CD, the pipeline creates a false sense of security while providing zero enforcement.

### 5. No HTTPS Enforcement
Sensitive data (auth tokens, documents, PII) travels in plaintext. This is the most fundamental transport security failure.

### 6. Published Content is Semi-Immutable
The publish model partially works — some paths use cutoff timestamps while others serve live attachment state. Semi-immutability is worse than either fully immutable or fully live because it looks safe while leaking.

### 7. Session Lifecycle is Broken
The refresh flow deletes its own cookie. Public routes skip session restore. Users experience random logouts that are expensive to diagnose.

### 8. Tests Create False Confidence
The test suite has stale assertions, shallow checks, and missing coverage on the exact surfaces (companies, support, feedback, analytics, AI tools) where the worst bugs exist.

---

## 16. Conclusion

This platform demonstrates **solid architectural thinking** — the separation of concerns, multi-tenancy patterns, RBAC design, versioning, audit logging, and collaboration integration all reflect thoughtful planning. The technology choices are appropriate for the problem domain.

However, the implementation has significant gaps between **design intent and actual enforcement**. The worst issues are not in the narrow happy path of internal document CRUD (which is materially stronger). They are in the surrounding surfaces: AI assistant, attachments, company management, support, feedback, analytics, chat, collaboration, and CI/CD infrastructure.

The 16 CRITICAL issues span four themes:
1. **Tenant isolation failures** — ChromaDB, company endpoints, support tickets, analytics, feedback
2. **Authorization bypass** — @mention injection, version endpoint privilege escalation, attachment ticket forgery
3. **Infrastructure gaps** — No HTTPS, hardcoded secrets, decorative security pipeline, skippable tests
4. **Data integrity** — Published attachment leakage, nullable tenant_id, cookie self-destruction

**The top 10 fixes (estimated 14-20 hours) would eliminate 13 CRITICAL and 4 HIGH issues**, dramatically improving the security posture.

**Production readiness: NOT READY.** The CRITICAL findings must be resolved before any production deployment with real user data.

**Post-fix projection: 8/10.** Once the CRITICAL and HIGH issues are resolved, this platform would be a solid, production-ready CMS with excellent feature depth and reasonable security posture.

If I were improving this project next, I would start with **authorization and release-integrity boundaries**: fix RAG tenant isolation, fix attachment HMAC auth, lock company/support/feedback/analytics scope down by tenant and role, repair the refresh/session lifecycle, make published attachments truly immutable, and enforce the security pipeline.

---

*End of combined audit. All findings are based on static code analysis across two independent deep reviews. Runtime testing may reveal additional issues.*
