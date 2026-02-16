# P2: Authoring and Content Assembly - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Create draft document | `POST /documents` | `require_editor` + tenant context | Creates baseline authoring artifact. |
| UC2 | Update metadata and structured content | `PUT /documents/{id}` | Editor role + document access + versioning rules | Main authoring mutation path. |
| UC3 | Create additional draft version | `POST /documents/{id}/versions` | Blocks when pending review exists | Prevents parallel conflicting review submissions. |
| UC4 | Upload artifacts/attachments | `POST /documents/upload`, `POST /documents/{id}/attachments`, `POST /documents/{id}/generate-word` | File/type/size constraints + access checks | Covers direct upload and generated artifacts. |
| UC5 | Create and edit comments | `POST /documents/{id}/comments`, `PATCH /documents/{id}/comments/{comment_id}` | Authenticated role + ownership/role checks | Supports collaboration threads. |
| UC6 | Resolve comment thread | `POST /documents/{id}/comments/{comment_id}/resolve` | Admin/editor resolve permissions | Enforces moderation authority. |
| UC7 | Assign companies to document | `POST /documents/{id}/assign-companies`, `DELETE /documents/{id}/assign-companies/{company_id}` | `assign_companies` permission + company validation | Controls customer visibility scope. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | New version when pending review exists | `POST /documents/{id}/versions` | Explicit pending-review conflict block | Add user-facing conflict details for faster resolution. |
| EX2 | Edit immutable/workflow-locked version | `PATCH /documents/{id}/versions/{version_id}` | Blocks published/approved/pending-review edits | Add structured error codes for client branching. |
| EX3 | Invalid file type or oversized upload | `POST /documents/upload`, `POST /documents/{id}/attachments` | Upload constraints | Add malware and secret scanning pipeline (`ADDITIONS.md`). |
| EX4 | Storage failure during artifact handling | `POST /documents/{id}/attachments`, `POST /documents/{id}/generate-word` | Service failure propagation | Add retry/outbox and partial-write recovery (`ADDITIONS.md`). |
| EX5 | Unauthorized comment mutate/resolve | `PATCH /comments/{id}`, `POST /comments/{id}/resolve` | Ownership/role checks | Add explicit audit records for denied moderation attempts. |
| EX6 | Invalid company assignment set | `POST /documents/{id}/assign-companies` | Permission + company id validation | Add bulk assignment transactional guarantees (`ADDITIONS.md`). |
| EX7 | Payload schema mismatch causing partial update risk | `PUT /documents/{id}`, `PATCH /versions/{version_id}` | Basic validation + service rules | Add schema version enforcement (`ADDITIONS.md`). |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Authoring hardening items are listed in `ADDITIONS.md`.
