# PRODUCTION READINESS EXECUTION PLAN - 2026-03-26

> Status: Closed. This file now serves as the production-readiness closure record after `RP-01` through `RP-11` were completed and re-verified.

## 1. Purpose

This file is the single execution plan for the current production-readiness gap.

It merges:

- [OPS_READINESS_AUDIT_2026-03-26.md](C:/Users/yogev/finale_project/OPS_READINESS_AUDIT_2026-03-26.md)
- [PERFORMANCE_LOAD_AUDIT_2026-03-26.md](C:/Users/yogev/finale_project/PERFORMANCE_LOAD_AUDIT_2026-03-26.md)
- [DEPENDENCY_SUPPLY_CHAIN_AUDIT_2026-03-26.md](C:/Users/yogev/finale_project/DEPENDENCY_SUPPLY_CHAIN_AUDIT_2026-03-26.md)

Use this file as the historical execution and verification record.

The three source audits remain useful as evidence snapshots, but this file now records the completed execution path.

## 2. Current Readiness Status

Current baseline after `RP-01` to `RP-11` is:

| Area | Current Rating | Current State |
|------|----------------|---------------|
| Ops / release readiness | `10/10` | Production bootstrap, release-chain execution, PostgreSQL-first recovery drills, and runtime-backed secret rotation are all now aligned with the documented runbook |
| Performance / load readiness | `10/10` | Search, assistant, collaboration, and document/conversion paths now have explicit guardrails, durable backpressure-aware execution, and CI-visible regression coverage |
| Dependency / supply-chain readiness | `10/10` | Runtime deps are locked, audit artifacts are real, release-path images/actions are pinned, and all deployable services are covered |
| Overall production readiness | `10/10` | The production contract is now explicit, verified, and operationally truthful across deploy, load, recovery, and dependency governance |

## 3. Unified Backlog

| ID | Priority | Status | Source IDs | Area | Title |
|----|----------|--------|------------|------|-------|
| `RP-01` | HIGH | CLOSED | OR-02, OR-03, OR-05 | Production Bootstrap | Make production bootstrap and env contract safe by default |
| `RP-02` | HIGH | CLOSED | OR-01, OR-04, OR-08 | Release Chain | Make deploy/rollback real and include the full app artifact chain |
| `RP-03` | HIGH | CLOSED | SC-01, SC-02 | Runtime Supply Chain | Remove live Node vulnerability findings and stop skipping `collab-server` |
| `RP-04` | HIGH | CLOSED | SC-03, SC-04, SC-08 | Python Dependency Governance | Establish one authoritative Python lock/audit path |
| `RP-05` | MEDIUM | CLOSED | SC-05, SC-06, SC-07 | Build Provenance | Pin mutable images/actions and fix broken security artifact paths |
| `RP-06` | HIGH | CLOSED | PL-02 | Search | Make the production search path explicit and benchmarkable |
| `RP-07` | HIGH | CLOSED | PL-03 | Assistant | Add assistant admission control and saturation visibility |
| `RP-08` | HIGH | CLOSED | PL-01 | Performance Tooling | Add real load/performance regression gates |
| `RP-09` | MEDIUM | CLOSED | PL-04, PL-07 | Collaboration Observability | Add collab saturation telemetry, guardrails, and SLO coverage |
| `RP-10` | MEDIUM | CLOSED | PL-05, PL-06 | Document / Conversion Load | Harden large-document and conversion paths for real load |
| `RP-11` | MEDIUM | CLOSED | OR-06, OR-07 | Recovery / Secrets | Make backup/restore and key-rotation procedures operationally truthful |

## 4. Work Items

### `RP-01` - Make production bootstrap and env contract safe by default

- Priority: HIGH
- Main source findings:
  - `OR-02`
  - `OR-03`
  - `OR-05`
- Scope:
  - stop production auto-seeding of demo users/sample data
  - make the production compose/env contract satisfy backend startup requirements
  - align env examples and README guidance with runtime-preferred variable names
- Done when:
  - a fresh production boot cannot create demo accounts by default
  - production compose can boot with the documented env contract
  - examples/docs no longer drift from runtime config names

