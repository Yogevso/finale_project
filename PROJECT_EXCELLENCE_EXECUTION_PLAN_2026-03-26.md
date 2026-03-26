# PROJECT EXCELLENCE EXECUTION PLAN - 2026-03-26

> Status: Completed on 2026-03-26. `XP-01` through `XP-08` are closed, and the final regression sweep is green across backend, frontend, and collab-server.

## 1. Purpose

This is the single working document for the next excellence phase.

It merges:

- [PROJECT_EXCELLENCE_AUDIT_2026-03-26.md](C:/Users/yogev/finale_project/PROJECT_EXCELLENCE_AUDIT_2026-03-26.md)
- [FRONTEND_EXCELLENCE_AUDIT_2026-03-26.md](C:/Users/yogev/finale_project/FRONTEND_EXCELLENCE_AUDIT_2026-03-26.md)

Use this file as the active backlog and execution order.

The two source audits remain useful as evidence snapshots, but this file is the one to work from.

## 2. Current Excellence Status

Opening baseline before execution was `8.6/10` overall. Current verified status is:

| Area | Current Rating | Current State |
|------|----------------|-----------------------|
| Frontend | 10/10 | Concentration, runtime-reporting, page-test, and transport-typing gaps from this phase are closed |
| Backend | 10/10 | Version-service concentration, lifespan/deprecation, and runtime-governance gaps from this phase are closed |
| Architecture | 10/10 | The excellence-phase architecture/runtime/type-discipline backlog is complete and verified |
| Overall | 10/10 | This execution plan is complete and the codebase now meets the phase exit criteria |

## 3. Unified Backlog

| ID | Priority | Status | Source IDs | Area | Title |
|----|----------|--------|------------|------|-------|
| XP-01 | HIGH | CLOSED | EX-02, FE-01 | Frontend Collaboration | Split `useCollaboration` into focused modules |
| XP-02 | HIGH | CLOSED | EX-01 | Backend Versions | Split `VersionService` into focused services/handlers |
| XP-03 | HIGH | CLOSED | EX-03, FE-02 | Frontend Admin | Split `UsersPage` and add page-level tests |
| XP-04 | MEDIUM | CLOSED | EX-03, FE-03 | Frontend Support | Split `SupportPage` into controller + feature modules |
| XP-05 | MEDIUM | CLOSED | FE-04 | Frontend Public | Split/test `PublicDocumentsPage` |
| XP-06 | MEDIUM | CLOSED | EX-05, FE-05 | Runtime Excellence | Unify runtime reporting and improve production-grade metrics/logging |
| XP-07 | MEDIUM | CLOSED | EX-04 | Backend Governance | Replace FastAPI `on_event` startup wiring with lifespan and keep the deprecation register truthful |
| XP-08 | LOW | CLOSED | EX-06, FE-06 | Frontend Type Discipline | Remove `any`-based API composition mixins |

## 4. Work Items

### XP-01 - Split `useCollaboration`

