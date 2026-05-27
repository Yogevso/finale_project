---
name: ci-cd-firefighter
description: Diagnose and fix failing GitHub Actions CI/CD checks for finale_project by mapping failed jobs to exact local reproduction commands, applying minimal code fixes, and validating before push.
---

# CI/CD Firefighter (finale_project)

Use this skill when the user reports failing CI/CD, red GitHub checks, broken PR pipeline, or deployment workflow failures.

This skill is repository-specific to `finale_project`.

## Scope

Workflows covered:

- `.github/workflows/ci.yml`
- `.github/workflows/pr-checks.yml`
- `.github/workflows/architecture-fitness.yml`
- `.github/workflows/security.yml`
- `.github/workflows/cd.yml`

## Operating rules

- Reproduce the exact failed command locally before changing code.
- Fix root cause, not symptoms.
- Do not disable tests, lower coverage thresholds, or weaken checks unless the user explicitly asks.
- Prefer the smallest safe patch.
- Re-run the failed check locally after the fix.

## Fast path

1. Identify the failing workflow, job, and step.
2. Capture the first actionable error line from logs.
3. Reproduce locally using the mapping below.
4. Patch code/config with minimal change.
5. Re-run failed command plus one adjacent guard check.
6. Summarize root cause, fix, and verification.

## 1) Find failing checks

Preferred:

- Use GitHub connector tools to fetch PR status checks and failing job logs.

Fallback (if `gh` CLI is available and authenticated):

```bash
gh pr checks <pr-number>
gh run list --branch <branch> --limit 10
gh run view <run-id> --job <job-id> --log-failed
```

If logs are unavailable, ask for the run URL.

## 2) Workflow -> local reproduction map

### CI workflow (`ci.yml`)

`migration-safety`:

```bash
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
python ../scripts/migration_safety/run_migration_safety.py
```

`backend-lint`:

```bash
cd backend
ruff check app/ tests/
ruff format app/ tests/ --check
python ../scripts/api_contracts/check_audience_error_codes.py
mypy app/ --ignore-missing-imports --no-error-summary
```

`backend-tests`:

```bash
cd backend
mkdir -p data uploads
APP_ENV=testing SECRET_KEY=test-secret-key-for-ci DATABASE_URL=sqlite:///./data/test.db \
pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=70 -v
```

`frontend-lint`:

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
```

`frontend-tests`:

```bash
cd frontend
npm ci
npm run test -- --run
```

`frontend-build`:

```bash
cd frontend
npm ci
npm run generate:api-contracts:check
npx vite build
```

`collab-quality`:

```bash
cd collab-server
npm ci
npm run lint
npm run test
```

`performance-gates`:

- Reproduce only when this exact job fails.
- Start with the specific failing sub-step log (backend perf gate, protocol gate, or seed/startup failures).
- Use the same env vars as in `.github/workflows/ci.yml`.

`e2e-core`, `e2e-roles`, `e2e-features`:

- Reproduce only failing spec(s), not all suites.

```bash
cd frontend
npx playwright test e2e/<failing-spec>.ts --reporter=github
```

### Architecture fitness (`architecture-fitness.yml`)

```bash
python scripts/architecture_checks/check_backend_architecture.py
python scripts/architecture_checks/check_exception_policy_annotations.py
python scripts/architecture_checks/check_collab_architecture.py
python scripts/architecture_checks/check_frontend_feature_dependencies.py
python scripts/architecture_checks/check_route_db_access.py
python scripts/architecture_checks/check_route_sql_usage.py
python scripts/architecture_checks/query_plans.py
python backend/scripts/tech_debt_budget.py --budget 200 --delta-only --max-new 0
python scripts/architecture_checks/check_refactor_budget.py
```

### PR automation (`pr-checks.yml`)

- `size-check`, `title-check`, `labeler` usually fail on PR metadata, not app code.
- If failing:
  - validate PR title format (`type(scope): subject` or `type: subject`)
  - reduce oversized PR when practical
  - ensure `.github/labeler.yml` paths are valid when labeler fails

### Security (`security.yml`)

Dependency scan failures:

```bash
cd backend && pip-audit -r requirements.txt
cd frontend && npm audit --audit-level=high
cd collab-server && npm audit --audit-level=high
```

Container scan failures:

```bash
docker build -t scan-backend ./backend
docker build -t scan-frontend ./frontend
docker build -t scan-collab ./collab-server
```

If vulnerability exists:

- prefer upgrading dependency/image
- if false positive is proven, document explicit ignore with justification

### CD (`cd.yml`)

- `cd.yml` reuses `ci.yml` through the `test` job. Fix CI failures first.
- Build failures: reproduce Docker build for failing service.
- Deploy failures: usually secrets/env/remote-host issues, not code.

Required deployment variables/secrets are documented in:

- `.github/CICD_DOCUMENTATION.md`
- `.github/workflows/cd.yml`

## 3) Minimal validation before push

Choose checks by touched area:

- `backend/**` changed:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && pytest tests/<affected> -q`
- `frontend/**` changed:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run test -- --run <affected-test>`
  - `cd frontend && npm run generate:api-contracts:check`
- `collab-server/**` changed:
  - `cd collab-server && npm run lint && npm run test`
- workflow or architecture scripts changed:
  - run the exact impacted script locally

When uncertain, run the same command that failed in CI end-to-end.

## 4) Output format to user

Always return:

- Failing check: workflow / job / step
- Root cause: one clear sentence
- Fix applied: file(s) + what changed
- Verification: commands rerun and result
- Residual risk: anything not yet validated

## 5) Anti-patterns

- Blindly rerunning pipeline without local repro
- Pushing speculative fixes without tests
- Hiding failures via `continue-on-error` edits
- Mixing unrelated refactors into CI-fix PR
