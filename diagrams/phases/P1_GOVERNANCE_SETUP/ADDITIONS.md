# P1: Governance and Setup - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Enforce tenant scoping on company APIs for non-system admins | Current company routes rely only on role checks | Add tenant-context checks so admins cannot manage unrelated tenants |
| High | Enforce tenant reassignment guard in user update path | Current `PUT /users/{id}` can reassign tenant without explicit non-system scope check | Require system-admin for cross-tenant reassignment |
| High | Expand audit coverage beyond RBAC/settings | Tenant, company, and user mutations currently lack uniform audit writes | Add structured audit events for all governance mutations |
| High | Optimistic locking for RBAC and settings updates | Current writes are last-write-wins | Add version or ETag checks to prevent silent overwrite |
| Medium | Tenant deletion dependency checks for documents/assignments | Current delete guard checks users only | Block deletion when documents or assignments still reference tenant |
| Medium | RBAC rollback and dry-run simulation | Bad policy updates can remove critical access | Add policy version history, dry-run, and rollback endpoint |
| Medium | Dual-control for high-risk governance actions | Single admin action can have broad impact | Require second approver for tenant deletion and RBAC publish in strict mode |
| Low | Settings schema registry and validation | Arbitrary values can be persisted | Validate key names, types, and ranges before upsert |

## Coverage Notes

1. Core governance CRUD and publishing flows are implemented.
2. RBAC and settings write audit events exist; broader governance audit coverage is still a gap.
3. The biggest risk areas are cross-tenant governance scope and concurrent update safety.
