# App Feature Map

This document is a quick orientation guide for new developers, QA, reviewers, product teammates, and stakeholders who want to understand what exists in the application without reading the code first.

Use this while walking through the product. It is meant to answer three simple questions:

- What areas does the app have?
- Who is each area for?
- Where do I go in the UI to review it?

For architecture and deployment details, see the root `README.md`.

## 1. System Overview

The product is split into five main surfaces:

1. Public documentation experience
   Anonymous browsing for published documents, search, platforms, help content, and changelog.
2. Internal staff workspace
   The main app for document operations, reviews, messaging, analytics, support, and administration.
3. Customer portal
   A logged-in experience for customers to view company documents, continue reading, submit feedback, and open support tickets.
4. Admin and platform controls
   Company management, system setup, and system-admin operations.
5. Shared account and access flows
   Login, password reset, invitation acceptance, profile settings, sessions, and security history.

## 2. Role Cheat Sheet

| Role | Main Purpose | Typical Home Route | Main Areas |
| --- | --- | --- | --- |
| Anonymous visitor | Browse public docs without logging in | `/docs` | Public docs, search, help, changelog |
| Customer | External user with company-specific access | `/portal/dashboard` | Customer dashboard, documents, feedback, support, assistant |
| Viewer | Internal read-only staff user | `/dashboard` | Dashboard, documents, chat, assistant, notifications, profile |
| Editor | Internal content author/editor | `/dashboard` | Everything a viewer has, plus review access and document creation/editing |
| Manager | Workflow and operations owner | `/dashboard` | Reviews, support, feedback, analytics, users |
| Admin | Tenant/company administrator | `/dashboard` | Companies, users, management screens |
| System Admin | Full platform operator | `/dashboard` | System setup, admin operations, platform-wide controls |

## 3. Quick Access Matrix

Use this when you want the shortest possible answer for "who should see what?"

| Area | Main Routes | Who Should See It |
| --- | --- | --- |
| Public portal | `/docs`, `/search`, `/platforms`, `/help`, `/changelog`, `/doc/:id` | Everyone |
| Login and account entry | `/login`, `/reset-password`, `/accept-invitation` | Unauthenticated users and invitees |
| Internal core workspace | `/dashboard`, `/documents`, `/chat`, `/assistant`, `/notifications`, `/profile` | All internal staff |
| Review workflow | `/reviews` | Editor and above |
| Operational management | `/support`, `/support/canned-responses`, `/analytics`, `/users`, `/admin/feedback` | Manager and above |
| Company administration | `/admin/companies` | Admin and system admin |
| Platform administration | `/admin/system-setup`, `/admin/operations` | System admin only |
| Customer portal | `/portal/*` | Customer only |
| Legacy published viewer | `/viewer/documents/:id` | Legacy internal/public viewing path |

## 4. Recommended Review Order

If someone is reviewing the app end to end, this is the cleanest order:

1. Public experience
   Start with `/docs`, `/search`, `/platforms`, `/help`, and `/changelog`.
2. Internal content workflow
   Go through `/dashboard`, `/documents`, document detail, compare, and `/reviews`.
3. Internal operations workflow
   Review `/notifications`, `/chat`, `/assistant`, `/support`, `/admin/feedback`, `/analytics`, and `/users`.
4. Customer journey
   Review `/portal/dashboard`, `/portal/documents`, `/portal/feedback`, `/portal/support`, and `/portal/assistant`.
5. Admin journey
   Review `/admin/companies`, `/admin/system-setup`, and `/admin/operations`.
6. Account and security
   Check `/profile`, `/profile/sessions`, `/profile/security-events`, `/login`, `/reset-password`, and `/accept-invitation`.

## 5. Feature Inventory

### A. Public Experience

#### 1. Documentation Library

- Main route: `/docs`
- Purpose: Public browsing of published documentation.
- What users do here:
  Search by keywords, browse document cards, filter results, and open document detail pages.
- Main reviewer focus:
  Listing quality, filters, empty states, pagination, card metadata, and route-to-detail behavior.

#### 2. Public Document Detail

- Main route: `/doc/:id`
- Purpose: Read a published public document.
- What users do here:
  Open a document, read the content, and interact with its public-facing presentation.
