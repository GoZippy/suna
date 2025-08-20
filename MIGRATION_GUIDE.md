# Supabase to Local PostgreSQL Migration Guide

This guide walks you through migrating your Suna installation from Supabase to a fully self-hosted PostgreSQL setup.

## Overview

The migration replaces the following Supabase services with local alternatives:

- **Supabase Database** → **PostgreSQL with pgvector**
- **Supabase Auth** → **Local JWT authentication**
- **Supabase Storage** → **Local file system storage**
- **Supabase Realtime** → **WebSocket-based real-time updates**

## Prerequisites

1. **Docker and Docker Compose** installed
2. **Access to your current Supabase project** (URL and service role key)
3. **Python 3.11+** for running migration scripts
4. **Sufficient disk space** for database and file storage

## Step 1: Prepare Local Environment

### 1.1 Clone and Setup

```bash
# Navigate to your Suna directory
cd /path/to/suna

# Create local environment file
cp backend/.env.example backend/.env.local
```

### 1.2 Configure Environment Variables

Edit `backend/.env.local`:

```bash
# Database Configuration
DATABASE_URL=postgresql://suna_user:suna_password@localhost:5432/suna

# JWT Configuration (generate a secure secret)
JWT_SECRET_KEY=your-very-secure-secret-key-here

# Local Storage
LOCAL_STORAGE_PATH=./data/storage
MAX_FILE_SIZE=104857600  # 100MB

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Legacy Supabase (for migration only)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Other existing configuration...
OPENAI_API_KEY=your-openai-key
# ... etc
```

## Step 2: Start Local Infrastructure

### 2.1 Start PostgreSQL and Redis

```bash
# Start only the database services first
docker-compose -f docker-compose.local.yml up -d postgres redis

# Wait for services to be ready
docker-compose -f docker-compose.local.yml logs -f postgres
```

### 2.2 Initialize Database Schema

The PostgreSQL container will automatically run the initialization scripts in `database/init/` when it starts for the first time.

Verify the database is ready:

```bash
# Connect to the database
docker exec -it suna_postgres psql -U suna_user -d suna

# Check that tables were created
\dt

# Check that extensions are installed
\dx

# Exit
\q
```

## Step 3: Migrate Data from Supabase

### 3.1 Export Supabase Data

```bash
cd backend

# Export all data to JSON files (creates ./migration_export/ directory)
python migrate_from_supabase.py export
```

This creates backup files in `./migration_export/`:
- `users.json`
- `projects.json`
- `threads.json`
- `messages.json`
- `knowledge_base.json`
- etc.

### 3.2 Import Data to PostgreSQL

```bash
# Import the exported data to local PostgreSQL
python migrate_from_supabase.py import
```

### 3.3 Alternative: Full Migration

You can also run export and import in one command:

```bash
# Full migration (export + import)
python migrate_from_supabase.py migrate
```

## Step 4: Migrate File Storage

### 4.1 Export Files from Supabase Storage

If you have files in Supabase Storage, you'll need to download them:

```bash
# Create storage directories
mkdir -p data/storage/{projects,uploads,avatars,screenshots,documents,temp}

# Use Supabase CLI or custom script to download files
# Example with Supabase CLI:
supabase storage download --project-ref your-project-ref bucket-name ./data/storage/bucket-name/
```

### 4.2 Update File References

After migrating files, update any database references to use the new local storage URLs:

```sql
-- Example: Update file URLs in your database
UPDATE knowledge_base 
SET metadata = jsonb_set(
    metadata, 
    '{file_url}', 
    to_jsonb(replace(metadata->>'file_url', 'supabase.co/storage', 'localhost:8000/api/storage'))
)
WHERE metadata->>'file_url' LIKE '%supabase.co/storage%';
```

## Step 5: Update Application Configuration

### 5.1 Update Backend Dependencies

The migration has already updated `pyproject.toml` to:
- Remove `supabase==2.17.0`
- Add `asyncpg==0.29.0` and `psycopg2-binary==2.9.9`

Install new dependencies:

```bash
cd backend
pip install -r requirements.txt
# or if using uv:
uv sync
```

