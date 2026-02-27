# Migration Safety Scripts

This folder provides the migration safety framework for Task 118.

## Runner

- `run_migration_safety.py`

## What it checks

1. Preflight guards
2. Dry-run upgrade validation + schema SQL dump artifact generation
3. Rollback probe (`upgrade head -> downgrade -1 -> upgrade head`)
4. Post-migration schema assertions

## Usage

From repo root:

```bash
python scripts/migration_safety/run_migration_safety.py
```

Optional output paths:

```bash
python scripts/migration_safety/run_migration_safety.py \
  --report-file docs/migrations/evidence/latest-migration-safety.json \
  --dry-run-sql-file docs/migrations/evidence/latest-dry-run.sql
```

## Evidence outputs

- JSON summary report
- Generated schema SQL dump artifact

These artifacts provide reproducible migration safety evidence for release checks.
