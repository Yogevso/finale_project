# P6: Distribution and Consumption - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Signed short-lived attachment URLs | Prevents direct object path abuse | Use time-bound signed URLs with document and actor claims |
| High | Permission re-check on download and cache bypass path | Prevents stale ACL leak | Always validate active status and scope before serving file |
| High | Tenant-isolated cache key strategy | Avoids cross-tenant cache pollution | Include tenant/visibility scope in cache keys |
| Medium | Bot/scrape protection and per-IP throttling | Reduces abuse and cost | Add rate limits, challenge mechanisms, anomaly thresholds |
| Medium | Fallback for missing publish artifacts | Maintains UX during inconsistencies | Return graceful degraded response and trigger repair job |
| Medium | Search query governance | Prevents expensive abusive queries | Limit query complexity and support indexed facets only |
| Low | CDN invalidation hooks on publish/update | Improves freshness | Emit cache purge events when active content changes |
| Low | Content delivery SLA metrics | Makes reliability observable | Track p95/p99 latency, cache hit rate, and error budgets |

## Coverage Notes

1. Existing phase diagrams cover channel-level visibility and access rules.
2. Additions focus on secure delivery, scale resilience, and cache correctness.
3. Important for public traffic and customer-facing reliability guarantees.