- Main reviewer focus:
  Document loading, not-found behavior, readability, attachments or related assets, and navigation back to listings.

#### 3. Public Search

- Main route: `/search`
- Purpose: Search the public documentation library.
- What users do here:
  Enter a query, review result cards, and move into matching documents.
- Main reviewer focus:
  Query behavior, URL state, no-results state, snippet quality, and filter behavior.

#### 4. Platforms

- Main routes: `/platforms`, `/platforms/:platformId`
- Purpose: Browse documentation grouped by platform or release area.
- What users do here:
  View platforms, select one, and inspect related documents or release history.
- Main reviewer focus:
  Platform grouping, navigation clarity, filtering, and consistency with the docs library.

#### 5. Help Center

- Main route: `/help`
- Purpose: Give public users a help-oriented landing area.
- What users do here:
  Discover support-related content and guidance.
- Main reviewer focus:
  Clarity, usefulness, content structure, and whether the page leads people to the right next step.

#### 6. Tools

- Main route: `/tools`
- Purpose: Public utilities and tool-related entry points.
- What users do here:
  Discover available tools or helper resources.
- Main reviewer focus:
  Whether the page is clear, current, and meaningfully connected to the rest of the public experience.

#### 7. Changelog

- Main route: `/changelog`
- Purpose: Public-facing change history.
- What users do here:
  Review recent updates and release notes.
- Main reviewer focus:
  Content rendering, chronological clarity, and empty/loading states.

#### 8. Accessibility Statement

- Main route: `/accessibility`
- Purpose: Public accessibility information.
- What users do here:
  Review the product's accessibility statement.
- Main reviewer focus:
  Clarity, completeness, and whether the page is easy to find.

### B. Authentication and Entry Flows

#### 1. Login

- Main route: `/login`
- Purpose: Primary sign-in page for authenticated users.
- Main reviewer focus:
  Valid login flow, error messaging, redirect behavior, and session persistence after reload.

#### 2. Reset Password

- Main route: `/reset-password`
- Purpose: Password recovery and reset flow.
- Main reviewer focus:
  Token handling, validation, expired-link behavior, and clear confirmation/error states.

#### 3. Accept Invitation

- Main route: `/accept-invitation`
- Purpose: Onboard invited users into the system.
- Main reviewer focus:
  Invite acceptance, form clarity, validation, and route behavior for valid vs invalid invites.

### C. Internal Staff Workspace

#### 1. Internal Dashboard

- Main route: `/dashboard`
- Purpose: Entry screen for internal users.
- What users do here:
  See high-level document stats, recent documents, onboarding steps, bookmarks, and activity.
- Main reviewer focus:
  Whether the dashboard is useful on day one, whether quick actions make sense, and whether stats match expectations.

#### 2. Documents List

- Main route: `/documents`
- Purpose: Central workspace for managing documents.
- What users do here:
  Browse documents, filter, save views, create new documents, upload files, bulk edit metadata, archive, restore, and manage visibility.
- Main reviewer focus:
  Filter behavior, bulk actions, create/upload discoverability, table quality, and permission differences between roles.

#### 3. Document Detail

- Main route: `/documents/:id`
- Purpose: Main document workspace for previewing and managing a single document.
- What users do here:
  Preview content, switch tabs, view details, edit metadata/content, manage assignments, see review history, inspect versions, and manage attachments.
- Main reviewer focus:
  Tab behavior, edit vs read states, review actions, attachment handling, company assignment flow, and role-based actions.

#### 4. Fullscreen Document View

- Main route: `/documents/:id/fullscreen`
- Purpose: Focused reading mode for document detail.
- What users do here:
  Read the document in a larger layout, print, and change reading width.
- Main reviewer focus:
  Reading experience, fullscreen transitions, print behavior, and navigation back to the standard document page.

#### 5. Version Compare

- Main route: `/documents/:id/compare`
- Purpose: Side-by-side review of document versions.
- What users do here:
  Compare versions before approval, publishing, or restore decisions.
- Main reviewer focus:
  Correct version selection, change visibility, and readability of diffs.

#### 6. Reviews

- Main route: `/reviews`
- Purpose: Review and approval workflow for document submissions.
- What users do here:
  Inspect review queues and perform approval-related actions.
- Main reviewer focus:
  Status clarity, review decision flow, and what different roles can actually do.

