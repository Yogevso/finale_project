#!/bin/bash
set -e

echo "🚀 Starting Documentation Platform Backend..."

# Initialize database schema (create tables if they don't exist)
echo "📦 Initializing database schema..."
python -c "from app.db import init_db; init_db()"

# Run database migrations
echo "📦 Running database migrations..."
python -m alembic upgrade head

# Check if seed data is needed (no users exist)
echo "🔍 Checking if seed data is needed..."
NEED_SEED=$(python -c "
from app.db import SessionLocal
from app.models import User
db = SessionLocal()
count = db.query(User).count()
db.close()
print('yes' if count == 0 else 'no')
")

if [ "$NEED_SEED" = "yes" ]; then
    echo "🌱 Running seed data script..."
    python seed_data.py
else
    echo "✅ Seed data already exists, skipping..."
fi

# Start the application
echo "🎯 Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
