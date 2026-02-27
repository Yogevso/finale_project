# ADR-0001: Wave E Governance Baseline

- Status: accepted
- Date: 2026-02-27
- Owners: Engineering
- Related tasks: 91, 92, 96, 97, 104, 115, 121

## Context

Wave E introduces cross-cutting architecture governance requirements. Before
continuing deeper refactors, the project needs a single process for decisions,
deprecations, migration playbooks, ownership boundaries, and architecture debt
visibility in CI.

## Decision

Adopt a governance baseline composed of:

- ADR workflow and template in `docs/adr/`.
- Deprecation lifecycle policy and active register in `docs/deprecation-policy.md`
  and `docs/deprecations.md`.
- Wave migration playbooks in `docs/migrations/`.
- Contract versioning policy in `docs/contracts/versioning.md`.
- Data ownership and context map artifacts in `docs/context-ownership.md` and
  `docs/context-map/`.
- Architecture debt register with CI reporting in
  `docs/architecture-debt.md` and `scripts/architecture_debt_checks/`.

## Scope

In scope:

- Documentation and CI governance controls.
- PR/contributor process updates to enforce usage.

Out of scope:

- Full architectural refactor implementation (Waves F-O).
- Runtime feature changes unrelated to governance.

## Consequences

### Benefits

- Architecture decisions become durable and reviewable.
- Compatibility/deprecation risk is explicit and trackable.
- Migration and ownership boundaries are easier to execute and audit.
- High-risk architecture debt is visible in CI reporting.

### Risks

- Additional process overhead for architecture-heavy pull requests.
- Governance docs can drift if not kept current in each wave.

## Alternatives considered

- Keep decisions in PR threads only.
  Rejected because rationale is fragmented and hard to audit later.
- Delay governance until after major refactors.
  Rejected because refactor risk increases without guardrails.

## Compatibility and migration

- Backward compatibility impact: none directly.
- Migration strategy: adopt docs and workflow immediately for Wave E onward.
- Rollback strategy: governance artifacts are additive and can be revised without
  runtime rollback.

## References

- Migration playbook: `docs/migrations/wave-e-governance-domain-mapping.md`
- Context map: `docs/context-map/README.md`
- Data ownership map: `docs/context-ownership.md`
- Contract versioning policy: `docs/contracts/versioning.md`
