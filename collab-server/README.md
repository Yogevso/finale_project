# Collaboration Server

Hocuspocus/Yjs server for real-time collaborative editing.

## Highlights

- JWT-authenticated WebSocket collaboration sessions
- Yjs CRDT conflict resolution for simultaneous editing
- Live cursor presence (see where others are editing)
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
| `JWT_SECRET` | — | Must match backend secret |
| `BACKEND_URL` | `http://localhost:8000` | Backend API base URL |
| `BACKEND_API_PREFIX` | `/api/v1` | Backend API prefix |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `REDIS_URL` | — | Optional, for horizontal scaling |

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
