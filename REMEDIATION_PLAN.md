# Audit Remediation Plan

> Based on the full project audit of 2025-03-23 — 148 deduplicated findings.
> That audit and the execution plans that closed it were removed from the tree
> once complete; read them with `git show 8d19e6c:PROJECT_FULL_AUDIT_FINAL.md`.
> Format mirrors existing `PRD.md` wave structure.
> Codebase-verified: 8 findings confirmed fixed, 1 accepted by-design, 5 partially fixed, rest open.

---

## Verified Fixed (excluded from plan)

| Finding | Why excluded |
|---------|-------------|
| C-04 | RBAC empty-set returns `set()`, not max permissions |
| C-11 | Reset URL correctly points to `{BASE_URL}/login?reset_token=` |
| C-14 | `documentAuthStore` validates `document_id` claim vs requested doc |
| C-16 | Sitemap doesn't interpolate `base_url`; no injection vector |
| C-17 | Session inactivity blocked at auth layer + cleanup worker |
| H-18 | `publish_version` gated by MANAGER+ in service layer |
| H-26 | Global `RateLimitMiddleware` covers public endpoints |
| H-29 | `add_chunks()` raises on `None` tenant; callers enforce |

## Accepted By-Design

| Finding | Decision |
|---------|----------|
| C-12 | SYSTEM_ADMIN cross-tenant chat is intentional |

---

## Wave AI — Critical Hot Fixes

> Tier 1 · ~1-2 days · Closes remaining exploitable CRITICAL + HIGH findings with minimal code changes

### Why this wave exists
These are stop-the-bleeding fixes — each item is a live vulnerability that can be exploited with minimal effort. Every fix is XS/S effort. This wave should ship as a hotfix before any other work begins.

### Non-negotiable outcomes
- No endpoint allows arbitrary document status changes
- All session-bearing operations (role change, password reset, user delete) cascade to session revocation
- Race conditions on invitation acceptance and review approval are locked
- WebSocket message path sanitizes HTML
- Avatar upload validates file content, not just headers
- User CRUD routes enforce admin role at the route level

### In scope
- Document status field removal from update schema
- Session cascade on role change, password reset, user deletion
- Row-level locking on invitation acceptance and review approval
- WebSocket message sanitization
- Avatar magic byte validation
- Route-level role guards on user CRUD

### Out of scope
- Token type system overhaul (Wave AJ)
- Collab-server architecture changes (Wave AK)
- State machine centralization (Wave AL)

### Exit criteria
- [ ] All 10 items implemented and passing tests
- [ ] Zero CRITICAL findings exploitable via the fixed paths
- [ ] Security contract tests cover each fix

---

### Critical Fixes
- [ ] AI-001: Remove `status` from `DocumentUpdate` schema — `backend/app/schemas/__init__.py` currently has `status: Optional[DocumentStatus] = None` on `DocumentUpdate`. Remove it entirely so `PUT /documents/{id}` cannot set status. Status transitions must only happen through dedicated endpoints.
- [ ] AI-002: Add session revocation on role change — `backend/app/web/controllers/management/users_controller.py` logs a `SecurityEvent` when role changes but does NOT revoke sessions. Copy the cascade logic from the deactivation path (lines ~293-305) into the role-change branch (lines ~384-388). Call `revoke_all_user_sessions()` and invalidate refresh tokens.
- [ ] AI-003: Add row-level lock on invitation acceptance — `backend/app/api/management/auth.py` `accept_invitation` does a plain `get_by_token()` lookup with no lock. Add `with_for_update()` to the invitation query to prevent two concurrent requests from both reading `status=PENDING` and creating duplicate users.
- [ ] AI-004: Add row-level lock on review approval — `backend/app/application/commands/review_commands.py` uses optimistic locking on audience but has no `SELECT ... FOR UPDATE` on the `ReviewRequest` row itself. Add `with_for_update()` to the review query in the approve handler.
- [ ] AI-005: Add session cascade to DELETE user — `backend/app/web/controllers/management/users_controller.py` `delete_user()` only sets `is_active = False` and logs a `SecurityEvent`. Copy session/token revocation from the deactivation path. Revoke `UserSession` rows and invalidate refresh tokens.

### Sanitization & Validation
- [ ] AI-006: Sanitize WebSocket support messages — `backend/app/ws/support_ws.py` `_handle_send_message` stores content directly without sanitization and broadcasts it. The REST path (`support_service.py`) sanitizes but the WS path bypasses it. Add `sanitize_html_content()` call before storing and broadcasting.
- [ ] AI-007: Revoke sessions after password reset — `backend/app/services/auth_service.py` `reset_password()` invalidates `PasswordReset` records but does NOT revoke `UserSession` rows or refresh tokens. Copy session revocation logic from `change_password()`.
- [ ] AI-008: Fix login timing side-channel — `backend/app/services/auth_service.py` `login()` returns early with 401 when user is `None` without doing dummy bcrypt work, leaking timing. The password reset path already has a dummy hash. Add `bcrypt.checkpw(dummy_password, dummy_hash)` before returning when user is `None`.
- [ ] AI-009: Add magic byte validation to avatar upload — `backend/app/api/management/users.py` avatar upload only checks `file.content_type` (client-supplied MIME header). Call the existing `_validate_magic_bytes()` from the attachment service to verify actual file content.
- [ ] AI-010: Add route-level role guards to user CRUD — `backend/app/api/management/users.py` uses `Depends(get_current_active_user)` on `list_users`, `create_user`, `update_user`, `delete_user`. Change to `Depends(require_admin)`. Only `/admin/users/{user_id}/unlock` currently has it.

