# P6: Distribution and Consumption - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Browse public catalog | `GET /public/documents`, `GET /public/categories`, `GET /public/topics`, `GET /public/stats`, `GET /public/platforms/history` | `status=active` and `visibility=public` | Anonymous discovery path. |
| UC2 | View public detail and search | `GET /public/documents/{document_id}`, `GET /public/search` | Public visibility filters | Public content retrieval. |
| UC3 | Browse customer portal catalog | `GET /portal/documents`, `GET /portal/search`, `GET /portal/categories`, `GET /portal/dashboard/stats` | Customer role + active + visibility/assignment checks | Company-scoped consumption. |
| UC4 | View portal document | `GET /portal/documents/{id}` | Customer role + access check | Requires assignment or public visibility. |
| UC5 | Download authorized attachment | `GET /portal/documents/{id}/attachments/{attachment_id}`, `GET /public/documents/{document_id}/attachments/{attachment_id}` | Access/status checks + public document constraints | Channel-specific attachment access. |
| UC6 | Browse internal viewer endpoints | `GET /viewer/documents`, `GET /viewer/documents/{id}`, `GET /viewer/documents/{id}/versions`, `GET /viewer/documents/{id}/attachments`, `GET /viewer/documents/{id}/comments` | Active document scope for internal viewers | Internal read-only channel. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Unauthorized customer access to non-assigned doc | `GET /portal/documents/{id}`, `GET /portal/documents` | Role + assignment/visibility checks | Add denied-access alert thresholds. |
| EX2 | Attachment URL guessing/enumeration | Attachment endpoints above | Access/status validation | Add signed short-lived download URLs (`ADDITIONS.md`). |
| EX3 | Cross-tenant filter leakage attempt | Portal and viewer listing/detail endpoints | Tenant/role scoped filtering | Add cache-key tenant isolation validation (`ADDITIONS.md`). |
| EX4 | Traffic spike/cache stampede | Public and portal list/search endpoints | Baseline endpoint behavior | Add throttle + CDN/cache hardening (`ADDITIONS.md`). |
| EX5 | Stale permission cache over-access risk | Portal attachment/detail endpoints | Re-check access paths exist | Add explicit cache invalidation and revalidation strategy (`ADDITIONS.md`). |
| EX6 | Missing published artifact on active doc | Public/portal detail endpoints | Standard retrieval behavior | Add artifact repair fallback workflow (`ADDITIONS.md`). |
| EX7 | Search abuse/scraping patterns | `GET /public/search`, `GET /portal/search` | Current role/visibility constraints | Add query governance + rate limits (`ADDITIONS.md`). |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Delivery/security hardening is listed in `ADDITIONS.md`.
