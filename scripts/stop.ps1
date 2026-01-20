# Stop development environment for Windows PowerShell

Write-Host "🛑 Stopping V2 Document Portal..." -ForegroundColor Yellow

Set-Location (Split-Path -Parent $PSScriptRoot)

docker-compose down

Write-Host "✅ All containers stopped." -ForegroundColor Green
