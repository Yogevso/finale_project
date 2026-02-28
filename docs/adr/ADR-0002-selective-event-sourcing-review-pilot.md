# ADR-0002: Selective Event-Sourcing Review Workflow Pilot

- Status: accepted
- Date: 2026-02-28
- Owners: Engineering
- Related tasks: 90

## Context

Wave O requires evaluating whether event sourcing is worth adopting for
high-complexity workflows. The codebase already uses domain events and outbox,
but write paths are still state-mutation first in relational tables.

A full-system event-sourcing migration would be high-risk. A bounded pilot is
needed to measure tradeoffs before any broader adoption.

## Decision

Approve a selective pilot for the review workflow only, implemented as a
feature-flagged shadow path:

- New append-only event store abstraction (`app.event_store`).
- Pilot review stream model (`review_workflow:{review_id}`) with events:
  - `review_submitted`
  - `review_approved`
  - `review_rejected`
  - `review_cancelled`
- Replay projection to reconstruct review lifecycle state.
- Optimistic concurrency checks on append operations.
- Feature flag gate: `FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT` (default `false`).

The relational model remains source-of-truth. The pilot exists to validate
operational and modeling fitness, not to replace current persistence yet.

## Go/No-Go Criteria

Go beyond pilot only if all criteria are met:

1. Replay parity: projected lifecycle status matches relational status for pilot
   sample sets.
2. Operational overhead: on-call burden does not increase materially (no
   sustained critical incidents attributable to event-store path).
3. Performance: append + replay overhead remains within agreed budgets for pilot
   read/write paths.
4. Team ergonomics: handlers/tests remain understandable and maintainable.

No-go if any criterion fails or cannot be measured reliably.

## Measured Tradeoffs

### Benefits

- Immutable review history enables deterministic replay and timeline debugging.
- Optimistic concurrency makes stale write races explicit.
- Event-first model clarifies legal transition boundaries.

### Costs/Risks

- Additional storage and projection logic to operate.
- Dual-model complexity during pilot (relational + event stream).
- New failure modes if event append/parity checks drift from relational writes.

## Alternatives considered

- Full event sourcing for all write domains.
  Rejected due migration and operational risk.
- Keep current relational-only model.
  Rejected because it does not answer feasibility questions for high-change
  workflows.

## Compatibility and migration

- Backward compatibility: no API contract change in pilot phase.
- Migration strategy: run pilot in shadow mode; gather evidence before any
  source-of-truth change.
- Rollback strategy: set `FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT=false` and
  stop shadow appends immediately.

## References

- Feature flags: `backend/app/feature_flags.py`
- Pilot implementation: `backend/app/event_store/`
- Pilot tests: `backend/tests/test_event_store_pilot.py`
