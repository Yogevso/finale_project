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

## Audience Domain Ownership Map

| Module/Path | Primary Owner | Secondary Owner | Responsibility |
| --- | --- | --- | --- |
| `backend/app/domain/aggregates/document_aggregate.py` | Backend Domain Team | Security Team | Audience invariants (visibility/assignment validity, submit readiness). |
| `backend/app/services/document_service.py` | Backend Authoring Team | Backend Domain Team | Assignment mutations, validation, audience audit logging, search/cache invalidation hooks. |
| `backend/app/services/version_service.py` | Backend Release Team | Backend Domain Team | Publish-time audience gates, safe-mode fallback, snapshot carry-forward. |
| `backend/app/services/outbox.py` | Platform Reliability Team | Backend Domain Team | Audience event delivery semantics, retries, DLQ transition rules. |
| `backend/app/api/management/documents.py` | Backend API Team | Backend Authoring Team | Assignment endpoints (`assign-companies`, `companies/batch`) and schema-version headers. |
| `backend/app/api/management/audience_governance.py` | Governance & Compliance Team | Backend API Team | Audience audit export, alert rules, access-history governance endpoints. |
| `backend/app/errors/audience_errors.py` | Backend Domain Team | API Contract Team | Canonical audience error taxonomy and contract lock alignment. |
| `frontend/src/features/documents/forms/audience*` | Frontend Documents Team | Backend API Team | UI schema defaults/validation for audience fields and assignment interactions. |