### `RP-02` - Make deploy/rollback real and include the full app artifact chain

- Priority: HIGH
- Main source findings:
  - `OR-01`
  - `OR-04`
  - `OR-08`
- Scope:
  - replace example-only CD deploy steps with executable rollout steps
  - implement a real rollback target path
  - build/publish/deploy `collab-server` with backend/frontend
  - wire `VITE_COLLAB_SERVER_URL` into frontend production builds
  - smoke-validate the actual frontend nginx/container production path
- Done when:
  - deploy and rollback are executable from CI
  - backend, frontend, and collab-server are all in the release chain
  - the production frontend container boots cleanly with its real config

### `RP-03` - Remove live Node vulnerability findings and stop skipping `collab-server`

- Priority: HIGH
- Status: CLOSED
- Main source findings:
  - `SC-01`
  - `SC-02`
- Scope:
  - upgrade direct vulnerable Node dependencies, starting with `axios`
  - add `collab-server` to dependency scanning
  - add `collab-server` to container scanning
  - add `collab-server` npm and Docker coverage to Dependabot
- Done when:
  - the direct `axios` finding is gone in both Node applications
  - the security workflow covers all three deployable services
  - Dependabot coverage includes `collab-server`
- Completed:
  - upgraded `axios` in both [frontend/package.json](C:/Users/yogev/finale_project/frontend/package.json) and [collab-server/package.json](C:/Users/yogev/finale_project/collab-server/package.json), and refreshed the lockfiles
  - expanded [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml) to run dependency and container scanning for `collab-server`
  - added `collab-server` npm and Docker coverage in [dependabot.yml](C:/Users/yogev/finale_project/.github/dependabot.yml)
  - added infra guardrail coverage in [test_wave_ag_infrastructure.py](C:/Users/yogev/finale_project/backend/tests/test_wave_ag_infrastructure.py)
- Verification:
  - `cmd /c npm audit --omit=dev --audit-level=high --json` in `frontend/` -> `0 vulnerabilities`
  - `cmd /c npm audit --omit=dev --audit-level=high --json` in `collab-server/` -> `0 vulnerabilities`
  - `pytest tests/test_wave_ag_infrastructure.py -q` -> `31 passed`
  - `cmd /c npx vitest run src/lib/api/httpClient.test.ts src/lib/api/collaborationApi.test.ts src/pages/LoginPage.test.tsx` -> `11 passed`
  - `cmd /c npm test -- --runInBand` in `collab-server/` -> `11 suites passed, 61 tests passed`

### `RP-04` - Establish one authoritative Python lock/audit path

- Priority: HIGH
- Status: CLOSED
- Main source findings:
  - `SC-03`
  - `SC-04`
  - `SC-08`
- Scope:
  - separate runtime and dev/test Python dependencies cleanly
  - decide and enforce one lockfile strategy
  - make `pip-audit` run against authoritative manifests rather than only the environment
  - remove duplicate/noisy runtime entries
- Done when:
  - the Python dependency source of truth is obvious
  - manifest-scoped audit is reproducible
  - runtime manifests are minimal and clean
- Completed:
  - replaced the stale mixed-manifest setup with [requirements.in](C:/Users/yogev/finale_project/backend/requirements.in), [requirements-dev.in](C:/Users/yogev/finale_project/backend/requirements-dev.in), [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt), and [requirements-dev.txt](C:/Users/yogev/finale_project/backend/requirements-dev.txt)
  - removed the stale `backend/requirements.lock` path and moved dev/test tooling fully out of the runtime source manifest
  - aligned the backend container and local docs/scripts with the locked manifests in [Dockerfile](C:/Users/yogev/finale_project/backend/Dockerfile), [README.md](C:/Users/yogev/finale_project/backend/README.md), [README.md](C:/Users/yogev/finale_project/README.md), [DEVELOPMENT.md](C:/Users/yogev/finale_project/docs/DEVELOPMENT.md), and [setup.ps1](C:/Users/yogev/finale_project/backend/setup.ps1)
  - switched Python auditing onto manifest-scoped lockfiles in [pip_audit_gate.py](C:/Users/yogev/finale_project/scripts/pip_audit_gate.py), [dependency_audit.py](C:/Users/yogev/finale_project/backend/scripts/dependency_audit.py), and [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml)
  - documented the one current no-fix pip-audit waiver in [pip-audit.ignore](C:/Users/yogev/finale_project/backend/pip-audit.ignore)
