#!/usr/bin/env python3
"""
Suna Configuration Migration Tool

This script migrates external service configurations to local equivalents for self-hosted deployment.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
import yaml
import shutil
from urllib.parse import urlparse

# Configure logging
logger = structlog.get_logger(__name__)

class ConfigurationMigrator:
    """Handles migration of external service configurations to local equivalents"""
    
    def __init__(self, config_file: str, output_dir: str = "migrated_configs"):
        self.config_file = Path(config_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Migration metadata
        self.migration_metadata = {
            "migration_timestamp": datetime.utcnow().isoformat(),
            "configs_migrated": [],
            "errors": [],
            "warnings": []
        }
        
        # Load source configuration
        self.source_config = self.load_source_config()
    
    def load_source_config(self) -> Dict[str, Any]:
        """Load source configuration file"""
        try:
            if self.config_file.suffix.lower() in ['.json', '.js']:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            elif self.config_file.suffix.lower() in ['.yaml', '.yml']:
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Try to detect format
                with open(self.config_file, 'r') as f:
                    content = f.read().strip()
                    if content.startswith('{'):
                        return json.loads(content)
                    else:
                        return yaml.safe_load(content)
        except Exception as e:
            logger.error("Failed to load source configuration", error=str(e))
            raise
    
    def migrate_all(self) -> Dict[str, Any]:
        """Migrate all configurations"""
        logger.info("Starting configuration migration")
        
        try:
            # Migrate environment variables
            self.migrate_environment_variables()
            
            # Migrate database configuration
            self.migrate_database_config()
            
            # Migrate authentication configuration
            self.migrate_auth_config()
            
            # Migrate external service configurations
            self.migrate_external_services()
            
            # Migrate file storage configuration
            self.migrate_storage_config()
            
            # Migrate monitoring configuration
            self.migrate_monitoring_config()
            
            # Generate migration report
            self.generate_migration_report()
            
            logger.info("Configuration migration completed successfully")
            return self.migration_metadata
            
        except Exception as e:
            logger.error("Configuration migration failed", error=str(e))
            self.migration_metadata["errors"].append(str(e))
            raise
    
    def migrate_environment_variables(self) -> None:
        """Migrate environment variables from external to local services"""
        logger.info("Migrating environment variables")
        
        try:
            # Create environment files for different environments
            environments = ["production", "development", "staging"]
            
            for env in environments:
                env_config = self.create_environment_config(env)
                env_file = self.output_dir / f".env.{env}"
                
                with open(env_file, 'w') as f:
                    for key, value in env_config.items():
                        f.write(f"{key}={value}\n")
                
                self.migration_metadata["configs_migrated"].append(str(env_file))
                logger.info("Environment config created", environment=env, file=str(env_file))
            
            # Create example file
            example_config = self.create_environment_config("example")
            example_file = self.output_dir / ".env.example"
            
            with open(example_file, 'w') as f:
                f.write("# Suna Self-Hosted Environment Configuration\n")
                f.write("# Copy this file to .env.{environment} and update with your values\n\n")
                for key, value in example_config.items():
                    f.write(f"{key}={value}\n")
            
            self.migration_metadata["configs_migrated"].append(str(example_file))
            logger.info("Example environment config created", file=str(example_file))
            
        except Exception as e:
            logger.error("Environment variables migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"Environment variables migration failed: {e}")
    
    def create_environment_config(self, environment: str) -> Dict[str, str]:
        """Create environment configuration for specific environment"""
        config = {
            # Database Configuration
            "POSTGRES_PASSWORD": f"suna_{environment}_password",
            "DATABASE_URL": f"postgresql://suna:suna_{environment}_password@postgres:5432/suna",
            
            # Redis Configuration
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6391",
            "REDIS_PASSWORD": "",
            "REDIS_SSL": "False",
            
            # Application Configuration
            "ENVIRONMENT": environment,
            "LOG_LEVEL": "INFO" if environment == "production" else "DEBUG",
            "SECRET_KEY": f"suna_{environment}_secret_key_change_this",
            
            # API Configuration
            "API_HOST": "0.0.0.0",
            "API_PORT": "8091",
            "CORS_ORIGINS": '["http://localhost:3091", "http://127.0.0.1:3091"]',
            
            # Frontend Configuration
            "NEXT_PUBLIC_API_URL": "http://localhost:8091",
            "NEXT_PUBLIC_WS_URL": "ws://localhost:8091",
            
            # Local AI Configuration
            "OLLAMA_HOST": "ollama",
            "OLLAMA_PORT": "11491",
            "DEFAULT_MODEL": "llama3.2:3b",
            
            # SMTP Configuration
            "SMTP_HOST": "mailhog",
            "SMTP_PORT": "1091",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "SMTP_TLS": "False",
            
            # Monitoring Configuration
            "PROMETHEUS_PORT": "9091",
            "GRAFANA_PORT": "3191",
            "ALERTMANAGER_PORT": "9191",
            
            # Storage Configuration
            "LOCAL_STORAGE_PATH": "/app/data/storage",
            "MAX_FILE_SIZE": "100MB",
            
            # Security Configuration
            "JWT_SECRET": f"suna_{environment}_jwt_secret_change_this",
            "JWT_EXPIRY": "24h",
            "RATE_LIMIT_ENABLED": "true",
            "RATE_LIMIT_REQUESTS": "100",
            "RATE_LIMIT_WINDOW": "60"
        }
        
        # Environment-specific overrides
        if environment == "production":
            config.update({
                "LOG_LEVEL": "INFO",
                "CORS_ORIGINS": '["https://your-domain.com"]',
                "NEXT_PUBLIC_API_URL": "https://your-domain.com",
                "NEXT_PUBLIC_WS_URL": "wss://your-domain.com",
                "SMTP_TLS": "True",
                "RATE_LIMIT_REQUESTS": "1000"
            })
        elif environment == "development":
            config.update({
                "LOG_LEVEL": "DEBUG",
                "RELOAD": "true",
                "CORS_ORIGINS": '["http://localhost:3091", "http://127.0.0.1:3091", "http://localhost:3000"]'
            })
        
        return config
    
    def migrate_database_config(self) -> None:
        """Migrate database configuration"""
        logger.info("Migrating database configuration")
        
        try:
            # Create database initialization script
            db_init_script = self.output_dir / "database" / "init.sql"
            db_init_script.parent.mkdir(exist_ok=True)
            
            init_sql = """
