# AI Assistant Tools — Permission & RBAC Deep Audit

> **Generated:** 2026-03-18  
> **Scope:** Every tool in `backend/app/assistant/tools/` vs. every normal API endpoint  
> **Verdict:** Multiple privilege-escalation and workflow-bypass gaps found

---

## Part 1: Complete Tool Inventory & Permission Checks

### Base Class Mechanics (`base.py`)

The `BaseTool` base class supports two gating mechanisms:
- **`required_permission`** — checked via `has_permission(user, perm)` against the `ROLE_PERMISSIONS` matrix
- **`required_role`** — checked via a role-hierarchy index comparison (higher index = more privileged)
- **`confirm_before_execute`** — advisory flag; the assistant should prompt the user before executing

The `ToolRegistry.execute_tool()` calls `tool.user_can_execute(user)` before every execution.

Role hierarchy (index 0-5):
```
CUSTOMER(0) < VIEWER(1) < EDITOR(2) < MANAGER(3) < ADMIN(4) < SYSTEM_ADMIN(5)
```

---

### Tool-by-Tool Breakdown

| # | Tool Name | File | Permission Check | Uses Service Layer? | Passes current_user for RBAC? | confirm_before_execute | Direct DB Write? |
|---|-----------|------|-------------------|---------------------|-------------------------------|----------------------|-----------------|
| 1 | `search_documents` | document_tools | `VIEW_INTERNAL_DOCS` | No — direct DB query | Tenant-scoped only | No | No (read) |
| 2 | `get_document` | document_tools | `VIEW_INTERNAL_DOCS` | No — direct DB query | Tenant-scoped only | No | No (read) |
| 3 | `create_document` | document_tools | `CREATE_DOCUMENT` | No — direct DB insert | Sets `created_by=user.id` | No | **Yes** |
| 4 | `edit_document` | document_tools | `EDIT_DOCUMENT` | No — direct DB update | Tenant-scoped only | No | **Yes** |
| 5 | `delete_document` | document_tools | `DELETE_DOCUMENT` | No — direct DB delete | Tenant-scoped only | **Yes** | **Yes** |
| 6 | `get_documents_by_status` | document_tools | role≥VIEWER | No — direct DB query | Tenant-scoped only | No | No (read) |
| 7 | `get_recent_documents` | document_tools | role≥VIEWER | No — direct DB query | Tenant-scoped only | No | No (read) |
| 8 | `list_users` | user_tools | `MANAGE_USERS` | No — direct DB query | Tenant-scoped only | No | No (read) |
| 9 | `get_user` | user_tools | `MANAGE_USERS` | No — direct DB query | Tenant-scoped check | No | No (read) |
| 10 | `create_user` | user_tools | `MANAGE_USERS` | No — direct DB insert | Role hierarchy enforced | No | **Yes** |
| 11 | `deactivate_user` | user_tools | `MANAGE_USERS` | No — direct DB update | Tenant-scoped, no self-deactivate | **Yes** | **Yes** |
| 12 | `change_user_role` | user_tools | `MANAGE_USERS` | No — direct DB update | Role hierarchy enforced | No | **Yes** |
| 13 | `submit_review` | review_tools | role≥EDITOR | No — direct DB update | Checks reviewer assignment | **Yes** | **Yes** |
| 14 | `list_pending_reviews` | review_tools | role≥EDITOR | No — direct DB query | Filters by `reviewed_by=user.id` | No | No (read) |
| 15 | `submit_feedback` | feedback_tools | `SUBMIT_FEEDBACK` | No — direct DB insert | Sets `user_id=user.id` | No | **Yes** |
| 16 | `get_my_feedback` | feedback_tools | `SUBMIT_FEEDBACK` | No — direct DB query | Filters by `user_id` | No | No (read) |
| 17 | `list_attachments` | attachment_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 18 | `get_attachment_info` | attachment_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 19 | `list_document_comments` | comment_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 20 | `add_comment` | comment_tools | role≥VIEWER | No — direct DB insert | Tenant + user_id | No | **Yes** |
| 21 | `resolve_comment` | comment_tools | role≥EDITOR | No — direct DB update | Tenant-scoped | No | **Yes** |
| 22 | `get_platform_analytics` | analytics_tools | `SYSTEM_SETTINGS` | No — direct DB query | **No tenant scope** | No | No (read) |
| 23 | `get_engagement_analytics` | analytics_tools | `SYSTEM_SETTINGS` | No — direct DB query | **No tenant scope** | No | No (read) |
| 24 | `get_content_analytics` | analytics_tools | `SYSTEM_SETTINGS` | No — direct DB query | **No tenant scope** | No | No (read) |
| 25 | `compare_versions` | version_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 26 | `get_document_history` | version_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 27 | `publish_document` | version_tools | role≥EDITOR | No — direct DB update | Tenant-scoped | **Yes** | **Yes** |
| 28 | `get_document_workflow` | version_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 29 | `get_my_profile` | info_tools | None | No — reads user object | Self only | No | No (read) |
| 30 | `get_my_permissions` | info_tools | None | No — calls `get_user_permissions` | Self only | No | No (read) |
| 31 | `get_help` | info_tools | None | No — reads registry | Self only | No | No (read) |
| 32 | `search_public_documents` | info_tools | None | No — direct DB query | Visibility-aware | No | No (read) |
| 33 | `get_document_content` | info_tools | None | No — direct DB query | Visibility-aware | No | No (read) |
| 34 | `get_site_settings` | settings_tools | `SYSTEM_SETTINGS` | No — direct DB query | No tenant scope | No | No (read) |
| 35 | `update_site_setting` | settings_tools | `SYSTEM_SETTINGS` | No — direct DB write | Sets `updated_by` | No | **Yes** |
| 36 | `create_announcement` | settings_tools | `SYSTEM_SETTINGS` | No — direct DB insert | Sets `created_by` | No | **Yes** |
| 37 | `list_announcements` | settings_tools | `SYSTEM_SETTINGS` | No — direct DB query | No | No | No (read) |
| 38 | `list_topics` | settings_tools | `VIEW_INTERNAL_DOCS` | No — direct DB query | No | No | No (read) |
| 39 | `create_topic` | settings_tools | `SYSTEM_SETTINGS` | No — direct DB insert | No | No | **Yes** |
| 40 | `list_tenants` | tenant_tools | role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 41 | `get_tenant` | tenant_tools | role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 42 | `update_tenant` | tenant_tools | role≥SYSTEM_ADMIN | No — direct DB update | No | **Yes** | **Yes** |
| 43 | `create_invitation` | invitation_tools | role≥ADMIN | No — direct DB insert | Sets `invited_by`, tenant_id | **Yes** | **Yes** |
| 44 | `list_invitations` | invitation_tools | role≥ADMIN | No — direct DB query | Tenant-scoped | No | No (read) |
| 45 | `get_my_notifications` | notification_tools | None | No — direct DB query | Filters by `user_id` | No | No (read) |
| 46 | `mark_notifications_read` | notification_tools | None | No — direct DB update | Filters by `user_id` | No | **Yes** |
| 47 | `semantic_search` | rag_tools | None | Uses VectorStore | Tenant-filtered post-query | No | No (read) |
| 48 | `summarize_document` | rag_tools | None | Ollama + direct DB | Tenant-scoped | No | No (read) |
| 49 | `ask_about_document` | rag_tools | None | Ollama + VectorStore + DB | Tenant-scoped | No | No (read) |
| 50 | `analyze_uploaded_file` | file_tools | None | Ollama + direct DB | Owns-file check | No | No (read) |
| 51 | `compare_files` | file_tools | None | Ollama + direct DB | Owns-file check | No | No (read) |
| 52 | `create_support_ticket` | support_tools | None | No — direct DB insert | Requires tenant_id | No | **Yes** |
| 53 | `list_my_tickets` | support_tools | None | No — direct DB query | Filters by `customer_id` | No | No (read) |
| 54 | `get_ticket_details` | support_tools | None | No — direct DB query | Owns-ticket check | No | No (read) |
| 55 | `bookmark_document` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB insert | user_id | No | **Yes** |
| 56 | `remove_bookmark` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB delete | user_id | No | **Yes** |
| 57 | `list_my_bookmarks` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB query | user_id | No | No (read) |
| 58 | `watch_document` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB insert | user_id | No | **Yes** |
| 59 | `unwatch_document` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB delete | user_id | No | **Yes** |
| 60 | `get_my_watched_documents` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB query | user_id | No | No (read) |
| 61 | `get_reading_progress` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB query | user_id | No | No (read) |
| 62 | `update_reading_progress` | engagement_tools | `VIEW_PUBLIC_DOCS` | No — direct DB write | user_id | No | **Yes** |
| 63 | `search_audit_logs` | audit_tools | `SYSTEM_SETTINGS` | No — direct DB query | **No tenant scope** | No | No (read) |
| 64 | `get_user_activity` | audit_tools | `SYSTEM_SETTINGS` | No — direct DB query | **No tenant scope** | No | No (read) |
| 65 | `get_active_collaborators` | collaboration_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 66 | `get_collaboration_history` | collaboration_tools | role≥VIEWER | No — direct DB query | Tenant-scoped | No | No (read) |
| 67 | `list_my_chats` | chat_tools | `ADD_COMMENTS` | No — direct DB query | user participation check | No | No (read) |
| 68 | `get_chat_messages` | chat_tools | `ADD_COMMENTS` | No — direct DB query | membership check | No | No (read) |
| 69 | `send_chat_message` | chat_tools | `ADD_COMMENTS` | No — direct DB insert | membership check | **Yes** | **Yes** |
| 70 | `search_chat_messages` | chat_tools | `ADD_COMMENTS` | No — direct DB query | membership check | No | No (read) |
| 71 | `get_chat_participants` | chat_tools | `ADD_COMMENTS` | No — direct DB query | membership check | No | No (read) |
| 72 | `get_unread_chats` | chat_tools | `ADD_COMMENTS` | No — direct DB query | user participation | No | No (read) |
| 73 | `mark_chat_read` | chat_tools | `ADD_COMMENTS` | No — direct DB update | membership check | No | **Yes** |
| 74 | `get_my_sessions` | security_tools | `VIEW_PUBLIC_DOCS` | No — direct DB query | user_id filter | No | No (read) |
| 75 | `revoke_session` | security_tools | `VIEW_PUBLIC_DOCS` | No — direct DB update | user_id + session ownership | **Yes** | **Yes** |
| 76 | `get_my_security_events` | security_tools | `VIEW_PUBLIC_DOCS` | No — direct DB query | user_id filter | No | No (read) |
| 77 | `get_security_events_admin` | security_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | **No tenant scope** | No | No (read) |
| 78 | `get_invitation_status` | security_tools | `MANAGE_USERS` | No — direct DB query | Tenant-scoped | No | No (read) |
| 79 | `cancel_invitation` | security_tools | `MANAGE_USERS` | No — direct DB update | **No tenant scope!** | **Yes** | **Yes** |
| 80 | `list_feature_flags` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 81 | `toggle_feature_flag` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB write | Sets `updated_by` | **Yes** | **Yes** |
| 82 | `list_maintenance_windows` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 83 | `create_maintenance_window` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB insert | Sets `created_by` | **Yes** | **Yes** |
| 84 | `get_tenant_quota` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 85 | `update_tenant_quota` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB write | Sets `updated_by` | **Yes** | **Yes** |
| 86 | `list_impersonation_sessions` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 87 | `list_admin_actions` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 88 | `review_admin_action` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB update | Self-review blocked | **Yes** | **Yes** |
| 89 | `get_platform_overview` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 90 | `get_tenant_summary` | admin_tools | `SYSTEM_SETTINGS` + role≥SYSTEM_ADMIN | No — direct DB query | No | No | No (read) |
| 91 | `list_scheduled_publishes` | version_tools_ext | `PUBLISH_DOCUMENT` | No — direct DB query | Tenant-scoped | No | No (read) |
| 92 | `get_version_details` | version_tools_ext | `VIEW_INTERNAL_DOCS` | No — direct DB query | No tenant scope | No | No (read) |
| 93 | `get_document_version_stats` | version_tools_ext | `VIEW_INTERNAL_DOCS` | No — direct DB query | No tenant scope | No | No (read) |
| 94 | `cancel_scheduled_publish` | version_tools_ext | `PUBLISH_DOCUMENT` | No — direct DB update | No tenant scope | **Yes** | **Yes** |
| 95 | `list_unpublished_versions` | version_tools_ext | `VIEW_INTERNAL_DOCS` | No — direct DB query | Tenant-scoped | No | No (read) |
| 96 | `search_attachments` | attachment_tools_ext | `DOWNLOAD_ATTACHMENTS` | No — direct DB query | Tenant-scoped | No | No (read) |
| 97 | `get_attachment_stats` | attachment_tools_ext | `DOWNLOAD_ATTACHMENTS` | No — direct DB query | Tenant-scoped | No | No (read) |
| 98 | `get_largest_attachments` | attachment_tools_ext | `DOWNLOAD_ATTACHMENTS` | No — direct DB query | Tenant-scoped | No | No (read) |

