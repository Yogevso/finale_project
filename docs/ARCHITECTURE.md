# Architecture

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Backend** | FastAPI | 0.115.0 |
| **ORM** | SQLAlchemy | 2.0.36 |
| **Database** | SQLite | 3.x (WAL mode) |
| **Validation** | Pydantic | 2.10.3 |
| **Auth** | python-jose (JWT) + bcrypt | - |
| **Frontend** | React | 18.2.0 |
| **Language** | TypeScript | 5.3.3 |
| **Build Tool** | Vite | 5.0.11 |
| **Styling** | TailwindCSS | 3.4.1 |
| **State** | Zustand | 4.5.0 |
| **HTTP Client** | Axios | 1.6.5 |
| **Routing** | React Router | 6.21.2 |
| **Testing** | pytest / Vitest | - |

## Architecture Governance Artifacts

- ADR workflow: `docs/adr/README.md`
- Backend context-first boundary: `docs/adr/ADR-0003-backend-context-first-architecture.md`
- Deprecation lifecycle policy: `docs/deprecation-policy.md`
- Active deprecations register: `docs/deprecations.md`
- Refactor wave playbooks: `docs/migrations/README.md`
- Contract versioning policy: `docs/contracts/versioning.md`
- Data ownership map: `docs/context-ownership.md`
- Context map artifacts: `docs/context-map/README.md`
- Architecture debt register: `docs/architecture-debt.md`

## Backend Orchestration Boundary

The backend follows a context-first modular monolith pattern.

- `app.api/**` and websocket modules are transport adapters.
- `app.application.contexts.<context>.api` is the public orchestration surface for new backend work.
- DDD aggregates, command/query handlers, repositories, and services are internal implementation techniques inside a context.
- `app.web.controllers/**` remains as a compatibility layer and must not be imported by route modules.

## Repository Boundary

The repository layer is aggregate-scoped, not universal.