### Wave AI — Tests
- [ ] AI-T01: `PUT /documents/{id}` with `status=active` in body → verify status field ignored/rejected (document stays in current state)
- [ ] AI-T02: Change user role → query `UserSession` → verify all old sessions have `revoked_at` set
- [ ] AI-T03: Two concurrent `POST /auth/accept-invitation` with same token → verify only one user created, second gets 400/409
- [ ] AI-T04: Two concurrent review approvals on same review → verify only one succeeds, second gets 409
- [ ] AI-T05: `DELETE /users/{id}` → verify `UserSession.revoked_at` set and refresh tokens invalidated
- [ ] AI-T06: Send WebSocket support message containing `<script>alert(1)</script>` → verify sanitized in DB and broadcast
- [ ] AI-T07: Complete password reset → query `UserSession` → verify old sessions revoked
- [ ] AI-T08: Measure response time: login with non-existent username ≈ login with wrong password (within 50ms)
- [ ] AI-T09: Upload avatar with `.jpg` extension but PDF content → verify 400 rejected
- [ ] AI-T10: Non-admin `GET /api/v1/users` → verify 403

---

## Wave AJ — Token & Auth Hardening

> Tier 2a · ~3-5 days · Fixes fundamental token system flaw + auth transaction atomicity

### Why this wave exists
The token system has no type checking — access, refresh, and collaboration tokens are interchangeable. This means any token signed with the JWT secret can authenticate as a regular user. Combined with auth service transaction atomicity issues and rate limit race conditions, these underpin the security of everything else.

### Non-negotiable outcomes
- Each token type is validated against its expected `type` claim
- Refresh token rotation is atomic
- Rate limiting is race-condition-free
- Login flow uses a single DB transaction
- Invitation emails are actually sent

### In scope
- Token type claim addition and verification
- Rate limit atomicity
- Auth service transaction consolidation
- Session ID salting
- Invitation rate limiting
- Refresh token atomicity
- Invitation email implementation

### Out of scope
- WebSocket token re-validation (Wave AK)
- Password reset workflow changes beyond session revocation (done in Wave AI)

### Exit criteria
- [ ] All 7 items implemented and passing tests
- [ ] Collab token cannot authenticate at regular API endpoints
- [ ] Refresh token cannot be used as access token
- [ ] Rate limiter passes concurrent stress test

---

### Token System
- [ ] AJ-001: Validate token `type` claim in all verification paths — `backend/app/security.py` `get_current_user()` and `backend/app/auth_context/token_service.py` `verify_token()` never check the `type` claim. Add `type` field to all token payloads during creation (`access`, `refresh`, `collaboration`). In `get_current_user()`, verify `payload.get("type") == "access"`. In refresh endpoint, verify `type == "refresh"`. In collab-server, verify `type == "collaboration"`.

### Auth Hardening
- [ ] AJ-002: Make rate limiting atomic — `backend/app/middleware/rate_limit.py` has a check-then-record pattern. Replace with atomic increment: either Redis `INCR` with TTL or SQLite `INSERT OR REPLACE` with atomic count. Prevents concurrent requests from bypassing the limit.
- [ ] AJ-003: Consolidate auth service transactions — `backend/app/services/auth_service.py` login flow performs 6 separate commits. Wrap the entire login flow (user lookup, session creation, token generation, audit log) in a single transaction with one commit at the end.
- [ ] AJ-004: Salt session ID hashing — `backend/app/services/auth_service.py` hashes session IDs without a per-session salt. Add a random salt column to `UserSession`, use `hashlib.sha256(salt + session_id)` instead of plain hash.
- [ ] AJ-005: Rate limit invitation endpoints — Add rate limit decorator (10 req/min) to invitation create and resend endpoints in `backend/app/api/management/`.
- [ ] AJ-006: Atomic refresh token rotation — `backend/app/services/auth_service.py` refresh token rotation is not wrapped in a single transaction. Wrap old-token-invalidation + new-token-creation in one atomic transaction to prevent token reuse during race conditions.
- [ ] AJ-007: Implement invitation email sending — `backend/app/services/auth_service.py` creates invitations but email sending is not implemented. Wire existing `email_service.py` to send invitation link when invitation is created.

### Wave AJ — Tests
- [ ] AJ-T01: Attempt API auth with refresh token → verify 401 (type mismatch)
- [ ] AJ-T02: Attempt API auth with collaboration token → verify 401 (type mismatch)
- [ ] AJ-T03: Send 100 concurrent login requests → verify rate limiter is atomic (no over-count, exactly N allowed)
- [ ] AJ-T04: Login flow → assert exactly 1 DB commit (mock/count commits)
- [ ] AJ-T05: Create invitation → verify `email_service.send()` called with correct URL
- [ ] AJ-T06: Concurrent refresh token rotation → verify old token invalidated, only one new token created
- [ ] AJ-T07: Two invitations to same user within 10 seconds → verify rate limited

---

## Wave AK — Collaboration Security

> Tier 2b · ~1-2 weeks · Fixes collab-server: token lifecycle, tenant isolation, persistence, access revocation

### Why this wave exists
The collab-server is the highest-risk subsystem. It has no tenant awareness, no token refresh propagation (refreshed tokens never reach the WebSocket), silent data loss on persistence failure, and no access revocation for connected users. Combined, these create a 60-minute window where revoked users retain full edit access with no error feedback.

### Non-negotiable outcomes
- Refreshed collab tokens propagate to the WebSocket connection
- Persistence failures are surfaced to the user
- Revoked users are disconnected within 5 minutes
- Collab tokens carry and enforce `tenant_id`
- Cross-tenant user enumeration via chat returns uniform errors
- Document status is enforced during collaboration

