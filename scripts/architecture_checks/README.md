# Architecture Fitness Checks

This directory contains structural checks used by Wave F guardrails.

## Checks

- `check_backend_architecture.py`
  - Verifies backend layer/context package layout exists.
  - Enforces import rules for new `domain/application/infrastructure/web` modules.
  - Enforces cross-context imports through context public APIs.
- `check_collab_architecture.py`
  - Verifies collab ports/adapters/layer layout.
  - Prevents direct axios usage in `src/persistence.ts` (must go through adapter).
- `check_frontend_feature_dependencies.py`
  - Enforces frontend dependency boundaries.
  - Blocks `components`/`lib` imports from `pages`.
  - Enforces feature-to-feature imports through feature public entrypoints.
- `check_route_db_access.py`
  - Prevents new direct `db.query(...)` in route modules.
  - Uses baseline file `baselines/route_db_access_baseline.txt` to track legacy debt.
- `check_refactor_budget.py`
  - Applies changed-lines/touched-files/per-file/branching budgets to diffs.
  - Supports explicit override records with owner/reason/expiry.

## Route DB baseline workflow

Regenerate baseline only when explicitly accepting current debt snapshot:

```bash
python scripts/architecture_checks/check_route_db_access.py --update-baseline
```

Then commit `baselines/route_db_access_baseline.txt`.

## Refactor budget override workflow

Add an entry to `refactor_budget_overrides.json` with:

- `glob` (path glob, or `__GLOBAL__` for global threshold override)
- `owner`
- `reason`
- `expires_on` (`YYYY-MM-DD`)

Expired overrides are ignored automatically.
