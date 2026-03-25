#!/usr/bin/env python3
"""
Simple Deployment Package Creator

Creates basic deployment packages for the self-hosted Suna system.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDeploymentCreator:
    """Creates simple deployment packages."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.output_dir = self.base_path / "dist"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.version = "1.0.0"

    def create_output_directory(self):
        """Create output directory for packages."""
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Created output directory: {self.output_dir}")

    def create_deployment_package(self):
        """Create a comprehensive deployment package."""
        logger.info("Creating deployment package...")

        package_name = f"suna-self-hosted-{self.version}-{self.timestamp}"
        package_dir = self.output_dir / package_name

        # Create package directory
        package_dir.mkdir(exist_ok=True)

        # Core files to include
        core_files = [
            "docker-compose.self-hosted.yml",
            "self-hosted.env.example",
            "README.md",
            "SELF-HOSTED-README.md",
            "DEPLOYMENT.md",
            "MIGRATION_GUIDE.md",
            "SECURITY.md",
            "scripts/backup-database.sh",
            "scripts/restore-database.sh",
            "scripts/rollback-migration.sh"
        ]

        # Copy core files
        for file_path in core_files:
            src = self.base_path / file_path
            if src.exists():
                dst = package_dir / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.copy2(src, dst)
                    logger.debug(f"Copied: {file_path}")

        # Create deployment script
        self.create_simple_deployment_script(package_dir)

        # Create configuration guide
        self.create_config_guide(package_dir)

        # Create archive
        archive_name = f"{package_name}.zip"
        archive_path = self.output_dir / archive_name

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.relative_to(package_dir))

        logger.info(f"Created deployment package: {archive_path}")
        return archive_path

    def create_simple_deployment_script(self, package_dir: Path):
        """Create a simple deployment script."""
        script_content = """#!/bin/bash
# Suna Self-Hosted Simple Deployment Script

set -e

echo "Starting Suna Self-Hosted Deployment"

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating environment configuration..."
    cp self-hosted.env.example .env
    echo "Please edit .env file with your configuration"
    echo "Press Enter to continue or Ctrl+C to exit"
    read
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p backups
mkdir -p logs
mkdir -p data

# Start services
echo "Starting Docker services..."
docker-compose -f docker-compose.self-hosted.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 30

echo "Deployment completed!"
echo ""
echo "Access your Suna instance at:"
echo "   Frontend: http://localhost:3091"
echo "   Backend API: http://localhost:8091"
echo ""
echo "See README.md for detailed configuration instructions"
"""

        script_path = package_dir / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make script executable (skip on Windows)
        try:
            os.chmod(script_path, 0o755)
        except:
            pass

    def create_config_guide(self, package_dir: Path):
        """Create configuration guide."""
        guide_content = """# Suna Self-Hosted Configuration Guide

## Quick Start

1. Extract the deployment package
2. Copy self-hosted.env.example to .env
3. Edit .env with your configuration
4. Run ./deploy.sh

## Environment Configuration

### Required Settings

# Database
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=suna
POSTGRES_DB=suna

# Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_here
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_secure_admin_password

### Optional Settings

# Domain (for production)
EXTERNAL_DOMAIN=yourdomain.com

# Email (optional)
SMTP_HOST=your_smtp_server
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password

# Monitoring
GRAFANA_PASSWORD=your_grafana_password

## Security Checklist

- [ ] Change all default passwords
- [ ] Set secure JWT secret key
- [ ] Configure domain and SSL (production)
- [ ] Set up backups
- [ ] Review firewall settings

## Troubleshooting

### Common Issues

1. Port conflicts: Change ports in docker-compose.self-hosted.yml
2. Permission issues: Ensure Docker has proper permissions
3. Memory issues: Increase Docker memory limits
4. Database issues: Check PostgreSQL logs

### Logs

View logs with: docker-compose logs [service_name]

## Support

See SELF-HOSTED-README.md for detailed documentation.
"""

        guide_path = package_dir / "CONFIG_GUIDE.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)

    def create_readme_update(self):
        """Create an updated README for the deployment package."""
        readme_content = f"""# Suna Self-Hosted v{self.version}

## Overview

Suna is a complete self-hosted AI Worker platform that provides all the functionality of the cloud version while giving you full control over your data and infrastructure.

## What's Included

- **Complete AI Stack**: Backend API, Frontend UI, AI models (Ollama)
- **Database**: PostgreSQL with pgvector for embeddings
- **Search**: Local metasearch with SearXNG
- **Monitoring**: Prometheus, Grafana, and alerting
- **Security**: Authentication, authorization, and SSL support
- **Backup**: Automated backup and restore scripts

## Quick Start

1. **Prerequisites**
   - Docker 24.0+
   - Docker Compose 2.20+
   - 8GB+ RAM
   - 50GB+ free disk space

2. **Deploy**
   ```bash
   ./deploy.sh
   ```

3. **Access**
   - Frontend: http://localhost:3091
   - API: http://localhost:8091
   - Monitoring: http://localhost:3191

## Features

### AI & ML
- Local LLM inference with Ollama
- Vector embeddings with pgvector
- Custom AI agent creation
- Background job processing

### Data Management
- PostgreSQL database with extensions
- File storage and management
- Real-time WebSocket communication
- Comprehensive audit logging

### Search & Discovery
- Local metasearch engine (SearXNG)
- Web scraping capabilities
- Result caching and deduplication

### Security & Monitoring
- JWT-based authentication
- Role-based access control
- SSL/TLS encryption
- Prometheus metrics
- Grafana dashboards
- Automated alerting

## Configuration

See CONFIG_GUIDE.md for detailed configuration instructions.

## Production Deployment

For production use:

1. **Domain & SSL**: Configure your domain and SSL certificates
2. **Security**: Change all default passwords and secrets
3. **Backups**: Set up automated backups
4. **Monitoring**: Configure alerting and notifications
5. **Scaling**: Adjust resource limits based on usage

## Migration

To migrate from Supabase:

1. Export your data from Supabase
2. Deploy this self-hosted instance
3. Run migration scripts: `python migration/migrate.py`
4. Update DNS to point to new instance

## Support

- **Documentation**: SELF-HOSTED-README.md
- **Migration Guide**: MIGRATION_GUIDE.md
- **Security Guide**: SECURITY.md
- **Deployment Guide**: DEPLOYMENT.md

## System Requirements

### Minimum
- CPU: 2 cores
- RAM: 8GB
- Storage: 50GB
- Network: 10Mbps

### Recommended
- CPU: 4+ cores
- RAM: 16GB+
- Storage: 100GB+ SSD
- Network: 100Mbps+

## License

MIT License - see LICENSE file for details.

## Version

{self.version} - {datetime.now().strftime('%Y-%m-%d')}
"""

        readme_path = self.output_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)

        logger.info(f"Created README: {readme_path}")


def main():
    """Main deployment package creation runner."""
    base_path = Path(__file__).parent  # suna directory

    creator = SimpleDeploymentCreator(base_path)
    creator.create_output_directory()

    # Create deployment package
    package = creator.create_deployment_package()

    # Create documentation
    creator.create_readme_update()

    print("\n" + "="*60)
    print("DEPLOYMENT PACKAGE CREATED")
    print("="*60)
    print(f"Package: {package}")
    print(f"Output directory: {creator.output_dir}")
    print()
    print("Package contents:")
    print("  - docker-compose.self-hosted.yml")
    print("  - self-hosted.env.example")
    print("  - deploy.sh (deployment script)")
    print("  - CONFIG_GUIDE.md")
    print("  - Documentation files")
    print()
    print("Next steps:")
    print("1. Extract the package")
    print("2. Configure environment variables")
    print("3. Run ./deploy.sh")
    print("4. Access at http://localhost:3091")
    print("="*60)

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)