---

## Part 2: Role Hierarchy & Permission Matrix

### Roles (from `UserRole` enum)

| Role | Internal? | Level |
|------|-----------|-------|
| `system_admin` | Yes | 5 (highest) |
| `admin` | Yes | 4 |
| `manager` | Yes | 3 |
| `editor` | Yes | 2 |
| `viewer` | Yes | 1 |
| `customer` | No | 0 (lowest) |

### Permission Matrix

| Permission | system_admin | admin | manager | editor | viewer | customer |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| VIEW_PUBLIC_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VIEW_INTERNAL_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| VIEW_COMPANY_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (own co.) |
| CREATE_DOCUMENT | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| EDIT_DOCUMENT | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| DELETE_DOCUMENT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| SUBMIT_REVIEW | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| APPROVE_REVIEW | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| APPROVE_PEER_REVIEW | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| PUBLISH_DOCUMENT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ASSIGN_COMPANIES | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ADD_COMMENTS | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| SUBMIT_FEEDBACK | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DOWNLOAD_ATTACHMENTS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MANAGE_USERS | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| MANAGE_EDITORS | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| MANAGE_COMPANIES | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| SYSTEM_SETTINGS | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| MANAGE_ADMINS | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Normal API Dependencies

| Dependency | Required Roles |
|-----------|----------------|
| `require_internal_user` | Any internal role (not customer) |
| `require_editor` | editor, manager, admin, system_admin |
| `require_manager` | manager, admin, system_admin |
| `require_admin` | admin, system_admin |
| `require_system_admin` | system_admin only |
| `require_permission(X)` | Any role that has permission X |

