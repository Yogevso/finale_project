# Adapter Boundary Chaos Suite

Task 120 staging chaos runner for adapter-boundary resilience checks.

## Runner

- `run_adapter_boundary_chaos.py`

The runner executes controlled fault-injection suites for:

1. backend adapter boundary scenarios
2. collab-server adapter/transport scenarios

Evidence output:

- `docs/chaos/evidence/latest-adapter-chaos-report.json`

## Local Usage

```bash
python scripts/chaos/run_adapter_boundary_chaos.py
```

Backend-only:

```bash
python scripts/chaos/run_adapter_boundary_chaos.py --skip-collab
```

## CI Usage

- `.github/workflows/staging-chaos.yml`
- staging gate in `.github/workflows/cd.yml`
