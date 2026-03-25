# Suna Migration Guide: Supabase to Self-Hosted

This guide provides step-by-step instructions for migrating from a Supabase-based Suna installation to the self-hosted version.

## 📋 Migration Overview

### What Gets Migrated

- **User Data**: User accounts, profiles, and authentication data
- **Agent Data**: Agent configurations, workflows, and execution history
- **Knowledge Base**: Documents, embeddings, and vector data
- **File Storage**: Uploaded files and media
- **Configuration**: System settings and environment variables
- **Analytics**: Usage statistics and performance data

### What Changes

- **Authentication**: From Supabase Auth to local JWT system
- **Database**: From Supabase PostgreSQL to local PostgreSQL with pgvector
- **Storage**: From Supabase Storage to local file system
- **Real-time**: From Supabase subscriptions to WebSocket implementation
- **Billing**: From Stripe to local user tier system

## 🚀 Pre-Migration Checklist

### 1. System Requirements Verification

```bash
# Check system resources
free -h
df -h
nproc

# Verify Docker installation
docker --version
docker-compose --version

# Check available ports
netstat -tulpn | grep -E ':(3091|8091|5491|6391|9091)'
```

### 2. Backup Current System

```bash
# Create backup directory
mkdir -p /opt/suna/backups/$(date +%Y%m%d_%H%M%S)
cd /opt/suna/backups/$(date +%Y%m%d_%H%M%S)

# Backup Supabase data (if you have access)
# This will be done by the migration tools
```

### 3. Environment Preparation

```bash
# Clone Suna repository
git clone https://github.com/your-org/suna.git
cd suna

# Install migration tools
pip install -r requirements.txt
```

## 🔄 Migration Process

### Step 1: Data Export from Supabase

#### Using Migration Tools

```bash
# Configure Supabase connection
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-supabase-anon-key"
export SUPABASE_SERVICE_KEY="your-supabase-service-key"

# Run data export
python -m suna.migration.export_data \
    --supabase-url $SUPABASE_URL \
    --supabase-key $SUPABASE_SERVICE_KEY \
    --output-dir ./migration_data \
    --include-files \
    --include-embeddings
```

#### Manual Export (Alternative)

```bash
# Export users
psql "postgresql://postgres:[password]@[host]:5432/postgres" \
    -c "COPY (SELECT * FROM auth.users) TO STDOUT CSV HEADER" > users.csv

# Export agents
psql "postgresql://postgres:[password]@[host]:5432/postgres" \
    -c "COPY (SELECT * FROM public.agents) TO STDOUT CSV HEADER" > agents.csv

# Export workflows
psql "postgresql://postgres:[password]@[host]:5432/postgres" \
    -c "COPY (SELECT * FROM public.agent_workflows) TO STDOUT CSV HEADER" > workflows.csv

# Export knowledge base
psql "postgresql://postgres:[password]@[host]:5432/postgres" \
    -c "COPY (SELECT * FROM public.knowledge_base) TO STDOUT CSV HEADER" > knowledge_base.csv
```

### Step 2: Self-Hosted System Setup

#### Install Self-Hosted Suna

```bash
# Follow installation guide
# See: docs/installation.md

# Start services
docker-compose up -d

# Wait for services to be ready
sleep 60
```

#### Verify Self-Hosted System

```bash
# Check service health
curl -f http://localhost:8091/health

# Check database connectivity
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_db():
    db = get_database()
    await db.execute('SELECT 1')
    print('Database ready for migration')
asyncio.run(check_db())
"
```

### Step 3: Data Import

#### Using Migration Tools

```bash
# Import data to self-hosted system
python -m suna.migration.import_data \
    --input-dir ./migration_data \
    --database-url "postgresql://suna_user:password@localhost:5491/suna" \
    --redis-url "redis://:password@localhost:6391/0" \
    --transform-passwords \
    --validate-data
```

#### Manual Import (Alternative)

```bash
# Import users (with password transformation)
psql "postgresql://suna_user:password@localhost:5491/suna" \
    -c "\COPY users FROM 'users.csv' CSV HEADER"

# Import agents
psql "postgresql://suna_user:password@localhost:5491/suna" \
    -c "\COPY agents FROM 'agents.csv' CSV HEADER"

# Import workflows
psql "postgresql://suna_user:password@localhost:5491/suna" \
    -c "\COPY agent_workflows FROM 'workflows.csv' CSV HEADER"

# Import knowledge base
psql "postgresql://suna_user:password@localhost:5491/suna" \
    -c "\COPY knowledge_base FROM 'knowledge_base.csv' CSV HEADER"
```

### Step 4: File Migration

#### Download Files from Supabase Storage

```bash
# Download all files from Supabase Storage
python -m suna.migration.migrate_files \
    --supabase-url $SUPABASE_URL \
    --supabase-key $SUPABASE_SERVICE_KEY \
    --local-storage-path /opt/suna/storage \
    --preserve-structure
```

#### Update File References

```bash
# Update file paths in database
python -m suna.migration.update_file_paths \
    --database-url "postgresql://suna_user:password@localhost:5491/suna" \
    --old-prefix "https://your-project.supabase.co/storage/v1/object/public" \
    --new-prefix "/storage"
```

### Step 5: Configuration Migration

#### Environment Variables

```bash
# Copy relevant environment variables
cp .env.example .env

# Update with your configuration
cat >> .env << EOF

# Migrated from Supabase
DOMAIN=your-domain.com
SECRET_KEY=your_secret_key
POSTGRES_PASSWORD=your_postgres_password
REDIS_PASSWORD=your_redis_password

# Admin user (from Supabase)
ADMIN_EMAIL=admin@your-domain.com
ADMIN_PASSWORD=your_admin_password
EOF
```

