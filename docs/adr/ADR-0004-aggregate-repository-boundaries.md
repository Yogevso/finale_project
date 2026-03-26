# ADR-0004: aggregate-repository-boundaries

- Status: accepted
- Date: 2026-03-26
- Owners: Platform Architecture
- Related tasks: AW-4

## Context

The codebase had a repository layer, but it was only used in some domains. That left an unclear abstraction boundary:

- comments, versions, invitations, and auth used repositories
- other aggregate-heavy write domains still embedded ORM queries in services or context APIs
- projection-style and admin-style read paths also lived next to aggregate mutation logic

That made the repository layer look vestigial instead of intentional.

## Decision

Repositories are now defined as the persistence boundary for aggregate-heavy write domains, not as a blanket rule for every query in the system.

- Aggregate owners should use repositories for transactional entity access and mutation orchestration.
- Projection-heavy read paths, analytics/reporting, and one-off admin dashboards may still query directly when no aggregate repository exists.
- Users, invitations, comments, versions, documents, and support tickets are repository-backed domains.
- Services and context APIs in those domains should depend on repositories instead of reimplementing aggregate queries inline.

## Scope

In scope:

- aggregate-heavy backend write paths
- repository-backed bounded contexts and services
- architecture fitness rules for repository-backed domains

Out of scope:

- forcing all analytics/reporting endpoints through repositories
- creating repositories for every model/table
- eliminating all direct SQLAlchemy usage from the backend

## Consequences

### Benefits

- The repository layer has a clear purpose instead of looking abandoned.
- Aggregate services become easier to test and refactor.
- Projection code is still free to optimize reads without artificial wrappers.

### Risks

- Repository boundaries can become too thin if they only mirror raw ORM calls.
- Some direct-query services remain and still need judgment about whether they are projections or missing repositories.

## Alternatives considered

- Require repositories everywhere: rejected because it adds low-value wrappers around analytics and projection code.
- Delete repositories and use services only: rejected because aggregate write paths benefit from a stable persistence boundary.
- Keep the current mixed usage without policy: rejected because it preserves the inconsistency that caused this finding.

## Compatibility and migration

- Backward compatibility impact: none at the API level.
- Migration strategy: move aggregate-heavy domains onto repositories first, then enforce targeted fitness rules for those domains.
- Rollback strategy: revert repository migrations and remove repository-boundary fitness checks.

## References

- Migration playbook: `docs/migrations/wave-f-structural-boundaries.md`
- Context map: `docs/context-map/contexts.md`
- Data ownership map: `docs/context-ownership.md`
- Contract versioning policy: `docs/contracts/versioning.md`
