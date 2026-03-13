$ErrorActionPreference = 'Stop'

if (-not (Test-Path 'temp')) {
  New-Item -ItemType Directory -Path 'temp' | Out-Null
}

$env:APP_ENV = 'testing'
$env:SECRET_KEY = 'test-secret-key'
$env:PYTHONUTF8 = '1'
$env:DATABASE_URL = 'sqlite:///./temp/playwright-e2e.db'

Remove-Item 'temp/playwright-e2e.db' -ErrorAction SilentlyContinue -Force

$pythonCandidates = @()
$preferredPython = Join-Path '..' '.venv\Scripts\python.exe'
if (Test-Path $preferredPython) {
  $pythonCandidates += (Resolve-Path $preferredPython).Path
}
if (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCandidates += (Get-Command python).Source
}
& where.exe python 2>$null | ForEach-Object {
  if ($_ -and (Test-Path $_)) {
    $pythonCandidates += $_
  }
}
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCandidates += (Get-Command py).Source
}

$pythonCommand = $null
foreach ($candidate in ($pythonCandidates | Select-Object -Unique)) {
  & cmd.exe /d /c "`"$candidate`" -c `"import sqlalchemy`" >nul 2>nul"
  if ($LASTEXITCODE -eq 0) {
    $pythonCommand = $candidate
    break
  }
}

if (-not $pythonCommand) {
  throw 'Unable to find a Python executable with backend dependencies for E2E backend startup.'
}

Write-Host "Using E2E database: $($env:DATABASE_URL)"
Write-Host "Using Python command: $pythonCommand"

& $pythonCommand -c "from app.db import init_db; init_db()"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& $pythonCommand seed_data.py
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& $pythonCommand -c "from app.db import SessionLocal; from app.services.search_index_service import SearchIndexSyncService; db = SessionLocal(); SearchIndexSyncService(db).rebuild_index(); db.commit(); db.close()"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& $pythonCommand -m uvicorn app.main:app --host 127.0.0.1 --port 8010
exit $LASTEXITCODE
