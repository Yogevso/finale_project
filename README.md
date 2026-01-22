# Document Portal V2

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
┌─────────────────┐     ┌─────────────────┐
│   React SPA     │     │  FastAPI        │
│   (Vite + TS)   │────▶│  Backend        │
│   Port: 3000    │     │  Port: 8001     │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  SQLite  │ │ S3/MinIO │ │  SMTP    │
              │ Database │ │ Storage  │ │  Email   │
              └──────────┘ └──────────┘ └──────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript 5, Vite 5, TailwindCSS 3, TipTap Editor |
| **Backend** | FastAPI 0.109+, Python 3.11+, SQLAlchemy 2.0, Pydantic 2.0 |
| **Database** | SQLite (development), PostgreSQL (production ready) |
| **Storage** | S3-compatible (AWS S3, MinIO, Azure Blob, local filesystem) |
| **Email** | aiosmtplib (SMTP), HTML templates |
| **Testing** | Pytest 262+ tests (backend), Vitest (frontend), Playwright 278 E2E tests (100% pass) |
| **CI/CD** | GitHub Actions (lint, test, build, docker) |
| **Deployment** | Docker Compose |

---

## 📦 Project Structure

```
├── .github/
│   └── workflows/
│       └── test.yml              # CI/CD pipeline
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── management/       # Admin API routes
│   │   │   │   ├── auth.py       # Login, logout, password reset
│   │   │   │   ├── documents.py  # Document CRUD
│   │   │   │   ├── versions.py   # Version management
│   │   │   │   ├── attachments.py# File uploads
│   │   │   │   ├── comments.py   # Comments & threads
│   │   │   │   ├── notifications.py # User notifications
│   │   │   │   ├── engagement.py # Feedback, bookmarks, progress
│   │   │   │   ├── search.py     # Search & saved searches
│   │   │   │   ├── users.py      # User management
│   │   │   │   └── tenants.py    # Tenant management
│   │   │   ├── viewer/           # Public viewer routes
│   │   │   │   └── documents.py  # Published documents
│   │   │   └── health.py         # Health checks
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── document_service.py
│   │   │   ├── email_service.py
│   │   │   ├── storage_service.py
│   │   │   └── ...
│   │   ├── dependencies/         # FastAPI dependencies
│   │   ├── middleware/           # CORS, logging, tenant context
│   │   ├── db.py                 # Database configuration
│   │   └── main.py               # Application entrypoint
│   ├── tests/                    # Pytest test suite
│   ├── data/                     # SQLite database files
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   │   ├── Layout.tsx        # Main layout with sidebar
│   │   │   ├── Header.tsx        # Top navigation
│   │   │   ├── Sidebar.tsx       # Side navigation
│   │   │   ├── NotificationBell.tsx # Real-time notifications
│   │   │   ├── DocumentEditor.tsx# Rich text editor
│   │   │   ├── RichTextEditor.tsx# TipTap wrapper
│   │   │   ├── CommentsSection.tsx
│   │   │   ├── VersionsSection.tsx
│   │   │   ├── AttachmentsSection.tsx
│   │   │   └── EngagementBar.tsx
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── DocumentDetailPage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   └── viewer/           # Public viewer pages
│   │   ├── lib/
│   │   │   ├── api.ts            # API client
│   │   │   └── auth.ts           # Auth context
│   │   └── types/                # TypeScript definitions
│   ├── tests/                    # Vitest + Playwright tests
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/                         # Documentation
├── docker-compose.yml            # Production deployment
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)

### Option 1: Local Development

**Backend:**
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

### Option 2: Docker Compose

```bash
docker compose up -d
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001

---

## 🔑 Default Users

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| sysadmin | sysadmin123 | System Admin | Full system access, manage all admins |
| admin | admin123 | Admin | Manage users, companies, settings |
| manager | manager123 | Manager | Publish, delete, approve reviews |
| editor | editor123 | Editor | Create, edit documents, comments |
| viewer | viewer123 | Viewer | Read-only internal access |
| customer1 | customer123 | Customer | Customer portal access (Company A) |
| customer2 | customer123 | Customer | Customer portal access (Company B) |

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
FRONTEND_URL=http://localhost:5173
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
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login and get tokens |
| POST | `/api/auth/logout` | Logout current session |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/password-reset/request` | Request password reset |
| POST | `/api/auth/password-reset/reset` | Reset password with token |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents` | List documents |
| POST | `/api/documents` | Create document |
| GET | `/api/documents/{id}` | Get document |
| PUT | `/api/documents/{id}` | Update document |
| DELETE | `/api/documents/{id}` | Delete document |
| POST | `/api/documents/upload` | Upload PDF/Word file |

### Versions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/{id}/versions` | List versions |
| POST | `/api/documents/{id}/versions` | Create version |
| POST | `/api/versions/{id}/publish` | Publish version |

### Comments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/{id}/comments` | List comments |
| POST | `/api/documents/{id}/comments` | Add comment |
| PUT | `/api/comments/{id}` | Update comment |
| DELETE | `/api/comments/{id}` | Delete comment |
| PUT | `/api/comments/{id}/resolve` | Resolve thread |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications` | List notifications |
| GET | `/api/notifications/unread-count` | Get unread count |
| POST | `/api/notifications/mark-read` | Mark as read |
| DELETE | `/api/notifications` | Delete notifications |

### Full API documentation available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

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

### Planned 🔜
- [x] Customer Portal (company-based document access, feedback)
- [ ] Real-time collaboration (WebSocket, presence indicators)
- [ ] Document templates
- [ ] Workflow approvals
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] AI-powered search and summaries

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
