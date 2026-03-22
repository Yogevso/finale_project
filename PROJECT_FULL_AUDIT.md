# Project Full Audit

## 1. Executive Summary

The repository is not production-ready for a serious multi-tenant, customer-facing deployment.

It has some real strengths:
- The codebase is broad and ambitious. It has explicit enums, service/query layering in several areas, contract tests, and some good intent around publication integrity and tenant isolation.
- There are meaningful tests around route auth parity, publication behavior, public contracts, and some assistant tool controls.
- Several newer abstractions are directionally right: `VisibilitySpec`, `DocumentAccessPolicy`, `published_attachment_resolver`, projection caching, and explicit role enums.

The problem is that the strongest-looking parts are not the most dangerous parts. The highest-risk failures sit in cross-layer business logic, not in syntax, typing, or route registration.

Main risks:
- The AI assistant can expose document content without proper authorization, and it is exposed to customer users.
- Tenant isolation is weak in multiple places. Internal users can become unscoped, and company-admin flows can reassign or orphan users in dangerous ways.
- Authorization is inconsistent across frontend routes, backend route dependencies, and deeper service/policy logic.
- Publication snapshot rules are only partially centralized. Portal/public metadata and actual download behavior diverge.
- The repository still carries legacy/current dual models (`platform` vs `platform_name`, `ACTIVE` vs `PUBLISHED`) in ways that already leak into behavior.

Most urgent issues:
- Lock down assistant document injection immediately.
- Remove the "unscoped internal user" state or reject it everywhere except system admin.
- Fix company user reassignment/removal logic.
- Fix the attachment upload validation bug that bypasses magic-byte validation.
- Align route/UI/backend role rules for support, feedback, versions, and search.

Overall verdict:
- The system is not failing because it is unfinished.
- It is failing because core trust boundaries are inconsistently enforced.
- That is worse than an incomplete product, because it creates false confidence.

## 2. Critical Problems

### 2.1 Assistant can inject arbitrary document content without authorization
- Severity: Critical
- Area: Security / Auth / Role Logic / Backend / Frontend
- Affected files:
  - `backend/app/api/management/assistant.py`
  - `backend/app/assistant/engine.py`
  - `frontend/src/lib/api/assistantApi.ts`
  - `frontend/src/features/assistant/useAssistantChat.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/layouts/CustomerLayout.tsx`
- Description:
  - The assistant API accepts `document_ids` from the client.
  - `AssistantEngine.chat()` loads each document by raw ID and injects latest version content into the prompt without checking `DocumentAccessPolicy.can_view_document()` for that path.
  - Customer users have assistant UI exposure via `/portal/assistant` and the customer chat bubble.
- Why it is a problem:
  - This is a direct confidentiality failure.
  - The assistant becomes a document exfiltration API.
  - The issue is not theoretical. The explicit `document_ids` path is separate from the safer `@mention` path and bypasses its permission check.
- Example scenario:
  - A customer user guesses or enumerates document IDs and sends `/assistant/chat` with `document_ids=[123]`.
  - The backend injects the document's latest version content into the LLM prompt and returns it in the answer, even if the document is internal or belongs to another tenant.
- Recommended fix:
  - Reject `document_ids` that the requesting user cannot view.
  - Apply the same access policy to explicit document IDs that the `@mention` flow uses.
  - Restrict assistant routes to internal roles unless there is a deliberate, separately designed customer-safe assistant mode.
  - Add end-to-end tests for customer -> assistant -> foreign/internal/company document attempts.

### 2.2 Tenant isolation breaks when internal users become unscoped
- Severity: Critical
- Area: Security / Role Logic / Auth / Architecture
- Affected files:
  - `backend/app/application/policies/access_policies.py`
  - `backend/app/security.py`
- Description:
  - `DocumentAccessPolicy._same_tenant_or_unscoped()` returns `True` when either the document tenant or user tenant is missing.
  - `get_current_active_user()` only checks company activity for internal users when `tenant_id is not None`.
  - That means an active internal user with `tenant_id=None` is treated as valid and can pass tenant-boundary checks that should fail closed.
- Why it is a problem:
  - "No tenant" is treated as "allowed everywhere" in edit/delete/publish checks.
  - That is the exact opposite of safe multi-tenant behavior.
- Example scenario:
  - An internal editor/admin is left with `tenant_id=None`.
  - They can still authenticate and may pass edit/delete/publish checks on documents owned by normal tenants.
- Recommended fix:
  - Remove the unscoped internal-user state entirely, except for `SYSTEM_ADMIN`.
  - Make tenant-boundary checks fail closed whenever a non-system-admin internal user has `tenant_id=None`.
  - Add a migration or repair script to find and fix orphaned internal users.

### 2.3 Company admin flows let admins hijack users across tenants and create orphaned internal users
- Severity: Critical
- Area: Security / Role Logic / Tenant Isolation / Backend
- Affected files:
  - `backend/app/api/management/companies.py`
- Description:
  - `add_user_to_company()` reassigns any user found by ID or email into the target company without validating the target user's current tenant, role, or ownership rules.
  - `remove_user_from_company()` allows non-customer users to be detached from a tenant entirely by setting `tenant_id=None`.
  - `create_company()` is available to `ADMIN`, even though the rest of the file strongly implies non-system-admin admins are tenant-scoped.
- Why it is a problem:
  - This is a user-binding integrity failure.
  - It enables cross-tenant user hijacking and directly creates the unscoped-user state that breaks document authorization.
- Example scenario:
  - A tenant admin adds another tenant's editor to their own company by email.
  - The victim's tenant binding changes.
  - A separate admin removes an internal user from a company, creating `tenant_id=None`.
