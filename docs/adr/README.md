# Architecture Decision Records (ADRs)

This directory stores architecture decisions that affect system boundaries,
contracts, migration strategy, or long-term operability.

## When an ADR is required

Create or update an ADR for any change that does one or more of the following:

- Introduces or changes architectural boundaries (layers, contexts, adapters).
- Changes cross-service or cross-layer contracts.
- Adds or removes long-lived infrastructure patterns (outbox, saga, bus, etc.).
- Changes migration strategy for active refactor waves (E-O).
- Introduces a deprecation path that affects compatibility windows.

## Naming convention

- File name format: `ADR-XXXX-short-title.md`
- `XXXX` is a zero-padded sequence (`0001`, `0002`, ...).
- Keep title short and concrete.

## ADR status values

- `proposed`
- `accepted`
- `superseded`
- `rejected`
- `deprecated`

## Workflow

1. Copy [template.md](./template.md) and create a new ADR file.
2. Fill all required sections, including rollback strategy.
3. Link related artifacts:
- migration playbook (`docs/migrations/*`)
- context map (`docs/context-map/*`)
- ownership map (`docs/context-ownership.md`)
- contract policy (`docs/contracts/versioning.md`)
4. Add ADR link in the pull request template.
5. Update ADR index below.

## ADR index

| ADR | Status | Date | Summary |
| --- | --- | --- | --- |
| [ADR-0001-wave-e-governance-baseline](./ADR-0001-wave-e-governance-baseline.md) | accepted | 2026-02-27 | Establishes governance artifacts and CI checks for Wave E. |
