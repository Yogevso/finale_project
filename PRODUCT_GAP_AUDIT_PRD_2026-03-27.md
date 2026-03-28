# PRODUCT GAP AUDIT / PRD - 2026-03-27

> Source: user-reported product gaps and UX failures collected on 2026-03-27
> Status: Implemented except deferred CAT-03-04 WhatsApp updates
> Purpose: turn the raw issue list into a categorized execution backlog with a recommended delivery order

## 1. How To Use This File

This is the working document for the next product-hardening phase.

It does three things:

1. groups the issues by category instead of by discovery order
2. turns each problem into a concrete backlog item with acceptance criteria
3. defines the recommended fix order so the team can implement them one by one

Important note:

- this file records the requested outcomes, not a full source-level verification of every item yet
- some items are implementation tasks
- some items are product-definition tasks that need explicit behavior rules before coding starts
- some items depend on external decisions such as email routing, WhatsApp provider choice, and conversion UX

## 2. Delivery Principles

- Fix platform trust and core workflows before visual polish.
- Prefer end-to-end flows over isolated UI tweaks.
- Every item must end with clear acceptance criteria and regression coverage.
- Customer-facing visibility and internal-admin workflows are both priority surfaces.
- Where behavior is undefined today, define the rule before implementing the UI.

## 3. Category Summary

| Category | Area | Priority | Item Count |
|----------|------|----------|------------|
| CAT-01 | UI/UX and layout | P1 | 7 |
| CAT-02 | Chat, tickets, feedback, notifications | P0 | 8 |
| CAT-03 | User admin, invitations, delivery channels | P0 | 4 |
| CAT-04 | Document lifecycle, archive, retention | P0 | 5 |
| CAT-05 | Upload, conversion, file-size policy | P1 | 2 |
| CAT-06 | AI tools and response quality | P2 | 1 |
| CAT-07 | Onboarding and first-run guidance | P1 | 2 |
| CAT-08 | Portal data sync, company/viewer visibility | P0 | 3 |

## 4. Recommended Execution Order

| Order | ID | Priority | Category | Reason |
|-------|----|----------|----------|--------|
| 1 | CAT-02 | P0 | Chat, tickets, feedback, notifications | communication workflows are core product reliability blockers |
| 2 | CAT-08 | P0 | Portal data sync, company/viewer visibility | customer and viewer content accuracy is a trust boundary |
| 3 | CAT-03 | P0 | User admin, invitations, delivery channels | admin control plane is incomplete today |
| 4 | CAT-04 | P0 | Document lifecycle, archive, retention | delete/archive behavior must be defined before more lifecycle work lands |
| 5 | CAT-01 | P1 | UI/UX and layout | polish should follow the workflow fixes so the UI reflects stable behavior |
| 6 | CAT-05 | P1 | Upload, conversion, file-size policy | important capability expansion, but not before core workflow stability |
| 7 | CAT-07 | P1 | Onboarding and first-run guidance | should be built on top of the corrected workflows |
| 8 | CAT-06 | P2 | AI tools and response quality | best done after the product data model and UX are less volatile |

## 5. Detailed Backlog

## CAT-01 - UI/UX and Layout

Current execution status on 2026-03-28:

- status: completed
- implemented slices:
  - sticky documents toolbar now respects header height, background layering, and z-index rules
  - document titles and descriptions now wrap or fall back cleanly across list/detail surfaces
  - documents filters now include suggestions, active-filter chips, clear actions, and date guardrails
  - the Manage companies action now deep-links to the correct document detail management state
  - documents page copy, empty states, and quick-start affordances were upgraded for clarity
  - shared input rules now cover create/upload/filter/saved-view fields plus chat, support, feedback, and visibility-reason text
  - CAT-01 edge-case matrix is documented in `CAT-01_EDGE_CASE_MATRIX_2026-03-28.md`
- verification evidence:
  - focused frontend tests cover sticky toolbar behavior, document display fallbacks, filter interactions, create/upload normalization, chat input limits, and visibility-reason limits
  - frontend `tsc`, targeted Vitest runs, and live Docker/frontend smoke checks passed during the CAT-01 slices