- Verification:
  - `pytest tests/test_wave_ag_infrastructure.py tests/test_wave_ah.py -q` -> `50 passed`
  - Python 3.11 lock generation in the backend service succeeded for both runtime and dev lockfiles
  - `pip-audit -r requirements.txt --strict --ignore-vuln CVE-2026-4539` in the backend service -> `No known vulnerabilities found, 1 ignored`
  - `pip-audit -r requirements-dev.txt --strict --ignore-vuln CVE-2026-4539` in the backend service -> `No known vulnerabilities found, 1 ignored`

### `RP-05` - Pin mutable images/actions and fix broken security artifact paths

- Priority: MEDIUM
- Status: CLOSED
- Main source findings:
  - `SC-05`
  - `SC-06`
  - `SC-07`
- Scope:
  - pin Docker base images and production compose images to digests
  - remove `latest` from production image references
  - pin security-sensitive GitHub Actions to immutable SHAs
  - fix the frontend npm-audit artifact generation/upload path
- Done when:
  - build provenance is digest/SHA pinned across the main release path
  - the security workflow produces the artifacts it claims to upload
- Completed:
  - pinned release-path Docker base images in [backend/Dockerfile](C:/Users/yogev/finale_project/backend/Dockerfile), [frontend/Dockerfile](C:/Users/yogev/finale_project/frontend/Dockerfile), and [collab-server/Dockerfile](C:/Users/yogev/finale_project/collab-server/Dockerfile)
  - pinned third-party runtime images in [docker-compose.prod.yml](C:/Users/yogev/finale_project/docker-compose.prod.yml) and aligned the dev compose references in [docker-compose.yml](C:/Users/yogev/finale_project/docker-compose.yml)
  - replaced mutable action refs in [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml) with immutable SHAs for checkout, setup, CodeQL, Docker, Trivy, Gitleaks, and TruffleHog
  - made the frontend and collab npm audit jobs generate real JSON reports before upload, and forced report uploads to run with `if: always()`
  - documented the image/action pin refresh procedure in [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md)
- Verification:
  - `pytest tests/test_wave_ag_infrastructure.py -q` -> `40 passed`
  - `docker compose -f docker-compose.prod.yml config` -> passed
  - `docker compose -f docker-compose.prod.yml --profile with-ollama --profile with-postgres config` -> passed
  - `docker compose -f docker-compose.yml config` -> passed
  - `docker compose -f docker-compose.yml --profile ai --profile postgres config` -> passed

### `RP-06` - Make the production search path explicit and benchmarkable

- Priority: HIGH
- Status: CLOSED
- Main source finding:
  - `PL-02`
- Scope:
  - choose and implement the actual production search strategy
  - stop treating silent `LIKE` fallback as the normal production path
  - surface degraded search mode in health/metrics
  - benchmark the chosen production path on seeded data
- Done when:
  - production search behavior is explicit
  - degraded fallback is visible rather than silent
  - search performance can be regression-tested meaningfully
- Completed:
  - added explicit `SEARCH_BACKEND_MODE` contract in [config.py](C:/Users/yogev/finale_project/backend/app/config.py), [search_backend.py](C:/Users/yogev/finale_project/backend/app/search_backend.py), [docker-compose.prod.yml](C:/Users/yogev/finale_project/docker-compose.prod.yml), [.env.example](C:/Users/yogev/finale_project/.env.example), [validate_config.py](C:/Users/yogev/finale_project/scripts/validate_config.py), and [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md)
  - replaced the SQLite-first implicit path in [search_queries.py](C:/Users/yogev/finale_project/backend/app/application/queries/search_queries.py) with explicit backend resolution: `sqlite_fts5`, `postgres_tsv`, or `portable_like`
  - made degraded fallback visible in runtime health via [search_runtime.py](C:/Users/yogev/finale_project/backend/app/observability/search_runtime.py), [health.py](C:/Users/yogev/finale_project/backend/app/api/health.py), and degradation events under `compensating:search.documents`
  - updated the seeded benchmark scenario in [audience_benchmarks.py](C:/Users/yogev/finale_project/backend/tests/scenarios/audience_benchmarks.py) so it records the active search backend mode on the measured path
