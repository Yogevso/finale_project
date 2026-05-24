# OPS / RELEASE-READINESS AUDIT - 2026-03-26

## 1. Goal

This audit focuses on operational readiness rather than code quality.

Scope:

- deploy path
- rollback path
- migration execution and recovery safety
- environment/config parity
- backup and restore readiness

This is the right follow-up audit after the codebase-level excellence work reached a clean baseline.

## 2. Current Rating

| Area                  | Current Rating | Why it is not 10/10 yet                                                                                    |
| --------------------- | -------------- | ---------------------------------------------------------------------------------------------------------- |
| Deploy automation     | 6.4/10         | CI/CD build quality is strong, but deployment and rollback are still mostly placeholders                   |
| Environment parity    | 6.8/10         | Runtime, compose, and examples/docs still drift in a few production-critical places                        |
| Migration readiness   | 8.8/10         | Migration safety is materially better than average, but production rollback/backup posture is still uneven |
| Backup / recovery     | 7.2/10         | Useful scripts exist, but they are SQLite-centric and not integrated into production validation            |
| Overall ops readiness | 7.3/10         | Strong engineering base, but not yet a turnkey production operations base                                  |

## 3. Bottom Line

The codebase is in a strong state, but the repository is **not yet a 10/10 operational base**.

The biggest gaps are not in application logic. They are in:

1. real deployment execution
2. real rollback execution
3. production config parity
4. production bootstrap safety

## 4. Findings Summary

| ID    | Severity | Area                        | Title                                                                                                                               |
| ----- | -------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| OR-01 | HIGH     | CD / Release                | Deployment workflow is example-only and rollback is a stub                                                                          |
| OR-02 | HIGH     | Production Config           | `docker-compose.prod.yml` cannot satisfy the backend's production rate-limit requirement as written                                 |
| OR-03 | HIGH     | Production Bootstrap        | Fresh production boot seeds demo users and sample data with known passwords                                                         |
| OR-04 | HIGH     | Release Artifact Chain      | The collab server is missing from the CD build/deploy chain, and frontend image builds do not inject the collab URL                 |
| OR-05 | MEDIUM   | Env / Docs Parity           | Ops examples still use stale names like `JWT_SECRET` and `VITE_COLLAB_WS_URL`                                                       |
| OR-06 | MEDIUM   | Backup / Recovery           | Backup, restore, and DR validation are mostly SQLite-oriented rather than production PostgreSQL-oriented                            |
| OR-07 | MEDIUM   | Secrets / Rotation          | The documented JWT rotation grace-period procedure is not implemented by runtime config                                             |
| OR-08 | MEDIUM   | Frontend Production Runtime | The production frontend image/config path is likely inconsistent with the unprivileged nginx base and needs a real smoke validation |

## 5. Detailed Findings

### OR-01 - Deployment workflow is example-only and rollback is a stub

- Severity: HIGH
- Evidence:
  - `.github/workflows/cd.yml`
- What is wrong:
  - The staging and production deploy steps still contain commented example `ssh` / `docker compose` commands instead of an executable deployment path.
  - The staging and production health checks are also commented examples.
  - The rollback job is a placeholder with `# Add rollback logic here`.
- Why this matters:
  - The repo can build images, but it does not yet provide a real release mechanism.
  - This means deployment success still depends on out-of-band operator behavior, not a repeatable audited path.
- Done when:
  - deploy jobs execute a real remote rollout path
  - post-deploy health checks are real
  - rollback takes an explicit target version/image and is executable

### OR-02 - `docker-compose.prod.yml` cannot satisfy the backend's production rate-limit requirement as written

- Severity: HIGH
- Evidence:
  - `docker-compose.prod.yml`
  - `backend/app/config.py`
- What is wrong:
  - Production compose sets `RATE_LIMIT_ENABLED=true`.
  - Backend runtime rejects production startup when rate limiting is enabled without `REDIS_URL`.
  - The backend service in `docker-compose.prod.yml` does not pass `REDIS_URL` at all.
- Why this matters:
  - The documented production compose path contains a startup blocker.
  - This is not a theoretical gap; it is a concrete env/config mismatch in the main production deployment file.
- Done when:
  - production compose passes `REDIS_URL` to the backend
  - deployment docs explicitly describe the production Redis requirement
  - production path is smoke-validated with the actual compose file

### OR-03 - Fresh production boot seeds demo users and sample data with known passwords

- Severity: HIGH
- Evidence:
  - `backend/docker-entrypoint.sh`
  - `backend/seed_data.py`
- What is wrong:
  - On empty databases, the backend entrypoint always runs `seed_data.py`.
  - The seed script creates fixed demo accounts like `sysadmin`, `admin`, `manager`, `editor`, `viewer`, and customer users with known passwords.
  - This behavior is not gated away from production startup.
- Why this matters:
  - A fresh production environment should never auto-create demo users and sample content.
  - This is a release-readiness and security problem at bootstrap time, not a dev-only convenience issue.
- Done when:
  - seeding is disabled by default in production
  - any bootstrap path requires an explicit one-time flag or admin-init procedure
  - production startup path is documented without demo-user creation

### OR-04 - The collab server is missing from the CD build/deploy chain, and frontend image builds do not inject the collab URL

- Severity: HIGH
- Evidence:
  - `.github/workflows/cd.yml`
- What is wrong:
  - CD builds and pushes backend and frontend images, but not the collab-server image.
  - The deploy jobs only talk about backend and frontend images.
  - The frontend build job injects `VITE_API_URL`, but not `VITE_COLLAB_SERVER_URL`.
- Why this matters:
  - The application is now operationally dependent on the collaboration service.
  - A production release pipeline that excludes that service is incomplete.
  - Even if collab is running separately, the frontend image build path is not wiring the collaboration endpoint at build time.
