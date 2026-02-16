# P7: Feedback, Analytics, and Audit - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Submit customer feedback | `POST /portal/feedback` | Customer role + document access checks | Feedback ingestion entrypoint. |
| UC2 | Track own feedback | `GET /portal/feedback`, `GET /portal/feedback/{id}` | Own-feedback visibility only | Customer self-service status tracking. |
| UC3 | View internal feedback queue | `GET /feedback`, `GET /feedback/{id}`, `GET /feedback/stats/summary` | Internal role + contributor visibility | Staff-facing feedback operations. |
| UC4 | Respond/update feedback status | `POST /feedback/{id}/respond`, `PUT /feedback/{id}/status` | Admin/manager or internal role + contributor visibility | Resolution and lifecycle transitions. |
| UC5 | Manage personal notifications | `GET /notifications`, `GET /notifications/count`, `POST /notifications/read`, `POST /notifications/{id}/read`, `DELETE /notifications/{id}`, `DELETE /notifications` | Current-user scoping | Notification consumption loop. |
| UC6 | View analytics dashboards | `GET /analytics/overview`, `GET /analytics/engagement`, `GET /analytics/content`, `GET /analytics/feedback`, `GET /analytics/recent-activity`, `GET /analytics/users`, `GET /analytics/tenants` | Manager+/admin+/system-admin role gates by endpoint | Role-specific analytics depth. |
| UC7 | Export analytics reports | `GET /analytics/export/csv`, `GET /analytics/export/pdf` | Manager+ role gates | Report extraction path. |
| UC8 | Review cross-tenant analytics | `GET /analytics/tenants` | `require_system_admin` | Global platform visibility. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Feedback spam/abuse | `POST /portal/feedback` | Customer access checks | Add anti-spam/rate controls (`ADDITIONS.md`). |
| EX2 | Unauthorized feedback response attempt | `POST /feedback/{id}/respond`, `PUT /feedback/{id}/status` | Contributor visibility + role checks | Add denied-action escalation signals. |
| EX3 | Notification unread/count drift | Notification read/count endpoints | Current user-scoped updates | Add periodic reconciliation job (`ADDITIONS.md`). |
| EX4 | Unauthorized export request | `GET /analytics/export/csv`, `GET /analytics/export/pdf` | Manager+ gate | Add signed export artifacts + audit hardening (`ADDITIONS.md`). |
| EX5 | Telemetry skew affecting analytics | Analytics dashboard endpoints | Aggregation with role filters | Add ingest schema governance + quality monitors (`ADDITIONS.md`). |
| EX6 | Long-running/failed export | Export endpoints | Direct request/response behavior | Add async export workflow with retry/resume (`ADDITIONS.md`). |
| EX7 | Cross-tenant analytics leak attempt | `GET /analytics/tenants` and tenant-scoped analytics endpoints | System-admin and scoped guards | Add stricter field-level tenancy checks in reporting pipeline. |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Data quality and governance improvements are in `ADDITIONS.md`.
