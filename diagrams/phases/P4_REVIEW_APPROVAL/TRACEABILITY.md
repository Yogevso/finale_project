# P4: Review and Approval - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Submit draft/version for review | `POST /reviews/documents/{document_id}/submit` | Draft status + no pending review + role checks | Initiates review workflow. |
| UC2 | Open pending review queue | `GET /reviews/pending` | Reviewer role guard + exclude own submissions | Reviewer workload view. |
| UC3 | Approve review request | `POST /reviews/{review_id}/approve` | No self-approval + stale-version checks | Transitions document to approved. |
| UC4 | Reject review request | `POST /reviews/{review_id}/reject` | Reviewer authorization + pending-state checks | Returns document to draft. |
| UC5 | Cancel own pending review | `POST /reviews/{review_id}/cancel` | Submitter ownership + pending-only rule | Allows submitter-driven abort. |
| UC6 | Inspect review history and status | `GET /reviews/my-submissions`, `GET /reviews/{review_id}`, `GET /reviews/documents/{document_id}/history` | Access checks + document existence | Provides lifecycle traceability. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Duplicate pending review submission | `POST /reviews/documents/{document_id}/submit` | No-existing-pending guard | Add stronger idempotency semantics (`ADDITIONS.md`). |
| EX2 | Reviewer self-approval attempt | `POST /reviews/{review_id}/approve` | Explicit no self-approval rule | Add explicit reviewer-separation policy options. |
| EX3 | Reviewer acts on stale version | `POST /reviews/{review_id}/approve` | Stale-version checks | Add clearer stale conflict remediation guidance. |
| EX4 | Concurrent approve/reject race | `POST /reviews/{review_id}/approve`, `POST /reviews/{review_id}/reject` | Pending-state transition checks | Add optimistic locking/idempotent action keys (`ADDITIONS.md`). |
| EX5 | Unauthorized reviewer action | `GET /reviews/{review_id}`, review action endpoints | Reviewer authorization checks | Add denied-action anomaly alerts. |
| EX6 | Cancel after final decision | `POST /reviews/{review_id}/cancel` | Pending-only cancellation | Add explicit terminal-state machine response codes. |
| EX7 | Notification/audit emission failure | Review action endpoints with side effects | Side effects performed after transition | Add outbox + retry for notification/audit durability (`ADDITIONS.md`). |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Governance and robustness improvements are in `ADDITIONS.md`.
