# Architecture Fitness Checks

Structural checks used by architecture governance and CI fitness gates.

Part of the Intel Documentation Platform quality tooling. These checks enforce architectural boundaries that the repo expects contributors to keep intact.

## Checks

- `check_backend_architecture.py`
  - validates backend layer/context package layout
  - enforces import rules across `domain/application/infrastructure/web`
  - enforces cross-context imports through context public APIs
  - blocks route-layer imports of `app.web.controllers.*`
  - keeps `app.application.contexts.*.api` as the public orchestration boundary
  - enforces aggregate-repository usage in the users/support/comment/version/auth write paths
- `check_collab_architecture.py`
  - validates collab layer/port/adapter layout
  - blocks direct transport bypass patterns
- `check_frontend_feature_dependencies.py`
  - enforces frontend feature dependency rules
  - blocks deep cross-feature imports
- `check_route_db_access.py`
  - blocks new direct `db.query(...)` usage in routes
  - uses baseline file for accepted legacy debt
- `check_exception_policy_annotations.py`
  - requires every `except Exception` in `backend/app` to declare an inline `# policy: ...`
  - keeps broad catches explicit instead of silently swallowing unexpected failures
  - allowed policies: `BOUNDARY`, `COMPENSATING`, `DEGRADED`, `FAIL_FAST`, `LOSSY`, `RETRYABLE`
- `check_refactor_budget.py`
  - enforces changed-lines/touched-files/per-file budgets
  - supports expiring override records

## Route DB Baseline Workflow

```bash
python scripts/architecture_checks/check_route_db_access.py --update-baseline
```

Then commit `baselines/route_db_access_baseline.txt`.

## Refactor Budget Override Workflow

Add entries in `refactor_budget_overrides.json`:

- `glob`
- `owner`
- `reason`
- `expires_on` (`YYYY-MM-DD`)

Expired overrides are ignored automatically.

## Related Docs

- [Root README](../../README.md)
- [Architecture](../../docs/ARCHITECTURE.md)
- [ADRs](../../docs/adr/README.md)
