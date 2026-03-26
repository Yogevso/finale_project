# Quick Start Script for Backend

Write-Host "🚀 Setting up Documentation Platform Backend..." -ForegroundColor Cyan

# Navigate to backend directory
Set-Location $PSScriptRoot

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements-dev.txt

# Create .env file if it doesn't exist
if (!(Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Yellow
python init_db.py

# Run tests
Write-Host "Running tests..." -ForegroundColor Yellow
pytest -v

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server, run:" -ForegroundColor Cyan
Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Default credentials:" -ForegroundColor Cyan
Write-Host "  Admin: admin / admin123" -ForegroundColor White
Write-Host "  Editor: editor / editor123" -ForegroundColor White
Write-Host "  Viewer: viewer / viewer123" -ForegroundColor White
Write-Host ""
