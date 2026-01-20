# Deploy script for Document Portal V2 (Windows PowerShell)
# Usage: .\deploy.ps1 [build|start|stop|restart|logs|status]

param(
    [Parameter(Position = 0)]
    [ValidateSet("build", "start", "stop", "restart", "logs", "status", "backup", "update", "help")]
    [string]$Command = "help"
)

$ComposeFile = "docker-compose.prod.yml"
$ProjectName = "document-portal"

function Write-Info($message) {
    Write-Host "[INFO] " -ForegroundColor Green -NoNewline
    Write-Host $message
}

function Write-Warn($message) {
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $message
}

function Write-Error($message) {
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $message
}

function Check-Env {
    if (-not (Test-Path ".env")) {
        Write-Warn ".env file not found. Creating from template..."
        
        # Generate random secret key
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
        
        @"
# Document Portal Production Configuration
# Generated on $(Get-Date)

# REQUIRED: Change this to a secure random string
SECRET_KEY=$secretKey

# Email Configuration (optional)
EMAIL_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@portal.com

# S3 Storage (optional)
S3_ENABLED=false
S3_BUCKET=document-portal
S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=us-east-1
"@ | Out-File -FilePath ".env" -Encoding UTF8
        
        Write-Info ".env file created. Please review and update settings."
    }
}

function Invoke-Build {
    Write-Info "Building Docker images..."
    docker compose -f $ComposeFile -p $ProjectName build --no-cache
    Write-Info "Build complete!"
}

function Invoke-Start {
    Check-Env
    Write-Info "Starting Document Portal..."
    docker compose -f $ComposeFile -p $ProjectName up -d
    Write-Info "Portal started! Checking health..."
    Start-Sleep -Seconds 5
    Invoke-Status
}

function Invoke-Stop {
    Write-Info "Stopping Document Portal..."
    docker compose -f $ComposeFile -p $ProjectName down
    Write-Info "Portal stopped."
}

function Invoke-Restart {
    Write-Info "Restarting Document Portal..."
    docker compose -f $ComposeFile -p $ProjectName restart
    Write-Info "Portal restarted."
}

function Invoke-Logs {
    Write-Info "Showing logs (Ctrl+C to exit)..."
    docker compose -f $ComposeFile -p $ProjectName logs -f
}

function Invoke-Status {
    Write-Info "Container Status:"
    docker compose -f $ComposeFile -p $ProjectName ps
    
    Write-Host ""
    Write-Info "Health Check:"
    
    # Check backend health
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/ready" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[INFO] Backend: " -ForegroundColor Green -NoNewline
            Write-Host "healthy" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[ERROR] Backend: " -ForegroundColor Red -NoNewline
        Write-Host "unhealthy" -ForegroundColor Red
    }
    
    # Check frontend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:80" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[INFO] Frontend: " -ForegroundColor Green -NoNewline
            Write-Host "healthy" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[WARN] Frontend: " -ForegroundColor Yellow -NoNewline
        Write-Host "not accessible" -ForegroundColor Yellow
    }
}

function Invoke-Backup {
    Write-Info "Creating backup..."
    $backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup database
    docker compose -f $ComposeFile -p $ProjectName exec -T backend `
        cp /app/data/portal.db /app/data/portal_backup.db
    docker compose -f $ComposeFile -p $ProjectName cp `
        backend:/app/data/portal_backup.db "$backupDir\portal.db"
    
    Write-Info "Backup created at $backupDir"
}

function Invoke-Update {
    Write-Info "Updating Document Portal..."
    
    # Pull latest code (if using git)
    if (Test-Path ".git") {
        git pull
    }
    
    # Rebuild
    Invoke-Build
    
    Write-Info "Stopping old containers..."
    docker compose -f $ComposeFile -p $ProjectName down
    
    Write-Info "Starting new containers..."
    Invoke-Start
    
    Write-Info "Update complete!"
}

function Show-Help {
    Write-Host "Document Portal V2 Deployment Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 <command>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  build   - Build Docker images"
    Write-Host "  start   - Start the portal"
    Write-Host "  stop    - Stop the portal"
    Write-Host "  restart - Restart the portal"
    Write-Host "  logs    - Show container logs"
    Write-Host "  status  - Show container status"
    Write-Host "  backup  - Backup database"
    Write-Host "  update  - Pull and deploy updates"
    Write-Host "  help    - Show this help message"
}

# Main command router
switch ($Command) {
    "build" { Invoke-Build }
    "start" { Invoke-Start }
    "stop" { Invoke-Stop }
    "restart" { Invoke-Restart }
    "logs" { Invoke-Logs }
    "status" { Invoke-Status }
    "backup" { Invoke-Backup }
    "update" { Invoke-Update }
    "help" { Show-Help }
    default { Show-Help }
}