### 5.2 Update Frontend Configuration

Update your frontend environment variables to point to the local backend:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Step 6: Start the Full Application

### 6.1 Start All Services

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Check logs
docker-compose -f docker-compose.local.yml logs -f
```

### 6.2 Verify Migration

1. **Check Database Connection**:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Test Authentication**:
   - Try logging in with existing user credentials
   - Create a new user account

3. **Test File Upload**:
   - Upload a file through the UI
   - Verify it appears in `data/storage/`

4. **Test Real-time Features**:
   - Open multiple browser tabs
   - Verify real-time updates work

## Step 7: Production Deployment

### 7.1 Security Hardening

1. **Change Default Passwords**:
   ```bash
   # Generate secure passwords
   openssl rand -base64 32  # For JWT_SECRET_KEY
   openssl rand -base64 16  # For database password
   ```

2. **Configure TLS/SSL**:
   - Set up reverse proxy (nginx/traefik)
   - Configure SSL certificates
   - Update CORS settings

3. **Database Security**:
   - Change default database credentials
   - Configure connection limits
   - Set up database backups

### 7.2 Performance Optimization

1. **Database Tuning**:
   ```sql
   -- Optimize PostgreSQL settings in postgresql.conf
   shared_buffers = 256MB
   effective_cache_size = 1GB
   maintenance_work_mem = 64MB
   ```

2. **Connection Pooling**:
   - Configure pgbouncer if needed
   - Adjust connection pool sizes

3. **Storage Optimization**:
   - Set up file compression
   - Configure backup retention
   - Monitor disk usage

## Step 8: Cleanup

### 8.1 Remove Supabase Dependencies

Once migration is verified successful:

1. **Remove Supabase environment variables**
2. **Update any remaining Supabase references in code**
3. **Cancel Supabase subscription** (after thorough testing)

### 8.2 Backup Strategy

Set up regular backups:

```bash
# Database backup script
#!/bin/bash
docker exec suna_postgres pg_dump -U suna_user suna > backup_$(date +%Y%m%d_%H%M%S).sql

# File storage backup
tar -czf storage_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/storage/
```

## Troubleshooting

### Common Issues

1. **Migration Script Fails**:
   - Check Supabase credentials
   - Verify network connectivity
   - Check PostgreSQL is running

2. **Authentication Issues**:
   - Verify JWT_SECRET_KEY is set
   - Check user passwords were migrated correctly
   - Ensure auth endpoints are working

3. **File Upload Issues**:
   - Check storage directory permissions
   - Verify LOCAL_STORAGE_PATH configuration
   - Check disk space

4. **Real-time Features Not Working**:
   - Verify WebSocket endpoint is accessible
   - Check browser console for connection errors
   - Ensure WebSocket API is included in routes

### Getting Help

1. **Check Logs**:
   ```bash
   # Backend logs
   docker-compose -f docker-compose.local.yml logs backend
   
   # Database logs
   docker-compose -f docker-compose.local.yml logs postgres
   ```

2. **Database Debugging**:
   ```bash
   # Connect to database
   docker exec -it suna_postgres psql -U suna_user -d suna
   
   # Check table contents
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM messages;
   ```

3. **Test Individual Components**:
   - Test database connection: `curl http://localhost:8000/api/health`
   - Test auth: `curl -X POST http://localhost:8000/api/auth/login`
   - Test storage: Upload a file through the API

## Migration Checklist

- [ ] Local PostgreSQL running with pgvector
- [ ] Database schema initialized
- [ ] Supabase data exported to JSON
- [ ] Data imported to PostgreSQL
- [ ] File storage migrated
- [ ] Authentication working
- [ ] Real-time features working
- [ ] File upload/download working
- [ ] All existing functionality verified
- [ ] Production security configured
- [ ] Backup strategy implemented
- [ ] Supabase dependencies removed

## Next Steps

After successful migration, consider:

1. **Setting up monitoring** (Prometheus/Grafana)
2. **Implementing log aggregation**
3. **Configuring automated backups**
4. **Setting up CI/CD for updates**
5. **Documenting your local deployment**

Your Suna installation is now fully self-hosted and independent of external services!