- Recommended fix:
  - Only `SYSTEM_ADMIN` should move users between tenants.
  - Tenant admins should only manage users already in their tenant, and should never be able to clear tenant binding for internal roles.
  - `create_company()` should be `SYSTEM_ADMIN` only unless the product intentionally allows tenant admins to create top-level tenants, which the rest of the code clearly does not support.

### 2.4 Attachment upload validation is broken by method-resolution/signature mismatch
- Severity: Critical
- Area: Security / Backend / File Handling
- Affected files:
  - `backend/app/services/attachment_service/common.py`
  - `backend/app/services/attachment_service/upload.py`
  - `backend/app/services/attachment_service/__init__.py`
- Description:
  - `AttachmentServiceCommonMixin.upload_attachment()` calls `cls._validate_magic_bytes(content, file_ext, original_filename)`.
  - The MRO resolves to `AttachmentServiceUploadMixin._validate_magic_bytes(content, original_filename, content_type)`.
  - The arguments are in the wrong order for the resolved method.
- Why it is a problem:
  - Restricted-extension enforcement is silently bypassed on the main upload path.
  - Security-critical validation is present in code but not reliably doing what it claims to do.
- Example scenario:
  - A file named `payload.docx` with non-DOCX bytes reaches `upload_attachment()`.
  - The wrong signature treats `.docx` as a filename and skips the restricted-extension rule.
- Recommended fix:
  - Remove the duplicate `_validate_magic_bytes()` implementations.
  - Keep one canonical validator with one canonical signature.
  - Add direct tests for the exact `upload_attachment()` entrypoint, not only helper-level tests.

### 2.5 Search exposes metadata to users who should not see it
- Severity: Critical
- Area: Security / Search / Backend
- Affected files:
  - `backend/app/api/management/search.py`
  - `backend/app/application/queries/search_queries.py`
  - `backend/app/domain/specifications/queries.py`
- Description:
  - Management search routes use `get_current_active_user`, not an internal-only dependency.
  - `_load_autocomplete()` and `_load_facets()` apply tenant scoping but not visibility filtering.
  - `VisibilitySpec.sql_clauses()` uses `company_id` in raw SQL against `document_company_assignments`, but the actual column is `tenant_id`.
- Why it is a problem:
  - Customers can reach internal search endpoints.
  - Even if full result pages are partially filtered, autocomplete and facets leak document titles, categories, and status counts for documents the user cannot see.
  - The raw SQL bug forces hidden fallback behavior and undermines trust in the search layer.
- Example scenario:
  - A customer calls `/api/v1/search/autocomplete?q=roadmap`.
  - Titles from tenant documents matching the customer's tenant scope but not the customer's visibility rules are returned.
- Recommended fix:
  - Restrict management search endpoints to internal users.
  - Apply `VisibilitySpec` to autocomplete and facets.
  - Fix the raw SQL column name and add tests for customer/company visibility in search, autocomplete, and facets.

## 3. Problems

### 3.1 Portal detail leaks attachment metadata outside the published snapshot
- Severity: High
- Category: Backend / UX Flow / Publication Integrity
- Affected files:
  - `backend/app/application/queries/portal_queries.py`
  - `backend/app/api/portal/documents.py`
  - `frontend/src/pages/portal/CustomerDocumentPage.tsx`
- Description:
  - Portal document detail loads all attachments for the document and renders download URLs for all of them.
  - The actual download endpoint later checks the published snapshot and rejects some of those attachments.
- Expected behavior:
  - Portal detail should only show attachments that are valid in the currently published snapshot.
- Current behavior:
  - Customers see attachments that they cannot actually download.
- Recommendation:
  - Filter detail attachments through `published_attachment_resolver` before rendering metadata or URLs.

### 3.2 Public and portal attachment rules are not using one canonical snapshot mechanism
- Severity: High
- Category: Backend / Architecture / Publication Integrity
- Affected files:
  - `backend/app/api/public/documents.py`
  - `backend/app/application/queries/portal_queries.py`
  - `backend/app/services/published_attachment_resolver.py`
- Description:
  - Public detail still uses `uploaded_at <= cutoff`.
  - Portal attachment download uses the newer snapshot resolver.
  - The system is split between timestamp-based logic and immutable publish-snapshot logic.
- Expected behavior:
  - One resolver should define "attachment visible to readers" everywhere.
- Current behavior:
  - Different endpoints can disagree about which attachments exist for the same published document.
- Recommendation:
  - Replace all timestamp-based public/portal attachment selection with the central snapshot resolver.

### 3.3 Reading-progress access recheck for company documents is wrong
- Severity: High
- Category: Backend / Role Logic / UX Flow
- Affected files:
  - `backend/app/api/portal/documents.py`
- Description:
  - `_customer_can_still_access()` returns `user.tenant_id is not None` for `COMPANY` documents.
  - It does not verify assignment of that tenant to the document.
- Expected behavior:
  - Reading-progress endpoints should exclude company documents once the customer's company no longer has access.
- Current behavior:
  - Recently viewed / continue-reading can still surface documents the customer should no longer access.
- Recommendation:
  - Use the same company-assignment visibility check as the portal query layer, not a weak shortcut.

### 3.4 Portal list can claim attachments exist when the published snapshot has none
- Severity: Medium
- Category: Backend / UX Consistency
- Affected files:
  - `backend/app/application/queries/portal_queries.py`
- Description:
  - `execute_list_documents()` counts all attachments on the document when setting `has_attachments`.
- Expected behavior:
  - Customer list cards should reflect only attachments available in the published reader snapshot.
- Current behavior:
  - A document can show attachment availability in the list and then show none in the actual published detail/download path.
- Recommendation:
  - Compute attachment flags from published-snapshot attachments only.