### In scope
- Token refresh propagation to collab-server
- Persistence failure notification
- Periodic permission re-check in collab-server
- Tenant ID in collab tokens
- Uniform error responses for cross-tenant chat
- WebSocket periodic re-auth
- Activity logging access verification
- Document status enforcement in collab

### Out of scope
- Full chat architecture redesign
- Real-time collab for read-only viewers (deferred, M-16 documented but low priority)

### Exit criteria
- [ ] All 12 items implemented and passing tests
- [ ] Revoked user disconnected from collab within 5 min (integration test)
- [ ] Persistence failure shows toast to user (E2E test)
- [ ] Collab token without `tenant_id` rejected (unit test)

---

### Token Lifecycle
- [ ] AK-001: Propagate refreshed collab token to server — `frontend/src/lib/useCollaboration.ts` refreshes the token every 45 min but only stores it in `tokenRef.current`. The Hocuspocus provider keeps using the original token. After refresh, either call `provider.disconnect()` + `provider.connect()` with new token, or implement a `setToken` mechanism that updates the WebSocket auth.
- [ ] AK-002: Surface persistence failures to user — `collab-server/src/server/collabServerApp.ts` `store` callback ignores `PersistenceResult { success: false }`. Broadcast an error event to connected clients via WebSocket awareness. In frontend, show toast notification "Document save failed — your changes may not be persisted."
- [ ] AK-003: Add periodic permission re-check — In `collab-server/src/server/collabServerApp.ts`, add a `setInterval` (every 5 min) that re-validates each connected user's JWT + access permissions. Disconnect users whose sessions are revoked or expired.

### Tenant Isolation
- [ ] AK-004: Add `tenant_id` to collab token — Backend token generation must include `tenant_id` claim in collaboration JWTs. Update `collab-server/src/types.ts` `CollabTokenPayload` to include `tenant_id`. In `onAuthenticate`, verify `tenant_id` is present and matches the document's tenant (requires a lookup or trust the claim + verify at connection time).
- [ ] AK-005: Uniform error for cross-tenant chat user lookup — `backend/app/services/chat_service.py` `create_direct_chat` returns different errors for "not found" vs "different tenant" (404 vs 403), enabling user enumeration. Return 404 for both cases.

### Connection Security
- [ ] AK-006: Periodic JWT re-validation in collab-server — Tied to AK-003. After re-validating the JWT, also check `exp` claim. If the token is expired and no refresh has occurred (AK-001), disconnect the client.
- [ ] AK-007: Verify document access on activity logging — `collab-server/src/` activity logging endpoint accepts writes without verifying the user has access to the document. Add document access check before persisting activity.
- [ ] AK-008: Validate token claims in persistence layer — `collab-server/src/persistence.ts` trusts tokens blindly. Verify that the token's `document_id` matches the document being persisted.
- [ ] AK-009: Enforce document status during collaboration — Check `document.status` before granting write access in collab-server. Only `DRAFT` documents should allow editing via WebSocket. `ACTIVE`/`ARCHIVED` documents should be read-only.
- [ ] AK-010: Fetch fresh token on reconnect — `frontend/src/lib/useCollaboration.ts` reconnection logic reuses potentially expired collab token. On reconnect event, fetch a fresh token from the backend before re-establishing the WebSocket.
- [ ] AK-011: Allow read-only WebSocket for viewers — Currently read-only viewers cannot join WebSocket. Allow `read-only` connections for live viewing without edit capability (send awareness/cursor data only).
- [ ] AK-012: Add document-level auth to state endpoints — Collab state/snapshot HTTP endpoints may lack document-level access verification. Add `can_view_document()` check before serving state.

### Wave AK — Tests
- [ ] AK-T01: Refresh collab token → verify new token reaches collab-server (mock WS, check auth message)
- [ ] AK-T02: Simulate persistence failure → verify client receives error notification via WS
- [ ] AK-T03: Revoke user session → verify user disconnected from collab within 5 min (integration test)
- [ ] AK-T04: Collab token without `tenant_id` claim → verify `onAuthenticate` rejects connection
- [ ] AK-T05: `create_direct_chat` with user in different tenant → verify 404 (not 403)
- [ ] AK-T06: Connect to collab for ARCHIVED document → verify write operations rejected

---

## Wave AL — Document Lifecycle & RBAC

> Tier 2c · ~1 week · Centralizes state machine, fixes review workflow, hardens permission model

### Why this wave exists
Document state transitions are validated ad-hoc per method rather than through a centralized state machine. Reviews are orphaned when documents are edited or reviewers are deactivated. Several RBAC gaps allow unintended cross-tenant access or stale permission caching.

### Non-negotiable outcomes
- All document state transitions go through one centralized state machine
- Pending reviews are auto-cancelled when documents revert to DRAFT
- RBAC policy overrides cannot remove mandatory role permissions
- Support ticket status transitions are enforced
- Optimistic locking prevents lost metadata updates

### In scope
- Centralized `DocumentStateMachine` with all valid transitions
- Review auto-cancellation on DRAFT revert
- RBAC permission invariants
- Support ticket state machine
- Optimistic locking for document metadata
- COMPANY visibility tenant filtering

### Out of scope
- Collaboration-level document status enforcement (Wave AK)
- Full RBAC redesign

### Exit criteria
- [ ] All 11 items implemented and passing tests
- [ ] Invalid state transitions raise `InvalidStateError` (parameterized test)
- [ ] RBAC override cannot remove admin mandatory permissions (invariant test)
- [ ] Concurrent document metadata update returns 409 (integration test)

---

