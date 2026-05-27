# Migration Safety Scripts

Task 118 migration safety framework runner.

Part of the Intel Documentation Platform rollout-safety tooling. Use this runner when a change could impact schema compatibility, upgrade sequencing, or rollback safety.

## Runner

- `run_migration_safety.py`

## Checks

1. preflight guards
2. dry-run upgrade validation + schema SQL artifact generation
3. rollback probe (`upgrade head -> downgrade -1 -> upgrade head`)
4. post-migration schema assertions

## Usage

```bash
python scripts/migration_safety/run_migration_safety.py
```

Custom output paths:

```bash
python scripts/migration_safety/run_migration_safety.py \
  --report-file docs/migrations/evidence/latest-migration-safety.json \
  --dry-run-sql-file docs/migrations/evidence/latest-dry-run.sql
```

## Evidence Outputs

- JSON summary report
- generated schema SQL dump artifact

## Related Docs

- [Root README](../../README.md)
- [Migration Playbooks](../../docs/migrations/README.md)
- [Deployment](../../docs/DEPLOYMENT.md)
