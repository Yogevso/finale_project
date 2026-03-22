# Backend

FastAPI backend for the Intel Documentation Platform.

## Highlights

- Multi-tenant API surface (`management`, `portal`, `public`, `bff`, `viewer` routes)
- Layered architecture (`domain`, `application`, `infrastructure`, `web`)
- 6-tier RBAC with centralized policy decision point and tenant isolation
- JWT + httpOnly cookie auth with session management, account lockout, concurrent session limits
- HMAC-signed tamper-evident audit logging
- Optimistic concurrency (`row_version` / ETag) on documents and versions
- Review workflow with audience snapshots, drift detection, and version locking
- AI assistant with Ollama LLM, RAG pipeline (ChromaDB), and 29 tool-augmented responses
- DOCX/PPTX content extraction and ingestion pipeline
- Global exception handler (safe 500s — no internal leak)
- Non-root Docker container via gosu privilege drop
- Required `SECRET_KEY` — no hardcoded fallbacks

## API Domains

| Domain | Modules | Description |
| --- | --- | --- |
| **Management** | auth, users, companies, tenants, documents, versions, attachments, analytics, assistant, chat, reviews, feedback, support, notifications, engagement, rbac, announcements, canned_responses, search, invitations, gdpr, collaboration | Internal admin/editor APIs |
| **Portal** | documents, feedback, nps, support | Customer-facing APIs |
| **Public** | documents, platforms, announcements, changelog, topics, sitemap | Unauthenticated public APIs |
| **Viewer** | documents | Public document viewer |
| **BFF** | documents | Backend-for-Frontend orchestration |

## Important Paths

- `app/api/`: FastAPI route modules (management, portal, public, viewer, bff)
- `app/application/`: command/query handlers, bus/pipeline orchestration
- `app/domain/`: aggregates, value objects, specifications, workflows
- `app/infrastructure/`: adapters and persistence-facing components
- `app/observability/`: telemetry, SLO, burn-rate models
- `app/event_store/`: event-sourcing pilot components
- `app/assistant/`: AI assistant engine, Ollama client, RAG pipeline, tools
- `tests/`: backend tests (unit/integration/contracts/security/resilience)

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/api/v1/docs | http://localhost:8000/api/v1/redoc

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SECRET_KEY` | **Yes** | — | Signing key for JWT and sessions |
| `DATABASE_URL` | No | `sqlite:///./data/portal.db` | Database connection string |
| `OLLAMA_BASE_URL` | No | `http://ollama:11434` | Ollama LLM service URL |
| `ASSISTANT_MODEL` | No | `llama3.1:8b` | Ollama model name |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis for rate limiting and pub/sub |

Feature flags: see `../docs/feature-rollout-flags.md`.

## AI Assistant

Self-hosted AI assistant powered by Ollama:

- **LLM**: llama3.1:8b (served via Ollama on port 11434)
- **Vector Store**: ChromaDB for document embeddings and RAG retrieval
- **Tools**: 29 tools — document search, analytics queries, content extraction
- **Security**: All RAG tools enforce `DocumentAccessPolicy.can_view_document()` before loading content
- **Architecture**: `app/assistant/` — engine, conversation manager, tool router, prompts, RAG modules

Requires the Ollama service running (included in Docker Compose with `--profile ai`).

## Quality Gates

Lint and format:

```bash
ruff check app/ tests/
ruff format app/ tests/ --check
```

Full backend tests:

```bash
pytest tests/ -v
```

## Related Docs

- `../docs/adr/`
- `../docs/migrations/`
- `../docs/slo/`
- `../scripts/migration_safety/README.md`
- `../scripts/chaos/README.md`
