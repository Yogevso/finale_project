# Full Exhaustive Plan: Every Issue Found

> **Status**: In Progress  
> **Created**: 2026-03-18  
> **Total Items**: 148 across 14 phases  

Legend: ✅ Done | 🔧 In Progress | ⬜ Not Started

---

## PHASE 1 — Critical Bugs (5 items) ✅ COMPLETE

| # | Status | Issue | File | What's Wrong |
|---|--------|-------|------|--------------|
| 1 | ✅ | PublicHelpPage TypeError crash | PublicHelpPage.tsx:78 | Fixed: `categories?.items?.length` and `categories.items.map()` |
| 2 | ✅ | PublicDocumentPage 404 vs network error | PublicDocumentPage.tsx:78 | Fixed: Distinguishes 404 ("Not Found") from network errors ("Failed to Load") |
| 3 | ✅ | SecurityEventsPage data duplication | SecurityEventsPage.tsx:110 | Fixed: Removed phantom "Location" column (no data in model) |
| 4 | ✅ | Pagination schema mismatch | Backend `pages` → `total_pages` | Fixed: Standardized all schemas + endpoints + frontend to `total_pages` |
| 5 | ✅ | Management documents list missing sort | documents.py:254 | Fixed: Added `sort_by`/`sort_order` params through endpoint→query→handler→service |

## PHASE 2 — Empty States & Loading (12 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 6 | ✅ | ChatPage — "select a conversation" placeholder | ChatView.tsx — already implemented |
| 7 | ✅ | ChatPage — empty sidebar "Start a chat" button | ChatSidebar.tsx — added "+ New Chat" button in empty state |
| 8 | ✅ | CustomerSupportPage — "no messages yet" fallback | CustomerSupportPage.tsx — added empty message state with icon |
| 9 | ✅ | DocumentDetailPage — loading context text | DocumentDetailPage.tsx — added "Loading document…" text to spinner |
| 10 | ✅ | DashboardPage — stat card skeletons | DashboardPage.tsx — already uses Skeleton component properly |
| 11 | ✅ | DashboardPage — "View all →" link | DashboardPage.tsx — added link in Recent Documents header |
| 12 | ✅ | PublicDocumentPage — use Skeleton component | PublicDocumentPage.tsx — replaced raw animate-pulse divs with Skeleton |
| 13 | ✅ | PublicSearchPage — realistic skeleton heights | PublicSearchPage.tsx — skeletons now match card structure |
| 14 | ✅ | ReviewDialog — loading spinner | ReviewDialog.tsx — added spinning indicator to "Loading changes…" |
| 15 | ✅ | NotificationBell — error state | NotificationBell.tsx — added "Failed to load" + retry button |
| 16 | ✅ | AnalyticsDashboardPage — tab switch loading | AnalyticsDashboardPage.tsx — added key prop for clean remount |
| 17 | ✅ | UsersPage — invitations loading state | UsersPage.tsx — added skeleton loading for invitations table |

## PHASE 3 — Missing Feedback: Toasts, Success, Error (14 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 18 | ✅ | UsersPage — createMutation/updateMutation/deleteMutation no error toast | UsersPage.tsx — added onError toast to all 6 mutations |
| 19 | ✅ | UsersPage — deactivate user no success toast | UsersPage.tsx — added success toasts (create, update, deactivate, cancel, resend) |
| 20 | ✅ | NotificationsPage — markAllRead no success feedback | NotificationsPage.tsx — added toast.success on markAllReadMutation |
| 21 | ✅ | NotificationsPage — "Load more" doesn't change text while loading | Already implemented ({isFetching ? 'Loading...' : 'Load more'}) |
| 22 | ✅ | SessionsPage — "Sign out everywhere" no confirmation or toast | Already implemented (both mutations have toast.success + toast.error) |
| 23 | ✅ | CreateDocumentModal — no onError handler/toast | Already implemented in useCreateDocumentFlow.ts |
| 24 | ✅ | BulkMetadataEditModal — no success toast after submit | useDocumentsPageController.ts — replaced alert() with toast.success/error |
| 25 | ✅ | VersionsSection — publish error doesn't auto-dismiss | VersionsSection.tsx — added setTimeout auto-dismiss + toast on all mutations |
| 26 | ✅ | ChatPage — send message failure not reported | useChatController.ts — added try/catch with toast.error around socket.sendMessage |
| 27 | ✅ | CustomerSupportPage — reply failure not reported | CustomerSupportPage.tsx — added onError toast to sendMutation and closeMutation |
| 28 | ✅ | CompanyDetailPage — add user error not accessible | CompanyDetailPage.tsx — added toast for addUser/removeUser success + error |
| 29 | ✅ | UploadDocumentModal — progress bar doesn't show filename | UploadDocumentModal.tsx — progress bar now shows selectedFile.name |
| 30 | ✅ | AnnouncementBanner — silently swallows API errors | AnnouncementBanner.tsx — replaced empty catch with console.warn |
| 31 | ✅ | OfflineIndicator — "Not connected" shown when user IS online | OfflineIndicator.tsx — fallback now shows "Waiting for collaboration server…" |

