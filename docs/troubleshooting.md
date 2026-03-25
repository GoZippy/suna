# Suna Troubleshooting Guide

This guide provides solutions for common issues encountered during Suna self-hosted deployment and operation.

## 🔍 Quick Diagnostic Commands

### System Health Check

```bash
# Check all service status
docker-compose ps

# Check system resources
free -h
df -h
nproc

# Check port usage
sudo netstat -tulpn | grep -E ':(3091|8091|5491|6391|9091)'

# Check service logs
docker-compose logs --tail=50
```

### Service Health Verification

```bash
# Check API health
curl -f http://localhost:8091/health

# Check database connectivity
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_db():
    try:
        db = get_database()
        await db.execute('SELECT 1')
        print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
asyncio.run(check_db())
"

# Check Redis connectivity
docker-compose exec backend python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6391, password='your_redis_password')
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
```

## 🚨 Common Issues and Solutions

### 1. Service Startup Issues

#### Problem: Services won't start

**Symptoms:**
- `docker-compose up` fails
- Services show as "Exited" status
- Port conflicts in logs

**Solutions:**

```bash
# Check for port conflicts
sudo netstat -tulpn | grep -E ':(3091|8091|5491|6391|9091)'

# Kill conflicting processes
sudo kill -9 $(sudo lsof -t -i:3091)
sudo kill -9 $(sudo lsof -t -i:8091)
sudo kill -9 $(sudo lsof -t -i:5491)
sudo kill -9 $(sudo lsof -t -i:6391)
sudo kill -9 $(sudo lsof -t -i:9091)

# Restart services
docker-compose down
docker-compose up -d

# Check logs for specific errors
docker-compose logs service_name
```

#### Problem: Database connection timeout

**Symptoms:**
- Backend service fails to start
- Database connection errors in logs
- "Connection refused" messages

**Solutions:**

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Check PostgreSQL logs
docker-compose logs postgres

# Verify environment variables
docker-compose exec backend env | grep POSTGRES

# Reset database (development only)
docker-compose down -v
docker-compose up -d postgres
sleep 30
docker-compose exec backend python -m alembic upgrade head
```

#### Problem: Redis connection issues

**Symptoms:**
- Cache-related errors
- Session management failures
- Redis connection refused

**Solutions:**

```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis

# Verify Redis configuration
docker-compose exec backend python -c "
import redis
r = redis.Redis(host='localhost', port=6391, password='your_redis_password')
print(f'Redis info: {r.info()}')
"
```

### 2. Authentication Issues

#### Problem: Users can't log in

**Symptoms:**
- Login failures
- JWT token errors
- Password authentication failures

**Solutions:**

```bash
# Check JWT configuration
docker-compose exec backend python -c "
from suna.auth.jwt import verify_jwt_token
print('JWT configuration check...')
"

# Reset user password
python -m suna.cli reset-user-password \
    --email user@example.com \
    --new-password "new_password"

# Check user in database
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_user():
    db = get_database()
    result = await db.fetch_one('SELECT * FROM users WHERE email = $1', 'user@example.com')
    print(f'User found: {result is not None}')
asyncio.run(check_user())
"
```

#### Problem: Admin panel access issues

**Symptoms:**
- Can't access admin panel
- Admin login failures
- Permission denied errors

**Solutions:**

```bash
# Check admin user exists
docker-compose exec backend python -c "
import asyncio
from suna.admin.auth import AdminAuthService
async def check_admin():
    auth_service = AdminAuthService()
    admin = await auth_service.get_admin_by_email('admin@your-domain.com')
    print(f'Admin user exists: {admin is not None}')
asyncio.run(check_admin())
"

# Create admin user
docker-compose exec backend python -m suna.cli create-admin \
    --email admin@your-domain.com \
    --password admin_password \
    --role super_admin

# Check admin panel logs
docker-compose logs admin
```

### 3. Performance Issues

#### Problem: Slow response times

**Symptoms:**
- High response times
- Timeout errors
- System resource exhaustion

**Solutions:**

```bash
# Check system resources
htop
docker stats

# Check database performance
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_db_performance():
    db = get_database()
    result = await db.fetch_one('SELECT version()')
    print(f'Database version: {result[0]}')
    
    # Check slow queries
    result = await db.fetch_all('''
        SELECT query, mean_time, calls 
        FROM pg_stat_statements 
        ORDER BY mean_time DESC 
        LIMIT 5
    ''')
    print('Slow queries:', result)
