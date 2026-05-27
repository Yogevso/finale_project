# Adapter Boundary Chaos Suite

Task 120 staging chaos runner for adapter-boundary resilience checks.

Part of the Intel Documentation Platform operational tooling. Use this runner for controlled fault-injection checks rather than ad hoc production experimentation.

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

## Related Docs

- [Root README](../../README.md)
- [Deployment](../../docs/DEPLOYMENT.md)
- [SLO Docs](../../docs/slo/README.md)