-- Suna Database Initialization Script
-- This script sets up the initial database structure

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    config JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create agent_versions table
CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    version TEXT NOT NULL,
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create agent_workflows table
CREATE TABLE IF NOT EXISTS agent_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    name TEXT NOT NULL,
    steps JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create knowledge_base table
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES knowledge_base(id),
    title TEXT NOT NULL,
    content TEXT,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    size BIGINT,
    mime_type TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_id ON agent_versions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_workflows_agent_id ON agent_workflows(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_user_id ON knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_knowledge_base_id ON documents(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);

-- Create functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_workflows_updated_at BEFORE UPDATE ON agent_workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
            
            with open(db_init_script, 'w') as f:
                f.write(init_sql)
            
            self.migration_metadata["configs_migrated"].append(str(db_init_script))
            logger.info("Database initialization script created", file=str(db_init_script))
            
        except Exception as e:
            logger.error("Database configuration migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"Database configuration migration failed: {e}")
    
    def migrate_auth_config(self) -> None:
        """Migrate authentication configuration"""
        logger.info("Migrating authentication configuration")
        
        try:
            # Create authentication configuration
            auth_config = {
                "jwt": {
                    "secret": "suna_jwt_secret_change_this",
                    "algorithm": "HS256",
                    "expiry": "24h",
                    "refresh_expiry": "7d"
                },
                "password": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True
                },
                "session": {
                    "max_sessions_per_user": 5,
                    "session_timeout": "24h"
                },
                "rate_limiting": {
                    "login_attempts": 5,
                    "login_window": "5m",
                    "register_attempts": 3,
                    "register_window": "1h"
                }
            }
            
            auth_file = self.output_dir / "auth_config.json"
            with open(auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)
            
            self.migration_metadata["configs_migrated"].append(str(auth_file))
            logger.info("Authentication configuration created", file=str(auth_file))
            
        except Exception as e:
            logger.error("Authentication configuration migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"Authentication configuration migration failed: {e}")
    
    def migrate_external_services(self) -> None:
        """Migrate external service configurations to local equivalents"""
        logger.info("Migrating external service configurations")
        
        try:
            # Create local service configurations
            services_config = {
                "search": {
                    "type": "local",
                    "searxng_url": "http://searxng:8091",
                    "fallback_apis": []
                },
                "ai": {
                    "type": "local",
                    "ollama_url": "http://ollama:11491",
                    "default_model": "llama3.2:3b",
                    "embedding_model": "nomic-embed-text",
                    "fallback_apis": []
                },
                "email": {
                    "type": "local",
                    "smtp_host": "mailhog",
                    "smtp_port": 1091,
                    "smtp_user": "",
                    "smtp_password": "",
                    "smtp_tls": False,
                    "from_email": "noreply@suna.local"
                },
                "storage": {
                    "type": "local",
                    "path": "/app/data/storage",
                    "max_file_size": "100MB",
                    "allowed_types": ["image/*", "text/*", "application/pdf"]
                },
                "queue": {
                    "type": "local",
                    "redis_host": "redis",
                    "redis_port": 6391,
                    "redis_password": "",
                    "redis_ssl": False
                }
            }
            
            services_file = self.output_dir / "services_config.json"
            with open(services_file, 'w') as f:
                json.dump(services_config, f, indent=2)
            
            self.migration_metadata["configs_migrated"].append(str(services_file))
            logger.info("Services configuration created", file=str(services_file))
            
        except Exception as e:
            logger.error("External services migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"External services migration failed: {e}")
    
    def migrate_storage_config(self) -> None:
        """Migrate file storage configuration"""
        logger.info("Migrating storage configuration")
        
        try:
            # Create storage configuration
            storage_config = {
                "local": {
                    "enabled": True,
                    "path": "/app/data/storage",
                    "max_file_size": "100MB",
                    "allowed_mime_types": [
                        "image/*",
                        "text/*",
                        "application/pdf",
                        "application/json",
                        "application/xml"
                    ],
                    "organize_by_date": True,
                    "backup_enabled": True,
                    "backup_retention_days": 30
                },
                "buckets": {
                    "uploads": {
                        "public": False,
                        "max_size": "50MB"
                    },
                    "documents": {
                        "public": False,
                        "max_size": "100MB"
                    },
                    "images": {
                        "public": True,
                        "max_size": "10MB"
                    }
                }
            }
            
            storage_file = self.output_dir / "storage_config.json"
            with open(storage_file, 'w') as f:
                json.dump(storage_config, f, indent=2)
            
            self.migration_metadata["configs_migrated"].append(str(storage_file))
            logger.info("Storage configuration created", file=str(storage_file))
            
            # Create storage directory structure
            storage_dirs = [
                "storage/uploads",
                "storage/documents", 
                "storage/images",
                "storage/backups"
            ]
            
            for dir_path in storage_dirs:
                full_path = self.output_dir / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                logger.info("Storage directory created", path=str(full_path))
            
        except Exception as e:
            logger.error("Storage configuration migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"Storage configuration migration failed: {e}")
    
    def migrate_monitoring_config(self) -> None:
        """Migrate monitoring configuration"""
        logger.info("Migrating monitoring configuration")
        
        try:
            # Create Prometheus configuration
            prometheus_config = {
                "global": {
                    "scrape_interval": "15s",
                    "evaluation_interval": "15s"
                },
                "rule_files": [],
                "scrape_configs": [
                    {
                        "job_name": "suna-backend",
                        "static_configs": [
                            {
                                "targets": ["backend:8000"]
                            }
                        ],
                        "metrics_path": "/api/monitoring/metrics"
                    },
                    {
                        "job_name": "suna-frontend",
                        "static_configs": [
                            {
                                "targets": ["frontend:3000"]
                            }
                        ],
                        "metrics_path": "/api/health"
                    },
                    {
                        "job_name": "postgres",
                        "static_configs": [
                            {
                                "targets": ["postgres:5432"]
                            }
                        ]
                    },
                    {
                        "job_name": "redis",
                        "static_configs": [
                            {
                                "targets": ["redis:6379"]
                            }
                        ]
                    }
                ]
            }
            
            prometheus_file = self.output_dir / "monitoring" / "prometheus.yml"
            prometheus_file.parent.mkdir(exist_ok=True)
            
            with open(prometheus_file, 'w') as f:
                yaml.dump(prometheus_config, f, default_flow_style=False)
            
            self.migration_metadata["configs_migrated"].append(str(prometheus_file))
            logger.info("Prometheus configuration created", file=str(prometheus_file))
            
            # Create Grafana dashboard configuration
            grafana_config = {
                "dashboard": {
                    "title": "Suna Self-Hosted Dashboard",
                    "panels": [
                        {
                            "title": "API Requests",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "rate(http_requests_total[5m])",
                                    "legendFormat": "{{method}} {{endpoint}}"
                                }
                            ]
                        },
                        {
                            "title": "Database Connections",
                            "type": "stat",
                            "targets": [
                                {
                                    "expr": "pg_stat_database_numbackends",
                                    "legendFormat": "{{datname}}"
                                }
                            ]
                        },
                        {
                            "title": "Redis Memory Usage",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "redis_memory_used_bytes",
                                    "legendFormat": "Memory Used"
                                }
                            ]
                        }
                    ]
                }
            }
            
            grafana_file = self.output_dir / "monitoring" / "grafana_dashboard.json"
            with open(grafana_file, 'w') as f:
                json.dump(grafana_config, f, indent=2)
            
            self.migration_metadata["configs_migrated"].append(str(grafana_file))
            logger.info("Grafana dashboard configuration created", file=str(grafana_file))
            
        except Exception as e:
            logger.error("Monitoring configuration migration failed", error=str(e))
            self.migration_metadata["errors"].append(f"Monitoring configuration migration failed: {e}")
    
    def generate_migration_report(self) -> None:
        """Generate migration report"""
        logger.info("Generating migration report")
        
        try:
            report = {
                "migration_summary": {
                    "timestamp": self.migration_metadata["migration_timestamp"],
                    "configs_migrated": len(self.migration_metadata["configs_migrated"]),
                    "errors": len(self.migration_metadata["errors"]),
                    "warnings": len(self.migration_metadata["warnings"])
                },
                "migrated_configs": self.migration_metadata["configs_migrated"],
                "errors": self.migration_metadata["errors"],
                "warnings": self.migration_metadata["warnings"],
                "next_steps": [
                    "1. Review all migrated configuration files",
                    "2. Update environment-specific values in .env files",
                    "3. Update domain names and URLs for production",
                    "4. Set secure passwords and secrets",
                    "5. Test the configuration with the deployment scripts",
                    "6. Update any application-specific configuration references"
                ]
            }
            
            report_file = self.output_dir / "migration_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info("Migration report generated", file=str(report_file))
            
        except Exception as e:
            logger.error("Failed to generate migration report", error=str(e))
            self.migration_metadata["errors"].append(f"Report generation failed: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Migrate external service configurations to local")
    parser.add_argument("--config-file", required=True, help="Source configuration file path")
    parser.add_argument("--output-dir", default="migrated_configs", help="Output directory for migrated configs")
    
    args = parser.parse_args()
    
    try:
        migrator = ConfigurationMigrator(
            config_file=args.config_file,
            output_dir=args.output_dir
        )
        
        metadata = migrator.migrate_all()
        
        print(f"\nConfiguration migration completed!")
        print(f"Configs migrated: {len(metadata['configs_migrated'])}")
        print(f"Errors: {len(metadata['errors'])}")
        print(f"Warnings: {len(metadata['warnings'])}")
        
        if metadata['errors']:
            print(f"\nErrors:")
            for error in metadata['errors']:
                print(f"  - {error}")
        
        if metadata['warnings']:
            print(f"\nWarnings:")
            for warning in metadata['warnings']:
                print(f"  - {warning}")
        
        print(f"\nMigrated configurations saved to: {args.output_dir}")
        print("Please review and update the configuration files as needed.")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error("Configuration migration failed", error=str(e))
        print(f"Configuration migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







