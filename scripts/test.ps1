# Run all tests for Windows PowerShell

$ErrorActionPreference = "Stop"

Write-Host "🧪 Running Documentation Platform tests..." -ForegroundColor Green

Set-Location (Split-Path -Parent $PSScriptRoot)

# Backend tests
Write-Host ""
Write-Host "📦 Running backend tests..." -ForegroundColor Yellow
Set-Location backend
python -m pytest tests/ -v --tb=short

# Frontend tests
Write-Host ""
Write-Host "🎨 Running frontend tests..." -ForegroundColor Yellow
Set-Location ../frontend
npm test -- --run

Write-Host ""
Write-Host "✅ All tests passed!" -ForegroundColor Green