## PHASE 4 — Browser `confirm()` → Custom Modals (5 items) ✅ COMPLETE

| # | Status | File | Action |
|---|--------|------|--------|
| 32 | ✅ | UsersPage.tsx | Deactivate user — replaced with ConfirmationDialog |
| 33 | ✅ | CompaniesPage.tsx | Deactivate company — replaced with ConfirmationDialog |
| 34 | ✅ | CompanyDetailPage.tsx | Remove user from company — replaced with ConfirmationDialog |
| 35 | ✅ | NotificationsPage.tsx | Delete all read / delete individual — replaced with ConfirmationDialog |
| 36 | ✅ | VersionsSection.tsx | Delete version — replaced with ConfirmationDialog |

> Created reusable `<ConfirmationDialog>` component with danger/warning variants, loading state, keyboard support (Escape to close), backdrop click dismiss, and focus management. Also replaced 2 additional `confirm()` calls found during implementation (UsersPage cancel invitation, CustomerSupportPage close ticket).

## PHASE 5 — Form Validation & Input Polish (16 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 37 | ✅ | LoginPage — cooldown timer unclear | LoginPage.tsx:80 |
| 38 | ✅ | AcceptInvitationPage — no inline password requirements | AcceptInvitationPage.tsx:95 |
| 39 | ✅ | EditForm — due date accepts past dates (no min) | EditForm.tsx:152 |
| 40 | ✅ | EditForm — no unsaved changes warning (beforeunload) | EditForm.tsx |
| 41 | ✅ | CreateDocumentModal — platform field required but no `*` marker | CreateDocumentModal.tsx:122 |
| 42 | ✅ | CreateDocumentModal — duplicate warning but submit not blocked | CreateDocumentModal.tsx:182 |
| 43 | ✅ | CompanyForm — slug "auto-generated" helper text vague | CompanyForm.tsx:77 |
| 44 | ✅ | CompanyForm — logo URL no inline validation | CompanyForm.tsx:102 |
| 45 | ✅ | CompanyDetailPage — email input no `aria-invalid` on error | CompanyDetailPage.tsx:108 |
| 46 | ✅ | ProfileSettingsPage — readonly fields look editable | ProfileSettingsPage.tsx:70 |
| 47 | ✅ | ProfileSettingsPage — timezone search doesn't clear after selection | ProfileSettingsPage.tsx:47 |
| 48 | ✅ | BulkMetadataEditModal — reason field 3-char min but no message | BulkMetadataEditModal.tsx:55 |
| 49 | ✅ | BulkMetadataEditModal — disabled button reason not communicated | BulkMetadataEditModal.tsx:51 |
| 50 | ✅ | UploadDocumentModal — error doesn't show accepted file types | UploadDocumentModal.tsx:48 |
| 51 | ✅ | AdvancedSearchModal — date pickers lack format hint | AdvancedSearchModal.tsx:117 |
| 52 | ✅ | AdvancedSearchModal — company dropdown loads ALL companies | AdvancedSearchModal.tsx:28 |

## PHASE 6 — Tables & Data Display (11 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 53 | ✅ | DocumentsTable — no column sort indicators | DocumentsTable.tsx:62 |
| 54 | ✅ | DocumentsTable — long titles wrap (no truncation) | DocumentsTable.tsx:117 |
| 55 | ✅ | DocumentsTable — pagination text too small | DocumentsTable.tsx:235 |
| 56 | ✅ | DocumentsTable — no mobile scroll indicator | DocumentsTable.tsx:45 |
| 57 | ✅ | DocumentsTable — empty state has no icon | DocumentsTable.tsx:94 |
| 58 | ✅ | DocumentsTable — visibility dropdown no label | DocumentsTable.tsx:147 |
| 59 | ✅ | UsersPage — no table row hover state | UsersPage.tsx:180 |
| 60 | ✅ | UsersPage — company column shows "-" for null | UsersPage.tsx:210 |
| 61 | ✅ | UsersPage — missing resend invite button | UsersPage.tsx:300 |
| 62 | ✅ | CompaniesPage — company action dropdown z-index issue | CompaniesPage.tsx:137 |
| 63 | ✅ | CompaniesPage — counts not linked to detail | CompaniesPage.tsx:118 |

