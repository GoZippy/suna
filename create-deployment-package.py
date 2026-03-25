#!/usr/bin/env python3
"""
Deployment Package Creator

This script creates deployment packages and release artifacts
for the self-hosted Suna system.
"""

import os
import sys
import shutil
import zipfile
import tarfile
from pathlib import Path
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeploymentPackageCreator:
    """Creates deployment packages and release artifacts."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.output_dir = self.base_path / "dist"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.version = "1.0.0"  # You can read this from a version file

    def create_output_directory(self):
        """Create output directory for packages."""
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Created output directory: {self.output_dir}")

    def create_docker_deployment_package(self):
        """Create Docker-based deployment package."""
        logger.info("Creating Docker deployment package...")

        package_name = f"suna-self-hosted-docker-{self.version}-{self.timestamp}"
        package_dir = self.output_dir / package_name

        # Create package directory
        package_dir.mkdir(exist_ok=True)

        # Files to include
        files_to_copy = [
            "docker-compose.self-hosted.yml",
            "docker-compose.production.yml",
            "docker-compose.development.yml",
            "self-hosted.env.example",
            ".env.example",
            "README.md",
            "SELF-HOSTED-README.md",
            "DEPLOYMENT.md",
            "MIGRATION_GUIDE.md",
            "SECURITY.md",
            "monitoring/prometheus.yml",
            "monitoring/grafana/provisioning/datasources/prometheus.yml",
            "monitoring/grafana/provisioning/dashboards/dashboard.yml",
            "monitoring/grafana/dashboards/suna-dashboard.json",
            "monitoring/alertmanager.yml",
            "scripts/backup-database.sh",
            "scripts/restore-database.sh",
            "scripts/rollback-migration.sh",
            "migration/migrate_config.py",
            "migration/migrate.py",
            "migration/README.md",
            "services/search/docker-compose.yml",
            "services/search/searxng/settings.yml",
            "database/init/01_extensions.sql",
            "database/init/02_users_auth.sql",
            "database/init/03_projects_threads.sql",
            "database/init/04_knowledge_base.sql",
            "database/init/05_usage_tracking.sql",
            "database/init/06_system_config.sql",
            "backend/database/migrations/001_create_auth_tables.sql",
            "backend/database/migrations/002_create_vector_tables.sql",
            "backend/database/migrations/003_add_credit_system.sql"
        ]

        # Copy files
        for file_path in files_to_copy:
            src = self.base_path / file_path
            if src.exists():
                dst = package_dir / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.copy2(src, dst)
                    logger.debug(f"Copied: {file_path}")
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    logger.debug(f"Copied directory: {file_path}")
            else:
                logger.warning(f"File not found: {file_path}")

        # Create deployment script
        self.create_deployment_script(package_dir)

        # Create configuration template
        self.create_config_template(package_dir)

        # Create archive
        archive_name = f"{package_name}.zip"  # Use zip instead of tar.gz for Windows compatibility
        archive_path = self.output_dir / archive_name

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.relative_to(package_dir))

        logger.info(f"Created Docker deployment package: {archive_path}")
        return archive_path

    def create_kubernetes_deployment_package(self):
        """Create Kubernetes deployment package."""
        logger.info("Creating Kubernetes deployment package...")

        package_name = f"suna-self-hosted-k8s-{self.version}-{self.timestamp}"
        package_dir = self.output_dir / package_name

        # Create package directory
        package_dir.mkdir(exist_ok=True)

        # Create Kubernetes manifests
        k8s_dir = package_dir / "k8s"
        k8s_dir.mkdir(exist_ok=True)

        # Generate Kubernetes manifests
        manifests = {
            "namespace.yml": self.generate_namespace_manifest(),
            "configmap.yml": self.generate_configmap_manifest(),
            "secrets.yml": self.generate_secrets_manifest(),
            "postgres.yml": self.generate_postgres_manifest(),
            "redis.yml": self.generate_redis_manifest(),
            "backend.yml": self.generate_backend_manifest(),
            "frontend.yml": self.generate_frontend_manifest(),
            "ingress.yml": self.generate_ingress_manifest(),
            "monitoring.yml": self.generate_monitoring_manifest()
        }

        for filename, content in manifests.items():
            manifest_path = k8s_dir / filename
            with open(manifest_path, 'w') as f:
                f.write(content)

        # Create Helm chart
        helm_dir = package_dir / "helm"
        helm_dir.mkdir(exist_ok=True)

        # Create basic Helm structure
        chart_yaml = f"""apiVersion: v2
