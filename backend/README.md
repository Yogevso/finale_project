# Document Portal V2 - Backend

FastAPI backend with SQLAlchemy 2.0, SQLite, and comprehensive document management features.

---

## 🚀 Features

### Authentication & Authorization
- JWT-based authentication with access/refresh tokens
- Role-based access control (Super Admin, Admin, Editor, Viewer)
- Password reset with email verification
- Secure password hashing with bcrypt

### Multi-Tenancy
- Complete tenant isolation
- Super Admin can manage all tenants
- Tenant-scoped queries for all resources

### Document Management
- Full CRUD operations
- Rich text content with HTML support
- Document status workflow (Draft → Active → Archived)
- Category and tag management
- Bulk PDF/Word upload with content extraction

### Version Control
- Immutable version history
- Publish specific versions
- Change summaries and tracking
- Version comparison support

### File Attachments
- S3-compatible storage (AWS S3, MinIO, local filesystem)
- Secure pre-signed download URLs
- File size limits and type validation
- Automatic cleanup on document deletion

### Comments & Collaboration
- Threaded comments with replies
- Private comments (admin/editor only)
- Inline comments anchored to text
- Comment resolution workflow

### Notifications
- In-app notifications with read/unread status
- Email notifications (document published, comments, replies)
- Configurable notification preferences

### Engagement & Analytics
- Document view tracking
- Reading progress indicators
- Helpful/Not helpful feedback
- User bookmarks
- Saved searches

### Search
- Full-text search across documents
- Filter by category, status, date range
- Saved search management

---

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.109+ |
| Python | 3.11+ |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Validation | Pydantic 2.0 |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Email | aiosmtplib |
| Storage | boto3 (S3-compatible) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |

---

## 🛠️ Setup

### Prerequisites
- Python 3.11+
- pip or pipenv

### Installation

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file in the backend directory:

```env
# ===================
# Application
# ===================
APP_ENV=development
DEBUG=true

# ===================
# Security
# ===================
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256

# ===================
# Database
# ===================
DATABASE_URL=sqlite:///./data/document_portal.db

# ===================
# Storage (S3-compatible)
# ===================
STORAGE_BACKEND=local              # Options: local, s3
LOCAL_STORAGE_PATH=./data/uploads

# For S3/MinIO:
S3_BUCKET_NAME=document-portal
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=http://localhost:9000  # MinIO
S3_REGION=us-east-1

# ===================
# Email (SMTP)
# ===================
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourcompany.com
EMAIL_FROM_NAME=Document Portal

# ===================
# Frontend URL (for email links)
# ===================
FRONTEND_URL=http://localhost:5173
```

---

## 🏃 Running

### Development Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Access Points
- API: http://localhost:8001
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- Health Check: http://localhost:8001/health

---

## 🗃️ Database

### Initialize Database

The database is automatically created on first run. To reset:

```bash
# Delete existing database
rm -f data/document_portal.db

# Restart server to recreate
uvicorn app.main:app --reload
```

### Seed Sample Data

```bash
python seed_sample_data.py
```

### Default Users

| Email | Password | Role |
|-------|----------|------|
| super@example.com | password | Super Admin |
| admin@example.com | password | Admin |
| editor@example.com | password | Editor |
| viewer@example.com | password | Viewer |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage report
pytest --cov=app --cov-report=html

# Run only unit tests (skip integration)
pytest -m "not integration"
```

---

## 🔍 Code Quality

```bash
# Lint code
ruff check app/

# Auto-fix lint issues
ruff check app/ --fix

# Format code
ruff format app/