### State Machine
- [ ] AL-001: Centralize document state machine — Create `DocumentStateMachine` class in `backend/app/services/document_service.py` (or new module) that defines all valid transitions as a dict: `{(from_status, to_status): required_permission}`. Route archive, restore, publish, revert-to-draft, and all other transitions through `StateMachine.transition(document, target_status, user)`. Remove ad-hoc status checks from individual methods.
- [ ] AL-002: Add `tenant_id` filter to COMPANY visibility queries — Documents with `COMPANY` visibility are currently visible to all internal users across tenants. Add `Document.tenant_id == current_user.tenant_id` filter to COMPANY visibility document queries.
- [ ] AL-003: Auto-cancel pending reviews on DRAFT revert — When a document's status changes back to `DRAFT` (edit after submission), automatically cancel any `PENDING` `ReviewRequest` records for that document. Notify the reviewer.
- [ ] AL-004: Add ACTIVE→DRAFT transition — The state machine currently treats ACTIVE as a terminal state. Add `ACTIVE→DRAFT` as a valid transition requiring MANAGER+ permission, to allow re-editing published content.
- [ ] AL-005: Add RBAC permission invariants — `backend/app/services/rbac_service.py` RBAC override currently has no guardrails. Add invariant checks per role (e.g., `admin` always has `MANAGE_USERS`, `system_admin` always has all permissions). Reject overrides that violate invariants.

### Review Workflow
- [ ] AL-006: Implement support ticket state machine — Create `TicketStateMachine` enforcing valid transitions: `open→in_progress→resolved→closed`, `resolved→open` (reopen). Reject invalid transitions like `closed→in_progress`.
- [ ] AL-007: Auto-cancel reviews on reviewer deactivation — When a user is deactivated, find all their `PENDING` review assignments. Auto-cancel or reassign to the next eligible reviewer. Notify document authors.

### RBAC & Access
- [ ] AL-008: Fix permission cache nullable tenant key — `backend/app/services/permissions.py` permission check cache uses `tenant_id` in key, but `tenant_id` can be `None`. Make tenant key required or handle `None` explicitly to prevent cross-tenant cache hits.
- [ ] AL-009: Document that frontend `RoleGuard` is UX-only — Add code comment to `RoleGuard` component clarifying it is cosmetic only and all enforcement happens server-side. This is by-design.
- [ ] AL-010: Add optimistic locking to document metadata — Use `Document.row_version` (if exists) or add one. On `PUT /documents/{id}`, require `If-Match` header with current version. Return 409 on version mismatch.
- [ ] AL-011: Define ACTIVE transitions in state machine — In the centralized state machine (AL-001), explicitly define allowed transitions from ACTIVE: at minimum `ACTIVE→ARCHIVED` and `ACTIVE→DRAFT` (AL-004).

### Wave AL — Tests
- [ ] AL-T01: Attempt `DRAFT→ARCHIVED` directly → verify rejected by state machine (must go through ACTIVE first or per defined rules)
- [ ] AL-T02: Query COMPANY-visibility documents as different tenant user → verify 0 results
- [ ] AL-T03: Edit document with PENDING review → verify review auto-cancelled and reviewer notified
- [ ] AL-T04: RBAC override removing `MANAGE_USERS` from admin role → verify 400 rejected
- [ ] AL-T05: Support ticket `closed→in_progress` → verify 400 rejected
- [ ] AL-T06: Two concurrent `PUT /documents/{id}` with same `row_version` → verify second returns 409
- [ ] AL-T07: Deactivate user with PENDING review assignment → verify review reassigned/cancelled

---

## Wave AM — AI Assistant Security

> Tier 2d · ~3-5 days · Fixes cross-tenant data exposure, prompt injection, and output sanitization in AI layer

### Why this wave exists
The AI assistant has a cross-tenant data exposure via `document_ids` parameter that bypasses tenant isolation entirely, prompt injection vectors through @mention and file content, context window overflow that can drop the safety prompt, and unsanitized LLM output rendering.

### Non-negotiable outcomes
- `document_ids` parameter enforces tenant isolation and access policy
- User-provided content is in the `user` role, not `system` role
- Context window management preserves safety prompt
- LLM output is sanitized before rendering
- RAG only returns published documents

### In scope
- `document_ids` tenant filter + access check
- Prompt role separation
- Context window truncation strategy
- RAG published-only filter
- LLM output sanitization
- Rate limiter TTL expiry
- Tool result fencing

### Out of scope
- AI content editing workflow (Phase 17)
- Full RAG re-architecture

### Exit criteria
- [ ] All 8 items implemented and passing tests
- [ ] Cross-tenant `document_ids` query returns 0 results (integration test)
- [ ] RAG query returns only published documents (unit test)
- [ ] LLM output with XSS payload is sanitized (component test)

---

### Tenant Isolation
- [ ] AM-001: Add tenant filter to `document_ids` — `backend/app/assistant/engine.py` line ~355 fetches documents by ID with no tenant filter and no access policy check. Add `Document.tenant_id == tenant_id` filter and `_policy.can_view_document()` check, matching the `@mention` fallback path at line ~394.
- [ ] AM-002: Move user content to `user` role — `backend/app/assistant/` prompt construction injects @mention content and uploaded file content as `system` role messages. Move to `user` role to prevent prompt injection from elevating user-provided content to system-level instructions.
- [ ] AM-003: Preserve safety prompt on context overflow — When context exceeds `num_ctx`, the safety system prompt may be dropped. Implement truncation strategy: always keep system prompt, truncate conversation history from the middle (keep first + last N messages), and truncate tool results before conversation.
- [ ] AM-004: Filter RAG to published documents only — `backend/app/assistant/rag/` queries should add `is_published=True` or `status=active` filter. Draft/unpublished versions should not be returned in RAG results.

