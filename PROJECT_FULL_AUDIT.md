# Project Full Audit

**Date:** 2026-03-18  
**Scope:** Deep static audit of the core backend, frontend, and collaboration server, plus a targeted backend test slice  
**Reviewed areas:** `backend/`, `frontend/`, `collab-server/`, top-level runtime config, selected tests, architecture docs  
**Verification note:** I traced behavior through code paths and ran `python -m pytest -o addopts='' tests/test_auth.py tests/test_comments.py tests/test_viewer_portal.py tests/test_attachments.py -q` from `backend/`. The sampled suite passed (`53 passed`) but produced `3833` warnings.

## 1. Executive Summary

This repository is architecturally ambitious and operationally inconsistent.

The good news:
- There is real engineering effort here. The codebase has meaningful layering, a serious permission model on paper, collaboration infrastructure, versioning, audience rules, and a frontend sanitizer that is better than average.
- The main HTTP auth path in `backend/app/security.py` is not toy code. It tracks sessions, inactivity, and revocation state.
- `backend/app/services/version_service.py` contains real publish-time checks and audience validation logic.

The bad news:
- Several of the most important system guarantees are false in practice.
- The code says "private comments", "published version only", "frontend-enforced role restrictions", and "public changelog". The runtime behavior does not consistently honor those promises.
- Auth is enforced differently depending on transport. HTTP requests, attachment downloads, collaboration, and WebSockets do not share one trustworthy security boundary.
- Publication state is not immutable. You can mutate what public, viewer, and customer users see without going through a clean publish flow.
- The public frontend contains XSS sinks, and the app stores bearer tokens in `localStorage`, which turns frontend injection into account takeover.

### Main strengths
- Strong architectural intent, especially around publish workflow and audience governance.
- Better-than-average HTML sanitization in `frontend/src/lib/htmlSanitizer.ts` and `frontend/src/lib/documentRenderer.tsx`.
- Reasonable separation between public, portal, viewer, and management concerns at the naming level.
- A broad test suite exists, and some auth/access parity tests are present.

### Main risks
- Broken authorization boundaries.
- Cross-tenant company enumeration in admin company management.
- Broken publication invariants.
- Review-state audience changes can invalidate what was actually reviewed.
- Stored XSS with bearer-token theft impact.
- GDPR export coverage is incomplete relative to the data the system actually stores.
- Production deployment still defaults to SQLite.
- High drift between documented behavior, UI behavior, and backend enforcement.
- Test coverage that looks reassuring while missing the wrong things.

### Severity meaning
- `Critical`: immediate trust-boundary, compliance, or release blocker.
- `High`: serious issue that can cause security, data-integrity, or operational damage, but is not the single most urgent blocker.
- `Medium`: meaningful reliability, maintainability, or policy weakness that should be fixed in planned work.
- `Low`: lower-risk inconsistency, naming problem, or cleanup item.

### Verification meaning
- `Verified`: directly traced in code paths, configuration, or sampled test behavior.
- `Potential`: strong indication of a real issue, but the exact production blast radius depends on runtime wiring or usage that was not fully executed during this audit.

### Executive triage

| Issue | Severity | Effort | Owner | Fix first? |
| --- | --- | --- | --- | --- |
| Public self-registration accepts caller-controlled role and tenant | Critical | Low | Backend/Auth | Yes |
| Company-management list leaks cross-tenant data | Critical | Low | Backend/RBAC | Yes |
| Download/WebSocket auth bypasses the main session model | Critical | Medium | Backend/Auth + Frontend | Yes |
| Comments privacy and route exposure are broken | Critical | Medium | Backend/Docs | Yes |
| Public XSS plus `localStorage` token storage enables account takeover | Critical | Medium | Frontend + Backend | Yes |
| **AI tools: editor can publish, self-approve, and set status to active** (3.27a-c) | **Critical** | Medium | Backend/AI | **Yes** |
| Publication — draft fallback and attachment leakage (auto-publish is by design) | High | High | Backend/Docs | Yes |
| **AI tools: all 33 write tools bypass service layer — no audit trail** (3.29) | **High** | High | Backend/AI | Yes |
| **AI tools: cross-tenant data exposure in 13 tools** (3.30) | **High** | Medium | Backend/AI | Yes |
| Real-time collab auth parity with main session model | High | Medium | Collab-server + Backend | Yes |
| Review-state audience can change after submission | Low (by design) | — | — | No |
| GDPR export omits user-linked data already stored by the system | Medium (later) | Medium | Backend/Compliance | No |

### Most urgent issues
- Block self-registration privilege escalation and tenant injection (force `customer` role on backend).
- Remove bearer tokens from query strings and stop using raw JWT verification outside the main auth path.
- Rebuild comment visibility and route access control.
- Scope company listing to the caller's tenant unless the caller is a system admin.
- Fix publication draft fallback and attachment leakage for public/portal reads (auto-publish itself is by design).
- Sanitize changelog and search output, then stop storing auth tokens in `localStorage`.
- Fix collab-server auth parity with the main session model (collab is actively used in production).
- Remove token-in-URL viewer access path.
- **Fix AI privilege escalations: remove `status` from EditDocumentTool params, route PublishDocumentTool through the publish command handler, enforce ReviewPolicy in SubmitReviewTool.**
- **Route all AI write tools through the service layer to restore audit trail, notifications, and state machine validation.**
- **Add tenant_id filtering to the 13 AI tools that currently allow cross-tenant access (especially those gated by VIEW_INTERNAL_DOCS or PUBLISH_DOCUMENT).**

### Deferred (by design / lower priority)
- GDPR export completion — nice-to-have for current stage, complete later.
- Review-state audience flexibility — intentional, optionally add audit logging.
- SQLite → PostgreSQL migration — when the author decides.
- Chat unification (document-scoped chats, feedback→chat) — planned architecture, not a bug.

### Overall verdict

**Project context (confirmed by author):**
- This is a **commercial product** built for a company. It will be presented for PR purposes.
- Currently deployed on **local machine only**, but must be ready to integrate into a cloud provider later.
- Staff users (editors, managers, admins) are created by sysadmin or other authorized users based on their role (pyramid model). Self-registration is for customers only.
- The role hierarchy is a pyramid: system_admin > admin > manager > editor > viewer > customer.

This is not production-ready in its current form, but the architecture is strong and most issues are fixable without redesign.

It is closer to "well-structured system with dangerous runtime shortcuts" than "messy prototype". The worst bugs are not style problems — they are trust-boundary failures that need fixing before any external exposure. For a commercial product that may be presented to a company, the XSS, self-registration escalation, and cross-tenant leaks are the must-fix items.

## 2. Critical Problems

### 2.1 Self-registration allows privilege escalation and tenant injection
- Severity: Critical
- Area: Auth / Security / Role Logic
- Verification: Verified
- Affected files:
  - `backend/app/api/management/auth.py:266-276`
  - `backend/app/services/auth_service.py:398-421`
  - `backend/app/schemas/__init__.py:39-44`
- Description:
  - The public `/auth/register` endpoint accepts a `UserCreate` payload that includes `role` and `tenant_id`.
  - The route docstring literally says "Only admins can set role other than viewer (enforced in frontend)."
  - The service persists `role=user_data.role` and `tenant_id=user_data.tenant_id` directly.
- Why it is a problem:
  - Frontend restrictions are not authorization.
  - A direct API caller can self-register as `admin`, `manager`, or `system_admin` if the enum allows it.
  - A direct API caller can inject themselves into an arbitrary tenant/company context.
- Example scenario:
  - An unauthenticated attacker posts `{"username":"x","email":"x@y.com","password":"...","role":"admin","tenant_id":7}` to `/api/v1/auth/register` and gets an elevated account.
- Recommended fix:
  - Remove `role` and `tenant_id` from public self-registration entirely.
  - Hard-force public registrations to `customer` role on the server (confirmed design intent).
  - Route all tenant-scoped/customer creation through invitation or admin-only flows.
  - Promotion from `customer` to any higher role must go through admin action.
  - Add tests that explicitly attempt elevated self-registration.
- **Design-intent note (confirmed by author):**
  - Self-registration is a production feature and should stay.
  - All self-registered users must land as `customer`. An admin promotes them if needed.
  - The backend must enforce this — the fix is to ignore the `role` field from the request payload and always set `customer`.
  - **Staff user creation** (editors, managers, admins) is done by sysadmin or other authorized users through the admin user-management flow — not through self-registration. Role hierarchy is a pyramid: system_admin > admin > manager > editor > viewer > customer.

### 2.2 Attachment downloads and WebSockets bypass the main auth/session model
- Severity: Critical
- Area: Auth / Security / API
- Verification: Verified
- Affected files:
  - `backend/app/api/management/attachments.py:35-102`
  - `backend/app/api/management/attachments.py:163-273`
  - `backend/app/security.py:63-123`
  - `backend/app/ws/chat_ws.py:35-43`
  - `backend/app/ws/support_ws.py:40`
  - `collab-server/src/auth.ts:36-38`
  - `frontend/src/lib/api/httpClient.ts:34-36`
  - `frontend/src/lib/api/httpClient.ts:96-107`
  - `frontend/src/lib/api/attachmentsApi.ts:49-54`
  - `frontend/src/hooks/useChatSocket.ts:37-40`
- Description:
  - Normal HTTP auth goes through `get_current_user`, which validates the JWT, checks session hash, checks revocation/inactivity, and writes session context into `request.state`.
  - Attachment downloads and reader-view endpoints accept a `token` query param and call `verify_token` directly.
  - Chat/support WebSockets also call `verify_token` directly.
  - Collaboration auth extracts tokens from URL query params.
  - The frontend puts tokens in `localStorage` and appends them to URLs.
- Why it is a problem:
  - URL tokens leak through browser history, logs, screenshots, and referrers.
  - Revoked or stale sessions can continue to function anywhere that only checks raw JWT validity.
  - The system has multiple auth truths instead of one.
- Example scenario:
  - A user is logged out or their session is revoked. Main API requests fail, but an old attachment URL or WebSocket token can still work until the JWT expires.
- Recommended fix:
  - Eliminate bearer tokens in query params.
  - Make all authenticated transports go through one shared validation policy that includes session revocation semantics.
  - For downloads, use short-lived one-time signed URLs or authenticated POST-to-download flows.
  - For WebSockets and collaboration, validate against a purpose-built, short-lived token tied to the session lifecycle, not just the JWT signature.

### 2.3 The comments permission model is broken and "private" comments are not private
- Severity: Critical
- Area: Role Logic / Security / Backend
- Verification: Verified
- Affected files:
  - `backend/app/api/management/comments.py:18-95`
  - `backend/app/services/comment_service.py:93-114`
  - `backend/app/services/comment_service.py:197-232`
  - `backend/app/services/comment_service.py:270-307`
  - `frontend/src/components/CommentsSection.tsx:270-280`
- Description:
  - The management comments API only depends on `get_current_active_user`. It is not internal-only.
  - `CommentService.get_comments()` and `create_comment()` enforce same-tenant access, not actual document visibility rules.
  - `can_view_comment()` ignores `comment.is_private`. It allows the author, system admins, or internal contributors. "Private" is not used as an actual access boundary.
  - The frontend `CommentsSection` exposes the private checkbox to any user who renders it.
- Why it is a problem:
  - Customers can hit internal comments endpoints as long as tenant checks pass.
  - A same-tenant customer can interact with comments on documents they should not be able to access through portal rules.
  - "Private" currently behaves like a label, not a permission boundary.
- Example scenario:
  - A customer from tenant A can POST to `/api/v1/documents/{id}/comments` on an internal document in tenant A if they know the document ID.
  - A customer can also mark their comment as private, even though the route docs say private comments are staff-only.
- Recommended fix:
  - Split comment access rules by audience and by route surface.
  - Use the same document access policy as the portal/viewer/public flows, not just tenant matching.
  - Enforce `is_private` on the backend with explicit role policy.
  - If comments are internal-only, require internal-user dependencies at the router level.
  - Add customer-specific tests that attempt to read and create comments on internal/company documents.