### CAT-01-01 - Title sizing and overflow handling
- Priority: P1
- Problem: long titles are truncated or visually oversized and the full title is not reliably visible.
- Outcome: titles remain readable for short, medium, and long values without breaking layout.
- Acceptance criteria:
  - titles support at least single-line and multi-line display modes where appropriate
  - no overlap with actions, badges, or side panels
  - edge cases are covered for empty, one-word, very long, mixed-language, and no-space titles

### CAT-01-02 - Description sizing and overflow handling
- Priority: P1
- Problem: descriptions do not scale well for short and long content.
- Outcome: descriptions are readable, space-efficient, and visually consistent.
- Acceptance criteria:
  - long descriptions wrap cleanly without clipping
  - empty descriptions render gracefully
  - dense descriptions do not push critical actions below the fold unexpectedly

### CAT-01-03 - General UI/UX upgrade
- Priority: P1
- Problem: elements need better placement, hierarchy, and clearer explanation text.
- Outcome: pages feel intentional, readable, and easier to understand on first use.
- Acceptance criteria:
  - primary actions are visually obvious
  - explanatory copy exists where user intent is unclear
  - spacing, headers, empty states, and action grouping are consistent across key screens

### CAT-01-04 - Filters usability and suggestions
- Priority: P1
- Problem: filters need better usability, suggestions, and clearer behavior.
- Outcome: filters are fast to scan, easy to reset, and help users discover valid options.
- Acceptance criteria:
  - filter options explain themselves clearly
  - suggestions/autocomplete are available where value lists are large
  - active filters are visible and removable without confusion

### CAT-01-05 - Documents-page sticky search/filter bar layering
- Priority: P1
- Problem: when scrolling, the search/filter bar renders above other elements incorrectly.
- Outcome: the sticky toolbar behaves correctly with consistent background and z-index.
- Acceptance criteria:
  - sticky bar keeps proper background fill
  - sticky bar does not visually collide with cards, modals, dropdowns, or table content
  - behavior is stable on desktop and mobile widths

### CAT-01-06 - Manage Company navigation target
- Priority: P1
- Problem: "Manage company" routes to the document page instead of company management.
- Outcome: the navigation target lands on the correct management screen.
- Acceptance criteria:
  - the entry point routes directly to company management
  - breadcrumbs, page title, and selected nav item match the destination

### CAT-01-07 - Edge-case review across input-heavy surfaces
- Priority: P1
- Problem: long, empty, malformed, and unusual inputs are not consistently handled.
- Outcome: the UI remains stable across valid and invalid edge-case inputs.
- Acceptance criteria:
  - edge-case matrix exists for titles, descriptions, names, categories, filters, and chat/ticket text
  - validation and truncation rules are explicit and consistent

## CAT-02 - Chat, Tickets, Feedback, and Notifications

Current execution status on 2026-03-28:

- status: completed on 2026-03-28
- implemented slice:
  - customer support create/close flows and ticket reply visibility are available through the portal support experience
  - customers can now access and reply to approved customer/internal chat threads through dedicated portal chat APIs and UI
  - internal roles can initiate customer-facing chats through the chat target-picker flow
  - feedback now becomes a ticket-backed conversation with customer/internal deep links into the live thread
  - support, feedback, and direct-chat surfaces now cross-link and explain their relationship more clearly
  - notification recipient logic, unread counters, and fallback recipient paths were audited and corrected across support, feedback, reviews, and communication-thread follow-ups
- verification evidence:
  - backend: targeted chat, support, feedback-ticket, review-notification, and notifications API tests passed during the CAT-02 slices
  - frontend: targeted portal chat, portal support, support page, and new-chat modal tests passed
  - Docker rebuilds and live smoke checks were run during the communication fixes, including verified support notifications, review notifications, chat API access, and collab/admin health

### CAT-02-01 - Ticket create and close flows
- Priority: P0
- Problem: ticket creation and closing need clearer, complete functionality.
- Outcome: internal users and customers can create and close tickets through defined workflows.
- Acceptance criteria:
  - create-ticket flow works for allowed roles
  - close-ticket flow has clear permission rules and status transitions
  - state changes are visible to all relevant participants

