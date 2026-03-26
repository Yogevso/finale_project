# Collaboration Server

Hocuspocus/Yjs server for real-time collaborative editing.

## Highlights

- JWT-authenticated WebSocket collaboration sessions
- Yjs CRDT conflict resolution for simultaneous editing
- Live cursor presence (see where others are editing)
- Required `SECRET_KEY` environment variable; `JWT_SECRET` is legacy fallback only
- Optional `SECRET_KEY_OLD` grace-period verification during coordinated key rotation
- Regex-validated document IDs (`/^\d+$/`) to prevent injection
- Adapter boundaries for backend token/state contracts
- Persistence integration with backend APIs
- Connection/session orchestration services
- Optional Redis support for horizontal scaling

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

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `8002` | WebSocket server port |
| `HOST` | `0.0.0.0` | Bind address |
| `SECRET_KEY` | - | **Required.** Must match backend `SECRET_KEY` |
| `SECRET_KEY_OLD` | - | Optional 24h grace-period verification key during rotation |
| `JWT_SECRET` | - | Legacy fallback only when `SECRET_KEY` is unset |
| `BACKEND_URL` | `http://localhost:8000` | Backend API base URL |
| `BACKEND_API_PREFIX` | `/api/v1` | Backend API prefix |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `REDIS_URL` | - | Optional, for horizontal scaling |
| `COLLAB_MAX_TOTAL_CONNECTIONS` | `200` | Hard cap for concurrent websocket connections per collab-server instance |
| `COLLAB_MAX_CONNECTIONS_PER_DOCUMENT` | `25` | Hard cap for concurrent connections on one document per instance |
| `COLLAB_RECONNECT_WINDOW_SECONDS` | `60` | Window used to classify rapid reconnect churn in runtime telemetry |

## Commands

```bash
npm run dev         # Development with hot reload
npm run build       # TypeScript compilation
npm start           # Production server
npm run typecheck   # Type checking
npm run test        # Jest tests
npm run lint        # Linting
```

## Important Paths

- `src/index.ts`: bootstrap entrypoint
- `src/server/`: server composition (app/health/connection registry)
- `src/adapters/`: contract adapters (backend integration)
- `src/authContext/`: auth context services (JWT validation)
- `src/__tests__/`: unit and contract tests
