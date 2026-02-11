# Project Domain Playbook

## Domain-Specific Output Anchors

Use these anchors to make capability specs implementation-ready.

### Backend

- Typical scope:
- API endpoints, request/response schemas, service logic, auth/permissions, persistence.
- Strong acceptance checks:
- Contract: success + validation + authorization failures.
- Data: migration/schema compatibility and rollback safety.
- Reliability: timeout/retry/error mapping behavior.

### Frontend

- Typical scope:
- Pages/components, state management, API integration, interaction flow.
- Strong acceptance checks:
- UX states: loading, empty, error, success.
- Accessibility: keyboard flow and semantic labeling.
- Responsiveness: mobile + desktop behavior without layout break.

### DevOps

- Typical scope:
- Container/runtime config, env vars, deployment scripts, observability, health checks.
- Strong acceptance checks:
- Startup/health probes succeed.
- Config validation (required env present, invalid env fails fast).
- Rollback path is documented and testable.

### Full-Stack

- Structure the capability as three tracks:
1. Backend contract and data behavior.
2. Frontend consumption and UX behavior.
3. Integration verification and operational checks.

## Capability Quality Hints

- Prefer explicit path patterns in `Deliverables` (example: `backend/app/...`, `frontend/src/...`).
- Require at least one command category in `Deliverables` (test/lint/build/check).
- Keep each acceptance test independently executable.
