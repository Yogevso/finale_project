# Document Portal V2 - Backend

FastAPI backend with SQLAlchemy 2.0 and SQLite.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Create `.env` file:
```env
# Application
APP_ENV=development
SECRET_KEY=your-secret-key-here
API_PREFIX=/api/v1

# Database
DATABASE_URL=sqlite:///./data/portal.db

# Security
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# Storage (S3)
S3_ENABLED=false
S3_BUCKET=document-portal
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Email (SMTP)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@portal.com
```

## Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

## Database Initialization

```bash
python -m app.db.init_db
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy app/
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── db.py                # Database session
│   ├── security.py          # Auth utilities
│   ├── api/
│   │   ├── management/      # Management portal routes
│   │   └── viewer/          # Viewer portal routes
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── utils/               # Helpers
├── tests/                   # Test suite
├── data/                    # SQLite database (gitignored)
└── requirements.txt
```
