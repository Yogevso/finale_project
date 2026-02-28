# Backend

FastAPI backend for the Documentation Platform.

## Highlights

- Multi-tenant API surface (`management`, `portal`, `public`, `bff` routes)
- Layered architecture (`domain`, `application`, `infrastructure`, `web`)
- CQRS-lite handlers, command/query bus middleware, and process managers
- Durable outbox, idempotency, optimistic concurrency, projection cache
- Policy decision point and policy explanation model
- Observability primitives (use-case telemetry, SLOs, burn-rate checks)
- Selective event-sourcing pilot for review workflow (feature-flagged)

## Important Paths

- `app/api/`: FastAPI route modules
- `app/application/`: command/query handlers, bus/pipeline orchestration
- `app/domain/`: aggregates, value objects, specifications, workflows
- `app/infrastructure/`: adapters and persistence-facing components
- `app/observability/`: telemetry, SLO, burn-rate models
- `app/event_store/`: event-sourcing pilot components
- `tests/`: backend tests (unit/integration/contracts/security/resilience)

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:

- `http://localhost:8000/api/v1/docs`
- `http://localhost:8000/api/v1/redoc`

## Key Environment Flags

Architecture rollout and rollback flags:

- `FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE`
- `FEATURE_FLAG_PROJECTION_CACHE`
- `FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT`

See full guidance: `../docs/feature-rollout-flags.md`.

## Quality Gates

Lint and format:

```bash
ruff check app/ tests/
ruff format app/ tests/ --check
```

Targeted Wave O checks:

```bash
pytest tests/test_use_case_telemetry.py tests/test_observability_slo.py tests/test_event_store_pilot.py tests/test_feature_flags.py -q
```

Full backend tests:

```bash
pytest tests/ -v
```

## Related Docs

- `../docs/adr/`
- `../docs/migrations/`
- `../docs/slo/`
- `../scripts/migration_safety/README.md`
- `../scripts/chaos/README.md`
