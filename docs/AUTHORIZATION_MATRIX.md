# Authorization Matrix

> **Canonical source of truth** for role-based access control across the platform.
> Every backend route dependency and frontend guard MUST align with this matrix.
>
> Last updated: FIX-027 remediation

---

## Role Hierarchy

| Role | Level | Scope | Description |
|------|-------|-------|-------------|
| `system_admin` | 1 (highest) | Cross-tenant | Full platform control, can impersonate, cross-tenant access |
| `admin` | 2 | Tenant | Manages users, companies, full access within own tenant |
| `manager` | 3 | Tenant | Approves content, publishes, creates editors, analytics |
| `editor` | 4 | Tenant | Creates/edits content, peer reviews, version management |
| `viewer` | 5 | Tenant | Internal read-only access (legacy role) |
| `customer` | 6 | Company | External user — views assigned company docs, submits feedback |

**Key concepts:**
- **Internal** = all roles except `customer` (system_admin, admin, manager, editor, viewer)
- **Editor+** = system_admin, admin, manager, editor
- **Manager+** = system_admin, admin, manager
- **Admin+** = system_admin, admin
- Tenant isolation enforced for all non-system_admin roles

---

## Permission Matrix

| Permission | system_admin | admin | manager | editor | viewer | customer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| VIEW_PUBLIC_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VIEW_INTERNAL_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| VIEW_COMPANY_DOCS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (own) |
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

---

## Backend Guard Mapping

| Guard Dependency | Allowed Roles | File |
|---|---|---|
| `get_current_active_user` | Any authenticated (all 6 roles) | `backend/app/security.py` |
| `get_tenant_context` | Any authenticated | `backend/app/dependencies/permissions.py` |
| `require_internal_user` | system_admin, admin, manager, editor, viewer | `backend/app/dependencies/permissions.py` |
| `require_editor` | system_admin, admin, manager, editor | `backend/app/dependencies/permissions.py` |
| `require_manager` | system_admin, admin, manager | `backend/app/dependencies/permissions.py` |
| `require_admin` | system_admin, admin | `backend/app/dependencies/permissions.py` |
| `require_system_admin` | system_admin | `backend/app/dependencies/permissions.py` |
| `require_customer` | customer | `backend/app/dependencies/permissions.py` |

---

## Frontend Guard Mapping

| Guard Component | Allowed Roles | File |
|---|---|---|
| `InternalGuard` | system_admin, admin, manager, editor, viewer | `frontend/src/components/guards/RoleGuard.tsx` |
| `EditorGuard` | system_admin, admin, manager, editor | `frontend/src/components/guards/RoleGuard.tsx` |
| `ManagerGuard` | system_admin, admin, manager | `frontend/src/components/guards/RoleGuard.tsx` |
| `AdminGuard` | system_admin, admin | `frontend/src/components/guards/RoleGuard.tsx` |
| `CustomerRoute` | customer | `frontend/src/components/guards/CustomerRoute.tsx` |

---

## API Endpoint Matrix

### Authentication (`/api/auth/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU | Public |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `/auth/login` | POST | None | | | | | | | ✅ |
| `/auth/register` | POST | None | | | | | | | ✅ |
| `/auth/forgot-password` | POST | None | | | | | | | ✅ |
| `/auth/reset-password` | POST | None | | | | | | | ✅ |
| `/auth/refresh` | POST | None | | | | | | | ✅ |
| `/auth/verify-email` | GET | None | | | | | | | ✅ |
| `/auth/invitation/{token}` | GET | None | | | | | | | ✅ |
| `/auth/invitation/accept` | POST | None | | | | | | | ✅ |
| `/auth/me` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `/auth/logout` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `/auth/change-password` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `/auth/collab-token` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |

### Documents — Management (`/api/documents/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/documents` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/upload` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/tags` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/duplicate-check` | GET | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/bulk-metadata` | POST | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/stats` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}` | PUT | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/{id}` | DELETE | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/watch-status` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}/watch` | POST | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}/watch` | DELETE | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}/generate-word` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/{id}/assigned-companies` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/documents/{id}/assign-companies` | POST | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/companies/batch` | PUT | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/assign-companies/{cid}` | DELETE | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/archive` | POST | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/restore` | POST | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/documents/{id}/calendar-export` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Versions (`/api/documents/{id}/versions/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/versions` | GET | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}` | GET | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}` | PATCH | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}` | DELETE | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/diff` | GET | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/restore` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/promote` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/attachments` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/attach-existing` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/attachments/{aid}` | DELETE | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/versions/{vid}/lock` | POST | Editor+ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