---

## Part 3: Normal API Flows vs. AI Tool Flows

### 3.1 Create Document

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Endpoint | `POST /documents` | `create_document` tool |
| Auth gate | `require_editor` (editor+) | `CREATE_DOCUMENT` permission (editor+) |
| Service layer | `CreateDocumentCommandHandler` (validates, generates doc number, creates initial version) | **Direct DB insert** — no command handler |
| Audit trail | Created via command handler | **None** |
| Version creation | Auto-creates initial version | **Does NOT create initial version** |
| Validation | Full schema validation via Pydantic model | **Minimal** — title only |
| **Match?** | | ⚠️ **Partial** — permission OK, but bypasses service layer, validation, and audit |

### 3.2 Edit Document Metadata

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Endpoint | `PATCH /documents/{id}` | `edit_document` tool |
| Auth gate | `require_editor` | `EDIT_DOCUMENT` permission |
| Service layer | `DocumentService.update_document()` | **Direct DB update** |
| Status transitions | **Validates state machine transitions** | ⚠️ **Allows arbitrary status changes** — can set any status directly |
| ETag concurrency | Supports `If-Match` ETag | **No concurrency control** |
| Audit trail | Logged | **None** |
| **Match?** | | 🔴 **GAP** — can bypass state machine and set status to any value |

