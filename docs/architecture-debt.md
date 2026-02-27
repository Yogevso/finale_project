# Architecture Debt Register

This register tracks architecture debt with explicit ownership and risk.

## Rules

- Risk score range: `1` (low) to `5` (critical).
- Every open item must have an owner and mitigation plan.
- Due dates use `YYYY-MM-DD`.
- CI reports overdue high-risk (`risk >= 4`) items.

## Debt items

| ID | Title | Owner | Risk | Due Date | Status | Mitigation Plan | Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AD-001 | Direct DB access remains in some route handlers | Engineering | 4 | 2026-04-15 | open | Enforce route-level DB access lint/check and migrate hot paths to services/repositories first | plan Task 100 |
| AD-002 | Bounded contexts not fully enforced by imports/layers | Engineering | 4 | 2026-05-01 | open | Ship package/layer split and architecture fitness checks before Wave G rollout closes | plan Tasks 93, 81 |
| AD-003 | Contract compatibility checks are partial across services | Engineering | 3 | 2026-05-15 | open | Expand provider/consumer contract checks and adopt version policy controls in CI | plan Tasks 97, 117, 79 |

## Maintenance cadence

- Review weekly during active refactor waves.
- Close or re-score items when mitigation lands.
- Add new items when significant architecture risks are identified.
