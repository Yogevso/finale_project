#!/bin/bash
# Deploy script for Documentation Platform
# Usage: ./deploy.sh [build|start|stop|restart|logs|status]

set -e

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_NAME="document-portal"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from template..."
        cat > .env << EOF
# Documentation Platform Production Configuration
# Generated on $(date)

# REQUIRED: Change this to a secure random string
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "change-this-secret-key")

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
EOF
        log_info ".env file created. Please review and update settings."
    fi
}

build() {
    log_info "Building Docker images..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache
    log_info "Build complete!"
}

start() {
    check_env
    log_info "Starting Documentation Platform..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    log_info "Portal started! Checking health..."
    sleep 5
    status
}

stop() {
    log_info "Stopping Documentation Platform..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    log_info "Portal stopped."
}

restart() {
    log_info "Restarting Documentation Platform..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
    log_info "Portal restarted."
}

logs() {
    log_info "Showing logs (Ctrl+C to exit)..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
}

status() {
    log_info "Container Status:"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    
    echo ""
    log_info "Health Check:"
    
    # Check backend health
    if curl -sf http://localhost:8001/ready > /dev/null 2>&1; then
        log_info "Backend: ${GREEN}healthy${NC}"
    else
        log_error "Backend: ${RED}unhealthy${NC}"
    fi
    
    # Check frontend
    if curl -sf http://localhost:80 > /dev/null 2>&1; then
        log_info "Frontend: ${GREEN}healthy${NC}"
    else
        log_warn "Frontend: ${YELLOW}not accessible${NC}"
    fi
}

backup() {
    log_info "Creating backup..."
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Backup database
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T backend \
        cp /app/data/portal.db /app/data/portal_backup.db
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME cp \
        backend:/app/data/portal_backup.db $BACKUP_DIR/portal.db
    
    log_info "Backup created at $BACKUP_DIR"
}

update() {
    log_info "Updating Documentation Platform..."
    
    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        git pull
    fi
    
    # Rebuild and restart
    build
    
    log_info "Stopping old containers..."
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    
    log_info "Starting new containers..."
    start
    
    log_info "Update complete!"
}

# Main command router
case "$1" in
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    backup)
        backup
        ;;
    update)
        update
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|status|backup|update}"
        echo ""
        echo "Commands:"
        echo "  build   - Build Docker images"
        echo "  start   - Start the portal"
        echo "  stop    - Stop the portal"
        echo "  restart - Restart the portal"
        echo "  logs    - Show container logs"
        echo "  status  - Show container status"
        echo "  backup  - Backup database"
        echo "  update  - Pull and deploy updates"
        exit 1
        ;;
esac
