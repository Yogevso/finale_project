# P2: Authoring and Content Assembly - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Create document with initial version | `POST /documents` | `require_editor` + tenant-context scope | Service auto-creates version `1.0.0` placeholder. |
| UC2 | List and read documents | `GET /documents`, `GET /documents/{id}` | `require_internal_user` + tenant-scoped document service queries | Customer users are blocked from internal routes. |
| UC3 | Update document metadata | `PUT /documents/{id}` | `require_editor`; visibility change requires manager/admin/system-admin | Changed fields produce patch version entries. |
| UC4 | Manage versions | `GET/POST/PATCH/DELETE /documents/{id}/versions...`, `POST /documents/{id}/versions/{version_id}/publish` | Role checks + review-state checks | Publish requires approved review for that version. |
| UC5 | Manage attachments and artifacts | `POST /documents/upload`, `POST /documents/{id}/attachments`, `POST /documents/{id}/generate-word`, attachment read endpoints | Upload role check + mime/size validation | PDF uploads queue reader-view generation; checksums persisted. |
| UC6 | Manage comments | `GET/POST/PATCH/DELETE /documents/{id}/comments...`, `POST .../resolve` | Auth + contributor visibility + mutation permission checks | Author/admin rules differ per content, resolve, and delete operations. |
| UC7 | Manage company assignments | `GET /documents/{id}/assigned-companies`, `POST/DELETE /documents/{id}/assign-companies...` | Internal user or `assign_companies` permission | Uses document-company assignment relationship. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Create version while review pending | `POST /documents/{id}/versions` | Explicit pending-review conflict check (`409`) | Include review reference in error payload for UX. |
| EX2 | Update published/pending/approved version | `PATCH /documents/{id}/versions/{version_id}` | Published -> `400`; pending/approved review -> `409` | Add machine-readable error codes for client branching. |
| EX3 | Publish without approved review | `POST /documents/{id}/versions/{version_id}/publish` | Requires existing approved review (`409` otherwise) | Add preflight endpoint to expose publish readiness. |
| EX4 | Unsupported or oversized upload | `POST /documents/upload`, `POST /documents/{id}/attachments` | MIME/extension and max-size checks (`400`) | Add malware and secret scanning pipeline. |
| EX5 | Non-admin attachment delete attempt | `DELETE /documents/{id}/attachments/{attachment_id}` | Service allows admin role only | Align role policy (admin-only vs manager/system-admin expectations). |
| EX6 | Unauthorized comment mutation | `PATCH` and `DELETE` comment endpoints | Role/author checks enforce operation-specific permissions | Add deny-event audit trail for moderation actions. |
| EX7 | Missing tenant/document access checks on some endpoints | Versions, attachments, comments read/mutate paths | Auth and role checks exist but some tenant-scope checks are absent | Add tenant-aware access validation in all service entry points. |

## Coverage and Gap Link

1. Endpoint coverage is mapped in `SEQUENCE.md`.
2. Actor behavior is summarized in `USE_CASE.md`.
3. Integrity and security backlog is listed in `ADDITIONS.md`.
