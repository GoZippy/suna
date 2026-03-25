# Suna Administration and Management System

This directory contains the comprehensive administration and management system for the Suna self-hosted platform. The admin system provides web-based interfaces, CLI tools, and APIs for system administration, monitoring, and maintenance.

## 🏗️ System Architecture

The admin system consists of several key components:

```
admin/
├── __init__.py          # Package initialization and configuration
├── models.py           # Pydantic data models
├── auth.py             # Authentication and authorization
├── monitoring.py       # System monitoring and health checks
├── api.py              # FastAPI endpoints
├── cli.py              # Command-line interface
└── README.md           # This documentation
```

## 🔐 Authentication & Authorization

### Admin User Roles

The system supports three levels of administrative access:

| Role | Permissions | Description |
|------|-------------|-------------|
| **Super Admin** | All permissions | Full system access including configuration changes |
| **Admin** | User management, service control, log analysis, performance monitoring | System administration access |
| **Operator** | Log analysis, performance monitoring | Basic operational access |

### Permissions

- **user_management**: Create, update, delete admin users
- **system_configuration**: Modify system configuration
- **service_control**: Start, stop, restart services
- **log_analysis**: View and search system logs
- **backup_restore**: Create and restore backups
- **security_management**: Security-related operations
- **performance_monitoring**: Access performance metrics
- **database_management**: Database administration

## 🌐 Web-Based Admin Panel

### API Endpoints

The admin system provides RESTful API endpoints for all administrative functions:

#### Authentication
- `POST /admin/login` - Admin login
- `POST /admin/logout` - Admin logout
- `GET /admin/me` - Get current admin user info

#### Dashboard
- `GET /admin/dashboard` - Get comprehensive dashboard data
- `GET /admin/dashboard/system-metrics` - System metrics
- `GET /admin/dashboard/services` - Service health status
- `GET /admin/dashboard/system-health` - Overall system health
- `GET /admin/dashboard/alerts` - System alerts

#### User Management
- `POST /admin/users` - Create admin user
- `GET /admin/users` - List admin users
- `GET /admin/users/{user_id}` - Get specific user
- `PUT /admin/users/{user_id}` - Update user
- `DELETE /admin/users/{user_id}` - Delete user
- `GET /admin/users/stats` - User management statistics

#### Service Control
- `POST /admin/services/{service_id}/control` - Control service (start/stop/restart)
- `GET /admin/services/{service_id}/logs` - Get service logs

#### Configuration
- `GET /admin/config` - List system configuration
- `PUT /admin/config/{key}` - Update configuration

#### Audit & Logs
- `GET /admin/audit-logs` - Get admin audit logs

### Usage Examples

#### Login and Get Dashboard Data

```bash
# Login
curl -X POST "http://localhost:9091/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# Use token to access dashboard
curl -X GET "http://localhost:9091/admin/dashboard" \
  -H "Authorization: Bearer <token>"
```

#### Service Control

```bash
# Restart backend service
curl -X POST "http://localhost:9091/admin/services/backend/control" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart",
    "force": false
  }'
```

#### User Management

```bash
# Create new admin user
curl -X POST "http://localhost:9091/admin/users" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newadmin",
    "email": "newadmin@example.com",
    "password": "securepassword",
    "role": "admin",
    "full_name": "New Administrator"
  }'
```

## 💻 Command-Line Interface

The admin system includes a comprehensive CLI tool for system administration:

### Installation

```bash
# Make CLI executable
chmod +x admin/cli.py

# Create symlink for easy access
ln -s admin/cli.py /usr/local/bin/suna-admin
```

### Basic Usage

```bash
# Show help
suna-admin --help

# Check system status
suna-admin system status

# List all services
suna-admin services list

# Check specific service
suna-admin services status backend

# Restart service
suna-admin services restart backend
```

### Command Categories

#### System Management

```bash
# System status
suna-admin system status
suna-admin system status --json

# System metrics
suna-admin system metrics
suna-admin system metrics --json

# System health
suna-admin system health
suna-admin system health --json
```

#### Service Management

