# Use-Case SLO Definitions

Wave O observability artifacts for:

Part of the Intel Documentation Platform observability documentation. This directory defines the SLO contract consumed by local checks, CI, and alert-response workflows.

- Task 98: use-case performance SLOs
- Task 119: use-case burn-rate alerts and escalation runbook

## Files

- `use-case-slos.json`: authoritative SLO and burn-rate threshold config
- `samples/sample-telemetry.json`: sample telemetry for local/CI checks
- `runbook-burn-rate.md`: alert response playbook
- `evidence/`: machine-generated reports

## Evaluation Command

```bash
python scripts/observability/evaluate_slo_burn_rate.py \
  --telemetry-file docs/slo/samples/sample-telemetry.json \
  --slo-file docs/slo/use-case-slos.json \
  --report-file docs/slo/evidence/latest-slo-burn-rate-report.json \
  --fail-on-critical
```

## Telemetry Contract

Events include:

- `use_case_id` (for example `command.approvereviewcommand`)
- `use_case_kind` (`command` or `query`)
- `outcome` (`success` or `failure`)
- `duration_ms`
- `started_at` (ISO-8601) or `minutes_ago`
- optional `dimensions`

Compatible with backend emitters in `app.observability.telemetry`.

## Related Docs

- [Root README](../../README.md)
- [Observability Scripts](../../scripts/observability/README.md)
- [Deployment](../DEPLOYMENT.md)
