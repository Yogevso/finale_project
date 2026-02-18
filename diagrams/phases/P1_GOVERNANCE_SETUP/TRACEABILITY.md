# P1: Governance and Setup - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Read and update RBAC policies | `GET /rbac/policies`, `PUT /rbac/policies` | `require_system_admin` + service publish | `PUT` also writes a `SYSTEM` audit log entry. |
| UC2 | Publish policy set | `POST /rbac/policies/publish` | `require_system_admin` | Loads persisted policy map into runtime permission store. |
| UC3 | Manage system settings | `GET /system/settings`, `PUT /system/settings` | `require_system_admin` | `PUT` upserts keys and removes missing keys. |
| UC4 | Manage tenants | `POST /tenants`, `GET /tenants`, `GET/PUT/DELETE /tenants/{id}`, `GET /tenants/{id}/users` | `require_system_admin` + slug and delete constraints | Delete is blocked if tenant still has users. |
| UC5 | Manage companies | `GET/POST /companies`, `GET/PUT/DELETE /companies/{id}` | Local admin role check | Company rows are backed by `Tenant` model; delete is soft (`is_active=false`). |
| UC6 | Manage company membership | `GET/POST /companies/{id}/users`, `DELETE /companies/{id}/users/{user_id}` | Local admin role check + cannot remove self | Membership maps to `user.tenant_id` assignment. |
| UC7 | Manage users and self profile | `GET/POST /users`, `GET/PUT/DELETE /users/{id}` | Role hierarchy + tenant context checks | Self-profile read/update is allowed; delete is admin/system-admin only. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Duplicate tenant/company slug | `/tenants...`, `/companies...` | Uniqueness checks before create/update | Add normalized slug reservation to avoid race collisions. |
| EX2 | Tenant delete with active users | `DELETE /tenants/{tenant_id}` | User-count guard blocks deletion | Add document/dependency checks for full safety. |
| EX3 | Role escalation beyond manager/admin limits | `POST /users`, `PUT /users/{user_id}`, `DELETE /users/{user_id}` | `can_manage_role` hierarchy checks | Add centralized policy-driven hierarchy. |
| EX4 | Self-deactivation or self-delete | `PUT /users/{user_id}`, `DELETE /users/{user_id}` | Explicit self-protection checks | Add break-glass and delegated recovery controls. |
| EX5 | Cross-tenant user visibility attempt | `GET /users`, `GET /users/{id}`, `DELETE /users/{id}` | Non-system users scoped by tenant context | Add explicit denied-attempt audit trail. |
| EX6 | Admin deactivates own company | `DELETE /companies/{company_id}` | Explicit check against current user tenant | Add safeguard warnings in UI and API confirmation token. |
| EX7 | Concurrent governance writes | `PUT /rbac/policies`, `PUT /system/settings` | Last-write-wins semantics | Add optimistic locking and version checks. |

## Coverage and Gap Link

1. Endpoint coverage is mapped in `SEQUENCE.md`.
2. Behavior and actors are summarized in `USE_CASE.md`.
3. Operational hardening backlog is documented in `ADDITIONS.md`.