- Verification:
  - `pytest tests/test_feature_flags.py tests/test_search_api.py tests/test_health_detailed.py tests/test_wave_ag_infrastructure.py tests/scenarios/audience_benchmarks.py -q` -> `82 passed`
  - `pytest -q` in `backend/` -> `1620 passed, 2 skipped`
  - `python scripts/validate_config.py --env production` with explicit `SEARCH_BACKEND_MODE=postgres_tsv` -> passed
  - `docker compose -f docker-compose.prod.yml config` with explicit `SEARCH_BACKEND_MODE=postgres_tsv` -> passed

### `RP-07` - Add assistant admission control and saturation visibility

- Priority: HIGH
- Status: CLOSED
- Main source finding:
  - `PL-03`
- Scope:
  - add assistant concurrency limits / admission control
  - separate chat capacity from embedding capacity
  - expose queue length, rejection behavior, and latency/saturation signals
- Done when:
  - assistant traffic cannot fan out unboundedly under concurrent load
  - operators can see assistant saturation before users feel collapse
- Completed:
  - added explicit chat and embedding admission-control lanes in [assistant_capacity_service.py](C:/Users/yogev/finale_project/backend/app/services/assistant_capacity_service.py), with queue limits, timeout-based rejection, latency tracking, and degradation-event recording
  - wired the management chat SSE path in [assistant.py](C:/Users/yogev/finale_project/backend/app/api/management/assistant.py) to acquire and release assistant chat permits, and return `503` with `Retry-After` when capacity is exhausted
  - constrained embedding fan-out separately in [embeddings.py](C:/Users/yogev/finale_project/backend/app/assistant/rag/embeddings.py), so chat admission and embedding admission no longer share one unconstrained path
  - exposed assistant saturation state in both [health.py](C:/Users/yogev/finale_project/backend/app/api/health.py) and the assistant health endpoint, including per-lane queue depth, rejections, timeout counts, and duration metrics
  - documented the new capacity knobs in [.env.example](C:/Users/yogev/finale_project/.env.example) and [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md), and validated the config contract in [config.py](C:/Users/yogev/finale_project/backend/app/config.py)
  - added isolation and regression coverage in [test_assistant_capacity.py](C:/Users/yogev/finale_project/backend/tests/test_assistant_capacity.py), [test_assistant_api.py](C:/Users/yogev/finale_project/backend/tests/test_assistant_api.py), [test_health_detailed.py](C:/Users/yogev/finale_project/backend/tests/test_health_detailed.py), [test_feature_flags.py](C:/Users/yogev/finale_project/backend/tests/test_feature_flags.py), and [test_wave_ag_infrastructure.py](C:/Users/yogev/finale_project/backend/tests/test_wave_ag_infrastructure.py)
- Verification:
  - `pytest tests/test_assistant_api.py tests/test_assistant_capacity.py tests/test_health_detailed.py tests/test_feature_flags.py -q` -> `54 passed`
  - `pytest tests/test_assistant_api.py tests/test_assistant_capacity.py tests/test_assistant_engine.py tests/test_assistant_document_version_access.py tests/test_health_detailed.py tests/test_feature_flags.py tests/test_wave_ag_infrastructure.py -q` -> `138 passed`
  - `pytest -q` in `backend/` -> `1627 passed, 2 skipped`

### `RP-08` - Add real load/performance regression gates

- Priority: HIGH
- Status: CLOSED
- Main source finding:
  - `PL-01`
- Scope:
  - add a CI-visible performance stage
  - replace synthetic collaboration load testing with a more protocol-faithful harness
  - add repeatable regression checks for search, assistant, collab, and conversion-heavy paths
- Done when:
  - performance can regress loudly in CI
  - the collaboration harness resembles real client behavior
