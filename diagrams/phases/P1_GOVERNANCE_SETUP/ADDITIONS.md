# P1: Governance and Setup - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | RBAC policy versioning with rollback | Safe recovery from bad policy publish | Keep immutable policy revisions and add rollback endpoint |
| High | Policy impact dry-run | Prevent accidental lockouts | Simulate publish against sampled role/action matrix before commit |
| High | Dual-approval for high-risk governance changes | Reduces single-admin blast radius | Require second approver for tenant delete and system-critical settings |
| High | Strong optimistic locking on policy/settings writes | Prevents lost updates | Use version/etag checks on `PUT` endpoints |
| Medium | Break-glass emergency admin process | Handles lockout incidents safely | Time-bound emergency role with mandatory audit and notification |
| Medium | Tenant deletion archive workflow | Preserves compliance and forensics | Soft-delete then delayed purge after retention window |
| Medium | Configuration schema validation registry | Avoids invalid setting payloads | Central schema for allowed keys, types, ranges |
| Low | Governance change notifications to auditors | Improves visibility | Emit notifications/webhooks for policy and settings changes |

## Coverage Notes

1. Existing phase diagrams cover core governance CRUD and policy publish.
2. Additions focus on safety rails, approval controls, and recovery paths.
3. These are especially important for multi-tenant production environments.