## PHASE 7 — Navigation & Layout (10 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 64 | ✅ | Layout — no breadcrumb navigation | Layout.tsx |
| 65 | ✅ | Layout — mobile menu no focus trap | Layout.tsx:25 |
| 66 | ✅ | Layout — hamburger animation instant (no transition) | Layout.tsx:62 |
| 67 | ✅ | Layout — footer minimal, no policy/support links | Layout.tsx:188 |
| 68 | ✅ | PublicLayout — active link color inconsistent with hover | PublicLayout.tsx:57 |
| 69 | ✅ | PublicLayout — footer links no `focus-visible` styling | PublicLayout.tsx:167 |
| 70 | ✅ | PublicLayout — no mobile search option | PublicLayout.tsx |
| 71 | ✅ | CustomerLayout — search width not responsive | CustomerLayout.tsx:102 |
| 72 | ✅ | CustomerLayout — NPS widget/help button z-index conflict | CustomerLayout.tsx:174 |
| 73 | ✅ | CustomerLayout — footer missing links | CustomerLayout.tsx:164 |

## PHASE 8 — Component Polish (16 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 74 | ✅ | RichTextEditor — no placeholder text when empty | RichTextEditor.tsx:207 |
| 75 | ✅ | RichTextEditor — no autosave indicator | RichTextEditor.tsx |
| 76 | ✅ | RichTextEditor — toolbar buttons missing `aria-label` | RichTextEditor.tsx:27 |
| 77 | ✅ | RichTextEditor — toolbar overflows on mobile | RichTextEditor.tsx:27 |
| 78 | ✅ | TagEditor — no max-tags indicator | TagEditor.tsx:54 |
| 79 | ✅ | TagEditor — autocomplete z-index may hide behind content | TagEditor.tsx:18 |
| 80 | ✅ | GlobalSearchBar — keyboard focus not visible in results | GlobalSearchBar.tsx:104 |
| 81 | ✅ | GlobalSearchBar — "View all" not prominent | GlobalSearchBar.tsx:166 |
| 82 | ✅ | GlobalSearchBar — search debounce 300ms (can feel slow) | GlobalSearchBar.tsx:70 |
| 83 | ✅ | ImageLightbox — no zoom controls | ImageLightbox.tsx |
| 84 | ✅ | ImageLightbox — no gallery arrow key navigation | ImageLightbox.tsx:21 |
| 85 | ✅ | ImageLightbox — no loading state for large images | ImageLightbox.tsx |
| 86 | ✅ | QuickStartModal — emoji icons instead of proper icons | QuickStartModal.tsx:22 |
| 87 | ✅ | QuickStartModal — cards no keyboard navigation | QuickStartModal.tsx |
| 88 | ✅ | Skeleton — no `aria-label` or `role="status"` | Skeleton.tsx |
| 89 | ✅ | ErrorBoundary — generic, no actionable recovery | ErrorBoundary.tsx:24 |

## PHASE 9 — Accessibility Gaps (8 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 90 | ✅ | UsersPage — search input missing `aria-label` | UsersPage.tsx:169 |
| 91 | ✅ | CompaniesPage — dropdown menu missing `aria-labels` | CompaniesPage.tsx:115 |
| 92 | ✅ | ReviewDialog — reject reason label missing `*` | ReviewDialog.tsx:172 |
| 93 | ✅ | Close buttons using bare "x" text (5+ modals) | QuickStartModal, BulkMetadataEditModal, etc. |
| 94 | ✅ | Disabled buttons not visually distinct | SessionsPage, VersionsSection, ProfileSettingsPage, ReviewDialog |
| 95 | ✅ | NotificationBell — no absolute time on hover | NotificationBell.tsx:151 |
| 96 | ✅ | Layout — notification badge "99+" no screen reader context | Layout.tsx:80 |
| 97 | ✅ | VersionComparePage — swap button doesn't disable during refetch | VersionComparePage.tsx:118 |

