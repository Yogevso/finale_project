# PRD: Intel Documentation Platform — Full Delivery Plan

> **Product**: Multi-tenant document management & publishing platform for Intel  
> **Users**: Intel internal staff (editors, managers, admins) + external client users (Dell, Lenovo, HP, etc.)  
> **Auth model**: Invitation-only, RBAC, no billing/subscription — all access is provisioned by Intel admins  
> **Branch**: `wave-x` (current)  
> **Stack**: FastAPI + React/Vite + Hocuspocus collab-server, SQLite, S3-compatible storage  

---

## Wave Y — DOCX/PPTX Ingestion Pipeline (COMPLETE)

### Why this wave exists
We are simplifying the document upload system to **only accept DOCX and PowerPoint files**, replacing the complex PDF extraction pipeline. This pivot allows us to build a high-quality, controllable extraction system that preserves document structure reliably rather than fighting PDF extraction edge cases.

### Non-negotiable outcome
- A user can upload a `.docx` or `.pptx` file and trust the platform to:
  - Preserve the original file exactly (download returns identical bytes)
  - Extract headings, paragraphs, lists, tables, and images accurately
  - Generate clean, semantic HTML that renders beautifully in the viewer
  - Surface clear warnings if any content couldn't be extracted

### In scope
- DOCX and PPTX file upload only (no PDF support — users must convert PDFs to DOCX before uploading)
- New extraction pipeline using `python-docx` and `python-pptx`
- Structured HTML generation with consistent styling
- PPTX slides rendered as vertical sections (scrollable, not horizontal navigation)
- Speaker notes in collapsible panels per slide
- Frontend rendering improvements for extracted content
- Upload validation and error messaging

### Out of scope
- PDF support (users should convert to DOCX externally)
- OCR or scanned document handling
- Real-time collaboration changes
- Admin/analytics surfaces

### Exit criteria
- Upload accepts only `.docx` and `.pptx` files with clear error for other types
- DOCX extraction preserves: headings (H1-H6), paragraphs, bulleted/numbered lists, tables, inline formatting (bold/italic/underline), images
- PPTX extraction produces per-slide sections with titles, bullet points, and images
- Extracted HTML renders consistently in the viewer with proper styling
- Original file download works correctly
- Backend unit tests cover extraction edge cases
- E2E test validates full upload-to-view flow

### Phase 1: Restrict Upload Types
- [x] Y-001: Update `backend/app/config.py` `ALLOWED_EXTENSIONS` to `{".docx", ".pptx"}`
- [x] Y-002: Update frontend `UploadDocumentModal.tsx` to accept only `.docx`/`.pptx` with clear messaging
- [x] Y-003: Add user-friendly error toast when unsupported file type is selected
- [x] Y-004: Disable/deprecate PDF conversion code paths (routes disabled; full code removal in Y1-050+)

### Phase 2: DOCX Extraction Engine
- [x] Y-005: Create `backend/app/conversion/docx_extractor.py` — dedicated DOCX parser
- [x] Y-006: Extract headings from Word styles (Heading 1-6, Title) → H1-H6 tags
- [x] Y-007: Extract paragraphs with inline formatting (bold, italic, underline, code)
- [x] Y-008: Extract bulleted and numbered lists with proper nesting
- [x] Y-009: Extract tables with `<table>/<thead>/<tbody>/<tr>/<td>` structure, handle merged cells
- [x] Y-010: Extract embedded images — save to storage, inject `<img src>` with proper URLs
- [x] Y-011: Generate semantic HTML with consistent CSS classes for styling

### Phase 3: PPTX Extraction Engine
- [x] Y-012: Create `backend/app/conversion/pptx_extractor.py` — dedicated PPTX parser
- [x] Y-013: Extract slides as vertical `<section>` blocks with slide number badge
- [x] Y-014: Extract slide titles as H2 headings
- [x] Y-015: Extract text boxes and bullet points
- [x] Y-016: Extract embedded images and shape graphics
- [x] Y-017: Extract speaker notes into collapsible `<details>` panel per slide

### Phase 4: Unified Pipeline & Storage
- [x] Y-018: Update `backend/app/conversion/document_strategies.py` to use new extractors
- [x] Y-019: Define intermediate representation (IR) format: `{type, content, styles, children}`
- [x] Y-020: Create HTML generator that converts IR → semantic HTML
- [x] Y-021: Add extraction metadata (element counts, warnings, confidence) to artifact payload
- [x] Y-022: Store extraction result alongside original file in attachment record

### Phase 5: Frontend Rendering
- [x] Y-023: Update `documentRenderer.tsx` transform rules for new HTML structure
- [x] Y-024: Add CSS styles in `index.css` for: tables (scroll wrapper, headers, zebra), lists (markers, nesting), code (background, mono font), images (responsive, max-width)
- [x] Y-025: Add horizontal scroll wrapper for wide tables on mobile
- [x] Y-026: Add lightbox click handler for extracted images
- [x] Y-027: Display extraction warnings banner if elements couldn't be extracted

### Phase 6: Tests & Validation
- [x] Y-028: Create test `.docx` files with headings, tables, lists, images, mixed formatting
- [x] Y-029: Create test `.pptx` files with multiple slides, bullets, images
- [x] Y-030: Add backend unit tests for `docx_extractor.py`
- [x] Y-031: Add backend unit tests for `pptx_extractor.py`
- [x] Y-032: Add frontend component tests for renderer with sample extracted HTML
- [x] Y-033: Add Playwright E2E test: upload DOCX → verify rendered headings/tables/images

---

## Wave Y.1 — Quality, Architecture & Upload Flow Fixes (CURRENT PRIORITY)

### Why this wave exists
Wave Y successfully delivered DOCX/PPTX ingestion, but code review revealed architectural debt, hidden coupling patterns, and edge-case bugs that need immediate attention. Additionally, a focused review of the upload/create flow uncovered UX bugs and missing test coverage. This wave addresses these issues before moving to new feature work.

### Non-negotiable outcomes
- The "Preview Not Available" logic works correctly for all attachment/content combinations
- The global `AttachmentService` coupling is documented and improved (ideally refactored to DI)
- Upload flow cancel behavior is correct (no redirect after user cancels)
- Test coverage exists for all preview mode decisions and upload flow paths

### In scope
- Must-fix bugs: Preview logic, AttachmentService coupling, upload cancel behavior
- Backend refactoring: reader_view.py, extractors, conversion pipeline configurability
- Frontend refactoring: DocumentPreview.tsx, useReaderView.ts, download helpers, state normalization
- Upload flow: progress UI, cancel behavior, manager features, E2E tests
- **PDF removal**: Complete system-wide disallow of PDFs (no upload, no attachments, no preview, no PDF-specific logic)
- Static analysis cleanup and test coverage improvements

### Out of scope
- New features (deferred to later waves)
- Major UI redesigns
- Database schema changes

### Status snapshot (2026-03-13)
- Core Wave Y.1 delivery is in place: preview bug fix, upload cancel fix, PDF removal, backend reader/extractor refactors, frontend preview hook splits, focused coverage work, AttachmentService facade decoupling from module-global initialization, conversion-pipeline hardening, preview-path frontend DOM/DTO cleanup, upload UX polish, and final viewer coverage polish.
- Latest verified checkpoint: backend full suite passes, frontend full unit suite passes, the Playwright matrix passes in sliced runs, and the dedicated upload-modal UI spec passes.
- Remaining work for Wave Y.1: none beyond non-blocking warning cleanup and future-wave work.

### Exit criteria
- [x] All "Preview Not Available" edge cases handled correctly with tests
- [x] AttachmentService initialization documented and module-global facade coupling removed
- [x] Upload modal cancel behavior is correct (cancel stops upload OR disables cancel during upload)
- [x] DocumentPreview.tsx split into focused hooks with unit tests
- [x] useReaderView.ts split into sub-hooks with focused tests
- [x] Backend extractors modularized (smaller helpers, existing tests still pass)
- [x] Python and TypeScript static analysis clean in the core viewer/upload paths
- [x] E2E test exists for upload modal UI flow
- [x] **PDF completely removed**: No PDF upload, no PDF attachments, no PDF preview code, no PDF-specific endpoints

---

### Must-Fix (Highest Priority)

#### Frontend — Fix "Preview Not Available" Logic
- [x] Y1-001: Fix branch logic in `DocumentPreview.tsx` — find `if (!activeHtmlContent && previewableAttachments.length === 0)` and ensure:
  - Triggers when attachments exist but no previewable attachment available and no inline content exists
  - Uses `attachments` array consistently (no `attachments[0]` when length is 0)

- [x] Y1-002: Add tests for preview availability cases:
  - Attachments exist, none previewable, no inline content → "download-only" UI shown
  - No attachments + no inline content → "no content yet" UI (no broken branch)

#### Backend — Reduce Hidden Global Coupling for AttachmentService
- [x] Y1-003: Locate the global `AttachmentService` symbol used in:
  - `backend/app/services/attachment_service/common.py`
  - `backend/app/services/attachment_service/reader_view.py`
  - Document the historical bootstrap in `attachment_service/__init__.py`
  - Remove reliance on post-import mutation so imports are safe without `None` placeholders

- [x] Y1-004: Refactor helpers away from the module-global facade pattern
  - Implemented via classmethod dispatch on the `AttachmentService` facade instead of package-level mutable globals
  - Updated call sites and tests accordingly

#### Upload Flow — Cancel Bug Fix
- [x] Y1-005: Fix closing upload modal during ongoing upload does not cancel:
  - Current: closes modal but `onSuccess` still navigates to new document
  - Fix option A: Cancel mutation on modal close (via `uploadMutation.reset()` or explicit abort)
  - Fix option B: Disable closing while upload in progress with clear UI indication

---

### Backend — Architectural & Quality Improvements

#### Refactor Reader Artifact Generation into Smaller Units
- [x] Y1-010: File: `backend/app/services/attachment_service/reader_view.py`
  - Extract helper: "Structured reader flow" (DOCX/PPTX → reader artifact)
  - Extract helper: "Status & error mapping" (internal statuses → API response statuses, error messages/logging)
  - Remove any PDF-specific reader logic (moved to Y1-054)
  - Goal: shorter, single-responsibility functions with clear unit tests for each

#### Modularize DOCX Extractor
- [x] Y1-011: File: `backend/app/conversion/docx_extractor.py`
  - Identify internal responsibilities:
    - Archive parsing / low-level XML
    - Headings/lists/paragraph building
    - Tables extraction
    - Images/media extraction
    - IR building and warning/confidence calculation
  - Refactor into smaller internal helpers or sub-modules
  - Keep public APIs stable
  - Ensure existing tests (`test_docx_extractor.py`, Wave Y fixtures) still pass

#### Modularize PPTX Extractor
- [x] Y1-012: File: `backend/app/conversion/pptx_extractor.py`
  - Same approach as DOCX extractor
  - Ensure `test_pptx_extractor.py` and Wave Y fixtures still pass

#### Remove/Isolate Dead HTML-Rendering Helpers
- [x] Y1-013: In DOCX/PPTX extractor files, search for `_render_html` and related `_render_*` methods
  - Confirm via search and tests that nothing uses them anymore (replaced by `html_generator` and IR → HTML)
  - Either delete them, or move to clearly named "legacy/debug" module with explicit comments

#### Improve DocumentConversionPipeline Configurability
- [x] Y1-014: File: `backend/app/conversion/document_pipeline.py`
  - Keep `get_document_conversion_pipeline()` but also:
    - Register `DocumentConversionPipeline` instance in DI container
    - Make higher-level services depend on interface/abstraction (e.g., `ConversionService`)
  - Prepares for: per-tenant variants, A/B tests, different pipelines in background tasks

#### Clarify Conversion Strategy Capabilities
- [x] Y1-015: File: `backend/app/conversion/document_strategies.py`
  - For each remaining strategy (Word/DOCX, PPT/PPTX, Text, HTML passthrough):
    - Document which outputs it supports (e.g., `html`, `reader_artifact`, `outline`)
    - Optionally introduce a small "capability descriptor" object or enum
  - Note: PDF strategies removed in Y1-054
  - Makes adding new strategies or formats easier and safer

#### Check for Brittle Text-Based Error Detection
- [x] Y1-016: Inside reader artifact generation (after PDF removal):
  - Identify logic that checks error conditions by matching substrings in HTML/text
  - Where possible: prefer structured error codes/fields from converters
  - Add tests for:
    - Real errors → correctly detected
    - Legitimate text that looks like an error message → not misclassified