```bash
# List all services
suna-admin services list
suna-admin services list --json

# Check service status
suna-admin services status backend
suna-admin services status backend --json

# Service control
suna-admin services start backend
suna-admin services stop backend
suna-admin services restart backend
suna-admin services reload backend
```

#### User Management

```bash
# List admin users
suna-admin users list
suna-admin users list --json

# Create admin user
suna-admin users create \
  --username newadmin \
  --email newadmin@example.com \
  --password securepass \
  --role admin \
  --full-name "New Administrator"

# Update user
suna-admin users update \
  --user-id <user-id> \
  --email updated@example.com \
  --role admin

# Delete user
suna-admin users delete --user-id <user-id>
```

#### Log Management

```bash
# Show service logs
suna-admin logs show backend
suna-admin logs show backend --lines 50
suna-admin logs show backend --follow

# Search logs
suna-admin logs search backend "error"
suna-admin logs search backend "authentication" --lines 20
```

#### Backup Management

```bash
# Create backup
suna-admin backup create --type full
suna-admin backup create --type database --output /backups/db.sql

# List backups
suna-admin backup list
suna-admin backup list --json

# Restore backup
suna-admin backup restore <backup-id>
suna-admin backup restore <backup-id> --force
```

#### Configuration Management

```bash
# Get configuration
suna-admin config get admin_port
suna-admin config get session_timeout

# Set configuration
suna-admin config set admin_port 9091
suna-admin config set session_timeout 7200

# List all configuration
suna-admin config list
suna-admin config list --json
```

## 📊 System Monitoring

### Monitored Services

The admin system monitors all Suna services:

| Service | Port | Health Endpoint | Description |
|---------|------|-----------------|-------------|
| Frontend | 3091 | `/health` | Next.js frontend application |
| Backend | 8091 | `/health` | FastAPI backend API |
| PostgreSQL | 5491 | N/A | Database server |
| Redis | 6391 | N/A | Cache and session store |
| Ollama | 11434 | `/api/tags` | Local LLM service |
| Prometheus | 9090 | `/-/healthy` | Metrics collection |
| Grafana | 3000 | `/api/health` | Monitoring dashboard |
| Nginx | 80 | `/health` | Reverse proxy |

### Metrics Collected

#### System Metrics
- CPU usage percentage
- Memory usage percentage
- Disk usage percentage
- Network I/O (bytes received/sent)
- Load average (1m, 5m, 15m)
- System uptime

#### Application Metrics
- Request rate (requests per second)
- Response time (average, p95, p99)
- Error rate percentage
- Active users count
- Total requests and errors

#### Database Metrics
- Connection count (total, active, idle)
- Query performance (average response time)
- Slow queries count
- Cache hit rate
- Database size and table count

### Health Checks

The system performs regular health checks on all services:

1. **Port Availability**: Check if service port is listening
2. **Health Endpoint**: Call service health endpoint if available
3. **Response Time**: Measure response time for health checks
4. **Version Information**: Extract service version from responses

### Alert System

The monitoring system generates alerts based on:

#### System Alerts
- **Critical**: CPU > 90%, Memory > 90%, Disk > 95%
- **Warning**: CPU > 80%, Memory > 80%, Disk > 85%

