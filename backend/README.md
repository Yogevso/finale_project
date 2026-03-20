# Backend

FastAPI backend for the Documentation Platform.

## Highlights

- Multi-tenant API surface (`management`, `portal`, `public`, `bff`, `viewer` routes)
- Layered architecture (`domain`, `application`, `infrastructure`, `web`)
- CQRS-lite handlers, command/query bus middleware, and process managers
- Durable outbox, idempotency, optimistic concurrency, projection cache
- Policy decision point and policy explanation model
- Observability primitives (use-case telemetry, SLOs, burn-rate checks)
- Selective event-sourcing pilot for review workflow (feature-flagged)
- AI assistant with Ollama LLM, RAG pipeline (ChromaDB), and tool-augmented generation
- DOCX/PPTX content extraction and ingestion pipeline

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

API docs:

- `http://localhost:8000/api/v1/docs`
- `http://localhost:8000/api/v1/redoc`

## AI Assistant

The backend includes a self-hosted AI assistant powered by Ollama:

- **LLM**: llama3.1:8b (served via Ollama on port 11434)
- **Vector Store**: ChromaDB for document embeddings and RAG retrieval
- **Tools**: document search, analytics queries, content extraction
- **Architecture**: `app/assistant/` — engine, conversation manager, tool router, prompts, RAG modules

Requires the Ollama service running (included in Docker Compose).

## Key Environment Flags

Architecture rollout and rollback flags:

- `FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE`
- `FEATURE_FLAG_PROJECTION_CACHE`
- `FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT`

AI/Assistant:

- `OLLAMA_BASE_URL` (default: `http://ollama:11434`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `OLLAMA_MAX_TOKENS` (default: `2048`)

See full guidance: `../docs/feature-rollout-flags.md`.

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