#### Run Python Static Checks for Unused Code
- [x] Y1-017: Enable or tighten tools (`ruff`, `flake8`, `mypy`/`pyright`):
  - Flag unused imports
  - Flag unused private/public functions
  - Flag unreachable code
  - Fix or remove unused/never-called code, especially in:
    - `conversion/*`
    - `services/attachment_service/*`
    - `legacy_wrappers/*`

---

### Frontend — Architectural & Quality Improvements

#### Refactor DocumentPreview into Smaller Pieces
- [x] Y1-020: File: `frontend/src/pages/document-detail/DocumentPreview.tsx`
  - Extract at least:
    - `usePreviewSource` — decide between reader HTML, inline version, or none (PDF removed in Y1-063)
    - `usePreviewProgress` — scroll tracking and document progress API sync
    - `usePreviewShortcuts` — keyboard shortcuts
  - Convert large effect blocks into smaller hooks or helper functions that are easier to test
  - Add unit tests for each hook, especially enumerating state combinations around source selection

#### Split Responsibilities Inside useReaderView
- [x] Y1-021: File: `frontend/src/pages/document-detail/hooks/useReaderView.ts`
  - Separate into:
    - `useReaderArtifact` — fetch/retry reader HTML, warnings, confidence
    - `useOutlineNavigation` — map outline/TOC → active heading/page
    - `useReaderModeSwitcher` — switch between reader/original modes, sync pages
  - Ensure each sub-hook has small, focused tests targeting its logic

#### Centralize Attachment Download Behavior
- [x] Y1-022: In `DocumentPreview.tsx` and any other places downloading attachments:
  - Extract a helper like `useAttachmentDownload`:
    - Input: `{ documentId, attachment }` (PDF conversion removed)
    - Handles: fetching blob, `URL.createObjectURL`, triggering `<a>` download, cleanup (`URL.revokeObjectURL`)
  - Use this helper everywhere to remove duplication and keep behavior consistent

#### Normalize "Empty" and "Preview Unavailable" States
- [x] Y1-023: In `DocumentPreview.tsx`, identify all branches that render "No Content Yet" / "Preview Not Available" / error states
  - Extract a pure function: `decidePreviewState({ attachments, inlineContent, readerStatus })`
  - Returns: `'NO_CONTENT' | 'DOWNLOAD_ONLY' | 'LOADING' | 'ERROR' | ...`
  - Write unit tests covering all combinations:
    - No attachments, no inline content
    - Attachments but no previewable attachments
    - Reader pending/failed/ready
    - (PDF preview status removed — no longer applicable)
  - Use that enum to drive the actual JSX branches

#### Abstract Direct DOM/Browser API Dependencies
- [x] Y1-024: Files to touch:
  - `frontend/src/lib/htmlSanitizer.ts`
  - `frontend/src/lib/documentRenderer.tsx`
  - `frontend/src/pages/document-detail/helpers/previewHelpers.ts`
  - `DocumentPreview.tsx` and related hooks relying on `DOMParser`, `window.location`, `document`, `navigator.clipboard`
  - Create wrappers like:
    - `env/dom.ts`: exports `getDomParser()`, `getDocument()`, `getWindowLocation()`
    - `env/clipboard.ts`: exports `writeText(text: string)`
  - Replace direct uses with these wrappers
  - Update tests to mock the wrappers instead of global objects

#### Strengthen DTO Mapping Safety
- [x] Y1-025: File: `frontend/src/lib/api/dto/mappers.ts`
  - For key mappings (`DocumentDetailPageBundleDto`, reader view responses, outline responses):
    - Add minimal comments clarifying which fields are intentionally dropped vs mapped
    - Consider dev-only assertions for presence of required fields (throw in dev if undefined)
  - Keep this file in sync whenever backend `openapi.contract.json` changes

#### Run TypeScript/ESLint Checks for Unused Code
- [x] Y1-026: Ensure `tsconfig.json` has:
  - `"noUnusedLocals": true`
  - `"noUnusedParameters": true`
  - Ensure ESLint enforces `no-unused-vars` and other relevant rules
  - Clean up unused functions, types, and exports, especially in viewer-related code

---

### Upload Flow Fixes & Improvements

#### Current State (Reviewed)
Upload UI & validation are mostly solid:
- Drag-and-drop + click-to-browse wired correctly
- Client-side validation enforces DOCX/PPTX, max 10MB
- Modal shows file name, size, error banner, disabled button states
- Metadata wiring is consistent with backend

#### Identified Issues

**Bug: Cancel During Upload**
- [x] Y1-005: (See Must-Fix section above)

**UX Roughness**
- [x] Y1-030: Add visible progress bar - modal now surfaces real multipart upload progress with a percent bar and in-flight status text

- [x] Y1-031: Replace placeholder icons in dropzone - replaced the "FILE"/"UP" placeholders with proper upload/file icons and clearer dropzone copy

**Feature Gap vs Backend Capabilities**
- [x] Y1-032: Backend supports but UI does not expose:
  - Status selection (managers/admins can set initial status at upload)
  - `release_notes` and `content_file` uploads alongside primary file
  - Implemented in upload modal for manager+ roles

**Missing E2E Tests**
- [x] Y1-033: Add E2E test for upload modal UI flow:
  - Opens upload modal
  - Selects file through UI (not just API)
  - Submits
  - Includes file-type validation and cancel-disabled-while-uploading coverage
  - Tests: drag-and-drop, file-type/size validation, error handling, cancel-during-upload behavior

---

### Tests & Coverage Improvements

#### Preview Mode Decision Logic
- [x] Y1-040: After extracting `decidePreviewMode`/`decidePreviewState` and `usePreviewSource`:
  - Write tests enumerating all relevant combinations of:
    - `attachments` present/absent
    - `readerStatus` (not requested, pending, ready, failed)
    - `previewStatus` (pending, ready, failed)
    - `inlineContent` present/absent
  - Assert selected mode/state matches expectations and correct path is used

#### Fixed "Preview Not Available" Case
- [x] Y1-041: Explicitly test:
  - Attachments exist, not previewable, no inline content → correct card + download button
  - Attachments exist, previewable but reader fails → user sees designed fallback state

#### Backend Coverage
- [x] Y1-042: Run coverage focusing on:
  - `backend/app/conversion/*`
  - `backend/app/services/attachment_service/*`
  - For significant untested methods/branches:
    - Real behavior → add tests
    - Dead code → delete/refactor

#### Frontend Viewer Coverage
- [x] Y1-043: Focus on:
  - `DocumentPreview.tsx`
  - `useReaderView.ts`
  - `previewHelpers.ts`
  - Add tests specifically for:
    - Edge cases in reader/preview failure and retry logic
    - Anchor copying behavior (already partially covered)
    - Warning banner rendering for different warning/confidence combinations

---

### PDF Removal — Complete System-Wide Disallow

#### Goal
Completely disallow PDFs anywhere in the system. No document upload, no attachments, no preview, no PDF-specific logic. This simplifies the codebase and aligns with the Wave Y decision to support only DOCX/PPTX.

#### Backend — Block PDFs at API & Domain Level

**Block PDFs for Document Upload**
- [x] Y1-050: File: `backend/app/api/management/documents.py`
  - In `upload_document`: check `file.content_type` and/or extension
  - Reject `application/pdf` or `.pdf` extension
  - Raise `ValidationError("PDF uploads are not allowed", error_code=...)`
  - Update docstring: "Word documents (DOCX) and PowerPoint (PPTX) only"

**Remove PDFs from Allowed Attachment Types**
- [x] Y1-051: File: `backend/app/services/attachment_service/common.py`
  - In `AttachmentServiceCommonMixin`:
    - Remove `"application/pdf"` from `ALLOWED_TYPES`
    - Remove `.pdf` from `OFFICE_EXTENSIONS` if present
  - Ensures attachments API also rejects PDFs

**Remove PDF-Specific Behavior in Attachment Creation**
- [x] Y1-052: File: `backend/app/services/attachment_service/upload.py`
  - In `create_attachment_from_bytes`:
    - Remove special-case logic marking PDFs as `PREVIEW_STATUS_READY`
    - Remove PDF metadata copying into `preview_pdf_*` fields
  - Any PDF attempt should already be blocked by Y1-051

**Handle Legacy Fields**
- [x] Y1-053: For `preview_pdf_*` fields and statuses:
  - Mark fields as "legacy; not used for new uploads" in comments
  - Stop writing these fields on new attachments
  - Keep reading for legacy rows if needed, or plan migration later

**Remove PDF-Only Conversion/Reader Logic**
- [x] Y1-054: File: `backend/app/conversion/document_pipeline.py`
  - Remove: `convert_pdf_to_reader_artifact`, `extract_pdf_toc`
  - Remove any strategy that is only for generic PDFs
  - Keep only: DOCX, PPTX, text, HTML strategies

**Remove PDF Outline/Preview Endpoints**
- [x] Y1-055: File: `backend/app/api/viewer/documents.py`
  - Remove endpoints that return PDF outline/TOC
  - Remove PDF-specific preview serving
  - Mark as deprecated if needed for backwards compatibility

**Ensure PDF Rejection in Attachment Upload**
- [x] Y1-056: After Y1-051, `upload_attachment` validates against `ALLOWED_TYPES + extensions`
  - PDF uploads will return `400 File type not allowed: application/pdf`
  - Optionally: make message explicit "PDF attachments are not allowed"

**Update Backend Tests**
- [x] Y1-057: Test updates:
  - `test_upload_lifecycle_defaults.py`: Replace `.pdf` fixtures with `.docx`
  - Add test: PDF upload to `/api/v1/documents/upload` returns 400 with clear message
  - `test_attachments.py`: Remove PDF tests or change to DOCX
  - Remove PDF outline/reader artifact tests from `test_viewer_api.py`, `test_reader_view_structured_artifacts.py`

#### Frontend — Disallow PDFs in UI & Client Code

**Update Upload Validation Constants**
- [x] Y1-060: File: `frontend/src/features/documents/useCases/documentsUseCases.ts`
  - Remove `'application/pdf'` from `DOCUMENT_UPLOAD_ALLOWED_MIME_TYPES`
  - Remove `'.pdf'` from `DOCUMENT_UPLOAD_ALLOWED_EXTENSIONS`
  - Remove `.pdf` from `DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES`
  - `validateDocumentUploadFile`: return "Only Word documents are allowed"

**Update Upload Modal UI**
- [x] Y1-061: File: `frontend/src/pages/documents/components/UploadDocumentModal.tsx`
  - Change helper text from "PDF, DOC, DOCX (max 10MB)" to "DOCX, PPTX (max 10MB)"
  - Update `<input type="file" accept={...}>` to only list `.docx,.pptx`
  - Note: Wave Y restricts to DOCX/PPTX only (not legacy .doc/.ppt formats)

**Remove PDF from Attachment Upload UI**
- [x] Y1-062: Wherever attachments can be added to documents:
  - Use shared config that excludes PDFs
  - Update messaging to not mention PDFs

**Remove PDF-Specific Viewer Code**
- [x] Y1-063: File: `frontend/src/pages/document-detail/DocumentPreview.tsx`
  - Remove: `previewUrl` / iframe-specific PDF preview
  - Remove: branches showing "Original PDF" view
  - Remove: PDF-mode switching logic
  - Keep only: Reader view (DOCX/PPTX) + inline HTML from versions

**Delete PDF Preview Component**
- [x] Y1-064: If `frontend/src/pages/document-detail/components/PdfPreviewPanel.tsx` exists:
  - Delete the component
  - Remove all usages

**Remove PDF Outline Fetching/Navigation**
- [x] Y1-065: File: `frontend/src/pages/document-detail/hooks/useReaderView.ts`
  - Remove: state for PDF outline/page (`pdfOutlinePage`, etc.)
  - Remove: network calls to backend PDF-outline endpoints
  - Remove: UI logic switching between PDF outline and reader-outline

**Remove PDF Helpers**
- [x] Y1-066: File: `frontend/src/pages/document-detail/helpers/previewHelpers.ts`
  - Remove helpers that map PDF outline to sections
  - Keep only DOCX/PPTX HTML behaviors

**Remove PDF-Related API Calls and Types**
- [x] Y1-067: Files: `attachmentsApi.ts`, `documentsApi.ts`
  - Remove methods calling PDF-outline endpoints
  - Remove PDF preview endpoints
  - After backend changes, regenerate `openapi-contracts.ts`
  - Delete DTO mappers for PDF preview/outline types

