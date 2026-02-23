# Hocuspocus Collaboration Server

Real-time collaborative document editing server using Yjs CRDT.

## Overview

This server enables Google Docs-style real-time collaboration in the document management system. Multiple users can edit the same document simultaneously, seeing each other's cursors and changes in real-time.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Browser 1  │     │  Browser 2  │     │  Browser 3  │
│  (TipTap)   │     │  (TipTap)   │     │  (TipTap)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │ WebSocket         │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌────────────────────────┐
              │   Hocuspocus Server    │  Port 8002
              │   (This Service)       │
              └───────────┬────────────┘
                          │ HTTP
                          ▼
              ┌────────────────────────┐
              │   FastAPI Backend      │  Port 8000
              └────────────────────────┘
```

## Features

- **Google Docs-style simultaneous editing**: Changes appear instantly for all users
- **Live cursor presence**: See where other users are editing
- **Yjs CRDT conflict resolution**: Handles concurrent edits automatically
- **Automatic sync with offline support**: Changes sync when connection restores
- **Authentication**: JWT-based auth validates user permissions
- **Persistence**: Document state saved to FastAPI backend

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env with your settings
# - JWT_SECRET must match FastAPI backend

# Start development server
npm run dev

# Or build and run production
npm run build
npm start
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8002 | WebSocket server port |
| `HOST` | 0.0.0.0 | Server host |
| `JWT_SECRET` | - | Must match FastAPI backend secret |
| `BACKEND_URL` | http://localhost:8000 | FastAPI backend URL |
| `BACKEND_API_PREFIX` | /api/v1 | FastAPI API prefix used for persistence endpoints |
| `LOG_LEVEL` | info | Logging verbosity |
| `REDIS_URL` | - | Optional Redis for horizontal scaling |

## WebSocket Connection

Connect to the collaboration server:

```
ws://localhost:8002/document/{documentId}?token={jwt}
```

The JWT token is obtained from the FastAPI backend via `POST /auth/collab-token`.

## API Endpoints

The server exposes WebSocket endpoints only. HTTP endpoints are handled by FastAPI.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start with hot-reload |
| `npm run build` | Compile TypeScript |
| `npm start` | Run production build |
| `npm run lint` | Run TypeScript static checks |
| `npm run typecheck` | Type check without emit |

## Docker

```bash
# Build image
docker build -t collab-server .

# Run container
docker run -p 8002:8002 \
  -e JWT_SECRET=your-secret \
  -e BACKEND_URL=http://backend:8000 \
  collab-server
```

## File Structure

```
collab-server/
├── src/
│   ├── index.ts        # Server entry point
│   ├── auth.ts         # JWT authentication
│   ├── persistence.ts  # Document storage
│   └── types.ts        # TypeScript types
├── package.json
├── tsconfig.json
├── Dockerfile
└── .env.example
```

## Testing

```bash
# Connect with wscat for testing
npx wscat -c "ws://localhost:8002/document/test-doc?token=YOUR_JWT"
```

## Scaling

For multiple server instances, configure Redis:

```env
REDIS_URL=redis://localhost:6379
```

This enables document state to be shared across server instances.
