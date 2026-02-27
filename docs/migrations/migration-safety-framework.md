# Migration Safety Framework

Task 118 introduces a repeatable migration safety framework for schema and architecture changes.

## Runner

Use the centralized runner:

```bash
python scripts/migration_safety/run_migration_safety.py
```

## Safety stages

1. Preflight guards
2. Dry-run upgrade validation + schema SQL dump generation
3. Rollback probe (`upgrade head -> downgrade -1 -> re-upgrade head`)
4. Post-migration assertions

## Evidence artifacts

Default outputs:

- `docs/migrations/evidence/latest-migration-safety.json`
- `docs/migrations/evidence/latest-dry-run.sql`

These artifacts are reproducible and can be attached to release candidate validation.

## Release checklist integration

Before release or high-risk merge:

1. Run migration safety runner.
2. Confirm all stages pass in JSON report.
3. Review dry-run SQL artifact for expected operations.
4. Record any deviations in wave migration notes.

## High-risk migration policy

Migrations that include table/column DDL are treated as high risk and are included in the evidence report under `high_risk_revisions`.
