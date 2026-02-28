# Frontend

React + TypeScript SPA for the Documentation Platform.

## Highlights

- Feature-module structure with controller/use-case boundaries
- Typed DTO mapper boundary + generated OpenAPI contracts
- Explicit workflow state machines for high-risk UI flows
- BFF-backed document detail orchestration
- Contract tests for backend compatibility

## Important Paths

- `src/pages/`: route-level pages
- `src/features/`: feature modules (controllers, state machines, use-cases)
- `src/lib/api/`: composed API client, DTO contracts/mappers, generated contracts
- `src/hooks/`: shared query/mutation hooks
- `e2e/`: Playwright specs

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

E2E:

```bash
npm run test:e2e
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