- **Design-intent note (confirmed by author):**
  - Inline comments (text-selection popup via `useInlineComments` hook) are the staying annotation method and are intentional.
  - The old comments tab was deliberately removed. Document-scoped chats are the planned replacement for threaded discussion.
  - Commenting on a document should open or create a chat with the document's author; multi-author documents create a group chat.
  - Inline comments will serve as "context cards" inside chat messages — showing the document title, section, and anchor text so recipients understand what is being discussed.
  - The security issues above (customer access to internal comment endpoints, `is_private` not enforced) still need fixing regardless of the migration plan.

### 2.4 Publication is not immutable: uploads can auto-publish and public-facing endpoints can serve draft/current state
- Severity: Critical
- Area: Logic / Backend / API / Product Flow
- Verification: Verified
- Affected files:
  - `backend/app/services/attachment_service/common.py:338-345`
  - `backend/app/services/attachment_service/upload.py:148-168`
  - `backend/app/api/public/documents.py:221-242`
  - `backend/app/application/queries/portal_queries.py:162-178`
  - `backend/app/application/queries/portal_queries.py:263-291`
  - `backend/app/api/viewer/documents.py:165-205`
- Description:
  - Attachment upload can create an initial `Version` with `is_published=True` and `published_at=attachment.uploaded_at`.
  - Public documents fall back to the latest draft version if no published version exists.
  - Public documents return all current attachments for the document.
  - Portal detail also resolves `published_versions or document.versions` and returns all current attachments.
  - Viewer has a version-specific attachment listing that respects a cutoff, but it also exposes a generic current-attachments endpoint.
- Why it is a problem:
  - The publish workflow exists, but there are side paths that bypass it.
  - What public/customer/viewer users see is not a trustworthy published snapshot.
  - Attachments added after publication can appear without republishing.
- Example scenario:
  - A document has a published version at v3.
  - Someone uploads a new attachment or an initial file through the upload path.
  - Public or portal consumers can now observe content/attachments that were never intentionally released through the normal publish flow.
- Recommended fix:
  - ~~Stop auto-publishing versions in attachment upload flows.~~ **(Auto-publish is intentional — see design note below.)**
  - Make public, viewer, and portal responses resolve only from an immutable published release object.
  - Associate attachments to versions or publish snapshots, not only to documents.
  - Remove draft fallback for public/customer reads unless there is an explicit product requirement and explicit permission.
- **Design-intent note (confirmed by author):**
  - Auto-publishing from uploads is intentional and should stay as a feature.
  - The remaining issues are still real: draft fallback for public reads, attachment leakage outside the published snapshot, and portal exposing mutable state. These should be fixed.
  - Severity adjusted from Critical to **High** for the remaining sub-issues (auto-publish itself is by design, not a bug).

### 2.5 Public changelog and public search are XSS sinks, and token storage makes the blast radius much worse
- Severity: Critical
- Area: Frontend / Security
- Verification: Verified
- Affected files:
  - `frontend/src/pages/public/PublicChangelogPage.tsx:79`
  - `frontend/src/pages/public/PublicSearchPage.tsx:64-69`
  - `frontend/src/pages/public/PublicSearchPage.tsx:182`
  - `frontend/src/pages/public/PublicSearchPage.tsx:188`
  - `backend/app/api/management/changelog.py:51-59`
  - `backend/app/api/public/documents.py:453-484`
  - `frontend/src/lib/api/httpClient.ts:34-36`
- Description:
  - The public changelog renders `entry.content` with `dangerouslySetInnerHTML` and no sanitization.
  - The public search page builds HTML by string replacement and injects it with `dangerouslySetInnerHTML`.
  - The backend search response passes raw title/snippet text through.
  - Access and refresh tokens are stored in `localStorage`.
- Why it is a problem:
  - Any XSS in this SPA can steal bearer tokens.
  - Public pages are same-origin pages. A logged-in admin visiting `/changelog` or `/search` is exposed.
  - Search is especially bad because it converts arbitrary text into HTML manually instead of rendering text safely.
- Example scenario:
  - A manager creates a changelog entry containing malicious markup.
  - An admin later views the public changelog page while logged in.
  - The script reads `localStorage.token` and exfiltrates it.
- Recommended fix:
  - Stop using `dangerouslySetInnerHTML` for search highlighting. Render text nodes and `<mark>` elements structurally.
  - Sanitize changelog HTML with the same rigor used for document rendering, or store a safe content format.
  - Move auth tokens out of `localStorage` into httpOnly secure cookies or another design that is not readable by injected script.

### 2.6 Unpublished changelog entries are publicly exposed by default
- Severity: High
- Area: API / Product Flow / Security
- Verification: Verified
- **Viewer design-intent note (confirmed by author):** The public viewer portal (screenshot: `localhost:3000/docs`) is the intended external-facing experience — a documentation library browsable by anyone. Users sign in for additional access. Token-in-URL shareable links are **not** the intended design. External viewers should authenticate (Option B). The token-in-URL viewer scheme should be replaced with auth-required access.
- Affected files:
  - `backend/app/api/management/changelog.py:36-59`
  - `backend/app/web/router_registry.py:90`
- Description:
  - `list_changelog()` is public.
  - `published_only` defaults to `False`.
  - The route docstring says "public: published only, admin: all", but that behavior is not enforced.
- Why it is a problem:
  - Unpublished release notes, planned features, or internal fixes can leak to any caller hitting `/api/v1/changelog`.
  - The route contract is misleading.
- Example scenario:
  - Product drafts a changelog entry for a not-yet-announced release.
  - Anyone can fetch `/api/v1/changelog` and see it because the default is not filtered.
- Recommended fix:
  - Make published-only the hard public default.
  - If admins need unpublished access, create a separate authenticated admin endpoint.

### 2.7 Company listing breaks tenant isolation for non-system admins
- Severity: Critical
- Area: Backend / Role Logic / Multi-Tenancy
- Verification: Verified
- Affected files:
  - `backend/app/api/management/companies.py:159-172`
- Description:
  - `list_companies()` requires `require_admin`, then starts from `db.query(Tenant)` with no tenant scoping for non-system admins.
  - The response includes company metadata plus aggregated counts like users and document totals.
- Why it is a problem:
  - Tenant isolation is one of the core trust boundaries in this product.
  - An ordinary tenant admin can enumerate other companies and infer business-sensitive information.
- Example scenario:
  - An admin from tenant A calls `GET /api/v1/companies` and sees tenant B's name, contact data, user count, and customer-visible document count.
- Recommended fix:
  - Restrict non-system-admin callers to `Tenant.id == current_user.tenant_id`.
  - If cross-tenant reporting is needed, make it explicit and system-admin-only.

### 2.8 GDPR export is materially incomplete
- Severity: Medium (reclassified — nice-to-have for current stage, will complete later)
- Area: Backend / Compliance / Data Governance
- Verification: Verified
- Affected files:
  - `backend/app/services/gdpr_service.py:101-199`
  - `backend/app/services/gdpr_service.py:314-315`
  - `backend/app/models/__init__.py:643-659`
  - `backend/app/models/__init__.py:1043-1115`
- Description:
  - The export includes profile, documents, comments, bookmarks, feedback, audit logs, reading progress, notifications, and attachment metadata.
  - It does not export `SecurityEvent`, `UserSession`, chat messages, or support messages even though the system stores them.
  - The deletion path explicitly deletes `SecurityEvent` and `UserSession`, which proves these are treated as user data elsewhere in the same service.
- Why it is a problem:
  - The system stores personal and behavioral data that the export omits.
  - That makes the export incomplete as a user-data access/export mechanism.
- Example scenario:
  - A user requests their data export and receives no login/session history and no chat/support transcript data even though both exist in the database.
- **Design-intent note (confirmed by author):**
  - GDPR compliance is a "nice-to-have" for the current stage. It will be completed later.
  - The export code and deletion code already exist — they just need to be expanded when the time comes.
- Recommended fix (when ready):
  - Expand the export to include sessions, security events, chat/support messages, and any other user-linked records.
  - Build a registry of user-data sources so this does not drift silently as new features are added.

### 2.9 Production Compose still defaults to SQLite
- Severity: Medium (reclassified — SQLite is accepted for current stage)
- Area: Architecture / Database / Deployment
- Verification: Verified
- Affected files:
  - `docker-compose.prod.yml:15`
- Description:
  - The production Compose file sets `DATABASE_URL=sqlite:///./data/portal.db`.
- Why it is a problem:
  - This system includes chat, collaboration, reviews, uploads, and general admin write traffic.
  - SQLite can hit lock contention under concurrent writes.
- **Design-intent note (confirmed by author):**
  - SQLite is the accepted database for the current development stage.
  - Migration to PostgreSQL/MySQL will happen when the author decides it is needed.
  - This is **not a bug** — it is a known trade-off for now.
- Recommendations for current state:
  - Enable WAL mode for better concurrent read performance: `PRAGMA journal_mode=WAL`.
  - Keep the PostgreSQL migration path ready (SQLAlchemy makes this straightforward).
  - When migrating, update `docker-compose.prod.yml`, add a PostgreSQL service, and switch `DATABASE_URL`.

### 2.10 Audience can be changed after review submission and before publication
- Severity: Low (reclassified — intentional flexibility)
- Area: Business Logic / Audit Integrity / Backend
- Verification: Verified
- Affected files:
  - `backend/app/services/document_service.py:818-874`
  - `backend/app/domain/aggregates/document_aggregate.py:36`
  - `backend/app/domain/states/review_stage.py:61`
- Description:
  - The document update path allows visibility and company assignment changes through the normal update flow.
  - `ensure_visibility_change_allowed()` is role-based only; it does not block edits while the document is in `PENDING_REVIEW`.
  - The review domain state blocks version modification while review is pending, but not document-level audience mutation.
- **Design-intent note (confirmed by author):**
  - This is intentional flexibility. The ability to change audience during review is by design.
  - Not a bug — the author wants this workflow flexibility.
- Improvement suggestion (optional):
  - Consider logging audience changes during pending review as audit events, so reviewers can check if the audience shifted since they started reviewing.
  - A UI indicator ("audience changed since review started") would add transparency without restricting the workflow.

## 3. Problems

### 3.1 Portal reading-progress endpoints leak metadata for documents that are no longer accessible
- Severity: High
- Category: Portal / Role Logic / Data Leakage
- Verification: Verified
- Affected files:
  - `backend/app/api/portal/documents.py:210-255`
- Description:
  - `/portal/reading-progress/recent` and `/portal/reading-progress/continue` only filter by `ReadingProgress.user_id`.
  - They join `Document` and return title/category/thumbnail without re-running `_ensure_customer_document_access`.
- Expected behavior:
  - If access to a document is revoked, customer-facing history endpoints should stop exposing its metadata.
- Current behavior:
  - A customer can continue seeing document metadata after company assignment or visibility changes.
- Recommendation:
  - Reuse portal access filtering for these endpoints, or precompute only currently visible reading history.

### 3.2 The "optional auth" dependency is broken twice
- Severity: Medium
- Category: Backend / Reliability
- Verification: Potential
- Affected files:
  - `backend/app/dependencies/permissions.py:325-365`
  - `backend/app/security.py:26`
- Description:
  - The helper is called `get_optional_current_user`, but it depends on `oauth2_scheme`, which is declared with default `auto_error=True`.
  - Missing bearer auth can fail before the helper ever returns `None`.
  - The exception path references `logger.warning(...)`, but the module defines `LOGGER`, not `logger`.
- Expected behavior:
  - Optional auth should be truly optional and should fail closed without throwing a `NameError`.
- Current behavior:
  - If this helper is wired into a real route, it is likely to behave incorrectly.
- Recommendation:
  - Use a dedicated optional bearer dependency with `auto_error=False`.
  - Fix the logger typo.
  - Add one direct unit test for "no token", one for "bad token", and one for "valid token".

### 3.3 API boundaries are semantically collapsed
- Severity: High
- Category: Architecture / Maintainability
- Verification: Verified
- Affected files:
  - `backend/app/web/router_registry.py:70-98`
  - `backend/app/api/management/changelog.py`
  - `frontend/src/pages/portal/CustomerDocumentPage.tsx:84`
  - `frontend/src/lib/api/searchEngagementApi.ts:169-176`