name: suna
description: Self-hosted AI Worker Platform
type: application
version: {self.version}
appVersion: "{self.version}"
"""

        with open(helm_dir / "Chart.yaml", 'w') as f:
            f.write(chart_yaml)

        # Create Helm values file
        values_yaml = self.generate_helm_values()
        with open(helm_dir / "values.yaml", 'w') as f:
            f.write(values_yaml)

        # Create archive
        archive_name = f"{package_name}.zip"
        archive_path = self.output_dir / archive_name

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.relative_to(package_dir))

        logger.info(f"Created Kubernetes deployment package: {archive_path}")
        return archive_path

    def create_deployment_script(self, package_dir: Path):
        """Create deployment script for Docker package."""
        script_content = """#!/bin/bash
# Suna Self-Hosted Deployment Script

set -e

echo "Starting Suna Self-Hosted Deployment"

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating environment configuration..."
    cp self-hosted.env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing"
    echo "   Press Enter to continue or Ctrl+C to exit"
    read
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p backups
mkdir -p logs
mkdir -p data

# Start services
echo "🐳 Starting Docker services..."
docker-compose -f docker-compose.self-hosted.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose -f docker-compose.self-hosted.yml exec -T backend python -m migration.migrate

# Create admin user
echo "👤 Creating admin user..."
docker-compose -f docker-compose.self-hosted.yml exec -T backend python -c "
from backend.database.init_auth import create_admin_user
import asyncio
asyncio.run(create_admin_user())
"

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access your Suna instance at:"
echo "   Frontend: http://localhost:3091"
echo "   Backend API: http://localhost:8091"
echo "   MailHog: http://localhost:8091"
echo "   Grafana: http://localhost:3191 (admin/admin)"
echo ""
echo "📚 Next steps:"
echo "   1. Update your DNS to point to this server"
echo "   2. Configure SSL certificates"
echo "   3. Set up backups"
echo "   4. Review security settings"
"""

        script_path = package_dir / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make script executable
        try:
            os.chmod(script_path, 0o755)
        except:
            pass  # Skip on Windows

    def create_config_template(self, package_dir: Path):
        """Create configuration template."""
        config_content = """# Suna Self-Hosted Configuration Template

# Database Configuration
POSTGRES_PASSWORD=your_secure_db_password_here
POSTGRES_USER=suna
POSTGRES_DB=suna

# Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_here_change_this
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_secure_admin_password_here

# External Services (Optional)
SMTP_HOST=your_smtp_host
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password

# Monitoring
GRAFANA_PASSWORD=your_secure_grafana_password

# AI Services (Optional)
OLLAMA_HOST=http://ollama:11434

# Network Configuration
EXTERNAL_DOMAIN=yourdomain.com
SSL_CERT_PATH=/path/to/ssl/cert.pem
SSL_KEY_PATH=/path/to/ssl/private.key

# Security
SECRET_KEY=your_django_secret_key_here
ALLOWED_HOSTS=yourdomain.com,localhost,127.0.0.1

# File Storage
UPLOAD_PATH=/opt/suna/uploads
BACKUP_PATH=/opt/suna/backups
"""

        config_path = package_dir / "config.env.template"
        with open(config_path, 'w') as f:
            f.write(config_content)

    def generate_namespace_manifest(self) -> str:
        """Generate Kubernetes namespace manifest."""
        return """apiVersion: v1
kind: Namespace
metadata:
  name: suna
  labels:
    name: suna
"""

    def generate_configmap_manifest(self) -> str:
        """Generate Kubernetes ConfigMap manifest."""
        return """apiVersion: v1
kind: ConfigMap
metadata:
  name: suna-config
  namespace: suna
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: '["http://localhost:3000", "https://yourdomain.com"]'
"""

    def generate_secrets_manifest(self) -> str:
        """Generate Kubernetes Secrets manifest."""
        return """apiVersion: v1
