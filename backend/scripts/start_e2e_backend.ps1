$ErrorActionPreference = 'Stop'

if (-not (Test-Path 'temp')) {
  New-Item -ItemType Directory -Path 'temp' | Out-Null
}

$env:APP_ENV = 'testing'
$env:SECRET_KEY = 'test-secret-key'
$env:PYTHONUTF8 = '1'
$env:DATABASE_URL = 'sqlite:///./temp/playwright-e2e.db'

Remove-Item 'temp/playwright-e2e.db' -ErrorAction SilentlyContinue -Force

Write-Host "Using E2E database: $($env:DATABASE_URL)"

python -m alembic upgrade heads
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

python seed_data.py
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
exit $LASTEXITCODE