- Description:
  - Public, portal, viewer, and management are presented as separate surfaces, but the actual routing and client usage blur them.
  - The public changelog sits in a management router.
  - The customer portal updates reading progress through the management engagement API.
- Expected behavior:
  - Surface boundaries should map to actual policy boundaries and client contracts.
- Current behavior:
  - Policy intent is encoded in naming, comments, and UI flows more than in hard endpoint segmentation.
- Recommendation:
  - Separate surfaces physically and logically.
  - Stop letting portal/public behavior depend on management routes unless the route is explicitly intended to be shared.

### 3.4 Collaboration config and contract drift is real
- Severity: Medium
- Category: Collaboration / Configuration / Frontend
- Verification: Verified
- Affected files:
  - `backend/app/api/management/auth.py:521`
  - `frontend/src/lib/useCollaboration.ts:77`
  - `docker-compose.yml:49`
- Description:
  - The backend returns `websocket_url = ws://localhost:8002/document/{id}`.
  - The frontend ignores that and uses `VITE_COLLAB_SERVER_URL`.
  - Docker Compose sets `VITE_COLLAB_WS_URL`, which the frontend does not read.
- Expected behavior:
  - One source of truth for collaboration server location.
- Current behavior:
  - The API contract, frontend config, and Compose config disagree.
- Recommendation:
  - Pick one contract and delete the rest.
  - If the frontend owns the URL, remove it from the API response.
  - If the backend owns it, use it and stop hardcoding `localhost`.

### 3.5 Viewer page does not auto-select a version (by design)
- Severity: Low (reclassified — intentional UX)
- Category: Frontend / UX Flow
- Verification: Confirmed by author
- Affected files:
  - `frontend/src/pages/viewer/ViewerDocumentPage.tsx:124-127`
  - `frontend/src/pages/viewer/ViewerDocumentPage.tsx:351`
- Description:
  - The viewer page explicitly says "Viewer does not auto-select the latest version."
  - Until a version is selected, content and attachments are effectively blank.
- **Design-intent note (confirmed by author):**
  - This is intentional. The author wants users to browse the version list and choose which version to read.
  - Not a bug — it is a deliberate UX decision to show what versions exist before committing to one.
- Recommendation (optional UX polish):
  - Consider showing a brief "Select a version to view its content" message or a version overview card so first-time visitors understand the page is waiting for their selection.

### 3.6 The comments feature is mid-migration — dead code to clean up
- Severity: Low (reclassified — intentional migration, not a bug)
- Category: Product Flow / Maintainability
- Verification: Confirmed by author
- Affected files:
  - `frontend/src/pages/DocumentDetailPage.tsx:19` — stale comment referencing a non-existent "chat bridge"
  - `frontend/src/components/CommentsSection.tsx` — **dead code, confirmed safe to delete**
- Description:
  - The comments tab was deliberately removed as part of a design decision to replace threaded comments with document-scoped chats.
  - `CommentsSection.tsx` is never imported anywhere in the current codebase. It is confirmed dead code.
  - The inline comments system (`useInlineComments` hook, text-selection popup) is staying and is the intended annotation method.
  - The stale comment on `DocumentDetailPage.tsx:19` references a "chat bridge" that does not exist yet.
- Design intent (confirmed):
  - Inline comments → context cards inside document-scoped chats.
  - Old `CommentsSection.tsx` → delete.
  - Stale "chat bridge" comment → replace with actual implementation (see Section 5 for planned architecture).
- Action items:
  - Delete `CommentsSection.tsx`.
  - Remove or update the stale comment on `DocumentDetailPage.tsx:19`.
  - The inline comment backend endpoints still need proper access control (see 2.3).

### 3.7 The tests look broad, but they miss the critical invariants
- Severity: High
- Category: QA / Testing
- Verification: Verified
- Affected files:
  - `backend/tests/test_viewer_portal.py:138`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_comments.py`
  - `backend/tests/test_download_auth_parity.py`
  - `backend/pyproject.toml:26-31`
- Description:
  - One viewer/portal test explicitly accepts `[404, 403, 200]` as valid behavior.
  - There is no sampled test covering elevated self-registration.
  - The comments tests are mostly happy-path and do not stress customer/private visibility boundaries.
  - Download parity tests focus on anonymous/public behavior, not session revocation parity.
  - The default pytest config requires xdist (`-n 8`), and the current environment did not have a working `pytest` entrypoint or xdist-compatible default invocation.
- Expected behavior:
  - Tests should lock down security and business invariants, not normalize contradictory outcomes.
- Current behavior:
  - The suite can pass while severe bugs remain live.
- Recommendation:
  - Add invariant tests for self-registration, comment privacy, revoked-session download/WebSocket access, published snapshot immutability, and portal revocation behavior.
  - Fix the local test runner assumptions.
  - Treat warning volume as a CI quality metric.

### 3.8 Security defaults and middleware messaging are misleading
- Severity: Medium
- Category: Security / Ops
- Verification: Verified
- Affected files:
  - `backend/app/app_factory.py:50-52`
  - `backend/app/config.py:22`
  - `backend/app/config.py:27`
  - `backend/app/middleware/csrf.py:109-119`
  - `docker-compose.yml:10-18`
- Description:
  - Docs/OpenAPI are always enabled.
  - `DEBUG` defaults to `True`.
  - The dev secret is present in config and Compose uses development-grade values.
  - The CSRF middleware returns `True` even when no `Origin` or `Referer` is present, while the real auth risk is XSS plus bearer tokens in JS-readable storage.
- Expected behavior:
  - Security features should enforce something real, and config should not overstate protection.
- Current behavior:
  - The posture is more "development convenience with defensive comments" than "hard production defaults".
- Recommendation:
  - Make docs and debug environment-dependent.
  - Be explicit that CSRF is not the primary risk in a bearer-token-in-JS architecture.
  - Harden default deployment docs and config.

### 3.9 `DocumentStatus.PUBLISHED = "active"` makes lifecycle reasoning harder than it needs to be
- Severity: Medium
- Category: Domain Modeling / Maintainability
- Verification: Verified
- Affected files:
  - `backend/app/models/__init__.py:41-49`
- Description:
  - `PUBLISHED` is an alias to `"active"`.
- Expected behavior:
  - Status names should communicate distinct state clearly.
- Current behavior:
  - Code, docs, and endpoints alternate between `ACTIVE` and `PUBLISHED`, which obscures lifecycle meaning.
- Recommendation:
  - Pick one canonical lifecycle vocabulary.
  - If aliases are needed for compatibility, isolate them at API translation boundaries.

### 3.10 Manager permissions are named narrowly but implementation is correct (pyramid model)
- Severity: Low (reclassified — naming issue only)
- Category: Role Logic / Maintainability
- Verification: Confirmed by author
- Affected files:
  - `backend/app/services/permissions.py:61`
  - `backend/app/services/permissions.py:103-128`
  - `backend/app/web/controllers/management/users_controller.py:501-507`
- Description:
  - The permission matrix says managers have `MANAGE_EDITORS` and comments that they can manage editors only.
  - The users controller allows managers to manage `EDITOR`, `VIEWER`, and `CUSTOMER`.
- **Design-intent note (confirmed by author):**
  - The role hierarchy is a **pyramid**: managers manage editors + viewers + customers. Admins manage managers and below. System admin manages all.
  - The **implementation is correct**. The permission **name** (`MANAGE_EDITORS`) is misleading — it should be `MANAGE_SUBORDINATES` or similar.
- Recommendation:
  - Rename `MANAGE_EDITORS` to something that reflects the pyramid model (e.g. `MANAGE_SUBORDINATES`).
  - Add a comment documenting the role hierarchy pyramid.

### 3.11 Non-production rate limiting can be bypassed with a header
- Severity: Medium
- Category: Backend / Security / Ops
- Verification: Verified
- Affected files:
  - `backend/app/middleware/rate_limit.py:141-154`
- Description:
  - `_is_e2e_bypass_request()` disables rate limiting for any request carrying `X-E2E-Test: 1` when `APP_ENV` is anything other than `production`.
- Expected behavior:
  - Test bypasses should be restricted to explicit test environments or isolated network paths, not a guessable header across every non-production deployment.
- Current behavior:
  - Staging/UAT-like environments inherit a trivial bypass.
- Recommendation:
  - Restrict this to `test`/`testing` only, or replace it with an IP allowlist and dedicated test-only deployment controls.

### 3.12 Upload validation trusts MIME headers and filename extensions instead of file content
- Severity: High
- Category: Backend / Security / Validation
- Verification: Verified
- Affected files:
  - `backend/app/api/management/documents.py:537-552`
  - `backend/app/services/attachment_service/common.py:368-396`
- Description:
  - Document upload and attachment upload validation is based on `file.content_type` and filename suffixes.
  - There is no content-based verification of the uploaded bytes.
- Expected behavior:
  - The server should validate the actual file signature for restricted upload types.
- Current behavior:
  - A disguised file can pass validation if its header/extension is acceptable.
- Recommendation:
  - Add content sniffing or magic-byte validation for formats where the system makes type-based trust decisions.
  - Separate "allowed for storage" from "trusted for conversion/rendering."

### 3.13 Chat messages have no upper bound
- Severity: Medium
- Category: Backend / Validation / Reliability
- Verification: Verified
- Affected files:
  - `backend/app/services/chat_service.py:195-206`
- Description:
  - `send_message()` rejects empty content but does not enforce a maximum length.
- Expected behavior:
  - Chat payloads should have a reasonable size cap.
- Current behavior:
  - A user can submit arbitrarily large message bodies.
- Recommendation:
  - Add a message size limit at the schema/service boundary and align the frontend with it.

### 3.14 Exception swallowing leaves subsystems degraded without hard failure
- Severity: High
- Category: Backend / Reliability / Observability
- Verification: Verified
- Affected files:
  - `backend/app/domain/events/dispatcher.py:24-34`
  - `backend/app/services/search_index_service.py:96-134`
  - `backend/app/api/bff/documents.py:139-198`
  - `backend/app/application/queries/search_queries.py:137-138`
- Description:
  - Multiple subsystems catch broad exceptions, log, and continue.
  - The event dispatcher suppresses handler failures by default.
  - Search index maintenance downgrades into warnings instead of durable recovery.
  - Some BFF/query paths swallow failures and return partial data.
- Expected behavior:
  - Non-critical degradations should still be explicit, measurable, and recoverable.
  - Critical side effects should not quietly vanish.
- Current behavior:
  - The system can drift into partially broken states without forcing an operator-visible failure.
- Recommendation:
  - Classify these paths explicitly: fail-fast, retryable, compensating, or intentionally lossy.
  - Add durable recovery where needed and wire these sinks into real alerting.

### 3.15 CORS allows credentials with overly permissive methods and headers
- Severity: Medium
- Category: Backend / Security / Browser Trust
- Verification: Verified
- Affected files:
  - `backend/app/app_factory.py:84-90`
  - `docker-compose.yml:10`
- Description:
  - `CORSMiddleware` is configured with `allow_credentials=True`, `allow_methods=["*"]`, and `allow_headers=["*"]`.
  - Origins are currently restricted to localhost variants in dev and `CORS_ORIGINS` in production, but the combination of `allow_credentials=True` with wildcard methods/headers is one misconfigured env var away from a full credential-stealing CORS bypass.
- Expected behavior:
  - `allow_methods` and `allow_headers` should be explicit allowlists. `allow_credentials=True` should only be combined with a narrow, validated origin list.
- Current behavior:
  - The configuration is safe *only because* `CORS_ORIGINS` is currently set correctly. There is no guardrail preventing a future mistake.
- Recommendation:
  - Replace `["*"]` methods/headers with explicit lists (`["GET", "POST", "PUT", "PATCH", "DELETE"]` and the headers actually used).
  - Add a startup check that rejects `allow_credentials=True` combined with wildcard or null origins.

### 3.16 No password complexity enforcement beyond minimum length
- Severity: Medium
- Category: Backend / Security / Auth
- Verification: Verified
- Affected files:
  - `backend/app/schemas/__init__.py:42`
  - `backend/app/schemas/__init__.py:110`
  - `backend/app/schemas/admin_ops.py:161`
- Description:
  - `UserCreate`, password reset, and admin password schemas all use `Field(..., min_length=8, max_length=100)` as the only validation.
  - No uppercase, lowercase, digit, or symbol requirements are enforced.
- Expected behavior:
  - At minimum, require mixed character classes or use a password strength estimator (e.g. `zxcvbn`).
- Current behavior:
  - `"aaaaaaaa"` is a valid password. Combined with the 5-attempt lockout, weak passwords make credential stuffing more feasible.
- Recommendation:
  - Add a Pydantic validator requiring at least one uppercase, one lowercase, one digit, and one special character — or integrate `zxcvbn` scoring.
  - Align the frontend password field with the backend rules.

### 3.17 Frontend nginx has no Content-Security-Policy header
- Severity: High
- Category: Frontend / Security / Browser Defense
- Verification: Verified
- Affected files:
  - `frontend/nginx.conf:55-61`
  - `backend/app/middleware/security_headers.py:56-61`
- Description:
  - The backend API responses include a strict CSP (`default-src 'none'; frame-ancestors 'none'`), which is good.
  - The frontend nginx config that serves the actual HTML/SPA has **no CSP header at all**.
  - This is the layer where CSP matters most — it is where XSS payloads execute in the browser.
- Expected behavior:
  - Nginx should set a CSP that restricts `script-src` to `'self'`, blocks `unsafe-inline` where possible, and prevents data: URI scripts.
- Current behavior:
  - There is zero browser-level XSS mitigation on the HTML-serving layer. Combined with the `dangerouslySetInnerHTML` sinks (2.5), there is no defense-in-depth.
- Recommendation:
  - Add `add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ws: wss:; frame-ancestors 'none'" always;` to nginx.conf.
  - Tune iteratively — start with report-only mode to avoid breaking the SPA.