kind: Secret
metadata:
  name: suna-secrets
  namespace: suna
type: Opaque
data:
  # Base64 encoded values - replace with your own
  postgres-password: eW91cl9zZWN1cmVfZGF0YWJhc2VfcGFzc3dvcmQ=  # your_secure_database_password
  jwt-secret-key: eW91cl9zdXBlcl9zZWNyZXRfam9kX2tleQ==  # your_super_secret_jwt_key
  admin-password: eW91cl9zZWN1cmVfYWRtaW5fcGFzc3dvcmQ=  # your_secure_admin_password
"""

    def generate_postgres_manifest(self) -> str:
        """Generate PostgreSQL deployment manifest."""
        return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: suna
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: pgvector/pgvector:pg16
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "suna"
        - name: POSTGRES_USER
          value: "suna"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: suna-secrets
              key: postgres-password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: suna
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: suna
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
"""

    def generate_redis_manifest(self) -> str:
        """Generate Redis deployment manifest."""
        return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: suna
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:8-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server", "--appendonly", "yes", "--maxmemory", "8gb", "--maxmemory-policy", "allkeys-lru"]
        volumeMounts:
        - name: redis-storage
          mountPath: /data
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: suna
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: suna
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
"""

    def generate_backend_manifest(self) -> str:
        """Generate backend deployment manifest."""
        return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: suna
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/suna-ai/suna-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          value: "postgresql://suna:$(POSTGRES_PASSWORD)@postgres:5432/suna"
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: suna-secrets
              key: jwt-secret-key
        volumeMounts:
        - name: backend-storage
          mountPath: /app/uploads
      volumes:
      - name: backend-storage
        persistentVolumeClaim:
          claimName: backend-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: suna
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-pvc
  namespace: suna
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
"""

    def generate_frontend_manifest(self) -> str:
        """Generate frontend deployment manifest."""
        return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: suna
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: ghcr.io/suna-ai/suna-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: NEXT_PUBLIC_API_URL
          value: "http://backend:8000"

---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: suna
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
"""

    def generate_ingress_manifest(self) -> str:
        """Generate Ingress manifest."""
        return """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: suna-ingress
  namespace: suna
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: suna-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
"""

    def generate_monitoring_manifest(self) -> str:
        """Generate monitoring manifests."""
        return """# Prometheus and Grafana manifests would go here
# This is a placeholder for the full monitoring setup
"""

    def generate_helm_values(self) -> str:
        """Generate Helm values file."""
        return """# Suna Helm Chart Values

# Global configuration
global:
  imageRegistry: ghcr.io
  imagePullSecrets: []

# PostgreSQL configuration
postgresql:
  enabled: true
  auth:
    postgresPassword: "your_secure_db_password"
    username: "suna"
    password: "your_secure_db_password"
    database: "suna"
  architecture: standalone
  primary:
    persistence:
      enabled: true
      size: 50Gi

# Redis configuration
redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: false
  master:
    persistence:
      enabled: true
      size: 10Gi

# Backend configuration
backend:
  image:
    repository: suna-ai/suna-backend
    tag: latest
  replicaCount: 2
  env:
    - name: ENVIRONMENT
      value: "production"
    - name: LOG_LEVEL
      value: "INFO"
  persistence:
    enabled: true
    size: 100Gi

# Frontend configuration
frontend:
  image:
    repository: suna-ai/suna-frontend
    tag: latest
  replicaCount: 2
  env:
    - name: NODE_ENV
      value: "production"

# Ingress configuration
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: suna-tls
      hosts:
        - yourdomain.com

# Monitoring
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
    adminPassword: "your_secure_grafana_password"
"""

    def create_installation_guide(self):
        """Create comprehensive installation guide."""
        logger.info("Creating installation guide...")

        guide_content = f"""# Suna Self-Hosted Installation Guide

## Overview

This guide provides step-by-step instructions for deploying Suna AI Worker in a self-hosted environment.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- At least 8GB RAM
- At least 50GB free disk space
- Linux/Windows/MacOS host system

## Quick Start (Docker Compose)