- Completed:
  - added a backend perf gate runner in [run_backend_perf_gate.py](C:/Users/yogev/finale_project/scripts/performance/run_backend_perf_gate.py) that executes seeded audience/search benchmarks, assistant SSE benchmarks, conversion-path benchmarks, and write-contention checks with threshold enforcement and JSON/JUnit outputs
  - added machine-readable benchmark scenarios in [audience_benchmarks.py](C:/Users/yogev/finale_project/backend/tests/scenarios/audience_benchmarks.py), [assistant_benchmarks.py](C:/Users/yogev/finale_project/backend/tests/scenarios/assistant_benchmarks.py), and [conversion_benchmarks.py](C:/Users/yogev/finale_project/backend/tests/scenarios/conversion_benchmarks.py)
  - replaced the synthetic collaboration load path with a protocol-faithful Yjs/Hocuspocus harness in [run-collab-perf-gate.mjs](C:/Users/yogev/finale_project/frontend/scripts/run-collab-perf-gate.mjs), and pointed the legacy entry point in [load_test_collaboration.py](C:/Users/yogev/finale_project/scripts/load_test_collaboration.py) at that real provider-based path
  - wired the new gates into CI in [ci.yml](C:/Users/yogev/finale_project/.github/workflows/ci.yml), including perf artifacts, collab-server startup, backend startup, and a dedicated `performance-gates` job
  - added infra guardrails for the perf gate wiring in [test_wave_ag_infrastructure.py](C:/Users/yogev/finale_project/backend/tests/test_wave_ag_infrastructure.py)
- Verification:
  - `python scripts/performance/run_backend_perf_gate.py` -> passed
  - backend perf metrics from the latest local run: audience assignment/detail/search p95 `10.62ms` / `9.73ms` / `9.02ms`, assistant SSE p95 `13.74ms`, docx reader-artifact p95 `31.45ms`, pdf export p95 `839.48ms`, pdf reader-artifact p95 `51.61ms`
  - `cmd /c npm run test:collab-perf-gate -- --backend-url http://127.0.0.1:8000 --collab-url ws://127.0.0.1:8002 --users 3 --rounds 3 --report-file collab-perf-report.json` in `frontend/` -> passed with sync p95 `50.21ms`, propagation p95 `6.00ms`, success ratio `1.0`
  - `pytest tests/test_wave_ag_infrastructure.py -q` -> `46 passed`

### `RP-09` - Add collab saturation telemetry, guardrails, and SLO coverage

- Priority: MEDIUM
- Status: CLOSED
- Main source findings:
  - `PL-04`
  - `PL-07`
- Scope:
  - add per-document and global collab traffic metrics
  - expose persistence latency/failure and reconnect churn
  - add explicit connection/document hot-spot guardrails
  - add SLOs for collaboration session start/save/reconnect paths
- Done when:
  - collaboration hot spots and saturation are observable
  - the SLO framework covers the collaboration path
- Completed:
  - added connection/document guardrails and runtime telemetry in [collabRuntimeMetrics.ts](C:/Users/yogev/finale_project/collab-server/src/server/collabRuntimeMetrics.ts), [connectionRegistry.ts](C:/Users/yogev/finale_project/collab-server/src/server/connectionRegistry.ts), and [collabServerApp.ts](C:/Users/yogev/finale_project/collab-server/src/server/collabServerApp.ts), including total/per-document connection caps, rejection counters, reconnect churn, top-document hot spots, and load/save latency metrics
  - enriched the collab health payload surfaced by [healthServer.ts](C:/Users/yogev/finale_project/collab-server/src/server/healthServer.ts) through the app runtime snapshot, so operators can see saturation state, guardrail utilization, hot documents, persistence failures, and load/save percentiles instead of only total counts
  - surfaced the important collab health details in backend system status via [admin_ops.py](C:/Users/yogev/finale_project/backend/app/api/management/admin_ops.py)
  - instrumented collaboration connect/save/revalidate routes into the shared use-case telemetry model in [sessions.py](C:/Users/yogev/finale_project/backend/app/api/management/collaboration/sessions.py), [state.py](C:/Users/yogev/finale_project/backend/app/api/management/collaboration/state.py), and [telemetry.py](C:/Users/yogev/finale_project/backend/app/api/management/collaboration/telemetry.py)
  - extended the shared SLO registry in [use-case-slos.json](C:/Users/yogev/finale_project/docs/slo/use-case-slos.json) to cover `collab.start_collaboration_session`, `collab.save_document_state`, and `collab.verify_collaboration_access`
  - updated operator-facing env/docs in [.env.example](C:/Users/yogev/finale_project/.env.example), [collab-server/.env.example](C:/Users/yogev/finale_project/collab-server/.env.example), [collab-server/README.md](C:/Users/yogev/finale_project/collab-server/README.md), and [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md)