# Type checking (optional)
mypy app/ --ignore-missing-imports
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Settings & environment variables
│   ├── db.py                   # Database session & engine
│   ├── security.py             # Password hashing & JWT utilities
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoints
│   │   │
│   │   ├── management/         # Admin/Editor API routes
│   │   │   ├── auth.py         # Login, logout, password reset
│   │   │   ├── documents.py    # Document CRUD
│   │   │   ├── versions.py     # Version management
│   │   │   ├── attachments.py  # File upload/download
│   │   │   ├── comments.py     # Comments & threads
│   │   │   ├── notifications.py# User notifications
│   │   │   ├── engagement.py   # Feedback, bookmarks, progress
│   │   │   ├── search.py       # Search & saved searches
│   │   │   ├── users.py        # User management
│   │   │   └── tenants.py      # Tenant management
│   │   │
│   │   └── viewer/             # Public viewer routes
│   │       └── documents.py    # Published document access
│   │
│   ├── models/
│   │   └── __init__.py         # SQLAlchemy ORM models
│   │                           # - Tenant, User, Document
│   │                           # - Version, Section, Attachment
│   │                           # - Comment, AuditLog, Notification
│   │                           # - SavedSearch, Bookmark, Feedback
│   │                           # - ReadingProgress, PasswordReset
│   │
│   ├── schemas/
│   │   └── __init__.py         # Pydantic request/response schemas
│   │
│   ├── services/               # Business logic layer
│   │   ├── auth_service.py     # Authentication logic
│   │   ├── document_service.py # Document operations
│   │   ├── comment_service.py  # Comment operations
│   │   ├── attachment_service.py# File handling
│   │   ├── storage_service.py  # S3/local storage abstraction
│   │   ├── email_service.py    # Email sending with templates
│   │   └── base_service.py     # Base service with tenant isolation
│   │
│   ├── dependencies/           # FastAPI dependencies
│   │   ├── auth.py             # get_current_user, require_role
│   │   └── tenant.py           # get_tenant_context
│   │
│   ├── middleware/             # Custom middleware
│   │   └── __init__.py         # CORS, logging, tenant context
│   │
│   └── utils/                  # Helper utilities
│       └── __init__.py
│
├── tests/                      # Pytest test suite
│   ├── conftest.py             # Test fixtures
│   ├── test_auth.py
│   ├── test_documents.py
│   └── ...
│
├── data/                       # SQLite database & uploads
│   ├── document_portal.db      # Database file (gitignored)
│   └── uploads/                # Local file storage
│
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image definition
├── pytest.ini                  # Pytest configuration
└── README.md
```

---

## 📋 API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Login with email/password |
| POST | `/logout` | Logout current session |
| POST | `/refresh` | Refresh access token |
| GET | `/me` | Get current user profile |
| POST | `/password-reset/request` | Request password reset email |
| POST | `/password-reset/reset` | Reset password with token |

### Documents (`/api/documents`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List documents (paginated) |
| POST | `/` | Create new document |
| GET | `/{id}` | Get document by ID |
| PUT | `/{id}` | Update document |
| DELETE | `/{id}` | Delete document |
| POST | `/upload` | Upload PDF/Word file |

### Versions (`/api/documents/{id}/versions`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List document versions |
| POST | `/` | Create new version |
| GET | `/{version_id}` | Get specific version |
| POST | `/{version_id}/publish` | Publish version |

### Attachments (`/api/documents/{id}/attachments`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List attachments |
| POST | `/` | Upload attachment |
| GET | `/{attachment_id}/download` | Download file |
| DELETE | `/{attachment_id}` | Delete attachment |

### Comments (`/api/documents/{id}/comments`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List comments (threaded) |
| POST | `/` | Add comment |
| PUT | `/{comment_id}` | Update comment |
| DELETE | `/{comment_id}` | Delete comment |
| PUT | `/{comment_id}/resolve` | Resolve thread |

### Notifications (`/api/notifications`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List user notifications |
| GET | `/unread-count` | Get unread count |
| POST | `/mark-read` | Mark as read |
| DELETE | `/` | Delete notifications |

### Engagement (`/api/engagement`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/{id}/bookmark` | Toggle bookmark |
| POST | `/documents/{id}/feedback` | Submit feedback |
| PUT | `/documents/{id}/progress` | Update reading progress |
| GET | `/documents/{id}/stats` | Get engagement stats |

### Search (`/api/search`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Search documents |
| GET | `/saved` | List saved searches |
| POST | `/saved` | Save a search |
| DELETE | `/saved/{id}` | Delete saved search |

### Users (`/api/users`) - Admin only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List users |
| POST | `/` | Create user |
| GET | `/{id}` | Get user |
| PUT | `/{id}` | Update user |
| DELETE | `/{id}` | Delete user |

### Tenants (`/api/tenants`) - Super Admin only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List tenants |
| POST | `/` | Create tenant |
| GET | `/{id}` | Get tenant |
| PUT | `/{id}` | Update tenant |
| DELETE | `/{id}` | Delete tenant |

### Viewer Portal (`/api/viewer`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/documents` | List published documents |
| GET | `/documents/{id}` | Get published document |
| GET | `/documents/{id}/versions` | List published versions |

### Health (`/health`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Basic health check |
| GET | `/detailed` | Detailed health (DB, storage) |

---

## 🐳 Docker

### Build Image

```bash
docker build -t document-portal-backend:latest .
```

### Run Container

```bash
docker run -p 8001:8001 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=sqlite:///./data/portal.db \
  -v $(pwd)/data:/app/data \
  document-portal-backend:latest
```

---

## 📝 License

MIT License - See [LICENSE](../LICENSE) for details.
