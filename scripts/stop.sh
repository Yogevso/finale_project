#!/bin/bash
# Stop development environment

set -e

echo "🛑 Stopping Documentation Platform..."

cd "$(dirname "$0")/.."

docker-compose down

echo "✅ All containers stopped."
