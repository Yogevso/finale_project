# Wave P - Audience and Company Binding

## Scope

- Task IDs: 123-140
- Reference plan: `plan`
- Status: completed (2026-03-01)
- Goal: make audience and company assignment behavior deterministic across create, upload, edit, and detail flows.

## Completion Summary

- Completed on: 2026-03-01
- Implemented task IDs: 123-140
- Implementation commits:
- `926388b` feat(backend): enforce audience-company rules and add draft migration helper
- `d71828c` feat(frontend): complete audience assignment UX safeguards
- `9263f4f` feat(frontend): enforce company selection on visibility changes
- Next active wave: Wave Q (starting at task 141)

## Logical Execution Order

1. 128 Audience form schema normalization
2. 124 Visibility transition invariants
3. 134 Company assignment conflict detection
4. 127 Shared company selector primitive
5. 129 Company picker search and pagination
6. 130 Audience defaults by role
7. 123 Create flow audience binding
8. 131 Assignment pre-submit validation
9. 125 Upload flow audience parity
10. 135 Draft audience migration helper
11. 126 Audience access preview panel
12. 132 Audience template presets
13. 133 Audience change confirmation dialog
14. 136 Assignment chips bulk remove UX
15. 137 Company selector keyboard navigation
16. 138 Audience field dirty-state tracking
17. 139 Assignment unsaved-changes guard
18. 140 Audience inline helper text standard

## Detailed Task Plans

### 123. Create flow audience binding

- Outcome: create flow supports `internal`, `public`, and `company`; `company` requires company selection before submit.
- Frontend changes:
- `frontend/src/pages/documents/components/CreateDocumentModal.tsx`
- `frontend/src/pages/documents/hooks/useCreateDocumentFlow.ts`
- `frontend/src/features/documents/useCases/documentsUseCases.ts`
- `frontend/src/types/index.ts`
- `frontend/src/lib/api/documentsApi.ts`
- Backend changes:
- `backend/app/schemas/__init__.py` add optional `company_ids` in `DocumentCreate` payload.
- `backend/app/services/document_service.py` support create-time company assignment.
- `backend/app/api/management/documents.py` pass create payload through command path without post-create manual patching.
- Test plan:
- `frontend/src/features/documents/useCases/documentsUseCases.test.ts` add create tests for company audience.
- `backend/tests/test_documents.py` add create success/failure coverage for `visibility=company`.
- Done criteria:
- Single create submit supports company audience and assignments.
- Backend rejects `visibility=company` with empty assignment set.

### 124. Visibility transition invariants

- Outcome: visibility transitions cannot leave invalid audience state.
- Backend changes:
- `backend/app/domain/specifications/invariants.py` add company visibility assignment spec.
- `backend/app/domain/aggregates/document_aggregate.py` enforce transition invariant checks.
- `backend/app/services/document_service.py` enforce update-time rules when visibility changes.
- `backend/app/application/commands/document_commands.py` return stable validation errors for invariant failures.
- Frontend changes:
- `frontend/src/pages/document-detail/EditForm.tsx`
- `frontend/src/pages/documents/components/DocumentsTable.tsx`
- `frontend/src/pages/documents/hooks/useDocumentsPageController.ts`
- Test plan:
- `backend/tests/test_documents.py` visibility transition matrix tests.
- `frontend/src/pages/document-detail/hooks/useDocumentDetailPageState.test.tsx` mutation error handling coverage.
- Done criteria:
- Transition to `company` fails without assignments.
- Transition away from `company` follows explicit rule and is audited.

### 125. Upload flow audience parity

- Outcome: upload flow has the same audience and company requirements as create flow.
- Frontend changes:
- `frontend/src/pages/documents/components/UploadDocumentModal.tsx`
- `frontend/src/pages/documents/hooks/useUploadDocumentFlow.ts`
- `frontend/src/features/documents/useCases/documentsUseCases.ts`
- `frontend/src/lib/api/documentsApi.ts`
- Backend changes:
- `backend/app/api/management/documents.py` accept upload company assignment input.
- `backend/app/application/process_managers/upload_workflow.py` apply assignment deterministically for parent and release-notes docs.
- `backend/app/services/document_service.py` reuse assignment validation.
- Test plan:
- `backend/tests/test_upload_lifecycle_defaults.py` add company visibility + assignment cases.
- `backend/tests/test_process_managers.py` add rollback tests on assignment failure.
- Done criteria:
- Upload with `visibility=company` requires at least one company.
- Assignment failure does not leave partial upload artifacts.

### 126. Audience access preview panel

- Outcome: detail page shows computed "who can access this document now."
- Backend changes:
- `backend/app/schemas/__init__.py` extend `DocumentDetailPageBundleResponse` with `audience_access_preview`.
- `backend/app/api/bff/documents.py` compute preview using visibility + assigned companies.
- Frontend changes:
- `frontend/src/types/index.ts` add typed preview model.
- `frontend/src/lib/api/dto/contracts.ts`
- `frontend/src/lib/api/dto/mappers.ts`
- `frontend/src/pages/document-detail/components/DocumentDetailsView.tsx`
- `frontend/src/pages/document-detail/hooks/useDocumentDetailPageState.ts`
- Test plan:
- `backend/tests/test_bff_documents_api.py` assert preview payload.
- `frontend/src/pages/document-detail/hooks/useDocumentDetailPageState.test.tsx` preview wiring assertions.
- Done criteria:
- Preview always matches current visibility and assignment state.