- Aggregate-heavy write domains should use repositories as their persistence boundary.
- Projection/reporting/admin read paths may query directly when they are not modeling aggregate mutation.
- The current repository-backed domains are users, invitations, comments, versions, documents, and support tickets.
- See `docs/adr/ADR-0004-aggregate-repository-boundaries.md` for the policy.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    React SPA                                 ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ││
│  │  │  Pages   │  │Components│  │  Stores  │  │  API Client │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Vite Dev Proxy                              │
│                   /api/* → localhost:8001                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐│   │
│  │  │  Routes  │  │  Schemas │  │     Dependencies         ││   │
│  │  └──────────┘  └──────────┘  └──────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Service Layer                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │AuthService│ │DocService│  │VersionSvc│  │ AuditSvc │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Data Layer                              │   │
│  │  ┌──────────────────────┐  ┌─────────────────────────┐   │   │
│  │  │  SQLAlchemy Models   │  │   Multi-DB Sessions     │   │   │
│  │  │  CoreBase (45)       │  │   get_db()              │   │   │
│  │  │  AnalyticsBase (7)   │  │   get_analytics_db()    │   │   │
│  │  │  ChatBase (10)       │  │   get_chat_db()         │   │   │
│  │  └──────────────────────┘  └─────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────┬──────────────────────┬───────────────────┬───────────┘
           │                      │                   │
           ▼                      ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Core Database   │  │ Analytics Database│  │  Chat Database   │
│  data/portal.db  │  │ data/analytics.db │  │  data/chat.db    │
│  (45 tables)     │  │ (7 tables)        │  │  (10 tables)     │
│  Users, Docs,    │  │ AuditLogs,        │  │  Notifications,  │
│  Versions, etc.  │  │ SecurityEvents,   │  │  Chats, AI       │
│                  │  │ NPS, Onboarding   │  │  Assistant, etc.  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │       │  Document   │       │   Version   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ username    │◄──────│ created_by  │       │ document_id │──┐
│ email       │       │ title       │◄──────│ version_num │  │
│ password_   │       │ description │   │   │ content     │  │
│   hash      │       │ status      │   │   │ is_published│  │
│ role        │       │ created_at  │   │   │ published_at│  │
│ is_active   │       │ updated_at  │   │   │ created_at  │  │
│ created_at  │       └─────────────┘   │   └─────────────┘  │
└─────────────┘                         │                    │
      │                                 │   ┌─────────────┐  │
      │    ┌─────────────┐              │   │   Section   │  │
      │    │  Attachment │              │   ├─────────────┤  │
      │    ├─────────────┤              │   │ id (PK)     │  │
      │    │ id (PK)     │              │   │ version_id  │◄─┘
      │    │ document_id │──────────────┘   │ order       │
      │    │ filename    │                  │ title       │
      │    │ storage_key │                  │ content     │
      │    │ size_bytes  │                  │ created_at  │
      │    │ content_type│                  └─────────────┘
      │    │ created_at  │
      │    └─────────────┘
      │
      │    ┌─────────────┐       ┌─────────────────┐
      │    │   Comment   │       │   Notification  │
      │    ├─────────────┤       ├─────────────────┤
      └───►│ id (PK)     │       │ id (PK)         │
           │ document_id │       │ user_id (FK)    │◄────┐
           │ user_id(FK) │       │ type            │     │
           │ content     │       │ title           │     │
           │ parent_id   │──┐    │ message         │     │
           │ created_at  │  │    │ is_read         │     │
           └─────────────┘  │    │ read_at         │     │
                  ▲         │    │ created_at      │     │
                  └─────────┘    └─────────────────┘     │
               (threading)                               │
                                                         │
      ┌─────────────────┐       ┌─────────────────┐      │
      │   AuditLog      │       │  PasswordReset  │      │
      ├─────────────────┤       ├─────────────────┤      │
      │ id (PK)         │       │ id (PK)         │      │
      │ user_id (FK)    │       │ user_id (FK)    │──────┘
      │ action          │       │ token_hash      │
      │ entity_type     │       │ expires_at      │
      │ entity_id       │       │ used_at         │
      │ details (JSON)  │       │ created_at      │
      │ ip_address      │       └─────────────────┘
      │ user_agent      │
      │ timestamp       │
      └─────────────────┘
```

### Tables Summary

The platform uses a 3-database architecture. When `ANALYTICS_DATABASE_URL` and
`CHAT_DATABASE_URL` are not set, all tables fall back to the core database.

**Core Database** (45 tables — `DATABASE_URL`):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | username, email, role, password_hash |
| `documents` | Document metadata | title, description, status, created_by |
| `versions` | Document versions | document_id, version_number, content, is_published |
| `sections` | Version sections | version_id, order, title, content |
| `attachments` | File uploads | document_id, filename, storage_key |
| `comments` | Document comments | document_id, user_id, content, parent_id |
| `password_resets` | Password reset tokens | user_id, token_hash, expires_at |

**Analytics Database** (7 tables — `ANALYTICS_DATABASE_URL`):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `audit_logs` | Tamper-evident audit trail | user_id, action, details, signature |
| `security_events` | Security incident log | user_id, event_type, ip_address |
| `nps_surveys` | NPS survey responses | user_id, score, feedback |
| `search_analytics` | Search query analytics | user_id, query, results_count |
| `onboarding_events` | User onboarding tracking | user_id, step, completed |
| `activation_milestones` | User activation metrics | user_id, milestone_type |
| `domain_event_outbox` | Outbox for event publishing | event_type, payload, published |

**Chat Database** (10 tables — `CHAT_DATABASE_URL`):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `notifications` | User notifications | user_id, type, title, message, is_read |
| `chats` | Chat rooms | name, type, created_by |
| `chat_participants` | Chat membership | chat_id, user_id, role |
| `chat_messages` | Chat messages | chat_id, sender_id, content |
| `assistant_conversations` | AI assistant sessions | user_id, title |
| `assistant_messages` | AI assistant messages | conversation_id, role, content |
| `assistant_uploaded_files` | AI assistant file uploads | conversation_id, filename |
| `collaboration_sessions` | Real-time collaboration | document_id, session_type |
| `collaboration_activities` | Collaboration activity log | session_id, user_id, action |
| `collaboration_snapshots` | Collaboration state snapshots | session_id, data |

## API Patterns

### Authentication

```
POST /api/v1/auth/login
  Request:  { "username": "admin", "password": "admin123" }
  Response: { "access_token": "...", "token_type": "bearer", "user": {...} }

POST /api/v1/auth/register
  Request:  { "username": "...", "email": "...", "password": "..." }
  Response: { "id": 1, "username": "...", "email": "...", "role": "VIEWER" }
```

### Protected Endpoints

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

### Pagination

```
GET /api/v1/documents?page=1&page_size=20

Response:
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### Filtering & Search

```
GET /api/v1/documents?status=published&search=quarterly
GET /api/v1/documents?created_after=2024-01-01
```

### Error Responses

```json
{
  "detail": "Document not found"
}
```

HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

## Security

### Password Hashing
- Algorithm: bcrypt
- Work factor: 12 rounds
- Passwords never stored in plaintext

### JWT Tokens
- Algorithm: HS256
- Access token expiry: 30 minutes
- Token contains: `sub` (user_id), `role`, `exp`

### CORS
- Allowed origins: Configured in `CORS_ORIGINS` env var
- Credentials: Allowed
- Methods: GET, POST, PUT, DELETE, OPTIONS

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| ADMIN | Full access to all resources |
| EDITOR | Create, edit, delete documents |
| VIEWER | Read-only access |

#### Dynamic RBAC Policies (Phase 1)
- System Admin can define RBAC policies through the DocsPortal admin console.
- Policies are persisted in `rbac_policies` and published to the ACL engine at runtime.
- If no policies are stored, the system falls back to built-in defaults.

#### System Settings (Phase 1)
- System-wide settings are stored in `system_settings` as key/value entries (JSON values).
- Updates are performed by System Admins and persisted in the CMS store.
- Each update writes a system audit log event (`ActionType.SYSTEM`) to `audit_logs`.

## File Storage

### Local Development
- Files stored in `backend/data/uploads/`
- Path structure: `/{document_id}/{attachment_id}/{filename}`

### Production (TODO)
- S3-compatible storage (AWS S3, MinIO, etc.)
- Pre-signed URLs for secure access
- Storage key format: `{tenant_id}/{document_id}/{attachment_id}/{filename}`

## Design Decisions

### Why SQLite?

1. **Simplicity**: No separate database server to manage
2. **Performance**: Excellent for read-heavy workloads
3. **Portability**: Single file, easy to backup and move
4. **Scale**: Handles 100K+ documents easily
5. **WAL Mode**: Enables concurrent reads with writes

### Why Zustand over Redux?

1. **Simplicity**: Minimal boilerplate
2. **Size**: ~2KB vs ~20KB
3. **TypeScript**: First-class support
4. **No providers**: No Context wrapper needed

### Why Vite over CRA?

1. **Speed**: Instant dev server start
2. **HMR**: Faster hot module replacement
3. **Build**: Faster production builds
4. **Modern**: ESM-first approach

### Why FastAPI over Flask/Django?

1. **Async**: Built-in async support
2. **Typing**: Pydantic integration
3. **Docs**: Auto-generated OpenAPI docs
4. **Performance**: One of the fastest Python frameworks