### 3.5 Feedback PII protection is inconsistently enforced
- Severity: High
- Category: Security / Role Logic / Backend
- Affected files:
  - `backend/app/application/policies/access_policies.py`
  - `backend/app/api/management/feedback.py`
- Description:
  - `FeedbackAccessPolicy.can_see_email()` restricts submitter email visibility to admin/system_admin.
  - `respond_to_feedback()` and `update_feedback_status()` return `user_email` unconditionally.
- Expected behavior:
  - PII masking should be enforced uniformly across all feedback responses.
- Current behavior:
  - Managers can receive customer email in response payloads despite policy saying they should not.
- Recommendation:
  - Centralize response mapping and always apply `can_see_email()`.

### 3.6 Feedback status updates are allowed for editor/viewer roles
- Severity: High
- Category: Role Logic / Backend
- Affected files:
  - `backend/app/application/policies/access_policies.py`
  - `backend/app/api/management/feedback.py`
  - `frontend/src/App.tsx`
- Description:
  - `can_update_status()` includes `EDITOR` and `VIEWER`.
  - The status-update route uses `require_internal_staff`.
  - The frontend guards feedback UI behind `ManagerGuard`.
- Expected behavior:
  - Backend permissions should match the intended management role boundary.
- Current behavior:
  - Direct API callers can update feedback status with lower roles than the UI implies.
- Recommendation:
  - Narrow status updates to the same roles that are allowed to manage/respond to feedback, unless there is a deliberate product requirement otherwise.

### 3.7 Feedback stats endpoint is not tenant-scoped
- Severity: High
- Category: Security / Analytics / Backend
- Affected files:
  - `backend/app/api/management/feedback.py`
- Description:
  - `/feedback/stats/summary` returns platform-wide totals for any admin/manager.
- Expected behavior:
  - Non-system-admin users should only see feedback stats for their tenant scope.
- Current behavior:
  - Tenant-scoped roles can see global numbers.
- Recommendation:
  - Scope counts by tenant for all non-system-admin callers.

### 3.8 Feedback tenant scoping depends on the current user row, not immutable feedback context
- Severity: Medium
- Category: Data Integrity / Backend
- Affected files:
  - `backend/app/api/management/feedback.py`
- Description:
  - `list_all_feedback()` scopes via `Feedback.user -> User.tenant_id`.
- Expected behavior:
  - Feedback visibility should be derived from stable feedback/document tenant context.
- Current behavior:
  - If a user changes tenants later, old feedback can move between tenant views.
- Recommendation:
  - Scope using document tenant or store an immutable feedback tenant snapshot.

### 3.9 Support module permissions are incoherent across UI, policy, routes, and service logic
- Severity: High
- Category: Role Logic / Architecture / UX Flow
- Affected files:
  - `backend/app/application/policies/access_policies.py`
  - `backend/app/api/management/support.py`
  - `backend/app/services/support_service.py`
  - `frontend/src/App.tsx`
- Description:
  - UI restricts support to `ManagerGuard`.
  - Policy allows admin/manager/editor/viewer.
  - Routes use `require_internal_user` for almost everything.
  - Service layer treats viewers/customers mostly as ticket owners only, not agents.
- Expected behavior:
  - One explicit role matrix should govern support access.
- Current behavior:
  - Viewers can reach routes they do not meaningfully own.
  - Editors can act as support agents through the API even though the UI says managers and above.
- Recommendation:
  - Decide which roles are support agents, encode it once, and apply it consistently in router dependencies and service checks.

### 3.10 Internal support ticket creation is conceptually wrong
- Severity: Medium
- Category: Product Flow / Backend
- Affected files:
  - `backend/app/api/management/support.py`
  - `backend/app/services/support_service.py`
- Description:
  - Internal users call `create_ticket()` and are passed as `customer=current_user`.
- Expected behavior:
  - Internal support should create tickets on behalf of a customer, or this route should be customer-only.
- Current behavior:
  - Internal users create tickets recorded as if they were the customer.
- Recommendation:
  - Split customer ticket creation from internal case creation/escalation flows.

### 3.11 Version compare flow is exposed to viewers in the frontend but blocked by the backend
- Severity: High
- Category: Frontend / Role Logic / UX Flow
- Affected files:
  - `frontend/src/App.tsx`
  - `frontend/src/components/VersionsSection.tsx`
  - `frontend/src/pages/VersionComparePage.tsx`
  - `backend/app/api/management/versions.py`
- Description:
  - The compare page lives under `InternalGuard`, not editor-only protection.
  - `VersionsSection` shows the compare link whenever more than one version exists.
  - All management version routes require `require_editor`.
- Expected behavior:
  - Either viewers should be allowed to compare versions end-to-end, or the UI should not route them there.
- Current behavior:
  - Viewer users can reach a page wired to APIs they are not allowed to call.
- Recommendation:
  - Align the route guard, link visibility, and backend dependency.

### 3.12 WebSocket auth skips active-tenant enforcement
- Severity: High
- Category: Security / Auth / Reliability
- Affected files:
  - `backend/app/ws/chat_ws.py`
  - `backend/app/ws/support_ws.py`
  - `backend/app/security.py`
- Description:
  - WS auth validates token, activity, and revocation, but it does not apply the inactive-tenant checks used by `get_current_active_user()`.
- Expected behavior:
  - Deactivated tenant users should lose real-time access immediately under the same rules as HTTP.
- Current behavior:
  - A tenant deactivation can leave existing real-time access alive until session expiry or explicit revocation.
- Recommendation:
  - Reuse the same active-tenant logic for WS auth that HTTP uses.

