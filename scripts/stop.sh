#!/bin/bash
# Stop development environment

set -e

echo "🛑 Stopping V2 Document Portal..."

cd "$(dirname "$0")/.."

docker-compose down

echo "✅ All containers stopped."