### Output Safety
- [ ] AM-005: Sanitize LLM output before rendering — Frontend renders LLM markdown without sanitization. Pipe output through `DOMPurify` or equivalent before rendering in `AssistantMessageList` component.
- [ ] AM-006: Add TTL to in-memory rate limiter — `backend/app/assistant/` rate limiter entries never expire, causing memory leak on long-running processes. Add TTL-based expiry (e.g., entries older than the rate window are pruned). Document single-instance limitation.
- [ ] AM-007: Fence tool results in prompt — Tool results injected into the prompt could contain LLM instructions. Wrap tool results in delimiter markers (e.g., `<tool_result>...</tool_result>`) and instruct the system prompt to treat delimited content as data, not instructions.
- [ ] AM-008: Document system admin cross-tenant RAG access — ChromaDB tenant isolation is intentionally bypassed for system admins. Add code comment and explicit guard: `if not user.is_system_admin: raise`.

### Wave AM — Tests
- [ ] AM-T01: AI query with `document_ids` containing cross-tenant document ID → verify filtered out, not returned in context
- [ ] AM-T02: Document content with `@mention` containing `Ignore all previous instructions` → verify treated as user content, not system instruction
- [ ] AM-T03: RAG query → verify only documents with `status=active` / `is_published=True` returned
- [ ] AM-T04: LLM response containing `<script>alert(1)</script>` → verify sanitized in frontend render
- [ ] AM-T05: Rate limiter with expired entries → verify memory is reclaimed after TTL

---

## Wave AN — Upload & Input Hardening

> Tier 2-3 · ~3-5 days · ZIP bomb protection, XXE defense, magic byte validation, input sanitization

### Why this wave exists
File upload paths lack ZIP bomb protection (DOCX/PPTX are ZIP archives), XXE defense (stdlib `xml.etree` is used instead of `defusedxml`), and several input fields across the app store unsanitized content that could enable stored XSS.

### Non-negotiable outcomes
- DOCX/PPTX extraction rejects ZIP bombs (>100:1 ratio)
- All XML parsing uses `defusedxml` (no stdlib ET)
- Legacy JWT-in-URL download fallback removed
- Feedback, NPS, announcement, and changelog content sanitized server-side
- Frontend file picker matches backend accepted types

### In scope
- ZIP decompression ratio check
- `defusedxml` replacement
- JWT-in-URL removal
- Content-Type inference from magic bytes
- Server-side sanitization for feedback/NPS/announcement/changelog
- Frontend upload type alignment
- Magic byte argument order fix

### Out of scope
- Antivirus integration (document as accepted risk, defer)
- Full sanitizer replacement (evaluate in AO-016)

### Exit criteria
- [ ] All 9 items implemented and passing tests
- [ ] `import xml.etree` appears nowhere in codebase (grep check)
- [ ] ZIP bomb test file rejected (integration test)
- [ ] `?token=` download path returns 400 (integration test)

---

### File Security
- [ ] AN-001: Add ZIP bomb protection — `backend/app/conversion/docx_extractor.py` and `pptx_extractor.py` use `zipfile` directly with no decompression limits. Add: (1) max decompressed size (500MB default), (2) decompression ratio check (reject >100:1), (3) max file count in archive (10,000 default).
- [ ] AN-002: Replace stdlib XML with defusedxml — Both extractors use `from xml.etree import ElementTree as ET`. Add `defusedxml` to `backend/requirements.txt`. Replace all `xml.etree.ElementTree` imports with `defusedxml.ElementTree`. This addresses H-08, H-28, and M-26 simultaneously.
- [ ] AN-003: Remove legacy JWT-in-URL download fallback — Download endpoints may still accept `?token=` query parameter as a legacy fallback. Remove this code path. All downloads should use header-based authentication or signed download tickets.
- [ ] AN-004: Infer Content-Type from magic bytes — Currently defaults to `application/octet-stream` when extension is unknown. Use `python-magic` or the existing magic byte validation to set accurate Content-Type headers on download responses.
- [ ] AN-005: Document antivirus as accepted risk — ClamAV integration would add significant infrastructure complexity. Document as accepted risk in `docs/` with recommendation to add when deploying to production with untrusted uploads. Add a `# TODO: AV scan` comment at the upload entry point.
- [ ] AN-006: Fix DOCX extraction HTML parsing — `backend/app/conversion/docx_extractor.py` uses regex for HTML parsing. Replace with `html.parser` from stdlib or `lxml` for more reliable and secure parsing.

### Input Sanitization
- [ ] AN-007: Sanitize feedback and NPS content — `backend/app/services/` stores feedback content and NPS comments without sanitization. Add `sanitize_html_content()` call before persisting. Addresses M-31 and M-32.
- [ ] AN-008: Sanitize announcement and changelog content server-side — Announcement creation and changelog entries rely solely on client-side DOMPurify. Add server-side sanitization in the create/update service methods. Addresses M-34 and M-35.
- [ ] AN-009: Fix frontend upload types and magic byte argument order — Frontend file picker allows PDF but backend rejects it (L-06). Either add PDF to backend allowed types or remove from frontend. Fix wrong argument order in `_validate_magic_bytes` (L-07).

### Wave AN — Tests
- [ ] AN-T01: Upload crafted DOCX with 1000:1 compression ratio → verify 400 rejected with "ZIP bomb detected" message
- [ ] AN-T02: Upload DOCX containing XXE entity expansion → verify no expansion occurs (defusedxml blocks it)
- [ ] AN-T03: Attempt download with `?token=<jwt>` query param → verify 400 or param ignored
- [ ] AN-T04: Submit feedback with `<script>alert(1)</script>` in content → verify sanitized in database
- [ ] AN-T05: Upload file with `.docx` extension but PNG content → verify correct Content-Type on download
- [ ] AN-T06: `grep -r "from xml.etree" backend/` → verify 0 results (all replaced with defusedxml)

