# Documentation Platform

[![CI/CD](https://github.com/Yogevso/finale_project/actions/workflows/test.yml/badge.svg)](https://github.com/Yogevso/finale_project/actions/workflows/test.yml)

A modern, multi-tenant Document Management System built with FastAPI, React, and SQLite. Features rich text editing, version control, file attachments, real-time notifications, customer portal with company-based access, and a public viewer portal.

---

## 🚀 Features

### Management Portal (Internal Users)

- **🔐 Authentication & Authorization**
  - JWT-based authentication with refresh tokens
  - Role-based access control (System Admin, Admin, Manager, Editor, Viewer, Customer)
  - Password reset with email verification
  - Multi-tenancy support with tenant isolation

- **📄 Document Management**
  - Create, edit, and delete documents
  - Rich text editor with TipTap (headings, lists, tables, links)
  - Document categorization and tagging
  - Draft → Active → Archived workflow
  - Bulk document upload (PDF/Word)

- **📝 Version Control**
  - Immutable version history
  - Publish specific versions to viewer portal
  - Version comparison and change summaries
  - Rollback capability

- **📎 File Attachments**
  - Upload files to documents (PDF, Word, images, etc.)
  - S3-compatible storage (AWS S3, MinIO, Azure Blob)
  - Secure download URLs with expiration
  - File size limits (10MB default)

- **💬 Comments & Collaboration**
  - Threaded comments with replies
  - Private comments (admin/editor only)
  - Inline comments anchored to text
  - Comment resolution workflow
  - @mentions and notifications

- **🤝 Real-Time Collaboration**
  - Google Docs-style simultaneous editing
  - Live cursor presence (see where others are editing)
  - Yjs CRDT conflict resolution
  - Automatic sync with offline support
  - Collaboration snapshots and history

- **🔔 Notifications**
  - Real-time notification bell with unread count
  - Email notifications (document published, comments, replies)
  - Notification preferences per user
  - Mark as read / mark all as read

- **📊 Engagement & Analytics**
  - Document view tracking
  - Reading progress indicators
  - Helpful/Not helpful feedback
  - User bookmarks
  - Saved searches

- **📈 Analytics Dashboard**
  - Overview statistics with trend analysis
  - Engagement analytics (views, downloads, reading progress)
  - User analytics (role distribution, activity) - Admin+
  - Content production metrics (documents, versions, reviews)
  - Feedback analytics with response times
  - Tenant comparison (System Admin only)
  - Export reports (CSV/PDF)
  - Interactive charts with Recharts

- **🔍 Search & Filtering**
  - Full-text search across documents
  - Filter by category, status, date range
  - Save and reuse search filters
  - Recent documents quick access

- **👥 User Management**
  - CRUD operations for users
  - Assign roles and permissions
  - Tenant-scoped user management
  - Activity audit logs

- **🛠️ System Setup (Phase 1)**
  - System Admin console for global settings
  - RBAC policy management with publish-to-ACL flow
  - System actions logged to audit logs

- **🏢 Multi-Tenancy**
  - Complete tenant isolation
  - Super Admin can manage all tenants
  - Tenant-specific settings and branding
  - Cross-tenant document sharing (future)

### Customer Portal (Authenticated Customers)

- **🏢 Company-Based Access**
  - Customers see documents assigned to their company
  - Company visibility (COMPANY level) for targeted content
  - Public documents also visible
  - Secure authenticated access

- **📝 Customer Engagement**
  - Submit feedback on documents
  - View document versions
  - Download attachments
  - Search within accessible documents

- **👤 Customer Management**
  - Admin assigns customers to companies
  - Companies assigned to documents via visibility
  - Self-service password reset

### Viewer Portal (Public)

- **📖 Document Viewing**
  - Clean, distraction-free reading experience
  - Published version access only (PUBLIC visibility)
  - Table of contents navigation
  - Print-friendly layout

- **🔍 Discovery**
  - Browse all public documents
  - Search and filter
  - Category-based navigation
  - Recent and popular documents

- **📥 Downloads**
  - Download attachments from public documents
  - Download tracking and analytics

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│  FastAPI        │     │  Hocuspocus     │
│   (Vite + TS)   │     │  Backend        │◀───▶│  Collab Server  │
│   Port: 3000    │     │  Port: 8000     │     │  Port: 8002     │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │                      ▲
         │   WebSocket           │                      │
         └───────────────────────┼──────────────────────┘
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  SQLite  │ │ S3/MinIO │ │  SMTP    │
              │ Database │ │ Storage  │ │  Email   │
              └──────────┘ └──────────┘ └──────────┘
```

### Technology Stack

| Layer             | Technology                                                                           |
| ----------------- | ------------------------------------------------------------------------------------ |
| **Frontend**      | React 18, TypeScript 5, Vite 5, TailwindCSS 3, TipTap Editor                         |
| **Design System** | Zip B (Space Grotesk + IBM Plex Sans, Slate/Sky/Emerald/Rose palette)                |
| **Real-time**     | Hocuspocus (Yjs CRDT), WebSocket collaboration                                       |
| **Backend**       | FastAPI 0.109+, Python 3.11+, SQLAlchemy 2.0, Pydantic 2.0                           |
| **Database**      | SQLite (development), PostgreSQL (production ready)                                  |
| **Storage**       | S3-compatible (AWS S3, MinIO, Azure Blob, local filesystem)                          |
| **Email**         | aiosmtplib (SMTP), HTML templates                                                    |
| **Testing**       | Pytest 262+ tests (backend), Vitest (frontend), Playwright 278 E2E tests (100% pass) |
| **CI/CD**         | GitHub Actions (lint, test, build, docker)                                           |
| **Deployment**    | Docker Compose                                                                       |

---

## 📦 Project Structure

.
├── backend/ # FastAPI backend (API, auth, RBAC, tenants, analytics)
│ ├── app/
│ │ ├── api/ # Route groups (management / portal / public / viewer / health)
│ │ ├── config.py # App settings & environment configuration
│ │ ├── db.py # DB session/engine setup
│ │ ├── dependencies/ # Auth, tenant context, permissions dependencies
│ │ ├── middleware/ # CORS, logging, tenant isolation, security middleware
│ │ ├── models/ # SQLAlchemy ORM models
│ │ ├── schemas/ # Pydantic request/response schemas
│ │ ├── security.py # Security utilities (JWT, hashing, guards)
│ │ ├── services/ # Business logic layer
│ │ ├── utils/ # Shared helpers (converters, validators, etc.)
│ │ └── workers/ # Background jobs / async workers (if enabled)
│ ├── tests/ # Pytest suite (auth, documents, collab, analytics, portals, etc.)
│ ├── data/ # Local DB + uploads (dev)
│ ├── Dockerfile
│ ├── pyproject.toml
│ └── requirements*.txt
│
├── collab-server/ # Hocuspocus (Yjs) real-time collaboration server
│ ├── src/
│ │ ├── index.ts # Server entry (WebSocket)
│ │ ├── auth.ts # JWT auth hook
│ │ ├── persistence.ts # Document persistence hook (store/load Yjs state)
│ │ └── tests/ # Jest unit tests
│ ├── Dockerfile
│ └── package.json
│
├── frontend/ # React + Vite + TS + Tailwind + TipTap
│ ├── src/
│ │ ├── components/ # UI components (editor, collaboration UI, analytics widgets, etc.)
│ │ ├── pages/ # App pages (admin, portal, public, viewer)
│ │ ├── layouts/ # Layout wrappers for different portals
│ │ ├── lib/ # API clients, auth context, collaboration hooks, utils
│ │ ├── stores/ # Client state stores (e.g., collaboration store)
│ │ └── types/ # Shared TS types
│ ├── e2e/ # Playwright E2E tests (roles, workflows, collaboration)
│ ├── Dockerfile / Dockerfile.dev
│ └── nginx.conf
│
├── docs/ # Product + dev documentation
│ ├── ARCHITECTURE.md
│ ├── DEVELOPMENT.md
│ ├── USER_GUIDE.md
│ └── API_EXAMPLES.md
│
├── diagrams/ # System diagrams + phased architecture docs
│ ├── phases/ # P0–P7 phase breakdown + traceability
│ └── *.md
│
├── scripts/ # Dev/test/deploy helper scripts
│ ├── dev.sh / dev.ps1
│ ├── test.sh / test.ps1
│ ├── stop.sh / stop.ps1
│ └── load_test_collaboration.py
│
├── docker-compose.yml # Local development stack
├── docker-compose.prod.yml # Production stack
├── REALTIME_COLLABORATION_PLAN.md
├── ANALYTICS_DASHBOARD_PLAN.md
├── CUSTOMER_PORTAL_PLAN.md
└── skills/ # Internal skills for agents (prompt-capability-builder)

---

## 🎨 Design System (Zip B)

The frontend uses the **Zip B Design System** for a modern, cohesive visual experience.

### Typography

- **Display Font**: Space Grotesk (headings)
- **Body Font**: IBM Plex Sans (text, UI)

### Color Palette

| Color       | Usage                         |
| ----------- | ----------------------------- |
| `slate-*`   | Backgrounds, text, borders    |
| `sky-*`     | Primary actions, links, focus |
| `emerald-*` | Success, published, positive  |
| `amber-*`   | Warning, draft, pending       |
| `rose-*`    | Error, delete, destructive    |

### Component Classes

| Class           | Description               |
| --------------- | ------------------------- |
| `surface-card`  | Card with border & shadow |
| `btn-primary`   | Primary action button     |
| `btn-secondary` | Secondary outline button  |
| `btn-ghost`     | Transparent hover button  |
| `input-field`   | Styled text input         |
| `select-field`  | Styled dropdown           |
| `pill`          | Rounded badge/tag         |

---

## 🚀 Quick Start

This project supports three execution modes:

1. Local Development (manual services)
2. Docker Compose (Development stack)
3. Docker Compose (Production stack)

---

## 📋 Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

---

# 🧪 Option 1: Local Development (Manual Services)

### Backend (FastAPI)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend:

- http://localhost:8000
- Swagger: http://localhost:8000/api/v1/docs

---

### Real-time Collaboration Server (Hocuspocus + Yjs)

```bash
cd collab-server
npm install
npm run dev
```

- WebSocket: ws://localhost:8002
- Health (dev): http://localhost:8003/health

---

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000

---

### Local Access Summary

| Service     | URL                               |
| ----------- | --------------------------------- |
| Frontend    | http://localhost:3000             |
| Backend API | http://localhost:8000             |
| API Docs    | http://localhost:8000/api/v1/docs |
| Collab WS   | ws://localhost:8002               |

---

# 🐳 Option 2: Docker Compose (Development)

```bash
docker compose up -d --build
```

Services started:

- Backend (8000)
- Frontend (3000)
- Collab Server (8002 + 8003)

Access:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/api/v1/docs
- Collab WS: ws://localhost:8002

Stop:

```bash
docker compose down
```

Reset database (⚠ deletes all data):

```bash
docker compose down -v
```

---

# 🚀 Option 3: Docker Compose (Production)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Services started:

- Backend (container 8000 → exposed as 8001)
- Frontend (80 / 443)
- Collab Server (8002)
- Optional Redis (profile: with-redis)

Production access:

| Service     | URL                |
| ----------- | ------------------ |
| Frontend    | http://<host>      |
| Backend API | http://<host>:8001 |
| Collab WS   | ws://<host>:8002   |

Enable Redis scaling:

```bash
docker compose -f docker-compose.prod.yml --profile with-redis up -d
```

Stop production:

```bash
docker compose -f docker-compose.prod.yml down
```

---

# 🧪 Running Tests

Backend:

```bash
cd backend
pytest -v
```

Frontend:

```bash
cd frontend
npm test
npm run test:e2e
```

---

# 🩺 Health Endpoints

Backend:

- `/health` (development)
- `/ready` (production)

Collab Server:

- `/health` (port 8003 in development)

---

# 📦 Persistent Docker Volumes

- backend-data
- backend-uploads
- redis-data (if enabled)

⚠ Use `docker compose down -v` only if you want to wipe all stored data.

## 🔑 Default Users

| Username  | Password    | Role         | Description                           |
| --------- | ----------- | ------------ | ------------------------------------- |
| sysadmin  | sysadmin123 | System Admin | Full system access, manage all admins |
| admin     | admin123    | Admin        | Manage users, companies, settings     |
| manager   | manager123  | Manager      | Publish, delete, approve reviews      |
| editor    | editor123   | Editor       | Create, edit documents, comments      |
| viewer    | viewer123   | Viewer       | Read-only internal access             |
| customer1 | customer123 | Customer     | Customer portal access (Company A)    |
| customer2 | customer123 | Customer     | Customer portal access (Company B)    |

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=sqlite:///./data/document_portal.db

# Authentication
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Storage (S3-compatible)
STORAGE_BACKEND=local  # or "s3"
S3_BUCKET_NAME=document-portal
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_REGION=us-east-1

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourcompany.com

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000
```

---

## 🧪 Testing

### Backend Tests (262+ tests)

```bash
cd backend
pytest -v                              # Run all tests
pytest --cov=app --cov-report=html     # With coverage
pytest tests/test_portal_api.py -v     # Customer portal tests
pytest tests/test_permissions.py -v    # Permission tests
pytest tests/test_roles.py -v          # Role-based tests
```

### Frontend E2E Tests (278 tests - 100% pass rate)

```bash
cd frontend
npm test           # Unit tests (Vitest)
npm run test:e2e   # E2E tests (Playwright)

# Run specific role tests
npx playwright test admin.spec.ts
npx playwright test customer.spec.ts
npx playwright test permissions.spec.ts
```

### Linting

```bash
# Backend
cd backend
ruff check app/
ruff format app/

# Frontend
cd frontend
npm run lint
```

---

## 📋 API Documentation

### Authentication

| Method | Endpoint                           | Description               |
| ------ | ---------------------------------- | ------------------------- |
| POST   | `/api/auth/login`                  | Login and get tokens      |
| POST   | `/api/auth/logout`                 | Logout current session    |
| POST   | `/api/auth/refresh`                | Refresh access token      |
| POST   | `/api/auth/password-reset/request` | Request password reset    |
| POST   | `/api/auth/password-reset/reset`   | Reset password with token |

### Documents

| Method | Endpoint                | Description          |
| ------ | ----------------------- | -------------------- |
| GET    | `/api/documents`        | List documents       |
| POST   | `/api/documents`        | Create document      |
| GET    | `/api/documents/{id}`   | Get document         |
| PUT    | `/api/documents/{id}`   | Update document      |
| DELETE | `/api/documents/{id}`   | Delete document      |
| POST   | `/api/documents/upload` | Upload PDF/Word file |

### Versions

| Method | Endpoint                       | Description     |
| ------ | ------------------------------ | --------------- |
| GET    | `/api/documents/{id}/versions` | List versions   |
| POST   | `/api/documents/{id}/versions` | Create version  |
| POST   | `/api/versions/{id}/publish`   | Publish version |

### Comments

| Method | Endpoint                       | Description    |
| ------ | ------------------------------ | -------------- |
| GET    | `/api/documents/{id}/comments` | List comments  |
| POST   | `/api/documents/{id}/comments` | Add comment    |
| PUT    | `/api/comments/{id}`           | Update comment |
| DELETE | `/api/comments/{id}`           | Delete comment |
| PUT    | `/api/comments/{id}/resolve`   | Resolve thread |

### Notifications

| Method | Endpoint                          | Description          |
| ------ | --------------------------------- | -------------------- |
| GET    | `/api/notifications`              | List notifications   |
| GET    | `/api/notifications/unread-count` | Get unread count     |
| POST   | `/api/notifications/mark-read`    | Mark as read         |
| DELETE | `/api/notifications`              | Delete notifications |

### Full API documentation available at `/api/v1/docs` (Swagger UI) or `/api/v1/redoc` (ReDoc).

---

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/test.yml`) runs:

1. **Backend Lint** - Ruff code quality checks
2. **Backend Tests** - Pytest with SQLite
3. **Frontend Lint** - ESLint + TypeScript checks
4. **Frontend Build** - Vite production build
5. **Frontend Tests** - Vitest unit tests
6. **Docker Build** - Build and validate images (main branch only)

---

## 📈 Roadmap

### Completed ✅

- [x] User authentication & authorization
- [x] Document CRUD with rich text
- [x] Version control with publishing
- [x] File attachments (S3)
- [x] Threaded comments
- [x] Notifications (in-app + email)
- [x] Multi-tenancy
- [x] Public viewer portal
- [x] Search & saved searches
- [x] Engagement tracking
- [x] Customer Portal (company-based document access, feedback)
- [x] Advanced analytics dashboard (Overview, Engagement, Users, Content, Feedback, Tenant sections)
- [x] Real-time collaboration (TipTap + Yjs + Hocuspocus, presence, offline, snapshots)

### Planned 🔜

- [ ] Document templates
- [ ] Workflow approvals
- [ ] Mobile app (React Native)
- [ ] AI-powered search and summaries

> Implementation details: see REALTIME_COLLABORATION_PLAN.md

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