### 3.18 Contradictory X-XSS-Protection headers between backend and frontend
- Severity: Low
- Category: Frontend / Security / Configuration
- Verification: Verified
- Affected files:
  - `backend/app/middleware/security_headers.py:34` — sets `X-XSS-Protection: 0`
  - `frontend/nginx.conf:59` — sets `X-XSS-Protection: 1; mode=block`
- Description:
  - The backend correctly sets `X-XSS-Protection: 0` (modern best practice — disable the legacy browser XSS auditor, which can introduce XSS in some edge cases).
  - The frontend nginx sets `X-XSS-Protection: 1; mode=block` (deprecated behavior that can cause false positives and in some browsers create new injection vectors).
- Expected behavior:
  - Both layers should agree on `0` (disable the legacy filter and rely on CSP).
- Current behavior:
  - API responses disable the filter; HTML responses enable it. The inconsistency is confusing and the nginx value is measurably worse.
- Recommendation:
  - Change `frontend/nginx.conf` to `X-XSS-Protection: 0` to match the backend.
  - Rely on CSP (once added per 3.17) for XSS prevention instead.

### 3.19 Dual JWT libraries installed — python-jose and PyJWT
- Severity: Medium
- Category: Backend / Dependencies / Security
- Verification: Verified
- Affected files:
  - `backend/requirements.txt` — lists both `python-jose[cryptography]==3.3.0` and `PyJWT==2.10.1`
- Description:
  - `python-jose` was released in 2021 and is effectively unmaintained. It has had reported CVEs.
  - `PyJWT` 2.10.1 is current and actively maintained.
  - Having two JWT libraries in the same project creates confusion about which one is used where, and increases supply-chain attack surface.
- Expected behavior:
  - One JWT library used consistently across the codebase.
- Current behavior:
  - Both are installed. Depending on which import path is used in different modules, behavior and vulnerability exposure may differ.
- Recommendation:
  - Audit which library is actually imported. Consolidate on `PyJWT`. Remove `python-jose` from requirements.

### 3.20 N+1 query patterns in admin, GDPR, and company endpoints
- Severity: Medium
- Category: Backend / Performance
- Verification: Verified
- Affected files:
  - `backend/app/api/management/companies.py:300,526,730`
  - `backend/app/api/management/gdpr.py:207`
  - `backend/app/api/management/admin_ops.py:1082-1083`
  - `backend/app/services/gdpr_service.py:104,120,133,138,152,165,173,188`
- Description:
  - Multiple endpoints use `.all()` followed by iteration that accesses lazy-loaded relationships (`user.tenant`, `request.user`, etc.).
  - The BFF documents endpoint does use `joinedload` correctly, but admin, GDPR, and company endpoints do not.
- Expected behavior:
  - All list endpoints that access relationships should use eager loading.
- Current behavior:
  - Listing 100 GDPR requests hits the database approximately 200+ times. Company user listings similarly multiply.
- Recommendation:
  - Add `options(joinedload(...))` or `selectinload(...)` to affected queries.
  - Add a query count assertion to critical endpoint tests.

### 3.21 No backup or disaster recovery strategy
- Severity: Medium (reclassified — SQLite is accepted for current stage)
- Category: Operations / Data Safety
- Verification: Verified
- Affected files:
  - `docker-compose.prod.yml` — no backup volumes, scripts, or cron jobs
  - `backend/alembic/` — migrations have downgrade paths but no pre-migration backup
- Description:
  - There is no backup script, no backup volume, no scheduled backup job, and no pre-migration snapshot.
  - The production database is a SQLite file on a Docker named volume.
  - Alembic migrations have `downgrade()` functions, but there is no automated pre-migration safety copy.
- Expected behavior:
  - Automated daily backups (at minimum). Pre-migration snapshots. Tested restore procedure.
- Current behavior:
  - If a migration fails, data corrupts, or a volume is deleted, there is no recovery path.
- **Design-intent note (confirmed by author):**
  - SQLite is the intended database for the current stage. Migration to PostgreSQL/MySQL will happen later when needed.
  - This makes backup simpler (file copy) but the backup automation itself is still missing.
- Recommendation:
  - Add a backup script that copies the SQLite file to a separate volume or local path.
  - Add a pre-migration hook: `cp data/portal.db data/portal.db.bak.$(date +%s)` before `alembic upgrade`.
  - Document and test the restore procedure.
  - When migrating to PostgreSQL, switch to `pg_dump` and add S3/remote backup.

### 3.22 Unlimited concurrent sessions per user
- Severity: Medium
- Category: Backend / Security / Auth
- Verification: Verified
- Affected files:
  - `backend/app/services/auth_service.py:318-326`
  - `backend/app/security.py:85-110`
- Description:
  - Every login creates a new `UserSession` row with no check against a maximum concurrent session count.
  - There is no `MAX_CONCURRENT_SESSIONS` setting or enforcement.
  - `logout()` revokes all sessions for the user, not just the current one, but there is no cap on how many can accumulate while active.
- Expected behavior:
  - A per-user session limit (e.g. 5-10) that revokes the oldest session when exceeded.
- Current behavior:
  - An attacker with compromised credentials can maintain dozens of parallel sessions. A legitimate user who logs in from many devices accumulates unbounded session rows.
- Recommendation:
  - Add a `MAX_CONCURRENT_SESSIONS_PER_USER` config (default 10).
  - On new login, if the limit is reached, revoke the oldest active session or reject the new login.

### 3.23 Deactivated tenant's public documents remain publicly accessible (accepted)
- Severity: Low (reclassified — accepted behavior)
- Category: Backend / Multi-Tenancy / Logic
- Verification: Verified
- Affected files:
  - `backend/app/api/public/documents.py:57-62`
  - `backend/app/services/auth_service.py:33-40`
- Description:
  - When a tenant is deactivated (`Tenant.is_active = False`), its users cannot log in (correctly enforced).
  - However, the public documents query filters only on `Document.visibility == PUBLIC` and `Document.status == ACTIVE`. It does not check `Tenant.is_active`.
- **Design-intent note (confirmed by author):**
  - It is **OK if deactivated tenant's public documents remain visible**. This is accepted behavior.
  - The documents are already published public content — keeping them visible after tenant deactivation is fine.
- Recommendation (optional):
  - If this ever changes, add a `Tenant.is_active` join to `get_public_documents_query()`.

### 3.24 Email delivery has no retry mechanism
- Severity: Medium
- Category: Backend / Reliability / Notifications
- Verification: Verified
- Affected files:
  - `backend/app/services/email_service.py:27-190`
  - `backend/app/api/management/auth.py:87-102`
- Description:
  - `send_email()` catches all SMTP exceptions, logs them, and returns `False`. There is no retry, no dead-letter queue, and no persistence of failed sends.
  - Password reset emails and invitation emails are sent via `background_tasks.add_task()`, which is fire-and-forget.
  - If the SMTP server is temporarily unavailable, the user never receives the email and has no way to know.
- Expected behavior:
  - Transient SMTP failures should be retried (e.g. 3 attempts with exponential backoff).
  - Permanently failed emails should be logged in a recoverable way.
- Current behavior:
  - A single SMTP timeout silently loses the email. The user sees "If an account exists, reset instructions will be sent" but nothing arrives.
- Recommendation:
  - Add retry logic with exponential backoff (1m, 5m, 15m) inside the email service.
  - Consider persisting email send attempts in the database so failed sends can be monitored and manually retried.

### 3.25 No cleanup jobs for expired sessions, tokens, and revoked records
- Severity: Medium
- Category: Backend / Operations / Data Hygiene
- Verification: Verified
- Affected files:
  - `backend/app/workers/` (outbox_worker, conversion_worker, broken_link_checker, assignment_reconciler exist)
  - `backend/app/models/__init__.py` (UserSession, PasswordResetToken models)
- Description:
  - The system creates `UserSession`, password reset tokens, email verification tokens, and `IdempotencyRecord` entries that expire but are never cleaned up.
  - Workers exist for outbox processing, document conversion, broken link checking, and assignment reconciliation — but no worker handles expired data cleanup.
  - Scheduled publish (`scheduled_publish_at` on `Version`) has no visible background executor to trigger publication at the scheduled time.
- Expected behavior:
  - A periodic cleanup job purges expired/revoked sessions, used password reset tokens, and stale idempotency records.
  - Scheduled publishes are executed by a background worker at the appointed time.
- Current behavior:
  - These tables grow indefinitely. Expired sessions remain in the database forever. Scheduled publishes may never fire.
- Recommendation:
  - Add a `cleanup_worker.py` that runs periodically (e.g. hourly) and purges expired sessions, used/expired tokens, and old idempotency records.
  - Add a `scheduled_publish_worker.py` that polls for versions where `scheduled_publish_at <= now()` and triggers the publish flow.

### 3.26 WebSocket chat reconnection lacks exponential backoff
- Severity: Low
- Category: Frontend / Reliability
- Verification: Verified
- Affected files:
  - `frontend/src/hooks/useChatSocket.ts:65-68`
- Description:
  - On WebSocket disconnect, the chat hook retries after a fixed 3-second delay with no backoff.
  - If the server is down or the user's network is flapping, the client retries every 3 seconds indefinitely.
- Expected behavior:
  - Exponential backoff: 3s → 6s → 12s → 30s → cap at 60s. Reset on successful reconnection.
- Current behavior:
  - Fixed 3-second retry can generate significant unnecessary load on a struggling server.
- Recommendation:
  - Implement exponential backoff with a maximum interval (e.g. 60s) and a retry counter.
  - Optionally show a connection status indicator to the user after N failed retries.

### 3.27 AI assistant tools — comprehensive privilege escalation and workflow bypass audit
- Severity: **Critical** (escalated from High after deep tool-by-tool audit of all 97 tool classes across 24 files)
- Category: Backend / AI / Business Logic / Security
- Verification: Verified
- Affected files:
  - `backend/app/assistant/tools/version_tools.py` — `PublishDocumentTool`
  - `backend/app/assistant/tools/review_tools.py` — `SubmitReviewTool`
  - `backend/app/assistant/tools/document_tools.py` — `EditDocumentTool`
  - `backend/app/assistant/tools/analytics_tools.py` — 3 cross-tenant analytics tools
  - `backend/app/assistant/tools/version_tools_ext.py` — `CancelScheduledPublishTool`, `GetVersionDetailsTool`, `GetDocumentVersionStatsTool`
  - `backend/app/assistant/tools/security_tools.py` — `CancelInvitationTool`
  - `backend/app/assistant/tools/audit_tools.py` — `SearchAuditLogsTool`, `GetUserActivityTool`
  - All 33 write tools across 24 tool files (direct DB writes, no service layer)
