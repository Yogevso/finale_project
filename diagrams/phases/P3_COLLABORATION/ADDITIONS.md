# P3: Real-Time Collaboration - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Session heartbeat and stale cleanup job | Prevents zombie sessions and bad activity metrics | Add heartbeat endpoint/event and TTL-based cleanup worker |
| High | Explicit write-downgrade protocol | Enforces permission revocation instantly | Broadcast permission change event and client-side lock transition |
| High | State persist retry queue with backpressure | Avoids data loss during transient DB/API failures | Durable queue for pending state writes with bounded retries |
| Medium | Snapshot retention policy and compaction | Controls storage growth | Keep last N snapshots + periodic archival policy |
| Medium | Per-document collaboration rate limits | Protects server from update storms | Throttle updates/activity per client and per document |
| Medium | Collab connection observability | Speeds incident diagnosis | Track connect failures, sync lag, persist latency, fanout counts |
| Low | Client conflict diagnostics overlay | Helps editors understand merge behavior | Surface Yjs conflict/merge indicators in debug mode |
| Low | Regional failover strategy for collab nodes | Improves availability | Sticky routing + state handoff plan for node failure |

## Coverage Notes

1. Existing diagrams cover token, ws auth, state persistence, sessions, and snapshots.
2. Additions focus on resilience, operational safety, and scale behavior.
3. These controls are critical for high-concurrency collaboration traffic.
