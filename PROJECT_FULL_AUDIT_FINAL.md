# PROJECT FULL AUDIT — FINAL AGGREGATED REPORT

**Original Audit Date:** 2025-03-23  
**Remediation Update:** 2026-03-26  
**Auditor:** Senior Architect / Security Auditor  
**Project:** Multi-Tenant Document Management Platform  
**Stack:** FastAPI 0.115 + React 18 + TypeScript 5.3 + SQLite WAL (×3) + Hocuspocus/Yjs CRDT + Ollama AI + ChromaDB  
**Sources:** Feature-by-Feature Review (131 findings), Flow-by-Flow Review (58 findings), Role & Permission Audit (21 findings), Engineering & Architecture Review (12 quality findings + 6 architectural weaknesses + 7 maintainability risks)  
**Methodology:** Aggressive, paranoid, source-level verification. Every finding traced to exact files and lines. UI restrictions not accepted as security unless backend enforces independently. No feature assumed correct because the UI exists.

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Scope & Methodology](#2-scope--methodology)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Aggregate Finding Statistics](#4-aggregate-finding-statistics)
5. [Critical Findings](#5-critical-findings)
6. [High-Severity Findings](#6-high-severity-findings)
7. [Medium-Severity Findings](#7-medium-severity-findings)
8. [Low & Informational Findings](#8-low--informational-findings)
9. [Authentication & Session Management](#9-authentication--session-management)
10. [Authorization & RBAC](#10-authorization--rbac)
11. [Tenant Isolation](#11-tenant-isolation)
12. [Document Lifecycle & State Machine](#12-document-lifecycle--state-machine)
13. [Collaboration & Real-Time](#13-collaboration--real-time)
14. [AI Assistant & RAG](#14-ai-assistant--rag)
15. [File Upload & Attachments](#15-file-upload--attachments)
16. [Customer Portal & Public Surface](#16-customer-portal--public-surface)
17. [Engineering Quality & Architecture](#17-engineering-quality--architecture)
18. [Remediation Priority Matrix](#18-remediation-priority-matrix)
19. [Final Verdict](#19-final-verdict)

---

## 1. EXECUTIVE SUMMARY

### Overall Production Readiness: READY FOR CONTROLLED PRODUCTION

The original 2025 audit verdict of "NOT READY" was accurate for the codebase at that time. It is no longer the current state. The findings inventory in this report has now been remediated and regression-tested across the backend, frontend, and collaboration server.

### 2026 Remediation Update
- Original finding inventory preserved below as the historical baseline.
- Current audit status: all tracked `C-*`, `H-*`, `M-*`, `L-*`, `I-*`, `AW-*`, and `EQ-*` items from this report are closed.
- Verification snapshot:
  - Backend: `1583 passed, 2 skipped`
  - Frontend: `84 files passed, 311 tests passed`
  - Collab server: `10 suites passed, 60 tests passed`

### What Changed Materially
- Core trust boundaries are now enforced consistently: token types are validated, route guards are centralized, tenant and document checks are explicit, and session invalidation gaps were closed.
- Collaboration no longer carries the original silent data-loss profile: reconnect/token-refresh behavior, auth verification, realtime notifications, and websocket parity were tightened.
- Public and portal surfaces were hardened: sitemap/XML handling, CSP/security headers, public rate limiting, sanitization, signed download paths, and attachment controls are wired into the paths that actually execute.
- User, support, and recovery workflows are materially more complete: invitation handling, audit logging, email verification, force-reset capability, role-change notifications, support notifications, and attachment support were added.
- Backend architecture is materially healthier: the model monolith was split, direct service instantiation was removed from callers, `DocumentService` was reduced, request tracing now crosses services, and error-boundary rules are enforced in CI.

### Original Systemic Failures (Historical Baseline)
- **State machines exist but are bypassed** — archive/restore, force-publish, direct status updates all circumvent transition rules
- **Session/token lifecycle has gaps at the most security-critical moments** — role demotion, password reset, user deletion all fail to invalidate sessions
- **Tenant isolation is trust-the-issuer** — the collaboration server has zero independent verification; if backend issues a bad token, there's no safety net
- **Sanitization is applied inconsistently** — REST sanitizes, WebSocket doesn't; feedback unsanitized, tickets sanitized; custom sanitizer vs DOMPurify vs bleach
- **Race conditions at every concurrent-write boundary** — invitation acceptance, review approval, auth login, all unprotected
- **Email infrastructure is unfinished** — 3 features silently break when email isn't configured (which is the default)

### Current Rating
- Overall project rating: `8.6/10`
- Frontend: `8.9/10`
- Backend: `8.3/10`
- Architecture trajectory: positive and now governed by ADRs plus architecture checks

### Residual Watchlist
- This update does not change the original audit scope limits: third-party library internals, network perimeter controls, CI/CD security, and true load/performance testing still need their own reviews.
- Non-blocking cleanup remains: legacy deprecation warnings in tests, some large services still worth further decomposition, and normal release hardening for rollout and migrations.

### Headline Numbers

| Metric | Baseline Audit | Current Status |
|--------|----------------|----------------|
| Raw findings across all reviews | ~220 | Historical baseline retained |
| Deduplicated unique findings | 148 | 148 addressed |
| Open CRITICAL findings from this audit | 18 | 0 |
| Open HIGH findings from this audit | 32 | 0 |
| Open MEDIUM findings from this audit | 52 | 0 |
| Open LOW findings from this audit | 34 | 0 |
| Open INFO findings from this audit | 12 | 0 |
| Architectural weaknesses still open | 6 | 0 |
| Engineering quality findings still open | 8 | 0 |

---

## 2. SCOPE & METHODOLOGY

### What Was Audited
- **Backend**: All FastAPI routes (~250 endpoints), all services, all domain aggregates, middleware chain, auth context, database models
- **Frontend**: All React components (~295 source files), routing guards, API client, state management, form validation
- **Collaboration Server**: Hocuspocus Node.js server, auth flow, persistence layer, connection registry
- **AI Assistant**: Engine, RAG tools, ChromaDB integration, tool registry, prompt construction
- **Infrastructure**: Docker Compose (dev + prod), Alembic migrations, config/secrets handling

### What Was NOT Audited
- Third-party library source code (only configuration and usage reviewed)
- Network infrastructure and firewall rules
- CI/CD pipeline security (beyond config review)
- Performance under load (only theoretical analysis)

### Methodology
1. **Feature-by-Feature Review**: Examined 10 feature areas independently, tracing each from frontend UI through API to database
2. **Flow-by-Flow Review**: Traced 11 complete end-to-end user journeys, identifying cross-layer inconsistencies
3. **Role & Permission Audit**: Scanned all ~250 endpoints for authorization gaps, compared frontend guards vs backend enforcement
4. **Engineering & Architecture Review**: Evaluated code quality, patterns, maintainability, and testability

### Deduplication Approach
Many findings appear in multiple source reviews (e.g., state machine bypass found in Feature Review, Flow Review, AND Role Audit). Each unique finding is counted once here, at its highest severity, with cross-references to all source documents.

---

## 3. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React 18)                │
│   Vite 5 · TypeScript 5.3 · TailwindCSS · Zustand  │
│   React Query · React Router 6 · Zod · TipTap      │
└──────────────┬──────────────────┬───────────────────┘
               │ REST/SSE         │ WebSocket
               ▼                  ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  Backend (FastAPI)   │  │  Collab Server (Node.js) │
│  SQLAlchemy 2.0      │  │  Hocuspocus + Yjs CRDT   │
│  python-jose + bcrypt│  │  Redis pub/sub            │
│  3× SQLite WAL       │  │  JWT auth (shared secret) │
│  Pydantic BaseSettings│  └──────────┬───────────────┘
│  bleach sanitization │              │ HTTP (state R/W)
│  Alembic migrations  │◄─────────────┘
└──────┬──────┬────────┘
       │      │
       ▼      ▼
┌───────┐  ┌───────┐  ┌──────────┐
│Core DB│  │Chat DB│  │Analytics │
│ 30+   │  │ 7     │  │ 4 tables │
│tables │  │tables │  │          │
└───────┘  └───────┘  └──────────┘
              │
              ▼
       ┌─────────────┐
       │  Ollama LLM  │
       │ llama3.1:8b  │
       │ + ChromaDB   │
       └─────────────┘
```

### Key Architecture Decisions
Current state update (2026-03-26):
- Backend governance is now context-first, ADR-documented, and CI-enforced.
- Shared auth, download, and collaboration flows replaced several parallel local implementations.
- Collaboration now uses explicit token validation, backend verification, signed invalidation, and cross-service trace propagation.
- Document, review, invitation, and support lifecycle paths are validated instead of relying on ad-hoc state mutation.
- **3 competing backend patterns**: DDD (domain aggregates) used ~10%, CQRS (command/query bus) used ~20%, direct route→service used ~70%
- **Hybrid frontend**: Layer-based top-level with feature-based modules for collaboration, reviews, chat, assistant
- **Trust model**: Collab server trusts backend JWT completely — no independent tenant verification
- **State management**: Explicit state machines for documents and reviews, but routinely bypassed by service code

---

## 4. AGGREGATE FINDING STATISTICS

### Current Closure Snapshot

| Metric | Baseline Audit | Current Status (2026-03-26) |
|--------|----------------|-----------------------------|
| Deduplicated unique findings | 148 | 148 addressed |
| Open CRITICAL findings from this audit | 18 | 0 |
| Open HIGH findings from this audit | 32 | 0 |
| Open MEDIUM findings from this audit | 52 | 0 |
| Open LOW findings from this audit | 34 | 0 |
| Open INFO findings from this audit | 12 | 0 |
| Architectural weaknesses still open | 6 | 0 |
| Engineering quality findings still open | 8 | 0 |

### Verification Snapshot

| Surface | Latest Result | Notes |
|---------|---------------|-------|
| Backend | `1583 passed, 2 skipped` | Full `pytest -q` sweep after remediation |
| Frontend | `84 files passed, 311 tests passed` | Full `npx vitest run` sweep after remediation |
| Collab server | `10 suites passed, 60 tests passed` | Full `npm test -- --runInBand` sweep after remediation |

### Closure by Audit Group

| Group | Original Count | Status |
|-------|----------------|--------|
| Critical (`C-*`) | 18 | Closed |
| High (`H-*`) | 32 | Closed |
| Medium (`M-*`) | 52 | Closed |
| Low (`L-*`) | 34 | Closed |
| Informational (`I-*`) | 12 | Closed |
| Architectural weaknesses (`AW-*`) | 6 | Closed |
| Engineering quality (`EQ-*`) | 8 | Closed |

The tables that follow in this report are retained as the original audit baseline. They are no longer the current open-risk list.

### By Severity (Deduplicated)

| Severity | Count | Immediately Exploitable |
|----------|-------|------------------------|
| **CRITICAL** | 18 | 5 |
| **HIGH** | 32 | 8 |
| **MEDIUM** | 52 | ~15 |
| **LOW** | 34 | — |
| **INFO** | 12 | — |
| **TOTAL** | **148** | **~28** |

### By Domain Area

| Domain | CRIT | HIGH | MED | LOW | INFO | Total |
|--------|------|------|-----|-----|------|-------|
| Authentication & Sessions | 2 | 4 | 3 | 1 | 0 | 10 |
| Authorization & RBAC | 2 | 4 | 4 | 3 | 0 | 13 |
| Tenant Isolation | 5 | 4 | 4 | 1 | 1 | 15 |
| Document Lifecycle | 2 | 3 | 3 | 1 | 0 | 9 |
| Collaboration & Real-Time | 3 | 2 | 4 | 2 | 1 | 12 |
| AI Assistant & RAG | 1 | 5 | 3 | 2 | 0 | 11 |
| File Upload & Attachments | 1 | 3 | 3 | 2 | 1 | 10 |
| Customer Portal & Public | 1 | 1 | 7 | 3 | 1 | 13 |
| Review Workflow | 1 | 3 | 3 | 0 | 0 | 7 |
| User Management | 1 | 3 | 4 | 1 | 0 | 9 |
| Support Tickets | 0 | 2 | 7 | 2 | 0 | 11 |
| Password Reset | 1 | 3 | 3 | 1 | 1 | 9 |
| Engineering / Cross-Cutting | 0 | 3 | 4 | 3 | 2 | 12 |
| Architecture | 0 | 2 | 3 | 2 | 1 | 8 |

### Systemic Pattern Summary

| Pattern | Occurrences | Affected Flows |
|---------|------------|----------------|
| State machine bypasses | 3+ bypass paths | Documents, Reviews, Support Tickets |
| Inconsistent sanitization | 5 unsanitized entry points | Support WS, Feedback, NPS, AI Tools, Invitations |
| Session/token lifecycle gaps | 4 missing invalidations | Role change, Password reset, User delete, Collab token refresh |
| Missing rate limiting | 6 unprotected surfaces | Public endpoints, Invitation, Search, NPS, Password reset verify |
| Race conditions (no locking) | 4 concurrent-write bugs | Invitation, Review approval, Auth login, Rate limit check |
| Email not implemented/disabled | 3 broken features | Invitation, Password reset, Support notifications |

---

## 5. CRITICAL FINDINGS

Status update (2026-03-26): all critical findings listed in this section were remediated and regression-tested. The entries below are preserved as the original baseline record.

### C-01: `PUT /documents/{id}` Allows Arbitrary Status Changes — Direct Privilege Escalation

- **Severity:** CRITICAL — **IMMEDIATELY EXPLOITABLE**
- **Sources:** Feature Review Doc#2, Flow F3-02, Role Audit RP-02
- **Files:** `backend/app/api/management/documents.py:439`, `backend/app/schemas/__init__.py:201`, `backend/app/services/document_service.py:870-876`
- **Description:** The `DocumentUpdate` schema includes an optional `status` field. `update_document()` applies it directly (`document.status = document_data.status`) with no state-machine validation and no role check. Any EDITOR can set `status=active` to bypass the entire review workflow and the MANAGER+ publish requirement.
- **Impact:** The publish workflow (review → approval → MANAGER publishes) is the core content governance mechanism. A single API call by any editor makes a document publicly visible without review.
- **Exploit:** `PUT /documents/42 {"status": "active"}` — document becomes publicly visible immediately.
- **Fix:** Remove `status` from `DocumentUpdate` schema entirely. All status transitions must go through dedicated endpoints with state-machine validation and role requirements. **One-line schema change.**
- **Effort:** XS

### C-02: Token Type Not Validated Anywhere

- **Severity:** CRITICAL
- **Sources:** Feature Review Auth#1, Flow F1-02
- **Files:** `backend/app/services/token_service.py`, `backend/app/auth_context/collaboration_auth_service.py`
- **Description:** JWT `type` field is set to `access`, `refresh`, or `collab` during creation but **never checked on validation**. An access token can be used as a collab token and vice versa. A refresh token (which is in an httpOnly cookie) works as an access token. All token types are interchangeable.
- **Impact:** Collapses all token types into a single interchangeable credential. Refresh tokens meant to be confined to httpOnly cookies become usable as bearer tokens.
- **Fix:** Add `type` claim check in ALL token verification paths. Reject tokens where `type != expected_type`.
- **Effort:** S

### C-03: State Machine Bypass on Archive/Restore (and ACTIVE→DRAFT)

- **Severity:** CRITICAL
- **Sources:** Feature Review Doc#1, Flow F3-01, Flow F4-03
- **Files:** `backend/app/services/document_service.py:851,905`, `backend/app/domain/document_stage.py`
- **Description:** `archive_document()` and `restore_document()` directly set `status = ARCHIVED` / `status = DRAFT` without going through the state machine's `transition()` method. Frontend also works around the state machine by using the raw `PUT /documents/{id}` API to force ACTIVE→DRAFT (a transition not in the state machine).
- **Impact:** The state machine is decorative, not enforced. Any valid state transitions to/from archive. The "workflow" can be bypassed at any point.
- **Fix:** Add ACTIVE→ARCHIVED and ARCHIVED→DRAFT to the state machine. Route all archive/restore through `DocumentAggregate.transition()`.
- **Effort:** M

### C-04: Dynamic RBAC Empty-Set Fallback Grants Maximum Permissions

- **Severity:** CRITICAL
- **Sources:** Feature Review RBAC#2
- **Files:** `backend/app/services/permissions.py:197-200`
- **Description:** When `_effective_permissions()` resolves an empty dynamic permission set for a role, it falls back to the **full static permission set**. Deleting all dynamic policies for a role silently grants maximum permissions instead of revoking all permissions.
- **Impact:** Inverse fail-safe — emptiness grants everything instead of nothing. Any misconfiguration or bulk policy deletion silently escalates all roles to maximum privilege.
- **Fix:** Change fallback: empty dynamic permissions = empty set (deny-all for that role), not full static set.
- **Effort:** S

### C-05: Review Approval Race Condition — Concurrent Overwrites

- **Severity:** CRITICAL
- **Sources:** Feature Review Review#1, Flow F4-01
- **Files:** `backend/app/api/management/reviews.py:551-580`, `backend/app/application/commands/review_commands.py`
- **Description:** No database-level locking on `ReviewRequest`. Two reviewers can approve simultaneously; both read `status=PENDING`, both set `status=APPROVED`. First reviewer's `reviewed_by`, `review_notes` are silently overwritten by the second.
- **Impact:** Review data silently corrupted. The wrong reviewer's notes are preserved. Audit trail is falsified.
- **Fix:** Add `with_for_update()` on the review query, or add an optimistic lock version column.
- **Effort:** S

### C-06: Collab Token Refresh Doesn't Reach Server — Silent Data Loss After 60 Minutes

- **Severity:** CRITICAL
- **Sources:** Flow F6-01
- **Files:** `frontend/src/lib/useCollaboration.ts:640-657`, `collab-server/src/server/collabServerApp.ts:207-219`
- **Description:** Frontend refreshes collab token every 45 min into `tokenRef.current` but never pushes the new token to the Hocuspocus server. The collab server's `documentAuthStore` retains the original token. After 60 min, the stored token expires and all `PUT /state` calls to backend return 401. **Auto-save silently fails for the remainder of the session.**
- **Impact:** Any collaborative editing session longer than 60 minutes silently loses all work after that point. This is a **data loss time bomb** for the primary use case.
- **Fix:** On token refresh, disconnect and reconnect the provider (triggering re-auth with the new token), or implement a token-update protocol message.
- **Effort:** M

### C-07: Silent Persistence Failure — No Client Notification

- **Severity:** CRITICAL
- **Sources:** Flow F6-02
- **Files:** `collab-server/src/server/collabServerApp.ts:213-215`
- **Description:** When `Database.store` has no write-capable token, it `console.error`s and returns — silently dropping the save. No error is propagated to connected clients. Users believe their work is being saved when it isn't.
- **Impact:** Users work for hours believing their edits are saved. They close the browser. The work is gone.
- **Fix:** Propagate save-failure events to connected clients via a custom Hocuspocus message. Show a warning banner in the editor.
- **Effort:** M

### C-08: No Real-Time Access Revocation in Collaboration

- **Severity:** CRITICAL
- **Sources:** Flow F6-03
- **Files:** `collab-server/src/documentAuthStore.ts`
- **Description:** A user whose document access is revoked retains full read/write WebSocket access for up to 60 minutes (token lifetime). No mechanism exists to push invalidation to active connections.
- **Impact:** 60-minute security window. An employee fired and removed from document access can read and modify documents for up to an hour.
- **Fix:** Implement periodic permission re-check (every 5 min) or listen for revocation events via Redis pub/sub.
- **Effort:** M

### C-09: Invitation Acceptance Race Condition — Duplicate Users

- **Severity:** CRITICAL
- **Sources:** Flow F2-01
- **Files:** `backend/app/api/management/auth.py:533-535`
- **Description:** No row-level lock on invitation lookup during acceptance. Two concurrent `POST /auth/invitation/accept` with the same token can both read the invitation as valid, both create users, and both mark it as accepted.
- **Impact:** Duplicate user accounts created from a single invitation. Data integrity violation.
- **Fix:** Add `with_for_update()` on the invitation query during acceptance.
- **Effort:** S

### C-10: No Session Invalidation on Role Change

- **Severity:** CRITICAL
- **Sources:** Flow F9-01, Role Audit RP-06
- **Files:** `backend/app/web/controllers/management/users_controller.py:250`, `backend/app/services/auth_service.py`
- **Description:** When a user is demoted (e.g., admin→editor), their existing sessions retain the elevated role until natural JWT expiry (15-30 min). A compromised admin account retains admin API access after demotion.
- **Impact:** The most common reason to demote urgently is suspected compromise. The demotion doesn't actually take effect for up to 30 minutes.
- **Fix:** Add `revoke_all_user_sessions(user.id)` to the role-change code path (same pattern as deactivation).
- **Effort:** S

### C-11: Password Reset Link URL Mismatch — Feature Completely Broken

- **Severity:** CRITICAL
- **Sources:** Flow F11-01
- **Files:** `backend/app/api/management/auth.py:271`, `frontend/src/pages/ResetPasswordPage.tsx:10`
- **Description:** Backend email generates `{BASE_URL}/login?reset_token={token}`. Frontend's ResetPasswordPage expects `/reset-password?token={token}`. LoginPage has no code to read `reset_token` param. **Clicking the email link lands on the login page — password reset via email does not work.**
- **Impact:** Core security feature (password reset) is non-functional. Users who forget their password have no recovery path.
- **Fix:** Change backend URL to `f"{settings.BASE_URL}/reset-password?token={quote(reset_token)}"`.
- **Effort:** XS

### C-12: Cross-Tenant Chat via SYSTEM_ADMIN Bypass

- **Severity:** CRITICAL
- **Sources:** Feature Review Collab#1
- **Files:** `backend/app/services/chat_service.py:49-60`
- **Description:** Direct chat creation allows cross-tenant messaging if either user is SYSTEM_ADMIN. Creates bidirectional channel between tenants with no isolation.
- **Impact:** SYSTEM_ADMIN from Tenant A can message any user in Tenant B. Breaks tenant boundary model.
- **Fix:** Add `User.tenant_id == user_a.tenant_id` filter to `create_direct_chat()` user lookup. Remove SYSTEM_ADMIN bypass.
- **Effort:** S

### C-13: Collab Server Has No Independent Tenant Verification

- **Severity:** CRITICAL
- **Sources:** Feature Review Collab#4, Role Audit RP-14
- **Files:** `collab-server/src/server/collabServerApp.ts:155-220`
- **Description:** `onAuthenticate` only verifies JWT signature and expiry. Never queries the backend to confirm `document.tenant_id == user.tenant_id`. Trusts the token issuer completely.
- **Impact:** If the backend ever issues a bad collab token (bug or exploit), the collab server has zero safety net. Token also lacks `tenant_id` claim.
- **Fix:** Add `tenant_id` to collab token. Add backend API call in `onAuthenticate` to verify tenant match.
- **Effort:** M

### C-14: documentAuthStore Doesn't Validate Token-Document Binding

- **Severity:** CRITICAL
- **Sources:** Feature Review Collab#3
- **Files:** `collab-server/src/documentAuthStore.ts:55-85`
- **Description:** Stores token per connection per document but never verifies the JWT's `document_id` claim matches the document being accessed. A token for document A could authorize access to document B.
- **Impact:** Any valid collab token could be replayed against a different document.
- **Fix:** Validate `token.document_id == requestedDocumentId` before storing.
- **Effort:** S

### C-15: User Enumeration via Cross-Tenant Lookup in Chat

- **Severity:** CRITICAL
- **Sources:** Feature Review Collab#5
- **Files:** `backend/app/services/chat_service.py:48-56`
- **Description:** `create_direct_chat()` queries `User` by ID with **no tenant filter**. Returns 404 only if user doesn't exist globally, revealing user existence across tenants.
- **Impact:** Any authenticated user can enumerate whether specific user IDs exist across all tenants.
- **Fix:** Add tenant filter to user lookup in chat creation.
- **Effort:** S

### C-16: XML Injection via `base_url` in Sitemap

- **Severity:** CRITICAL
- **Sources:** Feature Review Public#1
- **Files:** `backend/app/api/public/documents.py:610-625`
- **Description:** `base_url` query parameter interpolated directly into sitemap XML output **without XML-escaping**. An `_escape()` helper exists for RSS but is not used here.
- **Impact:** Enables XML injection and SEO poisoning on a public, unauthenticated endpoint.
- **Fix:** Apply `xml.sax.saxutils.escape()` to `origin`. Better: validate `base_url` against URL allowlist.
- **Effort:** XS

### C-17: Session Inactivity Check Doesn't Revoke in Database

- **Severity:** CRITICAL
- **Sources:** Feature Review Auth#2
- **Files:** `backend/app/security.py:100-101`
- **Description:** When inactivity timeout triggers, code raises `HTTPException` but **never sets `session.revoked = True`** in the database. The stale session remains valid — user can retry immediately and succeed.
- **Impact:** Session inactivity timeout is "check but don't enforce" — a cosmetic security measure.
- **Fix:** Add `session.revoked = True; db.commit()` before raising the exception.
- **Effort:** XS

### C-18: DELETE User Endpoint Missing Session/Token Cascade

- **Severity:** CRITICAL
- **Sources:** Flow F9-02, Feature Review User#1
- **Files:** `backend/app/web/controllers/management/users_controller.py:399-440`
- **Description:** `DELETE /users/{id}` sets `is_active=False` and logs a security event but does NOT revoke sessions, refresh tokens, or cancel invitations. The `PUT /users/{id} {is_active:false}` path does all three. A "deleted" user's sessions remain valid.
- **Impact:** Admin uses DELETE thinking the user is fully removed, but the user retains valid sessions.
- **Fix:** Add the same cascade logic from the PUT deactivation path to the DELETE endpoint.
- **Effort:** S

---

## 6. HIGH-SEVERITY FINDINGS

Status update (2026-03-26): all high-severity findings listed in this section were remediated and regression-tested. The entries below are preserved as the original baseline record.

### H-01: `document_ids` Chat Parameter Bypasses Tenant Isolation in RAG

- **Sources:** Flow F8-01, Role Audit RP-05
- **Files:** `backend/app/assistant/engine.py:342-375`
- **Description:** Chat request accepts explicit `document_ids`. The lookup queries `Document.id == did` with **no tenant filter and no access policy check**. The `@mention` path correctly validates access. Any authenticated user can inject cross-tenant document content into AI context.
- **Fix:** Add tenant filter and `DocumentAccessPolicy.can_view_document()` check to the explicit `document_ids` path.
- **Effort:** S

### H-02: Prompt Injection via @mention and Uploaded File Content

- **Sources:** Feature Review AI#2, AI#3
- **Files:** `backend/app/assistant/engine.py:310-322,355-395`
- **Description:** Document content and uploaded file text injected as `system`-role messages — the highest authority level. Documents containing `[END DOCUMENT]\n[SYSTEM OVERRIDE]...` can hijack the LLM's behavior.
- **Fix:** Change injection from `system` role to `user` role with clear untrusted-data framing.
- **Effort:** S

### H-03: LLM Context Window Overflow Drops Safety Prompt

- **Sources:** Feature Review AI#4
- **Files:** `backend/app/assistant/engine.py:282-310`, `backend/app/assistant/schemas.py:67`
- **Description:** Total possible context: ~25,500 chars against `num_ctx=4096`. System prompt (safety instructions) is first, but Ollama silently truncates from the start when context is too long. Attacker loads max files + documents + history to push safety prompt out.
- **Fix:** Implement context window budget management. Prioritize safety prompt retention.
- **Effort:** M

### H-04: RAG Tools Read Draft/Unpublished Versions

- **Sources:** Feature Review AI#6
- **Files:** `backend/app/assistant/tools/rag_tools.py:131-140`, `backend/app/assistant/engine.py:340-348`
- **Description:** `SummarizeDocumentTool` and `AskAboutDocumentTool` query latest version by `version_number DESC` without filtering `is_published`. Exposes unpublished draft content via AI.
- **Fix:** Add `.filter(Version.is_published.is_(True))` to all RAG tool version queries.
- **Effort:** S

### H-05: LLM Output Rendered Without Sanitization

- **Sources:** Feature Review AI#5
- **Files:** `frontend/src/features/assistant/AssistantMessageList.tsx:135-141`
- **Description:** `ReactMarkdown` renders assistant output. If LLM is tricked into outputting HTML/script payloads, and `rehypeRaw` is enabled, stored XSS fires. Markdown image injection (`![](https://evil.com/steal)`) works regardless.
- **Fix:** Add output sanitization before rendering. Disable `rehypeRaw` if enabled.
- **Effort:** S

### H-06: WebSocket Messages Bypass Sanitization (Stored XSS)

- **Sources:** Flow F10-02
- **Files:** `backend/app/ws/support_ws.py:150`
- **Description:** Support ticket WebSocket `_handle_send_message()` stores message content **without** calling `sanitize_html_content()`. The REST API path sanitizes correctly. Messages sent via WebSocket contain raw HTML.
- **Impact:** Stored XSS — malicious HTML stored via WebSocket rendered to all ticket viewers.
- **Fix:** Apply `sanitize_html_content()` in the WebSocket handler before storage.
- **Effort:** XS

### H-07: No ZIP Bomb Protection on DOCX/PPTX Extraction

- **Sources:** Feature Review Attach#2, Flow F5-01
- **Files:** `backend/app/services/docx_extractor.py:225`, `backend/app/services/pptx_extractor.py`
- **Description:** DOCX/PPTX files are ZIP archives. No decompression ratio limit, no max extracted size check. A 1MB upload can decompress to 10GB+, causing OOM.
- **Fix:** Add decompression ratio checks (abort if decompressed > 10× compressed) or process in a memory-limited subprocess.
- **Effort:** S

### H-08: XXE Risk in DOCX/PPTX Extraction

- **Sources:** Feature Review Attach#1, Flow F5-02
- **Files:** `backend/app/services/docx_extractor.py:1089`
- **Description:** Uses `xml.etree.ElementTree.fromstring()` which is vulnerable to entity expansion bombs (billion laughs). CPython's ET is safe against classic XXE but not against entity expansion.
- **Fix:** Replace with `defusedxml.ElementTree` throughout the conversion pipeline.
- **Effort:** S

### H-09: Sessions NOT Invalidated After Password Reset

- **Sources:** Flow F11-02
- **Files:** `backend/app/services/auth_service.py:182-196` vs `auth_service.py:499-505`
- **Description:** `reset_password()` does NOT revoke `UserSession` records. `change_password()` does. If reset is triggered because account is compromised, the attacker's existing session continues.
- **Fix:** Add session revocation to `reset_password()` — copy from `change_password()`.
- **Effort:** S

### H-10: O(n) bcrypt Comparisons on Reset Token Verification — DoS Vector

- **Sources:** Flow F11-03, Feature Review Auth#5
- **Files:** `backend/app/services/auth_service.py:157-166`
- **Description:** Token verification loads ALL valid PasswordReset records and performs bcrypt verify against each (~100ms each). An attacker can inflate n by requesting resets, then DoS the verification endpoint.
- **Fix:** Wire up the `token_prefix` column: store `token[:8]` on creation, filter by prefix before bcrypt.
- **Effort:** S

### H-11: Email Disabled by Default — Password Reset Non-Functional OOTB

- **Sources:** Flow F11-04
- **Files:** `backend/app/config.py:103`
- **Description:** `EMAIL_ENABLED` defaults to `False`. Token is generated but never emailed. Reset only works if SMTP is configured. No warning logged on startup.
- **Fix:** Log startup warning when `EMAIL_ENABLED=False`. Document SMTP as requirement.
- **Effort:** XS

### H-12: Email Sending Not Implemented for Invitations

- **Sources:** Flow F2-03
- **Files:** Invitation service email path
- **Description:** Invitation flow generates token but email delivery is not actually implemented. The invitation exists in DB but cannot be communicated to the invitee.
- **Fix:** Implement email sending for invitations or provide alternative token delivery.
- **Effort:** M

### H-13: Username Enumeration via Login Timing

- **Sources:** Feature Review Auth#3
- **Files:** `backend/app/services/auth_service.py:268`
- **Description:** Login with non-existent email returns 401 immediately (no bcrypt work). Valid email + wrong password does bcrypt verify. Timing delta reveals email existence. Password reset correctly uses dummy work — login does not.
- **Fix:** Add dummy bcrypt work when user not found.
- **Effort:** XS

### H-14: Rate Limit Race Condition

- **Sources:** Feature Review Auth#4
- **Files:** `backend/app/api/management/auth.py:205-216`
- **Description:** Rate limiting uses check-then-record pattern: read count, verify under limit, process request, then record. Concurrent requests all pass.
- **Fix:** Use atomic increment (Redis INCR or SQLite UPDATE...RETURNING).
- **Effort:** S

### H-15: COMPANY Document Visibility = All Internal Users (Cross-Tenant)

- **Sources:** Feature Review RBAC#3, Role Audit RP-07
- **Files:** `backend/app/application/policies/access_policies.py:57-69`
- **Description:** Documents with COMPANY visibility are accessible to ALL internal users across the platform, not scoped to the document's tenant. Any internal user in any tenant can view COMPANY-scoped documents.
- **Fix:** Add `document.tenant_id == user.tenant_id` filter to COMPANY visibility checks.
- **Effort:** S

### H-16: Stale Pending Review on Document Edit — Orphaned Reviews

- **Sources:** Flow F4-02
- **Files:** Frontend raw API use
- **Description:** When editor edits a document after submitting for review, the frontend forces `status=DRAFT` via `PUT /documents/{id}` (bypassing state machine via C-01). The existing PENDING review is NOT cancelled. Orphaned PENDING review linked to stale content.
- **Fix:** Auto-cancel PENDING reviews when document reverts to DRAFT.
- **Effort:** S

### H-17: ACTIVE→DRAFT Not in State Machine — Forces Bypass

- **Sources:** Flow F4-03
- **Files:** `backend/app/domain/document_stage.py`
- **Description:** Frontend needs ACTIVE→DRAFT but state machine doesn't support it, forcing code to bypass the state machine entirely.
- **Fix:** Add ACTIVE→DRAFT to state machine transitions.
- **Effort:** S

### H-18: Route Guard Mismatch: publish_version/force_publish Uses `require_editor`

- **Sources:** Feature Review Doc#2/#3, Role Audit RP-18
- **Files:** `backend/app/api/management/versions.py:151-155,203`
- **Description:** `publish_version` route uses `require_editor` but service requires MANAGER+. `force_publish_version` route uses `require_editor` but service requires SYSTEM_ADMIN. Editors get through the route guard but hit a confusing 403 from service layer.
- **Fix:** Change route guards: `require_manager` for publish, `require_system_admin` for force-publish.
- **Effort:** XS

### H-19: WebSocket JWT Validated Only at Connection — No Re-Auth

- **Sources:** Feature Review Collab#7, Cross-cutting #8
- **Files:** `backend/app/ws/chat_ws.py:64-120`
- **Description:** User authenticated once at WebSocket connect. Token never re-validated on subsequent messages. If session is revoked, user continues messaging indefinitely.
- **Fix:** Add per-message JWT validation or periodic token refresh check.
- **Effort:** M

### H-20: Activity Logging Endpoint Has No Document Access Verification

- **Sources:** Feature Review Collab#8
- **Files:** `backend/app/api/management/collaboration/activity.py:49-63`
- **Description:** Any authenticated user can POST activity log entries against any document_id with no tenant or ownership check. Pollutes audit trail.
- **Fix:** Add document access check before accepting activity log entries.
- **Effort:** S

### H-21: Persistence Layer Trusts Tokens Blindly

- **Sources:** Feature Review Collab#9
- **Files:** `collab-server/src/persistence.ts:93-110`
- **Description:** Sends token to backend for document state load without verifying it's meant for the requested document. Silent error handling on failure (returns null).
- **Fix:** Verify token's `document_id` matches the requested document before sending.
- **Effort:** S

### H-22: Avatar Upload Missing Magic Byte Validation

- **Sources:** Feature Review Attach#3
- **Files:** `backend/app/api/management/users.py:189-195`
- **Description:** Avatar upload checks Content-Type header and extension but not magic bytes. A `.png` file with script content passes validation.
- **Fix:** Add magic byte validation using the existing `_validate_magic_bytes()` helper.
- **Effort:** XS

### H-23: Frontend Blob Download Bypasses Ticket System

- **Sources:** Feature Review Attach#4
- **Files:** `frontend/src/hooks/useAttachmentDownload.ts:14`
- **Description:** Frontend downloads via direct blob fetch, bypassing HMAC-signed ticket system. Signature-based access control exists but isn't used by primary path.
- **Fix:** Wire up the ticket system for all downloads.
- **Effort:** S

### H-24: User CRUD Endpoints Have No Route-Level Role Guard

- **Sources:** Role Audit RP-01
- **Files:** `backend/app/api/management/users.py:88,100,368,399,414`
- **Description:** Five critical user management endpoints use only `get_current_active_user` (authentication only, not authorization). Role checks exist only in the service layer — single layer of defense.
- **Fix:** Add `Depends(require_manager)` to list/get and `Depends(require_admin)` to create/update/delete.
- **Effort:** XS

### H-25: RBAC Policy Update Has No Guardrails

- **Sources:** Feature Review User#3
- **Files:** `backend/app/api/management/rbac.py:40-54`
- **Description:** System admin can assign ANY permission set to ANY role, including giving CUSTOMER all system_admin permissions. No invariant enforcement, no confirmation step.
- **Fix:** Add minimum/maximum permission invariants per role. Add confirmation step (re-enter password or MFA).
- **Effort:** M

### H-26: No Rate Limiting on Any Public Endpoint

- **Sources:** Feature Review Public#3
- **Files:** `backend/app/api/public/__init__.py`
- **Description:** Zero rate limiting across 6 sub-routers including search (multiple ILIKE queries). Automated scraping or wildcard storms cause DB saturation.
- **Fix:** Add `slowapi` or equivalent to all `/public/*` routes.
- **Effort:** S

### H-27: No State Machine on Support Ticket Status Transitions

- **Sources:** Flow F10-01
- **Files:** `backend/app/services/support_service.py:152`
- **Description:** `update_ticket()` accepts any status value. Any transition is valid (CLOSED→OPEN, skip RESOLVED, etc.). No lifecycle enforcement.
- **Fix:** Implement state machine: OPEN→IN_PROGRESS→RESOLVED→CLOSED with allowed transitions per role.
- **Effort:** M

### H-28: `defusedxml` Not Used Anywhere in the Codebase

- **Sources:** Feature Review Cross-cutting#7
- **Files:** `backend/app/services/docx_extractor.py`, all XML parsing paths
- **Description:** Standard library `xml.etree.ElementTree` used for all XML parsing. While CPython's ET is safe against classic XXE, it's vulnerable to entity expansion (billion laughs).
- **Fix:** Replace with `defusedxml.ElementTree` throughout.
- **Effort:** S

### H-29: ChromaDB Tenant Filter Is Optional — None Bypasses

- **Sources:** Role Audit RP-13
- **Files:** `backend/app/assistant/rag/vector_store.py:108-145`
- **Description:** Passing `None` for `tenant_id` returns chunks from ALL tenants. Intentional for system_admin but the contract doesn't enforce non-None for other roles.
- **Fix:** Make `tenant_id` required. Add explicit `is_system_admin` check at call site.
- **Effort:** S

### H-30: Document Status Not Enforced During Collaboration

- **Sources:** Flow F6-04
- **Files:** `backend/app/application/policies/access_policies.py:85-88`, `backend/app/auth_context/collaboration_auth_service.py`
- **Description:** `can_edit_document` checks role and tenant but NOT `document.status`. A document moved to REVIEW or ARCHIVED can still be collaboratively edited if the collab token was issued while it was DRAFT.
- **Fix:** Check `document.status` in `get_user_permissions_for_document()`. Add status re-check on token refresh.
- **Effort:** S

### H-31: Pending Reviews Orphaned on User Demotion/Deactivation

- **Sources:** Flow F9-03
- **Files:** Review system
- **Description:** When a reviewer is demoted or deactivated, their pending review assignments are never reassigned or cancelled. Submitters wait indefinitely.
- **Fix:** Auto-cancel or reassign PENDING reviews where `reviewed_by == user.id`.
- **Effort:** S

### H-32: Transaction Race Conditions in Auth Service

- **Sources:** Engineering Review EQ-05
- **Files:** `backend/app/services/auth_service.py:40,99,128,191,218,380`
- **Description:** `login()` commits at 6 different points. `is_locked()` check and `increment_failed_attempts()` are not atomic. Two concurrent login requests can both pass the lock check.
- **Impact:** Account lockout bypass under concurrent requests.
- **Fix:** Wrap lock-check and session-creation in a single transaction with row-level locking.
- **Effort:** M

---

## 7. MEDIUM-SEVERITY FINDINGS

Status update (2026-03-26): all medium-severity findings listed in this section were remediated and regression-tested. The entries below are preserved as the original baseline record.

### M-01 through M-52

| ID | Title | Area | Files | Description |
|----|-------|------|-------|-------------|
| M-01 | Session ID hashed without salt | Auth | `session_tokens.py:5-8` | SHA-256 without salt. Rainbow tables apply if DB compromised. |
| M-02 | No rate limit on invitation endpoints | Auth | `auth.py:327-356` | Public endpoints with no throttling. |
| M-03 | Refresh token rotation not atomic | Auth | `auth_service.py:310-330` | Old token revoked and new created in separate operations. Crash between leaves user tokenless. |
| M-04 | Permission check cache with nullable tenant key | RBAC | `permissions.py:73-95` | System admin with `tenant_id=None` may pollute cache. |
| M-05 | Frontend RoleGuard is cosmetic only | RBAC | `components/guards/RoleGuard.tsx` | Backend is the real gate. If backend misconfigured, zero protection. |
| M-06 | RBAC override API has no confirmation step | RBAC | `rbac.py` | Single API call changes entire permission matrix. No MFA or dual-admin. |
| M-07 | Soft delete doesn't cascade to collab sessions | Document | `document_service.py:920-940` | Soft-deleted document still accessible via active collab tokens. |
| M-08 | No optimistic locking on document metadata | Document | `document_service.py` | Concurrent metadata edits → last-write-wins silently. |
| M-09 | Module-level document cache with tenant_id key | Document | `document_service.py:73-95` | System admins with `tenant_id=None` can pollute cache. |
| M-10 | ACTIVE is terminal state (no transitions out) | Document | `document_stage.py` | Once ACTIVE, no state machine path to DRAFT or ARCHIVED. Must bypass. |
| M-11 | No auto-save on non-collaborative editing | Document | Editor component | Single-player editing has no auto-save protection. |
| M-12 | Preflight review endpoint exists but is unused | Review | `reviews.py`, `ReviewDialog.tsx` | Backend checks publish prerequisites; frontend never calls it. |
| M-13 | Deactivated reviewer's approval persists | Review | `review_commands.py`, `access_policies.py` | If reviewer is deactivated, their approval remains valid at publish time. |
| M-14 | Document state not validated before review submission | Review | `reviews.py:480-510` | Review can be submitted against DRAFT or ARCHIVED document. |
| M-15 | Reconnection reuses potentially expired collab token | Collab | `useCollaboration.ts:456` | On reconnect, uses original token which may be expired. |
| M-16 | Read-only viewers cannot join WebSocket | Collab | `auth.py:593-597` | Read-only users can't observe real-time collaboration. |
| M-17 | State endpoints may lack document-level auth | Collab | `state.py:33-70` | Collab state read/write may not independently check document access. |
| M-18 | require_tenant_match() returns True for None tenant | Isolation | `tenant_context.py:50-90` | System admins implicitly bypass all tenant boundaries. |
| M-19 | Snapshot/state endpoints lack explicit tenant validation | Isolation | `collaboration/snapshots.py:57-70`, `state.py:31-45` | Rely on injected service for tenant checks. No endpoint-level assertion. |
| M-20 | Redis cache invalidation has no authentication | Isolation | `persistence.ts:32-48` | Redis PubSub accepts any document ID. No HMAC on messages. |
| M-21 | Chat deletion doesn't re-verify tenant | Isolation | `chat_service.py:231-244` | If `_get_chat_with_permission` bypassed, cross-tenant delete succeeds. |
| M-22 | In-memory AI rate limiter (not distributed, memory leak) | AI | Rate limit service | Not shared across workers. Entries never evicted. |
| M-23 | Tool result prompt injection risk | AI | `engine.py` | Tool results injected into LLM prompt without sanitization. |
| M-24 | No upload size limit on chat attachments | AI | Chat attachment handling | No `MAX_CHAT_ATTACHMENT_SIZE`. |
| M-25 | ChromaDB tenant isolation incomplete for system admins | AI | `vector_store.py:108-130` | System admin queries ALL tenants' chunks. Undocumented. |
| M-26 | No defusedxml for XML parsing in extractors | Upload | `docx_extractor.py` | Standard library ET used. Entity expansion bombs possible. |
| M-27 | Legacy JWT-in-URL download fallback | Upload | `attachments.py` | JWTs in URLs leak via history, logs, referer headers. |
| M-28 | Content-Type defaults to application/octet-stream | Upload | `upload.py:346` | Triggers browser content-sniffing. |
| M-29 | No antivirus/malware scanning | Upload | `storage_service.py` | Files stored directly without scanning. |
| M-30 | DOCX extraction regex-based HTML parsing | Upload | `docx_extractor.py:550-610` | Fragile, bypassable with malformed input. |
| M-31 | Feedback content stored unsanitized | Portal | `feedback.py:75-82` | Stored XSS vector if rendered as HTML in admin views. |
| M-32 | NPS comment stored unsanitized | Portal | `nps.py:63` | Same XSS risk as feedback. |
| M-33 | NPS endpoints don't enforce require_customer | Portal | `nps.py:26,46` | Any authenticated user can submit NPS. Pollutes data. |
| M-34 | Announcement content not sanitized server-side | Portal | `announcements.py:32` | Compromised admin → XSS for all public visitors. |
| M-35 | Changelog relies solely on client-side DOMPurify | Portal | `changelog.py:38` | API consumers bypass DOMPurify entirely. |
| M-36 | SQL wildcard injection in public search | Portal | `documents.py:119,460` | `%` and `_` not escaped in ILIKE patterns. |
| M-37 | Custom sanitizer instead of DOMPurify for documents | Portal | `htmlSanitizer.ts:1-287` | Custom sanitizers have higher bypass probability. |
| M-38 | LIKE wildcard injection in autocomplete | Search | `search_queries.py:333-335` | `escape_sql_wildcards()` exists but not used here. |
| M-39 | Search click endpoint accepts arbitrary document_id | Search | `search.py:179-192` | Analytics poisoning via cross-tenant click recording. |
| M-40 | No per-endpoint rate limiting on search | Search | `search.py:72-102` | FTS5 is computationally expensive. No throttling. |
| M-41 | Unbounded `limit` on notifications | Search | `notifications.py:71` | `?limit=999999` forces full table materialization. |
| M-42 | Admin-created users skip email verification | User | User creation flow | Email accepted without verification. Typo → no recovery. |
| M-43 | No admin force-reset password capability | User | Admin endpoints | Locked-out users with unconfigured email have no recovery. |
| M-44 | No notification on role change | User | User service | User's UI shows stale permissions until refresh. |
| M-45 | Self-profile edits have no audit trail | User | Profile endpoint | Admin edits logged; self-edits not logged. |
| M-46 | REST message doesn't trigger WebSocket broadcast | Support | `support.py`, `support_ws.py` | Agents on WebSocket miss REST-sent messages. |
| M-47 | No notification to customer on agent reply | Support | `support_service.py` | Customer must manually check for updates. |
| M-48 | Customer can message CLOSED tickets via API | Support | `support.py` | UI hides input but API accepts. |
| M-49 | AI tool CreateSupportTicketTool bypasses sanitization | Support | AI tool code | Content generated by AI not sanitized. |
| M-50 | No email notifications for any ticket events | Support | Support service | Feature is UI-only. No email on creation, reply, or resolution. |
| M-51 | token_prefix column never populated — dead optimization | Reset | `auth_service.py:140-145`, `models/__init__.py:726` | Column with index exists but always NULL. |
| M-52 | Frontend password complexity mismatch on reset page | Reset | `ResetPasswordPage.tsx:34` | Only checks length >= 8. Zod schema with full rules exists but unused. |

---

## 8. LOW & INFORMATIONAL FINDINGS

Status update (2026-03-26): all low and informational findings listed in this section were remediated or retired as intended. The entries below are preserved as the original baseline record.

### LOW (34 findings)

| ID | Title | Area |
|----|-------|------|
| L-01 | Dead `account_locked` UI code | Auth/Frontend |
| L-02 | Network errors indistinguishable from credentials error | Auth/UX |
| L-03 | No return-URL after auth redirect | Auth/UX |
| L-04 | Logout revokes ALL user sessions (not just current) | Auth |
| L-05 | No audit logging on invitation acceptance | Compliance |
| L-06 | Frontend allows PDF upload but backend rejects | Upload/UX |
| L-07 | Wrong argument order in magic byte validation | Upload |
| L-08 | No frontend file-size validation before upload | Upload/UX |
| L-09 | No reconnection backoff jitter (thundering herd) | Collab |
| L-10 | Session end request is fire-and-forget | Collab |
| L-11 | Reading progress uses separate engagement API path | Portal |
| L-12 | No real-time updates for customer support portal | Portal/UX |
| L-13 | Wasted inference on client disconnect | AI/Efficiency |
| L-14 | In-memory rate limiter resets on server restart | Auth |
| L-15 | User enumeration via invitation/create distinct errors | User |
| L-16 | Invitation message field not sanitized | User/XSS |
| L-17 | Profile update bypasses tenant suspension check | User/Isolation |
| L-18 | Invitation token stored as plaintext in DB | User/Security |
| L-19 | No row-level lock on invitation acceptance (also C-09) | User/Concurrency |
| L-20 | Comments endpoints accessible to customers on management router | RBAC |
| L-21 | Attachment management endpoints accessible to customers | RBAC |
| L-22 | Viewers can read DRAFT documents | RBAC/Visibility |
| L-23 | No ownership check on document edit/delete | RBAC/Design |
| L-24 | FTS5 index not tenant-partitioned | Search/Isolation |
| L-25 | Analytics implicit tenant scoping | Analytics/Isolation |
| L-26 | Error detail disclosure in analytics export | Analytics/InfoLeak |
| L-27 | Search analytics exposes raw queries cross-tenant | Analytics/Privacy |
| L-28 | FTS5 query syntax abuse (advanced operators) | Search |
| L-29 | No file attachment support on ticket messages | Support/UX |
| L-30 | No agent notification for new tickets | Support/UX |
| L-31 | Document audience churn endpoint lacks ownership check | Analytics |
| L-32 | File deduplication absent | Upload/Efficiency |
| L-33 | No rate limit on password reset verification endpoint | Auth |
| L-34 | Locally redefined auth guards risk enforcement drift | Architecture |

### INFORMATIONAL (12 findings)

| ID | Title | Area |
|----|-------|------|
| I-01 | Ticket download system declared but unused | Upload/Dead Code |
| I-02 | Shared JWT secret requires manual sync between services | Collab/Ops |
| I-03 | NPS dismiss state not persisted | Portal/UX |
| I-04 | No admin force-reset capability | User/Ops |
| I-05 | Duplicate sitemap endpoints with different security | Public/Maintenance |
| I-06 | No CSP headers on XML endpoints | Public/Security |
| I-07 | Uncapped list inputs on ChatRequest | AI/Validation |
| I-08 | Conversation title not sanitized | AI/XSS |
| I-09 | ConnectionRegistry O(N) lookup on disconnect | Collab/Performance |
| I-10 | Comment depth traversal N+1 ORM queries | Backend/Performance |
| I-11 | Feature flag defaults are production-unsafe (True) | Config |
| I-12 | No tech debt tracking in source code | Maintenance |

---

## 9. AUTHENTICATION & SESSION MANAGEMENT

### Architecture
- `python-jose` JWT encoding/decoding, `bcrypt` password hashing
- Access tokens (short-lived) + refresh tokens (httpOnly cookies) + collaboration tokens
- Session table: `user_id`, `session_id`, `ip_address`, `last_active`, `revoked`
- Inactivity timeout in `get_current_active_user` dependency
- Rate limiting via manual check-then-record pattern
- Password reset via bcrypt-hashed tokens stored in DB

### What Works Well
- Refresh tokens in httpOnly cookies (not localStorage)
- Session inactivity timeout exists (see C-17 for enforcement gap)
- Password reset uses bcrypt-hashed tokens (not plaintext)
- Constant-time compare on download ticket validation
- Security events logged for login, logout, password changes
- Dummy bcrypt work on password reset for non-existent users (anti-enumeration)

### What's Broken
| Finding | Severity | Status |
|---------|----------|--------|
| Token type not validated → all tokens interchangeable (C-02) | CRITICAL | Must fix |
| Session inactivity doesn't revoke in DB (C-17) | CRITICAL | Must fix |
| Username enumeration via login timing (H-13) | HIGH | Should fix |
| Rate limit race condition (H-14) | HIGH | Should fix |
| O(n) bcrypt on reset token verification (H-10) | HIGH | Should fix |
| Session ID hashed without salt (M-01) | MEDIUM | Can defer |
| Refresh token rotation not atomic (M-03) | MEDIUM | Can defer |
| Transaction race conditions in login (H-32) | HIGH | Should fix |

### Systemic Issue: Check-But-Don't-Enforce
The authentication layer has a pattern of implementing security checks that don't persist their results. Session inactivity checks but doesn't revoke. Rate limiting checks but has race conditions. Password reset generates tokens but email is disabled by default. The security mechanisms exist but fail to complete their enforcement cycle.

---

## 10. AUTHORIZATION & RBAC

### Architecture
- 6 roles: system_admin (19 perms) → admin (18) → manager (15) → editor (11) → viewer (6) → customer (4)
- Static permission map + dynamic RBAC policy table overrides
- PDP at `policy/pdp.py`
- FastAPI dependencies: `require_admin`, `require_manager`, `require_editor`, etc.
- Frontend `RoleGuard` hides UI elements (cosmetic only)
- Document visibility: PRIVATE/INTERNAL/COMPANY/PUBLIC scopes

### What Works Well
- Clean PDP separation from enforcement points
- Dynamic RBAC allows runtime policy adjustment
- Role hierarchy explicitly encoded and enforced on assignment
- Self-demotion explicitly blocked
- Frontend role guards are consistently correct-or-stricter than backend

### What's Broken
| Finding | Severity | Status |
|---------|----------|--------|
| Dynamic RBAC empty-set fallback grants max permissions (C-04) | CRITICAL | Must fix |
| PUT /documents/{id} status bypass → privilege escalation (C-01) | CRITICAL | Must fix |
| publish/force-publish route guard mismatch (H-18) | HIGH | Should fix |
| User CRUD endpoints no route-level guard (H-24) | HIGH | Should fix |
| RBAC policy update has no guardrails (H-25) | HIGH | Should fix |
| COMPANY visibility = all internal users (H-15) | HIGH | Should fix |

### Critical Pattern: Frontend Covers Backend Gaps
The frontend consistently applies correct guards. The backend routes are weaker, relying on service-layer checks. This creates false confidence — RBAC appears correct from the UI but is incomplete at the API layer.

| Frontend Guard | Backend Route Guard | Actual Requirement |
|---------------|--------------------|--------------------|
| `ManagerGuard` on /users | `get_current_active_user` only | ADMIN+ (service blocks) |
| `InternalGuard` on /assistant | `get_current_active_user` only | Internal (no route block) |
| `AdminGuard` on publish button | `require_editor` | MANAGER+ (service blocks) |
| `ManagerGuard` on delete user | `get_current_active_user` only | ADMIN+ (service blocks) |

---

## 11. TENANT ISOLATION

### Architecture
- `tenant_context.py` middleware sets context from authenticated user
- `TenantAwareService._base_query()` provides tenant-filtered queries
- System admins bypass tenant filtering (`is_system_admin` → see all)
- `require_tenant_match()` is available but **opt-in** (not enforced globally)

### Confirmed Isolation Gaps (Exploitable)

| Finding | Severity | Exploitable? |
|---------|----------|-------------|
| Cross-tenant chat via SYSTEM_ADMIN bypass (C-12) | CRITICAL | Yes |
| User enumeration via cross-tenant chat lookup (C-15) | CRITICAL | Yes |
| Collab server no independent tenant check (C-13) | CRITICAL | Latent |
| documentAuthStore no token-document binding (C-14) | CRITICAL | Yes |
| `document_ids` bypasses tenant isolation in AI RAG (H-01) | HIGH | Yes |
| ChromaDB None tenant filter bypass (H-29) | HIGH | Latent |
| COMPANY docs visible to all internal users (H-15) | HIGH | By design |

### Properly Isolated Areas (Verified ✅)

| Area | Mechanism |
|------|----------|
| Document CRUD | `_base_query()` filters by `document.tenant_id` |
| User management | `UsersController` filters by tenant + hierarchy |
| Support tickets | `_check_ticket_access()` enforces tenant match |
| Portal documents | `VisibilitySpec.customer_portal()` scopes by companies + status |
| Customer feedback | Filtered by `user_id` + tenant |
| Chat conversations | `ConversationManager` scopes by `user_id` |
| Search | `_base_query()` tenant filter applied |
| Companies | Scoped to tenant |
| Invitations | Scoped via `resolve_invitation_tenant_id()` |

### Systemic Issue: Trust-the-Issuer Model
The collaboration layer achieves tenant isolation by trusting the JWT issuer. Once a token is issued, it's valid regardless of access revocation. The collab server has zero independent verification. If the backend issues a bad token, there is no safety net.

---

## 12. DOCUMENT LIFECYCLE & STATE MACHINE

### Intended State Machine
```
DRAFT → REVIEW → PUBLISHED → ACTIVE → ARCHIVED
                                  ↑        ↓
                                  └── DRAFT ←┘ (via restore)
```

### Actual Behavior
The state machine exists in `document_stage.py` but is systematically bypassed:

| Operation | Uses State Machine? | How It Bypasses |
|-----------|:------------------:|-----------------|
| `create_document()` | ✅ | Sets DRAFT correctly |
| `submit_for_review()` | ✅ | DRAFT→REVIEW via aggregate |
| `publish_version()` | ✅ | REVIEW→PUBLISHED via aggregate |
| `archive_document()` | ❌ | Direct `status = ARCHIVED` |
| `restore_document()` | ❌ | Direct `status = DRAFT` |
| `update_document()` (PUT) | ❌ | Accepts arbitrary `status` field (C-01) |
| Frontend ACTIVE→DRAFT | ❌ | Forces via raw PUT (transition not in SM) |
| `force_publish_version()` | ⚠️ | Uses aggregate but route guard too weak |

### Key Findings
- C-01 (CRITICAL): PUT endpoint allows editor→publish escalation
- C-03 (CRITICAL): Archive/restore bypass state machine entirely
- H-16 (HIGH): State machine bypass creates orphaned reviews
- H-17 (HIGH): Missing ACTIVE→DRAFT forces all code to bypass
- M-10 (MEDIUM): ACTIVE is terminal — no transitions defined out of it

### Verdict
**The state machine is decorative, not enforced.** It covers the "happy path" but every operation that doesn't fit the model bypasses it. The investment in domain aggregates and transition rules provides zero actual governance.

---

## 13. COLLABORATION & REAL-TIME

### Architecture
- Hocuspocus WebSocket server + Y.js CRDT for real-time editing
- Collab JWT with 60-min expiry, issued by backend
- `documentAuthStore` tracks per-document auth tokens
- IndexedDB persistence for offline resilience
- Redis pub/sub for multi-instance sync
- Auto-save debounced (2s/max 10s) via `Database.store`
- Token refresh every 45 min on frontend

### What Works Well
- Y.js CRDT is mathematically correct for conflict resolution
- Exponential backoff on reconnection (1s→30s)
- IndexedDB provides genuine offline resilience
- Connection registry tracks per-document presence

### What's Broken — The 60-Minute Time Bomb

```
0 min:  Token issued, collaboration starts, auto-save works     ✅
45 min: Frontend refreshes token into tokenRef.current          ✅
        ...but never sends new token to collab server           ❌
60 min: Original token expires                                   
        collab-server tries auto-save → backend returns 401      ❌
        console.error("No write-capable token") → returns        ❌
        Client never notified                                    ❌
        User continues editing, believing work is saved          ❌
∞ min:  User closes browser. Work is gone.                      ❌
```

| Finding | Severity |
|---------|----------|
| Token refresh doesn't reach collab server (C-06) | CRITICAL |
| Silent persistence failure (C-07) | CRITICAL |
| No real-time access revocation — 60-min window (C-08) | CRITICAL |
| No independent tenant verification (C-13) | CRITICAL |
| Token-document binding not validated (C-14) | CRITICAL |
| Document status not enforced during collab (H-30) | HIGH |
| WebSocket re-auth missing (H-19) | HIGH |

### Verdict
**Architecturally sound, operationally dangerous.** The CRDT foundation, Hocuspocus relay, and IndexedDB offline support are well-chosen. But the token lifecycle gap means any session >60 minutes will silently lose persistence. This is the single most dangerous finding for user-facing data loss.

---

## 14. AI ASSISTANT & RAG

### Architecture
- Ollama local LLM (llama3.1:8b, 4096 token context)
- ChromaDB for document embeddings with tenant filtering
- 29+ tools with per-tool permission checks
- Hybrid keyword+embedding tool routing
- SSE streaming with heartbeats
- Auto-summarization on long conversations (>20 messages)
- Separate Chat DB (3rd SQLite database)

### What Works Well
- 5-layer tenant isolation (conversation, tools, ChromaDB, access policies, system prompt)
- Generic error messages to users (internals in logs only)
- Tool registry with centralized error handling
- @mention path correctly validates document access

### What's Broken

| Finding | Severity | Impact |
|---------|----------|--------|
| `document_ids` bypasses tenant isolation (H-01) | HIGH | Cross-tenant data leakage |
| Prompt injection via system-role messages (H-02) | HIGH | LLM behavior hijack |
| Context window overflow drops safety prompt (H-03) | HIGH | Safety bypass |
| RAG tools read draft versions (H-04) | HIGH | Unpublished content exposure |
| LLM output unsanitized (H-05) | HIGH | Stored XSS potential |
| In-memory rate limiter bypassed in multi-worker (M-22) | MEDIUM | Decorative rate limiting |
| Tool result prompt injection (M-23) | MEDIUM | Indirect LLM manipulation |

### Systemic Issue: Unsafe Content Injection Architecture
Untrusted document and file content is injected as `system`-role messages — the highest authority level in most LLMs. This is the LLM equivalent of executing user input as SQL. Combined with no output sanitization, a successful prompt injection flows: stored document → LLM → unsanitized display → XSS.

---

## 15. FILE UPLOAD & ATTACHMENTS

### Architecture
- UUID-based storage keys (no predictable filenames)
- HMAC-SHA256 signed download tickets with expiry
- Content-type validation + magic byte validation on upload
- DOCX/PPTX extraction pipeline → HTML conversion → bleach sanitization
- Avatar upload with Pillow re-encoding (strips metadata)
- bleach for HTML sanitization post-conversion

### What Works Well
- UUID storage keys prevent path enumeration
- HMAC download tickets with constant-time comparison
- bleach HTML sanitization on converted content
- Avatar re-encoding strips EXIF/metadata (best practice)
- File size limits enforced

### What's Broken

| Finding | Severity | Impact |
|---------|----------|--------|
| ZIP bomb on DOCX/PPTX — no decompression limits (H-07) | HIGH | OOM / DoS |
| XXE/entity expansion in XML parsing (H-08) | HIGH | Server resource exhaustion |
| Avatar missing magic byte validation (H-22) | HIGH | Script disguised as image |
| Frontend bypasses HMAC ticket system (H-23) | HIGH | Security architecture unused |
| Content-Type defaults to octet-stream (M-28) | MEDIUM | Content-sniffing risk |
| No antivirus scanning (M-29) | MEDIUM | Malware storage |
| Regex-based HTML parsing in extractor (M-30) | MEDIUM | Fragile, bypassable |

### Systemic Issue: Defense-in-Depth Not Connected
The codebase has HMAC-signed ticket system, magic byte validation, and bleach sanitization — all good security measures. But the primary frontend download path bypasses the ticket system, avatar upload skips magic byte validation, and the extraction pipeline uses stdlib XML instead of defusedxml. The security controls exist but aren't consistently wired into the paths that actually execute.

---

## 16. CUSTOMER PORTAL & PUBLIC SURFACE

### Architecture
- Public router: unauthenticated access to published documents, search, sitemap, RSS
- Customer portal: authenticated, role=customer, published + assigned documents only
- Portal uses `require_customer` dependency on most endpoints
- Three-layer internal note defense (query filter, API filter, schema exclusion)
- Custom HTML sanitizer for document rendering, DOMPurify for changelog

### What Works Well (Customer Portal)
- Tenant isolation enforced at every layer
- Published-only content serving
- 404 over 403 for access denied (prevents enumeration)
- Company deactivation immediately blocks access
- Internal note filtering is triple-defended
- Reading progress tracking with milestone saves

### What's Broken (Public Surface)

| Finding | Severity | Impact |
|---------|----------|--------|
| XML injection in sitemap via base_url (C-16) | CRITICAL | Public, unauthenticated exploit |
| SVG data URIs in custom sanitizer (Feature Review Public#2 — reclassified HIGH here) | HIGH | XSS via SVG decode in object/inline context |
| No rate limiting on any public endpoint (H-26) | HIGH | DB saturation via automated requests |
| Feedback content stored unsanitized (M-31) | MEDIUM | Stored XSS in admin views |
| NPS comments unsanitized (M-32) | MEDIUM | Stored XSS in admin views |
| Custom sanitizer vs DOMPurify inconsistency (M-37) | MEDIUM | Higher bypass probability |
| SQL wildcard injection in public search (M-36) | MEDIUM | `%` returns all results |

### Verdict
**Customer portal is the most robust flow in the system** — well-secured with proper tenant isolation. **Public surface is the most exposed attack surface** — unauthenticated, internet-facing, with XML injection, no rate limiting, and custom sanitizer instead of battle-tested libraries.

---

## 17. ENGINEERING QUALITY & ARCHITECTURE

### Current State (2026-03-26)

**Current project rating:** `8.6/10`

| Area | Current Rating | Notes |
|------|----------------|-------|
| Frontend | `8.9/10` | Shared guards, redirect flow, download flow, support UX, and regression coverage are materially stronger |
| Backend | `8.3/10` | Context-first boundaries, DI cleanup, split models, tracing, and explicit error policy materially improved maintainability |
| Architecture | `8.4/10` | No longer contradictory at the core; ADRs and architecture checks now govern direction |

| Item | Status | Current State |
|------|--------|---------------|
| `AW-1` | Closed | Context-first backend boundary documented and enforced |
| `AW-2` | Closed | `DocumentService` reduced and split across extracted collaborators |
| `AW-3` | Closed | Caller-side direct service construction replaced by DI/container paths |
| `AW-4` | Closed | Repository usage policy is explicit for aggregate-heavy write domains |
| `AW-5` | Closed | Model monolith split into focused modules |
| `AW-6` | Closed | Request and trace IDs propagate across services |
| `EQ-05` | Closed | Auth transaction flow tightened and regression-tested |
| `EQ-06` | Closed | Broad catches are policy-labeled and CI-enforced |
| `EQ-07` | Closed | Chat bridge now runs through durable outbox/event handling |
| `EQ-08` | Closed | Shared cache is explicit, bounded, and observable |
| `EQ-09` | Closed | Error-boundary policy standardized across service/application layers |
| `EQ-10` | Closed | Route auth guard duplication removed and prevented by checks |
| `EQ-11` | Closed | Collab disconnect lookup is indexed instead of O(N) |
| `EQ-12` | Closed | Comment depth traversal no longer performs N+1 parent loading |

The subsections that follow in section 17 are the original 2025 audit baseline and are retained for traceability.

### Historical Baseline Ratings (2025 audit)

| Aspect | Score | Notes |
|--------|-------|-------|
| Architecture & organization | 8.5/10 | Hybrid layer/feature structure, clean |
| State management | 9.5/10 | Textbook React Query + Zustand separation |
| API client | 9/10 | Mixin composition, DTO mapping, concurrent refresh |
| Component quality | 7.5/10 | DocumentDetailsView 19-prop drilling, duplicated MenuBar |
| Routing | 9/10 | Composable guards, lazy loading, error boundaries |
| Test coverage | 6/10 | 76 test files for 295 source files (26% ratio) |

### Backend: 5.5/10

| Aspect | Score | Notes |
|--------|-------|-------|
| Layering | 4/10 | Three competing patterns (DDD, CQRS, direct), no governance |
| Services | 5/10 | DocumentService god service (1750 lines, 41 methods) |
| Models | 6/10 | Correct schema, but single 2650-line file for 50+ classes |
| API design | 8/10 | Strong schemas, three competing error patterns |
| Data model | 8/10 | Good normalization, missing composite indexes |
| DI / Testability | 4/10 | Services create sub-services internally, untestable |
| Error handling | 5/10 | 19+ files with bare `except Exception` |
| Configuration | 8.5/10 | Pydantic BaseSettings, prod validation rejects insecure defaults |
| Middleware | 7.5/10 | 8 modules, correct order, but no request ID propagation |

### Architectural Weaknesses

| # | Weakness | Impact |
|---|----------|--------|
| AW-1 | Three competing backend patterns (DDD/CQRS/layered) | Onboarding confusion, contradictory architecture |
| AW-2 | DocumentService god service (1,750 lines, 41 methods) | Change risk, untestable, gravitational center |
| AW-3 | Service coupling via direct instantiation (not DI) | Cannot mock for testing; bypasses container |
| AW-4 | Vestigial repository layer (7 repos vs 25+ services with own queries) | Inconsistent abstraction |
| AW-5 | Single-file model monolith (2,650 lines, 3 databases) | Navigation nightmare |
| AW-6 | No request tracing across services | Impossible to debug cross-service issues |

### CQRS Is Architectural Theater
Command handlers are pass-through wrappers:
```python
def _execute_use_case(self, context):
    return self.service.create_document(command.document_data, command.current_user)
```
No command replay. No event sourcing. No aggregate-level invariant enforcement. The `Result<T, CommandError>` return type forces boilerplate error-mapping in every calling route — adding complexity without capability.

### Key Code Quality Findings

| ID | Title | Severity |
|----|-------|----------|
| EQ-05 | Transaction race conditions in auth service (6 commits in login()) | HIGH |
| EQ-06 | Bare `except Exception` in 19+ files | HIGH |
| EQ-07 | Silent chat bridging data loss | MEDIUM |
| EQ-08 | Module-level thread-shared cache without metrics | MEDIUM |
| EQ-09 | Three competing error patterns (DomainError, HTTPException, Result) | MEDIUM |
| EQ-10 | 9+ locally redefined auth guards | LOW |
| EQ-11 | O(N) connection lookup in collab server | LOW |
| EQ-12 | N+1 ORM queries in comment depth traversal | LOW |

---

## 18. REMEDIATION PRIORITY MATRIX

### Completion Status (2026-03-26)

| Track | Status | Notes |
|-------|--------|-------|
| Tier 1 | Completed | Immediate exploit and guard-gap fixes landed |
| Tier 2 | Completed | Core architecture, isolation, lifecycle, and collaboration fixes landed |
| Tier 3 | Completed | Hardening and UX/maintainability follow-through landed |
| `AW-*` and `EQ-*` follow-through | Completed | ADRs, architecture checks, tracing, DI cleanup, model split, and error policy landed |

### Audit Closure Snapshot

| Area | Status | Examples |
|------|--------|----------|
| Security-critical runtime controls | Closed | Token type checks, session invalidation, rate limiting, signed cache invalidation |
| Data integrity and lifecycle | Closed | State transitions, review preflight usage, collab token refresh, durable chat bridging |
| User and support operations | Closed | Email verification, admin force-reset, role notifications, support notifications and attachments |
| Public and portal hardening | Closed | Sitemap consolidation, XML escaping, CSP/security headers, customer-only NPS, sanitized feedback/NPS |
| Architecture and maintainability | Closed | Context-first ADR, repository policy ADR, split models, reduced `DocumentService`, tracing, CI guardrails |

### Checkpoint Commits
- `54dae6b` `Refactor backend architecture boundaries`
- `496c836` `Propagate request tracing across services`
- `7101df8` `Unify backend error boundaries and reliability guards`

The original priority matrix is retained below as the historical execution plan.

Prioritized by **exploitability × impact × blast radius**. Effort: XS (<1 hour), S (hours), M (1-2 days), L (3+ days).

### Tier 1: Stop-the-Bleeding (Do First — All XS/S Effort)

| # | Finding | Fix | Effort |
|---|---------|-----|--------|
| 1 | **C-01**: PUT /documents allows status bypass | Remove `status` from `DocumentUpdate` schema | XS |
| 2 | **C-11**: Password reset URL mismatch | Change `/login?reset_token=` to `/reset-password?token=` | XS |
| 3 | **C-16**: XML injection in sitemap | Apply `xml.sax.saxutils.escape()` to `base_url` | XS |
| 4 | **C-17**: Session inactivity doesn't revoke | Add `session.revoked = True; db.commit()` | XS |
| 5 | **H-06**: WebSocket message bypasses sanitization | Apply `sanitize_html_content()` in WS handler | XS |
| 6 | **H-18**: Route guard mismatch on publish | Change to `require_manager`/`require_system_admin` | XS |
| 7 | **H-22**: Avatar missing magic byte check | Add `_validate_magic_bytes()` call | XS |
| 8 | **H-11**: Email disabled warning | Log startup warning when `EMAIL_ENABLED=False` | XS |
| 9 | **H-13**: Login timing enumeration | Add dummy bcrypt work for non-existent users | XS |
| 10 | **H-24**: User CRUD no route-level guard | Add `Depends(require_admin)` to management routes | XS |
| 11 | **C-10**: No session invalidation on role change | Add `revoke_all_user_sessions()` to role-change path | S |
| 12 | **C-09**: Invitation race condition | Add `with_for_update()` on invitation lookup | S |
| 13 | **C-05**: Review approval race condition | Add `with_for_update()` on review query | S |
| 14 | **C-18**: DELETE user missing cascade | Copy cascade from PUT deactivation path | S |
| 15 | **H-09**: Password reset doesn't revoke sessions | Copy block from `change_password()` | S |

**Tier 1 Total: 15 fixes, ~1-2 days of work. Closes 9 CRITICAL and 6 HIGH findings.**

### Tier 2: Architecture Fixes (Do Next — S/M Effort)

| # | Finding | Fix | Effort |
|---|---------|-----|--------|
| 16 | **C-02**: Token type not validated | Add `type` claim check in all verification paths | S |
| 17 | **C-04**: RBAC empty-set fallback | Change fallback to deny-all | S |
| 18 | **H-01**: document_ids cross-tenant leak | Add tenant filter + access check | S |
| 19 | **C-12**: Cross-tenant chat | Add tenant filter to user lookup | S |
| 20 | **C-14**: Token-document binding | Validate `document_id` claim matches requested doc | S |
| 21 | **C-15**: Cross-tenant user enumeration | Add tenant filter to chat user query | S |
| 22 | **H-04**: RAG tools read drafts | Add `is_published` filter | S |
| 23 | **H-02**: Prompt injection via system role | Change to user role with framing | S |
| 24 | **H-07**: ZIP bomb protection | Add decompression ratio check | S |
| 25 | **H-08**: XXE protection | Replace with `defusedxml` throughout | S |
| 26 | **H-10**: O(n) bcrypt DoS | Wire up `token_prefix` column | S |
| 27 | **H-15**: COMPANY visibility cross-tenant | Add `document.tenant_id == user.tenant_id` filter | S |
| 28 | **H-16**: Orphaned reviews | Auto-cancel PENDING reviews on revert to DRAFT | S |
| 29 | **H-30**: Collab ignores document status | Check `document.status` in permission check | S |
| 30 | **H-31**: Orphaned reviews on deactivation | Auto-cancel/reassign on deactivation | S |
| 31 | **C-03**: State machine bypass | Route archive/restore through state machine | M |
| 32 | **C-06 + C-07**: Collab token lifecycle | Reconnect provider on refresh, propagate save failures | M |
| 33 | **C-08**: Collab access revocation | Periodic permission re-check (every 5 min) | M |
| 34 | **C-13**: Collab server tenant verification | Add tenant_id to token, verify independently | M |
| 35 | **H-25**: RBAC guardrails | Add permission invariants per role | M |
| 36 | **H-27**: Support ticket state machine | Implement allowed transitions per role | M |

**Tier 2 Total: 21 fixes, ~2-3 weeks. Closes remaining 9 CRITICAL and most HIGH findings.**

### Tier 3: Hardening (Schedule Into Sprints)

| # | Finding | Fix | Effort |
|---|---------|-----|--------|
| 37 | M-31, M-32 | Sanitize feedback + NPS content | XS |
| 38 | M-33 | NPS `require_customer` | XS |
| 39 | M-52 | Import Zod schema on reset page | XS |
| 40 | M-27 | Remove legacy JWT-in-URL fallback | XS |
| 41 | H-14 | Atomic rate limiting (Redis INCR) | S |
| 42 | M-38 | Fix LIKE wildcard injection in autocomplete | S |
| 43 | M-36 | Fix SQL wildcard in public search | S |
| 44 | H-26 | Rate limit public endpoints | S |
| 45 | M-40 | Rate limit search endpoints | S |
| 46 | H-19 | WebSocket periodic re-auth | M |
| 47 | H-32 | Auth service transaction atomicity | M |
| 48 | H-12 | Implement invitation email sending | M |
| 49 | AW-2 | Split DocumentService god service | L |
| 50 | AW-1 | Standardize on one backend pattern | L |

### Effort Summary

| Tier | Fixes | Effort | CRITICAL Closed | HIGH Closed |
|------|-------|--------|-----------------|-------------|
| Tier 1 | 15 | ~1-2 days | 9 | 6 |
| Tier 2 | 21 | ~2-3 weeks | 9 | 13 |
| Tier 3 | 14 | ~3-4 weeks | 0 | 5 |
| **Total** | **50** | **~6-8 weeks** | **18** | **24** |

---

## 19. FINAL VERDICT

### Current Production Readiness by Subsystem (2026-03-26)

| Subsystem | Current Verdict | Notes |
|-----------|-----------------|-------|
| Frontend | Ready | Shared guards, safer redirects, upload hardening, and green regression sweep |
| Authentication | Ready | Token validation, rate limiting, reset flow, and session invalidation gaps were closed |
| Authorization (RBAC) | Ready | Route-level and permission-layer gaps were closed and checked |
| Document Lifecycle | Ready | State transitions and review/publication flows are enforced through validated paths |
| Review Workflow | Ready with monitoring | Complex workflow, but original correctness and race issues were addressed |
| Collaboration | Ready with monitoring | Distributed path is materially safer; keep normal operational monitoring on reconnect/save flows |
| AI Assistant | Ready with guardrails | Isolation, validation, and rate-limiting posture materially improved |
| File Upload | Ready | Signed downloads, malware scanning, XML hardening, and validation paths are wired in |
| Customer Portal | Ready | Still one of the stronger areas of the product |
| Public Surface | Ready | XML, rate limiting, and sanitization issues from the original audit were addressed |
| Support Tickets | Ready | Sanitization parity, notifications, realtime parity, and attachments are now present |
| Password Reset | Ready | Functional, guarded, and rate-limited |
| User Management | Ready | Verification, recovery, session invalidation, and notification gaps were closed |

### Bottom Line (Current)

The original audit verdict of "NOT READY" is no longer the correct verdict for the current codebase.

Current assessment:
1. The project is ready for controlled production use.
2. The highest-risk trust-boundary failures, lifecycle gaps, cross-service inconsistencies, and architectural contradictions identified in this report were addressed and regression-tested.
3. Confidence is high for the issues covered by this audit and moderate for true load/performance behavior, which was outside the original review scope.

### Recommendation (Current)

Close this audit. Keep this file as the historical baseline plus closure record, and track only new work under the normal engineering backlog for performance, scale, and continued refactoring.

### Production Readiness by Subsystem (Historical Baseline)

| Subsystem | Verdict | Critical Issues |
|-----------|---------|-----------------|
| **Frontend** | ✅ Ready (with minor fixes) | Prop drilling in one view, duplicated MenuBar |
| **Authentication** | ⚠️ Needs Tier 1 fixes | Token type validation, session lifecycle gaps |
| **Authorization (RBAC)** | ❌ Not ready | Empty-set fallback, status bypass, route guard gaps |
| **Document Lifecycle** | ❌ Not ready | State machine bypassed on every non-happy-path |
| **Review Workflow** | ⚠️ Functional but racey | Concurrent approval race, orphaned reviews |
| **Collaboration** | ❌ Not ready | 60-min data loss time bomb, tenant verification gaps |
| **AI Assistant** | ⚠️ Impressive but vulnerable | Cross-tenant data leak, prompt injection, draft exposure |
| **File Upload** | ⚠️ Needs Tier 2 fixes | ZIP bomb, XXE, magic byte gaps |
| **Customer Portal** | ✅ Well-secured | Sanitization gaps only |
| **Public Surface** | ❌ Not ready | XML injection, no rate limiting, custom sanitizer |
| **Support Tickets** | ⚠️ Functional with gaps | No state machine, XSS via WebSocket |
| **Password Reset** | ❌ Broken | URL mismatch renders feature non-functional |
| **User Management** | ⚠️ Needs Tier 1 fixes | Session cascade gaps, route guard gaps |

### Systemic Patterns (The Root Causes)

These five patterns explain most of the 148 findings:

1. **Check-but-don't-enforce** (23 findings): Session inactivity checks but doesn't revoke. Rate limiting checks but races. State machine exists but is bypassed. Preflight exists but is never called. The security mechanism starts executing but doesn't complete.

2. **Trust-the-issuer** (15 findings): Collab server trusts JWT completely. ChromaDB trusts tenant_id from caller. WebSocket trusts initial auth forever. Once a credential is issued, it's valid regardless of downstream changes.

3. **Inconsistent defensive depth** (22 findings): Deactivate cascades sessions; delete doesn't. REST sanitizes; WebSocket doesn't. @mention validates access; document_ids doesn't. The same security control exists on some paths but not parallel ones.

4. **Opt-in security** (12 findings): `require_tenant_match()` is available but not mandatory. Route guards are applied inconsistently. defusedxml exists as a concept but isn't installed. The security tool exists but its use is optional.

5. **Decorative architecture** (8 findings): State machine exists but is bypassed. CQRS bus exists but handlers are pass-through. Repository layer exists but most services build own queries. The architectural structure communicates intent that the code doesn't fulfill.

### The Bottom Line

> **The system is not failing because it is unfinished. It is failing because core trust boundaries are inconsistently enforced. That is worse than an incomplete product, because it creates false confidence.**

The architecture is sophisticated and well-structured. The issues are not from incompetence — they're from the gap between "security mechanisms exist" and "security mechanisms are consistently enforced on every path."

**The good news:** The top 15 fixes (Tier 1) are mostly XS/S effort — 1-2 days of work to close 9 CRITICAL and 6 HIGH findings. The bones are good. The remediation path is clear and achievable.

**Recommendation:** Execute Tier 1 immediately (1-2 days). Schedule Tier 2 as a focused sprint (2-3 weeks). Tier 3 can be integrated into normal development. After Tier 1+2 completion, re-audit the CRITICAL and HIGH findings to verify closure. The system is close to production-ready — it needs disciplined enforcement, not a rewrite.

---

*End of Audit. Total unique findings: 148. Total immediately exploitable: ~28. Estimated remediation: 6-8 weeks for full resolution.*
