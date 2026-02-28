# Wave J - Write-Path Reliability and Rollout Safety

## Scope

- Task IDs: 53, 72, 73, 101, 107, 106, 105, 99, 108, 118
- Reference plan: plan

## Pre-checks

- [x] Confirm linked ADRs exist or are updated for architecture-impacting changes.
- [x] Confirm ownership and dependency impact in docs/context-ownership.md and docs/context-map/.
- [x] Confirm any compatibility/deprecation implications in policy docs.
- [x] Confirm architecture debt implications are recorded in docs/architecture-debt.md.

## Change steps

- [x] Implement tasks in dependency order listed for this wave.
- [x] Keep changes behind clear module/service boundaries.
- [x] Update tests and CI checks for touched architecture boundaries.

## Validation checklist

- [x] Unit/integration tests for touched domains pass.
- [x] Lint/type checks pass for touched modules.
- [x] Contract compatibility expectations are documented.
- [x] Manual smoke checks (where applicable) are completed.
- [x] Migration safety runner passes:
  `python scripts/migration_safety/run_migration_safety.py`.

## Rollback checklist

- [x] Identify feature flags/toggles or fallback paths before rollout.
- [x] Keep migration notes for reversal order.
- [x] Confirm observability signals can detect failed rollout quickly.
- [x] Rollback probe evidence captured in
  `docs/migrations/evidence/latest-migration-safety.json`.

## References

- ADR workflow: docs/adr/README.md
- Context ownership map: docs/context-ownership.md
- Context map artifacts: docs/context-map/README.md
- Contract versioning policy: docs/contracts/versioning.md
- Architecture debt register: docs/architecture-debt.md