- Verification:
  - `pytest tests/test_collaboration.py tests/test_observability_slo.py tests/test_wave_ag_infrastructure.py -q` -> `87 passed`
  - `pytest -q` in `backend/` -> `1633 passed, 2 skipped`
  - `cmd /c npm test -- --runInBand` in `collab-server/` -> `11 suites passed, 63 tests passed`

### `RP-10` - Harden large-document and conversion paths for real load

- Priority: MEDIUM
- Status: CLOSED
- Main source findings:
  - `PL-05`
  - `PL-06`
- Scope:
  - decide whether current upload/document size caps are the intended product boundary
  - remove or dev-gate daemon-thread conversion fallback
  - move heavier document processing toward worker-first/backpressure-aware paths where needed
- Done when:
  - large-document behavior is an intentional product boundary, not just an implementation artifact
  - production conversion no longer relies on request-adjacent daemon threads
- Completed:
  - made the reader-artifact scheduling path durable-only in [reader_view.py](C:/Users/yogev/finale_project/backend/app/services/attachment_service/reader_view.py), routing all production work through [conversion_jobs.py](C:/Users/yogev/finale_project/backend/app/services/conversion_jobs.py) instead of request-adjacent daemon threads
  - shared the active DB session from upload/read flows in [upload.py](C:/Users/yogev/finale_project/backend/app/services/attachment_service/upload.py) so durable conversion jobs are created transaction-safely during attachment writes
  - documented the current production document boundary in [.env.example](C:/Users/yogev/finale_project/.env.example) and [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md): uploads are intentionally capped at `10MB`, and heavier reader-artifact work is queue-backed rather than thread-backed
  - added regression coverage in [test_reader_view_structured_artifacts.py](C:/Users/yogev/finale_project/backend/tests/test_reader_view_structured_artifacts.py) and [test_wave_ag_infrastructure.py](C:/Users/yogev/finale_project/backend/tests/test_wave_ag_infrastructure.py)
- Verification:
  - `pytest tests/test_attachments.py tests/test_upload_lifecycle_defaults.py tests/test_upload_magic_bytes.py tests/test_reader_view_structured_artifacts.py -q` -> `58 passed`
  - `pytest -q` in `backend/` -> `1641 passed, 2 skipped`

### `RP-11` - Make backup/restore and key-rotation procedures operationally truthful

- Priority: MEDIUM
- Status: CLOSED
- Main source findings:
  - `OR-06`
  - `OR-07`
- Scope:
  - add PostgreSQL-first backup/restore drill support
  - make restore validation part of the actual production runbook
  - either implement dual-key rotation support or remove the unsupported grace-period guidance
- Done when:
  - recovery procedures match the production database reality
  - secret-rotation docs describe a path the runtime actually supports