- Priority: HIGH
- Main evidence:
  - [useCollaboration.ts](C:/Users/yogev/finale_project/frontend/src/lib/useCollaboration.ts#L138)
  - [useCollaboration.ts](C:/Users/yogev/finale_project/frontend/src/lib/useCollaboration.ts#L297)
  - [useCollaboration.ts](C:/Users/yogev/finale_project/frontend/src/lib/useCollaboration.ts#L624)
  - [useCollaboration.test.ts](C:/Users/yogev/finale_project/frontend/src/lib/useCollaboration.test.ts#L108)
- Scope:
  - extract collaboration auth/token lifecycle
  - extract provider connection/reconnect state machine
  - extract local persistence/session tracking
  - extract permission refresh/access recheck
  - keep the public hook orchestration-only
- Done when:
  - `useCollaboration.ts` becomes a small orchestration hook
  - extracted seams have focused tests
  - the current collaboration regression suite remains green

### XP-02 - Split `VersionService`

- Priority: HIGH
- Main evidence:
  - [version_service.py](C:/Users/yogev/finale_project/backend/app/services/version_service.py#L47)
  - [version_service.py](C:/Users/yogev/finale_project/backend/app/services/version_service.py#L649)
  - [version_service.py](C:/Users/yogev/finale_project/backend/app/services/version_service.py#L1066)
- Scope:
  - split version read/query behavior from publish workflows
  - split scheduled publish/cancel/process behavior
  - split review-readiness and audience validation concerns
  - inject collaborators explicitly rather than self-assembling them
- Done when:
  - `VersionService` is no longer the policy and side-effect bucket
  - publish/schedule/review behavior have clear boundaries
  - version-related backend suites stay green

### XP-03 - Split `UsersPage` and add tests

- Priority: HIGH
- Main evidence:
  - [UsersPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/UsersPage.tsx#L53)
  - [UsersPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/UsersPage.tsx#L194)
  - [UsersPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/UsersPage.tsx#L563)
- Scope:
  - extract query/filter controller state
  - extract user mutation flows
  - extract invitation management flows
  - extract the embedded user form dialog
  - add dedicated page-level tests for main admin user flows
- Done when:
  - the page becomes a composition root, not the implementation bucket
  - `UsersPage.test.tsx` exists with meaningful workflow coverage

### XP-04 - Split `SupportPage`

- Priority: MEDIUM
- Main evidence:
  - [SupportPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/SupportPage.tsx#L63)
  - [SupportPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/SupportPage.tsx#L651)
  - [SupportPage.test.tsx](C:/Users/yogev/finale_project/frontend/src/pages/SupportPage.test.tsx#L121)
- Scope:
  - extract support queue controller
  - extract ticket detail controller
  - extract handoff/assignment modules
  - extract canned-response composer behavior
- Done when:
  - page responsibilities are visibly separated
  - current support page coverage still passes after the split

### XP-05 - Split/test `PublicDocumentsPage`

- Priority: MEDIUM
- Main evidence:
  - [PublicDocumentsPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/public/PublicDocumentsPage.tsx#L108)
  - [PublicDocumentsPage.tsx](C:/Users/yogev/finale_project/frontend/src/pages/public/PublicDocumentsPage.tsx#L233)
- Scope:
  - extract query-string and category-tree logic
  - extract search/pagination behavior where practical
  - add dedicated page tests for search, category filtering, and pagination
- Done when:
  - `PublicDocumentsPage` is simpler to reason about
  - dedicated page tests exist for the public browsing flow

### XP-06 - Unify runtime reporting and production-grade metrics/logging

- Priority: MEDIUM
- Main evidence:
  - [degradation.py](C:/Users/yogev/finale_project/backend/app/infrastructure/degradation.py#L19)
  - [collabServerApp.ts](C:/Users/yogev/finale_project/collab-server/src/server/collabServerApp.ts#L149)
  - [useCollaboration.ts](C:/Users/yogev/finale_project/frontend/src/lib/useCollaboration.ts#L266)
  - [DocumentPreview.tsx](C:/Users/yogev/finale_project/frontend/src/pages/document-detail/DocumentPreview.tsx#L451)
  - [useReaderArtifact.ts](C:/Users/yogev/finale_project/frontend/src/pages/document-detail/hooks/useReaderArtifact.ts#L124)
- Scope:
  - replace placeholder degradation counters with real exported runtime metrics
  - introduce a structured logger abstraction for collab-server
  - add a shared frontend runtime reporter
  - move important failures away from console-only reporting
- Done when:
  - backend/collab/frontend runtime failures follow one clear operator-visible path
  - console output becomes dev-only or intentionally low-value

### XP-07 - Replace FastAPI startup `on_event` with lifespan

- Priority: MEDIUM
- Main evidence:
  - [app_factory.py](C:/Users/yogev/finale_project/backend/app/app_factory.py#L162)
  - [deprecations.md](C:/Users/yogev/finale_project/docs/deprecations.md#L1)
- Scope:
  - move startup wiring to lifespan
  - ensure the deprecation register reflects reality during the transition
  - keep deprecation checks meaningful
- Done when:
  - no active FastAPI `on_event("startup")` path remains
  - the deprecation register and code agree

### XP-08 - Remove `any`-based API composition mixins

- Priority: LOW
- Main evidence:
  - [httpClient.ts](C:/Users/yogev/finale_project/frontend/src/lib/api/httpClient.ts#L17)
  - [composition.ts](C:/Users/yogev/finale_project/frontend/src/lib/api/composition.ts#L1)
  - [attachmentsApi.ts](C:/Users/yogev/finale_project/frontend/src/lib/api/attachmentsApi.ts#L22)
- Scope:
  - replace `Constructor<any>` mixins with typed constructors or explicit composition
  - tighten transport-layer typing without changing API behavior
- Done when:
  - shared API composition no longer relies on `any` constructors
  - frontend test suite remains green

## 5. Recommended Execution Order

### Phase 1 - Remove the largest concentration risks

1. XP-01 - split `useCollaboration`
2. XP-02 - split `VersionService`
3. XP-03 - split `UsersPage` and add page-level tests

### Phase 2 - Finish the remaining major UI/runtime hotspots

4. XP-04 - split `SupportPage`
5. XP-05 - split/test `PublicDocumentsPage`
6. XP-06 - runtime reporting and production-grade metrics/logging
7. XP-07 - FastAPI lifespan and deprecation discipline

### Phase 3 - Final polish

8. XP-08 - remove `any`-based API composition mixins

## 6. How To Work From This File

For each work item:

1. Re-open the evidence links.
2. Make the smallest structural split that creates a real seam.
3. Add or move tests so the new seam is directly covered.
4. Run the focused suite first, then the full relevant suite.
5. Mark the item closed only when the structure is cleaner and the tests still prove behavior.

## 7. Exit Criteria For Calling The Base `10/10`

Status: satisfied on `2026-03-26`.

Do not call the project `10/10` until all of the following are true:

- no major frontend hook or backend service remains a known gravitational center
- `UsersPage` and `PublicDocumentsPage` have dedicated page-level tests
- support and collaboration logic are split into clearer modules
- frontend, collab-server, and backend runtime failures use consistent reporting paths
- placeholder degradation metrics are replaced with real exported signals
- FastAPI startup wiring uses lifespan and the deprecation register stays truthful
- the shared frontend API layer is strongly typed end-to-end
- full backend, frontend, and collab regression sweeps are green after the final pass

## 8. Bottom Line

No new audit is needed before execution for this phase, because the execution backlog is complete.

Verification snapshot:

- Backend: `pytest -q` -> `1587 passed, 2 skipped`
- Frontend: `cmd /c npx vitest run` -> `89 files passed, 325 tests passed`
- Collab server: `cmd /c npm test -- --runInBand` -> `11 suites passed, 61 tests passed`

This file is now the closure record for the excellence phase, not an active backlog.