### 3.13 Company deactivation and company deletion have different security consequences
- Severity: High
- Category: Auth / Architecture / Operations
- Affected files:
  - `backend/app/api/management/companies.py`
- Description:
  - `update_company(is_active=False)` cancels invitations only.
  - `delete_company()` also revokes sessions, invalidates tokens, and removes document assignments.
- Expected behavior:
  - Deactivation semantics should be explicit and consistent with session/security expectations.
- Current behavior:
  - "Deactivated company" can still have live sessions until unrelated mechanisms cut them off.
- Recommendation:
  - Treat deactivation as a security event and revoke sessions/tokens there too, or document and implement a separate suspension model explicitly.

### 3.14 Public and portal filtering still rely on deprecated `Document.platform`
- Severity: Medium
- Category: Backend / Data Model / Maintainability
- Affected files:
  - `backend/app/api/public/documents.py`
  - `backend/app/application/queries/portal_queries.py`
- Description:
  - Public list/search/history and portal list/facets/related-doc logic still filter or group on the deprecated `Document.platform` field.
- Expected behavior:
  - Filtering/grouping should run on the canonical platform model, not the legacy fallback.
- Current behavior:
  - Response payloads use `platform_name`, while search/filter/facet logic uses the deprecated string field.
- Recommendation:
  - Finish the migration and remove functional dependence on `Document.platform`.

### 3.15 Search hides failures with a broad fallback instead of surfacing broken FTS logic
- Severity: Medium
- Category: Architecture / Reliability / Performance
- Affected files:
  - `backend/app/application/queries/search_queries.py`
  - `backend/app/domain/specifications/queries.py`
- Description:
  - `execute_search_documents()` catches any exception from FTS and silently falls back to ORM search.
- Expected behavior:
  - Query bugs and index/schema mismatches should be observable.
- Current behavior:
  - The system can be "working" while the intended search path is broken and slower.
- Recommendation:
  - Catch only known search-backend failures, log them at warning/error level with enough detail, and test the FTS path directly.

### 3.16 Chat document-room creation does not validate document access
- Severity: High
- Category: Security / Backend / Role Logic
- Affected files:
  - `backend/app/services/chat_service.py`
- Description:
  - `create_document_chat()` loads a document by ID and creates a tenant-scoped chat under the creator's tenant without verifying document tenant or actual document access.
- Expected behavior:
  - Document-scoped chats should only be creatable for documents the caller can legitimately access.
- Current behavior:
  - The service can create chats around a foreign document and auto-add its author ID.
- Recommendation:
  - Require document access checks and same-tenant validation before chat creation.

### 3.17 Chat WebSocket message validation is weaker than REST validation
- Severity: Medium
- Category: Reliability / Security / Backend
- Affected files:
  - `backend/app/services/chat_service.py`
  - `backend/app/ws/chat_ws.py`
- Description:
  - REST uses `ChatService.MAX_MESSAGE_LENGTH`.
  - WS send-message persists content directly and only checks raw frame size, not logical message length.
- Expected behavior:
  - Message limits should be consistent across transport layers.
- Current behavior:
  - WS path accepts payloads that REST would reject.
- Recommendation:
  - Route all message creation through `ChatService.send_message()` or share one validator.

### 3.18 Chat and support file/message boundaries still trust client-side MIME too much
- Severity: Medium
- Category: Security / File Handling
- Affected files:
  - `backend/app/api/management/chat.py`
  - `backend/app/ws/support_ws.py`
  - `backend/app/ws/chat_ws.py`
- Description:
  - Chat file upload is stored based on client MIME allowlists without the stronger content sniffing present elsewhere.
- Expected behavior:
  - File acceptance should be backed by server-side validation.
- Current behavior:
  - Chat attachments are a weaker validation path than document attachments.
- Recommendation:
  - Reuse attachment validation rules or add a dedicated chat-file validator.

### 3.19 Direct-chat role logic is inconsistent for `VIEWER`
- Severity: Medium
- Category: Role Logic / Consistency
- Affected files:
  - `backend/app/services/chat_service.py`
- Description:
  - The special internal-role list used for cross-tenant direct-chat exceptions omits `viewer`, even though viewer is an internal role elsewhere.
- Expected behavior:
  - Internal role classifications should be consistent.
- Current behavior:
  - Viewer behavior diverges from the rest of the system's role model.
- Recommendation:
  - Centralize role grouping instead of hand-rolling role sets in features.

### 3.20 Invitation acceptance bootstraps auth differently from normal login
- Severity: Medium
- Category: Auth / UX Flow
- Affected files:
  - `backend/app/api/management/auth.py`
  - `frontend/src/pages/AcceptInvitationPage.tsx`
  - `frontend/src/lib/api/authApi.ts`
  - `frontend/src/lib/api/httpClient.ts`
- Description:
  - Normal login sets an HTTP-only refresh cookie via `_token_json_response()`.
  - `accept_invitation()` returns `TokenResponse` directly and does not set that cookie.
  - Frontend compensates by storing tokens in memory only.
- Expected behavior:
  - Invitation accept should bootstrap the same session model as normal login.
- Current behavior:
  - Session persistence after invitation acceptance depends on in-memory state rather than the cookie-based restore path.
- Recommendation:
  - Return the same cookie-setting response shape as login.

### 3.21 Password requirements are stricter on the backend than the invitation UI communicates
- Severity: Low
- Category: UX / Validation Consistency
- Affected files:
  - `backend/app/api/management/auth.py`
  - `frontend/src/pages/AcceptInvitationPage.tsx`
- Description:
  - Frontend says "Must be at least 8 characters."
  - Backend also requires uppercase, lowercase, digit, and special character.
- Expected behavior:
  - Client hints should match server rules.
- Current behavior:
  - Users hit avoidable server-side validation errors.