**Update Frontend Tests**
- [x] Y1-068: Test updates:
  - Confirm `e2e/office-upload.spec.ts` uses only DOCX (no PDF flow)
  - Remove "Original PDF" mode assertions from viewer tests
  - Remove PDF outline/preview UI tests
  - Add test: selecting PDF in modal yields client-side error text

#### Cleanup & Verification

**Search and Delete PDF-Specific References**
- [x] Y1-070: Global search for:
  - `'application/pdf'`
  - `'.pdf'`
  - `'PdfPreview'`
  - `pdfOutline`
  - `convert_pdf_to_reader_artifact`
  - `preview_pdf`
  - For each: remove OR ensure it exists only in legacy/compat code
  - **Update docs/USER_GUIDE.md** — currently lists "PDF, DOC, DOCX..." as supported; change to "DOCX, PPTX only"

**Regenerate OpenAPI & Frontend Contracts**
- [x] Y1-071:
  - Regenerate `backend/openapi.contract.json` from FastAPI
  - Regenerate `frontend/src/lib/api/generated/openapi-contracts.ts`

**Re-Run All Test Suites**
- [x] Y1-072:
  - Backend unit + integration tests
  - Frontend unit tests
  - E2E tests
  - Fix any failures related to removed PDF features or changed error messages

---

## Wave Y.1.5 — Security & Data Integrity Hardening

### Why this wave exists
The deep audit revealed critical security vulnerabilities and data integrity issues that must be fixed before adding new features. These are infrastructure-level fixes that protect the platform from attacks and data corruption.

### Non-negotiable outcomes
- No hardcoded secrets in production
- Containers run as non-root users
- Session revocation is immediate
- Cross-tenant data access is impossible
- Race conditions don't corrupt data

### In scope
- Security hardening (containers, secrets, authentication)
- Multi-tenancy isolation fixes
- Race condition fixes
- Orphaned resource cleanup
- Session management fixes

### Out of scope
- New features
- UI changes
- Performance optimizations (unless security-related)

---

### Critical Security Fixes

#### Container Security
- [x] Y15-001: Remove root user from backend Dockerfile — add `RUN adduser --disabled-password --gecos '' appuser` and `USER appuser` before CMD
- [x] Y15-002: Remove root user from frontend Dockerfile — add non-root user, ensure nginx runs as non-root
- [x] Y15-003: Remove root user from collab-server Dockerfile — add `USER node` before CMD
- [x] Y15-004: Add container security scanning to CI — integrate Trivy or similar, fail on HIGH/CRITICAL vulnerabilities

#### Secrets Management
- [x] Y15-005: Remove hardcoded `JWT_SECRET` fallback in `backend/app/config.py` — make `SECRET_KEY` env var required in production, fail startup if missing or insecure
- [x] Y15-006: Remove hardcoded secret fallback in `collab-server/src/collaborationAuthService.ts` — require `JWT_SECRET` env var in production
- [x] Y15-007: Add secrets validation on startup — check all required secrets are set, log warning for weak secrets
- [x] Y15-008: Document required secrets in `docs/DEPLOYMENT.md` with generation instructions

#### Session Security
- [x] Y15-009: Fix revoked sessions still valid — add `revoked_at` check to `auth_service.refresh_access_token()` before issuing new token
- [x] Y15-010: Fix token validation O(n) performance — add index on `refresh_tokens.token` column, add `LIMIT 1` to lookup query
- [x] Y15-011: Add session invalidation on password change — revoke all refresh tokens when user changes password
- [x] Y15-012: Add session listing endpoint for users — `GET /api/v1/users/me/sessions` showing active sessions with device/IP info

---

### Data Integrity Fixes

#### Multi-Tenancy Isolation
- [x] Y15-013: Fix cross-tenant attachment deletion — in `attachments.py` router, add tenant check before delete: `if attachment.document.tenant_id != current_user.tenant_id: raise 403`
- [x] Y15-014: Add tenant isolation tests for all document operations — verify user from tenant A cannot access/modify tenant B documents
- [x] Y15-015: Add tenant context middleware — inject `tenant_id` into request context, verify all DB queries filter by tenant
- [x] Y15-016: Audit all `DELETE` endpoints for tenant isolation — search for `.delete(` and verify tenant check exists

#### Race Condition Fixes
- [x] Y15-017: Fix document number race condition — use `SELECT ... FOR UPDATE` or atomic increment when generating next document number
- [x] Y15-018: Fix comment ordering race — add `SELECT ... FOR UPDATE` on parent comment when adding reply to ensure consistent ordering
- [x] Y15-019: Fix non-atomic version publish — wrap version publish in transaction: update status, copy content, update document in single tx
- [x] Y15-020: Add optimistic locking to document updates — use `row_version` column, return 409 on conflict

#### Orphaned Resource Cleanup
- [x] Y15-021: Fix orphaned files on delete failures — wrap file operations in try/finally, clean up storage if DB commit fails
- [x] Y15-022: Add orphaned file cleanup job — scheduled task to find storage files without DB records, log for manual review
- [x] Y15-023: Fix orphaned background jobs — add job cleanup for documents that were deleted while job was pending
- [x] Y15-024: Fix orphaned company assignments — add cascade delete or cleanup job when company is deactivated

---

### Backend Infrastructure

#### Error Handling
- [x] Y15-025: Fix silent exception swallowing in `comment_service.py` — replace bare `except:` with specific exceptions, log errors
- [x] Y15-026: Audit all `except Exception` blocks — ensure exceptions are logged, not silently ignored
- [x] Y15-027: Add structured error logging — include request ID, user ID, tenant ID in all error logs

#### Database Safety
- [x] Y15-028: Add foreign key constraints for critical relationships — document→tenant, attachment→document, comment→document
- [x] Y15-029: Add NOT NULL constraints where missing — audit models for nullable columns that shouldn't be
- [x] Y15-030: Add database connection pool health checks — verify connections are valid before use

#### Defense in Depth
- [x] Y15-041: Add security headers middleware — HSTS, X-Content-Type-Options, X-XSS-Protection, X-Frame-Options, CSP, Referrer-Policy
- [x] Y15-042: Add CSRF protection middleware — Origin/Referer validation for state-changing requests (POST/PUT/PATCH/DELETE)
- [x] Y15-043: Add input validation layer — max_length constraints on Pydantic schemas, SQL wildcard escaping, sanitization utilities
- [x] Y15-044: Add audit logging for user operations — SecurityEvent logging for user create/update/role change/deactivation/deletion

---

### Wave Y.1.5 — Tests
- [x] Y15-031: Security test: verify JWT without secret fails startup
- [x] Y15-032: Security test: verify revoked token returns 401
- [x] Y15-033: Security test: verify cross-tenant document access returns 403/404
- [x] Y15-034: Security test: verify cross-tenant attachment delete returns 403
- [x] Y15-035: Integration test: concurrent document number generation produces unique numbers
- [x] Y15-036: Integration test: concurrent comment creation maintains correct ordering
- [x] Y15-037: Integration test: delete with storage failure doesn't leave orphaned DB record
- [x] Y15-038: Playwright E2E: active sessions page shows current session, can revoke other sessions
- [x] Y15-039: Container test: verify backend container runs as non-root user
- [x] Y15-040: Container test: verify all required env vars are validated on startup

---

## Wave P0 (REMOVED)

> Wave P0 focused on PDF extraction quality. This entire wave was removed as part of Wave Y which pivots to DOCX/PPTX only. PDF support is no longer in scope.

## Wave T - Audit, Analytics, and Contract Safety

### Contracts & Schema Safety
- [x] T-001: Add consumer-driven contract test suite for audience-related API payloads (`/api/v1/documents`, `/api/v1/portal/documents`, `/api/v1/public/documents`) — verify response shapes match frontend DTO expectations.
- [x] T-002: Create contract fixture files in `backend/tests/contracts/audience/` with frozen request/response samples for company-assignment and visibility endpoints.
- [x] T-003: Add provider-side verification tests that validate backend responses against the contract fixtures on every CI run.
- [x] T-004: Add schema versioning headers (`X-API-Schema-Version`) to assignment endpoints (`/documents/{id}/companies`) and document the version evolution policy in `docs/deprecation-policy.md`.
- [x] T-005: Create `backend/app/errors/audience_errors.py` with a typed error-code catalog (e.g., `AUDIENCE_001` through `AUDIENCE_020`) and a lockfile `docs/contracts/audience-error-codes.json` that CI checks for backwards-compatible changes only.

### Audit Trail Hardening
- [x] T-006: Add `assignment_diff` field to `AuditLog` entries — store old→new company list whenever document-company assignments change via `document_service.py`.
- [x] T-007: Add cryptographic signing (HMAC-SHA256 with rotatable key from `config.py`) to visibility-change audit records so tampering is detectable.
- [x] T-008: Define an audience event taxonomy enum (`AudienceEventType`) in `models/__init__.py` covering: `ASSIGNMENT_CREATED`, `ASSIGNMENT_REMOVED`, `VISIBILITY_CHANGED`, `AUDIENCE_SNAPSHOT_TAKEN`, `AUDIENCE_ROLLBACK` — use in all audience audit entries.
- [x] T-009: Add `GET /api/v1/audit/export` endpoint with CSV/JSON format parameter, date-range filter, and `manager`+ role gate — wire through `analytics_service.py`.
- [x] T-010: Add compliance redaction middleware that strips PII (email, IP) from audit responses when the requesting user lacks `system_admin` role.

### Analytics Segmentation
- [x] T-011: Extend `AnalyticsOverview` schema with `by_audience_type` breakdown (internal vs. client-visible vs. public) — update `analytics/overview.py` aggregation query.
- [x] T-012: Add company-scoped analytics endpoint `GET /api/v1/analytics/company/{company_id}` returning document count, view count, and engagement stats for that company — gate by `admin`+ role and tenant isolation.
- [x] T-013: Add exposure-risk metric: count of documents that transitioned from `internal` to `public` visibility in the last 30 days — surface in analytics overview and admin dashboard.
- [x] T-014: Add assignment-churn metric: number of company-assignment add/remove operations per document over trailing 90 days — return in document detail analytics.

### Governance & Alerting
- [x] T-015: Add `POST /api/v1/admin/alerts/audience-rules` endpoint to configure threshold-based alerts (e.g., "alert if >5 visibility changes in 1 hour for same document") — store rules in `system_settings`.
- [x] T-016: Add admin action reason-capture: require a `reason` string field on visibility-change and force-publish requests — persist in audit log `details` JSON.
- [x] T-017: Build monthly audience governance report generator as a management command (`backend/scripts/audience_report.py`) that outputs a summary of all visibility changes, assignment churn, and exposure events — output as Markdown compatible with the `doc` skill.
- [x] T-018: Add `GET /api/v1/admin/access-history/{company_id}` endpoint returning timeline of documents that company gained/lost access to.

### Wave T — Backend Tests
- [x] T-019: Unit tests for audience contract fixtures — load each fixture, validate against current Pydantic schemas, assert no drift.
- [x] T-020: Unit tests for `AudienceEventType` taxonomy — verify every audit log creation path uses a valid taxonomy value.
- [x] T-021: Integration test for `GET /api/v1/audit/export` — verify CSV output, date filtering, role gating (403 for viewer/editor).
- [x] T-022: Integration test for signed audit records — create a visibility change, fetch the audit entry, verify HMAC signature with test key.
- [x] T-023: Integration test for exposure-risk and assignment-churn metrics — seed transitions, verify counts.
- [x] T-024: Integration test for compliance redaction — same audit entry returns PII for system_admin, redacted for manager.

### Wave T — Frontend Tests
- [x] T-025: Playwright E2E test `e2e/audit-analytics.spec.ts` — login as manager, navigate to analytics, verify audience-type breakdown renders, export CSV and verify download.
- [x] T-026: Playwright E2E test for admin alert rules page — create a rule, verify it appears in list, delete it.
- [x] T-027: Component test for `AnalyticsDashboardPage` — mock API, verify audience segmentation charts render with correct data.
- [x] T-028: Component test for reason-capture dialog on visibility change — verify the dialog enforces non-empty reason before submitting.

---

## Wave U — Security, Resilience, and Operational Controls

