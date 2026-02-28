# Documentation Platform

Multi-tenant document platform with a FastAPI backend, React frontend, and a Hocuspocus collaboration server.

## Current Status

As of 2026-02-28:

- Refactor waves `E` through `O` are complete.
- Architecture governance, migration safety, contract testing, and resilience/chaos checks are in place.
- Wave O observability is implemented:
  - use-case telemetry/tracing
  - SLO evaluation
  - burn-rate alert evaluation
  - scheduled SLO evidence workflow
- Selective event-sourcing pilot (review workflow) is implemented behind a feature flag.

## Repository Layout

- `backend/`: FastAPI app, domain/application layers, persistence, tests
- `frontend/`: React + TypeScript SPA
- `collab-server/`: Hocuspocus real-time editing server
- `docs/`: ADRs, migration playbooks, architecture docs, SLO and chaos evidence
- `scripts/`: migration safety, chaos, observability, scaffolding tools
- `plan`: active execution plan and wave progress log

## Quick Start

### Docker Compose

```bash
docker compose up -d
```

Endpoints:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/api/v1/docs`
- Collab WS: `ws://localhost:8002`

### Local Development

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Collab server:

```bash
cd collab-server
npm install
npm run dev
```

## Validation Commands

Backend targeted checks:

```bash
docker compose run --rm backend ruff check app/ tests/
docker compose run --rm backend pytest tests/ -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm run test -- --run
```

Collab server:

```bash
cd collab-server
npm run typecheck
npm run test
```

Wave O SLO evaluation:

```bash
python scripts/observability/evaluate_slo_burn_rate.py \
  --telemetry-file docs/slo/samples/sample-telemetry.json \
  --slo-file docs/slo/use-case-slos.json \
  --report-file docs/slo/evidence/latest-slo-burn-rate-report.json \
  --fail-on-critical
```

## CI/CD Workflows

Primary workflows in `.github/workflows/`:

- `ci.yml`: lint, tests, contracts, migration safety, E2E
- `cd.yml`: image build/deploy with staging chaos gate
- `staging-chaos.yml`: scheduled/manual adapter-boundary chaos suite
- `slo-burn-rate.yml`: scheduled/manual SLO and burn-rate evaluation
- `architecture-fitness.yml`: architecture boundary checks
- `architecture-governance.yml`: architecture debt/governance checks

## Key Documentation

- [Execution plan](./plan)
- [Migration playbooks](./docs/migrations/README.md)
- [ADRs](./docs/adr/README.md)
- [Feature rollout flags](./docs/feature-rollout-flags.md)
- [SLO docs](./docs/slo/README.md)
- [Chaos suite docs](./scripts/chaos/README.md)

## License

MIT. See [LICENSE](./LICENSE).