---

## Wave AO — Portal, Search & Support Hardening

> Tier 3 · ~1 week · Medium-severity input validation, search injection, and support workflow gaps

### Why this wave exists
Multiple medium-severity findings across the portal, search, and support subsystems: SQL wildcard injection, missing rate limits, unbounded queries, and support workflow gaps. None are immediately critical but they harden the user-facing surfaces against abuse.

### Non-negotiable outcomes
- SQL LIKE patterns escape wildcards
- Public search endpoints are rate-limited
- Notification queries are bounded
- Closed support tickets reject new messages
- REST and WebSocket support message paths are consistent

### In scope
- SQL wildcard escaping
- Search/notification rate limiting and bounds
- NPS role enforcement
- Support ticket status enforcement
- REST→WS broadcast for support
- Customer notification on agent reply
- Password complexity alignment
- Token prefix optimization
- Admin-created user email verification

### Out of scope
- Email notification infrastructure redesign
- Full search re-architecture

### Exit criteria
- [ ] All 16 items implemented and passing tests
- [ ] LIKE injection test with `%admin%` returns safe results (integration test)
- [ ] Notification limit capped at 100 (integration test)
- [ ] Closed ticket message rejected (integration test)

---

### Search & Input Safety
- [ ] AO-001: Enforce `require_customer` on NPS endpoints — NPS endpoints don't check caller role. Add `Depends(require_customer)` to NPS submission and dismissal routes.
- [ ] AO-002: Escape SQL wildcards in public search — Public search endpoint passes user input directly to LIKE patterns. Escape `%` and `_` characters before constructing LIKE clauses.
- [ ] AO-003: Escape SQL wildcards in autocomplete — Same LIKE wildcard injection in autocomplete queries. Apply same escaping.
- [ ] AO-004: Validate document access on search click — Search click-tracking endpoint accepts arbitrary `document_id` without verifying caller has access. Add `can_view_document()` check.
- [ ] AO-005: Rate limit search endpoints — Add per-endpoint rate limiting to search routes (e.g., 60 req/min for search, 30 req/min for autocomplete).
- [ ] AO-006: Cap notification `limit` parameter — `GET /notifications` accepts unbounded `limit` (currently allows 500+). Cap at 100, default to 20.

### User & Auth
- [ ] AO-007: Email verification for admin-created users — Admin-created users skip email verification. Either send verification email or document as intentional (admin-created users are pre-trusted).
- [ ] AO-008: Notify user on role change — When a user's role changes, create an in-app notification and optionally send email. Currently only a `SecurityEvent` is logged.

### Support Workflow
- [ ] AO-009: Broadcast WS event on REST support message — REST-created support messages (`POST /support/tickets/{id}/messages`) don't trigger WebSocket broadcast. Add WS broadcast after REST message creation so real-time participants see the message.
- [ ] AO-010: Notify customer on agent reply — When an agent replies to a support ticket, create a notification for the customer. Currently no notification is sent.
- [ ] AO-011: Reject messages on CLOSED tickets — Customer can still POST messages to CLOSED tickets via API. Add status check: reject messages when `ticket.status == CLOSED`.
- [ ] AO-012: Sanitize AI-created support tickets — `CreateSupportTicketTool` in AI assistant bypasses content sanitization. Add `sanitize_html_content()` in the tool's `execute()` method.
- [ ] AO-013: Wire email notifications for ticket events — Add email notifications for: ticket created (to assigned agents), agent reply (to customer), status change (to customer). Wire through existing `email_service.py`.

### Password Reset Polish
- [ ] AO-014: Wire up `token_prefix` column — `PasswordReset.token_prefix` column exists but is never populated. On token creation, store the first 8 characters of the hashed token for O(1) lookup instead of O(n) bcrypt comparisons. Addresses H-10.
- [ ] AO-015: Align reset page password complexity — Frontend password reset page doesn't import the shared Zod validation schema used on registration. Import and apply the same schema for consistent enforcement.
- [ ] AO-016: Evaluate custom sanitizer vs DOMPurify — The document viewer uses a custom HTML sanitizer instead of DOMPurify. Evaluate whether to replace with DOMPurify or document the rationale for the custom implementation. If custom is kept, add comprehensive XSS test suite.

### Wave AO — Tests
- [ ] AO-T01: Public search with `%admin%` payload → verify `%` escaped in SQL (no wildcard match on "admin")
- [ ] AO-T02: `GET /notifications?limit=10000` → verify response limited to 100 items
- [ ] AO-T03: Customer `POST /portal/support/tickets/{id}/messages` on CLOSED ticket → verify 400
- [ ] AO-T04: Agent REST reply to ticket → verify WebSocket broadcast includes the message
- [ ] AO-T05: Password reset page → verify Zod schema matches registration complexity rules
- [ ] AO-T06: NPS submission without customer role → verify 403
- [ ] AO-T07: AI `CreateSupportTicketTool` with HTML in content → verify sanitized

---

## Wave AP — Architecture, Quality & LOW/INFO Cleanup

> Tier 3 · ~1-2 weeks · Remaining LOW and INFO findings — dead code, minor hardening, UX, architecture debt

### Why this wave exists
None of these items are exploitable as-is, but they improve maintainability, defense-in-depth, and UX quality. They're grouped by subsystem for efficient implementation.