### Tenant Isolation & Attack Surface
- [x] U-001: Add cross-tenant assignment attack test suite — authenticate as tenant-A user, attempt to assign tenant-B companies to tenant-A documents, verify 403/404.
- [x] U-002: Add fuzz tests for audience API inputs — use `hypothesis` to generate random payloads for `/documents/{id}/companies`, verify no 500 errors (only 400/422).
- [x] U-003: Add rate limiting to assignment endpoints — configure in `config.py` (`ASSIGNMENT_RATE_LIMIT_REQUESTS=30`, `ASSIGNMENT_RATE_LIMIT_WINDOW=60`), enforce via existing rate-limit middleware.
- [x] U-004: Add bulk-assignment idempotency keys — extend `IdempotencyKeyRecord` usage to `POST /documents/{id}/companies/bulk` endpoint.

### Concurrency & Reliability
- [x] U-005: Add optimistic concurrency check for visibility updates — use `Document.row_version` to prevent lost updates when two admins change visibility simultaneously, return 409 on conflict.
- [x] U-006: Make assignment command handling replay-safe — ensure re-processing the same assignment event (via outbox replay) produces identical state.
- [x] U-007: Add background reconciliation worker (`backend/app/workers/assignment_reconciler.py`) that periodically checks `document_company_assignments` for orphaned entries (company deactivated but assignment remains).
- [x] U-008: Add dead-letter handling — if assignment domain event fails processing 3 times, move to `DomainEventOutbox` with status `dead_letter` and emit admin notification.
- [x] U-009: Tune retry policy for assignment jobs — exponential backoff with jitter, max 5 attempts, configurable via `config.py`.

### Operational Controls
- [x] U-010: Add chaos test for publish-with-audience-gate path — simulate DB failure mid-publish, verify rollback leaves document in `draft` state.
- [x] U-011: Add feature flag `FEATURE_FLAG_NEW_AUDIENCE_RULES` in `feature_flags.py` with gradual rollout support (percentage-based).
- [x] U-012: Add kill-switch `FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT` — when disabled, audience checks become advisory warnings instead of hard blocks.
- [x] U-013: Add safe-mode fallback for publish audience gates — if audience validation service is unreachable, allow publish with audit warning (configurable via system settings).
- [x] U-014: Write incident runbook `docs/chaos/exposure-incident-runbook.md` for exposure events (document accidentally made public).
- [x] U-015: Add staging smoke test suite (`backend/tests/scenarios/audience_smoke.py`) — 10 critical audience paths run as a single pytest marker `@pytest.mark.smoke`.

### Wave U — Tests
- [x] U-016: Playwright E2E test for concurrent visibility change — open document in two browser contexts, change visibility in both, verify conflict toast in second tab.
- [x] U-017: Backend integration test for kill-switch — disable flag, attempt publish missing audience, verify it succeeds with warning.
- [x] U-018: Backend test for dead-letter handling — fail event processing, verify DLQ entry and notification.
- [x] U-019: Security test: verify all `/api/v1/` audience endpoints return 401 without token and 403 with insufficient role.

---

## Wave V — Performance and Developer Productivity

### Performance
- [x] V-001: Create audience query benchmark suite (`backend/tests/scenarios/audience_benchmarks.py`) — measure p50/p95 latency for assignment list, document-with-companies, and search-with-audience-filter with 10K documents.
- [x] V-002: Add company assignment load-test scenario in `scripts/load_test_collaboration.py` — simulate 50 concurrent assignment updates.
- [x] V-003: Set document-detail payload size budget: max 50KB for `/api/v1/documents/{id}` response — add CI check that fails on regression.
- [x] V-004: Add company lookup caching in `document_service.py` — cache company name/id mappings for 5 minutes using in-memory LRU (no external cache dependency).
- [x] V-005: Add batched assignment update endpoint `PUT /documents/{id}/companies/batch` — accept array of company IDs, single DB transaction.
- [x] V-006: Add pagination performance tuning for assignment listings — keyset pagination instead of offset for tenant-scoped queries.
- [x] V-007: Add DB index on `document_company_assignments(document_id, tenant_id)` if missing — verify with `EXPLAIN QUERY PLAN`.
- [x] V-008: Add query plan regression check script (`scripts/architecture_checks/query_plans.py`) — run EXPLAIN on critical queries, fail if sequential scan on large tables.

### Developer Productivity
- [x] V-009: Create test data factory for audience edge cases (`backend/tests/factories/audience_factory.py`) — helper functions to create documents with specific visibility + company assignment combinations.
- [x] V-010: Create scenario builder for review+audience flows (`backend/tests/scenarios/review_audience_scenario.py`) — parameterized test that covers the full submit→approve→publish cycle with audience gates.
- [x] V-011: Add one-click local audience smoke command — `make test-audience-smoke` or npm script that runs the 10 critical audience tests.
- [x] V-012: Add PR bot check via CI that detects audience contract drift — compare `audience-error-codes.json` against `main` branch, comment on PR if codes removed.
- [x] V-013: Add architecture lint rule — no direct SQL queries in route handlers (must go through service/repository layer) — add to `scripts/architecture_checks/`.
- [x] V-014: Identify and remove legacy audience code paths from pre-Wave-S implementation — document removed files in `progress.txt`.
- [x] V-015: Update `docs/context-ownership.md` with audience domain module ownership map.

### Wave V — Frontend Tests
- [x] V-016: Add Storybook stories for `VisibilityBadge` in all visibility modes (internal, client, public, draft).
- [x] V-017: Frontend render performance test — measure and assert `DocumentsPage` renders <100 documents in <2 seconds (use React profiler in test).
- [x] V-018: Component tests for `CompanySelector` — verify search, pagination, keyboard navigation, bulk remove chips.

---

## Wave W — Core Website Account Experience

### Authentication & Session
- [x] W-001: Add email verification flow — on registration/invitation-accept, send verification email (use `email_service.py`), block login until verified, add `is_email_verified` column to `User` model.
- [x] W-002: Add password reset flow — `POST /auth/forgot-password` sends reset email, `POST /auth/reset-password` validates token from `PasswordReset` model and updates password.
- [x] W-003: Add session management page — list active sessions (browser, last active, IP), allow revoking individual sessions, auto-expire after configurable inactivity timeout.
- [x] W-005: Add login anomaly detection — flag logins from new IP/device and log as security event.
- [x] W-006: Add account lockout — lock after 5 failed login attempts (configurable in `config.py`), auto-unlock after 30 minutes, admin manual unlock endpoint.

### Profile & Preferences
- [x] W-007: Add profile settings page (`ProfileSettingsPage.tsx`) — editable full_name, username display, read-only email and role.
- [x] W-008: Add notification preferences — user can toggle email notifications per type (review assigned, document updated, mention, etc.) — store in User model JSON field `notification_preferences`.
- [x] W-009: Add timezone and locale preferences — store user timezone, use for all date formatting in frontend + email templates.
- [x] W-010: Add avatar upload — accept image, resize to 200x200, store via `storage_service.py`, add `avatar_url` to User model.
- [x] W-011: Add security events page — display login history, password changes, and session revocations.
- [x] W-012: Add device session tracking with revoke controls — fingerprint browser sessions, allow "sign out everywhere" action.

### Onboarding
- [x] W-013: Add welcome onboarding checklist component — after first login, show guided checklist: "Set up profile", "Explore documents", "Set notification preferences" — persist completion state.
- [x] W-014: Add first-company setup wizard for admins — guided flow to create first company (Intel client), invite first users, create first document.
- [x] W-015: Add role-based onboarding variants — viewers see "Browse documents" flow, editors see "Create your first document" flow, admins see full setup wizard.
- [x] W-016: Add guided empty states — when a page has no data (no documents, no reviews), show contextual help with CTA to create first item.
- [x] W-017: Add in-app product tour framework using `react-joyride` or similar — define tours for main workflows, run on first visit to each major page.

### UI/UX Fixes & Polish
- [x] W-026: Fix dashboard stats — replace filtering the 5-item paginated result with a dedicated stats/summary API call so counts reflect the full dataset, not just the last page.
- [x] W-027: Remove dead `Sidebar.tsx` and `Header.tsx` components — neither is imported anywhere in the app; delete both files and remove any stale references.
- [x] W-028: Fix login page first-visit redirect — remove the `sessionStorage` guard `useEffect` in `LoginPage.tsx` that bounces users away from `/login` when they navigate there directly.
- [x] W-029: Add "Forgot password?" link to `LoginPage.tsx` — `POST /auth/forgot-password` endpoint already exists; wire up the link and a minimal reset-request form.
- [x] W-030: Add global toast notification system — install `sonner`, mount `<Toaster>` in `App.tsx`, create a `useToast` hook; replace all silent mutation success/error paths with toast feedback.
- [x] W-031: Add `ErrorBoundary` components — wrap each major route section in a React error boundary to prevent full-page blank crashes on runtime JS errors; show a "Something went wrong — Reload" fallback.
- [x] W-032: Unify notification state — replace `NotificationBell`'s local `useState` + `setInterval` polling with the same React Query query key used by `NotificationsPage` so the badge and the full-page list always reflect the same data.
- [x] W-033: Add mobile hamburger menu to internal portal `Layout` — the horizontal `flex-wrap` nav overflows on small screens; add a responsive collapse/expand menu matching the Public and Customer layout patterns.
- [x] W-034: Unify portal header backgrounds — `PublicLayout` uses `bg-white/80` while Internal and Customer layouts use `bg-sky-100/85`; standardise to a consistent style across all three.
- [x] W-035: Fix login page logo colour — `LoginPage` uses `bg-sky-500` for the "DP" square while all in-app headers use `bg-slate-900`; update the login logo to match.
- [x] W-036: Differentiate `company` and `client` visibility badges in `VisibilityBadge.tsx` — both currently resolve to identical amber colour and `Lock` icon; give each a distinct colour and icon.
- [x] W-037: Replace emoji nav icons with Lucide icons in `routes.ts` — emoji render inconsistently across OS and don't scale cleanly; replace `📊`, `📄`, `✅`, etc. with matching Lucide icon components.
- [x] W-038: Paginate `NotificationsPage` — replace `api.getNotifications(false, 500)` with cursor-based or page-based loading so the page never loads 500 items in a single request.
- [x] W-039: Add skeleton screens for main loading states — replace spinner-only and plain "Loading..." text on `DocumentsPage`, `DashboardPage`, `UsersPage`, and `ReviewsPage` with layout-shaped skeleton placeholders.
- [x] W-040: Fix uncontrolled search input bug in `CustomerDocumentsPage` — the search field uses `defaultValue` and does not clear the URL `search` param when the user clears the field; convert to a controlled input.
- [x] W-041: Add input debounce to `UsersPage` and `DocumentsPage` search — both fire on every keystroke with no throttle; add 300 ms debounce consistent with `CompanySelector`.

### Wave W — Tests
- [x] W-018: Backend integration tests for email verification — register, verify email, login succeeds; register, skip verify, login blocked.
- [x] W-020: Backend integration tests for account lockout — 5 failed logins, verify locked, wait/unlock, verify access restored.
- [x] W-021: Playwright E2E test for profile settings — update name, save, reload, verify persisted.
- [x] W-022: Playwright E2E test for password reset flow — request reset, extract token, submit new password, login with new password.
- [x] W-023: Playwright E2E test for onboarding checklist — new user login, verify checklist appears, complete items, verify checklist dismissed.
- [x] W-024: Component test for `NotificationPreferences` — toggle switches, save, verify API call payload matches selections.
- [x] W-025: Component test for `AvatarUpload` — select image, verify preview, submit, verify upload API called.
- [x] W-042: Component test for global toast system — trigger a mutation success and a mutation error, verify toast appears with correct message and variant.
- [x] W-043: Playwright E2E test for mobile nav — resize viewport to 375 px, verify hamburger button visible, click it, verify nav items appear, click a nav item, verify navigation.
- [x] W-044: Component test for `VisibilityBadge` — verify `company` and `client` modes render distinct icons and colours.

---

## Wave X — Collaboration and Content UX

### Collaboration Features
- [x] X-001: Add document mention notifications — when `@username` appears in comment or document body, create notification for mentioned user.
- [x] X-002: Improve comment threading — support nested replies (2 levels deep), add collapse/expand, show reply count.
- [x] X-003: Add rich text diff view component — side-by-side HTML diff of two version contents using `diff-match-patch`.
- [x] X-004: Add side-by-side version compare page — select two versions from dropdown, render diff view, highlight additions/removals.
- [x] X-005: Add draft autosave recovery — on unexpected disconnect, save TipTap state to `localStorage`, on reconnect offer "Restore unsaved changes?" dialog.
- [x] X-006: Add conflict resolution UX for concurrent edits — when Yjs merge produces conflicts, highlight conflicting regions and let user choose resolution.
- [x] X-007: Add watch/follow document feature — user can "follow" a document and receive notifications on any update, store in new `document_watchers` table.

