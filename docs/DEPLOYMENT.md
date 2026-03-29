# Deployment Guide

This document covers the deployment requirements, environment configuration, and
operational procedures for the Documentation Platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Required Secrets](#required-secrets)
3. [Environment Variables](#environment-variables)
4. [Docker Deployment](#docker-deployment)
5. [Database Migrations](#database-migrations)
6. [Health Checks](#health-checks)
7. [Monitoring](#monitoring)

---

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** v2.x
- **PostgreSQL** 14+ (for production) or SQLite (development only)
- **Redis** (required for the default production rate-limit path; also used for collaboration coordination)
- **S3-compatible storage** (for production file storage)
- **SMTP server** (for email notifications)

---

## Required Secrets

The following secrets must be configured before deployment. **Never commit these to version control.**

### Critical Secrets (Required)

| Secret | Environment Variable | Description | Generation Instructions |
|--------|---------------------|-------------|------------------------|
| **JWT Secret Key** | `SECRET_KEY` | Signs JWT tokens for authentication | `openssl rand -hex 32` or `python -c "import secrets; print(secrets.token_hex(32))"` |
| **Database URL** | `DATABASE_URL` | PostgreSQL connection string | Format: `postgresql://user:password@host:5432/dbname` |

### Recommended Secrets (Production)

| Secret | Environment Variable | Description | Generation Instructions |
|--------|---------------------|-------------|------------------------|
| **Audit HMAC Keys** | `AUDIENCE_AUDIT_HMAC_KEYS` | Signs audience audit logs | `python -c "import secrets; print(f'v1:{secrets.token_hex(32)}')"` |
| **S3 Access Key** | `S3_ACCESS_KEY` | AWS/S3 access key ID | Obtain from AWS IAM console |
| **S3 Secret Key** | `S3_SECRET_KEY` | AWS/S3 secret access key | Obtain from AWS IAM console |
| **SMTP Password** | `SMTP_PASSWORD` | Email server password | Obtain from email provider |

### Secret Generation Commands

```bash
# Generate a secure 64-character random secret key
openssl rand -hex 32

# Alternative using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Generate password hash for initial admin user
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('your-password'))"

# Generate HMAC signing key for audit logs
python -c "import secrets; print(f'v1:{secrets.token_hex(32)}')"
```

### Storing Secrets

**Docker Secrets (Recommended for Docker Swarm)**:
```bash
echo "your-secret-value" | docker secret create secret_key -
```

**Kubernetes Secrets**:
```bash
kubectl create secret generic app-secrets \
  --from-literal=SECRET_KEY=your-secret-value \
  --from-literal=DATABASE_URL=postgresql://...
```

**Environment Files** (Development only):
```bash
# Create .env file (never commit this!)
cp .env.example .env
# Edit .env with your secrets
```

---

## Environment Variables

### Application Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_ENV` | `development` | No | Environment mode: `development`, `staging`, `production` |
| `APP_NAME` | `Documentation Platform` | No | Application display name |
| `DEBUG` | `True` | No | Enable debug mode (disable in production) |
| `BASE_URL` | `http://localhost:3000` | Yes | Frontend URL for CORS and links |

### Security Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | *(insecure default)* | **Yes** | JWT signing key (32+ chars) |
| `SECRET_KEY_OLD` | *(none)* | No | Optional previous signing key accepted temporarily during coordinated rotation |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No | JWT token expiration |
| `CSRF_PROTECTION_ENABLED` | `True` | No | Enable CSRF protection |
| `TRUST_PROXY_HEADERS` | `False` | No | Trust X-Forwarded-* headers |
| `TRUSTED_PROXY_IPS` | `[]` | No | List of trusted proxy IPs |

### Database Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./data/portal.db` | **Yes (prod)** | Core database connection URL |
| `ANALYTICS_DATABASE_URL` | *(falls back to `DATABASE_URL`)* | No | Analytics database (audit logs, security events, NPS) |
| `CHAT_DATABASE_URL` | *(falls back to `DATABASE_URL`)* | No | Chat database (notifications, assistant, collaboration) |
| `SQL_ECHO` | `False` | No | Log SQL queries (debug only) |

### Storage Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `S3_ENABLED` | `False` | Yes (prod) | Enable S3 storage |
| `S3_BUCKET` | `document-portal` | Conditional | S3 bucket name |
| `S3_ENDPOINT_URL` | *(none)* | Conditional | S3-compatible endpoint |
| `S3_ACCESS_KEY` | *(none)* | Conditional | S3 access key |
| `S3_SECRET_KEY` | *(none)* | Conditional | S3 secret key |
| `S3_REGION` | `us-east-1` | No | AWS region |
| `MAX_UPLOAD_SIZE` | `52428800` | No | Max file upload size (bytes). Current production tier allows uploads up to 50MB before additional worker/infra scaling concerns apply. |

### Email Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `EMAIL_ENABLED` | `False` | No | Enable email notifications |
| `SMTP_HOST` | *(none)* | Conditional | SMTP server hostname |
| `SMTP_PORT` | `587` | No | SMTP server port |
| `SMTP_USER` | *(none)* | Conditional | SMTP username |
| `SMTP_PASSWORD` | *(none)* | Conditional | SMTP password |
| `EMAIL_FROM` | `noreply@portal.com` | No | Sender email address |

### Rate Limiting

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `RATE_LIMIT_ENABLED` | `True` | No | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | No | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | No | Window size (seconds) |
| `REDIS_URL` | `redis://redis:6379/0` | **Yes when `RATE_LIMIT_ENABLED=True` in production** | Redis backend for rate limiting |

### Search Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SEARCH_BACKEND_MODE` | `auto` | **Yes (prod)** | Explicit search path: `sqlite_fts5`, `postgres_tsv`, or `portable_like` |

### Assistant Capacity Settings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ASSISTANT_CHAT_MAX_CONCURRENT` | `4` | No | Max concurrent assistant chat requests per backend instance |
| `ASSISTANT_CHAT_MAX_QUEUE` | `8` | No | Max queued assistant chat requests before rejection |
| `ASSISTANT_CHAT_QUEUE_TIMEOUT_SECONDS` | `15` | No | Max time a chat request may wait for capacity |
| `ASSISTANT_EMBEDDING_MAX_CONCURRENT` | `4` | No | Max concurrent assistant embedding jobs per backend instance |
| `ASSISTANT_EMBEDDING_MAX_QUEUE` | `16` | No | Max queued assistant embedding jobs before rejection |
| `ASSISTANT_EMBEDDING_QUEUE_TIMEOUT_SECONDS` | `10` | No | Max time an embedding job may wait for capacity |

### Collaboration Runtime Guardrails

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `COLLAB_MAX_TOTAL_CONNECTIONS` | `200` | No | Max concurrent websocket connections per collab-server instance |
| `COLLAB_MAX_CONNECTIONS_PER_DOCUMENT` | `25` | No | Max concurrent connections to one document per collab-server instance |
| `COLLAB_RECONNECT_WINDOW_SECONDS` | `60` | No | Window used to count rapid reconnect churn in collab runtime metrics |

---

## Docker Deployment

### Production Deployment

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

Notes:

- `docker-compose.prod.yml` now expects the frontend container to listen on `127.0.0.1:8080`.
- TLS should terminate at an upstream reverse proxy or load balancer, not inside the unprivileged frontend container.
- The release workflow can override `BACKEND_IMAGE`, `FRONTEND_IMAGE`, and `COLLAB_SERVER_IMAGE` to deploy prebuilt images from GHCR.
- Docker base images and third-party runtime images are digest pinned; refresh digests intentionally and review the security workflow pins in `.github/workflows/security.yml` when updating them.

### Supply-Chain Pin Refresh

When refreshing release-path base images or external runtime images:

1. Pull the exact tagged image and record its digest.
2. Update the pinned `FROM ...@sha256:...` or compose `image: ...@sha256:...` reference.
3. Run `docker compose -f docker-compose.prod.yml config` and the infrastructure regression tests.
4. If a GitHub Action pin also needs refresh, resolve the official repo ref to a commit SHA and update the workflow to that immutable SHA, not a moving tag or branch.

### Environment File Setup

Create a `.env.prod` file with production settings:

```env
# Required
SECRET_KEY=your-64-char-secret-key-here
SECRET_KEY_OLD=
DATABASE_URL=postgresql://portal:password@db:5432/portal
ANALYTICS_DATABASE_URL=postgresql://portal:password@db:5432/portal_analytics
CHAT_DATABASE_URL=postgresql://portal:password@db:5432/portal_chat
REDIS_URL=redis://redis:6379/0
SEARCH_BACKEND_MODE=postgres_tsv
ASSISTANT_CHAT_MAX_CONCURRENT=4
ASSISTANT_CHAT_MAX_QUEUE=8
ASSISTANT_CHAT_QUEUE_TIMEOUT_SECONDS=15
ASSISTANT_EMBEDDING_MAX_CONCURRENT=4
ASSISTANT_EMBEDDING_MAX_QUEUE=16
ASSISTANT_EMBEDDING_QUEUE_TIMEOUT_SECONDS=10
COLLAB_MAX_TOTAL_CONNECTIONS=200
COLLAB_MAX_CONNECTIONS_PER_DOCUMENT=25
COLLAB_RECONNECT_WINDOW_SECONDS=60
APP_ENV=production
DEBUG=False
SEED_DEMO_DATA=false
VITE_COLLAB_SERVER_URL=wss://collab.portal.example.com

# Storage
S3_ENABLED=True
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=AKIAXXXXXXXXXXXXXXXX
S3_SECRET_KEY=your-secret-key

# Email
EMAIL_ENABLED=True
SMTP_HOST=smtp.example.com
SMTP_USER=notifications@example.com
SMTP_PASSWORD=smtp-password
```

---

## Database Migrations

The platform uses 3 independent database migration chains via Alembic named sections.

### Running Migrations

```bash
# Inside backend container — all 3 databases
docker-compose exec backend alembic upgrade head                # Core
docker-compose exec backend alembic -n analytics upgrade head   # Analytics
docker-compose exec backend alembic -n chat upgrade head        # Chat

# Check current revision per database
docker-compose exec backend alembic current
docker-compose exec backend alembic -n analytics current
docker-compose exec backend alembic -n chat current

# Create new migration (specify target with -n)
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic -n analytics revision --autogenerate -m "description"
```

> **Note:** The Docker entrypoint automatically runs `alembic upgrade head` for all 3 databases on container startup.

### Data Migration (Single DB → 3 DBs)

To split an existing single-database deployment into 3 separate databases:

```bash
# 1. Dry run — preview what will be copied (default, no data written)
python scripts/split_databases.py

# 2. Execute — copy analytics/chat rows to their new databases
python scripts/split_databases.py --execute

# 3. Cleanup — delete migrated rows from the source (after verification)
python scripts/split_databases.py --execute --cleanup
```

The migration script is idempotent — running it multiple times skips already-migrated rows.

### Backup Before Migration

```bash
# PostgreSQL-first drill (recommended production path)
python -m scripts.backup_restore_drill --database-url "$DATABASE_URL" --backup-only
python -m scripts.backup_restore_drill --database-url "$DATABASE_URL"

# SQLite/local fallback drill
python -m scripts.backup_restore_drill --db-path data/portal.db --backup-only
python -m scripts.backup_restore_drill --db-path data/portal.db
```

### Disaster Recovery Validation

```bash
python -m scripts.disaster_recovery_validation --database-url "$DATABASE_URL"
```

### Secret Rotation

```bash
python -m scripts.rotate_secrets --type jwt
```

JWT rotation now supports a coordinated 24-hour grace period:

```bash
SECRET_KEY=<new key>
SECRET_KEY_OLD=<previous key>
```

Apply the same pair to both backend and collab-server during the grace window.

---

## Health Checks

### Backend Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0"
}
```

### Docker Health Check

```bash
docker-compose ps
# Check HEALTH column for status
```

---

## Monitoring

### Recommended Monitoring Setup

1. **Application Metrics**: Prometheus + Grafana
2. **Log Aggregation**: ELK Stack or Loki
3. **Error Tracking**: Sentry
4. **Uptime Monitoring**: Pingdom or UptimeRobot

### Log Locations

- Backend logs: `/var/log/portal/backend.log` or stdout in Docker
- Nginx logs: `/var/log/nginx/access.log` and `error.log`
- Database logs: PostgreSQL log directory

### Key Metrics to Monitor

- Request latency (p50, p95, p99)
- Error rate (4xx, 5xx responses)
- Database connection pool usage
- Storage usage and upload rates
- Active user sessions

---

## Security Checklist

Before going to production:

- [ ] `SECRET_KEY` is a unique, randomly generated 32+ character string
- [ ] `DEBUG` is set to `False`
- [ ] `APP_ENV` is set to `production`
- [ ] Database uses PostgreSQL (not SQLite)
- [ ] Analytics and chat databases are configured (separate or same instance)
- [ ] Data migration script has been run if upgrading from single-DB
- [ ] S3 storage is enabled for file uploads
- [ ] HTTPS is configured (via reverse proxy)
- [ ] CORS origins are properly restricted
- [ ] Rate limiting is enabled
- [ ] Container images are scanned for vulnerabilities
- [ ] Secrets are not committed to version control
- [ ] Database backups are configured
- [ ] Log aggregation is set up
- [ ] Error monitoring is configured

---

## Troubleshooting

### Common Issues

**JWT Token Errors**:
- Ensure `SECRET_KEY` is consistent across all backend instances
- Check token expiration settings

**Database Connection Refused**:
- Verify `DATABASE_URL` format
- Check network connectivity between services
- Ensure database container is healthy

**File Upload Failures**:
- Check S3 credentials and permissions
- Verify bucket exists and is accessible
- Check `MAX_UPLOAD_SIZE` setting

**CORS Errors**:
- Update `CORS_ORIGINS` to include frontend URL
- Ensure `BASE_URL` matches frontend domain

For additional help, see the [Development Guide](DEVELOPMENT.md).
