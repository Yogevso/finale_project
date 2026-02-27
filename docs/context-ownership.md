# Data Ownership Map by Bounded Context

This map defines single write-owners for major entity groups. Cross-context
writes are disallowed unless explicitly documented and approved.

| Bounded Context | Write Owner | Owned Entities/Aggregates | Allowed Read Dependencies | Cross-Context Write Rule |
| --- | --- | --- | --- | --- |
| Access and Identity | Backend auth/rbac services | users, invitations, role bindings, permission policies | documents metadata, tenant metadata | No writes outside identity entities |
| Governance and Tenant Setup | Backend tenant/system services | tenants, system settings | users, policy snapshots | No writes to document content/reviews |
| Authoring and Assembly | Backend document/version services | documents, versions, sections, tags/topic assignments | policy decisions, tenant context | No writes to notification delivery state |
| Review and Approval | Backend review services | review requests, approvals/rejections | documents/versions, users | No direct writes to analytics aggregates |
| Collaboration | Collab server + backend collaboration services | live sessions, snapshots, activity feed records | document metadata, auth tokens | No writes to canonical document metadata outside service contracts |
| Distribution and Consumption | Backend portal/viewer services | portal/document access projections, reader views | documents/versions, company assignments | No writes to identity or policy data |
| Feedback, Analytics, Audit | Backend analytics/feedback/audit services | feedback entries, engagement metrics, audit logs | documents/users/tenants | No writes to source-of-truth authoring content |

## Enforcement guidance

- Route handlers should call owning services/repositories only.
- Cross-context writes require explicit ADR and temporary migration guard.
- Context ownership changes must update:
- `docs/context-map/*`
- relevant migration playbook in `docs/migrations/*`