### 127. Shared company selector primitive

- Outcome: one reusable selector component serves create, upload, and detail flows.
- Frontend changes:
- `frontend/src/components/CompanySelector.tsx` refactor to reusable primitive API.
- `frontend/src/pages/documents/components/CreateDocumentModal.tsx` consume primitive.
- `frontend/src/pages/documents/components/UploadDocumentModal.tsx` consume primitive.
- `frontend/src/pages/document-detail/components/DocumentDetailsView.tsx` consume primitive.
- Test plan:
- Add `frontend/src/components/CompanySelector.test.tsx` for selection, remove, disabled, and load states.
- Done criteria:
- All document audience flows use the same selector component behavior and props.

### 128. Audience form schema normalization

- Outcome: create/upload/edit use the same audience form contract and normalization rules.
- Frontend changes:
- add `frontend/src/features/documents/forms/audienceSchema.ts`
- add `frontend/src/features/documents/forms/audienceFormTypes.ts`
- `frontend/src/features/documents/useCases/documentsUseCases.ts` normalize via shared utilities.
- `frontend/src/pages/documents/hooks/useCreateDocumentFlow.ts`
- `frontend/src/pages/documents/hooks/useUploadDocumentFlow.ts`
- `frontend/src/pages/document-detail/EditForm.tsx`
- Backend changes:
- align schema expectations in `backend/app/schemas/__init__.py`.
- Test plan:
- add `frontend/src/features/documents/forms/audienceSchema.test.ts`.
- Done criteria:
- No duplicated audience normalization logic remains in page hooks/components.

### 129. Company picker search and pagination

- Outcome: selector supports server-backed search and paging, not fixed `per_page=100`.
- Frontend changes:
- `frontend/src/components/CompanySelector.tsx` add debounced search input and paged fetch.
- `frontend/src/lib/queryKeys.ts` add company selector query keys.
- `frontend/src/lib/api/companiesApi.ts` reuse `page`, `per_page`, `search`.
- Backend changes:
- no schema change expected; verify existing `GET /companies` behavior.
- Test plan:
- selector test coverage for search and pagination.
- Done criteria:
- large company lists are usable and performant.

### 130. Audience defaults by role

- Outcome: default audience selection is role-aware and centralized.
- Frontend changes:
- add `frontend/src/features/documents/policies/audienceDefaults.ts`.
- wire into create/upload initial state.
- Backend changes:
- `backend/app/domain/specifications/invariants.py` keep role restrictions canonical.
- Test plan:
- add `frontend/src/features/documents/policies/audienceDefaults.test.ts`.
- Done criteria:
- defaults are consistent and do not bypass backend authorization.

### 131. Assignment pre-submit validation

- Outcome: invalid assignment payloads are blocked before API call and also server-side.
- Frontend changes:
- `frontend/src/features/documents/useCases/documentsUseCases.ts` enforce:
- required when `visibility=company`
- de-duplication and positive integer checks
- clear field-level errors
- Backend changes:
- `backend/app/services/document_service.py` validate:
- non-empty company set for `visibility=company`
- all company IDs exist and are active
- company IDs are tenant-safe for actor
- `backend/app/api/management/documents.py` return stable `error_code` values.
- Test plan:
- `backend/tests/test_documents.py` invalid set coverage.
- use-case tests for client-side validation paths.
- Done criteria:
- invalid payloads fail with actionable message and stable error code.

### 132. Audience template presets

- Outcome: quick presets reduce user error and speed up common audience setups.
- Frontend changes:
- `frontend/src/pages/documents/components/CreateDocumentModal.tsx`
- `frontend/src/pages/documents/components/UploadDocumentModal.tsx`
- add preset helper in `frontend/src/features/documents/policies/audiencePresets.ts`
- Test plan:
- preset utility tests and UI interaction tests.
- Done criteria:
- preset selection updates visibility and company-selection state predictably.

### 133. Audience change confirmation dialog

- Outcome: risky visibility changes require explicit user confirmation.
- Frontend changes:
- add reusable confirm modal component for visibility changes.
- `frontend/src/pages/document-detail/EditForm.tsx`
- `frontend/src/pages/documents/components/DocumentsTable.tsx`
- Backend changes:
- none for confirmation; backend keeps final enforcement.
- Test plan:
- detail/table interaction tests for confirm path and cancel path.
- Done criteria:
- moving to broader audience requires confirmation before mutation.

### 134. Company assignment conflict detection

