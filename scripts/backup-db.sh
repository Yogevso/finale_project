#!/bin/bash
# Backup SQLite database

set -e

BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="backend/data/portal.db"

cd "$(dirname "$0")/.."

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

if [ -f "$DB_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/portal_${TIMESTAMP}.db"
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "✅ Database backed up to: $BACKUP_FILE"
    
    # Keep only last 10 backups
    ls -t $BACKUP_DIR/portal_*.db | tail -n +11 | xargs -r rm
    echo "📦 Keeping last 10 backups only."
else
    echo "❌ Database file not found: $DB_FILE"
    exit 1
fi
