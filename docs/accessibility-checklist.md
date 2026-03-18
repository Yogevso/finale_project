# Accessibility PR Checklist (AC-015)

Use this checklist when reviewing PRs that touch UI components.

## Required checks

- [ ] **Focus management**: New modals/dialogs use `useFocusTrap` from `@/hooks/useAccessibility`
- [ ] **Dialog semantics**: Modals include `role="dialog"`, `aria-modal="true"`, and `aria-label`
- [ ] **Close buttons**: All icon-only close buttons have `aria-label="Close …"`
- [ ] **Form labels**: Every `<input>`, `<select>`, `<textarea>` has an associated `<label htmlFor="…">` with matching `id`
- [ ] **Error linking**: Form errors use `aria-describedby` pointing to an error `<p id="…">`, and the invalid field has `aria-invalid="true"`
- [ ] **Color contrast**: Text meets WCAG 2.1 AA minimums (4.5:1 normal, 3:1 large)
- [ ] **Keyboard navigation**: All interactive elements are reachable via Tab and operable via Enter/Space
- [ ] **Focus visible**: Focus rings are visible on all interactive elements (use Tailwind `focus-visible:ring-2`)
- [ ] **Image alt text**: Decorative images use `alt=""` or `aria-hidden="true"`, meaningful images have descriptive `alt`
- [ ] **ARIA live regions**: Dynamic status updates (notifications, toasts, connection status) use `aria-live="polite"` or `role="status"`
- [ ] **Skip navigation**: Page layouts include `<SkipNavLink />` and main content has `id="main-content"`
- [ ] **Mobile toggles**: Hamburger/menu buttons have `aria-label` and `aria-expanded`

## Automated checks

- **ESLint**: `eslint-plugin-jsx-a11y` catches common violations at build time
- **Playwright**: `e2e/accessibility.spec.ts` runs axe-core WCAG 2.1 AA on all routes
- **High contrast**: Test with `@media (forced-colors: active)` — see `index.css`

## Quick reference

| Pattern | Import |
|---------|--------|
| Focus trap | `import { useFocusTrap } from '@/hooks/useAccessibility'` |
| Skip nav | `import { SkipNavLink } from '@/components/a11y/SkipNavLink'` |
| Route announcer | `import { RouteAnnouncer } from '@/components/a11y/SkipNavLink'` |