### 3.3 Delete Document

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Endpoint | `DELETE /documents/{id}` | `delete_document` tool |
| Auth gate | `require_manager` (manager+) | `DELETE_DOCUMENT` permission |
| Who has DELETE_DOCUMENT? | system_admin, admin, **manager** | system_admin, admin, **manager** |
| Service layer | Uses service with cascade delete logic | **Direct `db.delete()`** — may leave orphans |
| Audit trail | Logged | **None** |
| **Match?** | | ⚠️ **Permission matches**, but bypasses cascade, soft-delete, and audit trail logic |

### 3.4 Submit for Review

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Endpoint | `POST /documents/{id}/submit` | N/A — **no `submit_for_review` tool exists** |
| AI equivalent | The `submit_review` tool is for **approving/rejecting**, not submitting | |
| **Match?** | | ℹ️ No AI tool for submitting documents for review |

### 3.5 Approve / Reject Review

| Aspect | Normal API | AI Tool (`submit_review`) |
|--------|-----------|---------|
| Endpoint | `POST /reviews/{id}/approve` / `POST /reviews/{id}/reject` | `submit_review` tool |
| Auth gate | `get_current_active_user` + `can_approve()` (checks APPROVE_REVIEW for managers, APPROVE_PEER_REVIEW for editors, prevents self-approval) | role≥EDITOR only |
| Self-approval? | **Blocked** — `submitted_by != current_user.id` checked | ⚠️ Checks `reviewed_by != user.id` but **NOT `submitted_by != user.id`** — partial check |
| Review policy | Uses `ReviewPolicy.can_approve_review()` with role-aware logic | **No review policy check** |
| Document status update | Transitions document status on approval | **Does NOT update document status** |
| Notifications | Creates notifications for submitter | **No notifications** |
| Audit trail | Logged | **None** |
| **Match?** | | 🔴 **CRITICAL GAP** — editors can approve reviews through AI that they couldn't through the normal API (editors need peer-review permission which is handled differently). The tool doesn't enforce the review-policy logic. |

