# Frontend

React and TypeScript frontend for the Intel Documentation Platform.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Development Flow](#development-flow)
- [Environment Configuration](#environment-configuration)
- [Project Structure](#project-structure)
- [Scripts](#scripts)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The frontend is a Vite-powered React SPA that serves:

- internal management workflows
- customer portal experiences
- public browsing and public document viewing

It integrates with the FastAPI backend, collaboration server, generated API contracts, and Playwright-based end-to-end coverage.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Local defaults:

- App URL: `http://localhost:3000`
- API proxy target: `http://127.0.0.1:8000`
- Collaboration URL: `ws://localhost:8002`

## Key Features

- React 18 plus TypeScript 5
- Vite dev server with `/api` proxying
- TipTap-based rich text and collaborative editing
- TanStack Query for server state
- DOMPurify-based sanitization
- Customer, public, and internal page surfaces
- Generated API contracts from backend OpenAPI
- Vitest, Playwright, Lighthouse, and accessibility coverage

## Development Flow

The typical local loop is:

1. start the backend on `http://localhost:8000`
2. start the collaboration server on `ws://localhost:8002`
3. run `npm run dev`
4. use the Vite proxy for `/api` traffic during local development

Important integration points:

- backend API prefix: `/api/v1`
- contract generation: `scripts/api_contracts/generate_frontend_contracts.mjs`
- collaboration URL: `VITE_COLLAB_SERVER_URL`
- optimistic concurrency feature flag: `VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS`

## Project Structure

```text
frontend/
|-- src/
|   |-- components/      shared UI building blocks
|   |-- config/          runtime flags and config
|   |-- features/        assistant, chat, reviews, analytics, and more
|   |-- hooks/           shared hooks and query helpers
|   |-- layouts/         page shells
|   |-- lib/             API client, contracts, utilities
|   `-- pages/           route-level screens
|-- e2e/                 Playwright suites
|-- scripts/             local quality gates
|-- package.json
`-- vite.config.ts
```

## Environment Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `VITE_API_URL` | `/api/v1` | Backend API base used in builds |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Dev proxy target |
| `VITE_COLLAB_SERVER_URL` | `ws://localhost:8002` | Collaboration websocket URL |
| `VITE_ALLOWED_HOSTS` | `localhost,127.0.0.1,frontend,host.docker.internal` | Allowed Vite hosts |
| `VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS` | `true` | Frontend feature flag |

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Validate API contracts, type-check, and build |
| `npm run build:docker` | Docker-oriented build without contract check |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run format` | Run Prettier |
| `npm run test -- --run` | Run Vitest once |
| `npm run test:ui` | Run Vitest UI |
| `npm run test:e2e` | Run Playwright E2E |
| `npm run test:e2e:phase10` | Run focused E2E quality suite |
| `npm run test:lighthouse` | Run Lighthouse CI |
| `npm run generate:api-contracts` | Generate frontend contracts |
| `npm run generate:api-contracts:check` | Verify frontend contracts |
| `npm run refresh:api-contracts` | Refresh backend snapshot and contracts |
| `npm run check:bundle-budget` | Enforce bundle budget |

## Testing

```bash
npm run test -- --run
npm run test:e2e
npm run test:lighthouse
```

Focused E2E suites:

- `npm run test:e2e:visual`
- `npm run test:e2e:responsive`
- `npm run test:e2e:ux`
- `npm run test:e2e:a11y`
- `npm run test:e2e:performance`

Recommended pre-PR checks:

```bash
npm run generate:api-contracts:check
npm run test -- --run
npm run build
```

## Troubleshooting

### API calls fail in dev

Check that the backend is healthy at `http://localhost:8000/health` and verify `VITE_API_PROXY_TARGET`.

### Collaboration is disconnected

Check `VITE_COLLAB_SERVER_URL` and make sure the collab server is running on port `8002`.

### Contract checks fail during build

Run:

```bash
npm run refresh:api-contracts
```

### Playwright fails against local dev

Make sure backend, frontend, and collab services are all running before the suite starts.

## Related Docs

- [Root README](../README.md)
- [Development Guide](../docs/DEVELOPMENT.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [API Examples](../docs/API_EXAMPLES.md)
- [Feature Rollout Flags](../docs/feature-rollout-flags.md)
