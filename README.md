# Intel Documentation Platform

[![CI](https://github.com/Yogevso/finale_project/actions/workflows/ci.yml/badge.svg)](https://github.com/Yogevso/finale_project/actions/workflows/ci.yml)
[![Security](https://github.com/Yogevso/finale_project/actions/workflows/security.yml/badge.svg)](https://github.com/Yogevso/finale_project/actions/workflows/security.yml)

Multi-tenant document management for internal Intel teams and external customer portals.

A full-stack platform for authoring, reviewing, publishing, searching, and securely distributing documentation across internal, customer, and public audiences.

## Table of Contents

- [Quick Start](#quick-start)
- [Default Seed Data](#default-seed-data)
- [Live Deployment](#live-deployment)
- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Available Scripts](#available-scripts)
- [API Documentation](#api-documentation)
- [API Examples](#api-examples)
- [Happy Path Walkthrough](#happy-path-walkthrough)
- [Features Deep Dive](#features-deep-dive)
- [Project Structure](#project-structure)
- [Database Setup](#database-setup)
- [Environment Configuration](#environment-configuration)
- [Testing](#testing)
- [Development Workflow](#development-workflow)
- [System Architecture](#system-architecture)
- [Security Best Practices](#security-best-practices)
- [Authentication and Authorization](#authentication-and-authorization)
- [Roles at a Glance](#roles-at-a-glance)
- [Permission Matrix Summary](#permission-matrix-summary)
- [Tenant Visibility and Audience Rules](#tenant-visibility-and-audience-rules)
- [Rate Limiting](#rate-limiting)
- [File Uploads](#file-uploads)
- [HTTP Status Codes and Error Handling](#http-status-codes-and-error-handling)
- [FAQ](#faq)
- [Monitoring and Logging](#monitoring-and-logging)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## Overview

This repository contains a document platform built around three user surfaces:

- Internal management portal for admins, editors, reviewers, and support staff
- Customer portal for tenant-scoped document access, support, and feedback
- Public viewer for published public documentation

Teams can:

- Author and edit rich documents with live collaboration
- Submit content for review and approval
- Publish scoped versions to customer and public audiences
- Search across documents, platforms, categories, and metadata
- Use an AI assistant with access-policy enforcement
- Track feedback, support, analytics, and engagement
- Manage tenants, roles, invitations, and notifications

Main features:

- JWT and cookie-based authentication
- Multi-tenant RBAC and tenant isolation
- Rich text authoring with TipTap
- Version history, rollback, and publishing
- Review workflow with audience locking and drift checks
- Real-time collaboration with Yjs and Hocuspocus
- AI assistant powered by Ollama and ChromaDB
- Customer portal and public viewer
- Audit logging, rate limiting, and security hardening

## Quick Start

Get the platform running locally with Docker Compose:

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd finale_project

# 2. Create local environment file
cp .env.example .env

# 3. Set a signing key
# Linux/macOS:
openssl rand -hex 32
# Windows PowerShell:
# [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")

# 4. Start the stack
docker compose up -d --build

# 5. Optional: start AI inference too
docker compose --profile ai up -d --build

# 6. Optional: use PostgreSQL instead of SQLite
docker compose --profile postgres up -d
```

Local endpoints:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/v1/docs`
- Collaboration server: `ws://localhost:8002`
- Collaboration health: `http://localhost:8003/health`

Default development users:

- `sysadmin / sysadmin123`
- `admin / admin123`
- `manager / manager123`
- `editor / editor123`
- `viewer / viewer123`
- `customer1 / customer123`
- `customer2 / customer123`

## Default Seed Data

Development and test environments seed demo data by default unless explicitly disabled. Production and staging require `SEED_DEMO_DATA=true` for a one-time opt-in.

Seeded users from [backend/seed_data.py](./backend/seed_data.py):

| Username    | Password      | Role           | Tenant                  |
| ----------- | ------------- | -------------- | ----------------------- |
| `sysadmin`  | `sysadmin123` | `system_admin` | default internal tenant |
| `admin`     | `admin123`    | `admin`        | default internal tenant |
| `manager`   | `manager123`  | `manager`      | default internal tenant |
| `editor`    | `editor123`   | `editor`       | default internal tenant |
| `viewer`    | `viewer123`   | `viewer`       | default internal tenant |
| `customer1` | `customer123` | `customer`     | Company A               |
| `customer2` | `customer123` | `customer`     | Company B               |

Notes:

- internal users belong to the default tenant
- customer users are scoped to their company tenant
- public and portal behavior depends on document visibility plus tenant assignment

## Live Deployment

The repository does encode canonical frontend environments in CI/CD, and it carries default production API and collaboration hosts in deployment config.

| Environment          | Surface              | URL                                  |
| -------------------- | -------------------- | ------------------------------------ |
| `staging`            | Frontend app         | `https://staging.portal.example.com` |
| `production`         | Frontend app         | `https://portal.example.com`         |
| `production default` | Backend API          | `https://api.portal.example.com`     |
| `production default` | Collaboration server | `wss://collab.portal.example.com`    |

Notes:

- the staging frontend URL is defined in `.github/workflows/cd.yml`
- the production frontend URL is defined in `.github/workflows/cd.yml`
- the production API and collab URLs are the checked-in build defaults in `docker-compose.prod.yml` and `.env.example`
- staging API and staging collab hosts are provided through deploy-time environment variables, not hardcoded in the repo

## Tech Stack

### Backend

- Runtime: Python 3.11+
- Framework: FastAPI
- ORM: SQLAlchemy 2
- Validation: Pydantic 2
- Migrations: Alembic
- Databases: SQLite by default, PostgreSQL in production
- Search: SQLite FTS5, PostgreSQL TSV, or portable fallback
- Storage: local filesystem or S3-compatible object storage

### Frontend

- Framework: React 18
- Language: TypeScript 5
- Build tool: Vite 5
- Styling: Tailwind CSS
- Data fetching: TanStack Query
- Editor: TipTap
- Charts: Recharts

### Real-Time and AI

- Collaboration: Hocuspocus + Yjs CRDT
- Cache and pub/sub: Redis 7
- LLM inference: Ollama
- Vector store: ChromaDB

### DevOps and Quality

- Containers: Docker Compose
- Backend tests: Pytest
- Frontend tests: Vitest + Playwright
- Linting and formatting: Ruff, ESLint, Prettier
- CI: GitHub Actions

## Installation

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Docker and Docker Compose
- Git
- Optional: PostgreSQL 16 if you want a local non-Docker database

### Step 1: Clone the repository

```bash
git clone <repo-url>
cd finale_project
```

### Step 2: Configure environment variables

```bash
cp .env.example .env
```

At minimum set:

```bash
SECRET_KEY=<32-byte-random-hex>
```

### Step 3: Start infrastructure

```bash
docker compose up -d --build
```

Optional profiles:

```bash
# AI assistant runtime
docker compose --profile ai up -d

# PostgreSQL
docker compose --profile postgres up -d
```

### Step 4: Local service installs without Docker

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
```

Frontend:

```bash
cd frontend
npm install
```

Collaboration server:

```bash
cd collab-server
npm install
```

## Running the Application

### Docker Compose

```bash
docker compose up -d --build
```

This starts:

- `backend` on port `8000`
- `frontend` on port `3000`
- `collab-server` on ports `8002` and `8003`
- `redis` on port `6379`
- optional `ollama` on port `11434`
- optional `postgres` on port `5432`

### Local development

Backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Collaboration server:

```bash
cd collab-server
npm run dev
```

### Stop the stack

```bash
docker compose down
```

Reset local volumes:

```bash
docker compose down -v
```

## Available Scripts

### Backend

Run these from `backend/`:

| Command                                                    | Purpose                      |
| ---------------------------------------------------------- | ---------------------------- |
| `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | Start FastAPI in development |
| `pytest tests/ -v`                                         | Run backend tests            |
| `ruff check app/ tests/`                                   | Lint backend code            |
| `ruff format app/ tests/ --check`                          | Check backend formatting     |
| `alembic upgrade head`                                     | Run core migrations          |
| `alembic -n analytics upgrade head`                        | Run analytics DB migrations  |
| `alembic -n chat upgrade head`                             | Run chat DB migrations       |

### Frontend

Run these from `frontend/`:

| Command                                | Purpose                                |
| -------------------------------------- | -------------------------------------- |
| `npm run dev`                          | Start Vite dev server                  |
| `npm run build`                        | Type-check and build                   |
| `npm run preview`                      | Preview production build               |
| `npm run lint`                         | Run ESLint                             |
| `npm run format`                       | Run Prettier                           |
| `npm run test -- --run`                | Run Vitest once                        |
| `npm run test:e2e`                     | Run Playwright E2E                     |
| `npm run test:lighthouse`              | Run Lighthouse CI                      |
| `npm run generate:api-contracts`       | Generate frontend API contracts        |
| `npm run generate:api-contracts:check` | Verify contracts are current           |
| `npm run refresh:api-contracts`        | Refresh OpenAPI snapshot and contracts |

### Collaboration server

Run these from `collab-server/`:

| Command                 | Purpose                                     |
| ----------------------- | ------------------------------------------- |
| `npm run dev`           | Start the Hocuspocus server with watch mode |
| `npm run build`         | Build TypeScript output                     |
| `npm start`             | Run compiled production server              |
| `npm run typecheck`     | Run TypeScript checks                       |
| `npm run test`          | Run Jest tests                              |
| `npm run test:coverage` | Run Jest with coverage                      |

## API Documentation

The backend exposes OpenAPI documentation in non-production environments.

- Swagger UI: `http://localhost:8000/api/v1/docs`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
- ReDoc: `http://localhost:8000/api/v1/redoc`

Primary API domains:

- `management`: internal admin and editorial workflows
- `portal`: customer-facing tenant-scoped APIs
- `public`: public browsing and published documentation
- `viewer`: public document viewer endpoints
- `bff`: backend-for-frontend orchestration

## API Examples

### Authenticate

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

### Get current user

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### List management documents

```bash
curl "http://localhost:8000/api/v1/documents?page=1&page_size=20" \
  -H "Authorization: Bearer <access_token>"
```

### Create a document

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Platform Installation Guide",
    "description": "Install and bootstrap the platform",
    "category": "Operations",
    "topic": "Setup",
    "platform": "General",
    "visibility": "internal",
    "status": "draft"
  }'
```

### Create a company-scoped document

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dell Deployment Guide",
    "description": "Scoped rollout instructions for Dell",
    "visibility": "company",
    "company_ids": [2],
    "status": "draft"
  }'
```

### Submit a document for review

```bash
curl -X POST http://localhost:8000/api/v1/reviews/documents/42/submit \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version_id": 7,
    "message": "Ready for review",
    "requested_reviewer_ids": [2, 3]
  }'
```

### Check review approval preflight

```bash
curl http://localhost:8000/api/v1/reviews/18/approve/preflight \
  -H "Authorization: Bearer <access_token>"
```

### Approve a review

```bash
curl -X POST http://localhost:8000/api/v1/reviews/18/approve \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "comments": "Approved for publish"
  }'
```

### Reject a review with structured feedback

```bash
curl -X POST http://localhost:8000/api/v1/reviews/18/reject \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "comments": "Please fix the audience and update the screenshots",
    "review_feedback": {
      "general_comment": "Needs another pass",
      "section_comments": [
        {
          "title": "Intro",
          "comment": "Clarify prerequisites",
          "severity": "medium"
        }
      ]
    }
  }'
```

### Ask the assistant

```bash
curl -X POST http://localhost:8000/api/v1/assistant/chat \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize the latest published guidance for Dell customers."
  }'
```

### Browse portal documents

```bash
curl http://localhost:8000/api/v1/portal/documents \
  -H "Authorization: Bearer <customer_token>"
```

### Browse public documents

```bash
curl http://localhost:8000/api/v1/public/documents
```

### Refresh an access token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

The backend prefers the `refresh_token` httpOnly cookie when present, and falls back to a body field if needed.

### Request a collaboration token

```bash
curl -X POST http://localhost:8000/api/v1/auth/collab-token \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 42
  }'
```

### Upload a document file

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@./fixtures/guide.docx" \
  -F "title=Uploaded Installation Guide" \
  -F "category=Uploaded" \
  -F "visibility=internal" \
  -F "status=draft"
```

### Upload a company-scoped document file

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@./fixtures/dell-guide.docx" \
  -F "title=Dell Customer Guide" \
  -F "visibility=company" \
  -F "status=draft" \
  -F "company_ids=2" \
  -F "company_ids=5"
```

This is important because `company_ids` are only valid when `visibility=company`, and `company` visibility is rejected if no assigned company is provided.

## Happy Path Walkthrough

One small end-to-end flow from internal authoring to customer or public consumption:

1. Log in as an internal editor or manager.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"editor","password":"editor123"}'
```

2. Create a draft document.

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q2 Deployment Guide",
    "description": "Customer rollout guide",
    "visibility": "company",
    "company_ids": [2],
    "status": "draft"
  }'
```

3. Submit it for review.

```bash
curl -X POST http://localhost:8000/api/v1/reviews/documents/42/submit \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Ready for customer review",
    "requested_reviewer_ids": [3]
  }'
```

4. Log in as a reviewer or manager, run approval preflight, then approve.

```bash
curl http://localhost:8000/api/v1/reviews/18/approve/preflight \
  -H "Authorization: Bearer <reviewer_access_token>"

curl -X POST http://localhost:8000/api/v1/reviews/18/approve \
  -H "Authorization: Bearer <reviewer_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"comments":"Approved"}'
```

5. View the published result from the appropriate audience surface.

Customer portal:

```bash
curl http://localhost:8000/api/v1/portal/documents \
  -H "Authorization: Bearer <customer_token>"
```

Public surface:

```bash
curl http://localhost:8000/api/v1/public/documents
```

Rule of thumb:

- use `portal` when the document is customer-scoped
- use `public` when the document has `public` visibility
- internal-only documents stay inside management views

## Features Deep Dive

### Document authoring

- TipTap editor with rich formatting
- Table of contents and document detail views
- Draft, pending review, approved, active, and archived lifecycle
- DOCX and PPTX ingestion flows
- PDF and PPTX export paths
- Duplicate-title checks and metadata helpers
- Row-version and ETag support on document responses

### Review and publishing

- Submit, approve, reject, and cancel review flows
- Audience snapshots captured at review time
- Drift detection to prevent publishing to the wrong tenants
- Version history, compare, restore, and rollback patterns
- Reviewer assignment support via explicit reviewer IDs or rule-based fallback
- Approval preflight checks include:
  - review must still be pending
  - approver cannot approve their own submission
  - assignment rules must pass
  - open review threads must be resolved
  - audience configuration must still be valid

### Document lifecycle

Canonical statuses from the backend:

```text
draft -> pending_review -> approved -> active -> archived
```

Notes:

- the enum exposes `PUBLISHED` as an alias of `active`
- active documents may require a fresh draft version before another review submission
- public publishing is role-gated and tied to audience policy checks

### Tenant visibility

Documents support three visibility levels:

- `internal`: internal users only
- `company`: internal users plus assigned customer companies
- `public`: available through the public surface

Audience invariants enforced by the backend:

- `company` visibility requires at least one assigned company
- non-`company` visibility must not carry `company_ids`
- portal customers only see `published` documents that match their tenant assignment or public audience

### Real-time collaboration

- Yjs CRDT-based document editing
- Live cursor presence and session coordination
- Snapshot support and reconnect guardrails
- Redis-backed horizontal scaling option
- Collaboration auth is issued by `POST /api/v1/auth/collab-token`
- Collaboration tokens are document-scoped and expire after 1 hour

### Customer and public distribution

- Customer portal with tenant-scoped access
- Public browsing for published public documents
- Downloadable attachments for allowed audiences
- Feedback, NPS, support tickets, and reading progress

### AI assistant

- Ollama-backed self-hosted inference
- ChromaDB retrieval-augmented generation
- Tool-augmented answers over documents and analytics
- Access-policy enforcement before content retrieval

### Administration and observability

- Users, roles, companies, invitations, and announcements
- Analytics dashboards and engagement tracking
- Notification preferences and support operations
- Health, audit, and security-oriented runtime signals

### Assistant and retrieval

- Ollama-backed assistant chat lives at `POST /api/v1/assistant/chat`
- Conversation endpoints support listing, creating, renaming, and deleting chats
- RAG tools respect document access policy before loading any content
- Assistant health is exposed at `GET /api/v1/assistant/health`

## Project Structure

```text
finale_project/
|-- backend/                 FastAPI application
|   |-- app/
|   |   |-- api/            management, portal, public, viewer, bff
|   |   |-- application/    commands, queries, orchestration
|   |   |-- assistant/      Ollama, RAG, tools
|   |   |-- db/             engines, sessions, database bases
|   |   |-- domain/         core domain models and rules
|   |   `-- infrastructure/ persistence and adapters
|   `-- tests/
|-- frontend/               React + TypeScript SPA
|   |-- src/components/
|   |-- src/features/
|   |-- src/pages/
|   `-- e2e/
|-- collab-server/          Hocuspocus real-time editing server
|-- docs/                   architecture, ADRs, migration guides, SLO docs
|-- scripts/                scaffolding, release, observability, migration tools
`-- docker-compose.yml      local multi-service stack
```

## Database Setup

### Default mode

The repository defaults to SQLite for local development:

- `DATABASE_URL=sqlite:///./data/portal.db`
- `ANALYTICS_DATABASE_URL=sqlite:///./data/analytics.db`
- `CHAT_DATABASE_URL=sqlite:///./data/chat.db`

### Production-oriented mode

PostgreSQL is supported and recommended for production:

```bash
docker compose --profile postgres up -d
```

Example connection string:

```bash
DATABASE_URL=postgresql://portal:portal@postgres:5432/portal
```

### Migrations

Core:

```bash
cd backend
alembic upgrade head
```

Analytics:

```bash
alembic -n analytics upgrade head
```

Chat:

```bash
alembic -n chat upgrade head
```

## Environment Configuration

Copy `.env.example` to `.env` and review all values before running.

Minimal example:

```bash
# Security
SECRET_KEY=replace-with-32-byte-random-hex
SECRET_KEY_OLD=

# Databases
DATABASE_URL=sqlite:///./data/portal.db
ANALYTICS_DATABASE_URL=sqlite:///./data/analytics.db
CHAT_DATABASE_URL=sqlite:///./data/chat.db

# Collaboration / cache
COLLAB_SERVER_URL=http://collab-server:8002
REDIS_URL=redis://redis:6379/0

# Search
SEARCH_BACKEND_MODE=portable_like

# Frontend
VITE_API_URL=https://api.portal.example.com
VITE_COLLAB_SERVER_URL=wss://collab.portal.example.com

# Optional integrations
S3_ENABLED=false
EMAIL_ENABLED=false
SEED_DEMO_DATA=false
```

### Required

| Variable     | Description                                                 |
| ------------ | ----------------------------------------------------------- |
| `SECRET_KEY` | Shared signing key used by backend and collaboration server |

### Common backend variables

| Variable                 | Default                         | Description                         |
| ------------------------ | ------------------------------- | ----------------------------------- |
| `DATABASE_URL`           | `sqlite:///./data/portal.db`    | Core database                       |
| `ANALYTICS_DATABASE_URL` | `sqlite:///./data/analytics.db` | Analytics database                  |
| `CHAT_DATABASE_URL`      | `sqlite:///./data/chat.db`      | Chat database                       |
| `REDIS_URL`              | `redis://redis:6379/0`          | Redis for rate limiting and pub/sub |
| `SEARCH_BACKEND_MODE`    | `portable_like` or `auto`       | Search backend strategy             |
| `MAX_UPLOAD_SIZE`        | `52428800`                      | Max upload size in bytes            |

### Frontend variables

| Variable                                 | Default                       | Description                       |
| ---------------------------------------- | ----------------------------- | --------------------------------- |
| `VITE_API_URL`                           | `/api/v1` or deployed API URL | Frontend API base                 |
| `VITE_API_PROXY_TARGET`                  | `http://127.0.0.1:8000`       | Vite dev proxy target             |
| `VITE_COLLAB_SERVER_URL`                 | `ws://localhost:8002`         | Collaboration server URL          |
| `VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS` | `true`                        | Frontend concurrency feature flag |

### Optional integrations

| Variable                                  | Description                             |
| ----------------------------------------- | --------------------------------------- |
| `OLLAMA_BASE_URL`                         | Ollama base URL                         |
| `ASSISTANT_MODEL`                         | LLM model name                          |
| `S3_ENABLED`                              | Enable S3-compatible attachment storage |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Email delivery                          |

## Testing

### Backend

```bash
cd backend
pytest tests/ -v
ruff check app/ tests/
ruff format app/ tests/ --check
```

### Frontend

```bash
cd frontend
npm run test -- --run
npm run test:e2e
npm run test:e2e:phase10
npm run test:lighthouse
```

### Collaboration server

```bash
cd collab-server
npm run typecheck
npm run test
```

## Development Workflow

Recommended workflow:

1. Branch from `main`
2. Pull the latest `main` before starting work
3. Make changes in the relevant service
4. Run the service-level tests you touched
5. Update docs when behavior or setup changes
6. Open a PR with testing notes

Local pre-push checks (recommended):

```bash
./scripts/setup-git-hooks.sh
```

This enables `.githooks/pre-push`, which runs short guard checks based on changed paths:

- `backend/**`: `ruff check app/ tests/`, `ruff format app/ tests/ --check`
- `frontend/**`: `npm run lint`, `tsc --noEmit`, `npm run generate:api-contracts:check`
- `collab-server/**`: `npm run lint`
- `.github/workflows/**` or `scripts/architecture_checks/**`: `check_refactor_budget.py`

Emergency bypass (single push):

```bash
SKIP_PRE_PUSH=1 git push
```

CI test modes:

- PR/push runs the critical profile only (fast and blocking).
- Full regression is available via Actions manual run (`CI - Tests & Quality`) with `test_profile=full`.
- Add `debug_mode=true` in manual run to get extra E2E runtime logs/artifacts for fast failure triage.

Suggested branch names:

- `feature/<name>`
- `fix/<name>`
- `docs/<name>`
- `refactor/<name>`

Suggested commit style:

```text
feat(documents): add assigned company batch update
fix(reviews): block publish when audience snapshot drifts
docs(readme): rewrite service setup and examples
```

## System Architecture

```text
+-------------------+        +-------------------+        +-------------------+
| React Frontend    | -----> | FastAPI Backend   | -----> | SQLite/PostgreSQL |
| Vite + TS         |        | /api/v1           |        | core + analytics  |
+---------+---------+        +---------+---------+        +---------+---------+
          |                            |                            |
          | WebSocket                  | Redis                      | ChromaDB
          v                            v                            v
+-------------------+        +-------------------+        +-------------------+
| Collab Server     |        | Rate limit/pubsub |        | AI retrieval data |
| Hocuspocus + Yjs  |        | Redis             |        | Ollama + vectors  |
+-------------------+        +-------------------+        +-------------------+
```

Request flow:

```text
Browser -> Vite/Frontend -> FastAPI route -> policy/auth -> service layer -> database/storage
                                                         -> assistant tools -> Ollama/ChromaDB
Browser -> WebSocket -> collab-server -> backend token verification -> Yjs state sync
```

## Security Best Practices

Do:

- Generate a strong `SECRET_KEY`
- Keep backend and collab server keys in sync during normal operation
- Restrict CORS origins in deployed environments
- Use PostgreSQL plus Redis in production
- Store uploads in approved storage only
- Keep docs routes disabled in production unless explicitly required
- Rotate secrets carefully using `SECRET_KEY_OLD` only for short grace periods

Do not:

- Commit `.env` files with live secrets
- Rely on legacy `JWT_SECRET` when `SECRET_KEY` should be present
- Expose Redis, Postgres, or internal health endpoints publicly without controls
- Disable tenant isolation or auth checks for convenience
- Serve unvalidated uploads

## Authentication and Authorization

### Roles

The backend defines six roles:

- `system_admin`
- `admin`
- `manager`
- `editor`
- `viewer`
- `customer`

High-level expectations:

- `system_admin`: cross-tenant administration
- `admin`: internal administration within the tenant scope
- `manager`: review and publishing authority
- `editor`: create and edit content
- `viewer`: read-only internal access
- `customer`: portal-only tenant-scoped access

### Token model

- access tokens expire after `30` minutes
- refresh tokens expire after `7` days
- password reset tokens expire after `60` minutes
- login response returns JSON tokens and sets the refresh token as an httpOnly cookie
- refresh prefers the cookie over the request body

### Important auth endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/collab-token`

### Login notes

- login uses `username`, not email
- rate limiting applies to login and reset flows when enabled
- collaboration uses a separate short-lived token for websocket auth

## Roles at a Glance

| Role           | Primary use                       | Can create/edit docs | Can submit reviews | Can approve reviews | Can access portal as customer |
| -------------- | --------------------------------- | -------------------- | ------------------ | ------------------- | ----------------------------- |
| `system_admin` | cross-tenant administration       | Yes                  | Yes                | Yes                 | No                            |
| `admin`        | tenant administration             | Yes                  | Yes                | Yes                 | No                            |
| `manager`      | publishing and review authority   | Yes                  | Yes                | Yes                 | No                            |
| `editor`       | authoring and collaboration       | Yes                  | Yes                | Usually no          | No                            |
| `viewer`       | internal read-only                | No                   | No                 | No                  | No                            |
| `customer`     | tenant-scoped customer portal use | No                   | No                 | No                  | Yes                           |

This is a quick scan table, not a full permission matrix. For route-level detail, use [docs/AUTHORIZATION_MATRIX.md](./docs/AUTHORIZATION_MATRIX.md).

## Permission Matrix Summary

This table is the higher-signal summary of the platform permission model. It is intentionally broader than the quick roles table above, but still not a substitute for the full route matrix.

| Capability                                     | system_admin | admin | manager | editor     | viewer | customer |
| ---------------------------------------------- | ------------ | ----- | ------- | ---------- | ------ | -------- |
| Access internal management UI                  | Yes          | Yes   | Yes     | Yes        | Yes    | No       |
| Access customer portal                         | No           | No    | No      | No         | No     | Yes      |
| Create and edit documents                      | Yes          | Yes   | Yes     | Yes        | No     | No       |
| Upload DOCX/PPTX/PDF documents                 | Yes          | Yes   | Yes     | Yes        | No     | No       |
| Create public documents directly               | Yes          | Yes   | Yes     | No         | No     | No       |
| Upload directly as `active`                    | Yes          | Yes   | Yes     | No         | No     | No       |
| Assign company audience                        | Yes          | Yes   | Yes     | Yes        | No     | No       |
| Submit documents for review                    | Yes          | Yes   | Yes     | Yes        | No     | No       |
| Approve or reject reviews                      | Yes          | Yes   | Yes     | Usually no | No     | No       |
| View tenant analytics and admin operations     | Yes          | Yes   | Yes     | Limited    | No     | No       |
| Use internal assistant against accessible docs | Yes          | Yes   | Yes     | Yes        | Yes    | No       |
| Use portal/customer document access            | No           | No    | No      | No         | No     | Yes      |
| Access public documents                        | Yes          | Yes   | Yes     | Yes        | Yes    | Yes      |

Interpretation notes:

- `editor` can author and submit content, but approval authority is typically reserved for `manager` and above.
- `customer` access is constrained by tenant assignment and published visibility.
- `system_admin` is the only role that should be assumed to operate across tenant boundaries by default.
- some internal capabilities depend on policy checks beyond role alone, especially review assignment and audience drift conditions.

## Tenant Visibility and Audience Rules

Audience behavior is central to the platform.

### Visibility values

| Value      | Meaning                                                  |
| ---------- | -------------------------------------------------------- |
| `internal` | only internal users can access the document              |
| `company`  | internal users plus specific assigned customer companies |
| `public`   | publicly viewable through public routes                  |

### Backend invariants

- `company` visibility requires one or more `company_ids`
- `internal` and `public` must not include `company_ids`
- only privileged users can directly create public or active uploads
- portal access only returns documents that are `published` and allowed by tenant or visibility checks

### Operational implications

- changing audience after review submission creates drift warnings during approval
- company deactivation and assignment reconciliation can downgrade audience state
- portal and public APIs intentionally return `404` for inaccessible documents instead of leaking existence

## Rate Limiting

Rate limiting is Redis-backed in production and controlled through environment variables.

Relevant variables:

- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS=100`
- `RATE_LIMIT_WINDOW=60`

Notes:

- `/health` is excluded from rate limiting
- Auth and API traffic should run behind Redis in production
- Collab connection counts are also guarded with `COLLAB_MAX_TOTAL_CONNECTIONS`, `COLLAB_MAX_CONNECTIONS_PER_DOCUMENT`, and `COLLAB_RECONNECT_WINDOW_SECONDS`

## File Uploads

Current upload model:

- Max upload size default: `50 MB`
- Storage: local filesystem by default, S3-compatible when enabled
- Typical content: document attachments, imported office files, images
- Validation: file-type checks and content validation before acceptance

Management upload endpoint:

- `POST /api/v1/documents/upload`

Supported management upload types:

- `DOCX`
- `PPTX`
- `PDF`

Upload rules enforced by the endpoint:

- requires `editor` role or above
- PDF uploads require `pdf_conversion_target` set to `docx` or `pptx`
- only managers and above may upload directly as `public`
- only managers and above may upload directly as `active`
- `company_ids` are only valid when `visibility=company`
- an optional `release_notes` file can be attached during upload

Key variables:

- `MAX_UPLOAD_SIZE`
- `S3_ENABLED`
- `S3_BUCKET`
- `S3_ENDPOINT_URL`

## HTTP Status Codes and Error Handling

Common API responses:

| Code  | Meaning               | Typical case                            |
| ----- | --------------------- | --------------------------------------- |
| `200` | OK                    | Successful read or update               |
| `201` | Created               | Resource created                        |
| `204` | No Content            | Successful delete                       |
| `400` | Bad Request           | Validation or malformed input           |
| `401` | Unauthorized          | Missing or invalid auth                 |
| `403` | Forbidden             | RBAC or tenant isolation denial         |
| `404` | Not Found             | Unknown route or entity                 |
| `409` | Conflict              | Pending review exists or state conflict |
| `422` | Unprocessable Entity  | Schema validation failure               |
| `429` | Too Many Requests     | Rate limit exceeded                     |
| `500` | Internal Server Error | Unexpected backend failure              |

Health endpoints:

- `GET /health`
- `GET /health/detailed`
- `GET /api/v1/assistant/health`
- `GET http://localhost:8003/health` for collaboration runtime

## FAQ

### Can I run without Docker?

Yes. Run the backend, frontend, and collab server separately, but you still need Redis for production-like behavior and Ollama if you want assistant features locally.

### Does the platform require PostgreSQL?

No for local development. Yes, it is the recommended production database.

### Where do I find the API contract?

Use `http://localhost:8000/api/v1/openapi.json` or the generated frontend contracts.

### Are demo users always seeded?

No. Development and test seed automatically by default. Production and staging require `SEED_DEMO_DATA=true`.

### Can I disable the AI stack?

Yes. Do not start the `ollama` profile if you do not need assistant inference.

### Why do portal requests return 404 instead of 403 for some documents?

The portal and public surfaces intentionally avoid revealing document existence when the audience policy does not allow access.

### What does company visibility require?

At least one assigned company. If `company_ids` are missing, the backend rejects the request.

## Monitoring and Logging

Useful checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8003/health
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f collab-server
```

Operational areas to watch:

- API error rates
- assistant health and queue pressure
- Redis connectivity
- collaboration connection counts
- database latency
- upload failures

## Deployment

Production guidance:

1. Set a strong `SECRET_KEY`
2. Use PostgreSQL and Redis
3. Set explicit `CORS_ORIGINS`
4. Set deployed `VITE_API_URL` and `VITE_COLLAB_SERVER_URL`
5. Disable demo seeding unless intentionally needed
6. Run Alembic migrations for all active databases
7. Decide whether AI is enabled and provision Ollama separately if needed
8. Put the services behind TLS and a reverse proxy

The repo includes:

- `docker-compose.yml` for local development
- `docker-compose.prod.yml` for production-oriented orchestration

## Troubleshooting

### Backend will not start

- Verify `SECRET_KEY` is set
- Check `docker compose logs backend`
- Confirm `DATABASE_URL` is valid

### Frontend cannot reach the API

- Confirm backend is healthy at `http://localhost:8000/health`
- Check `VITE_API_PROXY_TARGET` and `VITE_API_URL`
- Confirm the frontend dev server is on port `3000`

### Collaboration is disconnected

- Confirm `collab-server` is running on `8002`
- Check `http://localhost:8003/health`
- Verify backend and collab server share the same `SECRET_KEY`

### AI assistant is unavailable

- Start the AI profile: `docker compose --profile ai up -d`
- Check `OLLAMA_BASE_URL`
- Inspect `GET /api/v1/assistant/health`

### Contracts are out of date

```bash
cd frontend
npm run refresh:api-contracts
```

## Contributing

Use the repository as a multi-service project, not as isolated folders.

Expected contribution flow:

1. Branch from `main`
2. Pull the latest `main` before starting work
3. Keep changes scoped to one feature, bug, or documentation concern
4. Run the relevant tests and quality gates for the services you touched
5. Update documentation when behavior, setup, permissions, or deployment expectations change
6. Open a PR with a concise summary and testing notes

Recommended pre-PR checks:

```bash
# Backend
cd backend
pytest tests/ -v
ruff check app/ tests/

# Frontend
cd ../frontend
npm run generate:api-contracts:check
npm run test -- --run
npm run build

# Collaboration server
cd ../collab-server
npm run typecheck
npm run test
```

When to update docs:

- new endpoints or changed request or response shapes
- role or audience policy changes
- environment variable or deployment changes
- workflow changes for review, publishing, collaboration, or assistant behavior

Reference docs:

- [Development Guide](./docs/DEVELOPMENT.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Authorization Matrix](./docs/AUTHORIZATION_MATRIX.md)
- [Architecture](./docs/ARCHITECTURE.md)

## Support

Useful repository docs:

- [APP_FEATURE_MAP.md](./APP_FEATURE_MAP.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/API_EXAMPLES.md](./docs/API_EXAMPLES.md)
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)
- [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)
- [docs/adr](./docs/adr)

## License

MIT. See [LICENSE](./LICENSE).

Last Updated: May 2026
Version: 2.0.0