### CAT-02-02 - Customers can see responses to their tickets
- Priority: P0
- Problem: customers do not reliably see replies or updates on their tickets.
- Outcome: customer ticket detail exposes the full allowed response history.
- Acceptance criteria:
  - customer sees new staff responses without hidden internal-only content leaking
  - unread and read-state behavior is clear
  - portal ticket thread updates without manual confusion

### CAT-02-03 - Feedback should become a full conversation thread
- Priority: P0
- Problem: customer feedback stays a two-step flow instead of opening a real thread like editor conversations.
- Outcome: feedback can transition into an ongoing threaded conversation.
- Clarified product decision:
  - feedback should open into a customer-visible conversation flow rather than staying a one-off admin response model
  - implementation direction: feedback should become a ticket-backed conversation with chat-style UX, not a generic direct chat
- Acceptance criteria:
  - feedback can spawn or map to a conversation thread
  - internal users and customers can continue the discussion in one place
  - context from the original feedback is preserved

### CAT-02-04 - Notify internal users when internal customers leave feedback
- Priority: P0
- Problem: feedback does not notify or update the internal user side when internal customers submit feedback.
- Outcome: relevant internal users are notified immediately and can act on the feedback.
- Acceptance criteria:
  - new feedback triggers the correct notification recipients
  - the feedback view updates on the internal side without stale state

### CAT-02-05 - Internal users can initiate chats with customers
- Priority: P0
- Problem: internal users cannot start customer-facing chat threads.
- Outcome: internal users can open an allowed customer conversation from a defined entry point.
- Clarified product decision:
  - all internal roles are allowed to initiate these customer-facing chats
- Acceptance criteria:
  - role and tenant rules are enforced
  - the thread is visible to the target customer
  - audit trail or metadata exists for who initiated the thread

### CAT-02-06 - Customers can access customer/internal chat threads
- Priority: P0
- Problem: customers currently cannot see or access these chat threads.
- Outcome: customer access exists for approved cross-role conversation threads.
- Clarified product decision:
  - customers should both see and reply to any thread that explicitly includes them
- Acceptance criteria:
  - customer portal exposes the thread list and thread detail
  - unauthorized internal-only chats remain hidden
  - unread state, replies, and permissions behave correctly

### CAT-02-07 - Ticket and feedback responses should feel like one communication system
- Priority: P0
- Problem: support, feedback, and chat are separate experiences with inconsistent behavior.
- Outcome: communication workflows share clear mental models and transitions.
- Acceptance criteria:
  - users can tell whether they are in feedback, support, or chat
  - related threads can link or convert between modes when business rules allow

### CAT-02-08 - Notification reliability review across communication surfaces
- Priority: P0
- Problem: communication events need a full audit for recipient logic, unread counts, and UI updates.
- Outcome: notifications are reliable across support, feedback, reviews, and customer/internal chat.
- Acceptance criteria:
  - notification producers are cataloged and tested
  - each major communication event has a verified recipient rule
  - notification UI updates without stale counters

## CAT-03 - User Admin, Invitations, and Delivery Channels

Current execution status on 2026-03-28:

- status: completed for active scope on 2026-03-28; CAT-03-04 remains deferred by product decision
- implemented slice:
  - the user-admin flow now supports deactivation as the default delete path and SYSADMIN-only permanent deletion for inactive users, with dependent data handled safely
  - SYSADMIN can now view and update the active SMTP sender configuration in-app, including host, port, security, username, password, from-name, and from-email
  - pending invitations now expose email delivery status, sender identity, delivery errors, and a safe preview of the outbound invitation email
  - the admin/system setup surfaces now show whether email settings are coming from environment or database-backed overrides
- verification evidence:
  - backend: focused tests for system email settings, invitations API behavior, and user admin recovery/deletion passed during the CAT-03 slices
  - frontend: focused tests for system setup, users page invitation visibility, and delete/deactivate actions passed
  - `tsc`, targeted builds, and Docker rebuilds were completed during the SMTP and user-lifecycle changes