1. **Download and extract the deployment package**
   ```bash
   tar -xzf suna-self-hosted-docker-{self.version}-{self.timestamp}.tar.gz
   cd suna-self-hosted-docker-{self.version}-{self.timestamp}
   ```

2. **Configure environment**
   ```bash
   cp config.env.template .env
   # Edit .env with your configuration
   nano .env
   ```

3. **Deploy Suna**
   ```bash
   ./deploy.sh
   ```

4. **Access your instance**
   - Frontend: http://localhost:3091
   - Backend API: http://localhost:8091
   - MailHog: http://localhost:8091
   - Grafana: http://localhost:3191

## Production Deployment

### Security Considerations

1. **Change default passwords** in `.env` file
2. **Configure SSL certificates** for HTTPS
3. **Set up firewall rules** to restrict access
4. **Enable database backups** using the provided scripts
5. **Configure monitoring** and alerting

### Performance Tuning

1. **Database optimization**
   - Adjust PostgreSQL memory settings based on your server
   - Configure connection pooling
   - Set up proper indexing

2. **Redis configuration**
   - Adjust memory limits based on available RAM
   - Configure persistence settings

3. **Container resources**
   - Set CPU and memory limits for containers
   - Configure health checks and restart policies

### Networking

1. **Domain configuration**
   - Point your domain to the server IP
   - Update CORS settings in environment variables