#### Service Configuration

```bash
# Update service configurations
python -m suna.migration.migrate_config \
    --input-config ./migration_data/config.json \
    --output-config ./config/local.json \
    --transform-urls
```

### Step 6: Data Validation

#### Verify Data Integrity

```bash
# Run data validation
python -m suna.migration.validate_migration \
    --source-data ./migration_data \
    --target-database "postgresql://suna_user:password@localhost:5491/suna" \
    --check-users \
    --check-agents \
    --check-workflows \
    --check-files \
    --generate-report
```

#### Test User Authentication

```bash
# Test user login
curl -X POST http://localhost:8091/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test@example.com",
        "password": "testpassword"
    }'
```

## 🔧 Post-Migration Configuration

### 1. Update DNS and Domain

```bash
# Update DNS records
# Point your domain to the new server IP

# Update Nginx configuration
sudo nano /etc/nginx/sites-available/suna

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Configure SSL/TLS

```bash
# Install Let's Encrypt certificate
sudo certbot --nginx -d your-domain.com

# Verify certificate
sudo certbot certificates
```

### 3. Set Up Monitoring

```bash
# Configure Prometheus targets
sudo nano /opt/suna/prometheus/prometheus.yml

# Import Grafana dashboards
# See: docs/monitoring-setup.md
```

### 4. Configure Backups

```bash
# Set up automated backups
sudo crontab -e

# Add backup schedule
0 2 * * * /opt/suna/scripts/backup.sh
```

## 🔒 Security Hardening

### 1. Update Passwords

```bash
# Force password reset for all users
python -m suna.cli force-password-reset --all-users

# Update admin password
python -m suna.cli update-admin-password \
    --email admin@your-domain.com \
    --new-password "secure_new_password"
```

### 2. Configure Firewall

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3091/tcp
sudo ufw allow 8091/tcp
sudo ufw allow 9091/tcp
sudo ufw reload
```

### 3. Security Scanning

```bash
# Run security scan
python -m suna.security.scan \
    --target localhost \
    --ports 3091,8091,9091 \
    --check-vulnerabilities \
    --generate-report
```

## 📊 Migration Validation

### 1. Functional Testing

```bash
# Run comprehensive tests
python -m pytest tests/migration/test_migration.py -v

# Test user workflows
python -m suna.tests.e2e.test_user_workflows \
    --base-url http://localhost:3091 \
    --admin-email admin@your-domain.com \
    --admin-password your_admin_password
```

### 2. Performance Testing

```bash
# Run performance tests
python -m suna.tests.performance.test_performance \
    --target http://localhost:8091 \
    --users 10 \
    --duration 300 \
    --generate-report
```

### 3. Data Verification

```bash
# Verify data completeness
python -m suna.migration.verify_data \
    --source-counts ./migration_data/counts.json \
    --target-database "postgresql://suna_user:password@localhost:5491/suna" \
    --tolerance 0.01
```

## 🔄 Rollback Plan

### If Migration Fails

```bash
# Stop self-hosted services
docker-compose down

# Restore from backup
python -m suna.migration.rollback \
    --backup-dir /opt/suna/backups/$(date +%Y%m%d_%H%M%S) \
    --supabase-url $SUPABASE_URL \
    --supabase-key $SUPABASE_SERVICE_KEY

# Verify rollback
python -m suna.migration.verify_rollback \
    --source-data ./migration_data \
    --supabase-url $SUPABASE_URL \
    --supabase-key $SUPABASE_SERVICE_KEY
```

## 📈 Post-Migration Optimization

### 1. Database Optimization

```bash
# Run database optimization
docker-compose exec backend python -m suna.database.optimize \
    --analyze-tables \
    --create-indexes \
    --vacuum-tables
```

### 2. Cache Warming

```bash
# Warm up Redis cache
python -m suna.cache.warm \
    --redis-url "redis://:password@localhost:6391/0" \
    --popular-queries \
    --user-sessions
```

### 3. Performance Monitoring

```bash
# Set up performance alerts
python -m suna.monitoring.setup_alerts \
    --prometheus-url http://localhost:9090 \
    --alertmanager-url http://localhost:9093 \
    --thresholds ./config/alert-thresholds.yml
```

## 🆘 Troubleshooting

### Common Issues

#### Data Import Errors

```bash
# Check import logs
tail -f /var/log/suna/migration.log

# Fix encoding issues
python -m suna.migration.fix_encoding \
    --input-file problematic_file.csv \
    --output-file fixed_file.csv \
    --encoding utf-8
```

#### Authentication Issues

```bash
# Reset user passwords
python -m suna.cli reset-user-password \
    --email user@example.com \
    --new-password "new_password"

# Check JWT configuration
python -m suna.auth.verify_jwt_config
```

#### File Access Issues

```bash
# Fix file permissions
sudo chown -R suna:suna /opt/suna/storage
sudo chmod -R 755 /opt/suna/storage

# Verify file paths
python -m suna.migration.verify_files \
    --storage-path /opt/suna/storage \
    --database-url "postgresql://suna_user:password@localhost:5491/suna"
```

### Getting Help

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Review migration logs: `/var/log/suna/migration.log`
3. Run diagnostic tools: `python -m suna.diagnostics.run`
4. Open issue with detailed error information

## 📚 Next Steps

After successful migration:

1. **Monitor Performance**: Watch system metrics and user feedback
2. **Update Documentation**: Update internal documentation
3. **Train Users**: Provide training on new features
4. **Plan Maintenance**: Schedule regular maintenance tasks
5. **Scale as Needed**: Monitor usage and scale resources

---

**Migration Complete!** 🎉

Your Suna instance has been successfully migrated from Supabase to self-hosted. The system is now running independently with full control over your data and infrastructure.