### CAT-03-01 - Create and delete users
- Priority: P0
- Problem: user administration is incomplete for creation and deletion.
- Outcome: admins can create and delete users through a defined lifecycle.
- Clarified product decision:
  - user deletion should support both soft delete first and a later hard-delete option
- Acceptance criteria:
  - create-user flow supports required role/tenant rules
  - delete-user flow defines hard delete vs deactivation behavior
  - sessions, invitations, and dependent data are handled safely

### CAT-03-02 - Invitation email visibility for SYSADMIN
- Priority: P0
- Problem: the invitation email flow is not accessible enough to SYSADMIN.
- Outcome: SYSADMIN can review, resend, or inspect invitation state and delivery results.
- Clarified product decision:
  - SYSADMIN should be able to see the invitation email content
  - SYSADMIN should be able to see which sender email/account is being used
  - SYSADMIN should be able to switch the sending account to another configured email
- Acceptance criteria:
  - invitation state is visible from the admin control plane
  - SYSADMIN can resend or recover from failed delivery
  - the email content and target state are auditable

### CAT-03-03 - Review email delivery system
- Priority: P0
- Problem: the delivery system needs a broader review for reliability and administration.
- Outcome: outbound email has clear failure visibility, resend behavior, and admin controls.
- Clarified product decision:
  - sender identity should be manageable by SYSADMIN from the product, not only from environment configuration
  - SYSADMIN should be able to enter and store full SMTP credentials for a new mailbox inside the app
- Acceptance criteria:
  - delivery failures are visible to admins
  - retry/resend behavior is defined
  - templates and routing for invitation/support/review emails are documented

### CAT-03-04 - WhatsApp updates option
- Priority: P1
- Problem: users may need an alternate update channel beyond email.
- Outcome: the product supports or explicitly rejects WhatsApp updates based on a defined policy.
- Current decision:
  - deferred for a future phase
- Acceptance criteria:
  - provider and compliance decision is documented
  - opt-in, opt-out, and message types are defined if enabled
  - no implementation begins before the channel policy is approved

## CAT-04 - Document Lifecycle, Archive, and Retention

### CAT-04-01 - Define archive and restore behavior
- Priority: P0
- Status: implemented on 2026-03-28
- Problem: archiving and restoring need explicit product rules and UX.
- Outcome: documents can move cleanly between active and archived states.
- Acceptance criteria:
  - archive and restore rules are defined by role and status
  - archive visibility in lists, filters, and analytics is clear
  - restore returns the document to a defined lifecycle state

### CAT-04-02 - Deleted documents get a 30-day grace period
- Priority: P0
- Status: implemented on 2026-03-28
- Problem: delete behavior needs soft-delete retention before permanent removal.
- Outcome: deleted documents remain recoverable for one month.
- Clarified product decision:
  - deleted documents should disappear immediately from normal users
  - recovery during the grace period should be limited to internal admins
- Acceptance criteria:
  - delete action becomes soft delete
  - recovery window is exactly 30 days unless policy overrides it later
  - permanent purge happens only after the grace period

### CAT-04-03 - Automatic archive after X time
- Priority: P0
- Status: implemented on 2026-03-28
- Problem: aging content should move to archive automatically based on admin policy.
- Outcome: SYSADMIN can configure time-based archive automation.
- Clarified product decision:
  - the archive timer starts from `last_published`
  - SYSADMIN chooses the duration, for example one month, one year, or longer
- Acceptance criteria:
  - SYSADMIN can configure the threshold
  - archive automation is auditable and reversible
  - exclusions and default behavior are defined

### CAT-04-04 - SYSADMIN-controlled lifecycle settings
- Priority: P0
- Status: implemented on 2026-03-28
- Problem: lifecycle automation needs a control surface.
- Outcome: retention and auto-archive settings are centrally managed.
- Clarified product decision:
  - this settings surface should include configurable archive durations based on `last_published`
- Acceptance criteria:
  - settings are visible and editable by SYSADMIN only
  - changes affect future jobs predictably

