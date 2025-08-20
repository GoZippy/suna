# Suna Database Setup

This directory contains the PostgreSQL database setup for the Suna self-hosted migration, replacing Supabase with local database infrastructure.

## Features

- **PostgreSQL 16** with pgvector extension for vector similarity search
- **Redis** for caching and session management
- **Complete schema migration** from Supabase structure
- **Connection pooling** and performance optimization
- **Backup and restore** procedures
- **Database abstraction layer** replacing Supabase client

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for testing and migration scripts)

### 1. Start Database Services

**Windows:**
```cmd
start-database.bat
```

**Linux/macOS:**
```bash
./start-database.sh
```

### 2. Manual Setup (Alternative)

1. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings

3. Start services:
   ```bash
   docker-compose -f docker-compose.db.yml up -d
   ```

4. Test connection:
   ```bash
   cd database
   python3 test_connection.py
   ```

## Database Schema

The database includes the following main tables:

### Core Tables
- `users` - User accounts and authentication
- `user_sessions` - JWT session management
- `user_tiers` - User tier configuration (free, pro, enterprise)
- `projects` - User projects
- `threads` - Conversation threads
- `messages` - Thread messages

### Knowledge Base
- `knowledge_base` - Documents with vector embeddings
- `document_collections` - Knowledge organization
- `search_history` - Search analytics

### Usage Tracking
- `usage_logs` - Resource usage tracking
- `monthly_usage` - Aggregated monthly usage
- `api_keys` - API key management

### System
- `system_config` - System-wide configuration
- `audit_logs` - Security and compliance logging
- `background_jobs` - Task queue management

## Database Operations

### Backup

Create a backup:
```bash
docker exec suna_postgres /backups/backup.sh
```

### Restore

Restore from backup:
```bash
docker exec suna_postgres /backups/restore.sh backup_file.sql.gz
```

### Migrations

Run migrations:
```bash
cd database
python3 scripts/migrate.py migrate
```

Check migration status:
```bash
python3 scripts/migrate.py status
```

Create new migration:
```bash
python3 scripts/migrate.py create "migration_name"
```

## Configuration

### PostgreSQL Configuration

Key settings in `config/postgresql.conf`:
- Connection pooling: 200 max connections
- Memory: 256MB shared buffers, 1GB effective cache
- Logging: Slow query logging enabled
- pgvector: Extension preloaded

### Redis Configuration

Key settings in `config/redis.conf`:
- Memory limit: 512MB with LRU eviction
- Persistence: RDB snapshots enabled
- Performance: Optimized for caching workload

## Connection Management

The database abstraction layer provides:

### Connection Types
- **Raw asyncpg connections** for high-performance queries
- **SQLAlchemy sessions** for ORM operations
- **Redis connections** for caching

### Usage Examples

```python
from database.connection import db_manager
from database.repository import RepositoryFactory

# Raw connection
async with db_manager.get_connection() as conn:
    result = await conn.fetch("SELECT * FROM users")

# SQLAlchemy session
async with db_manager.get_session() as session:
    repos = RepositoryFactory(session)
    user = await repos.users.get_by_email("user@example.com")

# Redis connection
async with db_manager.get_redis() as redis:
    await redis.set("key", "value")
```

## Repository Pattern

High-level database operations through repositories:

### User Operations
```python
# Create user
user = await repos.users.create_user("user@example.com", "password")

# Authenticate
session = await repos.users.create_session(user)

# Verify password
is_valid = await repos.users.verify_password(user, "password")
```

### Project Operations
```python
# Create project
project = await repos.projects.create_project(user.id, "My Project")

# Get user projects
projects = await repos.projects.get_user_projects(user.id)
```

### Knowledge Base Operations
```python
# Add knowledge
knowledge = await repos.knowledge.add_knowledge(
    content="Document content",
    embedding=[0.1, 0.2, ...],  # Vector embedding
    user_id=user.id
)

# Vector search
results = await repos.knowledge.vector_search(
    query_embedding=[0.1, 0.2, ...],
    user_id=user.id,
    limit=10
)
```

## Performance Optimization

### Indexing Strategy
- B-tree indexes on frequently queried columns
- GIN indexes for JSONB and full-text search
- HNSW indexes for vector similarity search

### Connection Pooling
- 20 connections in pool with 30 max overflow
- Connection recycling every hour
- 30-second timeout for connection acquisition

### Caching
- Redis for session storage and query result caching
- Application-level caching for expensive operations

## Security

### Authentication
- bcrypt password hashing with salt
- JWT tokens with secure random generation
- Session management with expiration

### Access Control
- Role-based permissions (admin, user, agent)
- User tier limits and quotas
- API key management with rate limiting

### Audit Logging
- All database operations logged
- IP address and user agent tracking
- Compliance-ready audit trail

## Monitoring

### Health Checks
- Database connection health endpoints
- Redis connectivity monitoring
- Container health status

### Metrics
- Connection pool utilization
- Query performance statistics
- Usage tracking and analytics

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Check if Docker containers are running
   - Verify port mappings in docker-compose.yml
   - Check firewall settings

2. **Permission denied**
   - Ensure proper file permissions on scripts
   - Check Docker volume permissions

3. **Out of memory**
   - Adjust PostgreSQL memory settings
   - Monitor Redis memory usage
   - Check for connection leaks

### Logs

View container logs:
```bash
docker-compose -f docker-compose.db.yml logs -f postgres
docker-compose -f docker-compose.db.yml logs -f redis
```

### Performance Issues

1. Check slow query log in PostgreSQL
2. Monitor connection pool utilization
3. Analyze query execution plans
4. Review index usage statistics

## Migration from Supabase

### Data Export
1. Export data from Supabase using their CLI or API
2. Convert data format to match new schema
3. Use migration scripts to import data

### Configuration Migration
1. Update connection strings in application
2. Replace Supabase client calls with repository methods
3. Update authentication flow to use local JWT

### Testing
1. Run comprehensive test suite
2. Verify data integrity after migration
3. Performance test under expected load

## Development

### Adding New Tables
1. Create migration file in `migrations/`
2. Update SQLAlchemy models in `models.py`
3. Add repository methods in `repository.py`
4. Run migration: `python3 scripts/migrate.py migrate`

### Schema Changes
1. Create new migration file
2. Test migration on development database
3. Backup production before applying
4. Apply migration with rollback plan

## Production Deployment

### Resource Requirements
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM for database
- **Storage**: SSD recommended, 100GB+ space
- **Network**: Gigabit connection for large datasets

### Security Hardening
1. Change default passwords
2. Enable SSL/TLS connections
3. Configure firewall rules
4. Set up regular backups
5. Enable audit logging
6. Monitor for suspicious activity

### Backup Strategy
1. Daily automated backups
2. Weekly full database dumps
3. Point-in-time recovery capability
4. Offsite backup storage
5. Regular restore testing