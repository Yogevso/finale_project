# Deprecation Lifecycle Policy

This policy defines how APIs, modules, and internal contracts are retired.

## Lifecycle stages

1. `proposed`
- Candidate for deprecation.
- No user-facing warning yet.
- Must include owner and rationale in `docs/deprecations.md`.

2. `deprecated`
- Officially deprecated.
- Replacement path documented.
- Release notes and docs updated.

3. `warned`
- Runtime and/or build-time warnings are active where applicable.
- Final compatibility window countdown is active.

4. `removed`
- Deprecated surface removed from code paths.
- Register row retained for historical audit.

## Required metadata per deprecation

Every deprecation entry in `docs/deprecations.md` must include:

- `ID`
- `Component`
- `Replacement`
- `Stage`
- `Owner`
- `Announced`
- `Warn From`
- `Removal Target`
- `Notes`

The owner is accountable for communication, migration support, and removal.

## Compatibility window rules

- Minimum target window: two minor releases or 60 days, whichever is longer.
- Breaking removals must reference an ADR if architecture-impacting.
- Contract changes must follow `docs/contracts/versioning.md`.

## Runtime and CI markers

- Runtime markers:
- Backend: warnings in logs/headers where practical.
- Frontend/collab: warning logs or typed annotations where practical.
- CI marker:
- `scripts/architecture_debt_checks/check_deprecations_register.py` validates
  required metadata and reports active deprecations in CI summary output.

## Communication requirements

- Document migration path before stage changes to `warned`.
- Mention deprecations in release notes and PR descriptions.
- Link relevant playbook/ADR/context artifacts for architecture-level changes.
