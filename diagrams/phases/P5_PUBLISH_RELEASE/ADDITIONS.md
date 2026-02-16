# P5: Publish and Release - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Idempotent publish operation key | Prevents duplicate release transitions | Require idempotency key and unique publish transaction id |
| High | Controlled rollback workflow | Handles bad releases safely | Add rollback/unpublish protocol with strict audit and approvals |
| High | Publish health checks and post-release validation | Catches broken releases quickly | Validate key retrieval paths and attachment availability after publish |
| Medium | Scheduled publish windows | Supports coordinated launches | Allow delayed publish with lock and preflight validation |
| Medium | Release notes and change summary artifact | Improves stakeholder communication | Auto-generate release note from version diffs and approvals |
| Medium | Notification delivery retry/outbox | Improves reliability | Use durable outbox + retries + dead-letter tracking |
| Low | Canary release for selected tenants | Reduces rollout risk | Enable phased activation to subset of audience |
| Low | Freeze window policy | Avoids risky off-hours releases | Time-based guard with privileged override and audit |

## Coverage Notes

1. Existing diagrams cover core publish path and immutability guard.
2. Additions improve release safety, observability, and rollback readiness.
3. Recommended before strict uptime or compliance commitments.
