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

# Run database migrations (core, analytics, chat)
echo "Running database migrations..."
# Core database (default alembic section)
if python -m alembic upgrade head; then
    echo "Core migrations completed successfully."
else
    echo "Core migrations failed, attempting schema bootstrap..."
    python -c "from app.db import init_db; init_db()"
    echo "Schema bootstrap completed."
fi

# Analytics database
if python -m alembic -n analytics upgrade head 2>/dev/null; then
    echo "Analytics migrations completed successfully."
else
    echo "Analytics migrations skipped (no separate DB configured or first run)."
fi

# Chat database
if python -m alembic -n chat upgrade head 2>/dev/null; then
    echo "Chat migrations completed successfully."
else
    echo "Chat migrations skipped (no separate DB configured or first run)."
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

ALLOW_DEMO_SEED=$(python -c "
from seed_data import should_seed_demo_data
print('yes' if should_seed_demo_data() else 'no')
" 2>/dev/null || echo "no")

if [ "$NEED_SEED" = "yes" ] && [ "$ALLOW_DEMO_SEED" = "yes" ]; then
    echo "Running seed data script..."
    python seed_data.py || echo "Seed data script failed (non-fatal), continuing..."
elif [ "$NEED_SEED" = "yes" ]; then
    echo "Skipping demo seed data. Set SEED_DEMO_DATA=true for an explicit one-time opt-in."
else
    echo "Seed data already exists, skipping."
fi

# Start the application
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