#### 7. Notifications

- Main route: `/notifications`
- Purpose: User-level update center.
- What users do here:
  Review updates, mark items read or unread, open linked items, and delete notifications.
- Main reviewer focus:
  Notification usefulness, read-state behavior, link correctness, and empty/loading states.

#### 8. Chat

- Main route: `/chat`
- Purpose: Internal private and group messaging.
- What users do here:
  Open conversations, send messages, and manage chat threads.
- Main reviewer focus:
  Conversation loading, message delivery, state syncing, and general usability.

#### 9. AI Assistant

- Main route: `/assistant`
- Purpose: Conversational assistant inside the internal app.
- What users do here:
  Start conversations, continue old threads, search chats, rename chats, delete chats, and export content.
- Main reviewer focus:
  Conversation flow, tool usefulness, permissions, message quality, and failure handling.

#### 10. Support Desk

- Main routes: `/support`, `/support/canned-responses`
- Purpose: Internal support operations.
- What users do here:
  Review support tickets, assign tickets, reply to customers, and use reusable response templates.
- Main reviewer focus:
  Ticket list clarity, assignment flow, message timeline, canned-response insertion, and role-based access.

#### 11. User Management

- Main route: `/users`
- Purpose: Manage internal users and invitations.
- What users do here:
  Create users, edit users, deactivate users, resend invites, cancel invites, and message people.
- Main reviewer focus:
  User lifecycle clarity, role handling, invitation state, and admin-only actions.

#### 12. Customer Feedback Management

- Main route: `/admin/feedback`
- Purpose: Review and respond to customer feedback.
- What users do here:
  Browse feedback items, inspect details, and manage responses or statuses.
- Main reviewer focus:
  Feedback triage flow, visibility of customer context, and response workflow.

#### 13. Analytics

- Main route: `/analytics`
- Purpose: Management-facing content and engagement insights.
- What users do here:
  Review dashboard metrics and activity trends.
- Main reviewer focus:
  Clarity of metrics, date filtering, usefulness for decision-making, and whether the data feels trustworthy.

### D. Customer Portal

#### 1. Customer Dashboard

- Main route: `/portal/dashboard`
- Purpose: Home page for customers after login.
- What users do here:
  See summary stats, continue reading, review recently viewed documents, and navigate quickly into the portal.
- Main reviewer focus:
  Whether the dashboard is useful to customers and whether "continue reading" feels reliable.

#### 2. Customer Documents

- Main route: `/portal/documents`
- Purpose: Browse all documents available to the customer.
- What users do here:
  Filter by category, topic, and platform, search available docs, and open document detail.
- Main reviewer focus:
  Relevance of results, entitlement boundaries, filter quality, and empty/loading states.

#### 3. Customer Document Detail

- Main route: `/portal/documents/:id`
- Purpose: Read a customer-accessible document in the portal.
- What users do here:
  Read the document, view assets, continue progress, and open the focused reading mode.
- Main reviewer focus:
  Access control, reading continuity, content availability, and document navigation.

#### 4. My Feedback

- Main route: `/portal/feedback`
- Purpose: Let customers track their own feedback submissions.
- What users do here:
  Review submitted feedback and see responses or status changes.
- Main reviewer focus:
  Submission history quality, status clarity, and whether the page closes the loop for the customer.

#### 5. Customer Support

- Main route: `/portal/support`
- Purpose: Customer-facing support ticket area.
- What users do here:
  Create tickets, view ticket history, and continue ticket conversations.
- Main reviewer focus:
  Ticket creation clarity, reply flow, status changes, and whether the page is understandable without training.

#### 6. Customer AI Assistant

- Main route: `/portal/assistant`
- Purpose: Assistant experience inside the customer portal.
- What users do here:
  Interact with the assistant in a portal context.
- Main reviewer focus:
  Whether the assistant feels appropriate for customers, whether responses stay within the expected scope, and whether portal context is handled well.

### E. Admin and Platform Controls

#### 1. Company Management

- Main routes: `/admin/companies`, `/admin/companies/:id`
- Purpose: Manage companies and company membership.
- What users do here:
  View companies, open a company detail screen, review users in a company, and inspect assigned documents.
- Main reviewer focus:
  Company lifecycle clarity, user assignment/removal flow, document assignment visibility, and admin-only restrictions.

