# P5: Publish and Release - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Inspect release candidates | `GET /documents/{document_id}/versions`, `GET /documents/{document_id}/versions/{version_id}` | Internal-user access for inspection | Candidate evaluation before release. |
| UC2 | Publish approved version | `POST /documents/{document_id}/versions/{version_id}/publish` | Manager/admin/system-admin + approved review required | Main release action. |
| UC3 | Activate document state | Side effect of publish endpoint above | Sets `document.status=active` and publish metadata | Runtime visibility transition. |
| UC4 | Emit publish notifications | Side effect of publish endpoint (email/event path) | Optional publish notification branch | Stakeholder communication path. |
| UC5 | Enforce published immutability | `PATCH /documents/{document_id}/versions/{version_id}`, `DELETE /documents/{document_id}/versions/{version_id}` | Published version mutation blocked | Protects release integrity. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Publish without approved review | `POST /documents/{document_id}/versions/{version_id}/publish` | Latest approved review required | Add explicit preflight API for UI workflows. |
| EX2 | Duplicate publish on already-published version | Publish endpoint above | `is_published` guard | Add idempotency key semantics (`ADDITIONS.md`). |
| EX3 | Concurrent publish race | Publish endpoint above | Validation path exists | Add transactional locking and unique publish op id (`ADDITIONS.md`). |
| EX4 | Post-publish mutation attempt | `PATCH/DELETE /documents/{document_id}/versions/{version_id}` | Immutable guard rejects mutation | Add dedicated immutable-violation audit stream. |
| EX5 | Notification delivery failure | Publish side-effect pipeline | Optional queue path | Add durable outbox + retries (`ADDITIONS.md`). |
| EX6 | Rollback needed after release | No explicit rollback endpoint in current inventory | Manual mitigation only | Add controlled rollback workflow (`ADDITIONS.md`). |
| EX7 | Actor lacks publish role | Publish endpoint above | Publisher role validation | Add step-up auth for production-critical releases. |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Release-hardening additions are in `ADDITIONS.md`.
