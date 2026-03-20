# WCAG 2.1 AA Accessibility Audit

**Last Updated**: 2026-03-18 (Wave AC)
**Standard**: WCAG 2.1 Level AA
**Tools**: axe-core 4.11, eslint-plugin-jsx-a11y, manual code inspection

## Audit Scope

All public-facing and authenticated portal pages across three layout contexts:
Internal staff (`Layout.tsx`), Public viewer (`PublicLayout.tsx`), and Customer portal (`CustomerLayout.tsx`).

## Audit Tools

| Tool | Purpose |
|------|---------|
| `@axe-core/playwright` | Automated accessibility scanning in E2E tests |
| `eslint-plugin-jsx-a11y` | Static JSX accessibility linting in CI |
| Manual keyboard testing | Tab order, focus management, keyboard traps |
| Manual code review | ARIA patterns, semantic HTML, heading hierarchy |

## Pages Audited

| Page | Route | Status | Critical | Serious | Moderate | Minor |
|------|-------|--------|----------|---------|----------|-------|
| Public Home | `/` | Fixed | 0 | 0 | 0 | 0 |
| Browse Documents | `/docs` | Fixed | 0 | 0 | 0 | 0 |
| Login | `/login` | Fixed | 0 | 0 | 0 | 0 |
| Dashboard | `/dashboard` | Fixed | 0 | 0 | 0 | 0 |
| Document Detail | `/documents/:id` | Fixed | 0 | 0 | 0 | 0 |
| Reviews | `/reviews` | Fixed | 0 | 0 | 0 | 0 |
| Users | `/users` | Fixed | 0 | 0 | 0 | 0 |
| Customer Dashboard | `/portal/dashboard` | Fixed | 0 | 0 | 0 | 0 |

> **Note:** Zero critical/serious violations enforced by `frontend/e2e/accessibility.spec.ts`.

---

## Findings & Remediation (Wave AC)

### Critical — Fixed

| ID | Description | WCAG | Components | Fix |
|----|-------------|------|------------|-----|
| C-01 | Modals lack focus trap — keyboard can leave dialog | 2.1.2 | AdvancedSearchModal, InviteUserDialog, ReviewDialog, FeedbackResponseDialog, VisibilityChangeConfirmDialog | Added `useFocusTrap` hook |
| C-02 | Icon-only buttons without accessible names | 4.1.2 | Close buttons in modals, mobile menu toggles | Added `aria-label` |
| C-03 | No `role="dialog"` or `aria-modal` on modals | 4.1.2 | AdvancedSearchModal, InviteUserDialog | Added semantic attributes |
| C-04 | No skip navigation link | 2.4.1 | Layout, PublicLayout, CustomerLayout | Added `SkipNavLink` component |

### Serious — Fixed

| ID | Description | WCAG | Components | Fix |
|----|-------------|------|------------|-----|
| S-01 | Color contrast below 4.5:1 | 1.4.3 | `.eyebrow` (`slate-500`), descriptive text (`slate-400`) | Upgraded to `slate-600` / `slate-500` |
| S-02 | No visible focus indicators on custom buttons | 2.4.7 | `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.pill`, NavLink pills | Added `focus-visible:ring-2` utilities |
| S-03 | ARIA live regions missing for dynamic content | 4.1.3 | NotificationBell, toast messages, collaboration status | Added `aria-live="polite"` |
| S-04 | Form inputs without associated labels | 1.3.1 | AdvancedSearchModal, NotFoundPage search | Added `htmlFor`/`id` bindings |
| S-05 | Mobile menu toggle missing `aria-label` | 4.1.2 | PublicLayout, CustomerLayout | Added `aria-label` |
| S-06 | No Escape key handler on modals | 2.1.2 | AdvancedSearchModal, InviteUserDialog | Added `onKeyDown` handler |
| S-07 | Focus not returned to trigger after modal close | 2.4.3 | All dialog components | `useFocusTrap` returns focus |
| S-08 | SPA route changes don't announce to screen readers | 4.1.3 | App.tsx routing | Added `RouteAnnouncer` component |

### Moderate — Fixed

| ID | Description | WCAG | Components | Fix |
|----|-------------|------|------------|-----|
| M-01 | Form errors not linked via `aria-describedby` | 3.3.1 | InviteUserDialog | Linked errors with `aria-describedby` + `aria-invalid` |
| M-02 | `aria-expanded` missing on mobile menu toggles | 4.1.2 | Layout, PublicLayout, CustomerLayout | Added `aria-expanded` |
| M-03 | High contrast mode: custom shadows/borders may hide focus | 1.4.11 | Design system components | Added `forced-colors` media query support |

---

## Automated CI Enforcement

### axe-core Playwright Tests
- **File:** `frontend/e2e/accessibility.spec.ts`
- **Threshold:** Zero critical or serious violations
- **Pages tested:** All public routes + portal routes + internal routes
- **Standard:** WCAG 2.1 Level AA (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` tags)

### ESLint JSX A11y
- **Plugin:** `eslint-plugin-jsx-a11y` (added in Wave AC)
- **Mode:** `recommended` ruleset, errors on violations
- **Scope:** All `.tsx` files

## Manual Testing Checklist

- [x] All interactive elements reachable via keyboard (Tab/Shift+Tab)
- [x] No keyboard traps (can escape all components)
- [x] Visible focus indicators on all interactive elements
- [x] Color contrast meets 4.5:1 (text) and 3:1 (large text) ratios
- [x] All images have appropriate alt text or `alt=""`
- [x] Form inputs have associated labels
- [x] Error messages are programmatically associated with inputs
- [x] Page language is set (`lang="en"`)
- [x] Heading hierarchy is logical (h1 → h2 → h3)
- [x] ARIA attributes are used correctly
- [x] Skip navigation link present on all layouts
- [x] Focus trapped in modals, returned on close
- [x] Route changes announced to screen readers

## Compliance Status

| Level | Status |
|-------|--------|
| WCAG 2.1 Level A | Compliant |
| WCAG 2.1 Level AA | Compliant |
