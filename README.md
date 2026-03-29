# Intel Documentation Platform

[![CI](https://github.com/Yogevso/finale_project/actions/workflows/ci.yml/badge.svg)](https://github.com/Yogevso/finale_project/actions/workflows/ci.yml)
[![Security](https://github.com/Yogevso/finale_project/actions/workflows/security.yml/badge.svg)](https://github.com/Yogevso/finale_project/actions/workflows/security.yml)

A multi-tenant document management platform built for Intel. Internal staff create, review, and publish documentation while external customers (Dell, Lenovo, HP, etc.) access company-scoped content through a dedicated portal.

**Stack:** FastAPI + React 18 + TypeScript + Hocuspocus (Yjs CRDT) + Ollama AI + ChromaDB + SQLite/PostgreSQL

---

## Features

### Management Portal (Internal Users)

- **Authentication & Authorization** — JWT + httpOnly cookie sessions, 6-tier RBAC (System Admin → Customer), bcrypt, account lockout, concurrent session limits, timing-safe comparisons
- **Document Management** — CRUD, rich text editor (TipTap), categorization/tagging, Draft → Active → Archived workflow, bulk upload (PDF/Word), DOCX/PPTX content extraction
- **Version Control** — Immutable version history, publish to viewer portal, version comparison, rollback
- **Review Workflow** — Submit/approve/reject pipeline, audience snapshots with drift detection, stale-company checks at publish time, audience version locking
- **File Attachments** — Upload PDF, Word, images; S3-compatible storage (AWS S3, MinIO, Azure Blob, local); magic-byte validation; 50 MB default limit
- **Real-Time Collaboration** — Google Docs-style simultaneous editing, live cursor presence, Yjs CRDT conflict resolution, offline support, snapshots
- **Comments & Collaboration** — Threaded comments with replies, private comments, inline text anchoring, resolution workflow, @mentions
- **AI Assistant** — Self-hosted LLM (Ollama llama3.1:8b), RAG pipeline with ChromaDB, 29 tool-augmented responses, document access policy enforcement on all tools
- **Chat & Messaging** — Real-time direct and group messaging, reactions, threading, online presence, tenant-scoped
- **Analytics Dashboard** — Engagement, user, content production, feedback metrics, tenant comparison (System Admin), CSV/PDF export with row limits
- **Support Desk** — Ticket management with tenant isolation, agent assignment with boundary checks, canned responses
- **Notifications** — Real-time bell with unread count, email notifications, per-user preferences
- **Search** — Full-text search (FTS5), autocomplete, faceted filtering, saved searches
- **User & Company Management** — CRUD, role assignment, tenant-scoped, invitation workflow
- **RBAC & System Setup** — Policy decision point, publish-to-ACL flow, system admin console, HMAC-signed audit logs
- **Multi-Tenancy** — Complete tenant isolation enforced at service layer, middleware-level context propagation

### Customer Portal

- **Company-Based Access** — Customers see documents assigned to their company, public documents visible
- **Engagement** — Submit feedback, view versions, download attachments, search within accessible documents
- **Support Tickets** — Create and track tickets, reply to agents
- **AI Assistant** — Portal-scoped assistant with document access policy enforcement
- **NPS Surveys** — Tenant-scoped with rate limiting

### Public Viewer Portal

- **Document Viewing** — Distraction-free reading, published versions only (PUBLIC visibility), table of contents, print-friendly
- **Discovery** — Browse, search, filter, category/platform navigation
- **Changelog & Help** — Public-facing change history and help center

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│  FastAPI        │────▶│  Ollama (LLM)   │
│   (Vite + TS)   │     │  Backend        │     │  llama3.1:8b    │
│   Port: 3000    │     │  Port: 8000     │     │  Port: 11434    │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         │   WebSocket           │◀───▶┌─────────────────┐
         │                       │     │  Hocuspocus     │
         └───────────────────────┼────▶│  Collab Server  │
                                 │     │  Port: 8002     │
                    ┌────────────┼─────└─────────────────┘
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  SQLite / │ │ ChromaDB │ │  Redis   │
              │ PostgreSQL│ │ Vectors  │ │  Cache   │
              └──────────┘ └──────────┘ └──────────┘
```

### Technology Stack

| Layer | Technology |
| --- | --- |
| **Frontend** | React 18, TypeScript 5, Vite 5, TailwindCSS 3, TipTap Editor, Recharts |
| **Design System** | Space Grotesk + IBM Plex Sans, Slate/Sky/Emerald/Rose palette, Dark Mode |
| **Real-time** | Hocuspocus (Yjs CRDT), WebSocket collaboration |
| **Backend** | FastAPI 0.115, Python 3.11+, SQLAlchemy 2.0, Pydantic 2.0 |
| **AI / RAG** | Ollama (llama3.1:8b), ChromaDB vector store, tool-augmented generation |
| **Database** | SQLite (development), PostgreSQL (production) |
| **Storage** | S3-compatible (AWS S3, MinIO, Azure Blob, local filesystem) |
| **Cache** | Redis 7 (rate limiting, collab pub/sub) |
| **Testing** | Pytest (backend), Vitest (frontend), Playwright E2E, Lighthouse CI |
| **CI/CD** | GitHub Actions (ci, cd, pr-checks, security, architecture, SLO, chaos) |
| **Deployment** | Docker Compose (5 services) |

### Repository Layout

```
backend/          FastAPI app — domain, application, infrastructure layers, AI assistant, tests
frontend/         React + TypeScript SPA — pages, features, components, e2e tests
collab-server/    Hocuspocus real-time editing server (Yjs CRDT)
docs/             ADRs, migration playbooks, architecture docs, SLO/chaos evidence
scripts/          Migration safety, chaos, observability, scaffolding tools
data/             Runtime data (SQLite DB, ChromaDB vectors, uploads) — gitignored
```

---

## Security

The platform has undergone a comprehensive security audit with all critical and high-priority issues remediated:

- **Tenant Isolation** — Enforced at service layer; NULL tenant_id rejected (except SYSTEM_ADMIN); cross-tenant operations blocked on NPS, support, chat, agent assignment, and document queries
- **Non-Root Container** — Backend runs as a non-root user via gosu privilege drop in the entrypoint
- **No Hardcoded Secrets** — `SECRET_KEY` is required across backend and collab-server; `JWT_SECRET` is legacy fallback only
- **Input Validation** — Magic-byte file validation (including WebP RIFF+WEBP check), DOMPurify on frontend HTML, regex validation on collab-server document IDs
- **Review Integrity** — Audience version lock prevents publish to unintended companies after approval
- **Rate Limiting** — Per-IP rate limiting on auth and API paths via Redis-backed middleware
- **Audit Logging** — HMAC-signed tamper-evident audit trail; 403 DomainErrors logged with user context
- **Global Error Handling** — Unhandled exceptions return safe 500 responses without leaking internals
- **CI Security Gates** — `security.yml` workflow fails on vulnerabilities (no `continue-on-error`); `ci.yml` enforces `--cov-fail-under=70`

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

---

## Quick Start (Docker Compose)

```bash
# 1. Create .env from template
cp .env.example .env
# Edit .env — set SECRET_KEY (required)

# 2. Start all services
docker compose up -d --build

# 3. (Optional) Start with AI assistant
docker compose --profile ai up -d --build
```

Services:

| Service | URL | Port |
| --- | --- | --- |
| Frontend | http://localhost:3000 | 3000 |
| Backend API | http://localhost:8000 | 8000 |
| Swagger UI | http://localhost:8000/api/v1/docs | 8000 |
| Collab WS | ws://localhost:8002 | 8002 |
| Redis | — | 6379 |
| Ollama (optional) | http://localhost:11434 | 11434 |

Stop:

```bash
docker compose down
```

Reset database (deletes all data):

```bash
docker compose down -v
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Collaboration Server

```bash
cd collab-server
npm install
npm run dev
```

---

## Testing

```bash
# Backend
cd backend
pytest tests/ -v                    # 262+ tests
ruff check app/ tests/              # Lint
ruff format app/ tests/ --check     # Format check

# Frontend
cd frontend
npm test -- --run                   # Unit tests (Vitest)
npm run test:e2e                    # E2E tests (Playwright) — 278 tests

# Collab server
cd collab-server
npm run typecheck
npm run test
```

---

## Environment Variables

Copy `.env.example` to `.env` before running. Required variables:

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | **Yes** | Shared backend/collab signing key (`openssl rand -hex 32`) |
| `VITE_COLLAB_SERVER_URL` | No | Frontend collaboration server URL |
| `DATABASE_URL` | No | Default: `sqlite:///./data/portal.db` |
| `OLLAMA_BASE_URL` | No | Default: `http://ollama:11434` |
| `REDIS_URL` | No | Default: `redis://redis:6379/0` |

---

## Default Users (Development or Explicit Demo Seed Only)

These accounts are created automatically only in development/test environments.
Production and staging require an explicit `SEED_DEMO_DATA=true` opt-in.

| Username | Password | Role | Description |
| --- | --- | --- | --- |
| sysadmin | sysadmin123 | System Admin | Full system access |
| admin | admin123 | Admin | Manage users, companies, settings |
| manager | manager123 | Manager | Publish, approve reviews |
| editor | editor123 | Editor | Create, edit documents |
| viewer | viewer123 | Viewer | Read-only internal access |
| customer1 | customer123 | Customer | Customer portal (Company A) |
| customer2 | customer123 | Customer | Customer portal (Company B) |

---

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Purpose |
| --- | --- |
| `ci.yml` | Lint, test (70% coverage gate), build |
| `cd.yml` | Continuous deployment |
| `pr-checks.yml` | Pull request validation |
| `security.yml` | Dependency vulnerability scanning (fails on findings) |
| `architecture-fitness.yml` | Architecture compliance checks |
| `architecture-governance.yml` | Governance rules enforcement |
| `slo-burn-rate.yml` | SLO burn-rate monitoring |
| `staging-chaos.yml` | Chaos testing on staging |

---

## Key Documentation

- [App Feature Map](./APP_FEATURE_MAP.md) — UI areas, roles, routes, and review walkthroughs
- [Architecture](./docs/ARCHITECTURE.md) — System design and component relationships
- [ADRs](./docs/adr/) — Architecture decision records
- [Migration Playbooks](./docs/migrations/) — Database migration guides
- [Feature Rollout Flags](./docs/feature-rollout-flags.md) — Feature flag reference
- [SLO Docs](./docs/slo/) — Service level objectives
- [Authorization Matrix](./docs/AUTHORIZATION_MATRIX.md) — Role/route permission mapping
- [API Examples](./docs/API_EXAMPLES.md) — API usage examples

---

## API Documentation

Interactive API docs are available when the backend is running:

- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc

---

## Roadmap

### Completed

- User authentication & authorization (JWT, RBAC, multi-tenancy)
- Document CRUD with rich text (TipTap)
- Version control with publishing and review workflow
- File attachments (S3-compatible)
- Threaded & inline comments
- Notifications (in-app + email)
- Multi-tenancy with tenant isolation
- Public viewer portal
- Search & saved searches
- Customer Portal (company-based access, feedback, NPS, support)
- Analytics dashboard (engagement, users, content, feedback, tenant)
- Real-time collaboration (TipTap + Yjs + Hocuspocus)
- AI assistant (Ollama + RAG + ChromaDB + tool-augmented chat)
- Real-time chat & messaging (direct, groups, reactions)
- DOCX/PPTX content ingestion pipeline
- Dark mode, accessibility audit (WCAG), skeleton loading
- E2E test suites (a11y, performance, responsive, visual, UX)
- Architecture governance & SLO monitoring
- GDPR compliance endpoints
- Full security audit and remediation

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
