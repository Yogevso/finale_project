# Document Portal V2

[![Tests](https://github.com/Yogevso/project_end/actions/workflows/test.yml/badge.svg)](https://github.com/Yogevso/project_end/actions/workflows/test.yml)

A greenfield rebuild of the Document Management System with SQLite, FastAPI, and React.

## Architecture

- **Backend**: FastAPI 0.109+ + SQLAlchemy 2.0 + SQLite
- **Frontend**: React 18 + TypeScript 5 + Vite 5 + TailwindCSS 3
- **Storage**: S3-compatible (AWS S3/MinIO/Azure Blob)
- **Email**: aiosmtplib (SMTP)
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Docker Deployment
```bash
docker-compose up -d
```

## Features

### Management Portal
- User authentication & authorization
- Document CRUD operations
- Version control
- File attachments (S3)
- Email notifications
- Audit logging

### Viewer Portal
- Public document access
- Search & filtering
- Document versioning
- Download tracking

## Project Structure

```
v2/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── utils/         # Helpers
│   ├── tests/             # Test suite
│   └── data/              # SQLite database
├── frontend/
│   └── src/
│       ├── components/    # React components
│       ├── pages/         # Page components
│       ├── lib/           # Utilities
│       └── types/         # TypeScript types
└── docs/                  # Documentation
```

## Documentation

See the [docs/](docs/) directory for detailed documentation:
- [API Contracts](docs/api-contracts.md)
- [Database Schema](docs/database-schema.md)
- [Deployment Guide](docs/deployment.md)
- [Testing Guide](docs/testing.md)

## License

MIT License - See [LICENSE](LICENSE) for details
