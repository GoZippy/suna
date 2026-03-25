#!/bin/bash

# Suna Production Deployment Script
# This script deploys the complete Suna self-hosted stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
LOG_FILE="./deployment.log"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

check_requirements() {
    log "Checking deployment requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file $ENV_FILE not found. Please copy env.production.example to $ENV_FILE and configure it."
    fi
    
    # Check if required directories exist
    if [ ! -d "./monitoring" ]; then
        error "Monitoring directory not found. Please ensure monitoring configuration is present."
    fi
    
    success "Requirements check passed"
}

backup_existing() {
    if [ -d "$BACKUP_DIR" ]; then
        log "Creating backup of existing deployment..."
        BACKUP_NAME="suna-backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
        
        # Backup volumes
        docker run --rm -v suna_postgres_data:/data -v "$(pwd)/$BACKUP_DIR/$BACKUP_NAME":/backup alpine tar czf /backup/postgres.tar.gz -C /data .
        docker run --rm -v suna_redis_data:/data -v "$(pwd)/$BACKUP_DIR/$BACKUP_NAME":/backup alpine tar czf /backup/redis.tar.gz -C /data .
        
        success "Backup created: $BACKUP_DIR/$BACKUP_NAME"
    fi
}

stop_existing() {
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    success "Existing services stopped"
}

pull_images() {
    log "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    success "Images pulled successfully"
}

deploy_services() {
    log "Deploying services..."
    
    # Start services in order
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    log "Waiting for database services to be ready..."
    sleep 30
    
    docker-compose -f "$COMPOSE_FILE" up -d backend
    log "Waiting for backend to be ready..."
    sleep 60
    
    docker-compose -f "$COMPOSE_FILE" up -d worker frontend
    log "Waiting for application services to be ready..."
    sleep 30
    
    docker-compose -f "$COMPOSE_FILE" up -d
    success "All services deployed"
}

wait_for_health() {
    log "Waiting for services to be healthy..."
    
    # Wait for backend health check
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8091/api/health &> /dev/null; then
            success "Backend is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Backend health check failed after $max_attempts attempts"
        fi
        
        log "Waiting for backend health check... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    # Wait for frontend health check
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:3091/api/health &> /dev/null; then
            success "Frontend is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Frontend health check failed after $max_attempts attempts"
        fi
        
        log "Waiting for frontend health check... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
}

run_migrations() {
    log "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T backend python -m alembic upgrade head
    success "Database migrations completed"
}

show_status() {
    log "Deployment Status:"
    echo ""
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    log "Service URLs:"
    echo "  Frontend:     http://localhost:3091"
    echo "  Backend API:  http://localhost:8091"
    echo "  Admin Panel:  http://localhost:8091/admin"
    echo "  Grafana:      http://localhost:3191 (admin/admin)"
    echo "  Prometheus:   http://localhost:9091"
    echo "  MailHog:      http://localhost:8091 (SMTP: localhost:1091)"
    echo "  Ollama:       http://localhost:11491"
    echo ""
    
    log "Health Check URLs:"
    echo "  Backend Health: http://localhost:8091/api/health"
    echo "  Frontend Health: http://localhost:3091/api/health"
    echo "  Metrics: http://localhost:8091/api/monitoring/metrics"
    echo ""
}

cleanup_old_backups() {
    log "Cleaning up old backups (keeping last 5)..."
    if [ -d "$BACKUP_DIR" ]; then
        cd "$BACKUP_DIR"
        ls -t | tail -n +6 | xargs -r rm -rf
        cd - > /dev/null
        success "Old backups cleaned up"
    fi
}

# Main deployment process
main() {
    log "Starting Suna production deployment..."
    
    check_requirements
    backup_existing
    stop_existing
    pull_images
    deploy_services
    wait_for_health
    run_migrations
    show_status
    cleanup_old_backups
    
    success "Suna production deployment completed successfully!"
    log "Deployment log saved to: $LOG_FILE"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --backup-only  Only create backup, don't deploy"
        echo "  --status       Show current deployment status"
        echo ""
        echo "Environment:"
        echo "  COMPOSE_FILE   Docker Compose file (default: docker-compose.production.yml)"
        echo "  ENV_FILE       Environment file (default: .env.production)"
        exit 0
        ;;
    --backup-only)
        check_requirements
        backup_existing
        success "Backup completed"
        exit 0
        ;;
    --status)
        docker-compose -f "$COMPOSE_FILE" ps
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        ;;
esac







