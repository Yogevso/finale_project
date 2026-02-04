# Development environment startup script for Windows PowerShell

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Documentation Platform development environment..." -ForegroundColor Green

# Navigate to v2 directory
Set-Location (Split-Path -Parent $PSScriptRoot)

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker and try again." -ForegroundColor Red
    exit 1
}

# Build and start containers
Write-Host "📦 Building containers..." -ForegroundColor Yellow
docker-compose build

Write-Host "🐳 Starting containers..." -ForegroundColor Yellow
docker-compose up -d

# Wait for backend to be healthy
Write-Host "⏳ Waiting for backend to be ready..." -ForegroundColor Yellow
$timeout = 60
$counter = 0
do {
    Start-Sleep -Seconds 1
    $counter++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { break }
    } catch {}
} while ($counter -lt $timeout)

if ($counter -ge $timeout) {
    Write-Host "❌ Backend failed to start within $timeout seconds" -ForegroundColor Red
    docker-compose logs backend
    exit 1
}

Write-Host ""
Write-Host "✅ Development environment is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 URLs:" -ForegroundColor Cyan
Write-Host "   Frontend:  http://localhost:3000"
Write-Host "   Backend:   http://localhost:8000"
Write-Host "   API Docs:  http://localhost:8000/api/v1/docs"
Write-Host ""
Write-Host "👤 Test Users:" -ForegroundColor Cyan
Write-Host "   admin / admin123"
Write-Host "   editor / editor123"
Write-Host "   viewer / viewer123"
Write-Host ""
Write-Host "📋 Commands:" -ForegroundColor Cyan
Write-Host "   Stop:      .\scripts\stop.ps1"
Write-Host "   Logs:      docker-compose logs -f"
Write-Host "   Backend:   docker-compose logs -f backend"
Write-Host "   Frontend:  docker-compose logs -f frontend"