asyncio.run(check_db_performance())
"

# Optimize database
docker-compose exec backend python -m suna.database.optimize \
    --analyze-tables \
    --create-indexes \
    --vacuum-tables
```

#### Problem: High memory usage

**Symptoms:**
- Out of memory errors
- System slowdown
- Container restarts

**Solutions:**

```bash
# Check memory usage
free -h
docker stats

# Optimize memory settings
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Restart services with memory limits
docker-compose down
docker-compose up -d --scale backend=1
```

### 4. File Storage Issues

#### Problem: File upload failures

**Symptoms:**
- File upload errors
- Storage permission issues
- File not found errors

**Solutions:**

```bash
# Check storage permissions
ls -la /opt/suna/storage
sudo chown -R suna:suna /opt/suna/storage
sudo chmod -R 755 /opt/suna/storage

# Check storage space
df -h /opt/suna/storage

# Verify file paths in database
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_files():
    db = get_database()
    files = await db.fetch_all('SELECT file_path FROM files LIMIT 5')
    for file in files:
        import os
        exists = os.path.exists(file['file_path'])
        print(f'File {file[\"file_path\"]}: {\"✅\" if exists else \"❌\"}')
asyncio.run(check_files())
"
```

#### Problem: File access issues

**Symptoms:**
- 404 errors for files
- Broken file links
- Permission denied errors

**Solutions:**

```bash
# Check Nginx configuration
sudo nginx -t
sudo systemctl reload nginx

# Check file server logs
docker-compose logs nginx

# Verify file server configuration
curl -I http://localhost/storage/test-file
```

### 5. Network and Connectivity Issues

#### Problem: External access issues

**Symptoms:**
- Can't access from external network
- DNS resolution problems
- SSL certificate issues

**Solutions:**

```bash
# Check firewall settings
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3091/tcp
sudo ufw allow 8091/tcp
sudo ufw allow 9091/tcp

# Check DNS resolution
nslookup your-domain.com
dig your-domain.com

# Check SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Test local access
curl -f http://localhost:3091
curl -f http://localhost:8091/health
```

#### Problem: Internal service communication issues

**Symptoms:**
- Service-to-service communication failures
- Network timeout errors
- Connection refused between containers

**Solutions:**

```bash
# Check Docker network
docker network ls
docker network inspect suna_default

# Test inter-service communication
docker-compose exec backend curl -f http://postgres:5491
docker-compose exec backend curl -f http://redis:6391

# Check service discovery
docker-compose exec backend nslookup postgres
docker-compose exec backend nslookup redis
```

### 6. Monitoring and Logging Issues

#### Problem: Prometheus not collecting metrics

**Symptoms:**
- No metrics in Prometheus
- Target down errors
- Missing service metrics

**Solutions:**

```bash
# Check Prometheus status
curl http://localhost:9090/-/healthy

# Check targets
curl http://localhost:9090/api/v1/targets

# Check Prometheus configuration
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml

# Restart Prometheus
docker-compose restart prometheus
```

#### Problem: Grafana dashboard issues

**Symptoms:**
- Can't access Grafana
- Dashboard errors
- Missing data sources

**Solutions:**

```bash
# Check Grafana status
curl http://localhost:3000/api/health

# Check Grafana logs
docker-compose logs grafana

# Reset Grafana admin password
docker-compose exec grafana grafana-cli admin reset-admin-password new_password

# Import dashboards
# See: docs/monitoring-setup.md
```

### 7. Migration Issues

#### Problem: Data import failures

**Symptoms:**
- Migration script errors
- Data corruption
- Missing data after migration

**Solutions:**

```bash
# Check migration logs
tail -f /var/log/suna/migration.log

# Verify data integrity
python -m suna.migration.validate_migration \
    --source-data ./migration_data \
    --target-database "postgresql://suna_user:password@localhost:5491/suna" \
    --check-users \
    --check-agents \
    --check-workflows \
    --check-files

# Fix encoding issues
python -m suna.migration.fix_encoding \
    --input-file problematic_file.csv \
    --output-file fixed_file.csv \
    --encoding utf-8

# Retry migration
python -m suna.migration.import_data \
    --input-dir ./migration_data \
    --database-url "postgresql://suna_user:password@localhost:5491/suna" \
    --redis-url "redis://:password@localhost:6391/0" \
    --transform-passwords \
    --validate-data
