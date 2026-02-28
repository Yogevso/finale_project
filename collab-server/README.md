# Collaboration Server

Hocuspocus/Yjs server for real-time collaborative editing.

## Highlights

- JWT-authenticated websocket collaboration sessions
- Adapter boundaries for backend token/state contracts
- Persistence integration with backend APIs
- Connection/session orchestration services

## Setup

```bash
npm install
npm run dev
```

Build + run:

```bash
npm run build
npm start
```

## Environment Variables

- `PORT` (default `8002`)
- `HOST` (default `0.0.0.0`)
- `JWT_SECRET` (must match backend)
- `BACKEND_URL` (default `http://localhost:8000`)
- `BACKEND_API_PREFIX` (default `/api/v1`)
- `LOG_LEVEL` (default `info`)
- `REDIS_URL` (optional, for horizontal scaling)

## Commands

```bash
npm run typecheck
npm run test
npm run lint
```

## Important Paths

- `src/index.ts`: bootstrap entrypoint
- `src/server/`: server composition (app/health/connection registry)
- `src/adapters/`: contract adapters
- `src/authContext/`: auth context services
- `src/__tests__/`: unit and contract tests
