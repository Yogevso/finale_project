# P1: Governance and Setup - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Read and update RBAC policies | `GET /rbac/policies`, `PUT /rbac/policies` | `require_system_admin` | Policy matrix management is system-admin only. |
| UC2 | Publish active policy set | `POST /rbac/policies/publish` | System-admin publish guard | Pushes effective permission changes runtime-wide. |
| UC3 | Manage system settings | `GET /system/settings`, `PUT /system/settings` | `require_system_admin` | Global config change control. |
| UC4 | Manage tenants | `POST /tenants`, `GET /tenants`, `PUT /tenants/{id}`, `DELETE /tenants/{id}` | `require_system_admin` + validation constraints | Includes slug and dependency validations. |
| UC5 | Manage companies | `GET /companies...`, `POST /companies...`, `PUT /companies...`, `DELETE /companies...` | Admin/system-admin role gates | Tenant-aware company operations. |
| UC6 | Manage users in hierarchy bounds | `GET /users...`, `POST /users...`, `PUT /users...`, `DELETE /users...` | Role hierarchy + tenant scope | Prevents out-of-scope user operations. |
| UC7 | Review governance audit effects | Audit writes from policy/settings/tenant/company/user mutations | Audit insertion on mutating operations | Read endpoint not explicitly listed in this phase inventory. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Policy publish causes access conflict | `POST /rbac/policies/publish` | Publish flow with admin gate | Add dry-run impact analysis + rollback (`ADDITIONS.md`). |
| EX2 | Cross-tenant management attempt | `/tenants...`, `/companies...`, `/users...` | Tenant scope and role checks | Add explicit denied-action alerting for repeated attempts. |
| EX3 | Manager creates user above allowed role | `POST /users...`, `PUT /users...` | Role hierarchy validation | Add clearer policy explanation payloads for clients. |
| EX4 | Tenant delete with active dependencies | `DELETE /tenants/{id}` | Constraint validation | Add staged archive/delete lifecycle (`ADDITIONS.md`). |
| EX5 | Concurrent policy/settings edits race | `PUT /rbac/policies`, `PUT /system/settings` | Upsert semantics | Add optimistic locking with version/etag (`ADDITIONS.md`). |
| EX6 | Self-deactivation or admin lockout path | `DELETE /users/{id}` | Cannot delete self checks | Add break-glass mechanism (`ADDITIONS.md`). |
| EX7 | Invalid settings key/type payload | `PUT /system/settings` | Current upsert behavior | Add strict schema registry enforcement (`ADDITIONS.md`). |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Safety and governance improvements are in `ADDITIONS.md`.
