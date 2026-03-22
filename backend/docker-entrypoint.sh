#!/bin/bash
set -e

echo "Starting Documentation Platform Backend..."

# Fix volume permissions (runs as root, then drops to appuser)
if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /app/data
    exec gosu appuser "$0" "$@"
fi

# Ensure data directory exists
mkdir -p /app/data /app/data/chromadb /app/data/uploads

# Run database migrations
echo "Running database migrations..."
if python -m alembic upgrade head; then
    echo "Migrations completed successfully."
else
    echo "Migrations failed, attempting schema bootstrap..."
    python -c "from app.db import init_db; init_db()"
    echo "Schema bootstrap completed."
fi

# Check if seed data is needed (no users exist)
echo "Checking if seed data is needed..."
NEED_SEED=$(python -c "
from app.db import SessionLocal
from app.models import User
db = SessionLocal()
try:
    count = db.query(User).count()
    print('yes' if count == 0 else 'no')
finally:
    db.close()
" 2>/dev/null || echo "yes")

if [ "$NEED_SEED" = "yes" ]; then
    echo "Running seed data script..."
    python seed_data.py || echo "Seed data script failed (non-fatal), continuing..."
else
    echo "Seed data already exists, skipping."
fi

# Start the application
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