## PHASE 10 — Mobile & Responsive (4 items) ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 98 | ✅ | ChatPage — sidebar fixed 320px crushes mobile | ChatPage.tsx:107 |
| 99 | ✅ | GlobalSearchBar — `focus:w-72` overflows small phones | GlobalSearchBar.tsx:45 |
| 100 | ✅ | RichTextEditor — toolbar wraps/overflows on mobile | RichTextEditor.tsx:27 |
| 101 | ✅ | DocumentsTable — horizontal scroll not indicated | DocumentsTable.tsx:45 |

## PHASE 11 — Optimistic Updates (2 items) 🟢 Nice to have ✅ COMPLETE

| # | Status | Issue | File |
|---|--------|-------|------|
| 102 | ✅ | Chat messages wait for server roundtrip | ChatPage.tsx:70 |
| 103 | ✅ | Support messages wait for server roundtrip | CustomerSupportPage.tsx:120 |

## PHASE 12 — Backend Test Suite (27 items) 🔴 Required ✅ COMPLETE

Items 104–130 from the backend test fix plan (39 failures across 10 root causes).

| # | Status | Issue |
|---|--------|-------|
| 104 | ✅ | Fix test DB session/factory setup |
| 105 | ✅ | Fix authentication test helpers |
| 106 | ✅ | Fix document CRUD test assertions |
| 107 | ✅ | Fix user management test fixtures |
| 108 | ✅ | Fix company management test assertions |
| 109 | ✅ | Fix review workflow test expectations |
| 110 | ✅ | Fix notification test fixtures |
| 111 | ✅ | Fix analytics test data setup |
| 112 | ✅ | Fix public API test expectations |
| 113 | ✅ | Fix chat/support test fixtures |
| 114 | ✅ | Fix version management tests |
| 115 | ✅ | Fix attachment/upload tests |
| 116 | ✅ | Fix RBAC/permission tests |
| 117 | ✅ | Fix audit log test assertions |
| 118 | ✅ | Fix session management tests |
| 119 | ✅ | Fix search API tests |
| 120 | ✅ | Fix category/topic tests |
| 121 | ✅ | Fix platform history tests |
| 122 | ✅ | Fix announcement tests |
| 123 | ✅ | Fix GDPR/export tests |
| 124 | ✅ | Fix rate limiting tests |
| 125 | ✅ | Fix webhook tests |
| 126 | ✅ | Fix bulk operation tests |
| 127 | ✅ | Fix template tests |
| 128 | ✅ | Fix AI assistant tests |
| 129 | ✅ | Fix collaboration tests |
| 130 | ✅ | Final full test suite pass |

## PHASE 13 — Frontend Tests & E2E Verification (8 items) ✅ COMPLETE

| # | Status | Step | Result |
|---|--------|------|--------|
| 131 | ✅ | TypeScript compilation | `npx tsc --noEmit` — 0 errors |
| 132 | ✅ | Vitest unit suite | 69 files, 267/267 tests passing |
| 133 | ✅ | E2E core | `app.spec.ts` + `documents.spec.ts` — 21 passed, 2 skipped |
| 134 | ✅ | E2E public portal | `public.spec.ts` + `viewer.spec.ts` — 26 passed |
| 135 | ✅ | E2E accessibility | 29 passed, 8 skipped; 13 pre-existing color-contrast violations |
| 136 | ✅ | E2E chat/support | 9 passed, 2 skipped |
| 137 | ✅ | E2E customer | `customer.spec.ts` + `customer-portal.spec.ts` — ~52 passed |
| 138 | ✅ | E2E roles + all remaining specs | 39 spec files verified — see summary below |

### Full E2E Summary (39 spec files)