#### 2. System Setup

- Main route: `/admin/system-setup`
- Purpose: Configure global settings and role/permission structures.
- What users do here:
  Review or update system settings, RBAC policy definitions, and audience alert rules.
- Main reviewer focus:
  Whether the page is understandable, whether settings are grouped logically, and whether changes feel safe and traceable.

#### 3. Admin Operations

- Main route: `/admin/operations`
- Purpose: System-admin control center for platform operations.
- What users do here:
  View system status, impersonation tools, action queue, tenant management, feature matrix, and maintenance windows.
- Main reviewer focus:
  Operational clarity, safety of powerful actions, and whether system-admin controls are separated cleanly from normal admin work.

## 6. Suggested Walkthroughs by Reviewer Type

### If the reviewer is mostly product or QA

Use this route order:

1. `/docs`
2. `/search`
3. `/doc/:id`
4. `/dashboard`
5. `/documents`
6. `/documents/:id`
7. `/reviews`
8. `/portal/dashboard`
9. `/portal/documents`
10. `/portal/support`

### If the reviewer is focused on internal operations

Use this route order:

1. `/dashboard`
2. `/documents`
3. `/documents/:id`
4. `/reviews`
5. `/support`
6. `/support/canned-responses`
7. `/admin/feedback`
8. `/analytics`
9. `/users`
10. `/admin/companies`

### If the reviewer is focused on admin/platform control

Use this route order:

1. `/admin/companies`
2. `/admin/system-setup`
3. `/admin/operations`
4. `/users`
5. `/profile/sessions`
6. `/profile/security-events`

### If the reviewer is focused on customer experience

Use this route order:

1. `/portal/dashboard`
2. `/portal/documents`
3. `/portal/documents/:id`
4. `/portal/feedback`
5. `/portal/support`
6. `/portal/assistant`

## 7. What to Pay Attention to During Review

Even for non-developers, these are the highest-value things to watch:

- Navigation clarity
  Can users tell where they are and where to go next?
- Role clarity
  Does the app clearly explain who can do what?
- Empty and loading states
  Does the product still make sense when there is little or no data?
- Error handling
  Are failures obvious, understandable, and recoverable?
- Workflow continuity
  Can users finish key tasks without getting lost?
- Trust signals
  Do status labels, counts, permissions, and document states feel believable and consistent?

## 8. Optional Code Pointers for Engineers

People reviewing only the app can ignore this section.

| Area | Main Frontend Location | Main Backend Location |
| --- | --- | --- |
| Public portal | `frontend/src/pages/public` | `backend/app/api/public` |
| Customer portal | `frontend/src/pages/portal` | `backend/app/api/portal` |
| Internal management app | `frontend/src/pages` | `backend/app/api/management` |
| Auth and session handling | `frontend/src/lib/auth.tsx`, `frontend/src/lib/api/authApi.ts` | `backend/app/api/management/auth.py`, `backend/app/services/auth_service.py` |
| Route and menu map | `frontend/src/App.tsx`, `frontend/src/config/routes.ts` | N/A |
| Support | `frontend/src/pages/SupportPage.tsx`, `frontend/src/pages/portal/CustomerSupportPage.tsx` | `backend/app/api/management/support.py`, `backend/app/services/support_service.py` |
| Feedback | `frontend/src/pages/admin/FeedbackPage.tsx`, `frontend/src/pages/portal/MyFeedbackPage.tsx` | `backend/app/api/management/feedback.py` |
| Documents and document detail | `frontend/src/pages/DocumentsPage.tsx`, `frontend/src/pages/DocumentDetailPage.tsx` | `backend/app/api/management/documents.py`, related application and service modules |
| Collaboration and chat | `frontend/src/pages/ChatPage.tsx`, `frontend/src/lib/useCollaboration.ts`, `frontend/src/hooks/useChatSocket.ts` | `backend/app/ws`, `collab-server/src` |
| Admin controls | `frontend/src/pages/admin` | Management and policy-related backend modules |

## 9. Short Summary

At a high level, the app has:

- A public documentation site
- An internal document operations workspace
- A customer portal
- Management and support tools
- Company and system administration
- Shared account, session, and security screens

If someone is new to the product, this file should be their starting point.