- Recommendation:
  - Mirror server complexity requirements in the form and helper text.

### 3.22 Viewer page intentionally avoids auto-selecting the latest version
- Severity: Low
- Category: Product Flow / UX
- Affected files:
  - `frontend/src/pages/viewer/ViewerDocumentPage.tsx`
- Description:
  - The UI explicitly tells users the viewer does not auto-select the latest version.
- Expected behavior:
  - Read-only viewers should default to the latest safe version unless there is a strong reason not to.
- Current behavior:
  - Users are pushed into a confusing manual version choice in a supposedly simple viewing mode.
- Recommendation:
  - Default to the latest published/viewable version.

### 3.23 Potential Issue: comment visibility and chat-bridging rules are product-fragile
- Severity: Medium
- Category: Product Flow / Architecture / Potential Issue
- Affected files:
  - `backend/app/services/comment_service.py`
- Description:
  - Comment visibility is contributor-centric, not purely document-visibility-centric.
  - Comment creation can trigger chat side effects.
- Expected behavior:
  - Comment visibility and collaboration side effects should be explicit product decisions, not surprising coupling.
- Current behavior:
  - The rules are unusual enough that future developers are likely to misread them.
- Recommendation:
  - Document the intended model clearly or simplify it. If the product intent is "any document viewer can see non-private comments," the implementation is currently misleading.

## 4. Improvement Suggestions

### 4.1 Build one canonical authorization matrix
- Area: Architecture / Security
- Why it would help:
  - The same role concept is currently redefined in guards, route dependencies, policy objects, and service methods.
- Suggested implementation direction:
  - Create a central capability matrix by role and feature, and make frontend guards consume the same capability model the backend uses.
- Priority: High

### 4.2 Collapse duplicate validation logic in attachment handling
- Area: Backend / Maintainability
- Why it would help:
  - Duplicated validators already caused a security regression.
- Suggested implementation direction:
  - One validation module, one signature, one test suite, one upload entrypoint.
- Priority: High

### 4.3 Finish the platform-field migration
- Area: Data Model / Backend
- Why it would help:
  - The current `platform` vs `platform_name` split guarantees more drift.
- Suggested implementation direction:
  - Migrate all filters/facets/history queries to the canonical platform relation, backfill, then delete the deprecated field from active logic.
- Priority: High

### 4.4 Make publication snapshot rules a single subsystem
- Area: Backend / Product Integrity
- Why it would help:
  - Public, portal, viewer, and download surfaces should never disagree on what was published.
- Suggested implementation direction:
  - Replace every "uploaded before publish timestamp" shortcut with the snapshot resolver.
- Priority: High

### 4.5 Add service-level and cross-layer auth tests, not only route-dependency tests
- Area: Testability / Security
- Why it would help:
  - Route auth parity tests currently pass while deeper business logic still leaks.
- Suggested implementation direction:
  - Add tests for: assistant doc injection, company user reassignment, unscoped internal users, portal attachment listing vs download, feedback email visibility, support role parity.
- Priority: High

### 4.6 Introduce explicit tenant-lifecycle semantics
- Area: Operations / Auth / Architecture
- Why it would help:
  - "Inactive company" currently means different things in different channels.
- Suggested implementation direction:
  - Define suspend, deactivate, delete, and reactivate as explicit lifecycle states with guaranteed session/token/WS behavior.
- Priority: Medium

### 4.7 Remove broad `except Exception` paths from core query flows
- Area: Reliability / Maintainability
- Why it would help:
  - The code is currently able to hide broken primary logic.
- Suggested implementation direction:
  - Catch targeted exceptions and emit structured logs/metrics.
- Priority: Medium

### 4.8 Move sensitive response mapping into dedicated presenters
- Area: Backend / Maintainability
- Why it would help:
  - Repeated inline response mapping is already causing inconsistent PII masking.
- Suggested implementation direction:
  - Use a presenter/serializer layer for feedback, support, assistant, and portal DTOs.
- Priority: Medium

## 5. Ideas

- Add a "security assertions" test suite that crawls feature capabilities by role and tenant relationship, not just endpoint dependencies.
- Add a tenant-scope invariant checker that runs in CI and rejects non-system-admin internal users with `tenant_id=None`.
- Add an audit event whenever a user's tenant binding changes, including actor, old tenant, new tenant, and reason.
- Add explicit feature flags or separate products for customer-safe assistant vs internal authoring assistant. Right now they are mixed.
- Add a release-integrity dashboard that shows the published version, published attachment snapshot, and visibility snapshot together. That would make drift obvious.
- Add a route/UI parity linter that flags frontend routes linked for roles that backend dependencies reject.

## 6. Helpful Notes

- Assumption: `ADMIN` is intended to be tenant-scoped except for `SYSTEM_ADMIN`. This is strongly implied by `_enforce_tenant_scope()`, route guards, and comments in `companies.py`.
- The repository contains both older and newer patterns. Newer abstractions are usually better, but they are not fully adopted.
- Passing tests do not contradict the audit. The targeted run below passed, but it mostly verifies route-level auth and a narrower slice of publication/security behavior:
  - `pytest -n 0 --basetemp .pytest_tmp tests/test_wave_af_publication.py tests/test_wave_ae_security.py tests/test_route_auth_parity.py tests/test_dependencies_permissions.py -q`
  - Result: `97 passed`
- Several issues are not "missing code." They are contradictions between code that already exists.
- The project has useful architecture docs and debt notes, but some of the most dangerous gaps are lower-level and more concrete than those docs suggest.

## 7. Review by Feature

### 7.1 Authentication, session, and invitation flow
- Supposed to do:
  - Authenticate users, enforce tenant activity, bootstrap stable sessions, and let invitation acceptance behave like first-class login.
