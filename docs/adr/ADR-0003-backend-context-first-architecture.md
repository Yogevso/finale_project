# ADR-0003: backend-context-first-architecture

- Status: accepted
- Date: 2026-03-26
- Owners: Platform Architecture
- Related tasks: AW-1

## Context

The backend had three visible orchestration styles at the same boundary:

- route modules importing `app.web.controllers.*`
- route modules calling services directly
- route modules calling command/query handlers directly

That made the architecture look contradictory to new contributors. DDD aggregates, CQRS handlers, and layered services all existed, but there was no explicit rule for where each one belonged.

## Decision

The backend standard is now a context-first modular monolith.

- `app.api/**` and websocket entrypoints are transport adapters only.
- The public orchestration surface for backend features lives in `app.application.contexts.<context>.api`.
- DDD aggregates, command/query handlers, repositories, and services are implementation techniques inside a context, not competing top-level architectures.
- `app.web.controllers/**` is a compatibility layer only. Routes must not import it.
- Cross-context imports continue to go through context public APIs only.

## Scope

In scope:

- backend HTTP and websocket entrypoints
- context public APIs under `app.application.contexts`
- architecture fitness checks and onboarding documentation

Out of scope:

- removing all existing services
- forcing every read path through a single command/query abstraction
- immediate full rewrite of legacy adapters

## Consequences

### Benefits

- New backend code has one clear orchestration boundary.
- DDD and CQRS stay available where they help, without looking like parallel frameworks.
- Routes become thinner and easier to reason about.
- CI can prevent drift back to route-level controller imports.

### Risks

- There is still legacy service code behind some context APIs.
- Some contexts remain broader than ideal and will need future extraction work.

## Alternatives considered

- Keep the mixed patterns and document them as equal: rejected because it preserves onboarding ambiguity.
- Rewrite the backend into pure CQRS or pure layered services: rejected because it is too disruptive for the current codebase.
- Delete `app.web.controllers` immediately: rejected because compatibility wrappers reduce migration risk.

## Compatibility and migration

- Backward compatibility impact: route behavior is unchanged; controller classes remain available as wrappers.
- Migration strategy: move route orchestration into `app.application.contexts.*.api`, then keep controllers as thin adapters until callers disappear.
- Rollback strategy: restore route imports of controllers and remove the route-boundary fitness rule.

## References

- Migration playbook: `docs/migrations/wave-f-structural-boundaries.md`
- Context map: `docs/context-map/contexts.md`
- Data ownership map: `docs/context-ownership.md`
- Contract versioning policy: `docs/contracts/versioning.md`
