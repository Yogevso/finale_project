# Frontend

React + TypeScript SPA for the Intel Documentation Platform.

## Highlights

- Feature-module structure with controller/use-case boundaries
- Typed DTO mapper boundary + generated OpenAPI contracts
- In-memory token storage (not localStorage) for auth security
- DOMPurify-based HTML sanitization on all user-generated content
- BFF-backed document detail orchestration
- Dark mode support with theme toggle
- Skeleton loading states for all major views
- Accessibility (WCAG) audit and improvements
- Comprehensive E2E test suites (a11y, performance, responsive, visual, UX)
- Contract tests for backend compatibility

## Important Paths

- `src/pages/`: route-level pages (admin, portal, public, viewer, documents)
- `src/features/`: feature modules — assistant, chat, reviews, analytics dashboard
- `src/components/`: shared UI — form inputs, skeletons, analytics widgets, modals
- `src/lib/api/`: composed API client, DTO contracts/mappers, generated contracts
- `src/hooks/`: shared hooks (useTheme, useAccessibility, queries/mutations)
- `src/layouts/`: layout shells (PublicLayout, etc.)
- `e2e/`: Playwright specs (a11y, performance, responsive, visual, UX)

## Setup

```bash
npm install
npm run dev
```

App URL: `http://localhost:3000`

## Build and Tests

Type + build:

```bash
npm run build
```

Unit tests:

```bash
npm run test -- --run
```

E2E (full suite):

```bash
npm run test:e2e
```

E2E (phase 10 — visual, responsive, UX, a11y, performance):

```bash
npm run test:e2e:phase10
```

Lighthouse CI:

```bash
npx lhci autorun
```

## Contract Generation

```bash
npm run generate:api-contracts
npm run generate:api-contracts:check
npm run refresh:api-contracts
```

## Frontend Feature Flags

- `VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS`

Details: `../docs/feature-rollout-flags.md`.
