# Development Guide

## Prerequisites

- **Docker & Docker Compose** (recommended for quick start)
- **Python 3.11+** (for local backend development)
- **Node.js 20+** (for local frontend development)

## Quick Start (Docker)

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd v2
   ```

2. Start all services:
   ```bash
   # Linux/Mac
   ./scripts/dev.sh
   
   # Windows PowerShell
   .\scripts\dev.ps1
   ```

3. Access the application:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8001
   - **API Docs (Swagger)**: http://localhost:8001/docs
   - **API Docs (ReDoc)**: http://localhost:8001/redoc

4. Test users:
   | Username | Password | Role |
   |----------|----------|------|
   | admin | admin123 | ADMIN |
   | editor | editor123 | EDITOR |
   | viewer | viewer123 | VIEWER |

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app.db import init_db; init_db()"

# Create test users
python -c "from app.db import create_test_users; create_test_users()"

# Start server
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend will be available at http://localhost:3000 and will proxy API requests to the backend.

## Testing

### Backend Tests
```bash
cd backend
pytest -v                    # Run all tests
pytest -v --cov=app          # Run with coverage
pytest tests/test_auth.py    # Run specific test file
```

### Frontend Tests
```bash
cd frontend
npm test                     # Run all tests
npm run test:coverage        # Run with coverage
npm test -- Button.test.tsx  # Run specific test file
```

### Run All Tests
```bash
# Linux/Mac
./scripts/test.sh

# Windows PowerShell
.\scripts\test.ps1
```

## Database

### Location
- **Development**: `backend/data/portal.db` (SQLite)

### Reset Database
```bash
cd backend
rm -f data/portal.db           # Delete existing database
python -c "from app.db import init_db; init_db()"
python -c "from app.db import create_test_users; create_test_users()"
```

### Backup Database
```bash
# Linux/Mac
./scripts/backup-db.sh

# This creates a timestamped backup in backend/data/backups/
```

### View Database (SQLite CLI)
```bash
cd backend
sqlite3 data/portal.db

# Useful commands:
.tables                        # List all tables
.schema users                  # Show table schema
SELECT * FROM users;           # Query data
.quit                          # Exit
```

## Project Structure

```
v2/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── config.py         # Settings
│   │   ├── db.py             # Database setup
│   │   ├── main.py           # FastAPI app
│   │   └── security.py       # Auth utilities
│   ├── tests/                # Pytest tests
│   ├── data/                 # SQLite database
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── lib/              # Utilities, API client
│   │   ├── stores/           # Zustand stores
│   │   └── types/            # TypeScript types
│   ├── tests/                # Vitest tests
│   └── package.json
├── scripts/                  # Dev/deployment scripts
├── docs/                     # Documentation
└── docker-compose.yml
```

## Environment Variables

### Backend (.env)
```bash
APP_ENV=development           # development | production
SECRET_KEY=your-secret-key    # JWT signing key (required)
DEBUG=true                    # Enable debug mode
DATABASE_URL=sqlite:///./data/portal.db
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8001  # Backend URL (optional, uses proxy)
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 8001 (backend)
# Windows:
netstat -ano | findstr :8001
taskkill /PID <pid> /F

# Linux/Mac:
lsof -i :8001
kill -9 <pid>
```

### Database locked error
SQLite can only handle one write at a time. If you get "database is locked":
1. Stop all running instances of the backend
2. Delete `data/portal.db-wal` and `data/portal.db-shm` if they exist
3. Restart the backend

### CORS errors
Make sure the frontend origin is in `CORS_ORIGINS` in the backend config.

### Login not working
1. Check backend is running: `curl http://localhost:8001/api/v1/health`
2. Verify test users exist in database
3. Check browser console for errors
4. Ensure Vite proxy is configured correctly (should point to `127.0.0.1:8001`)

### Docker containers not starting
```bash
# View logs
docker-compose logs -f

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```