- What is good:
  - Login/refresh flow has cookie support and some session revocation logic.
  - Password complexity is enforced server-side.
- What is problematic:
  - Invitation acceptance bypasses the normal refresh-cookie bootstrap.
  - WS auth does not enforce active-tenant rules consistently with HTTP.
  - Internal users without a tenant are still accepted unless they are customers.
- What is missing:
  - One consistent auth bootstrap path.
  - One consistent tenant-active check across HTTP and WS.
- Production readiness:
  - Superficially functional, not safely coherent.

### 7.2 Company and tenant management
- Supposed to do:
  - Let privileged users manage companies, users, and lifecycle safely within tenant boundaries.
- What is good:
  - There is some explicit scoping logic and delete-company cleanup for sessions/assignments.
- What is problematic:
  - Regular admins can create companies.
  - Tenant admins can rebind arbitrary users into their company.
  - Internal users can be orphaned from tenants.
  - Deactivation and deletion have different security outcomes.
- What is missing:
  - A hard rule for who can move users across tenants.
  - A prohibition on unscoped internal users.
- Production readiness:
  - Unsafe for multi-tenant administration.

### 7.3 Document lifecycle, versioning, and compare flow
- Supposed to do:
  - Let internal staff create, review, compare, and publish versions with role-aware controls.
- What is good:
  - Version routes are at least protected on the backend by `require_editor`.
  - There are tests around publication integrity and assistant tool limits.
- What is problematic:
  - Compare UI is exposed to viewers while backend requires editor.
  - Some service methods rely too heavily on route dependencies for real enforcement.
- What is missing:
  - Full route-to-service-to-UI consistency.
- Production readiness:
  - Core mechanics exist, but role-flow integrity is sloppy.

### 7.4 Attachments and published releases
- Supposed to do:
  - Validate uploads strongly and show/download only attachments in the published snapshot.
- What is good:
  - A central `published_attachment_resolver` exists.
  - Public attachment download checks the snapshot.
- What is problematic:
  - Main upload validation is broken.
  - Portal detail still shows all attachments.
  - Public/portal metadata and actual download behavior do not fully agree.
- What is missing:
  - One source of truth for reader-visible attachments.
- Production readiness:
  - Not safe enough.

### 7.5 Search
- Supposed to do:
  - Provide scoped search, autocomplete, facets, analytics, and saved searches.
- What is good:
  - There is a visibility-spec abstraction and FTS path with ORM fallback.
- What is problematic:
  - Management search is not internal-only.
  - Autocomplete/facets ignore visibility.
  - FTS company-visibility SQL is wrong and hidden by broad fallback.
- What is missing:
  - Tests for metadata leakage by role/visibility.
- Production readiness:
  - Search exists, but trust boundaries are weak.

### 7.6 AI assistant
- Supposed to do:
  - Provide contextual assistant answers and controlled tool execution with auditability.
- What is good:
  - Tool routing, conversation history, and audit-aware tool design show real effort.
  - Cross-tenant version tool tests exist.
- What is problematic:
  - Explicit document context injection bypasses authorization.
  - Customer-facing assistant surface exists on top of that.
  - Confirmation-required tool flow is not truly resumable or enforceable.
- What is missing:
  - One explicit trust model for customer-safe assistant access.
  - A persistent confirmation state machine.
- Production readiness:
  - The feature is high-risk in its current form.

### 7.7 Feedback management
- Supposed to do:
  - Let customers submit feedback and authorized internal staff triage/respond safely.
- What is good:
  - There is at least an extracted feedback access policy and contributor-based intent.
- What is problematic:
  - Email PII masking is inconsistent.
  - Status update permissions are wider than management permissions.
  - Stats are not tenant-scoped.
  - Tenant scoping depends on mutable user records.
- What is missing:
  - A stable feedback visibility/ownership model.
- Production readiness:
  - Not acceptable for sensitive customer communication data.

### 7.8 Support
- Supposed to do:
  - Let customers and support staff create and manage support tickets with clear role boundaries.
- What is good:
  - There is a service layer with access helpers and internal-note handling.
- What is problematic:
  - The role model is inconsistent across policy, routes, service, and UI.
  - Internal ticket creation models internal users as customers.
  - WS and HTTP role/lifecycle behavior are not aligned.
- What is missing:
  - A clean distinction between customer flows and agent flows.
- Production readiness:
  - Operationally confusing and likely to create support debt.

### 7.9 Chat and real-time collaboration
- Supposed to do:
  - Provide internal messaging and document-linked discussions safely.
- What is good:
  - There is a reasonably complete service and WS stack.
- What is problematic:
  - Document chat creation skips document access validation.
  - WS validation is weaker than REST.
  - Role grouping is inconsistent.
- What is missing:
  - Unified permission checks and shared validators between transports.
- Production readiness:
  - Functional, but security boundaries are not trustworthy enough.

### 7.10 Portal/public/viewer experiences
- Supposed to do:
  - Give customers, anonymous users, and viewers a stable read path that reflects published state.
- What is good:
  - Public detail does require a published version.
  - Viewer/public/portal are clearly separated conceptually.
- What is problematic:
  - Portal detail attachment metadata is wrong.
  - Reading-progress filtering is too weak for company docs.
  - Viewer UX intentionally avoids selecting the latest version.
  - Public filtering still uses deprecated fields.
- What is missing:
  - Strong published-state consistency across all read surfaces.
- Production readiness:
  - The happy path mostly works; the edges do not.

## 8. Review by Flow

### 8.1 Invitation accept -> logged-in session
- Entry points:
  - `/auth/invitation/accept`, `AcceptInvitationPage`