### CAT-04-05 - Retention jobs and recovery UX
- Priority: P1
- Status: implemented on 2026-03-28
- Problem: archive and soft-delete rules require job execution and user-facing recovery paths.
- Outcome: lifecycle automation and restore flows are operationally complete.
- Acceptance criteria:
  - background job behavior is defined
  - recover and purge actions have clear UX and audit logs

## CAT-05 - Upload, Conversion, and File-Size Policy

Current execution status on 2026-03-28:

- status: completed on 2026-03-28
- implemented slice:
  - shared upload boundaries now allow files up to `50 MB` across backend config, document uploads, document attachments, support attachments, assistant uploads, chat file uploads, and the main frontend validators/copy
  - `.env.example`, deployment docs, user guide, README, and checked-in OpenAPI contract descriptions now reflect the `50 MB` boundary
  - PDF uploads now present a visible conversion target choice in the frontend, preserve the original PDF as an attachment, and create a generated working `DOCX` or `PPTX` attachment while seeding editable document content from the original PDF
  - backend runtime dependencies and Docker images now include `python-pptx` and `XlsxWriter`, and the OpenAPI snapshot/contracts now include the new `pdf_conversion_target` multipart field
- verification evidence:
  - backend: `pytest tests/test_attachments.py tests/test_wave_ag_infrastructure.py -q` passed with `70 passed`
  - backend: `pytest tests/test_upload_lifecycle_defaults.py tests/test_process_managers.py -q` passed with `21 passed`
  - frontend: `tsc --noEmit` passed and focused Vitest for the upload use-cases, upload hook, and upload modal passed with `34 passed`
  - Docker rebuild for `backend` and `frontend` succeeded; `http://127.0.0.1:8000/health` returned healthy, `http://127.0.0.1:3000/documents` returned `200`, and the running backend container confirmed `python-pptx 1.0.2` plus `XlsxWriter 3.2.9`

### CAT-05-01 - Raise max upload size to 50 MB
- Priority: P1
- Status: implemented on 2026-03-28
- Problem: current upload limits are too restrictive.
- Outcome: the system accepts files up to 50 MB where policy allows.
- Acceptance criteria:
  - backend, frontend, proxy, and storage limits all align to 50 MB
  - error messaging clearly explains the limit
  - large-file behavior is tested

### CAT-05-02 - PDF upload conversion target selection
- Priority: P1
- Status: implemented on 2026-03-28
- Problem: PDF uploads need a user choice of conversion target before the normal flow continues.
- Outcome: users can choose Word or PowerPoint as the conversion target for PDFs.
- Clarified product decision:
  - the frontend should allow PDF upload
  - the original PDF must be preserved alongside the converted working file
- Acceptance criteria:
  - the upload UX asks for a target format when the source file is PDF
  - converted output enters the normal document workflow afterward
  - conversion limits, failure states, and preview messaging are defined

## CAT-06 - AI Tools and Response Quality

Current execution status on 2026-03-28:

- status: completed on 2026-03-28
- implemented slice:
  - the assistant prompt layer now has an explicit quality contract for grounded, answer-first, source-aware responses
  - uploaded assistant files now flow from the UI into `file_ids`, so backend file-context injection is no longer dead
  - assistant header and welcome UX now explain how to ground answers with attached files and `@`-mentioned documents, and surface assistant health status
  - confirmation-only tool requests now return a deterministic confirmation response instead of a vague summary loop
  - all-tool-failure runs now return a deterministic failure response that lists the tool errors instead of pretending the task completed
  - parallel tool execution now converts raw execution exceptions into explicit failed tool results
  - response quality criteria and weak-output examples are documented in `docs/AI_ASSISTANT_RESPONSE_QUALITY_2026-03-28.md`
- verification evidence:
  - backend: `python -m pytest tests/test_assistant_prompts.py tests/test_assistant_engine.py -q` passed with `58 passed`
  - frontend: `node .\\node_modules\\typescript\\bin\\tsc --noEmit --pretty false` passed
  - frontend: focused Vitest for assistant API/input/message rendering passed with `5 passed`
  - docker rebuild for `backend` and `frontend` completed successfully
  - live smoke: `/health` returned healthy and the frontend returned `200` for `/` and `/assistant`