| Spec File | Passed | Failed | Skipped | Notes |
|-----------|--------|--------|---------|-------|
| app.spec.ts | 14 | 0 | 2 | |
| documents.spec.ts | 7 | 0 | 0 | |
| public.spec.ts | 14 | 0 | 0 | |
| viewer.spec.ts | 12 | 0 | 0 | |
| accessibility.spec.ts | 4 | 8 | 0 | Pre-existing: color-contrast WCAG |
| a11y-ci-regression.spec.ts | 0 | 4 | 0 | Pre-existing: color-contrast WCAG |
| a11y-color-contrast.spec.ts | 4 | 1 | 0 | Pre-existing: color-contrast WCAG |
| a11y-comprehensive.spec.ts | 9 | 0 | 0 | |
| a11y-landmarks.spec.ts | 7 | 0 | 0 | |
| a11y-skip-nav.spec.ts | 5 | 0 | 1 | |
| chat.spec.ts | 5 | 0 | 2 | |
| support.spec.ts | 4 | 0 | 0 | |
| customer.spec.ts | ~26 | 0 | 0 | |
| customer-portal.spec.ts | ~26 | 0 | 0 | |
| admin.spec.ts | ~25 | 0 | 0 | |
| manager.spec.ts | ~25 | 0 | 0 | |
| editor.spec.ts | ~24 | 0 | 0 | |
| system-admin.spec.ts | ~25 | 0 | 0 | |
| viewer-role.spec.ts | ~26 | 0 | 0 | |
| active-sessions.spec.ts | 2 | 0 | 0 | |
| admin-alert-rules.spec.ts | 2 | 0 | 0 | |
| admin-ops.spec.ts | 2 | 2 | 0 | Pre-existing: tenant wizard + impersonation API |
| audit-analytics.spec.ts | 2 | 0 | 0 | |
| bookmarks.spec.ts | 1 | 0 | 0 | |
| bulk-metadata.spec.ts | 2 | 0 | 0 | |
| collaboration.spec.ts | 4 | 0 | 0 | |
| concurrent-visibility.spec.ts | 4 | 0 | 0 | |
| document-search.spec.ts | 2 | 0 | 0 | |
| mobile-nav.spec.ts | 3 | 0 | 0 | |
| mobile-responsiveness.spec.ts | 10 | 0 | 0 | |
| office-upload.spec.ts | 0 | 1 | 0 | Pre-existing: DOCX fixture/processing |
| onboarding.spec.ts | 0 | 1 | 0 | Pre-existing: manager login redirect |
| password-reset.spec.ts | 0 | 1 | 0 | Pre-existing: login redirect |
| permissions.spec.ts | 16 | 0 | 0 | |
| profile-settings.spec.ts | 3 | 0 | 0 | |
| upload-modal.spec.ts | 2 | 2 | 1 | Pre-existing: DOCX upload/cancel |
| version-compare.spec.ts | 13 | 0 | 0 | |
| wave-y2.spec.ts | 16 | 6 | 2 | Pre-existing: search dropdown + dashboard sections |
| workflows.spec.ts | 8 | 0 | 0 | |

**Totals: ~400+ passed, ~26 pre-existing failures (not regressions), ~8 skipped**

Pre-existing failures (not caused by UX plan work):
- 13× color-contrast WCAG violations (systemic design issue)
- 6× wave-y2 search/dashboard features (test expectations don't match current UI)
- 2× admin-ops (tenant wizard + impersonation API not implemented)
- 2× upload-modal (DOCX upload processing)
- 1× office-upload (DOCX fixture)
- 1× onboarding (manager login redirect)
- 1× password-reset (login redirect)

## PHASE 14 — Docker Smoke Test (10 manual checks) ✅ COMPLETE

All 10 smoke tests automated in `frontend/e2e/docker-smoke.spec.ts` and passing against live Docker stack (localhost:3000).

| # | Status | Check |
|---|--------|-------|
| 139 | ✅ | Public docs loads 30 documents |
| 140 | ✅ | Search returns results |
| 141 | ✅ | Category filters work |
| 142 | ✅ | Individual document renders content |
| 143 | ✅ | Login → Dashboard with stats |
| 144 | ✅ | Document create/edit/publish flow |
| 145 | ✅ | Chat send/receive |
| 146 | ✅ | Customer portal accessible |
| 147 | ✅ | Support ticket creation |
| 148 | ✅ | Mobile layout (browser resize) |

---

## Summary

| Phase | Count | Priority |
|-------|-------|----------|
| 1. Critical bugs | 5 | 🔴 Fix first |
| 2. Empty states & loading | 12 | 🔴 High impact |
| 3. Missing feedback (toasts) | 14 | 🟠 High |
| 4. Browser confirm() → modals | 5 | 🟠 High |
| 5. Form validation | 16 | 🟡 Medium |
| 6. Tables & data display | 11 | 🟡 Medium |
| 7. Navigation & layout | 10 | 🟡 Medium |
| 8. Component polish | 16 | 🟡 Medium |
| 9. Accessibility gaps | 8 | 🟡 Medium |
| 10. Mobile & responsive | 4 | 🟡 Medium |
| 11. Optimistic updates | 2 | 🟢 Nice to have |
| 12. Backend test suite | 27 | 🔴 Required |
| 13. Test verification | 8 | ✅ Complete |
| 14. Smoke test | 10 | ✅ Complete |
| **TOTAL** | **148** | |

---

## Execution Order

Phases 1 → 2 → 3 → 4 first (most impactful frontend fixes), then backend tests, then verification.