### Non-negotiable outcomes
- Dead code removed
- Audit logging covers invitation acceptance and profile edits
- Viewers cannot read DRAFT documents
- FTS5 query syntax abuse prevented
- Error details not leaked in analytics export

### In scope
All LOW and INFO findings not covered by previous waves.

### Out of scope
- Items requiring major architecture changes (DocumentService split, pattern standardization — tracked separately)
- Feature additions masquerading as fixes

### Exit criteria
- [ ] All items implemented or documented as accepted risk
- [ ] Dead code grep check passes
- [ ] Viewer DRAFT access returns 403 (integration test)
- [ ] Analytics export error response contains no stack trace (integration test)

---

### Auth & UX Polish
- [ ] AP-001: Remove dead `account_locked` UI code (L-01) — Frontend has dead code for account locked state that's never triggered. Remove the unused component/branch.
- [ ] AP-002: Distinguish network errors from credential errors (L-02) — Login page shows same error for network failure and wrong credentials. Show "Network error — please try again" for connection failures.
- [ ] AP-003: Add return-URL after auth redirect (L-03) — When unauthenticated user is redirected to login, preserve the original URL and redirect back after successful login.
- [ ] AP-004: Fix logout to revoke only current session (L-04) — `logout()` currently revokes ALL user sessions, not just the current one. Change to revoke only the session ID from the current token.
- [ ] AP-005: Persist rate limiter state across restarts (L-14) — In-memory rate limiter resets on server restart. For single-instance deployment, accept this risk but document it. For future multi-instance, recommend Redis.
- [ ] AP-006: Rate limit password reset verification (L-33) — Add rate limiting to the reset token verification endpoint to prevent brute-force token guessing.

### Compliance & Audit
- [ ] AP-007: Audit log invitation acceptance (L-05) — No audit log entry is created when a user accepts an invitation. Add `AuditLog` creation in the acceptance handler.
- [ ] AP-008: Audit log self-profile edits (M-45) — Self-profile updates (name, avatar, preferences) have no audit trail. Add `AuditLog` creation for profile changes.
- [ ] AP-009: Fix module-level document cache tenant key (M-09) — Module-level cache uses `tenant_id` in key but doesn't validate tenant isolation properly. Review and fix cache key construction.

### Collaboration Polish
- [ ] AP-010: Add reconnection backoff jitter (L-09) — WebSocket reconnection uses fixed intervals, creating thundering herd on server recovery. Add random jitter (±20%) to backoff intervals.
- [ ] AP-011: Make session end request reliable (L-10) — Collab session end request is fire-and-forget. Add retry with timeout for graceful session cleanup.
- [ ] AP-012: Cascade soft delete to collab sessions (M-07) — Soft-deleting a document doesn't terminate active collaboration sessions. Add cascade that disconnects collab users when document is soft-deleted.
- [ ] AP-013: Document non-collaborative auto-save gap (M-11) — When editing without collab-server (single user, offline), there's no auto-save. Document this limitation and add localStorage draft recovery (may already exist from X-005).

### RBAC & Access Polish
- [ ] AP-014: Fix comments accessible to customers on management router (L-20) — Management comment endpoints are accessible to customer-role users. Add role guard or move customer-facing comment endpoints to portal router.
- [ ] AP-015: Fix attachment management accessible to customers (L-21) — Same issue: management attachment endpoints accessible to customers. Add appropriate role guards.
- [ ] AP-016: Prevent viewers from reading DRAFT documents (L-22) — Viewers can currently access DRAFT documents. Add `status != DRAFT or user.role >= editor` check to document access policy.
- [ ] AP-017: Add ownership check on document edit/delete (L-23) — No ownership check exists — any editor in the tenant can edit/delete any document. Consider adding optional ownership checks or document this as intentional (tenant-wide editing).
- [ ] AP-018: Consolidate locally redefined auth guards (L-34) — Auth guards are redefined in multiple files instead of using shared definitions. Consolidate to prevent enforcement drift.

### Search & Analytics
- [ ] AP-019: Tenant-partition FTS5 index (L-24) — Full-text search index is not partitioned by tenant. Add `tenant_id` to FTS5 index or filter results post-query with tenant check.
- [ ] AP-020: Explicit tenant scoping in analytics (L-25) — Analytics queries implicitly scope by tenant through joins. Add explicit `tenant_id` filter for defense-in-depth.
- [ ] AP-021: Redact error details in analytics export (L-26) — Analytics export error responses may include stack traces. Return generic error message for non-admin users.
- [ ] AP-022: Restrict search analytics cross-tenant (L-27) — Search analytics may expose raw search queries from other tenants. Add tenant filter.
- [ ] AP-023: Sanitize FTS5 query syntax (L-28) — FTS5 accepts advanced operators (`NEAR()`, `NOT`, etc.) that could be abused. Escape or restrict to simple term matching for user-facing search.
- [ ] AP-024: Add ownership check to audience churn endpoint (L-31) — Endpoint lacks document ownership verification. Add access check.

### User & Support Polish
- [ ] AP-025: Fix user enumeration via invitation errors (L-15) — Invitation creation and user creation return distinct errors that confirm user existence. Return uniform error messages.
- [ ] AP-026: Sanitize invitation message field (L-16) — Invitation custom message is not sanitized. Add sanitization before storing/sending.
- [ ] AP-027: Check tenant suspension on profile update (L-17) — Self-profile updates bypass tenant suspension check. Add suspension check to profile update path.
- [ ] AP-028: Hash invitation tokens (L-18) — Invitation tokens are stored as plaintext in DB. Hash before storage, compare with hash on acceptance.
- [ ] AP-029: Add file attachments to support ticket messages (L-29) — Currently no file attachment support on ticket messages. Add upload capability similar to chat file messages.
- [ ] AP-030: Notify agents on new support tickets (L-30) — No agent notification when new tickets are created. Add notification to available/assigned agents.
- [ ] AP-031: Add admin force-reset password (M-43 / I-04) — No admin capability to force a password reset for another user. Add endpoint and UI.
- [ ] AP-032: Remove file deduplication gap (L-32) — No deduplication for uploaded files. Add content-hash-based dedup check before storage (or document as accepted).

