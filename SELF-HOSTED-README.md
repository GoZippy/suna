# Self-Hosted Suna Deployment Guide

This guide provides instructions for deploying Suna as a self-hosted solution using Docker Compose. This replaces third-party services like Supabase, Stripe, and Daytona with local alternatives.

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM recommended (16GB+ for AI/ML services)
- 50GB+ free disk space
- Linux/Windows/macOS with virtualization support
- (Optional) NVIDIA GPU for local AI model acceleration

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kortix-ai/suna.git
   cd suna
   ```

2. **Set up environment variables:**
   ```bash
   cp self-hosted.env.example .env
   # Edit .env with your preferred values
   ```

3. **Start the services:**
   ```bash
   docker compose -f docker-compose.self-hosted.yml up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Admin Interface: http://localhost:8000/api/admin/
   - Monitoring: http://localhost:9090 (Prometheus), http://localhost:3001 (Grafana)

## Services Overview

### Core Services
- **PostgreSQL + pgvector**: Database with vector search capabilities
- **Redis**: Caching and background job queue
- **Backend**: FastAPI application server
- **Frontend**: Next.js web application
- **Worker**: Background job processor

### AI/ML Services
- **Ollama**: Local LLM server for AI model inference
- **Sentence Transformers**: Local embedding generation

### Supporting Services
- **MailHog**: Local email testing and delivery
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Dashboard and visualization
- **Nginx**: Load balancer and reverse proxy
- **Docker-in-Docker**: Sandbox container management

## Configuration

### Environment Variables

The self-hosted deployment uses a comprehensive environment configuration. Key variables include:

#### Database
```bash
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://suna:password@postgres:5432/suna
```

#### Authentication
```bash
JWT_SECRET_KEY=your_super_secret_jwt_key
ADMIN_EMAIL=admin@suna.local
ADMIN_PASSWORD=your_admin_password
```

#### AI/ML (Optional)
```bash
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_API_KEY=sk-your-openai-key  # Fallback
```

### User Tiers and Credits

The system includes three user tiers with different limits:

- **Free**: 60 minutes/month, 1 concurrent agent, 3 projects
- **Pro**: 300 minutes/month, 3 concurrent agents, 10 projects
- **Enterprise**: 1200 minutes/month, 10 concurrent agents, 50 projects

Users receive initial credits based on their tier:
- Free: 10 credits
- Pro: 50 credits
- Enterprise: 100 credits

## Deployment Options

### Development
```bash
# Start all services
docker compose -f docker-compose.self-hosted.yml up

# Start with logs
docker compose -f docker-compose.self-hosted.yml up -d
docker compose -f docker-compose.self-hosted.yml logs -f
```

### Production
```bash
# Build and start
docker compose -f docker-compose.self-hosted.yml up -d --build

# Scale workers
docker compose -f docker-compose.self-hosted.yml up -d --scale worker=4
```

### Individual Services
```bash
# Start only database
docker compose -f docker-compose.self-hosted.yml up postgres redis

# Start only application
docker compose -f docker-compose.self-hosted.yml up backend frontend

# Start with monitoring
docker compose -f docker-compose.self-hosted.yml up prometheus grafana
```

## Database Setup

The PostgreSQL database is automatically initialized with:

1. **User management tables**: Users, sessions, authentication
2. **Project and agent tables**: Projects, threads, messages, knowledge base
3. **Vector search**: pgvector extension for embeddings
4. **Usage tracking**: Usage logs, credit transactions
5. **Admin interface**: User tier management

### Running Migrations

If you need to run additional migrations:

```bash
# Connect to the database
docker compose -f docker-compose.self-hosted.yml exec postgres psql -U suna -d suna

# Run migration files
docker compose -f docker-compose.self-hosted.yml exec postgres psql -U suna -d suna -f /migrations/003_add_credit_system.sql
```

## AI/ML Setup

### Ollama Configuration

Ollama is included for local AI model inference:

1. **Pull models** (after starting services):
   ```bash
   docker compose -f docker-compose.self-hosted.yml exec ollama ollama pull llama3.1:8b
   docker compose -f docker-compose.self-hosted.yml exec ollama ollama pull codellama:7b
   ```

