# Internal Contract Versioning Policy

This policy applies to payload/token contracts between:

- Backend API (`backend/app/*`)
- Frontend API clients (`frontend/src/lib/api/*`)
- Collaboration server (`collab-server/src/*`)

## Version model

- Contract versions use `major.minor.patch`.
- `major`: incompatible change.
- `minor`: backward-compatible additive change.
- `patch`: backward-compatible fix/clarification.

## Compatibility rules

- Providers must support current and previous minor versions for at least one
  release cycle.
- Incompatible (`major`) changes require:
- ADR reference.
- migration notes.
- explicit rollout plan in relevant wave playbook.

## Change categories

- Add optional field: `minor`
- Add required field: `major`
- Remove field: `major`
- Rename field: `major`
- Relax validation without shape change: `patch` or `minor`
- Tighten validation that may reject prior valid payloads: `major`

## Release and migration expectations

- Every contract-affecting PR must document:
- impacted producer(s)
- impacted consumer(s)
- compatibility window
- test coverage impact
- Maintain a compatibility note in release docs/PR when crossing major versions.

## Verification guidance

- Use generated/typed client checks where available.
- Add or update contract tests when changing payload semantics.
- Validate backend/frontend/collab compatibility in CI before merge.