```

#### Problem: Password migration issues

**Symptoms:**
- Users can't log in after migration
- Password hash errors
- Authentication failures

**Solutions:**

```bash
# Check password hashing
docker-compose exec backend python -c "
import bcrypt
password = 'testpassword'
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f'Password hash: {hashed}')
"

# Reset all user passwords
python -m suna.cli force-password-reset --all-users

# Check user authentication
docker-compose exec backend python -c "
import asyncio
from suna.auth.service import AuthService
async def test_auth():
    auth_service = AuthService()
    user = await auth_service.authenticate_user('user@example.com', 'password')
    print(f'Authentication result: {user is not None}')
asyncio.run(test_auth())
"
```

## 🔧 Advanced Troubleshooting

### Database Debugging

```bash
# Check database connections
docker-compose exec postgres psql -U suna_user -d suna -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
"

# Check slow queries
docker-compose exec postgres psql -U suna_user -d suna -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# Check table sizes
docker-compose exec postgres psql -U suna_user -d suna -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
"
```

### Performance Analysis

```bash
# Check system performance
docker-compose exec backend python -c "
import psutil
print(f'CPU Usage: {psutil.cpu_percent()}%')
print(f'Memory Usage: {psutil.virtual_memory().percent}%')
print(f'Disk Usage: {psutil.disk_usage(\"/\").percent}%')
"

# Check application performance
docker-compose exec backend python -c "
import asyncio
import time
from suna.database import get_database

async def performance_test():
    db = get_database()
    start_time = time.time()
    
    # Test database query performance
    result = await db.fetch_all('SELECT * FROM users LIMIT 100')
    
    end_time = time.time()
    print(f'Query time: {end_time - start_time:.3f} seconds')
    print(f'Results: {len(result)} rows')

asyncio.run(performance_test())
"
```

### Security Analysis

```bash
# Check for security vulnerabilities
python -m suna.security.scan \
    --target localhost \
    --ports 3091,8091,9091 \
    --check-vulnerabilities \
    --generate-report

# Check SSL/TLS configuration
openssl s_client -connect localhost:443 -servername your-domain.com

# Check security headers
curl -I http://localhost:8091/health

# Run security tests
python -m pytest tests/security/test_security.py -v
```

## 📊 Diagnostic Tools

### System Information Collection

```bash
# Collect system information
python -m suna.diagnostics.collect_info \
    --output-file system_info.json \
    --include-logs \
    --include-configs \
    --include-metrics

# Generate diagnostic report
python -m suna.diagnostics.generate_report \
    --input-file system_info.json \
    --output-file diagnostic_report.html
```

### Log Analysis

```bash
# Analyze error patterns
python -m suna.diagnostics.analyze_logs \
    --log-file /var/log/suna/application.log \
    --error-patterns \
    --frequency-analysis \
    --generate-report

# Search for specific errors
grep -i "error\|exception\|failed" /var/log/suna/*.log | tail -20
```

## 🆘 Getting Help

### Before Seeking Help

1. **Collect Information:**
   ```bash
   # System information
   uname -a
   docker --version
   docker-compose --version
   
   # Service status
   docker-compose ps
   docker-compose logs --tail=100
   
   # Configuration
   cat .env
   docker-compose config
   ```

2. **Reproduce the Issue:**
   - Document exact steps to reproduce
   - Note any error messages
   - Check if issue is consistent

3. **Check Recent Changes:**
   - Review recent deployments
   - Check configuration changes
   - Verify environment changes

### Support Resources

1. **Documentation:**
   - [Installation Guide](installation.md)
   - [Migration Guide](migration.md)
   - [API Reference](api-reference.md)

2. **Community Support:**
   - GitHub Issues
   - Community Forums
   - Discord/Slack Channels

3. **Professional Support:**
   - Enterprise Support (if applicable)
   - Consulting Services
   - Training Programs

### Issue Reporting Template

When reporting issues, include:

```markdown
## Issue Description
Brief description of the problem

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 20.04]
- Docker Version: [e.g., 20.10.21]
- Suna Version: [e.g., v1.0.0]
- Hardware: [e.g., 8GB RAM, 4 cores]

## Logs
```
[Paste relevant logs here]
```

## Configuration
```
[Paste relevant configuration]
```

## Additional Information
Any other relevant details
```

---

**Need More Help?**

If you can't find a solution in this guide:

1. Check the [FAQ](faq.md) for common questions
2. Search existing [GitHub Issues](https://github.com/your-org/suna/issues)
3. Open a new issue with detailed information
4. Contact support with your diagnostic report