- **Core design rule (confirmed by author):**
  - **Everything the AI does must be treated as if it was done by the user who asked it, bound by that user's role and permissions.**
  - If the user is an editor, the AI can only do what an editor can do. If the user is a viewer, the AI can only read.
  - The AI is not a separate actor — it is a tool that acts on behalf of the current user.
- **Infrastructure (what works well):**
  - `BaseTool.user_can_execute()` checks both `required_permission` and `required_role` against the role hierarchy.
  - `ToolRegistry.execute_tool()` re-checks permissions before executing — two-layer gate.
  - `AssistantEngine.get_ollama_tools(user)` only exposes tools the user is allowed to use.
  - `confirm_before_execute = True` on 13 destructive tools sends a confirmation event instead of executing.
  - Every `execute()` receives `(user, tenant_id, params, db)` — the plumbing exists.

#### 3.27a CRITICAL — Privilege escalation: Editor can publish via AI (needs manager+ in normal flow)
- Affected tool: `PublishDocumentTool` in `backend/app/assistant/tools/version_tools.py`
- Tool config: `required_role = "EDITOR"`, no `required_permission`
- Normal API: `POST /documents/{id}/versions/{id}/publish` delegates to `PublishApprovedVersionCommandHandler` which enforces manager/admin-only access, checks review approval status, validates state machine, generates audit trail
- AI tool behavior: Sets `version.is_published = True` directly. **Does not check**:
  - Whether the version has been approved through review
  - Whether the user has `PUBLISH_DOCUMENT` permission (only checks EDITOR role)
  - Whether the document is in a publishable state via the state machine
- Impact: Any editor can publish any version through the AI, completely bypassing the review-approve-publish workflow

#### 3.27b CRITICAL — Privilege escalation: Editor can approve reviews without ReviewPolicy checks
- Affected tool: `SubmitReviewTool` in `backend/app/assistant/tools/review_tools.py`
- Tool config: `required_role = "EDITOR"`, no `required_permission`
- Normal API: `POST /reviews/{id}/approve` delegates to `ApproveReviewCommandHandler` which uses `ReviewPolicy.can_approve_review()`:
  - Blocks self-approval (reviewer.id == submitter.id is denied)
  - Requires `APPROVE_REVIEWS` permission, OR `PEER_APPROVE_REVIEWS` permission if submitter is an editor
- AI tool behavior: Only checks `review.reviewed_by != user.id` (is assigned reviewer). **Does not check**:
  - Whether the reviewer is the same person who submitted the document for review (self-approval of own submission)
  - `ReviewPolicy` approval rules
  - Whether the user has `APPROVE_REVIEWS` or `PEER_APPROVE_REVIEWS` permission
- Impact: An editor who submitted a document for review can ask the AI to approve it — self-approval backdoor

#### 3.27c CRITICAL — EditDocumentTool can set doc.status to any value including `active`
- Affected tool: `EditDocumentTool` in `backend/app/assistant/tools/document_tools.py`
- Tool config: `required_permission = Permission.EDIT_DOCUMENT`, no role check
- The tool's parameter schema explicitly allows: `"enum": ["draft", "pending_review", "approved", "active", "archived"]`
- Normal flow: Status transitions go through `DocumentAggregate` then `document_stage.py` state machine then `review_stage.py` gates
- AI tool behavior: `doc.status = params["status"]` — direct assignment, no state machine, no validation
- Impact: An editor can set any document to `active` (published) status via AI, completely bypassing: submit, peer review, approve, publish

- **Combined recommendation for 3.27a-c:**
  - Route `PublishDocumentTool` through `PublishApprovedVersionCommandHandler` — the same handler the API uses.
  - Route `SubmitReviewTool` through `ApproveReviewCommandHandler` — enforce `ReviewPolicy` checks.
  - Remove `status` from `EditDocumentTool`'s allowed parameters entirely — status transitions must only happen through the state machine.
  - Add tests: "editor asks AI to publish" denied, "editor asks AI to approve own submission" denied, "editor asks AI to set status to active" denied.

### 3.29 All 97 AI tools bypass the service layer — direct DB writes with no audit trail
- Severity: High
- Category: Backend / AI / Architecture
- Verification: Verified — every single `execute()` method examined
- Description:
  - Every AI tool that writes data does so via raw SQLAlchemy operations (`db.add()`, `db.commit()`, direct field assignment) rather than calling the service layer / command handlers that the REST API uses.
  - The normal API flow: Controller then Command Handler then Service then Repository then audit log + notifications + state validation
  - The AI tool flow: `execute()` then raw `db.query()` + `db.commit()`
- What is lost:
  - **No audit trail**: None of the AI write operations create `AuditLog` entries. Every normal API write generates an audit record.
  - **No notifications**: The AI path never calls the notification service. A publish, review, or status change via AI generates zero notifications to watchers/stakeholders.
  - **No state machine validation**: `DocumentAggregate`, `document_stage.py`, and `review_stage.py` transition guards are completely bypassed.
  - **No ETag / optimistic locking**: The normal API uses ETags to prevent concurrent edit conflicts. AI tools do not.
  - **No version mutability guards**: `ensure_version_mutable()` is never called — AI could theoretically modify published (immutable) versions if such a tool existed.
- Affected write tools (33 tools, all with the same pattern):
  - Admin: `ToggleFeatureFlagTool`, `CreateMaintenanceWindowTool`, `UpdateTenantQuotaTool`, `ReviewAdminActionTool`
  - Chat: `SendChatMessageTool`, `MarkChatReadTool`
  - Comments: `AddCommentTool`, `ResolveCommentTool`
  - Documents: `CreateDocumentTool`, `EditDocumentTool`, `DeleteDocumentTool`
  - Engagement: `BookmarkDocumentTool`, `RemoveBookmarkTool`, `WatchDocumentTool`, `UnwatchDocumentTool`, `UpdateReadingProgressTool`
  - Feedback: `SubmitFeedbackTool`
  - Invitations: `CreateInvitationTool`
  - Notifications: `MarkNotificationsReadTool`
  - Reviews: `SubmitReviewTool`
  - Security: `RevokeSessionTool`, `CancelInvitationTool`
  - Settings: `UpdateSiteSettingTool`, `CreateAnnouncementTool`, `CreateTopicTool`
  - Support: `CreateSupportTicketTool`
  - Tenants: `UpdateTenantTool`
  - Users: `CreateUserTool`, `DeactivateUserTool`, `ChangeUserRoleTool`
  - Versions: `PublishDocumentTool`, `CancelScheduledPublishTool`
- Recommendation:
  - Route all write operations through the same command handlers / service methods the API uses.
  - This single change would fix audit trail, notifications, state machine, ETag, and mutability guards — all at once.
  - If full service-layer integration is too large for one pass, at minimum add explicit `AuditLog` creation in each write tool as a stopgap.

### 3.30 AI tools missing tenant isolation — cross-tenant data exposure
- Severity: High
- Category: Backend / AI / Multi-tenancy / Security
- Verification: Verified
- Description:
  - Several AI tools query the database without filtering by `tenant_id`, allowing users to see or modify data from other tenants. While some of these tools require `Permission.SYSTEM_SETTINGS` (currently only system_admin), others have weaker permission gates.
- **Cross-tenant read tools (data leakage):**

  | Tool | Permission gate | Tenant filter? | Risk |
  |------|----------------|---------------|------|
  | `GetPlatformAnalyticsTool` | SYSTEM_SETTINGS | **No** — counts all users/docs across tenants | Medium (only sysadmin) |
  | `GetEngagementAnalyticsTool` | SYSTEM_SETTINGS | **No** — shows top users/docs across tenants | Medium (only sysadmin) |
  | `GetContentAnalyticsTool` | SYSTEM_SETTINGS | **No** — shows authors/status across tenants | Medium (only sysadmin) |
  | `SearchAuditLogsTool` | SYSTEM_SETTINGS | **No** — queries all audit logs | Medium (only sysadmin) |
  | `GetUserActivityTool` | SYSTEM_SETTINGS | **No** — queries any user's activity | Medium (only sysadmin) |
  | `GetSecurityEventsAdminTool` | SYSTEM_SETTINGS + SYSTEM_ADMIN | **No** — all security events | Low (sysadmin only) |
  | `GetVersionDetailsTool` | VIEW_INTERNAL_DOCS | **No** — any version by ID | **High** — editors have this |
  | `GetDocumentVersionStatsTool` | VIEW_INTERNAL_DOCS | **No** — any doc's version stats | **High** — editors have this |

- **Cross-tenant write tools (data modification):**

  | Tool | Permission gate | Tenant filter? | Risk |
  |------|----------------|---------------|------|
  | `CancelScheduledPublishTool` | PUBLISH_DOCUMENT | **No** — cancels any version's scheduled publish | **High** — managers have this |
  | `CancelInvitationTool` | MANAGE_USERS | **No** — cancels any invitation by ID | **High** — admins have this |

- **Cross-tenant engagement tools:**

  | Tool | Permission gate | Doc tenant check? | Risk |
  |------|----------------|-------------------|------|
  | `BookmarkDocumentTool` | VIEW_PUBLIC_DOCS | **No** | Medium — can bookmark docs from other tenants |
  | `WatchDocumentTool` | VIEW_PUBLIC_DOCS | **No** | Medium — can watch docs from other tenants |
  | `UpdateReadingProgressTool` | VIEW_PUBLIC_DOCS | **No** | Low — tracks own progress only |

- Recommendation:
  - Add `tenant_id` filtering to all tools that currently lack it.
  - For tools gated by `SYSTEM_SETTINGS` + `SYSTEM_ADMIN`: acceptable for cross-tenant views if sysadmin is truly global. Document this as intentional.
  - For tools gated by `VIEW_INTERNAL_DOCS` or `PUBLISH_DOCUMENT`: **must add tenant check** — these permissions are held by per-tenant roles (editor, manager).
  - For engagement tools: add `doc.tenant_id == tenant_id` check before allowing bookmarks/watches.

#### Summary: AI tool gaps by role

| Role | What they SHOULD be able to do via AI | What they CAN currently do that is wrong |
|------|--------------------------------------|----------------------------------------|
| **Customer** | Search/read public docs, submit feedback, manage support tickets, chat | Correctly limited — most tools filtered by permission |
| **Viewer** | Read internal docs, list attachments, view collaboration history, comments | Can view versions/stats from other tenants via `get_version_details`, `get_document_version_stats` |
| **Editor** | Create/edit docs, submit for review, peer-review, comments | Can **publish** docs (should need manager+). Can **approve own submissions**. Can **set doc.status to active** directly. Can view/modify cross-tenant versions. |
| **Manager** | All editor actions + approve reviews + publish + manage editors/viewers | Can **cancel scheduled publishes** from other tenants. Service layer bypasses mean no audit trail or notifications for any action. |
| **Admin** | All manager actions + manage users + invitations + company settings | Can **cancel invitations** from other tenants. All write actions bypass audit trail. |
| **System Admin** | Full platform control | Cross-tenant analytics/audit reads are likely intentional but should be documented. All writes bypass audit trail. |

### 3.28 AI assistant content editing is not yet implemented but needs review-workflow integration when built
- Severity: N/A (future — not yet built)
- Category: AI / Product / Business Logic
- Verification: Confirmed — Phase 17 in `aiplan.md` is "Not Started"
- **Core design rule (confirmed by author):**
  - **Everything the AI does must be treated as if it was done by the user who asked it, bound by that user’s role and permissions.**
  - When the AI can edit paragraph content (rewrite, expand, simplify), those edits **must** go through the approval workflow.
  - Flow: User asks AI to edit a paragraph → AI proposes the change → User approves the AI's suggestion → Change is applied to the document (attributed to the user, not "the AI") → The document still requires normal review/approval from an editor/manager before publication.
  - AI edits should never auto-publish or bypass the review chain.
  - If a viewer asks the AI to edit content, it should be denied — viewers can’t edit.
