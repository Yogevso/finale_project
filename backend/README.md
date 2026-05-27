# Backend

FastAPI backend for the Intel Documentation Platform.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [API Surface](#api-surface)
- [Authentication Model](#authentication-model)
- [Visibility and Review Rules](#visibility-and-review-rules)
- [Project Structure](#project-structure)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Commands](#commands)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The backend owns authentication, authorization, tenant isolation, document workflows, review pipelines, analytics, assistant orchestration, notifications, and public or customer-facing read APIs.

Core capabilities:

- FastAPI application with `/api/v1` prefix
- Layered architecture across `domain`, `application`, `infrastructure`, and `api`
- Multi-tenant RBAC with centralized policy enforcement
- JWT and cookie session flows
- Review lifecycle with audience snapshot locking
- AI assistant orchestration with Ollama and ChromaDB
- Audit logging, rate limiting, and health endpoints

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful local URLs:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/v1/docs`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
- Health: `http://localhost:8000/health`
- Detailed health: `http://localhost:8000/health/detailed`

## API Surface

The API is grouped into these domains:

| Domain | Purpose |
| --- | --- |
| `management` | Internal admin, editorial, review, support, and analytics flows |
| `portal` | Customer-facing tenant-scoped APIs |
| `public` | Public document and discovery endpoints |
| `viewer` | Public document consumption |
| `bff` | Backend-for-frontend orchestration for complex views |

Representative endpoints:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/documents`
- `POST /api/v1/documents`
- `POST /api/v1/reviews/documents/{document_id}/submit`
- `POST /api/v1/reviews/{review_id}/approve`
- `POST /api/v1/assistant/chat`
- `GET /api/v1/portal/documents`
- `GET /api/v1/public/documents`

## Authentication Model

- login uses `username` and `password`
- access tokens expire after `30` minutes
- refresh tokens expire after `7` days
- login and refresh both support cookie-oriented session flows
- collaboration uses `POST /api/v1/auth/collab-token` to mint a document-scoped websocket token

Primary auth endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/collab-token`

## Visibility and Review Rules

Visibility values:

- `internal`
- `company`
- `public`

Important invariants:

- `company` visibility requires at least one assigned company
- non-`company` visibility must not carry `company_ids`
- customer portal access is tenant-scoped and only returns published content

Review workflow notes:

- document reviews are submitted through `POST /api/v1/reviews/documents/{document_id}/submit`
- review payload uses `message`, `version_id`, and `requested_reviewer_ids`
- approval preflight is available at `GET /api/v1/reviews/{review_id}/approve/preflight`
- approval and rejection support structured review feedback payloads
- audience drift is checked between submission time and approval time

## Project Structure

```text
backend/
|-- app/
|   |-- api/              route modules
|   |-- application/      command and query orchestration
|   |-- assistant/        AI assistant, tools, RAG, Ollama client
|   |-- db/               engines, sessions, database bases
|   |-- domain/           business rules and aggregates
|   |-- infrastructure/   persistence and external adapters
|   |-- middleware/       auth, rate limiting, audit, logging
|   `-- observability/    health and SLO support
|-- tests/                unit, integration, contracts, scenarios
|-- alembic.ini
|-- requirements.in
|-- requirements-dev.in
`-- requirements-dev.txt
```

## Environment Configuration

Important variables:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SECRET_KEY` | Yes | none | Shared signing key |
| `DATABASE_URL` | No | `sqlite:///./data/portal.db` | Core database |
| `ANALYTICS_DATABASE_URL` | No | falls back to `DATABASE_URL` | Analytics database |
| `CHAT_DATABASE_URL` | No | falls back to `DATABASE_URL` | Chat and assistant database |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis for rate limiting and pub/sub |
| `OLLAMA_BASE_URL` | No | `http://ollama:11434` | Ollama base URL |
| `ASSISTANT_MODEL` | No | `llama3.1:8b` | Assistant model |
| `MAX_UPLOAD_SIZE` | No | `52428800` | Max upload size in bytes |
| `SEARCH_BACKEND_MODE` | No | `auto` or `portable_like` | Search backend strategy |

## Database Setup

Local development defaults to SQLite. Production should use PostgreSQL.

Run migrations:

```bash
alembic upgrade head
alembic -n analytics upgrade head
alembic -n chat upgrade head
```

If you need to split an existing single DB into dedicated analytics and chat stores:

```bash
python scripts/split_databases.py
python scripts/split_databases.py --execute
```

## Commands

| Command | Purpose |
| --- | --- |
| `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | Start dev server |
| `pytest tests/ -v` | Run backend tests |
| `ruff check app/ tests/` | Lint backend code |
| `ruff format app/ tests/ --check` | Check formatting |
| `alembic upgrade head` | Run core migrations |
| `alembic -n analytics upgrade head` | Run analytics migrations |
| `alembic -n chat upgrade head` | Run chat migrations |

Sample requests:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

curl -X POST http://localhost:8000/api/v1/auth/collab-token \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"document_id":42}'
```

## Testing

```bash
pytest tests/ -v
ruff check app/ tests/
ruff format app/ tests/ --check
```

High-value test areas:

- auth and RBAC
- tenant isolation
- review workflow correctness
- assistant safety and tool routing
- contracts and public API stability

## Troubleshooting

### Swagger is missing

Docs are exposed in non-production only. Confirm your environment is not running in production mode.

### Auth works in API tests but collab fails

The collaboration server must share the same `SECRET_KEY` as the backend.

### Assistant calls fail

Check `OLLAMA_BASE_URL`, model availability, and `GET /api/v1/assistant/health`.

### Rate limiting behaves unexpectedly

Verify `REDIS_URL` connectivity and your `RATE_LIMIT_*` environment variables.

## Related Docs

- [Root README](../README.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Deployment](../docs/DEPLOYMENT.md)
- [API Examples](../docs/API_EXAMPLES.md)
- [Authorization Matrix](../docs/AUTHORIZATION_MATRIX.md)
- [ADRs](../docs/adr)
