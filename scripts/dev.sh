#!/bin/bash
# Development environment startup script

set -e

echo "🚀 Starting Documentation Platform development environment..."

# Navigate to v2 directory
cd "$(dirname "$0")/.."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start containers
echo "📦 Building containers..."
docker-compose build

echo "🐳 Starting containers..."
docker-compose up -d

# Wait for backend to be healthy
echo "⏳ Waiting for backend to be ready..."
timeout=60
counter=0
until curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; do
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo "❌ Backend failed to start within ${timeout} seconds"
        docker-compose logs backend
        exit 1
    fi
    sleep 1
done

echo ""
echo "✅ Development environment is ready!"
echo ""
echo "📍 URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/api/v1/docs"
echo ""
echo "👤 Test Users:"
echo "   admin / admin123"
echo "   editor / editor123"
echo "   viewer / viewer123"
echo ""
echo "📋 Commands:"
echo "   Stop:      ./scripts/stop.sh"
echo "   Logs:      docker-compose logs -f"
echo "   Backend:   docker-compose logs -f backend"
echo "   Frontend:  docker-compose logs -f frontend"