### 3.6 Publish Document

| Aspect | Normal API | AI Tool (`publish_document`) |
|--------|-----------|---------|
| Endpoint | `POST /documents/{docId}/versions/{verId}/publish` | `publish_document` tool |
| Auth gate | `get_current_active_user` + `PublishApprovedVersionCommandHandler` (checks `PUBLISH_DOCUMENT` permission → manager+) | role≥**EDITOR** |
| Who can publish via API? | manager, admin, system_admin | **editor, manager, admin, system_admin** |
| Requires approved review? | **Yes** — command handler validates review is approved | **No** — just sets `is_published=True` |
| Preflight checks | Version exists, not already published, user can publish, review approved, audience ready | **None** |
| Document status update | Sets document to ACTIVE | **Does NOT update document status** |
| Audit trail | Logged | **None** |
| **Match?** | | 🔴 **CRITICAL GAP** — **Editors can publish through AI** but NOT through normal API. The tool also **skips the requirement for an approved review**, completely bypassing the review workflow. |

### 3.7 Create / Manage Users

| Aspect | Normal API | AI Tool (`create_user`) |
|--------|-----------|---------|
| Endpoint | `POST /users` | `create_user` tool |
| Auth gate | `get_current_active_user` + `evaluate_manage_user()` | `MANAGE_USERS` permission |
| Who has MANAGE_USERS? | system_admin, admin | system_admin, admin |
| Role hierarchy | Enforced in service layer | Enforced in tool (can't create higher role) |
| Password policy | Validated by service layer | **No validation** — accepts any string |
| Audit trail | Logged | **None** |
| **Match?** | | ⚠️ **Permission matches**, but missing password validation and audit |

### 3.8 View Company Data / Tenants

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Auth gate | `require_system_admin` | `role≥SYSTEM_ADMIN` |
| **Match?** | | ✅ Matches |

### 3.9 Access Chat

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Auth gate | Typically `require_internal_user` / `ADD_COMMENTS` | `ADD_COMMENTS` permission |
| Customer access? | Customers don't have `ADD_COMMENTS` | Customers excluded (permission check) |
| **Match?** | | ✅ Matches — customers correctly blocked |

### 3.10 Access Feedback

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Auth gate | Various, `SUBMIT_FEEDBACK` | `SUBMIT_FEEDBACK` permission |
| **Match?** | | ✅ Matches — all roles including customer can submit |

### 3.11 Download Attachments

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Auth gate | `DOWNLOAD_ATTACHMENTS` + document visibility | `DOWNLOAD_ATTACHMENTS` or role≥VIEWER |
| Note | AI tools list/query attachments but don't serve file downloads | |
| **Match?** | | ✅ Read-only listing matches |

### 3.12 GDPR Export / Delete

| Aspect | Normal API | AI Tool |
|--------|-----------|---------|
| Endpoint | `/gdpr/export`, `/gdpr/deletion` | **No AI tool exists** |
| Auth gate | `require_system_admin` | N/A |
| **Match?** | | ℹ️ No AI tool for GDPR — this is correct behavior |

---

## Part 4: Detailed Comparison — AI Tools vs. Normal Flow

### Does each AI tool enforce the same permission as the normal API?

| AI Tool | Same Permission? | Notes |
|---------|:---:|------|
| `search_documents` | ✅ | Both require VIEW_INTERNAL_DOCS |
| `get_document` | ✅ | Both require VIEW_INTERNAL_DOCS |
| `create_document` | ✅ | Both require editor+ |
| `edit_document` | ⚠️ | Permission matches, but **no state-machine enforcement** |
| `delete_document` | ✅ | Both require manager+ (via DELETE_DOCUMENT) |
| `submit_review` | 🔴 | AI requires editor+, but **doesn't use ReviewPolicy** |
| `publish_document` | 🔴 | AI requires editor+, API requires **manager+** |
| `create_user` | ✅ | Both require MANAGE_USERS (admin+) |
| `deactivate_user` | ✅ | Both require MANAGE_USERS |
| `change_user_role` | ✅ | Both enforce hierarchy |
| `list_users` | ✅ | Both require MANAGE_USERS |
| `create_invitation` | ✅ | Both require admin+ |
| Chat tools | ✅ | All use ADD_COMMENTS |
| Settings tools | ✅ | All use SYSTEM_SETTINGS |
| Admin tools | ✅ | All use SYSTEM_SETTINGS + SYSTEM_ADMIN |
| Tenant tools | ✅ | All require SYSTEM_ADMIN |
| Analytics tools | ✅ | All use SYSTEM_SETTINGS |

### Does the AI tool respect document ownership / tenant scoping?

| AI Tool | Tenant-Scoped? | Notes |
|---------|:---:|------|
| `search_documents` | ✅ | Filters by `tenant_id` |
| `get_document` | ✅ | Checks `tenant_id` |
| `create_document` | ✅ | Sets `tenant_id` |
| `edit_document` | ✅ | Checks `tenant_id` |
| `delete_document` | ✅ | Checks `tenant_id` |
| `publish_document` | ✅ | Checks via `_check_doc_access` |
| `cancel_invitation` | 🔴 | **No tenant scope check** — can cancel any invitation |
| `get_version_details` | 🔴 | **No tenant scope** — can read any version |
| `get_document_version_stats` | 🔴 | **No tenant scope** |
| `cancel_scheduled_publish` | 🔴 | **No tenant scope** — can cancel any scheduled publish |
| Analytics tools | ⚠️ | Query **all data across tenants** (by design for sysadmin, but admin also has SYSTEM_SETTINGS) |
| Audit tools | ⚠️ | Query **all audit logs across tenants** |

### Does the AI tool go through the same state machine?

| Action | Normal API State Machine | AI Tool |
|--------|-------------------------|---------|
| Edit doc status | Validates transitions (draft→pending_review→approved→active) | 🔴 **Allows arbitrary status jumps** (e.g., draft→active) |
| Publish | Requires approved review first | 🔴 **No review check** |
| Submit for review | Validates doc is in submittable state | N/A (no tool) |
| Approve review | Updates document status to approved | 🔴 **Does NOT update document status** |

---

## Part 5: Complete Gap Analysis

### 🔴 CRITICAL — Privilege Escalation

| # | Gap | Affected Roles | Description |
|---|-----|---------------|-------------|
| **C1** | **Editor can publish via AI** | Editor | `publish_document` tool requires `role≥EDITOR`, but the normal API requires **manager+** (`PUBLISH_DOCUMENT` permission). An editor who cannot publish through the UI can publish through the AI assistant. |
| **C2** | **Editor can approve reviews without proper policy** | Editor | `submit_review` tool requires `role≥EDITOR` and doesn't enforce `ReviewPolicy`. The normal API checks whether the editor can do peer review (same-level) vs. final approval (requires manager+). The AI tool treats all approve/reject decisions the same. |
| **C3** | **Status can be set arbitrarily** | Editor+ | `edit_document` tool allows setting `status` to any value including `active` (published). This completely bypasses the review→approve→publish workflow. An editor could set a document directly to `active` status. |

### 🟠 HIGH — Workflow Bypass

| # | Gap | Description |
|---|-----|-------------|
| **H1** | **No review required before publish** | The `publish_document` tool just sets `is_published=True` on a version without checking if there's an approved `ReviewRequest`. The entire review workflow can be skipped. |
| **H2** | **No document status transition on publish** | When publishing via AI, the document's `status` field is NOT updated to `ACTIVE`. This leaves the document in an inconsistent state (version published but document still shows `draft`). |
| **H3** | **No document status transition on review approval** | When approving a review via AI, the document status is NOT updated to `APPROVED`. The normal API transitions `pending_review` → `approved`. |
| **H4** | **All write tools bypass the service layer** | Every single write operation goes directly to the database, skipping command handlers, aggregate validation, event publishing, and audit logging. |
| **H5** | **No audit trail for any AI tool action** | None of the 98 tools create `AuditLog` entries. Every normal API mutation creates audit logs. This is a compliance gap. |
| **H6** | **No notifications generated** | Review approval, document creation, status changes — none generate notifications through the AI path. |

### 🟡 MEDIUM — Tenant Isolation Gaps

| # | Gap | Description |
|---|-----|-------------|
| **M1** | **`cancel_invitation` has no tenant scope** | An admin user can cancel any invitation in the system, not just their tenant's. The `get_invitation_status` tool IS tenant-scoped, but `cancel_invitation` is not. |
| **M2** | **`get_version_details` has no tenant scope** | An editor can read version details for documents in other tenants. |
| **M3** | **`get_document_version_stats` has no tenant scope** | Same as M2 — cross-tenant data leak. |
| **M4** | **`cancel_scheduled_publish` has no tenant scope** | A user with PUBLISH_DOCUMENT permission can cancel scheduled publishes for documents in other tenants. |
| **M5** | **Analytics/audit tools show cross-tenant data** | `get_platform_analytics`, `get_engagement_analytics`, `get_content_analytics`, `search_audit_logs`, `get_user_activity` all query across all tenants. While SYSTEM_SETTINGS permission gates these, **admin** role also has SYSTEM_SETTINGS — meaning admins can see analytics for ALL tenants, not just their own. |

### 🟢 LOW — Missing Validation / Consistency

| # | Gap | Description |
|---|-----|-------------|
| **L1** | **No password validation in `create_user`** | Accepts any string as password; normal API enforces password policy. |
| **L2** | **No ETag/concurrency for `edit_document`** | Normal API uses `If-Match` headers; AI tool has no optimistic locking. |
| **L3** | **`create_document` skips initial version** | Normal API creates initial version via command handler; AI tool only creates the document record. |
| **L4** | **`delete_document` may leave orphans** | Uses `db.delete()` directly instead of the service layer's cascade logic. |
| **L5** | **No `confirm_before_execute` on `edit_document`** | Status changes are destructive but the flag is not set. |
| **L6** | **No `confirm_before_execute` on `change_user_role`** | Role changes are high-impact but the flag is not set. |
| **L7** | **`add_comment` uses `role≥VIEWER` instead of `ADD_COMMENTS` permission** | Viewer has `ADD_COMMENTS` so the net effect is the same, but customer is technically blocked by role check (correct) rather than permission check. |

---

## Summary of Findings

| Severity | Count | Key Issue |
|----------|:-----:|-----------|
| 🔴 CRITICAL | 3 | Editor privilege escalation (publish, approve, status bypass) |
| 🟠 HIGH | 6 | Workflow bypass, no audit trail, no service layer |
| 🟡 MEDIUM | 5 | Cross-tenant data access, admin sees all tenants |
| 🟢 LOW | 7 | Missing validation, missing confirmations |
| **Total** | **21** | |

### Top Recommendations

1. **`publish_document` must check `PUBLISH_DOCUMENT` permission** (not role≥EDITOR) and must verify an approved review exists before publishing
2. **`submit_review` must use `ReviewPolicy`** and check `APPROVE_REVIEW` / `APPROVE_PEER_REVIEW` correctly, including `submitted_by != user.id`
3. **`edit_document` must NOT allow arbitrary status changes** — remove `status` from editable fields, or validate state transitions
4. **All write tools should create `AuditLog` entries** — this is a compliance requirement
5. **All write tools should go through the service/command layer** instead of direct DB writes
6. **Add tenant scoping** to `cancel_invitation`, `get_version_details`, `get_document_version_stats`, `cancel_scheduled_publish`
7. **Analytics tools** should scope data to the user's tenant unless the user is `system_admin`