- Current state:
  - The AI can only modify metadata (title, status, topic). It cannot modify `Version.content` (the document body).
  - Inline AI editing (select text → rewrite/expand/simplify, slash commands) is planned as Phase 17 but not built.
- Requirements for Phase 17 implementation:
  1. AI proposes content changes as a diff/suggestion — not applied immediately.
  2. The user reviews and accepts/rejects the AI's suggestion in the editor.
  3. Accepted changes modify the draft version content (same as human edits), attributed to the requesting user.
  4. The document must still go through the normal review workflow (submit → peer review → approve → publish).
  5. AI edits should be tagged in version history ("edited via AI assistant by [user]") for auditability.
  6. Role enforcement: only users with edit permissions on the document can trigger AI edits.
  7. The AI cannot approve its own user’s edits — a different reviewer must approve, same as any human edit.

## 4. Improvement Suggestions

### 4.1 Centralize access decisions around one document access policy
- Area: Architecture
- Why it would help:
  - The same document visibility rules are currently re-implemented differently in portal, public, comments, attachments, and collaboration paths.
- Suggested implementation direction:
  - Create one access service that resolves read/write/download/comment access per user, per document, per version or publication snapshot.
- Priority: P0

### 4.2 Treat publication as a release artifact, not a loose combination of current rows
- Area: Backend / Product
- Why it would help:
  - It would eliminate draft fallback and current-attachment leakage.
- Suggested implementation direction:
  - Create an immutable published revision record that snapshots content, metadata, audience, and attachments.
- Priority: P0

### 4.3 Eliminate ad hoc HTML rendering
- Area: Frontend / Security
- Why it would help:
  - The codebase already has a sanitizer. The public pages bypass it.
- Suggested implementation direction:
  - Route every HTML-like rendering path through one safe rendering utility, or move to structured rich text.
- Priority: P0

### 4.4 Replace token-in-URL patterns with signed capabilities or cookie/session-backed flows
- Area: Security / API
- Why it would help:
  - URL tokens are a recurring design failure across attachments and sockets.
- Suggested implementation direction:
  - Use server-issued, narrow-scope, short-lived download tickets and WebSocket session tokens.
- Priority: P0

### 4.5 Make API surfaces honest
- Area: Architecture / DX
- Why it would help:
  - "Management" endpoints that are public and portal pages that use management APIs create policy confusion.
- Suggested implementation direction:
  - Split route registries by audience and remove accidental sharing.
- Priority: P1

### 4.6 Reduce test warning noise aggressively
- Area: QA / DX
- Why it would help:
  - `3833` warnings is not harmless background noise. It hides real regressions.
- Suggested implementation direction:
  - Fix deprecations, tighten warning filters, fail on new warning classes in CI.
- Priority: P1

### 4.7 Remove or complete dead feature branches
- Area: Maintainability / Product
- Why it would help:
  - Comments UI drift and collaboration config drift suggest half-finished transitions.
- Suggested implementation direction:
  - Delete dead components and stale contracts, or finish their replacement path in one slice.
- Priority: P1

### 4.8 Stop exposing raw role and tenant fields in external write payloads
- Area: Auth / Role Logic
- Why it would help:
  - External API payloads should not carry server-owned authority decisions.
- Suggested implementation direction:
  - Move role assignment to admin-only commands and invitation acceptance.
- Priority: P0

### 4.9 Tighten contract tests around security-sensitive routes
- Area: QA / Security
- Why it would help:
  - Security regressions should break tests immediately.
- Suggested implementation direction:
  - Add route-by-route parity tests for HTTP auth, download auth, portal access, and WebSocket auth.
- Priority: P0

### 4.10 Align configuration sources
- Area: Configuration / Ops
- Why it would help:
  - Collaboration URL handling currently has no trustworthy source of truth.
- Suggested implementation direction:
  - Define one env var and one contract path, then remove all unused variants.
- Priority: P1

### 4.11 Move production defaults off SQLite
- Area: Database / Deployment
- Why it would help:
  - It removes a self-imposed operational ceiling from the default production shape.
- Suggested implementation direction:
  - Make PostgreSQL the default production target in Compose and deployment docs; leave SQLite as explicit local/dev mode only.
- Priority: P1

### 4.12 Build a complete user-data inventory for export and deletion flows
- Area: Compliance / Backend
- Why it would help:
  - GDPR-like workflows drift whenever new user-linked tables are added and the export/delete service is not updated.
- Suggested implementation direction:
  - Create a registry-driven export/delete map that covers sessions, security events, chat/support messages, and future user-linked entities.
- Priority: P1

### 4.13 Replace blanket exception suppression with explicit degradation policies
- Area: Reliability / Observability
- Why it would help:
  - It makes "degraded but operating" a deliberate state instead of an accident.
- Suggested implementation direction:
  - Audit all broad exception sinks and mark each as fail-fast, retry, compensate, or intentionally ignore with metrics.
- Priority: P1

### 4.14 Harden upload trust boundaries with content-based validation
- Area: Security / File Handling
- Why it would help:
  - Extension and declared MIME type are not enough when uploads feed conversion, preview, or downstream processing.
- Suggested implementation direction:
  - Add content-based sniffing for trusted types and isolate untrusted binaries from conversion/rendering pipelines.
- Priority: P1

## 5. Ideas

- Introduce a "permission debugger" admin screen that explains why a user can or cannot access a document.
- Add a "published snapshot diff" tool so editors can see exactly what will change for public/customer viewers before publishing.
- Create a security regression suite focused only on auth, RBAC, tenant boundaries, and HTML rendering sinks.
- Add an "access revocation cleanup" job that prunes or masks reading history for documents the user no longer has access to.
- ~~Split internal comments, reviewer annotations, and customer feedback into separate concepts instead of one overloaded comments model.~~ **(Superseded — see chat unification plan below.)**
- **Chat Unification Architecture (confirmed design vision):**
  - **General chats** stay as-is (tenant-scoped messaging between users).
  - **Document-scoped chats**: Add `document_id` (nullable FK) to the Chat model. When a user creates an inline comment on a document, the system opens or creates a chat with the document's author(s). Multi-author documents create a group chat.
  - **Context cards**: Each chat message originating from an inline comment carries metadata (document title, section, anchor text, comment type: question/suggestion/issue/other) so chat participants understand the topic without leaving the chat.
  - **Feedback → chat**: The customer feedback system becomes chat-like — back-and-forth between customer and internal staff, keeping the existing feedback business logic but presented as a conversation. Customers see a "Chat" tab/page under or alongside their existing Feedback page in the portal.
  - **Customer chat routing**: Customers can chat with any internal user related to the document they are discussing, or continue existing chat threads with any internal user they have already chatted with.
  - **Inline comments stay**: The text-selection popup (`useInlineComments` hook) remains as the annotation/entry-point method. It serves as the bridge between document content and chat.
  - **Migration**: Forward-only (no retroactive migration of old feedback records into chat threads).
- Add a route ownership matrix so public, portal, viewer, management, and collaboration are mechanically separated.
- Build audit alerts around suspicious self-registration attempts, token misuse, and cross-surface access anomalies.
- Add a deploy-time configuration validator that checks env var names across backend, frontend, and collab-server.
- Run `pip audit` and `npm audit` as CI gates to catch dependency vulnerabilities automatically.
- Add a pre-migration backup hook that snapshots the database before every `alembic upgrade`.
- Generate a machine-readable route ownership matrix that maps each endpoint to its audience surface (public/portal/viewer/management) and enforced auth level.
- Implement a periodic cleanup worker to purge expired sessions, used password reset tokens, and stale idempotency records.
- Add a scheduled-publish executor worker that fires publication at the appointed `scheduled_publish_at` time.
- **PDF Upload → Editable Document (confirmed feature request by author):**
  - Allow internal users to upload PDF files (in addition to DOCX/PPTX).
  - The system converts the PDF content to HTML and loads it into the TipTap editor, so users can edit it like a Word document.
  - **Current state**: `PyMuPDF` and `pdfplumber` are already installed. The extraction strategy pattern exists (`WordConverterStrategy`, `PowerPointConverterStrategy`). PDF is **not** in the frontend file picker or `STRUCTURED_READER_EXTENSIONS`.
  - **Implementation path**:
    1. Add `.pdf` to the frontend file picker accept list in `documentsUseCases.ts`.
    2. Create `PdfConverterStrategy` in `backend/app/conversion/` following the existing DOCX/PPTX extractor pattern.
    3. Use `PyMuPDF` (fitz) to extract text blocks, images, and structure → build IR nodes → generate HTML via existing `html_generator.py`.
    4. Register `.pdf` in `STRUCTURED_READER_EXTENSIONS` and wire the new strategy into `document_strategies.py`.
    5. The existing flow handles the rest: HTML → TipTap editor → collaborative editing → save.
  - **Caveat**: PDF → HTML conversion is lossy by nature (PDFs describe visual layout, not document structure). Complex multi-column layouts, scanned image PDFs, and advanced formatting may degrade. Consider OCR (`pytesseract`) for scanned PDFs if needed later.
- **PDF-Only Downloads for External Users (confirmed feature request by author):**
  - When a customer (portal) or external viewer downloads a document, they should receive a **PDF export** — not the original DOCX/PPTX file.
  - Internal users continue to get the original file.
  - **Current state**: `reportlab` is installed. All download endpoints currently serve the original binary. The HTML representation of each document already exists as a reader artifact.
  - **Implementation path**:
    1. Add a PDF render service: take the existing reader artifact HTML → render to PDF using `reportlab` (or `weasyprint` for better HTML→PDF fidelity).
    2. Cache the generated PDF as an `AttachmentArtifact` (type `pdf_export`) alongside the existing `reader_html` artifact.
    3. Regenerate the PDF artifact whenever a new version is published.
    4. Modify the portal (`/api/v1/portal/.../download`) and viewer (`/api/v1/viewer/.../download`) endpoints to serve the PDF artifact instead of the original file.
    5. Keep the management download endpoint unchanged (internal users get the original).
  - **Benefit**: Customers never see raw editable files. The company controls the presentation format. Also prevents accidental metadata leakage from DOCX/PPTX properties.
- **AI Content Editing — Review Workflow Integration (confirmed requirement by author):**
  - When AI inline editing (Phase 17) is built, all AI content changes must go through the normal review/approval workflow.
  - AI should propose changes as suggestions, not apply them directly.
  - After user accepts the AI’s suggestion, the document remains in draft and must be submitted for review like any human edit.
  - AI edits should be attributed in version history.
  - See finding 3.28 for full requirements.

## 6. Helpful Notes

- The most important theme in this repo is not "bad code". It is "good-looking abstractions with badly placed trust boundaries."
- The main HTTP auth path is one of the stronger parts of the system. The worst auth bugs happen when the code steps around it.
- `frontend/src/lib/htmlSanitizer.ts` and `frontend/src/lib/documentRenderer.tsx` are meaningfully better than the public search/changelog implementations. The secure pattern already exists inside the codebase.
- `backend/app/services/version_service.py` appears to contain real business rules, but those rules are undermined by alternative write/read paths.
- The README and architecture docs overstate behavioral guarantees. In particular:
  - README says public viewer access is "published version access only".
  - README says private comments are "admin/editor only".
  - The code does not reliably enforce either claim.
- I did not fully audit every script, migration, or every E2E spec. The review focused on core production behavior.
- Sampled backend tests passed, which is useful only as evidence that the suite is not covering the right invariants.
- The project installs both `python-jose` and `PyJWT`. This is a supply-chain hygiene issue — consolidate on one.
- The frontend nginx.conf and backend security_headers.py disagree on `X-XSS-Protection` (1 vs 0). Align on 0.
- Account enumeration is well-handled: login and password reset return generic messages regardless of whether the user exists.
- Logging is secure: the logging middleware does not log request bodies, auth headers, or tokens.
- Docker security is solid: both Dockerfiles use non-root users and slim base images.
- **AI/Ollama features are confirmed production features** (not experimental). The AI assistant, summary, and extraction endpoints backed by Ollama are intended to ship. Error handling, model availability checks, and graceful fallbacks for when Ollama is unreachable should be treated as production requirements, not nice-to-haves.

## 7. Review by Feature

This section maps the validated findings back to product features. Full evidence and remediation detail remain in sections 2 and 3.