### Informational Items
- [ ] AP-033: Remove unused ticket download system (I-01) — Declared but unused. Clean up dead code.
- [ ] AP-034: Document shared JWT secret sync requirement (I-02) — Collab-server and backend share JWT secret that requires manual sync. Document the requirement and add startup validation.
- [ ] AP-035: Persist NPS dismiss state (I-03) — NPS dismissal is not persisted across page refreshes. Store dismiss state in user preferences or localStorage.
- [ ] AP-036: Remove duplicate sitemap endpoints (I-05) — Two sitemap endpoints exist with different security postures. Remove the duplicate.
- [ ] AP-037: Add CSP headers to XML endpoints (I-06) — XML endpoints lack Content-Security-Policy headers. Add appropriate headers.
- [ ] AP-038: Cap list inputs on ChatRequest (I-07) — `ChatRequest` schema accepts uncapped list sizes. Add `max_items` validation.
- [ ] AP-039: Sanitize conversation title (I-08) — AI conversation titles are not sanitized. Add sanitization before storage.
- [ ] AP-040: Fix ConnectionRegistry O(N) lookup (I-09) — Collab-server `ConnectionRegistry` uses O(N) scan on disconnect. Add index/map for O(1) lookup.
- [ ] AP-041: Fix comment depth N+1 queries (I-10) — Comment tree traversal causes N+1 ORM queries. Add `selectinload` for nested comments.
- [ ] AP-042: Fix feature flag defaults (I-11) — Feature flags default to `True` in production. Change defaults to `False` (safe-off pattern).
- [ ] AP-043: Add tech debt tracking (I-12) — No systematic tech debt tracking. Add `# TECH-DEBT:` comment convention and CI counter.

### Wave AP — Tests
- [ ] AP-T01: Invitation acceptance → verify audit log entry created with user ID, invitation ID, timestamp
- [ ] AP-T02: Viewer `GET /documents/{id}` where document is DRAFT → verify 403
- [ ] AP-T03: FTS5 search query with `NEAR(term1 term2)` → verify sanitized/rejected
- [ ] AP-T04: Analytics export error as non-admin → verify no stack trace in response body
- [ ] AP-T05: Logout → verify only current session revoked (other sessions still valid)
- [ ] AP-T06: Soft-delete document with active collab session → verify collab users disconnected

---

## Summary

| Wave | Focus | Items | Effort | CRITICAL Closed | HIGH Closed |
|------|-------|-------|--------|-----------------|-------------|
| **AI** | Critical Hot Fixes | 10 | ~1-2 days | 5 | 5 |
| **AJ** | Token & Auth Hardening | 7 | ~3-5 days | 1 | 3 |
| **AK** | Collaboration Security | 12 | ~1-2 weeks | 4 | 4 |
| **AL** | Document Lifecycle & RBAC | 11 | ~1 week | 1 | 5 |
| **AM** | AI Assistant Security | 8 | ~3-5 days | 0 | 5 |
| **AN** | Upload & Input Hardening | 9 | ~3-5 days | 0 | 3 |
| **AO** | Portal, Search & Support | 16 | ~1 week | 0 | 1 |
| **AP** | Architecture & Quality | 43 | ~1-2 weeks | 0 | 0 |
| **Total** | | **116** | **~6-8 weeks** | **11** | **26** |

> **Note:** 8 findings excluded (verified fixed), 1 accepted by-design, 5 partially fixed (reduced scope in plan). Remaining ~23 findings from the original 148 are MEDIUM/LOW items absorbed into wave task descriptions (e.g., M-06 RBAC override confirmation → part of AL-005; M-12 unused preflight review → part of AL dead code cleanup; M-13 deactivated reviewer approval → part of AL-007; M-14 document state before review → part of AL state machine; M-18-M-21 tenant isolation → distributed across AK and AP).

### Parallelization Strategy
```
Week 1:       [====== Wave AI (Critical Hot Fixes) ======]
Week 2-3:     [==== Wave AJ (Auth) ====] [==== Wave AM (AI) ====]     ← parallel
Week 2-4:     [========== Wave AK (Collab) ==========]                 ← parallel with AJ/AM
Week 3-4:     [======= Wave AL (Document/RBAC) =======]
Week 4-5:     [==== Wave AN (Upload) ====]
Week 5-6:     [======= Wave AO (Portal/Search) =======]
Week 6-8:     [============ Wave AP (Quality) ============]
```

### Verification (after all waves)
1. Re-run static analysis against all 148 audit finding IDs — verify each is addressed or documented as accepted
2. Full test suite passes (existing + all new AI-T/AJ-T/AK-T/AL-T/AM-T/AN-T/AO-T/AP-T tests)
3. Security contract test: every management endpoint returns 401/403 appropriately
4. Invariant tests: self-registration, comment privacy, tenant isolation, published snapshot immutability
5. `grep -r "from xml.etree" backend/` → 0 results
6. `grep -r "status.*Optional.*DocumentStatus" backend/app/schemas/` → 0 results
7. `grep -r "token=" backend/app/api/` download paths → 0 results (no JWT-in-URL fallback)