### Document Viewer
- [x] X-008: **SECURITY** Fix XSS vulnerability in public and customer document pages — `PublicDocumentPage` and `CustomerDocumentPage` render `doc.content` via `dangerouslySetInnerHTML` with no sanitisation; pipe both through the existing `sanitizeHtmlForPreview()` utility already used by the internal viewer.
- [x] X-009: Fix broken Unicode characters in `InlineCommentPopups.tsx` — the "🔒 Private" label and loading spinner render as corrupted `??` / `?` placeholder characters; restore correct emoji or replace with Lucide icons.
- [x] X-010: Fix broken Unicode characters in `TocPanel.tsx` — H1/H2 level indicators render as `?` instead of bullet/arrow icons; replace with Lucide icons.
- [x] X-011: Replace ASCII `<-` arrow in `DocumentHeaderCard.tsx` with the `ArrowLeft` Lucide icon (already imported elsewhere in the component tree).
- [x] X-012: Add match counter and next/previous navigation to in-document search — display an "N of M" count badge and ↑↓ arrow buttons in the `PreviewCanvas` search bar; the underlying `applyHighlights()` highlight logic is already in place.
- [x] X-013: Restore scroll position when returning to a document — on mount, if a `ReadingProgress` record exists for the current user+document, scroll the preview pane to the corresponding position.
- [x] X-014: Remove duplicate document title in non-fullscreen viewer — the title appears in both `DocumentHeaderCard` and the `PreviewCanvas` blue bar simultaneously; suppress the canvas bar title when not in fullscreen.
- [x] X-015: Add reading time estimate to `DocumentHeaderCard` — calculate from document HTML word count at ~200 wpm and display as "~8 min read" alongside the document number.
- [x] X-016: Add counts to `DocumentTabs` labels — show "Comments (4)", "Attachments (2)", "Versions (3)" using data already fetched in `detailPageBundle`; show 0 gracefully.
- [x] X-017: Extract shared `FullscreenTopBar` component — the fullscreen topbar (sky gradient, Exit Fullscreen button, Reading width / Full width toggles) is copy-pasted identically in `DocumentDetailPage`, `PublicDocumentPage`, and `CustomerDocumentPage`; extract to a single reusable component.
- [x] X-018: Fix TOC panel `maxHeight` magic number — replace `style={{ maxHeight: 'calc(70vh - 50px)' }}` with `flex-1 overflow-y-auto h-0` so the TOC fills available height dynamically without overflowing on short screens.
- [x] X-019: Fix inline comment popup z-ordering in fullscreen mode — the popup uses `position: fixed` and clips behind the sticky fullscreen topbar; offset `top` by the topbar height or use a portal anchored to the scroll container.
- [x] X-020: Improve collapsed TOC rail — when the TOC is collapsed to its 40 px narrow state, show the active section label rotated 90° so users can see where they are without reopening the panel.
- [x] X-021: Add "Copy link to section" to TOC — show a link icon on hover next to each TOC entry; click copies an anchor URL (`/documents/{id}#heading-id`) to clipboard (anchor IDs are already generated per heading).
- [x] X-022: Add print-friendly layout — add a CSS `@media print` stylesheet that hides the header, tabs, and sidebar; add a "Print" button to `DocumentHeaderCard` actions.
- [x] X-023: Add category breadcrumb to public portal document page — display "Home / {Category} / {Title}" above the hero header so users understand their location in the content hierarchy.

### Document Renderer Upgrade — `html-react-parser`
Replace all `dangerouslySetInnerHTML` usages in the document viewer with `html-react-parser` so content becomes a proper React element tree. Content storage stays as HTML (TipTap output, PDF-extracted HTML, file-upload conversions) — only the render layer changes.

- [x] X-024-a: Install `html-react-parser` — add to `frontend/package.json`, create a shared `parseDocumentHtml(html: string, options?)` wrapper in `frontend/src/lib/documentRenderer.tsx` that accepts the sanitized HTML string and an optional `replace` transform and returns `ReactNode`.
- [x] X-024-b: Replace `dangerouslySetInnerHTML` in `PreviewCanvas.tsx` — pass sanitized content through `parseDocumentHtml`; attach `onMouseUp` handlers directly to `<p>` and heading elements for inline comment selection instead of the current DOM listener approach.
- [x] X-024-c: Replace `dangerouslySetInnerHTML` in `PublicDocumentPage.tsx` and `CustomerDocumentPage.tsx` — use the same `parseDocumentHtml` wrapper (also resolves the XSS items X-008); run sanitizer inside the wrapper so callers can't bypass it.
- [x] X-024-d: Replace `dangerouslySetInnerHTML` in `ViewerDocumentPage.tsx` — apply same wrapper for consistency.
- [x] X-024-e: Add element-level transform rules inside `parseDocumentHtml`:
  - `<pre><code>` → swap in `react-syntax-highlighter` (Prism) with auto-detected language for syntax-coloured code blocks.
  - `<table>` → wrap in `<div className="overflow-x-auto">` so wide tables scroll on mobile instead of breaking layout.
  - `<img>` → replace with a `<img loading="lazy" decoding="async">` element so images are lazy-loaded.
  - `<a href>` — external links get `target="_blank" rel="noopener noreferrer"` automatically; internal `/documents/` links use React Router `<Link>` for client-side navigation.
- [x] X-024-f: Write unit tests for `parseDocumentHtml` — verify each transform rule (code block, table scroll wrapper, lazy image, external link attributes, internal link → router Link) and verify XSS vectors (`<script>`, `onerror`, `javascript:` href) are stripped before parsing.

### Document Readability & Reading UX
- [x] X-025-a: **Narrow the reading column** — reduce `document-preview-paper` max-width from 920px to 720px (≈70 characters per line at 16px IBM Plex Serif). The paper card stays centred; the grey pane background already fills the sides. This is the single highest-impact readability change.
- [x] X-025-b: Add a **visual reading progress bar** — thin (3px) sky-600 bar pinned to the top of the `document-preview-pane`; width driven by the `scrollProgress` value already tracked in state. No new backend calls needed.
- [x] X-025-c: Add **font size A−/A+ controls** in `PreviewToolbar` — three steps (small 0.9rem / default 1rem / large 1.15rem); persist selection in `localStorage` under `doc-font-size`; apply as a CSS custom property on `document-preview-content`.
- [x] X-025-d: Add **reading theme toggle** — cycle between Light (current white paper), Sepia (`#fdf6e3` background, `#5c4b32` text), and Dark (`#1a1f2e` background, `#d4dbe8` text) modes; persist in `localStorage` under `doc-theme`; implemented as a class on the paper element with corresponding CSS blocks in `index.css`.
- [x] X-025-e: Add `hyphens: auto` to `.document-preview-content p` and `.document-preview-content li` — tables already have it; body text paragraphs don't, causing long words to break jarringly on narrow viewports.
- [x] X-025-f: Add **heading anchor links** — on hover of any H1–H3 inside `.document-preview-content`, show a `#` icon (Lucide `Link2`) to the left; click copies the anchor URL (`/documents/{id}#{anchorId}`) to clipboard. IDs are already injected by `processHtmlIntoSections`.
- [x] X-025-g: Add **copy button on code blocks** — after the `html-react-parser` upgrade (X-024-b), each `<pre><code>` becomes a React component; add a small absolute-positioned `Copy` button (Lucide `Copy`) in the top-right corner; on click, write code text to clipboard and show a 2s "Copied!" confirmation.
- [x] X-025-h: Add **image lightbox** — wrap each `<img>` inside `.document-preview-content` in a click handler that opens a full-viewport overlay showing the image at its natural size with a close button. No third-party library needed; a small `ImageLightbox.tsx` component with a React portal is sufficient.
- [x] X-025-i: Add **keyboard shortcuts** for the document viewer — `/` focuses the in-page search input, `J`/`K` scrolls to next/previous TOC section, `F` toggles fullscreen, `Esc` closes any open popup (comment form, lightbox, section editor). Register on `keydown` in `DocumentPreview` and display a keyboard shortcut hint on hover of the relevant controls.
- [x] X-025-j: Add **callout box styles** — add CSS classes `callout-info`, `callout-warning`, `callout-tip`, `callout-danger` to `index.css` with left-border accent colours and light background tints. Add a TipTap extension or post-process rule to detect common patterns (e.g. a `<div class="callout*">` from pasted Word content) and apply the correct class.
- [x] X-025-k: Add **sticky current-section indicator** — a slim bar below the preview toolbar that shows the active H2 text (from `activeHeading` state already tracked). Fades in when the user has scrolled past the first section. Clicking it scrolls back to that heading.
- [x] X-025-l: Write **component tests for reading UX controls** — font size persists across remounts, theme class applied correctly for all three modes, progress bar width matches scroll percentage, anchor copy writes correct URL to clipboard.

### Content Management
- [x] X-024: Add bookmark/favorites UI — already has `Bookmark` model, add UI toggle (star icon) on document cards and detail page header.
- [x] X-025: Add recent activity feed on dashboard — show last 20 actions across all documents the user has access to (created, edited, published, commented).
- [x] X-026: Add custom tags/labels editor in document detail — inline tag input with autocomplete from existing tags, tenant-scoped.
- [x] X-027: Add saved filters/views on documents page — save current filter combination (status, category, company, date range) as a named view, persist in `SavedSearch`.
- [x] X-028: Add bulk metadata editing — select multiple documents in list view, batch-update category, visibility, or company assignments.
- [x] X-029: Add smart duplicate detection — on document create, check title similarity (Levenshtein) against existing documents in tenant, warn if >80% match.
- [x] X-030: Add template library — pre-defined document templates (Release Notes, Technical Spec, API Guide, etc.) that pre-fill content structure.
- [x] X-031: Add snippet/boilerplate library — reusable content blocks (disclaimers, legal notices, standard headers) insertable from editor toolbar.

### Workflow Enhancements
- [x] X-032: Add approval SLA reminders — if review request is pending >48 hours (configurable), send reminder notification to reviewer, escalate to manager after 96 hours.
- [x] X-033: Add due date field to documents + calendar integration — optional due date, show overdue badge, support iCal export.
- [x] X-034: Add knowledge base category navigation — tree sidebar for `/docs` public page with nested categories, expand/collapse.
- [x] X-035: Polish archive/restore UX — add "Archived" filter on documents page, one-click restore, confirm dialog for archive.
- [x] X-036: Add print-friendly document layout — CSS print stylesheet, "Print" button in document detail header, optimized for A4.

### Wave X — Tests
- [x] X-037: Unit test for `sanitizeHtmlForPreview` (security regression) — verify XSS vectors (`<script>`, `onerror`, `javascript:` href) are stripped by the sanitiser.
- [x] X-038: Component test for `DocumentTabs` with counts — render with mock bundle data, verify badge counts displayed correctly for comments, attachments, and versions.
- [x] X-039: Component test for extracted `FullscreenTopBar` — verify Exit and width-toggle buttons render in both reading and fluid modes.
- [x] X-040: Playwright E2E for in-document search — open a document, type a search term, verify match count badge appears, verify Next/Prev buttons move focus to correct occurrence.
- [x] X-041: Backend unit test for mention parsing — extract `@username` from content string, verify notification created.
- [x] X-042: Backend integration test for duplicate detection — create two similar-titled documents, verify warning returned.
- [x] X-043: Backend integration test for approval SLA — create review, advance time, verify reminder notification generated.
- [x] X-044: Playwright E2E for version compare — create two versions, navigate to compare view, verify diff rendered.
- [x] X-045: Playwright E2E for bookmarks — bookmark a document, navigate to dashboard, verify it appears in favorites section.
- [x] X-046: Playwright E2E for bulk metadata edit — select 3 documents, bulk-change category, verify all updated.
- [x] X-047: Component test for `TemplateLibrary` — render library, select template, verify content pre-filled in editor.
- [x] X-048: Component test for `TagEditor` — type tag, verify autocomplete suggestions, add tag, verify chip rendered.
- [x] X-049: Component test for `DraftRecoveryDialog` — simulate stored draft, verify dialog shown, accept recovery, verify content restored.

---

## Wave X.1 — Private & Group Messaging + Customer Support Chat

