# Security Documentation for Suna Self-Hosted Deployment

This document outlines the security measures implemented in the Suna self-hosted deployment and provides guidance for maintaining a secure environment.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Network Security](#network-security)
4. [Application Security](#application-security)
5. [Data Protection](#data-protection)
6. [Infrastructure Security](#infrastructure-security)
7. [Monitoring & Auditing](#monitoring--auditing)
8. [Security Best Practices](#security-best-practices)
9. [Incident Response](#incident-response)
10. [Compliance](#compliance)

## Security Architecture

### Defense in Depth

The Suna self-hosted deployment implements a multi-layered security approach:

1. **Network Layer**: Firewall rules, SSL/TLS encryption, VPN access
2. **Application Layer**: Input validation, rate limiting, authentication
3. **Data Layer**: Encryption at rest, secure database connections
4. **Infrastructure Layer**: Container security, file permissions, monitoring

### Security Zones

- **Public Zone**: Frontend application, public APIs
- **DMZ Zone**: Reverse proxy (nginx), load balancer
- **Application Zone**: Backend services, API endpoints
- **Data Zone**: Database, file storage, secrets
- **Management Zone**: Admin interfaces, monitoring tools

## Authentication & Authorization

### JWT Token Security

- **Token Expiration**: Configurable token lifetime (default: 24 hours)
- **Refresh Tokens**: Secure token refresh mechanism
- **Token Validation**: Server-side validation with proper signature verification
- **Token Storage**: Secure storage in HTTP-only cookies

### Password Security

#### Password Policy

```python
# Production password requirements
min_length: 16 characters
require_uppercase: True
require_lowercase: True
require_digits: True
require_special: True
max_age_days: 60
prevent_reuse: 10 previous passwords
```

#### Password Storage

- **Hashing**: bcrypt with cost factor 12
- **Salt**: Unique salt per password
- **Verification**: Constant-time comparison

### Multi-Factor Authentication (MFA)

- **TOTP Support**: Time-based one-time passwords
- **Backup Codes**: Emergency access codes
- **MFA Enforcement**: Required for admin accounts

### Role-Based Access Control (RBAC)

```python
# User roles and permissions
ROLES = {
    "user": ["read:own", "write:own", "delete:own"],
    "admin": ["read:all", "write:all", "delete:all", "admin:system"],
    "system": ["system:all"]
}
```

## Network Security

### SSL/TLS Configuration

#### Nginx SSL Settings

```nginx
# Modern SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
```

#### Security Headers

```nginx
# Security headers
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Firewall Configuration

#### UFW Rules (Ubuntu)

```bash
# Basic firewall rules
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8091/tcp  # Backend API
ufw allow 3091/tcp  # Frontend
ufw allow 5491/tcp  # PostgreSQL (restrict to internal)
ufw allow 6391/tcp  # Redis (restrict to internal)
```

#### Docker Network Security

```yaml
# Docker network isolation
networks:
  suna_network:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Application Security

### Input Validation

#### Request Validation

```python
# Pydantic models for input validation
class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', v):
            raise ValueError('Password must meet complexity requirements')
        return v
```

#### SQL Injection Prevention

- **Parameterized Queries**: All database queries use parameterized statements
- **ORM Usage**: SQLAlchemy ORM with proper escaping
- **Input Sanitization**: Regular expression validation for suspicious patterns

#### XSS Prevention

```python
# XSS protection patterns
XSS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript:",
    r"vbscript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>"
]
```

### Rate Limiting

#### API Rate Limits

```python
# Rate limiting configuration
RATE_LIMITS = {
    "/api/auth/login": {"limit": 5, "window": 300},      # 5 attempts per 5 minutes
    "/api/auth/register": {"limit": 3, "window": 3600},  # 3 attempts per hour
    "/api/admin": {"limit": 50, "window": 60},           # 50 requests per minute
    "/api/": {"limit": 100, "window": 60},               # 100 requests per minute
}
```

#### DDoS Protection

- **Request Throttling**: Per-IP rate limiting
- **Connection Limits**: Maximum concurrent connections
- **Resource Monitoring**: CPU and memory usage limits

### CORS Configuration

```python
# CORS settings
CORS_ORIGINS = [
    "https://your-domain.com",
    "https://www.your-domain.com"
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-API-Key"]
```

## Data Protection

### Encryption

#### Data at Rest

- **Database Encryption**: PostgreSQL with pgcrypto extension
- **File Storage**: Encrypted file system or encrypted volumes
- **Backup Encryption**: Encrypted backup storage

#### Data in Transit

- **TLS 1.3**: All external communications
- **Database SSL**: Encrypted database connections
- **API Encryption**: HTTPS for all API endpoints

### Database Security

#### PostgreSQL Security

```sql
-- Database security settings
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL';
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own data" ON users
    FOR ALL USING (auth.uid() = user_id);
```

#### Connection Security

```python
# Database connection with SSL
DATABASE_URL = "postgresql://user:pass@host:port/db?sslmode=require"
```

### File Storage Security

#### File Upload Security

```python
# File upload restrictions
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.doc', '.docx', '.jpg', '.png'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_PATH = "/secure/storage"
```

#### File Access Control

- **Permission-based Access**: File access based on user permissions
- **Virus Scanning**: Automated virus scanning for uploaded files
- **Quarantine**: Suspicious files are quarantined for review

## Infrastructure Security

### Container Security

#### Docker Security

```dockerfile
# Security-focused Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

#### Container Scanning

```bash
# Container vulnerability scanning
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image suna-backend:latest
```

### Environment Security

#### Secrets Management

```bash
# Environment variable security
export JWT_SECRET_KEY=$(openssl rand -base64 32)
export DATABASE_PASSWORD=$(openssl rand -base64 32)
export API_KEY_SECRET=$(openssl rand -base64 32)
```

#### File Permissions

```bash
# Secure file permissions
chmod 600 /app/.env
chmod 700 /app/data
chmod 755 /app/logs
chown -R appuser:appuser /app
```

### Network Isolation

#### Docker Networks

```yaml
# Network segmentation
networks:
  frontend_network:
    driver: bridge
  backend_network:
    driver: bridge
    internal: true
  database_network:
    driver: bridge
    internal: true
```

## Monitoring & Auditing

### Security Monitoring

#### Log Aggregation

```python
# Structured logging for security events
logger.security(
    "Authentication attempt",
    user_id=user_id,
    ip_address=client_ip,
    success=success,
    user_agent=user_agent
)
```

#### Security Event Types

- **Authentication Events**: Login attempts, password changes
- **Authorization Events**: Access denied, permission changes
- **Data Access Events**: File access, database queries
- **System Events**: Configuration changes, service restarts

### Audit Logging

#### Audit Trail

```python
# Audit log entry
audit_log = {
    "timestamp": datetime.utcnow().isoformat(),
    "user_id": user_id,
    "action": "user_created",
    "resource": "users",
    "resource_id": new_user_id,
    "ip_address": client_ip,
    "user_agent": user_agent,
    "details": {"email": email, "role": role}
}
```

#### Log Retention

- **Security Logs**: 1 year retention
- **Audit Logs**: 7 years retention
- **Application Logs**: 90 days retention
- **System Logs**: 30 days retention

### Intrusion Detection

#### Security Scanning

```bash
# Automated security scanning
python security/security_scan.py --url https://your-domain.com --output security_report.json
```

#### Vulnerability Assessment

- **Regular Scans**: Weekly automated vulnerability scans
- **Dependency Updates**: Automated dependency vulnerability checking
- **Container Scanning**: Regular container image scanning
- **Network Scanning**: Port scanning and service enumeration

## Security Best Practices

### Development Security

#### Code Security

```python
# Secure coding practices
# 1. Input validation
def validate_input(data: str) -> bool:
    if not data or len(data) > 1000:
        return False
    return not any(pattern in data.lower() for pattern in SUSPICIOUS_PATTERNS)

# 2. Secure random generation
import secrets
token = secrets.token_urlsafe(32)

# 3. Constant-time comparison
import hmac
def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
```

#### Dependency Management

```bash
# Security-focused dependency management
pip install safety
safety check
pip-audit
```

### Operational Security

#### Access Control

- **Principle of Least Privilege**: Users have minimum required permissions
- **Regular Access Reviews**: Quarterly access permission reviews
- **Account Lockout**: Automatic account lockout after failed attempts
- **Session Management**: Automatic session timeout and cleanup

#### Backup Security

```bash
# Secure backup procedures
# Encrypted backup
pg_dump $DATABASE_URL | gpg -e -r admin@company.com > backup.sql.gpg

# Secure backup storage
aws s3 cp backup.sql.gpg s3://secure-backups/ --sse aws:kms
```

### Incident Response

#### Security Incident Types

1. **Data Breach**: Unauthorized access to sensitive data
2. **Service Compromise**: Unauthorized access to services
3. **DDoS Attack**: Distributed denial of service attack
4. **Malware Infection**: Malicious software detection

#### Response Procedures

```python
# Incident response checklist
INCIDENT_RESPONSE = {
    "detection": [
        "Identify the incident type and scope",
        "Document initial findings",
        "Notify security team"
    ],
    "containment": [
        "Isolate affected systems",
        "Block malicious IP addresses",
        "Disable compromised accounts"
    ],
    "eradication": [
        "Remove malware or unauthorized access",
        "Patch vulnerabilities",
        "Update security controls"
    ],
    "recovery": [
        "Restore systems from clean backups",
        "Verify system integrity",
        "Monitor for recurrence"
    ],
    "lessons_learned": [
        "Document incident details",
        "Update security procedures",
        "Conduct post-incident review"
    ]
}
```

## Compliance

### Data Protection Regulations

#### GDPR Compliance

- **Data Minimization**: Collect only necessary data
- **Consent Management**: Clear consent mechanisms
- **Data Portability**: Export user data on request
- **Right to be Forgotten**: Delete user data on request
- **Data Breach Notification**: 72-hour notification requirement

#### Security Standards

- **OWASP Top 10**: Address all OWASP security risks
- **NIST Cybersecurity Framework**: Implement NIST security controls
- **ISO 27001**: Information security management system
- **SOC 2**: Security, availability, and confidentiality controls

### Security Documentation

#### Required Documentation

1. **Security Policy**: Overall security approach and procedures
2. **Access Control Policy**: User access management procedures
3. **Incident Response Plan**: Security incident handling procedures
4. **Data Protection Policy**: Data handling and protection procedures
5. **Change Management Policy**: System change control procedures

#### Security Training

- **Developer Training**: Secure coding practices
- **Admin Training**: Security administration procedures
- **User Training**: Security awareness and best practices
- **Regular Updates**: Quarterly security training updates

## Security Tools

### Security Scanning Tools

```bash
# Container security
trivy image suna-backend:latest

# Dependency scanning
safety check
pip-audit

# Network scanning
nmap -sV -sC target-host

# Web application scanning
owasp-zap -t https://your-domain.com
```

### Monitoring Tools

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Security dashboard visualization
- **ELK Stack**: Log aggregation and analysis
- **Falco**: Runtime security monitoring

### Security Automation

```yaml
# GitHub Actions security workflow
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run security scan
        run: python security/security_scan.py
      - name: Scan dependencies
        run: safety check
      - name: Container scan
        run: trivy image suna-backend:latest
```

## Conclusion

This security documentation provides a comprehensive framework for securing the Suna self-hosted deployment. Regular review and updates of security measures are essential to maintain a secure environment.

### Security Checklist

- [ ] SSL/TLS certificates installed and configured
- [ ] Firewall rules configured and tested
- [ ] Security headers implemented
- [ ] Rate limiting configured
- [ ] Input validation implemented
- [ ] Authentication system secured
- [ ] Database security configured
- [ ] Backup encryption enabled
- [ ] Monitoring and alerting configured
- [ ] Security scanning automated
- [ ] Incident response plan documented
- [ ] Security training completed
- [ ] Compliance requirements met

### Regular Security Tasks

- **Daily**: Review security logs and alerts
- **Weekly**: Run security scans and update dependencies
- **Monthly**: Review access permissions and security policies
- **Quarterly**: Conduct security training and penetration testing
- **Annually**: Complete security audit and compliance review

For questions or security concerns, contact the security team at security@your-domain.com.







