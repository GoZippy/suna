# Suna Self-Hosted Deployment Guide

This guide covers deploying Suna as a fully self-hosted solution with all the services we've implemented in the migration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Production Deployment](#production-deployment)
4. [Development Deployment](#development-deployment)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements

- **OS**: Linux, macOS, or Windows with Docker support
- **Docker**: Version 20.10+ with Docker Compose
- **RAM**: Minimum 8GB (16GB recommended for production)
- **Storage**: Minimum 20GB available space
- **CPU**: 4 cores minimum (8 cores recommended for production)

### Software Requirements

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd suna
```

### 2. Set Up Environment

```bash
# For development
cp env.development.example .env.development
# Edit .env.development with your configuration

# For production
cp env.production.example .env.production
# Edit .env.production with your configuration
```

### 3. Deploy

```bash
# Development deployment
chmod +x scripts/deploy-development.sh
./scripts/deploy-development.sh

# Production deployment
chmod +x scripts/deploy-production.sh
./scripts/deploy-production.sh
```

### 4. Access Services

After deployment, you can access:

- **Frontend**: http://localhost:3091
- **Backend API**: http://localhost:8091
- **Admin Panel**: http://localhost:8091/admin
- **Grafana**: http://localhost:3191 (admin/admin)
- **Prometheus**: http://localhost:9091
- **MailHog**: http://localhost:8091 (SMTP: localhost:1091)
- **Ollama**: http://localhost:11491

## Production Deployment

### Step-by-Step Production Setup

1. **Prepare Environment**

```bash
# Copy production environment template
cp env.production.example .env.production

# Edit configuration
nano .env.production
```

2. **Configure Security**

```bash
# Generate secure passwords
openssl rand -base64 32  # For JWT_SECRET_KEY
openssl rand -base64 32  # For API_KEY_SECRET
openssl rand -base64 32  # For POSTGRES_PASSWORD
```

3. **Deploy**

```bash
# Run production deployment
./scripts/deploy-production.sh
```

4. **Verify Deployment**

```bash
# Check service status
./scripts/deploy-production.sh --status

# Check health endpoints
curl http://localhost:8091/api/health
curl http://localhost:3091/api/health
```

### Production Configuration

#### Environment Variables

Key production settings in `.env.production`:

```bash
# Security
JWT_SECRET_KEY=your-super-secret-jwt-key
API_KEY_SECRET=your-api-key-secret
POSTGRES_PASSWORD=secure-database-password

# Performance
WORKER_PROCESSES=4
WORKER_THREADS=4

# Monitoring
GRAFANA_PASSWORD=secure-grafana-password

# Feature Flags
ENABLE_MONITORING=true
ENABLE_ALERTING=true
ENABLE_AUDIT_LOGGING=true
```

#### Resource Allocation

For production deployments, consider:

- **Database**: 2-4GB RAM, 4+ CPU cores
- **Redis**: 1-2GB RAM, 2+ CPU cores
- **Backend**: 4-8GB RAM, 4+ CPU cores
- **Frontend**: 2-4GB RAM, 2+ CPU cores
- **Monitoring**: 2-4GB RAM, 2+ CPU cores

## Development Deployment

### Step-by-Step Development Setup

1. **Prepare Environment**

```bash
# Copy development environment template
cp env.development.example .env.development

# Edit configuration (optional)
nano .env.development
```

2. **Deploy**

```bash
# Run development deployment
./scripts/deploy-development.sh
```

3. **Development Workflow**

```bash
# View logs
./scripts/deploy-development.sh --logs

# Rebuild images
./scripts/deploy-development.sh --rebuild

# Stop services
./scripts/deploy-development.sh --stop
```

### Development Configuration

Development-specific settings:

```bash
# Development mode
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true
RELOAD=true

# Reduced resources
WORKER_PROCESSES=2
WORKER_THREADS=2
MAX_PARALLEL_AGENT_RUNS=2
```

## Configuration

### Docker Compose Files

The deployment uses different Docker Compose files:

- `docker-compose.production.yml` - Production deployment
- `docker-compose.development.yml` - Development deployment
- `docker-compose.self-hosted.yml` - Self-hosted variant
- `docker-compose.local.yml` - Local development

### Service Configuration

#### Database (PostgreSQL)

```yaml
postgres:
  image: pgvector/pgvector:pg16
  environment:
    POSTGRES_DB: suna
    POSTGRES_USER: suna
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  ports:
    - "5491:5432"
```

#### Redis

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
  ports:
    - "6391:6379"
```

#### Backend (FastAPI)

```yaml
backend:
  build: ./backend
  environment:
    - DATABASE_URL=postgresql://suna:${POSTGRES_PASSWORD}@postgres:5432/suna
    - REDIS_HOST=redis
    - REDIS_PORT=6391
  ports:
    - "8091:8000"
```

#### Frontend (Next.js)

```yaml
frontend:
  build: ./frontend
  environment:
    - NEXT_PUBLIC_API_URL=http://localhost:8091
    - NEXT_PUBLIC_WS_URL=ws://localhost:8091
  ports:
    - "3091:3000"
```

### Port Configuration

All services use the `XX91` port scheme:

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Frontend | 3000 | 3091 |
| Backend | 8000 | 8091 |
| PostgreSQL | 5432 | 5491 |
| Redis | 6379 | 6391 |
| Grafana | 3000 | 3191 |
| Prometheus | 9090 | 9091 |
| Alertmanager | 9093 | 9191 |
| SMTP | 1025 | 1091 |
| Ollama | 11434 | 11491 |

## Monitoring

### Prometheus Configuration

Prometheus scrapes metrics from:

- Backend API: `http://backend:8000/api/monitoring/metrics/prometheus`
- Node Exporter: `http://node-exporter:9100/metrics`

### Grafana Dashboards

Pre-configured dashboards include:

- **System Overview**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times
- **Database Performance**: Connection pool, query latency
- **Redis Metrics**: Memory usage, command rates
- **WebSocket Connections**: Active connections, message rates

### Alerting

Alertmanager is configured with:

- **High CPU Usage**: >80% for 5 minutes
- **High Memory Usage**: >85% for 5 minutes
- **High Disk Usage**: >90% for 5 minutes
- **Database High Latency**: >1000ms for 5 minutes
- **Redis High Latency**: >100ms for 5 minutes

### Accessing Monitoring

```bash
# Grafana
http://localhost:3191
Username: admin
Password: admin (change in production)

# Prometheus
http://localhost:9091

# Alertmanager
http://localhost:9191
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts

If you get port conflicts:

```bash
# Check what's using the ports
netstat -tulpn | grep :3091
netstat -tulpn | grep :8091

# Stop conflicting services or change ports in .env file
```

#### 2. Database Connection Issues

```bash
# Check database logs
docker-compose logs postgres

# Test database connection
docker-compose exec backend python -c "
from database.connection import get_db
db = next(get_db())
print('Database connection successful')
"
```

#### 3. Redis Connection Issues

```bash
# Check Redis logs
docker-compose logs redis

# Test Redis connection
docker-compose exec backend python -c "
import redis
r = redis.Redis(host='redis', port=6391)
print('Redis connection successful:', r.ping())
"
```

#### 4. Service Health Checks

```bash
# Check all service health
curl http://localhost:8091/api/health
curl http://localhost:8091/api/monitoring/health

# Check individual services
curl http://localhost:8091/api/monitoring/health/database
curl http://localhost:8091/api/monitoring/health/redis
curl http://localhost:8091/api/monitoring/health/websocket
```

### Logs and Debugging

#### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

#### Debug Mode

For development debugging:

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart services
docker-compose restart backend
```

### Performance Issues

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

#### Slow Database Queries

```bash
# Check database performance
docker-compose exec postgres psql -U suna -d suna -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"
```

## Backup and Recovery

### Automated Backups

The production deployment script includes automated backups:

```bash
# Create backup
./scripts/deploy-production.sh --backup-only

# Backups are stored in ./backups/
```

### Manual Backup

```bash
# Database backup
docker-compose exec postgres pg_dump -U suna suna > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis backup
docker-compose exec redis redis-cli BGSAVE
docker cp suna_redis_1:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# File storage backup
tar -czf storage_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./data/storage/
```

### Recovery

#### Database Recovery

```bash
# Stop services
docker-compose down

# Restore database
docker-compose up -d postgres
sleep 30
docker-compose exec -T postgres psql -U suna -d suna < backup_file.sql

# Restart services
docker-compose up -d
```

#### Full System Recovery

```bash
# Stop all services
docker-compose down

# Restore volumes
docker run --rm -v suna_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
docker run --rm -v suna_redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis_backup.tar.gz -C /data

# Restart services
docker-compose up -d
```

### Backup Retention

The deployment script automatically manages backup retention:

- Keeps last 5 backups
- Removes older backups automatically
- Logs backup operations

## Security Considerations

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Use strong JWT secrets
- [ ] Configure firewall rules
- [ ] Enable HTTPS (reverse proxy)
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption
- [ ] Network isolation

### Network Security

```bash
# Restrict external access (example)
# Only allow localhost access
ports:
  - "127.0.0.1:8091:8000"
  - "127.0.0.1:3091:3000"
```

### SSL/TLS Configuration

For production, add a reverse proxy (nginx/traefik):

```yaml
# Example nginx configuration
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./ssl:/etc/nginx/ssl
```

## Support and Maintenance

### Regular Maintenance

```bash
# Weekly tasks
docker system prune -f
docker-compose pull
./scripts/deploy-production.sh --backup-only

# Monthly tasks
docker-compose down
docker volume prune -f
docker-compose up -d
```

### Monitoring Alerts

Set up monitoring alerts for:

- Service downtime
- High resource usage
- Database connection issues
- Disk space warnings

### Updates and Upgrades

```bash
# Update images
docker-compose pull

# Rebuild with new code
docker-compose build --no-cache

# Deploy updates
./scripts/deploy-production.sh
```

## Conclusion

This deployment guide covers the complete self-hosted Suna setup. The system includes:

- **Core Services**: Backend API, Frontend, Database, Redis
- **Email System**: Local SMTP with MailHog
- **Background Jobs**: Redis-based Dramatiq workers
- **Real-time Communication**: WebSocket endpoints
- **File Storage**: Local file system with admin interface
- **Monitoring**: Prometheus, Grafana, Alertmanager
- **Local AI**: Ollama integration
- **Admin Interface**: Comprehensive management dashboard

For additional support or questions, refer to the project documentation or create an issue in the repository.