- Completed:
  - added PostgreSQL-first backup and restore-drill support in [backup_restore_drill.py](C:/Users/yogev/finale_project/backend/scripts/backup_restore_drill.py), while preserving SQLite compatibility for local/dev
  - made disaster-recovery validation backend-aware in [disaster_recovery_validation.py](C:/Users/yogev/finale_project/backend/scripts/disaster_recovery_validation.py), including backend-specific backup discovery and PostgreSQL restore-tooling checks
  - implemented runtime-backed JWT grace-period verification through `SECRET_KEY_OLD` in [config.py](C:/Users/yogev/finale_project/backend/app/config.py), [token_service.py](C:/Users/yogev/finale_project/backend/app/auth_context/token_service.py), [collaboration_auth_service.py](C:/Users/yogev/finale_project/backend/app/auth_context/collaboration_auth_service.py), and [collaborationAuthService.ts](C:/Users/yogev/finale_project/collab-server/src/authContext/collaborationAuthService.ts)
  - aligned the operator runbook and env examples in [rotate_secrets.py](C:/Users/yogev/finale_project/backend/scripts/rotate_secrets.py), [.env.example](C:/Users/yogev/finale_project/.env.example), [collab-server/.env.example](C:/Users/yogev/finale_project/collab-server/.env.example), [collab-server/README.md](C:/Users/yogev/finale_project/collab-server/README.md), and [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md)
  - added regression coverage in [test_ops_readiness_scripts.py](C:/Users/yogev/finale_project/backend/tests/test_ops_readiness_scripts.py), [test_auth_context_services.py](C:/Users/yogev/finale_project/backend/tests/test_auth_context_services.py), [test_wave_ag_infrastructure.py](C:/Users/yogev/finale_project/backend/tests/test_wave_ag_infrastructure.py), and [auth.test.ts](C:/Users/yogev/finale_project/collab-server/src/__tests__/auth.test.ts)
- Verification:
  - `pytest tests/test_reader_view_structured_artifacts.py tests/test_auth_context_services.py tests/test_feature_flags.py tests/test_ops_readiness_scripts.py tests/test_wave_ag_infrastructure.py -q` -> `94 passed`
  - `pytest -q` in `backend/` -> `1641 passed, 2 skipped`
  - `cmd /c npm test -- --runInBand` in `collab-server/` -> `11 suites passed, 65 tests passed`
  - `python scripts/validate_config.py --env production` with explicit production-like env vars -> passed (warning-only if a local legacy `JWT_SECRET` remains exported)

## 5. Recommended Execution Order

### Phase 1 - Close the production blockers and live supply-chain gaps

1. `RP-01` - production bootstrap and env contract safety - done
2. `RP-02` - real deploy/rollback and full release chain - done
3. `RP-03` - Node vulnerabilities and collab-server scan coverage - done
4. `RP-04` - authoritative Python lock/audit path - done
5. `RP-05` - build provenance pinning and workflow cleanup - done

### Phase 2 - Close the biggest runtime/load risks

6. `RP-06` - production search path - done
7. `RP-07` - assistant bulkheads and saturation visibility - done
8. `RP-08` - real performance/load gates - done

### Phase 3 - Mature observability and recovery confidence

9. `RP-09` - collab telemetry, guardrails, and SLO coverage - done
10. `RP-10` - document/conversion load hardening - done
11. `RP-11` - backup/restore and secret-rotation truthfulness - done

## 6. How To Work From This File

For each work item:

1. Re-open the source audit evidence.
2. Make the smallest set of changes that closes the operational gap for real.
3. Add verification that proves the runtime/deploy/ops behavior, not just unit correctness.
4. Re-run the focused checks first, then the wider relevant sweep.
5. Mark the item closed only when the runtime story is actually better, not just cleaner on paper.

## 7. Exit Criteria For Calling Production Readiness `10/10`

Do not call this phase `10/10` until all of the following are true:

- production startup cannot create demo users or sample data by default
- production env examples and compose files match runtime requirements
- backend, frontend, and collab-server are all in a real deploy/rollback chain
- live dependency findings are removed from direct runtime dependencies
- security automation covers all deployable services
- Python dependency locking/auditing is authoritative and reproducible
- images and GitHub Actions are pinned to immutable references
- production search behavior is explicit on the actual target database
- assistant traffic has explicit admission control and visible saturation behavior
- at least one meaningful performance/load regression gate exists in CI - done
- collaboration, conversion, search, and assistant paths have usable telemetry/SLO coverage
- PostgreSQL restore and secret rotation procedures match what operators can actually execute

## 8. Bottom Line

No more broad audit is needed before execution for this phase.

The backlog is now complete enough to stop reviewing and start closing items.

If the goal is to make the base genuinely production-ready rather than only
code-clean, this file is the one to work from next.
