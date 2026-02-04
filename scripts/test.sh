#!/bin/bash
# Run all tests

set -e

echo "🧪 Running Documentation Platform tests..."

cd "$(dirname "$0")/.."

# Backend tests
echo ""
echo "📦 Running backend tests..."
cd backend
python -m pytest tests/ -v --tb=short

# Frontend tests
echo ""
echo "🎨 Running frontend tests..."
cd ../frontend
npm test -- --run

echo ""
echo "✅ All tests passed!"