#### Service Alerts
- **Critical**: Service down (not responding)
- **Warning**: Service degraded (slow response)

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PORT` | `9091` | Admin panel port |
| `ADMIN_HOST` | `0.0.0.0` | Admin panel host |
| `ADMIN_SECRET` | `admin-secret-key-change-in-production` | JWT secret key |
| `ADMIN_SESSION_TIMEOUT` | `3600` | Session timeout in seconds |
| `ADMIN_MAX_LOGIN_ATTEMPTS` | `5` | Max login attempts before lockout |
| `ADMIN_LOG_RETENTION_DAYS` | `30` | Log retention period |
| `ADMIN_BACKUP_RETENTION_DAYS` | `7` | Backup retention period |
| `ADMIN_HEALTH_CHECK_INTERVAL` | `60` | Health check interval in seconds |
| `ADMIN_DASHBOARD_REFRESH` | `30` | Dashboard refresh interval |

### Service Configuration

Each service is configured with:

```python
{
    'name': 'Service Display Name',
    'port': 8091,
    'health_endpoint': '/health',
    'restart_command': 'docker-compose restart service',
    'log_file': '/var/log/suna/service.log'
}
```

## 🛡️ Security Features

### Authentication Security
- JWT token-based authentication
- Password hashing with bcrypt
- Account lockout after failed attempts
- Session timeout management
- IP address and user agent tracking

### Authorization Security
- Role-based access control (RBAC)
- Permission-based endpoint protection
- Resource-level access control
- Audit logging for all actions

### Input Validation
- Pydantic model validation
- SQL injection prevention
- XSS protection
- Command injection prevention

### Audit Logging
- All admin actions logged
- User authentication events
- Service control operations
- Configuration changes
- Security events

## 📈 Performance Monitoring

### Real-time Metrics
- Live system metrics collection
- Service health monitoring
- Performance trend analysis
- Resource utilization tracking

### Historical Data
- Metrics history storage
- Performance trend analysis
- Capacity planning data
- Troubleshooting support

### Alerting
- Real-time alert generation
- Configurable thresholds
- Multiple alert levels (critical, warning, info)
- Alert acknowledgment system

## 🔄 Backup & Recovery

### Backup Types
- **Database Backup**: PostgreSQL database dump
- **File Backup**: Application files and uploads
- **Full Backup**: Complete system backup

### Backup Features
- Automated backup scheduling
- Backup verification
- Compression and encryption
- Retention policy management
- Cloud storage integration

### Recovery Procedures
- Point-in-time recovery
- Selective restore options
- Backup validation
- Rollback procedures

## 🚀 Deployment

### Docker Integration

The admin system is designed to work with Docker Compose:

```yaml
admin:
  build: ./backend
  ports:
    - "9091:9091"
  environment:
    - ADMIN_PORT=9091
    - ADMIN_SECRET=${ADMIN_SECRET}
  volumes:
    - ./logs:/var/log/suna
  depends_on:
    - postgres
    - redis
```

### Production Setup

1. **Set Environment Variables**:
   ```bash
   export ADMIN_SECRET="your-secure-secret-key"
   export ADMIN_PORT=9091
   ```

2. **Create Initial Admin User**:
   ```bash
   suna-admin users create \
     --username admin \
     --email admin@example.com \
     --password securepassword \
     --role super_admin \
     --full-name "System Administrator"
   ```

3. **Start Admin Service**:
   ```bash
   docker-compose up -d admin
   ```

4. **Access Admin Panel**:
   - Web Interface: http://localhost:9091
   - API Documentation: http://localhost:9091/docs

## 🛠️ Troubleshooting

### Common Issues

#### Service Not Responding
```bash
# Check service status
suna-admin services status <service-name>

# Check service logs
suna-admin logs show <service-name>

# Restart service
suna-admin services restart <service-name>
```

#### High Resource Usage
```bash
# Check system metrics
suna-admin system metrics

# Check system health
suna-admin system health

# Check service performance
suna-admin services list
```

#### Authentication Issues
```bash
# Check admin users
suna-admin users list

# Reset user password
suna-admin users update --user-id <id> --password <new-password>

# Check audit logs
curl -H "Authorization: Bearer <token>" \
  "http://localhost:9091/admin/audit-logs"
```

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=debug
```

### Health Check

Test admin system health:

```bash
curl http://localhost:9091/admin/health
```

## 📚 API Documentation

The admin API includes comprehensive OpenAPI documentation available at:

- **Swagger UI**: http://localhost:9091/docs
- **ReDoc**: http://localhost:9091/redoc
- **OpenAPI JSON**: http://localhost:9091/openapi.json

## 🔗 Integration

### External Monitoring
- Prometheus metrics endpoint
- Grafana dashboard integration
- SNMP monitoring support
- Webhook notifications

### External Tools
- Ansible playbook integration
- Terraform provider support
- CI/CD pipeline integration
- Third-party monitoring tools

## 📄 License

This admin system is part of the Suna project and follows the same licensing terms.

## 🤝 Contributing

When contributing to the admin system:

1. Follow the established code patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Include audit logging for security-sensitive operations
5. Follow security best practices
6. Add proper error handling and validation







