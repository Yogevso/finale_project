# Use-Case SLO and Burn-Rate Checks

Wave O observability evaluator scripts:

Part of the Intel Documentation Platform observability tooling. These scripts evaluate use-case telemetry against the checked-in SLO contract and produce evidence artifacts.

- Task 98: use-case SLO evaluation
- Task 119: burn-rate alert evaluation and evidence export

## Script

- `evaluate_slo_burn_rate.py`

## Usage

```bash
python scripts/observability/evaluate_slo_burn_rate.py \
  --telemetry-file docs/slo/samples/sample-telemetry.json \
  --slo-file docs/slo/use-case-slos.json \
  --report-file docs/slo/evidence/latest-slo-burn-rate-report.json
```

Fail on critical alerts:

```bash
python scripts/observability/evaluate_slo_burn_rate.py \
  --telemetry-file docs/slo/samples/sample-telemetry.json \
  --fail-on-critical
```

Telemetry input can use:

- absolute `started_at`
- relative `minutes_ago` (resolved at evaluation time)

## CI Scheduling

- workflow: `.github/workflows/slo-burn-rate.yml`
- evidence output: `docs/slo/evidence/latest-slo-burn-rate-report.json`

## Related Docs

- [Root README](../../README.md)
- [SLO Docs](../../docs/slo/README.md)
- [Deployment](../../docs/DEPLOYMENT.md)