### Why this wave exists
Users need a way to communicate privately about documents without those conversations being visible to everyone. Current comments are tied to documents and visible to all document viewers. Additionally, customer feedback needs to become a proper support conversation — not just a one-way form submission. This wave adds:
1. **Internal chat** — WhatsApp-style messaging with private 1:1 chats and group conversations for staff
2. **Customer support chat** — Helpdesk-style ticketing where customer feedback becomes a live conversation with support agents

### Status snapshot (2026-03-14)
- Core internal chat is fully functional: models, service, REST API, WebSocket real-time, frontend ChatPage with sidebar/view/header/message components, file/image upload in chat, comment-to-chat bridge, typing indicators, read receipts (backend).
- Customer support system fully functional: models, service, REST API (portal + management), WebSocket, customer portal page, agent dashboard with assignment/status/priority controls, internal notes.
- Additional UX improvements delivered: Comments tab removed from document viewer (replaced by chat), "View in document" links scroll to and highlight anchor text, chat file/image uploads with thumbnail preview.
- Remaining: tests (all 22 items), canned responses (4 items), polish features (emoji picker, read receipt UI, chat search, floating help button, agent presence indicators, handoff).

### Non-negotiable outcomes
- Internal users can start private 1:1 conversations
- Internal users can create group chats with selected participants  
- Messages are only visible to chat participants
- Customer feedback creates a support ticket
- Customers can have ongoing conversations with support agents
- Internal agents can collaborate on support tickets with internal notes
- Real-time message delivery for both internal chat and support

### In scope

**Internal Chat:**
- Private 1:1 direct messages between staff
- Group chats with selected staff members
- Real-time message delivery via WebSocket
- Message notifications, read receipts, typing indicators
- Chat history and search

**Customer Support:**
- Feedback → Support ticket auto-creation
- Customer ↔ Agent conversation (unlimited messages, not 2-level comments)
- Multiple agents can respond to same ticket
- Internal agent notes (not visible to customer)
- Ticket status workflow (open → in progress → resolved → closed)
- Canned responses for common questions

### Out of scope
- Voice/video calls
- Public channels visible to all users
- Cross-tenant messaging
- Customer-to-customer chat (only customer ↔ support)

### Bonus Deliverables (not originally scoped)
- [x] X1-B01: **Comment-to-chat bridge** — when a user comments on a document, `_bridge_comment_to_chat()` creates/finds a direct chat between commenter and document author, sends a rich context message with document link, anchor text, and formatted markdown. ChatMessage renders these as rich reference cards.
- [x] X1-B02: **Remove Comments tab from document viewer** — Comments tab removed from `DocumentTabs`, `DocumentDetailPage`, and `ViewerDocumentPage`. Inline comment popups still work and trigger the chat bridge.
- [x] X1-B03: **"View in document" anchor highlight** — Chat "View in document" links use `?highlight={encoded_anchor_text}` URL param. `DocumentPreview` reads the param, calls `applyHighlights()`, scrolls to the match with smooth animation, applies amber→yellow fade highlight that clears after 6 seconds.
- [x] X1-B04: **File/image upload in chat** — `FILE` message type added to `ChatMessage` model with `file_url`, `file_name`, `file_size`, `file_mime_type` columns. Backend upload endpoint (max 10MB, images + office docs + PDF + text/CSV). Frontend `MessageInput` with Paperclip/Image buttons, file preview. `ChatMessage` renders images as thumbnails, files as download cards. `ChatSidebar` shows "📎 filename" for file messages.

---

### Backend — Internal Chat Models & API

#### Data Models
- [x] X1-001: Create `Chat` model — `id`, `type` (direct/group), `name` (nullable for direct), `created_by`, `tenant_id`, `created_at`, `updated_at`
- [x] X1-002: Create `ChatParticipant` model — `chat_id`, `user_id`, `role` (owner/admin/member), `joined_at`, `last_read_at`, `is_muted`
- [x] X1-003: Create `ChatMessage` model — `id`, `chat_id`, `sender_id`, `content`, `message_type` (text/system/file), `created_at`, `updated_at`, `deleted_at`, + file fields (`file_url`, `file_name`, `file_size`, `file_mime_type`)
- [x] X1-004: Add Alembic migration for chat tables with proper indexes (chat_id+created_at for message ordering)
- [x] X1-005: Add foreign key constraints: ChatParticipant→User, ChatMessage→Chat, Chat→Tenant

#### Chat Service
- [x] X1-006: Create `backend/app/services/chat_service.py` with methods: `create_direct_chat`, `create_group_chat`, `add_participant`, `remove_participant`, `send_message`, `get_chat_history`, `send_file_message`
- [x] X1-007: Implement direct chat deduplication — `create_direct_chat(user_a, user_b)` returns existing chat if one exists between the two users
- [x] X1-008: Implement group chat ownership — only owner can rename, add/remove members, delete chat
- [x] X1-009: Add tenant isolation — all chat queries filter by `tenant_id`, cross-tenant chat creation fails
- [x] X1-010: Add message pagination — `get_chat_history(chat_id, before_id, limit=50)` for infinite scroll

#### Chat API Endpoints
- [x] X1-011: `GET /api/v1/chats` — list user's chats with last message preview, unread count, sorted by last activity
- [x] X1-012: `POST /api/v1/chats` — create direct or group chat, body: `{type, participant_ids, name?}`
- [x] X1-013: `GET /api/v1/chats/{id}` — get chat details with participants
- [x] X1-014: `GET /api/v1/chats/{id}/messages` — paginated message history
- [x] X1-015: `POST /api/v1/chats/{id}/messages` — send message, body: `{content}` (+ `POST /chats/{id}/messages/upload` for file messages)
- [x] X1-016: `PUT /api/v1/chats/{id}/participants` — add/remove participants (group only, owner/admin only)
- [x] X1-017: `POST /api/v1/chats/{id}/read` — mark chat as read up to latest message
- [x] X1-018: `DELETE /api/v1/chats/{id}` — delete chat (owner only for groups, either party for direct)

#### Real-Time Integration
- [x] X1-019: Extend collab-server for chat WebSocket — new `chat` namespace alongside document collaboration
- [x] X1-020: Implement chat room subscription — when user connects, join rooms for all their active chats
- [x] X1-021: Broadcast new messages to all chat participants in real-time
- [x] X1-022: Implement typing indicators — `user_typing` event with 3-second debounce
- [x] X1-023: Implement read receipts — broadcast `message_read` event when user marks chat as read

#### Notifications
- [x] X1-024: Create chat message notifications — notify participants when message arrives (if not muted, not currently viewing chat) (partial: real-time WS delivery works, no persistent Notification DB row)
- [x] X1-025: Add notification preferences for chats — `mute_chat`, `mute_group_chats`, `desktop_notifications` (mute toggle UI + backend endpoint)
- [x] X1-026: Add unread badge to header — show total unread message count across all chats

---

### Frontend — Chat UI

#### Chat Layout
- [x] X1-027: Create `ChatSidebar` component — list of chats with avatars, names, last message preview, unread badges, search filter
- [x] X1-028: Create `ChatView` component — message list with infinite scroll (load older on scroll up), message input at bottom
- [x] X1-029: Create `ChatMessage` component — sender avatar, name, timestamp, content, read receipt indicators, file/image rendering, comment-bridge cards
- [x] X1-030: Create `ChatHeader` component — chat name/participant info, group members dropdown, mute/settings, add people, delete chat
- [x] X1-031: Add chat page at `/chat` — full-width layout with sidebar + chat view, responsive collapse on mobile

#### Message Composer
- [x] X1-032: Create `MessageInput` component — multiline textarea, send button, Shift+Enter for newline, Enter to send, file/image upload buttons
- [x] X1-033: Add emoji picker — button to open emoji selector, insert at cursor position
- [x] X1-034: Add typing indicator display — "User is typing..." below messages when receiving typing events
- [x] X1-035: Add message sending state — optimistic update, show pending indicator, retry on failure (optimistic insert + "Sending..." indicator + auto-replace on WS confirm)

#### Chat Creation
- [x] X1-036: Create `NewChatModal` — tabs for "Direct Message" and "New Group"
- [x] X1-037: Direct message tab — user search/select dropdown, creates chat and navigates to it
- [x] X1-038: Group chat tab — name input, multi-select user picker, create button
- [x] X1-039: Add "Message" action to user profile cards — quick start direct chat (MessageCircle button on UsersPage)

#### Chat Features
- [x] X1-040: Implement real-time message subscription — WebSocket connection, add new messages to view instantly
- [x] X1-041: Implement read receipts UI — check marks showing sent/delivered/read status
- [x] X1-042: Add message timestamps — relative time ("2m ago") updating live, full timestamp on hover
- [x] X1-043: Add chat search — search within current chat history, highlight matching messages
- [x] X1-044: Add document linking (optional) — "@document-123" syntax creates clickable link to document

#### Group Management
- [x] X1-045: Create `GroupSettingsModal` — rename group, view/manage members, leave group, delete group (owner)
- [x] X1-046: Add member management — owner can promote to admin, admin/owner can remove members
- [x] X1-047: Add "Add People" button in group header — opens user picker to add new participants
- [x] X1-048: Show system messages for member changes — "Alice added Bob to the group", "Carol left the group"

---

### Customer Support Chat (Feedback → Helpdesk)

> When a customer submits feedback, it creates a support ticket that becomes a private chat between the customer and internal support staff. Think of it like WhatsApp customer service — the customer sees only their conversation, while internal team members can collaborate to help.

#### Backend — Support Ticket Models
- [x] X1-061: Create `SupportTicket` model — `id`, `customer_id`, `subject`, `status` (open/in_progress/resolved/closed), `priority` (low/normal/high/urgent), `category`, `created_at`, `resolved_at`, `tenant_id`
- [x] X1-062: Create `SupportTicketMessage` model — `id`, `ticket_id`, `sender_id`, `sender_type` (customer/agent), `content`, `is_internal_note` (visible only to agents), `created_at`
- [x] X1-063: Create `SupportTicketAssignment` model — `ticket_id`, `agent_id`, `assigned_at`, `is_primary` (who is main handler)
- [x] X1-064: Add Alembic migration for support tables with indexes (ticket_id+created_at for message ordering, status for filtering)
- [x] X1-065: Link `Feedback` model to `SupportTicket` — add `support_ticket_id` FK, feedback submission creates ticket automatically

#### Backend — Support Service
- [x] X1-066: Create `backend/app/services/support_service.py` with methods: `create_ticket_from_feedback`, `assign_agent`, `add_message`, `add_internal_note`, `change_status`, `get_ticket_history`
- [x] X1-067: Auto-create ticket when feedback submitted — `create_ticket_from_feedback(feedback)` extracts subject from feedback, sets initial status to "open"
- [x] X1-068: Support multiple agents per ticket — any assigned agent can respond, all see full history including internal notes
- [x] X1-069: Internal notes feature — agents can leave notes visible only to other agents (not customer), useful for handoffs
- [x] X1-070: Status transitions — open → in_progress (when agent responds) → resolved (agent marks) → closed (customer confirms or auto-close after 7 days)
- [x] X1-071: Customer isolation — customer only sees their own tickets, cannot see other customers' conversations

#### Backend — Support API Endpoints

**Customer-Facing Endpoints:**
- [x] X1-072: `GET /api/v1/portal/support/tickets` — list customer's own tickets with status, last message preview
- [x] X1-073: `GET /api/v1/portal/support/tickets/{id}` — get ticket details and full message history (excluding internal notes)
- [x] X1-074: `POST /api/v1/portal/support/tickets/{id}/messages` — customer sends message to ticket
- [x] X1-075: `POST /api/v1/portal/support/tickets/{id}/close` — customer closes resolved ticket

**Agent-Facing Endpoints (internal users):**
- [x] X1-076: `GET /api/v1/support/tickets` — list all tickets with filters (status, priority, assigned_to_me, unassigned)
- [x] X1-077: `GET /api/v1/support/tickets/{id}` — get ticket with full history including internal notes
- [x] X1-078: `POST /api/v1/support/tickets/{id}/messages` — agent sends visible reply to customer
- [x] X1-079: `POST /api/v1/support/tickets/{id}/notes` — agent adds internal note (not visible to customer)
- [x] X1-080: `PUT /api/v1/support/tickets/{id}/assign` — assign agent(s) to ticket
- [x] X1-081: `PUT /api/v1/support/tickets/{id}/status` — change ticket status
- [x] X1-082: `PUT /api/v1/support/tickets/{id}/priority` — change priority

