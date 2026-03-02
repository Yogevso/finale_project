# Refactor Wave Migration Playbooks

These playbooks provide repeatable execution checklists for architecture waves.

## Playbooks

- [Wave E - Governance and Domain Mapping](./wave-e-governance-domain-mapping.md)
- [Wave F - Structural Boundaries and Enforcement](./wave-f-structural-boundaries.md)
- [Wave G - Backend Core Foundations](./wave-g-backend-core-foundations.md)
- [Wave H - Domain Model Hardening](./wave-h-domain-model-hardening.md)
- [Wave I - Workflow and Use-Case Orchestration](./wave-i-workflow-orchestration.md)
- [Wave J - Write-Path Reliability and Rollout Safety](./wave-j-write-path-reliability.md)
- [Wave K - Service and Integration Refactors](./wave-k-service-integration-refactors.md)
- [Wave L - Frontend Architecture and Contract Alignment](./wave-l-frontend-architecture-contracts.md)
- [Wave M - Testability and Scaffolding Acceleration](./wave-m-testability-scaffolding.md)
- [Wave N - Security and Resilience Validation](./wave-n-security-resilience-validation.md)
- [Wave O - Observability and Long-Horizon Evolution](./wave-o-observability-evolution.md)
- [Wave P - Audience and Company Binding](./wave-p-audience-company-binding.md)

## Completion Snapshot

As of 2026-03-01, waves `E` through `P` are complete, and Wave `Q` is active.

## Checklist Usage

For each wave:

1. complete pre-checks before implementation
2. track changes against listed task IDs
3. run validation checklist before merge
4. confirm rollback readiness for high-risk steps

## Shared References

- ADR workflow: `docs/adr/README.md`
- context ownership: `docs/context-ownership.md`
- context map: `docs/context-map/README.md`
- contract versioning: `docs/contracts/versioning.md`
- architecture debt register: `docs/architecture-debt.md`
- migration safety framework: `docs/migrations/migration-safety-framework.md`

## Operational Helpers

- Wave P draft-audience remediation dry run:
  - `python backend/scripts/draft_audience_migration_helper.py --strategy auto`
- Wave P draft-audience remediation apply:
  - `python backend/scripts/draft_audience_migration_helper.py --apply --strategy auto`