### CAT-06-01 - Improve AI tools and response quality
- Priority: P2
- Problem: AI tools and generated responses need better usefulness and quality.
- Outcome: AI answers are more accurate, actionable, and context-aware.
- Acceptance criteria:
  - major AI tool surfaces are audited for prompt quality, grounding, and fallback behavior
  - response quality criteria exist for correctness, tone, and task completion
  - weak outputs are captured with examples and regression checks

## CAT-07 - Onboarding and First-Run Guidance

Current execution status on 2026-03-28:

- status: completed on 2026-03-28
- implemented slice:
  - onboarding state is now persisted per user in the backend instead of localStorage-only UI state
  - authenticated users now have a dedicated `/users/me/onboarding` read/update contract for guide visibility and checklist progress
  - internal and customer dashboards now open a role-aware first-run welcome guide and show a persistent role-based onboarding checklist
  - onboarding content is role-specific for customer, viewer, editor, manager, admin, and system-admin workflows
  - profile settings now include onboarding replay/reset controls alongside the existing product-tour replay controls
  - the documents workspace now recognizes `?action=upload` so onboarding links can deep-link directly into the upload flow
- verification evidence:
  - backend: `python -m pytest tests/test_auth.py -q -k onboarding` passed with `3 passed`
  - frontend: `npx.cmd tsc --noEmit --pretty false` passed
  - frontend: focused Vitest for the onboarding hook, checklist, and guide dialog passed with `6 passed`
  - OpenAPI snapshot and generated frontend contracts were refreshed after adding the onboarding endpoints

### CAT-07-01 - Initial guide for first-time users
- Priority: P1
- Status: implemented on 2026-03-28
- Problem: new users do not get a clear first-use guide.
- Outcome: first-time users receive a lightweight guided introduction.
- Acceptance criteria:
  - role-aware first-run guide exists
  - guide explains the main workflows and where to start
  - guide can be revisited later from help/settings

### CAT-07-02 - Mandatory onboarding checklist
- Priority: P1
- Status: implemented on 2026-03-28
- Problem: onboarding is not complete or enforced.
- Outcome: every user must go through a structured checklist before normal usage.
- Clarified product decision:
  - users should be strongly guided through onboarding on first login, not hard-blocked
- Acceptance criteria:
  - checklist progress is tracked per user
  - required steps differ by role when needed
  - first-login guidance is prominent enough that users are pushed through it without fully blocking the app

## CAT-08 - Portal Data Sync, Company Visibility, and Viewer Behavior

Current execution status on 2026-03-28:

- status: completed on 2026-03-28
- implemented slice:
  - customer, public, and viewer document surfaces now use audience-sensitive freshness rules so audience/category/topic changes refetch immediately instead of sitting behind long-lived SPA/browser caches
  - public, viewer, and portal detail/list reads now share the same published-version contract for externally visible documents
  - category/topic propagation and company-scoped audience visibility were traced through the relevant internal, portal, public, and viewer surfaces and aligned to the same effective rules
  - public-to-company visibility transitions are covered by targeted parity regressions across portal, public, and viewer endpoints
- verification evidence:
  - frontend: `tsc`, focused public-document tests, and `vite build` passed after the freshness changes
  - backend: `pytest tests/test_portal_api.py tests/test_public_api.py tests/test_viewer_api.py tests/test_viewer_portal.py -q` passed with `93 passed`

### CAT-08-01 - Customer categories/topics do not update
- Priority: P0
- Problem: customer-facing categories/topics are stale or not refreshed correctly.
- Outcome: category/topic data updates correctly in the customer experience.
- Acceptance criteria:
  - category/topic changes propagate to the customer side
  - stale-cache conditions are identified and fixed

### CAT-08-02 - Company-scoped platform/document visibility does not update
- Priority: P0
- Problem: after changing status to company and selecting the customer company, platforms and documents still do not update correctly.
- Outcome: company audience changes are reflected correctly in internal, customer, and viewer views.
- Acceptance criteria:
  - company-scoped content visibility updates correctly after audience changes
  - customer portal and viewer portal show the same allowed data model
  - propagation timing is defined and verified