- Breaks:
  - Backend returns tokens directly instead of cookie-setting login response.
  - Frontend stores session only in memory after accept.
- Result:
  - Session bootstrap differs from normal login and is easier to lose.

### 8.2 Internal authoring -> version compare -> publish
- Entry points:
  - `/documents/:id`, `/documents/:id/compare`, version APIs
- Breaks:
  - Frontend allows viewer navigation to compare.
  - Backend requires editor.
- Result:
  - Flow works only for some roles and fails late.

### 8.3 Customer portal browse -> open doc -> download attachment
- Entry points:
  - `/portal/documents`, `/portal/documents/:id`, attachment routes
- Breaks:
  - Detail page lists all attachments.
  - Download route correctly rejects unpublished-snapshot attachments.
- Result:
  - User sees broken actions because listing and download disagree.

### 8.4 Customer reading progress -> lost access
- Entry points:
  - `/portal/reading-progress/recent`, `/continue`
- Breaks:
  - Company visibility recheck is too weak.
- Result:
  - Users can keep seeing stale progress entries for documents they should no longer have.

### 8.5 Customer feedback -> internal triage -> response
- Entry points:
  - Feedback submission and management routes
- Breaks:
  - PII masking is inconsistent.
  - Status changes are allowed for lower roles than the UI implies.
  - Stats are global for tenant-scoped roles.
- Result:
  - Operational and privacy boundaries are not trustworthy.

### 8.6 Internal/customer support ticket flow
- Entry points:
  - Support pages, support API, support WS
- Breaks:
  - Role model is fragmented.
  - Internal "create ticket" acts as customer creation.
  - WS auth misses tenant-active enforcement.
- Result:
  - Support behavior is functional but policy-incoherent.

### 8.7 Assistant ask with document context
- Entry points:
  - `/assistant/chat`, portal assistant UI, internal assistant UI
- Breaks:
  - Explicit `document_ids` bypass doc-visibility checks.
  - Confirm-required tool flow is not end-to-end real.
- Result:
  - The feature crosses the line from "rough UX" into "security bug."

## 9. Review by User Type / Role

### 9.1 Anonymous user
- Should be able to:
  - Access public document surfaces only.
- Currently can:
  - Mostly that.
- Main gaps:
  - Public/public-download consistency is weaker than it should be, but this is not the most dangerous role.

### 9.2 Customer
- Should be able to:
  - View only public and assigned company documents in their tenant, use portal features safely, submit feedback/support.
- Currently can:
  - Reach assistant routes and customer assistant UI.
  - Reach management search endpoints because they only require authenticated users.
  - See portal attachment entries that later fail to download.
  - Potentially use assistant `document_ids` to read unauthorized content.
- Main risks:
  - Biggest exposure surface in the system right now.

### 9.3 Viewer
- Should be able to:
  - Read internal content, not mutate management workflows.
- Currently can:
  - Reach compare UI that depends on editor-only APIs.
  - Update feedback status through the backend.
  - Reach support routes guarded only as internal-user routes.
- Main risks:
  - UI and backend disagree on what "viewer" means.

### 9.4 Editor
- Should be able to:
  - Author content, participate in collaboration, not perform management-only actions.
- Currently can:
  - Update feedback status.
  - Act as support agent via service logic in places where the UI says manager-only.
- Main risks:
  - "Internal staff" is used as a shortcut where actual capability should be narrower.

### 9.5 Manager
- Should be able to:
  - Publish/manage feedback/support within tenant scope.
- Currently can:
  - Receive customer email in some feedback responses despite policy saying otherwise.
  - See global feedback stats rather than tenant-scoped data.
- Main risks:
  - Overexposure of PII and data beyond tenant scope.

### 9.6 Admin
- Should be able to:
  - Manage their tenant, users, and operations consistent with tenant scope.
- Currently can:
  - Create companies globally.
  - Reassign arbitrary users to their company.
  - Remove internal users from tenant binding entirely.
- Main risks:
  - This role is underconstrained in the exact places where tenant isolation matters most.

### 9.7 System admin
- Should be able to:
  - Cross tenant boundaries intentionally and safely.
- Currently can:
  - Do that, but the system also accidentally grants some cross-tenant-like behavior to non-system-admin states.
- Main risks:
  - The distinction between "true global admin" and "broken unscoped internal user" is not enforced hard enough.

## 10. Review by Engineering Quality

### 10.1 Logic correctness
- Strongest issue:
  - Authorization logic is not consistently fail-closed.
- Pattern:
  - The repository often has the right abstraction and then bypasses it in one critical path.

### 10.2 Architecture quality
- Good:
  - There are emerging policy/query/service layers.
- Weak:
  - Legacy and canonical data models coexist in active behavior.
  - Authorization is spread across router dependencies, ad hoc role checks, policy objects, and service methods.
  - Different transports implement different rules.

### 10.3 Code quality and maintainability
- Good:
  - Naming is usually readable.
  - The project is not raw spaghetti.
- Weak:
  - Duplicate logic exists in security-sensitive areas.
  - Broad fallbacks hide failures.
  - Inline response mapping repeatedly reimplements sensitive masking logic.
  - Role groups are hand-written repeatedly instead of centralized.

### 10.4 Testability
- Good:
  - There is visible investment in tests.
- Weak:
  - Too many tests validate route dependency shape or intended behavior while missing deeper business-logic bypasses.
  - The assistant, company-user binding, and UI/backend role parity gaps should already have dedicated regression tests and do not.

### 10.5 Scalability and performance
- Good:
  - Projection caching and FTS show awareness of scale.
- Weak:
  - Broken FTS visibility SQL silently falls back to ORM search.
  - Manual feedback filtering and pagination after loading all matching rows will age badly.

