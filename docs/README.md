# Suna Self-Hosted Migration Documentation

Welcome to the comprehensive documentation for Suna's self-hosted migration. This guide covers everything you need to deploy, configure, and maintain your own Suna AI Worker instance.

## 📚 Documentation Index

### 🚀 Getting Started
- [Installation Guide](installation.md) - Complete setup instructions
- [Quick Start Guide](quickstart.md) - Get up and running in 10 minutes
- [System Requirements](requirements.md) - Hardware and software prerequisites

### 🔄 Migration
- [Migration Guide](migration.md) - Migrate from Supabase to self-hosted
- [Data Migration Tools](migration-tools.md) - Export/import procedures
- [Configuration Migration](config-migration.md) - Service configuration setup

### 🛠️ Administration
- [Admin Panel Guide](admin-panel.md) - Web-based administration interface
- [CLI Tools](cli-tools.md) - Command-line administration
- [System Monitoring](monitoring.md) - Health checks and metrics

### 🔧 Configuration
- [Environment Configuration](environment.md) - Environment variables and settings
- [Service Configuration](services.md) - Individual service configuration
- [Security Configuration](security.md) - Security hardening and best practices

### 🔒 Security
- [Security Guide](security-guide.md) - Security best practices
- [Hardening Guide](hardening.md) - System hardening procedures
- [Access Control](access-control.md) - User management and permissions

### 📊 Monitoring & Maintenance
- [Monitoring Setup](monitoring-setup.md) - Prometheus and Grafana configuration
- [Backup & Recovery](backup-recovery.md) - Data backup and disaster recovery
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### 🚀 Deployment
- [Docker Deployment](docker-deployment.md) - Docker Compose deployment
- [Proxmox Deployment](proxmox-deployment.md) - VM/LXC deployment automation
- [Production Deployment](production.md) - Production-ready deployment

### 🔌 API Reference
- [API Documentation](api-reference.md) - Complete API reference
- [Webhook Integration](webhooks.md) - Webhook configuration
- [SDK Documentation](sdk.md) - Client library documentation

### 🧪 Testing
- [Testing Guide](testing.md) - Running tests and validation
- [Performance Testing](performance-testing.md) - Load testing procedures
- [Security Testing](security-testing.md) - Vulnerability assessment

## 🎯 Quick Navigation

### For New Users
1. Start with [Installation Guide](installation.md)
2. Follow [Quick Start Guide](quickstart.md)
3. Configure [Environment](environment.md)

### For Existing Supabase Users
1. Review [Migration Guide](migration.md)
2. Use [Data Migration Tools](migration-tools.md)
3. Configure [Services](services.md)

### For Administrators
1. Set up [Admin Panel](admin-panel.md)
2. Configure [Monitoring](monitoring-setup.md)
3. Implement [Security](security-guide.md)

### For Developers
1. Review [API Reference](api-reference.md)
2. Set up [Testing](testing.md)
3. Configure [Development Environment](development.md)

## 📋 System Overview

Suna is a comprehensive AI Worker platform with the following components:

### Core Services (XX91 Port Scheme)
- **Frontend** (Port 3091) - Next.js web application
- **Backend API** (Port 8091) - FastAPI REST API
- **PostgreSQL** (Port 5491) - Primary database with pgvector
- **Redis** (Port 6391) - Caching and session store
- **Ollama** (Port 11434) - Local LLM inference
- **Admin Panel** (Port 9091) - System administration

### Supporting Services
- **Prometheus** (Port 9090) - Metrics collection
- **Grafana** (Port 3000) - Monitoring dashboards
- **Nginx** (Port 80/443) - Reverse proxy and SSL termination
- **SearXNG** (Port 8080) - Local search engine

### Key Features
- **Self-hosted AI Workers** - Isolated Docker containers
- **Vector Database** - Semantic search and embeddings
- **Local LLM Support** - Ollama integration
- **Web Scraping** - Automated data collection
- **User Management** - Local authentication system
- **Monitoring** - Comprehensive system monitoring
- **Security** - Hardened security configuration

## 🆘 Support

### Getting Help
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [FAQ](faq.md) - Frequently asked questions
- [Community Support](community.md) - Community resources

### Reporting Issues
- [Issue Templates](issue-templates.md) - Bug report and feature request templates
- [Log Collection](log-collection.md) - How to collect diagnostic information

## 📄 License

This documentation is part of the Suna project and is licensed under the same terms as the main project.

## 🔄 Version History

- **v1.0.0** - Initial self-hosted migration documentation
- **v1.1.0** - Added comprehensive deployment guides
- **v1.2.0** - Enhanced security and monitoring documentation

---

**Last Updated**: December 2024  
**Documentation Version**: 1.2.0  
**Suna Version**: Self-Hosted Migration v1.0