### Reviews (`/api/reviews/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/documents/{id}/submit` | POST | Policy (Editor+) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/pending` | GET | Policy check | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/my-submissions` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/{review_id}` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/{review_id}/approve/preflight` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/{review_id}/approve` | POST | Policy (Manager+ or peer) | ✅ | ✅ | ✅ | ✅* | ❌ | ❌ |
| `/{review_id}/reject` | POST | Policy check | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/{review_id}/cancel` | POST | Ownership check | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `/documents/{id}/history` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> *Editor can approve **peer reviews** only (not formal approvals)

### Comments (`/api/documents/{id}/comments/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/comments` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments/stats` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments/{cid}` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments/{cid}` | PATCH | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments/{cid}/resolve` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/comments/{cid}` | DELETE | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Attachments (`/api/attachments/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/attachments/{id}/pdf-status` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/attachments/download-ticket` | POST | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/documents/{id}/attachments` | GET | Any auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/documents/{id}/attachments/{aid}/download` | GET | Ticket-based | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Users (`/api/users/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/users` | GET | Policy (Admin+) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/users` | POST | Policy (Admin+) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/users/me` | PATCH | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/notification-preferences` | PATCH | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/avatar` | POST | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/sessions` | GET | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/sessions/{sid}` | DELETE | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/sessions` | DELETE | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/me/security-events` | GET | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/users/{uid}` | GET | Policy (Admin+) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/users/{uid}` | PUT | Policy (Admin+) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/users/{uid}` | DELETE | Policy (Admin+) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/admin/users/{uid}/unlock` | POST | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

### Companies (`/api/companies/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/companies` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies` | POST | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}` | PUT | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}` | DELETE | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}/users` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}/users` | POST | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}/users/{uid}` | DELETE | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/companies/{id}/documents` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

### Tenants (`/api/tenants/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| All tenant CRUD | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Analytics (`/api/analytics/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/overview` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/recent-activity` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/engagement` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/engagement/top-documents` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/users` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/content` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/feedback` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/tenants` | GET | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `/company/{id}` | GET | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/documents/{id}/audience-churn` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/export/csv` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Search (`/api/search/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `/` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/autocomplete` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/facets` | GET | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/saved` | GET/POST | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/saved/{id}` | DELETE | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/click` | POST | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `/analytics` | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Chat (`/api/chats/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| All chat endpoints | * | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### AI Assistant (`/api/assistant/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| All assistant endpoints | * | Any auth + enabled check | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Support (`/api/support/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Ticket list/detail/create | * | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Ticket update/assign/handoff | * | Support agent (Manager+) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Canned responses | * | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Feedback (`/api/feedback/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| List/detail/respond/stats | * | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Update status | PUT | Internal | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Invitations (`/api/invitations/`)

| Action | SA | AD | MG | ED | VW | CU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Manage invitations | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Invite system_admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Invite admin | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite manager | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Invite editor/viewer/customer | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Admin Operations (`/api/admin/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| All admin ops | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| System settings | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| RBAC policies | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GDPR/compliance | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Feature flags (DB) | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Config flags (read) | GET | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Experimentation | * | System admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Notifications (`/api/notifications/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Own notifications CRUD | * | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Engagement (`/api/engagement/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Bookmarks, feedback, reading progress | * | Any auth (self) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Broken Links (`/api/broken-links/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| All endpoints | * | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Changelog (`/api/changelog/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Write (POST/PUT/DELETE) | * | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Audience Governance (`/api/audience/`)

| Endpoint | Method | Guard | SA | AD | MG | ED | VW | CU |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Audit export | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Alert rules | * | Admin+ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Access history | GET | Manager+ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## Customer Portal (`/api/portal/`)

| Feature | Guard | CU |
|---|---|:---:|
| Documents (list, detail, related, attachments, download) | Customer only | ✅ |
| Categories, facets, search | Customer only | ✅ |
| Dashboard, reading progress | Customer only | ✅ |
| Feedback (submit, list, chat) | Customer only | ✅ |
| Support (tickets) | Customer only | ✅ |
| NPS (submit, status) | Any auth | ✅ |

---

## Public API (`/api/public/`)

All endpoints are unauthenticated:
- Published documents, platforms, topics, categories
- Changelog, announcements, sitemap

---

## Frontend Route Guard Alignment

| Frontend Route | Frontend Guard | Backend Guard | Aligned? |
|---|---|---|:---:|
| `/dashboard` | InternalGuard | Internal | ✅ |
| `/documents` | InternalGuard | Internal (list), Editor+ (write) | ✅ |
| `/documents/:id/compare` | EditorGuard | Editor+ | ✅ |
| `/reviews` | RoleGuard (editor+) | Policy (editor+) | ✅ |
| `/notifications` | InternalGuard | Any auth | ✅ |
| `/profile` | InternalGuard | Any auth (self) | ✅ |
| `/chat` | InternalGuard | Internal | ✅ |
| `/assistant` | InternalGuard | Any auth | ✅ |
| `/support` | ManagerGuard | Internal (view), Manager+ (manage) | ✅ |
| `/users` | ManagerGuard | Admin+ (policy) | ⚠️ |
| `/admin/feedback` | ManagerGuard | Manager+ | ✅ |
| `/analytics` | ManagerGuard | Manager+ | ✅ |
| `/admin/companies` | AdminGuard | Admin+ | ✅ |
| `/admin/system-setup` | RoleGuard (SA) | System admin | ✅ |
| `/admin/operations` | RoleGuard (SA) | System admin | ✅ |
| `/portal/*` | CustomerRoute | Customer | ✅ |

> ⚠️ `/users` route uses ManagerGuard (allows manager) but backend user CRUD requires Admin+. Manager users see the page but API calls return 403. Acceptable since manager can manage editors via the invitation flow.