2. **SSL/TLS setup**
   - Obtain SSL certificates (Let's Encrypt recommended)
   - Configure reverse proxy for SSL termination

## Migration from Supabase

If migrating from an existing Supabase instance:

1. **Export data** from Supabase
2. **Deploy Suna** using the Docker method above
3. **Run migration scripts**
   ```bash
   python migration/migrate.py
   ```
4. **Validate data integrity**
5. **Update DNS** to point to new instance

## Troubleshooting

### Common Issues

1. **Port conflicts**
   - Check if ports 3091, 8091, 5491, 6391 are available
   - Modify port mappings in docker-compose.yml if needed

2. **Database connection issues**
   - Verify PostgreSQL container is running
   - Check database credentials in .env file
   - Review database logs: `docker-compose logs postgres`

3. **Memory issues**
   - Increase Docker memory limits
   - Reduce Ollama model size or disable local LLM
   - Monitor resource usage with `docker stats`

### Logs and Monitoring

- **Application logs**: `docker-compose logs backend`
- **Database logs**: `docker-compose logs postgres`
- **Monitoring**: Access Grafana at http://localhost:3191

## Support

For support and questions:
- Documentation: https://docs.suna.ai
- Community: https://community.suna.ai
- Issues: https://github.com/suna-ai/suna/issues

## Security Checklist

- [ ] Changed all default passwords
- [ ] Configured SSL certificates
- [ ] Set up firewall rules
- [ ] Enabled database backups
- [ ] Configured monitoring and alerting
- [ ] Reviewed file permissions
- [ ] Set up log rotation
- [ ] Configured backup encryption

## Performance Checklist

- [ ] Adjusted database memory settings
- [ ] Configured Redis memory limits
- [ ] Set container resource limits
- [ ] Enabled compression
- [ ] Configured caching
- [ ] Set up CDN for static assets
"""

        guide_path = self.output_dir / f"INSTALLATION_GUIDE_{self.version}.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)

        logger.info(f"Created installation guide: {guide_path}")

    def create_release_notes(self):
        """Create release notes."""
        logger.info("Creating release notes...")

        notes_content = f"""# Suna Self-Hosted v{self.version} Release Notes

## Overview

Suna v{self.version} is a complete self-hosted AI Worker platform that provides all the functionality of the cloud version while giving you full control over your data and infrastructure.

## What's New

### 🚀 Major Features

- **Complete Self-Hosted Stack**: PostgreSQL, Redis, Ollama, SearXNG, and more
- **Docker Compose Deployment**: Easy one-command deployment
- **Kubernetes Support**: Helm charts for production deployments
- **Migration Tools**: Seamless migration from Supabase
- **Monitoring & Observability**: Prometheus, Grafana, and comprehensive logging
- **Security Hardening**: SSL, authentication, and access controls

### 🔧 Technical Improvements

- **Vector Database**: Integrated pgvector for AI embeddings
- **Background Jobs**: Redis-based job queue with Dramatiq
- **WebSocket Support**: Real-time communication for collaborative features
- **File Storage**: Local file storage with organization and versioning
- **Email System**: Local SMTP with MailHog for development
- **Search Services**: Local metasearch with SearXNG and scraping

### 📊 Performance

- **Database Optimization**: Connection pooling and query optimization
- **Caching**: Redis-based caching for improved performance
- **Resource Management**: Container resource limits and health checks
- **Scalability**: Support for multiple concurrent users

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 8GB
- **Storage**: 50GB
- **OS**: Linux, Windows, or macOS

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: 100Mbps+ connection

## Installation

See the [Installation Guide](INSTALLATION_GUIDE_{self.version}.md) for detailed instructions.

## Migration Guide

For users migrating from Supabase, see the [Migration Guide](MIGRATION_GUIDE.md).

## Known Issues

- WebSocket connections may require additional configuration in production
- GPU acceleration requires NVIDIA Docker runtime
- Some third-party integrations may require additional setup

## Security Considerations

- Change all default passwords before deployment
- Configure SSL certificates for production use
- Set up proper firewall rules
- Enable database backups and monitoring
- Review and adjust file permissions

## Support

- **Documentation**: Comprehensive guides and API reference
- **Community**: Active community support
- **Enterprise**: Professional support available

## Changelog

### v{self.version} ({datetime.now().strftime('%Y-%m-%d')})

#### Added
- Complete self-hosted deployment packages
- Docker Compose and Kubernetes configurations
- Migration tools and documentation
- Monitoring and observability stack
- Security hardening features
- Performance optimization

#### Changed
- Improved container orchestration
- Enhanced security measures
- Better resource management

#### Fixed
- Various bugs and stability issues
- Performance bottlenecks
- Security vulnerabilities

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Suna is licensed under the MIT License. See [LICENSE](LICENSE) for details.
"""

        notes_path = self.output_dir / f"RELEASE_NOTES_{self.version}.md"
        with open(notes_path, 'w') as f:
            f.write(notes_content)

        logger.info(f"Created release notes: {notes_path}")

    def create_all_packages(self):
        """Create all deployment packages and artifacts."""
        logger.info("Creating all deployment packages...")

        self.create_output_directory()

        # Create Docker package
        docker_package = self.create_docker_deployment_package()

        # Create Kubernetes package
        k8s_package = self.create_kubernetes_deployment_package()

        # Create documentation
        self.create_installation_guide()
        self.create_release_notes()

        # Create checksums
        self.create_checksums([docker_package, k8s_package])

        logger.info("✅ All deployment packages created successfully!")
        logger.info(f"📦 Packages available in: {self.output_dir}")

        return [docker_package, k8s_package]

    def create_checksums(self, package_files):
        """Create checksums for package files."""
        import hashlib

        checksums = {}

        for package_file in package_files:
            if package_file.exists():
                # Calculate SHA256
                sha256 = hashlib.sha256()
                with open(package_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)

                checksums[package_file.name] = sha256.hexdigest()

        # Write checksums file
        checksums_path = self.output_dir / f"CHECKSUMS_{self.version}.txt"
        with open(checksums_path, 'w') as f:
            f.write(f"# Suna Self-Hosted v{self.version} Checksums\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")

            for filename, checksum in checksums.items():
                f.write(f"SHA256({filename}) = {checksum}\n")

        logger.info(f"Created checksums file: {checksums_path}")


def main():
    """Main deployment package creation runner."""
    base_path = Path(__file__).parent  # suna directory

    creator = DeploymentPackageCreator(base_path)
    packages = creator.create_all_packages()

    print("\n" + "="*80)
    print("DEPLOYMENT PACKAGES CREATED")
    print("="*80)
    print("Created packages:")
    for package in packages:
        print(f"  📦 {package.name}")
    print()
    print(f"Output directory: {creator.output_dir}")
    print()
    print("Next steps:")
    print("1. Test the Docker deployment package")
    print("2. Validate Kubernetes manifests")
    print("3. Update documentation as needed")
    print("4. Publish packages to release location")
    print("="*80)

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