#### Real-Time Support Chat
- [x] X1-083: Extend WebSocket for support tickets — new `support` namespace, customer and agents join ticket room
- [x] X1-084: Real-time message delivery — when agent replies, customer sees it instantly (and vice versa)
- [x] X1-085: Real-time status updates — when status changes, both customer and agents see update (partial: WS event structure exists but REST status change doesn't trigger WS broadcast)
- [x] X1-086: Agent typing indicator — show "Support is typing..." to customer when agent is composing
- [x] X1-087: Notify assigned agents on new customer message — push notification + in-app badge (partial: WS real-time works, no persistent notification)

---

### Frontend — Customer Support Portal

#### Customer View (Portal Side)
- [x] X1-088: Add "My Support" section to customer portal navigation
- [x] X1-089: Create `CustomerSupportPage` — list of customer's tickets with status badges, unread indicators
- [x] X1-090: Create `CustomerTicketView` — chat-style view of ticket conversation with agent(s)
- [x] X1-091: Auto-create ticket from feedback form — feedback success shows link to support tickets page
- [x] X1-092: Add "Help" floating button on all portal pages — opens feedback form or shows existing open tickets

#### Agent View (Internal Side)
- [x] X1-093: Add "Support" section to internal navigation — only visible to users with support role/permission
- [x] X1-094: Create `SupportDashboard` — ticket queue with filters (my tickets, unassigned, all open), search, sort by priority/age
- [x] X1-095: Create `SupportTicketView` — full ticket history with customer messages, agent replies, internal notes (distinguished visually)
- [x] X1-096: Add internal note composer — separate from regular reply, clearly marked "Internal Note - Not visible to customer"
- [x] X1-097: Add quick actions bar — Assign to me, Change priority, Mark resolved, Add canned response
- [x] X1-098: Add ticket assignment UI — dropdown to assign/reassign agents, show current assignees with avatars

#### Agent Collaboration
- [x] X1-099: Multiple agents can view and respond to same ticket — all see same history
- [x] X1-100: Show "Other agents viewing" indicator — when multiple agents have ticket open
- [x] X1-101: Add @mention for agents in internal notes — notify mentioned agent specifically
- [x] X1-102: Add handoff feature — primary agent can transfer ownership to another agent with internal note explaining context

#### Canned Responses & Templates
- [x] X1-103: Create `CannedResponse` model — `id`, `title`, `content`, `category`, `created_by`, `tenant_id`
- [x] X1-104: Add canned response management page — create/edit/delete reusable responses
- [x] X1-105: Add canned response selector in ticket view — search/filter, click to insert into message composer
- [x] X1-106: Support variables in canned responses — `{{customer_name}}`, `{{ticket_id}}`, `{{agent_name}}` auto-replaced

---

### Wave X.1 — Support Tests
- [x] X1-107: Backend unit test for `create_ticket_from_feedback` — verify ticket created with correct customer, subject extracted
- [x] X1-108: Backend unit test for internal notes — verify customer cannot see notes, agents can
- [x] X1-109: Backend unit test for status transitions — verify valid transitions, reject invalid (e.g., closed → in_progress)
- [x] X1-110: Backend integration test for multi-agent ticket — two agents respond, verify both messages appear
- [x] X1-111: Backend integration test for customer isolation — customer cannot access other customer's ticket
- [x] X1-112: Playwright E2E for customer support flow — submit feedback → see ticket created → reply → see agent response
- [x] X1-113: Playwright E2E for agent response — open ticket → reply → verify customer sees it
- [x] X1-114: Playwright E2E for internal notes — add internal note → verify hidden from customer view
- [x] X1-115: Component test for `SupportDashboard` — render tickets, filter by status, verify counts
- [x] X1-116: Component test for `CustomerTicketView` — render conversation, send message, verify display

---

### Wave X.1 — Internal Chat Tests
- [x] X1-049: Backend unit test for `chat_service.create_direct_chat` — verify deduplication (same chat returned for A→B and B→A)
- [x] X1-050: Backend unit test for group chat permissions — only owner can delete, admin can add members
- [x] X1-051: Backend unit test for tenant isolation — user cannot access chat from different tenant
- [x] X1-052: Backend integration test for message pagination — create 100 messages, verify pagination works correctly
- [x] X1-053: Backend integration test for read receipts — mark as read, verify `last_read_at` updated
- [x] X1-054: Playwright E2E for direct message — start chat with user, send message, verify delivery
- [x] X1-055: Playwright E2E for group chat — create group, add members, send message, all members see it
- [x] X1-056: Playwright E2E for real-time — open chat in two browsers, send message, verify instant appearance in other
- [x] X1-057: Component test for `ChatSidebar` — render chats, verify unread badges, search filter works
- [x] X1-058: Component test for `MessageInput` — type message, send, verify input clears
- [x] X1-059: Component test for `ChatMessage` — render with different states (sent, delivered, read)
- [x] X1-060: Accessibility test for chat — keyboard navigation, screen reader announcements for new messages

---

## Wave Y.2 — Search, Discovery, and Portal Experience

### Search & Discovery
- [x] Y2-001: Add global search with quick results dropdown — search bar in header, show top 5 results as-you-type with debounced API call, keyboard navigation.
- [x] Y2-002: Add advanced search query builder — modal with fields: title, content, category, company, tag, date range, status, visibility — generates filter object for search API.
- [x] Y2-003: Add faceted filters for portal users — sidebar filters on customer portal documents page: category, date, platform, topic — counts per facet.
- [x] Y2-004: Add relevance ranking tuning — weight title matches 3x, tag matches 2x, content matches 1x — configurable weights in `system_settings`.
- [x] Y2-005: Add search analytics dashboard — track top search queries, queries with no results, click-through rates — store in new `search_analytics` table, surface in admin analytics.
- [x] Y2-006: Add broken link detection job (`backend/app/jobs/broken_links.py`) — scan published document HTML for broken internal links, report in admin dashboard.
- [x] Y2-007: Add related documents recommendations — on document detail, show "Related Documents" section based on shared tags, category, and platform.

### Portal & Public Experience
- [x] Y2-008: Add personalized landing dashboard for customer portal — show recently viewed, documents assigned to user's company, new publications since last visit.
- [x] Y2-009: Add "recently viewed across devices" — track document views per user (use `ReadingProgress` model), show in portal sidebar.
- [x] Y2-010: Add continue-reading queue — documents the user started reading but didn't complete (progress < 100%), show "Continue Reading" section on dashboard.
- [x] Y2-011: Add public docs SEO metadata — add `<meta>` tags (description, og:title, og:description, og:image) to public document pages, generate from document metadata.
- [x] Y2-012: Add XML sitemap automation — generate `/sitemap.xml` listing all published public documents, regenerate on publish/unpublish events.
- [x] Y2-013: Add Open Graph and social preview cards — render preview images for documents using thumbnail or auto-generated card.
- [x] Y2-014: Add canonical URL strategy — ensure each public document has a single canonical URL, add `<link rel="canonical">`.
- [x] Y2-015: Add 404 and fallback experience — custom 404 page with search bar and suggested documents.

### Communication & Support
- [x] Y2-016: Add help center search integration — `/help` page with searchable FAQ, link to documentation categories.
- [x] Y2-017: Add changelog/release notes page — admin can create release note entries, display chronologically on `/changelog`.
- [x] Y2-018: Add in-app announcement banner system — admin can set a banner message (info/warning) shown across all pages, dismissible per user.
- [x] Y2-019: Add feedback widget (NPS) — periodic in-app survey ("How likely are you to recommend this platform?"), store responses in `feedbacks`.
- [x] Y2-020: Add support ticket handoff — "Contact Support" button that pre-fills context (document ID, user info, browser) into an email or external ticketing link.

### Wave Y.2 — Tests
- [x] Y2-021: Backend integration test for search ranking — create documents with specific titles/tags, search, verify result order matches weight config.
- [x] Y2-022: Backend integration test for sitemap generation — publish a document, request `/sitemap.xml`, verify URL present; unpublish, verify removed.
- [x] Y2-023: Backend integration test for broken link detection — create document with broken internal link, run job, verify report generated.
- [x] Y2-024: Playwright E2E for global search — type in header search bar, verify dropdown results, click result, verify navigation.
- [x] Y2-025: Playwright E2E for customer portal personalized dashboard — login as customer, verify "Recently Viewed" and "New for You" sections.
- [x] Y2-026: Playwright E2E for advanced search builder — open builder, set filters, search, verify results match criteria.
- [x] Y2-027: Component test for `SearchBar` — type query, verify debounced API call, verify dropdown renders results, keyboard navigation works.
- [x] Y2-028: Component test for `AnnouncementBanner` — render with message, verify displayed, dismiss, verify hidden, reload page, verify still hidden.
- [x] Y2-029: Accessibility test for public pages — run axe-core on `PublicHomePage`, `PublicDocumentsPage`, `PublicDocumentPage` — zero critical violations.

---

## Wave Z — Admin Operations and Tenant Management

### Admin Controls
- [x] Z-001: Add tenant impersonation for system admins — "View as Tenant X" mode that scopes all API calls to that tenant, with audit log entry for impersonation start/end.
- [x] Z-002: Add admin action queue with approvals — critical admin actions (tenant deletion, mass user deactivation) require approval from second system admin.
- [x] Z-003: Add bulk tenant maintenance tools — batch update tenant settings, batch send announcements to all tenants.
- [x] Z-004: Add tenant-level configuration registry — key-value settings per tenant (max users, max documents, storage quota, enabled features) editable by system admin.
- [x] Z-005: Add feature access matrix — UI table showing which features are enabled per role per tenant, editable by admin.
- [x] Z-006: Add status page integration — `GET /api/v1/admin/status` returns service health of backend, collab-server, storage, email — surface in admin dashboard.

### Tenant Lifecycle
- [x] Z-007: Add SLA/performance reporting by tenant — response time p50/p95, error rate, active users per tenant — surface in admin analytics with tenant selector.
- [x] Z-008: Add organization provisioning workflow — admin can create a new tenant + initial admin user + initial company in a single guided flow.
- [x] Z-009: Add tenant suspension/reactivation — suspend blocks all API access for tenant users (return 403 with "Account suspended"), reactivate restores access, both with audit trail.
- [x] Z-010: Add domain verification for tenant ownership — tenant admin can verify they own a domain by adding a DNS TXT record, verified domains shown in admin panel.
- [x] Z-011: Add custom branding settings — tenant can upload logo, set primary/accent colors, configure portal header text — stored in `Tenant.settings` JSON.
- [x] Z-012: Add tenant quota policy — configurable limits on users, documents, storage per tenant — enforcement in service layer with friendly error messages.

### Admin Infrastructure
- [x] Z-013: Add admin configuration change audit trail — every change to tenant config, system settings, RBAC policies logged with before/after diff.
- [x] Z-014: Add operations runbook integration page — admin page linking to runbooks in `docs/chaos/` with last-run status.
- [x] Z-015: Add tenant migration toolkit — export tenant data to JSON, import into another instance — for disaster recovery or environment promotion.
- [x] Z-016: Add cross-tenant admin boundary checks in CI — architecture test that verifies no service method crosses tenant boundary without explicit tenant_id parameter.
- [x] Z-017: Add admin API rate limiting — separate, higher rate limits for admin endpoints (500 req/min vs 100 for regular users).
- [x] Z-018: Add maintenance window scheduling — admin can schedule read-only mode with advance notification banner.

### Wave Z — Tests
- [x] Z-019: Backend integration test for tenant impersonation — impersonate, access tenant data, verify audit log, end impersonation, verify scope restored.
- [x] Z-020: Backend integration test for tenant suspension — suspend tenant, attempt API call as tenant user, verify 403.
- [x] Z-021: Backend integration test for tenant quota enforcement — set quota to 2 documents, create 2, attempt third, verify 429.
- [x] Z-022: Playwright E2E for admin tenant provisioning wizard — create tenant, verify it appears in list, login as new tenant admin.
- [x] Z-023: Playwright E2E for admin impersonation mode — impersonate, verify scoped data, exit, verify returned to admin view.
- [x] Z-024: Playwright E2E for custom branding — upload logo, set colors, switch to tenant portal view, verify branding applied.
- [x] Z-025: Component test for tenant configuration editor — modify quota, save, verify API payload.
- [x] Z-026: Architecture test for tenant boundary — scan all service files, verify no cross-tenant data access without tenant_id guard.

---

## Wave AA — Compliance, Data, and Scale Maturity

### Data Governance
- [ ] AA-001: Add data export requests workflow — user/admin can request full export of their documents and metadata, generate ZIP, email download link (GDPR Article 20).
- [ ] AA-002: Add data deletion requests workflow — user requests account deletion, admin approves, system anonymizes user data while preserving audit trail integrity.
- [ ] AA-004: Add audit log immutability hardening — append-only audit table with DB trigger preventing `UPDATE`/`DELETE`, add integrity check command.

### Security Ops
- [ ] AA-005: Add key rotation script (`backend/scripts/rotate_secrets.py`) — rotate JWT secret key with grace period (accept old key for 24 hours), rotate HMAC audit signing key.
- [ ] AA-006: Add backup/restore game-day drill script — automate: take backup, corrupt DB, restore, verify data integrity — document as runbook.
- [ ] AA-007: Add disaster recovery validation — document RTO (4 hours) and RPO (1 hour) targets, create test that verifies backup recency.
- [ ] AA-008: Add cross-region failover simulation — if S3-compatible storage configured, test failover to secondary bucket.
- [ ] AA-009: Add dependency vulnerability response pipeline — `pip-audit` + `npm audit` in CI, auto-create GitHub issue for critical CVEs.

### Compliance & Accessibility
- [ ] AA-010: Add SOC2 evidence collection script — gather: user access logs, config change logs, uptime metrics, test results — output as compliance bundle.
- [ ] AA-011: Create GDPR/CCPA policy mapping document (`docs/compliance/data-policy-mapping.md`) — map each data field to legal basis, retention period, and deletion procedure.
- [ ] AA-012: Run WCAG 2.1 AA accessibility audit on all frontend pages — fix critical issues (missing alt text, keyboard traps, color contrast).
- [ ] AA-013: Add performance budget enforcement in CI — Lighthouse score ≥80 for public pages, bundle size <500KB, first contentful paint <2s.
- [ ] AA-014: Add mobile responsiveness baseline — all public and portal pages must pass viewport test at 375px, 768px, 1024px widths.
- [ ] AA-015: Add API deprecation communication workflow — when an endpoint is deprecated, set `Sunset` header, add to `docs/deprecations.md`, send notification to API consumers.
- [ ] AA-016: Add public API version sunset tooling — scheduled job that removes deprecated endpoints after sunset date, with 30-day advance warnings.

### Wave AA — Tests
- [ ] AA-017: Backend integration test for data export — request export, verify ZIP contains all user documents, metadata, and attachments.
- [ ] AA-018: Backend integration test for data deletion — request deletion, verify user anonymized, documents attributed to "Deleted User", audit log intact.
- [ ] AA-019: Backend integration test for retention policy — create document, set retention to 0 days, run retention job, verify archived.
- [ ] AA-020: Backend test for audit immutability — attempt to UPDATE audit_logs row via raw SQL in test, verify it fails/is prevented.
- [ ] AA-021: CI test for dependency vulnerabilities — run `pip-audit` and `npm audit`, assert no critical/high severity issues.
- [ ] AA-022: Playwright accessibility test for all public pages — run `@axe-core/playwright` on 5 key public pages, assert zero critical/serious violations.
- [ ] AA-023: Playwright mobile responsiveness test — render `PublicHomePage` at 375px width, verify no horizontal scroll, verify mobile nav works.
- [ ] AA-024: Performance budget test — build frontend, assert bundle size <500KB, run Lighthouse CI on public home page.

---

## Wave AB — Experimentation and Growth Systems

### Feature Management
- [ ] AB-001: Add feature flag targeting UI — admin page to manage feature flags (existing `feature_flags.py`), add percentage rollout and tenant-targeting.
- [ ] AB-002: Add experiment assignment service — assign users to A/B test variants deterministically (hash user_id + experiment_id), store assignment in `experiment_assignments` table.
- [ ] AB-003: Add A/B test metrics guardrails — define primary metric and guardrail metrics per experiment, auto-halt experiment if guardrail metric degrades >10%.
- [ ] AB-004: Add experiment kill-switch — admin can immediately end experiment and assign all users to control/winner variant.

### Analytics & Engagement
- [ ] AB-005: Add onboarding funnel analytics — track: invitation sent → accepted → first login → first document view → first action — surface as funnel chart in admin analytics.
- [ ] AB-006: Add activation milestone tracking — define milestones (viewed 5 docs, created 1 doc, completed profile) — track per user, surface in admin user detail.
- [ ] AB-007: Add retention cohort dashboard — group users by signup week, show weekly retention rates in heatmap chart.
- [ ] AB-008: Add churn prediction baseline — flag users with no login in 30 days as "at risk", surface in admin user list.

### Integration & API
- [ ] AB-009: Add webhook registration management — admin can register webhook URLs for events (document published, review completed, user invited), deliver via `DomainEventOutbox`.
- [ ] AB-010: Add developer API key management — admin users can generate/revoke API keys for programmatic access, separate from JWT tokens.
- [ ] AB-011: Add integration health monitoring — dashboard showing webhook delivery success rates, API key usage stats, recent failures.
- [ ] AB-012: Add API developer portal page — public page documenting API endpoints (auto-generated from OpenAPI spec), with authentication guide and code examples.

### Internal Tooling
- [ ] AB-013: Add internal playbook search — admin page linking to all runbooks, architecture docs, and decision records in `docs/` — searchable index.
- [ ] AB-014: Add technical debt budgeting — track `# TODO` and `# FIXME` counts in CI, fail if count increases beyond threshold.
- [ ] AB-015: Add end-user trust center page — public page showing: security practices, data handling, compliance certifications, contact for security reports.
- [ ] AB-016: Add security questionnaire self-serve portal — FAQ-style page answering common enterprise security questions (data encryption, access controls, incident response).

### Wave AB — Tests
- [ ] AB-017: Backend integration test for experiment assignment — assign user to experiment, verify deterministic, re-assign same user, verify same variant.
- [ ] AB-018: Backend integration test for webhook delivery — register webhook, trigger event, verify HTTP POST sent to registered URL with correct payload.
- [ ] AB-019: Backend integration test for API key auth — create key, make API call with key, verify success; revoke key, verify 401.
- [ ] AB-020: Playwright E2E for feature flag admin page — create flag, set percentage rollout, verify flag state changes.
- [ ] AB-021: Playwright E2E for webhook management — register URL, trigger event, view delivery log, verify success entry.
- [ ] AB-022: Playwright E2E for developer API portal — navigate to portal page, verify endpoint documentation renders, try interactive example.
- [ ] AB-023: Component test for `RetentionCohortHeatmap` — mock data, verify heatmap renders correct cells with correct colors.
- [ ] AB-024: Component test for `OnboardingFunnel` — mock funnel data, verify stages render with correct counts and percentages.
- [ ] AB-025: Tech debt CI test — count TODO/FIXME in codebase, assert below threshold (store current count as baseline).

---

## Wave AC — Accessibility Compliance

> Dedicated accessibility wave scheduled at end of roadmap per user decision. Consolidates WCAG 2.1 AA compliance work.

### WCAG 2.1 AA Audit
- [ ] AC-001: Conduct full WCAG 2.1 AA audit on all pages using axe-core, WAVE, and manual testing — document all violations in `docs/accessibility-audit.md`.
- [ ] AC-002: Fix all Level A violations — missing alt text, empty links, missing form labels, invalid ARIA, keyboard traps.
- [ ] AC-003: Fix all Level AA violations — color contrast, resize/reflow, focus visible, status messages, error identification.
- [ ] AC-004: Add skip navigation links — "Skip to main content" link at top of every page, visible on focus.

### Screen Reader & Keyboard
- [ ] AC-005: Verify all interactive components work with screen readers (NVDA, VoiceOver) — document list, document viewer, modals, forms, comments.
- [ ] AC-006: Implement full keyboard navigation — all actions reachable without mouse, logical tab order, visible focus indicators.
- [ ] AC-007: Add ARIA live regions for dynamic content — document status changes, notification counts, real-time collaboration updates.
- [ ] AC-008: Ensure all images have meaningful alt text or are marked decorative (`alt=""`).

### Focus & State Management
- [ ] AC-009: Implement focus trapping in modals — focus stays within modal when open, returns to trigger on close.
- [ ] AC-010: Add focus management for SPA navigation — focus moves to main content area after route change.
- [ ] AC-011: Ensure all form errors are announced and linked to inputs — use `aria-describedby` and `aria-invalid`.
- [ ] AC-012: Add high contrast mode support — ensure all UI is usable with Windows High Contrast Mode.

### Testing & CI
- [ ] AC-013: Add axe-core accessibility checks to all Playwright E2E tests — fail on any critical or serious violations.
- [ ] AC-014: Add accessibility linting to CI — eslint-plugin-jsx-a11y for React components, fail build on errors.
- [ ] AC-015: Create accessibility testing checklist for PR reviews — document in `docs/accessibility-checklist.md`.
- [ ] AC-016: Add automated color contrast checking — integrate contrast checker into design system, fail if new colors don't meet AA.

### Documentation & Training
- [ ] AC-017: Document accessibility patterns in component library — each component includes accessibility notes and keyboard shortcuts.
- [ ] AC-018: Create accessibility statement page — public page describing conformance level, known issues, and contact for accessibility feedback.

### Wave AC — Tests
- [ ] AC-019: Playwright test for skip navigation — tab from page load, verify skip link appears and works.
- [ ] AC-020: Playwright test for keyboard-only document browsing — complete full flow without mouse.
- [ ] AC-021: Playwright test for screen reader announcements — verify ARIA live regions announce status changes.
- [ ] AC-022: Component test for focus management — open modal, verify focus trapped, close, verify focus returns.
- [ ] AC-023: CI accessibility regression test — run axe-core on all routes, store baseline violations, fail if count increases.

---

## Cross-Cutting: UI/UX Quality Gates (applied across all waves)

### Visual & Interaction Testing
- [ ] UX-001: Add visual regression testing with Playwright screenshots — capture baseline screenshots of 10 key pages, fail PR if pixel diff >0.5%.
- [ ] UX-002: Add responsive design test suite — every new page must pass at 375px (mobile), 768px (tablet), 1024px (laptop), 1440px (desktop).
- [ ] UX-003: Add dark mode support baseline — define CSS custom properties for colors, implement theme toggle, test all pages in both modes.
- [ ] UX-004: Add loading state tests — every page that fetches data must show skeleton/spinner, test that loading state renders before data arrives.
- [ ] UX-005: Add error state tests — every page must handle API errors gracefully (error boundary, retry button, user-friendly message).
- [ ] UX-006: Add empty state tests — every list page must show helpful empty state with CTA when no data exists.

### Accessibility
> **Note**: Accessibility work consolidated into **Wave AC — Accessibility Compliance**. The items below are superseded by AC-001 through AC-023.
>
> See Wave AC for: keyboard navigation (AC-006), screen reader testing (AC-005), color contrast (AC-003, AC-016), and focus management (AC-009, AC-010).

### Performance UX
- [ ] UX-011: Add perceived performance tests — measure time-to-interactive for document list and document detail pages, assert <3s on throttled 3G.
- [ ] UX-012: Add infinite scroll / virtual list for document tables — replace full-list rendering with virtualized list for >50 items.
- [ ] UX-013: Add optimistic UI updates for common actions — bookmark, mark notification read, comment submit — update UI immediately, rollback on failure.

---

## How to Run the Ralph Loop

```bash
# Default: 10 iterations
./ralph-loop.sh

# Custom iteration count
./ralph-loop.sh --max-iterations 20

# The loop will:
# 1. Read this PRD.md and progress.txt
# 2. Pick the highest-priority unchecked task
# 3. Select the best skill(s) from .agents/skills/
# 4. Implement the task with verification
# 5. Log to progress.txt and check off the task
# 6. Stop if no progress is made (safety guard)
```

**Installed Skills** (21 in `.agents/skills/`):
`create-plan` · `doc` · `fastapi-router-py` · `gh-address-comments` · `gh-fix-ci` · `github-issue-creator` · `jupyter-notebook` · `linear` · `mcp-builder` · `notion-meeting-intelligence` · `notion-research-documentation` · `notion-spec-to-implementation` · `openai-docs` · `playwright` · `screenshot` · `security-best-practices` · `security-ownership-map` · `security-threat-model` · `sentry` · `skill-creator` · `spreadsheet`