### CAT-08-03 - Viewer portal parity review
- Priority: P0
- Problem: the viewer portal shows the same stale visibility issue.
- Outcome: viewer behavior matches the intended audience rules.
- Acceptance criteria:
  - viewer portal is included in the same audience-sync fix plan
  - parity tests exist for internal, customer, and viewer access results

## 6. Execution Order

Work this backlog in dependency order, not in raw discovery order.

### Phase 1 - Communication and customer-visible conversations

Start here first.

Why:

- these are the highest-trust failures in the product
- they affect both internal and external users immediately
- they define the right conversation model for later feedback/support/onboarding work

Recommended implementation sequence:

1. CAT-02-02 - Customers can see responses to their tickets
2. CAT-02-04 - Feedback notifies and updates internal users
3. CAT-02-05 - Internal users can initiate chats with customers
4. CAT-02-06 - Customers can see and reply to customer/internal chat threads
5. CAT-02-01 - Ticket create and close flows
6. CAT-02-03 - Feedback becomes a ticket-backed conversation with chat-style UX
7. CAT-02-07 - Communication surfaces feel like one system
8. CAT-02-08 - Full notification reliability review across communication surfaces

### Phase 2 - Portal and audience correctness

Run this immediately after the first communication slice.

Why:

- customer and viewer content visibility is a trust boundary
- stale audience/category/platform data will make every portal workflow feel broken even after chat fixes

Recommended implementation sequence:

1. CAT-08-01 - Customer categories/topics update correctly
2. CAT-08-02 - Company-scoped platform/document visibility updates correctly
3. CAT-08-03 - Viewer portal parity review and fixes

### Phase 3 - SYSADMIN and admin control plane

Why:

- user lifecycle and email delivery control are foundational admin capabilities
- retention and archive automation should not be implemented before the admin control plane exists

Recommended implementation sequence:

1. CAT-03-01 - Create users, soft delete users, then hard delete option
2. CAT-03-02 - Invitation email visibility and control for SYSADMIN
3. CAT-03-03 - Delivery-system review plus SYSADMIN-managed SMTP sender accounts
4. CAT-03-04 - WhatsApp is explicitly deferred for a future phase

### Phase 4 - Document lifecycle and retention

Why:

- delete/archive/restore behavior must be defined before adding more automation
- retention and recovery change product semantics and require admin controls from Phase 3

Recommended implementation sequence:

1. CAT-04-01 - Archive and restore behavior
2. CAT-04-02 - 30-day grace-period soft delete with admin-only recovery
3. CAT-04-03 - Auto-archive based on `last_published`
4. CAT-04-04 - SYSADMIN-controlled lifecycle settings
5. CAT-04-05 - Retention jobs and recovery UX

### Phase 5 - UI/UX and layout

Do this after the core workflow contracts are stable.

Recommended implementation sequence:

1. CAT-01-05 - Documents sticky search/filter bar layering
2. CAT-01-01 - Title sizing and overflow handling
3. CAT-01-02 - Description sizing and overflow handling
4. CAT-01-04 - Filters usability and suggestions
5. CAT-01-06 - Manage Company navigation target
6. CAT-01-03 - General UI/UX upgrade
7. CAT-01-07 - Edge-case review across input-heavy surfaces

### Phase 6 - Upload and conversion expansion

Recommended implementation sequence:

1. CAT-05-01 - Raise max upload size to 50 MB across frontend, backend, and infra
2. CAT-05-02 - PDF upload with conversion-target choice while preserving the original PDF

### Phase 7 - Onboarding and first-run guidance

Recommended implementation sequence:

1. CAT-07-01 - Initial first-time-user guide
2. CAT-07-02 - Strongly guided onboarding checklist on first login

### Phase 8 - AI quality

Completed on 2026-03-28 after the core workflow, lifecycle, upload, and onboarding slices stabilized.

## 7. Exit Criteria For This Phase

This phase is complete only when:

- the categorized backlog has explicit status transitions from open to closed
- each closed item has linked implementation evidence
- each workflow change includes regression coverage
- the customer portal, viewer portal, and internal portal are validated together where behavior overlaps