### 7.1 Authentication and user management
- What it is supposed to do:
  - Authenticate users, enforce role boundaries, manage tenants, and support secure registration/login/session flows.
- How it currently works:
  - Main HTTP auth uses JWT plus session tracking and inactivity checks.
  - Public registration can set role and tenant directly.
- What is good:
  - Session hash validation and revocation logic in `backend/app/security.py`.
  - Better-than-average auth core for the standard API path.
- What is problematic:
  - The strongest auth logic exists only on the standard HTTP path. Public registration and alternative transport paths bypass it (see 2.1, 2.2).
- What is missing:
  - One coherent story for auth across HTTP, downloads, WebSockets, and collaboration.
  - Server-owned role assignment on registration.
- Production readiness:
  - Superficially functional, not trustworthy.

### 7.2 RBAC and role behavior
- What it is supposed to do:
  - Enforce role-based visibility and action permissions across all surfaces.
- How it currently works:
  - There is a permission matrix and helper functions.
  - Some routes and services enforce roles well. Others rely on UI or tenant matching.
- What is good:
  - Central permission definitions are present.
- What is problematic:
  - Comment access and self-registration bypass the intended model.
  - Manager role semantics are inconsistent between names and implementation.
- What is missing:
  - Mandatory server-side enforcement at every externally reachable boundary.
- Production readiness:
  - Incomplete and inconsistent.

### 7.3 Document management and versioning
- What it is supposed to do:
  - Support draft, review, publish, version history, and controlled releases.
- How it currently works:
  - The main version service has serious checks.
  - Alternative paths can create published versions automatically or serve draft fallbacks.
- What is good:
  - Publish preflight and audience checks in `backend/app/services/version_service.py`.
- What is problematic:
  - Published state is not the single source of truth for public/customer reads.
  - Attachment uploads can mutate release state.
- What is missing:
  - Immutable publication snapshots.
- Production readiness:
  - Good intent, broken invariants.

### 7.4 Attachments and reader view
- What it is supposed to do:
  - Store files, expose downloads safely, and optionally generate reader-friendly derivatives.
- How it currently works:
  - Upload uses the strong auth path.
  - Download/reader view accept query-string JWTs.
  - Public/customer/viewer attachment exposure is not version-snapshot safe.
- What is good:
  - Reader artifact generation is a real subsystem, not a stub.
- What is problematic:
  - Security model is weaker on read paths than write paths.
  - Attachment-to-version semantics are underdesigned.
- What is missing:
  - Version-bound or release-bound attachment visibility.
- Production readiness:
  - Fragile.

### 7.5 Public viewer, search, and changelog
- What it is supposed to do:
  - Offer a public documentation library ("Viewer Portal") for external users, with search, categories, and published document browsing.
  - External users land on the docs page and can browse/read published documents without logging in.
  - Signing in unlocks extra features (feedback, chat, bookmarks, reading progress, etc.).
- Design intent (confirmed by author):
  - The public viewer portal at `/docs` is the intended external experience (documentation library with search, categories, platform highlights).
  - **Anyone can browse and read published docs without logging in.** Signing in is for additional features.
  - External viewers should **not** use token-in-URL shareable links. The current token-in-URL viewer scheme should be replaced or removed.
- How it currently works:
  - Public documents are readable, searchable, and have a changelog page.
  - Search and changelog render unsanitized HTML.
  - The changelog API can leak unpublished entries by default.
  - The viewer also has a separate token-in-URL access path that should be removed.
- What is good:
  - Public document rendering itself benefits from the safer document renderer.
  - The documentation library UI is well-structured.
- What is problematic:
  - Severe XSS risk and unreliable public release boundaries (see 2.4, 2.5, 2.6).
  - Token-in-URL viewer access contradicts the design intent.
- What is missing:
  - Safe rendering discipline and clear public-only data contracts.
  - Remove token-in-URL viewer path.
- Production readiness:
  - The documentation library concept is solid. The XSS and token-in-URL issues need fixing.

### 7.6 Customer portal
- What it is supposed to do:
  - Let customers read only documents they are allowed to see, download attachments, track progress, and submit feedback.
- How it currently works:
  - The portal query handler has a central `_ensure_customer_document_access`.
  - Some ancillary endpoints bypass that central policy.
- What is good:
  - There is at least a real customer access abstraction in `portal_queries.py`.
- What is problematic:
  - Portal policy is only partially centralized; history and detail views still leak mutable or revoked state (see 3.1, 2.4, 3.3).
- What is missing:
  - Full policy consistency across every portal endpoint.
- Production readiness:
  - Partially functional, not rigorous.

### 7.7 Comments, chat, and collaboration
- What it is supposed to do:
  - Allow controlled discussion via inline comments, document-scoped chats, and real-time collaboration.
- **Real-time collaboration is an actively used production feature** (confirmed by author). The collab server is not experimental.
- How it currently works:
  - Collaboration uses purpose-built tokens but still depends on query-string transport and separate validation semantics.
  - Three messaging systems coexist: inline comments (active, text-selection popup), general chat (tenant-scoped, no `document_id`), and feedback (customer-facing, separate model).
  - `CommentsSection.tsx` is dead code (never imported). The inline comments hook is the only active comment UI.
- What is good:
  - Collaboration permissions are not entirely ad hoc. There is real permission modeling.
  - The inline comments system works and is intentionally staying.
  - The design vision for chat unification is clear and well-reasoned.
- What is problematic:
  - Comment privacy is not enforced on the backend (see 2.3).
  - Collaboration config is inconsistent and brittle.
  - Socket auth parity is weak.
  - The Chat model lacks `document_id` — document-scoped chats are not yet implemented.
- What is missing (planned):
  - Document-scoped chats (`document_id` on Chat model, auto-create chat from inline comment).
  - Context cards in chat messages (doc title, section, anchor text, comment type).
  - Feedback → chat migration (customer↔staff back-and-forth as conversations).
  - Customer "Chat" tab/page in the portal.
  - Consistent auth and revocation handling for real-time channels.
- Production readiness:
  - Inline comments work. General chat works. The unification is not yet built.
  - The comment permission bugs (2.3) need fixing before production regardless.

### 7.8 Testing and quality controls
- What it is supposed to do:
  - Catch regressions, especially in security and access behavior.
- How it currently works:
  - There are many tests, but key invariants are missing.
- What is good:
  - The test footprint is real.
- What is problematic:
  - Some tests allow contradictory outcomes.
  - Warning volume is extreme.
  - Default local runner assumptions are brittle.
- What is missing:
  - Security regression tests that match the actual risk surface.
- Production readiness:
  - Not enough for the risk profile of this codebase.

### 7.9 Company management and tenant administration
- What it is supposed to do:
  - Let admins manage their own companies/tenants without leaking cross-tenant data.
- How it currently works:
  - Company listing is admin-gated, but not tenant-scoped for non-system admins.
- What is good:
  - The company API is feature-rich and includes useful aggregate stats.
- What is problematic:
  - The central list path violates tenant isolation outright (see 2.7).
- What is missing:
  - Hard tenant scoping on every non-system-admin company-management path.
- Production readiness:
  - Not acceptable for a serious multi-tenant system.

### 7.10 Chat and support messaging
- What it is supposed to do:
  - Provide internal/direct messaging, document-scoped discussion, and customer support communication with sane guardrails.
- How it currently works:
  - The chat service validates existence and participation rules, but message bodies have no practical size limit.
  - Chat is currently tenant-scoped only — there is no `document_id` linkage yet.
- What is good:
  - There is real participant-based access logic and real-time delivery.
  - The planned design (general chats + document-scoped chats + feedback-as-chat) is coherent.
- What is problematic:
  - Payload size is under-constrained.
  - WebSocket auth still inherits the broader token-in-URL/auth-parity problems.
- What is planned (confirmed by author):
  - Add `document_id` to Chat model for document-scoped chats.
  - Inline comments trigger chat creation with document author(s).
  - Context cards carry doc/section/anchor metadata into chat messages.
  - Feedback becomes a chat-like conversation (customer↔staff).
  - Customers get a "Chat" tab/page in the portal.
- What is missing:
  - Bounded message size, explicit retention/export rules, and stronger socket session semantics.
- Production readiness:
  - Usable, but under-hardened.

### 7.11 Data export and deletion
- What it is supposed to do:
  - Give users a complete export of their personal data and support deletion/anonymization safely.
- How it currently works:
  - Export covers a subset of user-linked entities.
  - Deletion handles some data categories that export omits.
- What is good:
  - The service exists and the deletion path at least recognizes sessions/security events as user-linked data.
- What is problematic:
  - Export coverage is incomplete and therefore untrustworthy (see 2.8).
- What is missing:
  - A registry-driven inventory of every user-linked data source.
- Production readiness:
  - Not good enough for compliance-sensitive deployment.

## 8. Review by Flow

This section summarizes where end-to-end behavior breaks. It intentionally references, rather than repeats, the detailed evidence from sections 2 and 3.

### 8.1 Registration and onboarding flow
- Entry points:
  - `/api/v1/auth/register`
- Flow:
  - Request payload includes role and tenant.
  - Service persists them directly.
- Breaks:
  - Authority assignment happens at the edge, controlled by caller input.
- Verdict:
  - Unsafe by design.

### 8.2 Internal authoring to publish flow
- Entry points:
  - Document creation/editing routes, version routes, attachment upload
- Flow:
  - Main version service has checks.
  - Attachment upload can side-step the publish model.
- Breaks:
  - Publish invariants are not centralized.
- Verdict:
  - Works on the happy path, unsafe on side paths.

### 8.3 Attachment upload/download flow
- Entry points:
  - Management upload endpoints, public/viewer/portal download endpoints
- Flow:
  - Upload uses strong auth.
  - Read/download paths use weaker auth and mutable attachment sets.
- Breaks:
  - Read security is weaker than write security.
  - Release integrity is not preserved.
- Verdict:
  - Architecturally inconsistent.

### 8.4 Public discovery flow
- Entry points:
  - `/docs`, `/search`, `/changelog`, `/doc/:id`
- Flow:
  - Public document viewing is mostly okay through sanitized document rendering.
  - Search/changelog are not okay.
- Breaks:
  - HTML injection.
  - Unpublished changelog leak.
  - Public doc route can fall back to drafts.
- Verdict:
  - Unsafe for public internet exposure as-is.

### 8.5 Customer read and progress flow
- Entry points:
  - Portal document detail, reading-progress endpoints
- Flow:
  - Portal detail uses a customer access check.
  - Reading history endpoints do not.
- Breaks:
  - Revoked access does not fully revoke visibility.
- Verdict:
  - Partial access control.

### 8.6 Collaboration/session flow
- Entry points:
  - `/auth/collab-token`, collab server WebSocket, chat/support WebSockets
- Flow:
  - Token issuance is one path; socket validation is a separate path.
  - Config sources disagree.
- Breaks:
  - Auth semantics and deployment semantics drift apart.
- Verdict:
  - Functional under ideal setup, brittle in reality.

### 8.7 Logout/revocation flow
- Entry points:
  - Main API logout/session revocation
- Flow:
  - Standard API requests honor session state.
  - Some alternate transports do not.
- Breaks:
  - Revocation is not uniformly enforced.
- Verdict:
  - Security posture is inconsistent.

### 8.8 Company administration flow
- Entry points:
  - Admin company-management screens and `/api/v1/companies`
- Flow:
  - Admin enters company-management surface, list endpoint returns tenants plus aggregate counts.
- Breaks:
  - Non-system-admins are not scoped to their own tenant before the list query is built.
- Verdict:
  - The admin flow violates the product's own multi-tenant boundary.

### 8.9 User data export flow
- Entry points:
  - GDPR/data export request and ZIP generation
- Flow:
  - Request is created, export ZIP is assembled from selected user-linked records, download token is issued.
- Breaks:
  - The export set is incomplete relative to the user-linked data the app actually stores.
- Verdict:
  - Functionally present, legally and operationally incomplete.

## 9. Review by User Type / Role

This section maps the validated findings to user classes and permission boundaries instead of restating the full technical proof.

### 9.1 Anonymous user
- Should be able to:
  - View only intended public surfaces and only published public content.