- Outcome: concurrent assignment updates surface as conflicts, not silent overwrites.
- Backend changes:
- add concurrency check for assignment updates in:
- `backend/app/services/document_service.py`
- `backend/app/api/management/documents.py` (If-Match or row version binding)
- return `409` with explicit conflict error code.
- Frontend changes:
- include concurrency token on assignment mutation in:
- `frontend/src/pages/document-detail/hooks/useDocumentDetailPageState.ts`
- Test plan:
- `backend/tests/test_documents.py` concurrent assignment conflict test.
- detail hook test for conflict message and refresh prompt behavior.
- Done criteria:
- stale assignment updates are rejected deterministically.

### 135. Draft audience migration helper

- Outcome: existing inconsistent data is repaired before strict enforcement rollout.
- Backend and scripts changes:
- add migration helper script under `scripts/`.
- detect drafts/company-visibility docs without assigned companies.
- apply configured remediation strategy and write audit log entries.
- Docs changes:
- add runbook section in `docs/migrations/`.
- Test plan:
- script dry-run fixture test.
- Done criteria:
- dry run report available and production run is repeatable/idempotent.

Execution:
- Dry run:
```bash
python backend/scripts/draft_audience_migration_helper.py \
  --strategy auto \
  --report-file docs/migrations/evidence/wave-p-draft-audience-migration-dry-run.json
```
- Apply:
```bash
python backend/scripts/draft_audience_migration_helper.py \
  --apply \
  --strategy auto \
  --actor-user-id <admin_user_id> \
  --report-file docs/migrations/evidence/wave-p-draft-audience-migration-apply.json \
  --fail-on-unresolved
```
- Notes:
- default strategy `auto` assigns active owner tenant when available, otherwise demotes visibility to `internal`.
- re-running after a successful apply is idempotent (no new candidates, no new audit rows).

### 136. Assignment chips bulk remove UX

- Outcome: users can clear many assigned companies quickly and safely.
- Frontend changes:
- `frontend/src/components/CompanySelector.tsx` add:
- select-all-in-view
- clear-all
- remove-selected
- Test plan:
- selector tests for bulk remove actions.
- Done criteria:
- bulk removal updates form state and validation state correctly.

### 137. Company selector keyboard navigation

- Outcome: selector is fully keyboard operable.
- Frontend changes:
- `frontend/src/components/CompanySelector.tsx` add:
- roving focus for options
- arrow navigation
- enter and space toggle
- escape close
- Test plan:
- keyboard interaction tests.
- Done criteria:
- users can search, navigate, select, and close without mouse.

### 138. Audience field dirty-state tracking

- Outcome: UI tracks whether audience-related fields changed from initial state.
- Frontend changes:
- `frontend/src/pages/documents/hooks/useCreateDocumentFlow.ts`
- `frontend/src/pages/documents/hooks/useUploadDocumentFlow.ts`
- `frontend/src/pages/document-detail/hooks/useDocumentDetailPageState.ts`
- add shared dirty-state utility under `frontend/src/features/documents/forms/`.
- Test plan:
- unit tests for dirty-state utility and hook state transitions.
- Done criteria:
- save/submit buttons and warning banners reflect true dirty-state.

### 139. Assignment unsaved-changes guard

- Outcome: navigation/close warns users when audience assignments were changed but not saved.
- Frontend changes:
- `frontend/src/pages/documents/components/CreateDocumentModal.tsx`
- `frontend/src/pages/documents/components/UploadDocumentModal.tsx`
- `frontend/src/pages/document-detail/components/DocumentDetailsView.tsx`
- route-level guard integration where needed.
- Test plan:
- modal close/navigation guard behavior tests.
- Done criteria:
- user is prompted before losing unsaved assignment changes.

### 140. Audience inline helper text standard

- Outcome: all audience/assignment errors use consistent actionable copy.
- Frontend changes:
- add copy map in `frontend/src/features/documents/policies/audienceMessages.ts`.
- wire to create/upload/edit/detail errors.
- Backend changes:
- align `error_code` values to message map in `backend/app/api/management/documents.py`.
- Test plan:
- message-map unit tests and spot checks in hook/component tests.
- Done criteria:
- no raw backend strings shown directly for audience validation failures.

## Validation Checklist For Wave P

- Backend lint:
- `docker compose run --rm backend ruff check app/ tests/`
- Backend tests:
- `docker compose run --rm backend pytest tests/test_documents.py tests/test_upload_lifecycle_defaults.py tests/test_process_managers.py tests/test_bff_documents_api.py -q`
- Frontend typecheck:
- `npm --prefix frontend exec -- tsc --noEmit -p tsconfig.json`
- Frontend tests:
- `npm --prefix frontend run test -- src/features/documents/useCases/documentsUseCases.test.ts --run`
- `npm --prefix frontend run test -- src/pages/document-detail/hooks/useDocumentDetailPageState.test.tsx --run`

## Rollout Notes

- Keep strict backend enforcement behind a feature flag until task 135 data remediation is complete.
- Rollout sequence:
- dry-run migration helper
- run migration helper in apply mode
- enable strict create/update/upload enforcement
- monitor error rates for `invalid_company_set` and transition conflicts