- Done when:
  - CD builds, scans, and publishes a collab-server image
  - deploy jobs roll out collab-server alongside backend/frontend where required
  - frontend production build path includes `VITE_COLLAB_SERVER_URL`

### OR-05 - Ops examples still use stale names like `JWT_SECRET` and `VITE_COLLAB_WS_URL`

- Severity: MEDIUM
- Evidence:
  - `collab-server/.env.example`
  - `collab-server/README.md`
  - `.env.example`
  - `collab-server/src/authContext/collaborationAuthService.ts`
  - `frontend/src/lib/collaboration/collaborationRuntime.ts`
- What is wrong:
  - Collab docs/examples still tell operators to configure `JWT_SECRET`, while runtime now prefers `SECRET_KEY` and only supports `JWT_SECRET` as legacy fallback.
  - Root `.env.example` still uses `VITE_COLLAB_WS_URL`, while frontend runtime expects `VITE_COLLAB_SERVER_URL`.
- Why this matters:
  - This is exactly the kind of drift that creates "works in repo, fails in environment" incidents.
  - The examples are part of the deployment surface.
- Done when:
  - env examples and READMEs use the runtime-preferred names
  - legacy names are clearly marked as compatibility-only if kept at all

### OR-06 - Backup, restore, and DR validation are mostly SQLite-oriented rather than production PostgreSQL-oriented

- Severity: MEDIUM
- Evidence:
  - `backend/alembic/env.py`
  - `backend/scripts/disaster_recovery_validation.py`
  - `backend/scripts/backup_restore_drill.py`
  - `docs/DEPLOYMENT.md`
- What is wrong:
  - Alembic pre-migration backups are implemented only for SQLite.
  - DR validation and restore-drill scripts are built around SQLite files and `data/backups`.
  - Production docs recommend PostgreSQL, but the operational automation does not provide equivalent PostgreSQL restore validation.
- Why this matters:
  - Migration safety is good for local/SQLite paths, but production recovery confidence is weaker than it looks.
  - Manual `pg_dump` commands in docs are not the same as an exercised restore path.
- Done when:
  - PostgreSQL backup/restore/runbook procedures are first-class
  - production restore validation is scripted and exercised
  - release readiness includes a real PostgreSQL restore drill

### OR-07 - The documented JWT rotation grace-period procedure is not implemented by runtime config

- Severity: MEDIUM
- Evidence:
  - `backend/scripts/rotate_secrets.py`
  - `backend/app/config.py`
- What is wrong:
  - The rotation script instructs operators to use `SECRET_KEY_OLD` during a grace period.
  - Runtime config does not expose or consume `SECRET_KEY_OLD`.
- Why this matters:
  - A runbook that cannot actually be honored by the app is dangerous.
  - Operators will believe they have a safe rotation path when they do not.
- Done when:
  - either runtime supports dual-key verification during rotation
  - or the script/runbook is corrected to match actual supported behavior

### OR-08 - The production frontend image/config path is likely inconsistent with the unprivileged nginx base and needs a real smoke validation

- Severity: MEDIUM
- Evidence:
  - `frontend/Dockerfile`
  - `frontend/nginx.conf`
  - `docker-compose.prod.yml`
- What is wrong:
  - The frontend image uses `nginxinc/nginx-unprivileged`.
  - The nginx config listens on ports `80` and `443` and expects in-container TLS certificates.
  - The production compose file maps `80:80` and `443:443`.
- Why this matters:
  - This path is likely to require extra runtime capability or a different listen/mapping strategy than the current files show.
  - At minimum, it is not validated in CI, so the repo does not prove that the production frontend container boots as configured.
- Done when:
  - the production frontend container is smoke-tested with its actual nginx config
  - port/certificate strategy is validated and documented

## 6. Strengths

This is not a weak ops base overall. Important things are already in place:

- CI is strong and broad, including migration safety and large test coverage.
- Health and readiness endpoints exist and are wired into Docker health checks.
- Migration safety has an actual runner, evidence artifacts, and rollback probing.
- The codebase already contains useful DR/backup scripts instead of having nothing.
- Production config validation in `backend/app/config.py` catches several unsafe startup states.

## 7. Recommended Execution Order

### Phase 1 - Fix real release blockers

1. OR-03 - stop production auto-seeding of demo users and sample data
2. OR-02 - wire `REDIS_URL` correctly through production compose and docs
3. OR-01 - make deployment and rollback real instead of placeholder-only
4. OR-04 - add collab-server to CD artifacts/deploys and inject `VITE_COLLAB_SERVER_URL` in frontend image builds

### Phase 2 - Fix parity drift that will cause bad deploys

5. OR-05 - align env examples and READMEs with runtime names
6. OR-08 - validate the real production frontend nginx/container path

### Phase 3 - Improve recovery confidence

7. OR-06 - add PostgreSQL-first backup/restore validation
8. OR-07 - implement or remove unsupported secret-rotation grace-period guidance

## 8. Exit Criteria For Calling Ops Readiness `10/10`

Do not call operations readiness `10/10` until:

- release jobs execute real deploys, not commented examples
- rollback is a real executable procedure
- production compose can boot cleanly with the documented env contract
- fresh production startup cannot create demo users or sample content
- backend, frontend, and collab are all in the release artifact/deploy chain
- env examples and runbooks match runtime variable names
- PostgreSQL backup/restore has a validated drill path
- secret rotation documentation matches actual supported runtime behavior

## 9. Recommendation

No more broad code audit is needed right now.

The next valuable work is an **ops-hardening execution plan** that closes `OR-01` through `OR-08`, starting with the four Phase 1 items above.