- Currently can:
  - Register with caller-controlled role/tenant values.
  - Query the changelog API for unpublished entries unless the caller explicitly passes `published_only=true`.
- Main risk:
  - Privilege escalation and information leakage.

### 9.2 Customer
- Should be able to:
  - Access only assigned/public documents in the portal.
  - Download only approved attachments for those documents.
  - Leave feedback through customer-safe channels.
- Currently can:
  - Potentially hit management comments routes for same-tenant documents.
  - Keep seeing document metadata via reading-progress endpoints after access changes.
  - Observe mutable current attachments rather than stable published sets.
- Main risk:
  - Policy bypass through shared/internal APIs.

### 9.3 Viewer
- Should be able to:
  - Read a clean, published public/viewer version.
- Currently can:
  - Land on a viewer page with no version preselected.
  - Interact with a surface where attachment semantics are not version-tight.
- Main risk:
  - Confusing behavior and leaky publication semantics.

### 9.4 Editor
- Should be able to:
  - Create/edit content, comment internally, submit review.
- Currently can:
  - Use a system whose publish guarantees are undermined by side paths.
  - Potentially create XSS-bearing changelog content if they can reach that flow indirectly through role hierarchy.
- Main risk:
  - The system does not make the safe path the only path.

### 9.5 Manager
- Should be able to:
  - Manage a limited user subset and publishing workflow.
- Currently can:
  - Create changelog entries that are publicly reachable.
  - Manage more user roles than the permission naming suggests.
- Main risk:
  - Authority surface is larger and less explicit than intended.

### 9.6 Admin
- Should be able to:
  - Operate the system safely with strong oversight tools.
- Currently can:
  - Be compromised via XSS on public pages if logged into the SPA.
  - Enumerate all companies through the company-management list endpoint instead of being scoped to their own tenant.
- Main risk:
  - Public content becomes an admin session-stealing vector, and company-management scope currently breaks tenant isolation.

### 9.7 System admin
- Should be able to:
  - Trust that revocation, publication, and private/internal rules are real.
- Currently can:
  - Rely on guarantees that are only partially true.
- Main risk:
  - Operational decisions based on false security assumptions.

## 10. Review by Engineering Quality

### 10.1 Code quality
- Positive:
  - There is real structure. This is not a random pile of handlers.
- Negative:
  - Critical invariants are not centralized.
  - Some abstractions are misleading because they imply guarantees the runtime does not actually hold.

### 10.2 Separation of concerns
- Positive:
  - Services, queries, policies, and adapters exist.
- Negative:
  - Authorization still leaks into route-specific shortcuts and alternative helper paths.
  - Public/portal/management boundaries are not clean enough.

### 10.3 Maintainability
- Positive:
  - Naming is often understandable.
- Negative:
  - Dead UI, drifted contracts, and alias-heavy lifecycle naming increase confusion.
  - You have multiple ways to do the same thing, and they do not agree.

### 10.4 Testability
- Positive:
  - The repo is test-heavy.
- Negative:
  - The tests are not forcing the important behavior.
  - Default test config is less portable than it should be.

### 10.5 Type safety and contracts
- Positive:
  - TypeScript usage is serious.
  - DTO/contracts exist.
- Negative:
  - The collab contract is drifted enough that typed contracts do not prevent config mismatch.

### 10.6 Security engineering
- Positive:
  - Core HTTP auth is stronger than average.
  - The document HTML sanitizer is a real asset.
- Negative:
  - URL tokens, localStorage auth, unsanitized public HTML, and inconsistent revocation handling are major design problems.

### 10.7 Reliability and failure handling
- Positive:
  - Some flows have explicit fallbacks and status handling.
- Negative:
  - Too many "fallbacks" are actually policy violations, especially the draft/publication fallbacks.
  - Warning noise and broken optional auth utilities indicate quality debt.

## 11. Priority Action Plan

### Immediate fixes
- Remove `role` and `tenant_id` from public registration payload handling.
- Scope the company listing endpoint to the caller's tenant unless the caller is a system admin.
- Remove query-string bearer token support for attachment downloads and WebSocket auth.
- Sanitize or redesign changelog and search rendering immediately.
- Force public changelog responses to published-only by default.
- Lock comments behind correct role/document access checks.
- Freeze or review-reset audience changes while a document is pending review.

### Short-term improvements
- Model publication as immutable snapshots, including attachment visibility.
- Add security regression tests for self-registration, comments, and session-revocation parity.
- Complete GDPR export coverage for sessions, security events, and message data.
- Remove the non-production `X-E2E-Test` rate-limit bypass or narrow it to true test envs.
- Add content-based validation for trusted upload types.
- Clean up collaboration URL/config ownership.
- Fix portal reading-history access leakage.

### Medium-term refactors
- Consolidate document access decisions into one policy service used by every surface.
- Split public, portal, viewer, and management APIs more cleanly.
- Remove dead comments UI and stale contract shapes.
- Replace broad exception suppression with explicit degradation/retry policies.
- Normalize lifecycle vocabulary around document state.
- Move production defaults to PostgreSQL instead of SQLite.

### Long-term ideas
- Move auth to httpOnly secure cookies or equivalent safer browser storage architecture.
- Add access-debugging and publish-diff tooling for admins/editors.
- Introduce release-bound attachment/version models instead of document-global attachment visibility.

## 12. Top 10 Highest-Value Fixes

1. Server-force public self-registration to one safe role and no caller-supplied tenant.
2. Scope company-management listing to the caller's tenant unless the caller is a system admin.
3. Delete all token-in-query auth patterns and replace them with scoped server-issued capabilities.
4. Rebuild comment authorization around document visibility plus true private-comment semantics.
5. Stop attachment upload from creating published versions automatically and bind public/customer reads to immutable published snapshots.
6. Sanitize changelog/search rendering and move auth tokens out of `localStorage`.
7. Freeze or review-reset audience changes while a document is pending review.
8. Complete GDPR export coverage for sessions, security events, and message/support data.
9. Move production defaults to PostgreSQL instead of SQLite.
10. Add invariant-focused tests that fail on the exact bugs above.

## 13. Risk Heatmap Summary by Area

| Area | Risk | Summary |
| --- | --- | --- |
| Auth | Critical | Multiple auth models exist; revocation is not uniformly enforced. |
| Multi-Tenancy | Critical | Admin company management currently exposes cross-tenant data. |
| Role Logic | Critical | UI/documentation imply restrictions that backend code does not consistently enforce. |
| Public Frontend | Critical | XSS sinks plus token storage create account-takeover risk. |
| Comments | Critical | Route exposure and privacy rules are broken. |
| Publication / Versioning | Critical | Public/customer/viewer content is not reliably tied to immutable published state. |
| Compliance / Data Governance | High | User-data export is incomplete relative to stored data. |
| Portal | High | Core access checks exist, but side endpoints leak metadata and mutable state. |
| Collaboration | High | Config drift and query-string token transport make the system brittle. |
| Testing | High | Broad suite, weak invariants, huge warning noise. |
| Configuration / Ops | High | Production defaults still point at SQLite and some test backdoors are too broad. |
| Browser Security (CSP/CORS) | High | No CSP on frontend nginx, CORS allows credentials with wildcard methods/headers. |
| Backup / Recovery | High | No backup strategy, no pre-migration snapshots, single SQLite file on Docker volume. |
| Password Policy | Medium | Length-only validation, no complexity requirements. |
| Dependency Hygiene | Medium | Dual JWT libraries, no automated `pip audit` / `npm audit` in CI. |
| Session Management | Medium | Unlimited concurrent sessions per user, no cleanup of expired sessions. |
| Email / Notifications | Medium | No retry on SMTP failure; fire-and-forget delivery for critical flows. |
| Tenant Lifecycle | Medium | Deactivated tenants' public documents remain internet-accessible. |
| General Maintainability | Medium | Strong structure, but too much hidden coupling and contract drift. |

## 14. Files / Modules That Appear Most Fragile

- `backend/app/api/management/auth.py`
- `backend/app/api/management/companies.py`
- `backend/app/api/management/attachments.py`
- `backend/app/api/management/comments.py`
- `backend/app/services/comment_service.py`
- `backend/app/services/gdpr_service.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/services/chat_service.py`
- `backend/app/api/public/documents.py`
- `backend/app/application/queries/portal_queries.py`
- `backend/app/api/portal/documents.py`
- `frontend/src/pages/public/PublicSearchPage.tsx`
- `frontend/src/pages/public/PublicChangelogPage.tsx`
- `frontend/src/lib/api/httpClient.ts`
- `frontend/src/hooks/useChatSocket.ts`
- `backend/app/web/router_registry.py`
- `backend/app/services/document_service.py` — 800+ lines, single point of failure for all document operations
- `backend/app/domain/events/dispatcher.py` — events lost on crash, broad exception suppression
- `frontend/nginx.conf` — missing CSP, contradictory XSS header

## 15. Files / Modules That Appear Strongest

- `backend/app/security.py`
- `backend/app/services/version_service.py`
- `frontend/src/lib/htmlSanitizer.ts`
- `frontend/src/lib/documentRenderer.tsx`
- `backend/app/services/collaboration_service.py`
- `backend/app/api/viewer/documents.py`
  - Note: this file is stronger on content rendering and version attachment cutoff than the corresponding public/portal flows, even though its overall UX is still awkward.
- `backend/app/middleware/security_headers.py` — well-implemented defense-in-depth headers with correct modern practices (X-XSS-Protection: 0, strict CSP for API, HSTS in production)
- `backend/Dockerfile` and `frontend/Dockerfile` — non-root users, slim base images, proper layer caching

## 16. Top Architectural Weaknesses

- Critical business invariants are not centralized. Alternative paths bypass the "real" policy logic.
- Surface naming (`management`, `portal`, `public`, `viewer`) implies stronger separation than the code actually enforces.
- Publication is modeled as both document status and version state, but read paths are not consistently tied to versioned releases.
- Auth is transport-specific instead of system-specific.
- The multi-tenant model is not consistently enforced at administrative listing/reporting boundaries.
- Production deployment defaults are still closer to a dev convenience stack than an operationally safe default.
- The repository has strong abstractions, but some of them are decorative because they are not the only path to execution.
- No backup or disaster recovery strategy exists — a single volume deletion or failed migration is unrecoverable.
- Dual JWT libraries (`python-jose` + `PyJWT`) increase supply-chain surface and create import confusion.
- Frontend HTML-serving layer (nginx) has no CSP, while the API layer does — defense-in-depth is inverted.

## 17. Top Logic Risks

- Caller-controlled role assignment during self-registration.
- Audience changes slipping in after review submission.
- Draft or unreviewed state leaking into public/customer/viewer experiences.
- Attachment visibility changing outside the publish process.
- Reading-history endpoints continuing to expose revoked documents.
- Comment visibility depending on tenant coincidence instead of actual document access rules.
- Deactivated tenants' public documents still served — tenant lifecycle not fully enforced on public reads.
- Scheduled publishes have no background executor — documents with `scheduled_publish_at` may never auto-publish.

## 18. Top Security / Permission Risks

- Stored XSS on public pages with bearer-token theft impact.
- Cross-tenant company enumeration through the admin company list.
- URL-based bearer token leakage for downloads and sockets.
- Revoked-session bypass on transports that only validate raw JWTs.
- Public exposure of unpublished changelog entries.
- "Private" comments that are not actually protected by private-comment rules.
- CORS configured with `allow_credentials=True` and wildcard methods/headers — one origin misconfiguration away from credential theft.
- No password complexity enforcement — `"aaaaaaaa"` is a valid password.
- No CSP on the frontend nginx layer where XSS actually executes.
- Abandoned `python-jose` library (2021, known CVEs) still in dependency tree.
- Unlimited concurrent sessions per user — compromised credentials can maintain many parallel sessions.
- Fire-and-forget email delivery — transient SMTP failure silently loses password reset and invitation emails.

## 19. Conclusion

If I were improving this project next, I would start with the trust boundaries, not the polish.

The first wave should harden registration, unify auth enforcement, fix public HTML rendering, and make publication immutable. Until those are fixed, the rest of the architecture is carrying more confidence than the runtime deserves.
