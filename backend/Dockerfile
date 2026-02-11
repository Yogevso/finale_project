FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for health check
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

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
