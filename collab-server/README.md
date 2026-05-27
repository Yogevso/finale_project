# Collaboration Server

Hocuspocus and Yjs collaboration server for real-time document editing.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Auth Flow](#auth-flow)
- [Environment Configuration](#environment-configuration)
- [Scripts](#scripts)
- [Runtime Notes](#runtime-notes)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

This service handles real-time collaborative editing sessions for documents. It verifies auth with the shared signing key, synchronizes Yjs document state, exposes health checks, and can use Redis for scaling and coordination.

## Quick Start

```bash
cd collab-server
npm install
npm run dev
```

Local defaults:

- WebSocket server: `ws://localhost:8002`
- Health server: `http://localhost:8003/health`

## Key Features

- Hocuspocus websocket server
- Yjs CRDT synchronization
- Shared `SECRET_KEY` verification with backend
- Optional `SECRET_KEY_OLD` during key rotation
- Regex validation of document identifiers
- Optional Redis extension for horizontal scaling
- Connection guardrails and reconnect telemetry

## Auth Flow

The collaboration server does not accept arbitrary websocket clients. The intended flow is:

1. authenticate against the backend
2. request `POST /api/v1/auth/collab-token` with a `document_id`
3. receive a signed collaboration token, permissions list, websocket URL, and expiry
4. connect to the returned websocket URL with that token

Key runtime details:

- token expiry is `3600` seconds
- permissions are document-scoped
- backend and collab server must share `SECRET_KEY`
- inaccessible documents are rejected before token issuance

## Environment Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `8002` | WebSocket server port |
| `HOST` | `0.0.0.0` | Bind host |
| `SECRET_KEY` | none | Required `SECRET_KEY` environment variable used as the shared signing key |
| `SECRET_KEY_OLD` | none | Optional grace-period rotation key |
| `JWT_SECRET` | none | Legacy fallback only |
| `BACKEND_URL` | `http://localhost:8000` | Backend API base |
| `BACKEND_API_PREFIX` | `/api/v1` | Backend API prefix |
| `REDIS_URL` | none | Optional Redis URL |
| `LOG_LEVEL` | `info` | Logging level |
| `COLLAB_MAX_TOTAL_CONNECTIONS` | `200` | Per-instance connection cap |
| `COLLAB_MAX_CONNECTIONS_PER_DOCUMENT` | `25` | Per-document connection cap |
| `COLLAB_RECONNECT_WINDOW_SECONDS` | `60` | Reconnect churn window |

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start watch mode with `tsx` |
| `npm run build` | Build production output |
| `npm start` | Start compiled server |
| `npm run typecheck` | Run TypeScript checks |
| `npm run test` | Run Jest tests |
| `npm run test:coverage` | Run Jest with coverage |
| `npm run lint` | Alias to typecheck |

## Runtime Notes

- The backend and collaboration server must use the same `SECRET_KEY`
- The frontend should point `VITE_COLLAB_SERVER_URL` at this service
- Health checks run on port `8003`, separate from the websocket port
- Redis is optional locally and strongly recommended when scaling beyond a single instance

## Testing

```bash
npm run typecheck
npm run test
```

## Troubleshooting

### Clients cannot connect

Check port `8002`, verify the frontend websocket URL, and confirm there is no mismatch between `ws://` and `wss://`.

### Auth succeeds in HTTP but collaboration fails

This usually means the backend and collab server are not sharing the same `SECRET_KEY`.

### Health checks fail

Check that the health listener is reachable at `http://localhost:8003/health`.

## Related Docs

- [Root README](../README.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Deployment](../docs/DEPLOYMENT.md)
- [Development Guide](../docs/DEVELOPMENT.md)
