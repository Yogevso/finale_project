# Wave G - Backend Core Foundations

## Scope

- Task IDs: 45, 50, 51, 52, 111, 74, 64, 75, 102, 114
- Reference plan: plan

## Pre-checks

- [ ] Confirm linked ADRs exist or are updated for architecture-impacting changes.
- [ ] Confirm ownership and dependency impact in docs/context-ownership.md and docs/context-map/.
- [ ] Confirm any compatibility/deprecation implications in policy docs.
- [ ] Confirm architecture debt implications are recorded in docs/architecture-debt.md.

## Change steps

- [ ] Implement tasks in dependency order listed for this wave.
- [ ] Keep changes behind clear module/service boundaries.
- [ ] Update tests and CI checks for touched architecture boundaries.

## Validation checklist

- [ ] Unit/integration tests for touched domains pass.
- [ ] Lint/type checks pass for touched modules.
- [ ] Contract compatibility expectations are documented.
- [ ] Manual smoke checks (where applicable) are completed.

## Rollback checklist

- [ ] Identify feature flags/toggles or fallback paths before rollout.
- [ ] Keep migration notes for reversal order.
- [ ] Confirm observability signals can detect failed rollout quickly.

## References

- ADR workflow: docs/adr/README.md
- Context ownership map: docs/context-ownership.md
- Context map artifacts: docs/context-map/README.md
- Contract versioning policy: docs/contracts/versioning.md
- Architecture debt register: docs/architecture-debt.md
