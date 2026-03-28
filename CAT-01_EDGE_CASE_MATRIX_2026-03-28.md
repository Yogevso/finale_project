# CAT-01 Edge Case Matrix

Date: 2026-03-28
Scope: documents page and related input-heavy communication surfaces

## Rules

| Surface | Field | Rule |
| --- | --- | --- |
| Documents create/upload | Title | Single-line, trim edges, collapse internal whitespace, max 160 chars, blank upload title falls back to normalized filename stem |
| Documents create/upload | Description | Multiline, normalize line endings, trim trailing line whitespace, collapse 3+ blank lines to 2, max 1000 chars |
| Documents create/upload | Category | Single-line, trim/collapse whitespace, max 80 chars |
| Documents create/upload | Topic | Single-line, trim/collapse whitespace, max 80 chars |
| Documents create/upload | Platform | Single-line, trim/collapse whitespace, max 80 chars |
| Documents create/upload | Release branch | Single-line, trim/collapse whitespace, max 40 chars |
| Documents create/upload | Tags | Comma-separated list, trim entries, dedupe case-insensitively, max 200 chars |
| Documents filters | Search | Single-line, max 120 chars |
| Documents filters | Category | Single-line, max 80 chars |
| Documents saved views | View name | Single-line, trim/collapse whitespace, max 80 chars |
| Template save | Template name | Single-line, trim/collapse whitespace, max 120 chars |
| Template save | Template description | Multiline normalization, max 320 chars |
| Chat | Message body | Multiline normalization on send, max 2000 chars |
| Support reply | Reply body | Max 2000 chars |
| Feedback | Customer feedback body | Multiline normalization on submit, max 2000 chars |
| Feedback | Internal response body | Multiline normalization on submit, max 2000 chars |
| Visibility change | Audit reason | Multiline normalization on confirm, min 3 chars, max 280 chars |

## Edge Cases Covered

| Case | Expected behavior |
| --- | --- |
| Empty title | Create flow blocks submission; upload falls back to filename stem |
| Empty description | Surface keeps layout stable and shows empty-state fallback copy where needed |
| Long title with spaces | Wraps on display and truncates to rule limit on submit paths |
| Long title without spaces | Wraps without breaking action layout and truncates to rule limit |
| Whitespace-only values | Normalize to empty and trigger the same validation as blank input |
| Duplicate tags with mixed casing | Deduped before submit (`ops, Ops` becomes `ops`) |
| Repeated blank lines in multiline fields | Collapsed to at most one blank line gap |
| Oversized saved view names | Truncated to 80 chars before save |
| Oversized chat/support/feedback text | Client max length prevents overflow and counters expose remaining size |
| Company visibility without companies | Visibility change dialog blocks confirmation |
| Inverted date range filters | Toolbar warns and constrains the paired date input |

## Verification

- `frontend/src/lib/uiInputRules.test.ts`
- `frontend/src/pages/documents/hooks/useCreateDocumentFlow.test.tsx`
- `frontend/src/pages/documents/hooks/useUploadDocumentFlow.test.tsx`
- `frontend/src/features/chat/MessageInput.test.tsx`
- `frontend/src/components/VisibilityChangeConfirmDialog.test.tsx`
- `frontend/src/pages/documents/components/DocumentsFiltersToolbar.test.tsx`