### 10.6 Defensive programming
- Weak:
  - Several critical areas fail open instead of closed.
  - "Missing tenant" is treated as permissive in the wrong places.
  - WS transport bypasses service-level validation used by REST.

### 10.7 Separation of concerns
- Weak:
  - Some route files still own too much business logic.
  - Support and feedback responses combine permission logic with data mapping too late.
  - Comment creation causing chat side effects is hidden coupling.

## 11. Priority Action Plan

### Immediate fixes
- Lock down assistant `document_ids` with real document authorization checks.
- Restrict assistant access to intended roles only, or split customer-safe assistant into a separate capability set.
- Eliminate non-system-admin internal users with `tenant_id=None`.
- Block tenant admins from reassigning arbitrary users across tenants or removing tenant binding from internal users.
- Fix attachment magic-byte validation in the actual upload entrypoint.

### Short-term improvements
- Align support, feedback, version compare, and search roles across frontend guards, router dependencies, policies, and service methods.
- Scope feedback stats by tenant and enforce email masking everywhere.
- Make portal/public attachment listing use the published snapshot resolver only.
- Apply visibility filtering to search autocomplete and facets.

### Medium-term refactors
- Centralize role capabilities and make all feature modules consume them.
- Remove deprecated `Document.platform` behavior from queries and responses.
- Route WS message creation through shared service validators.
- Replace mutable-user-based feedback scoping with stable tenant/document context.

### Long-term ideas
- Introduce explicit tenant lifecycle states with clear auth/session semantics.
- Build a security regression suite for multi-tenant invariants and feature-by-role behavior.
- Simplify product models where contributor-only comment visibility and support-role ambiguity are likely to confuse both users and developers.

## 12. Top 10 Highest-Value Fixes

1. Authorize assistant document context injection before any content enters the prompt.
2. Forbid unscoped non-system-admin internal users and repair existing records.
3. Restrict company user reassignment/removal flows so tenant admins cannot hijack or orphan users.
4. Fix attachment upload validation and add entrypoint-level tests for malicious file content.
5. Apply visibility rules to search autocomplete/facets and restrict management search to internal users.
6. Unify portal/public attachment metadata and download behavior behind one published-snapshot resolver.
7. Fix feedback PII masking and reduce feedback status updates to management roles only.
8. Align support permissions across UI, router dependencies, and service methods.
9. Fix the viewer/version-compare route mismatch.
10. Finish the platform-field migration and stop using deprecated `Document.platform` in active query logic.

## Risk Heatmap Summary by Area

| Area | Risk | Notes |
| --- | --- | --- |
| Assistant | Critical | Direct document-content exposure path |
| Tenant isolation | Critical | Unscoped users + company reassignment/orphaning |
| Auth/session | High | HTTP/WS divergence, invitation bootstrap inconsistency |
| Search | High | Metadata leakage + hidden FTS bug |
| Attachments/publication | High | Broken upload validation, snapshot inconsistencies |
| Feedback | High | PII leakage and role drift |
| Support | High | Cross-layer role incoherence |
| Chat/WS | High | Weak transport validation and access checks |
| Portal/public UX | Medium | Broken states, stale progress, inconsistent visibility |
| Maintainability | Medium | Duplicate logic, legacy/current field drift |

## Files/Modules That Appear Most Fragile

- `backend/app/api/management/companies.py`
- `backend/app/assistant/engine.py`
- `backend/app/application/policies/access_policies.py`
- `backend/app/application/queries/search_queries.py`
- `backend/app/domain/specifications/queries.py`
- `backend/app/application/queries/portal_queries.py`
- `backend/app/api/management/feedback.py`
- `backend/app/api/management/support.py`
- `backend/app/services/attachment_service/common.py`
- `backend/app/services/attachment_service/upload.py`
- `backend/app/services/chat_service.py`
- `backend/app/ws/chat_ws.py`
- `backend/app/ws/support_ws.py`
- `frontend/src/App.tsx`

## Files/Modules That Appear Strongest

- `backend/tests/test_wave_af_publication.py`
- `backend/tests/test_wave_ae_security.py`
- `backend/tests/test_route_auth_parity.py`
- `backend/tests/contracts/*`
- `backend/app/services/published_attachment_resolver.py`
- `backend/app/api/management/tenants.py`
- `backend/app/models/__init__.py` as a schema map, despite domain sprawl

## Top Architectural Weaknesses

- Authorization is not centralized enough to be trustworthy.
- Legacy and canonical data models coexist in active production logic.
- Transport layers implement different business rules.
- Sensitive response shaping is duplicated instead of centralized.
- Tenant lifecycle semantics are not explicit across the platform.

## Top Logic Risks

- "Missing tenant" is treated as permissive.
- Attachment visibility depends on endpoint, not one release model.
- Search metadata visibility is weaker than search-result visibility.
- Role meaning changes between UI, router, policy, and service layers.
- Mutable user state is used as a proxy for historical tenant ownership.

## Top Security/Permission Risks

- Assistant document exfiltration via explicit `document_ids`.
- Cross-tenant user reassignment through company admin flows.
- Orphaned internal users bypassing tenant checks.
- Customer email exposure in feedback management responses.
- Customer access to management search metadata.
- Deactivated-tenant real-time access persisting longer than intended.

## Short Conclusion

If I were improving this project next, I would start with the trust boundary failures, not the UI polish and not the refactors:

1. Fix assistant authorization.
2. Fix tenant/user binding and eliminate unscoped internal users.
3. Fix attachment validation and publication snapshot consistency.
4. Align role enforcement across frontend, backend routes, and services.

Until those are fixed, the rest of the system is building on unstable ground.
