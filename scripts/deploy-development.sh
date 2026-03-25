#!/bin/bash

# Suna Development Deployment Script
# This script deploys the Suna development stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.development.yml"
ENV_FILE=".env.development"
LOG_FILE="./development.log"

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
    log "Checking development requirements..."
    
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
        warning "Environment file $ENV_FILE not found. Creating from template..."
        cp env.development.example "$ENV_FILE" 2>/dev/null || {
            warning "Could not create environment file. Please create $ENV_FILE manually."
        }
    fi
    
    success "Requirements check passed"
}

stop_existing() {
    log "Stopping existing development services..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    success "Existing services stopped"
}

build_images() {
    log "Building development images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    success "Images built successfully"
}

deploy_services() {
    log "Deploying development services..."
    
    # Start database services first
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    log "Waiting for database services to be ready..."
    sleep 20
    
    # Start backend
    docker-compose -f "$COMPOSE_FILE" up -d backend
    log "Waiting for backend to be ready..."
    sleep 30
    
    # Start remaining services
    docker-compose -f "$COMPOSE_FILE" up -d
    success "All development services deployed"
}

wait_for_health() {
    log "Waiting for services to be healthy..."
    
    # Wait for backend health check
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8091/api/health &> /dev/null; then
            success "Backend is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            warning "Backend health check failed after $max_attempts attempts"
            log "You can check logs with: docker-compose -f $COMPOSE_FILE logs backend"
        fi
        
        log "Waiting for backend health check... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
}

run_migrations() {
    log "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T backend python -m alembic upgrade head || {
        warning "Migration failed, but continuing..."
    }
    success "Database migrations completed"
}

show_status() {
    log "Development Deployment Status:"
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
    
    log "Development Commands:"
    echo "  View logs:    docker-compose -f $COMPOSE_FILE logs -f [service]"
    echo "  Restart:      docker-compose -f $COMPOSE_FILE restart [service]"
    echo "  Shell:        docker-compose -f $COMPOSE_FILE exec backend bash"
    echo "  Stop all:     docker-compose -f $COMPOSE_FILE down"
    echo ""
}

setup_dev_environment() {
    log "Setting up development environment..."
    
    # Create development directories
    mkdir -p ./data/storage
    mkdir -p ./logs
    mkdir -p ./backups
    
    # Set permissions
    chmod 755 ./data/storage
    chmod 755 ./logs
    chmod 755 ./backups
    
    success "Development environment setup completed"
}

# Main deployment process
main() {
    log "Starting Suna development deployment..."
    
    check_requirements
    setup_dev_environment
    stop_existing
    build_images
    deploy_services
    wait_for_health
    run_migrations
    show_status
    
    success "Suna development deployment completed successfully!"
    log "Development log saved to: $LOG_FILE"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --rebuild      Rebuild all images"
        echo "  --status       Show current deployment status"
        echo "  --logs         Show logs for all services"
        echo "  --stop         Stop all development services"
        echo ""
        echo "Environment:"
        echo "  COMPOSE_FILE   Docker Compose file (default: docker-compose.development.yml)"
        echo "  ENV_FILE       Environment file (default: .env.development)"
        exit 0
        ;;
    --rebuild)
        log "Rebuilding development images..."
        docker-compose -f "$COMPOSE_FILE" build --no-cache
        success "Images rebuilt successfully"
        exit 0
        ;;
    --status)
        docker-compose -f "$COMPOSE_FILE" ps
        exit 0
        ;;
    --logs)
        docker-compose -f "$COMPOSE_FILE" logs -f
        exit 0
        ;;
    --stop)
        log "Stopping development services..."
        docker-compose -f "$COMPOSE_FILE" down
        success "Development services stopped"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        ;;
esac