2. **List available models**:
   ```bash
   docker compose -f docker-compose.self-hosted.yml exec ollama ollama list
   ```

3. **Access Ollama API**:
   - Web interface: http://localhost:11434
   - API endpoint: http://localhost:11434/api/generate

### GPU Support

For GPU acceleration, ensure your Docker environment supports NVIDIA GPUs:

```yaml
# Add to ollama service in docker-compose.self-hosted.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Monitoring and Observability

### Prometheus Metrics

Access Prometheus at http://localhost:9090

### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin/admin by default)

### Logs

View logs for all services:
```bash
# All services
docker compose -f docker-compose.self-hosted.yml logs -f

# Specific service
docker compose -f docker-compose.self-hosted.yml logs -f backend

# Last 100 lines
docker compose -f docker-compose.self-hosted.yml logs --tail=100 worker
```

## Backup and Recovery

### Database Backup
```bash
# Create backup
docker compose -f docker-compose.self-hosted.yml exec postgres pg_dump -U suna suna > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker compose -f docker-compose.self-hosted.yml exec -T postgres psql -U suna suna < backup_file.sql
```

### Volume Backup
```bash
# Backup all volumes
docker run --rm -v suna_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
docker run --rm -v suna_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz /data
```

## Networking

### Internal Network

All services communicate through the `suna-network` bridge network with subnet `172.20.0.0/16`.

### External Access

Services are exposed on localhost ports:
- Frontend: 3000
- Backend API: 8000
- Database: 5432
- Redis: 6379
- Ollama: 11434
- MailHog: 1025 (SMTP), 8025 (Web)
- Prometheus: 9090
- Grafana: 3001

### Production Deployment

For production, consider:
1. Using a reverse proxy (nginx included)
2. Setting up SSL certificates
3. Configuring firewall rules
4. Using environment-specific configurations

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change ports in docker-compose.self-hosted.yml
2. **Memory issues**: Reduce Ollama model size or disable GPU acceleration
3. **Database connection**: Check POSTGRES_PASSWORD in .env file
4. **AI models not loading**: Ensure sufficient RAM and disk space

### Health Checks

Check service health:
```bash
# Check all services
docker compose -f docker-compose.self-hosted.yml ps

# Check specific service
docker compose -f docker-compose.self-hosted.yml exec backend curl -f http://localhost:8000/api/health
```

### Reset Deployment

To reset the entire deployment:
```bash
# Stop and remove everything
docker compose -f docker-compose.self-hosted.yml down -v --remove-orphans

# Clean up
docker system prune -f

# Restart
docker compose -f docker-compose.self-hosted.yml up -d
```

## Security Considerations

### Production Security

1. **Change default passwords** in .env file
2. **Use strong JWT secrets**
3. **Configure SSL/TLS** for external access
4. **Limit network exposure** (avoid exposing database ports externally)
5. **Regular updates** of Docker images
6. **Monitor logs** for suspicious activity

### Access Control

- Admin interface: http://localhost:8000/api/admin/
- Create admin user through the admin interface
- Use strong passwords for all accounts
- Implement 2FA if required

## Performance Tuning

### Database Optimization
```sql
-- Adjust PostgreSQL settings based on your hardware
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem = '64MB';
```

### Redis Optimization
```bash
# Adjust Redis memory in docker-compose.self-hosted.yml
command: redis-server --maxmemory 16gb --maxmemory-policy allkeys-lru
```

### Worker Scaling
```bash
# Scale background workers
docker compose -f docker-compose.self-hosted.yml up -d --scale worker=8
```

## Support

For issues and questions:
1. Check the logs: `docker compose -f docker-compose.self-hosted.yml logs`
2. Verify configuration in .env file
3. Review this documentation
4. Check GitHub issues for known problems

## Migration from Existing Deployments

If migrating from Supabase/Stripe:

1. Export data from Supabase
2. Use the migration scripts in `backend/database/migrations/`
3. Update user tiers and credits
4. Test functionality thoroughly
5. Go live with new deployment

---

This self-hosted deployment provides all the functionality of the cloud version while giving you complete control over your data and infrastructure.
