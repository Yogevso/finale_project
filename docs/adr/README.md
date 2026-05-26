# Architecture Decision Records (ADRs)

This directory stores architecture decisions that affect boundaries, contracts, migration strategy, or long-term operability.

Part of the Intel Documentation Platform documentation set. ADRs are the durable record for architectural decisions that should outlive a single pull request or migration wave.

## ADR Required When

Create or update an ADR when a change:

- introduces or changes architectural boundaries (layers, contexts, adapters)
- changes cross-service or cross-layer contracts
- adds or removes long-lived infrastructure patterns
- changes migration strategy for active refactor waves
- introduces a deprecation path affecting compatibility windows

## Naming Convention

- file format: `ADR-XXXX-short-title.md`
- `XXXX` is zero-padded sequence (`0001`, `0002`, ...)

## ADR Status Values

- `proposed`
- `accepted`
- `superseded`
- `rejected`
- `deprecated`

## Workflow

1. copy [template.md](./template.md) to a new ADR file
2. fill all sections, including rollback strategy
3. link related artifacts:
   - migration playbook (`docs/migrations/*`)
   - context map (`docs/context-map/*`)
   - ownership map (`docs/context-ownership.md`)
   - contract policy (`docs/contracts/versioning.md`)
4. include ADR reference in pull request context
5. update ADR index below

## ADR Index

| ADR | Status | Date | Summary |
| --- | --- | --- | --- |
| [ADR-0001-wave-e-governance-baseline](./ADR-0001-wave-e-governance-baseline.md) | accepted | 2026-02-27 | Governance baseline for Wave E. |
| [ADR-0002-selective-event-sourcing-review-pilot](./ADR-0002-selective-event-sourcing-review-pilot.md) | accepted | 2026-02-28 | Feature-flagged review workflow event-sourcing pilot decision. |
| [ADR-0003-backend-context-first-architecture](./ADR-0003-backend-context-first-architecture.md) | accepted | 2026-03-26 | Standardize backend orchestration on context public APIs and block route-level controller imports. |
| [ADR-0004-aggregate-repository-boundaries](./ADR-0004-aggregate-repository-boundaries.md) | accepted | 2026-03-26 | Repositories are mandatory for aggregate-heavy write domains, not all projections. |

## Related Docs

- [Root README](../../README.md)
- [Architecture](../ARCHITECTURE.md)
- [Migration Playbooks](../migrations/README.md)
