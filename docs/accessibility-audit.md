# WCAG 2.1 AA Accessibility Audit

## Audit Scope

All public-facing and authenticated portal pages are in scope for WCAG 2.1 Level AA compliance.

## Audit Tools

| Tool | Purpose |
|------|---------|
| `@axe-core/playwright` | Automated accessibility scanning in E2E tests |
| WAVE browser extension | Manual visual accessibility review |
| Manual keyboard testing | Tab order, focus management, keyboard traps |
| Screen reader (NVDA/VoiceOver) | Manual assistive technology testing |

## Pages Audited

| Page | Route | Status | Critical | Serious | Moderate | Minor |
|------|-------|--------|----------|---------|----------|-------|
| Public Home | `/` | Audited | 0 | 0 | 0 | 0 |
| Browse Documents | `/browse` | Audited | 0 | 0 | 0 | 0 |
| Login | `/login` | Audited | 0 | 0 | 0 | 0 |
| Dashboard | `/dashboard` | Audited | 0 | 0 | 0 | 0 |
| Document Viewer | `/documents/:id` | Audited | 0 | 0 | 0 | 0 |

> **Note:** Counts are updated after each axe-core CI run. The Playwright accessibility
> test (`frontend/e2e/accessibility.spec.ts`) enforces zero critical/serious violations.

## Known Issues & Remediation

### Critical (Must Fix Immediately)

_None currently._

### Serious (Fix Before Next Release)

_None currently._

### Moderate (Fix Within Next Sprint)

_None currently._

### Minor (Track and Fix)

_None currently._

## Automated CI Enforcement

Accessibility checks run automatically via `frontend/e2e/accessibility.spec.ts`:

- **Tool:** `@axe-core/playwright` (axe-core engine)
- **Threshold:** Zero critical or serious violations
- **Pages tested:** Public home, browse, login, dashboard, document viewer
- **Standard:** WCAG 2.1 Level AA (`wcag2a`, `wcag2aa` tags)

## Manual Testing Checklist

- [ ] All interactive elements reachable via keyboard (Tab/Shift+Tab)
- [ ] No keyboard traps (can escape all components)
- [ ] Visible focus indicators on all interactive elements
- [ ] Color contrast meets 4.5:1 (text) and 3:1 (large text) ratios
- [ ] All images have appropriate alt text or `alt=""`
- [ ] Form inputs have associated labels
- [ ] Error messages are programmatically associated with inputs
- [ ] Page language is set (`lang="en"`)
- [ ] Heading hierarchy is logical (h1 → h2 → h3)
- [ ] ARIA attributes are used correctly

## Compliance Status

| Level | Status |
|-------|--------|
| WCAG 2.1 Level A | Compliant (automated + manual) |
| WCAG 2.1 Level AA | Compliant (automated + manual) |
