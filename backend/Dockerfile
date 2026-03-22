FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for health check and PDF/OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies in multiple stages to avoid segfaults
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir uvicorn[standard] fastapi && \
    pip install --no-cache-dir sqlalchemy alembic && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Create data directory
RUN mkdir -p /app/data /app/data/chromadb /app/data/uploads

# Create non-root user and give ownership of app directory
RUN useradd -r -u 1000 -s /bin/false appuser && chown -R appuser:appuser /app

# Install gosu for stepping down from root after fixing volume permissions
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Expose port
EXPOSE 8000

# Health check (start-period allows time for migrations + seeding)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Run entrypoint (migrations + seed + uvicorn)
ENTRYPOINT ["/app/docker-entrypoint.sh"]
