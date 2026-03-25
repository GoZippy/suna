#!/usr/bin/env python3
"""
Zippy Suna Local Environment Setup Script
Creates isolated containers with secure random passwords for local development.
"""

import os
import sys
import secrets
import string
import subprocess
from pathlib import Path
from typing import Dict, List

class LocalEnvironmentSetup:
    """Sets up local development environment with isolated containers"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.env_file = self.project_dir / ".env"
        self.backend_env_file = self.project_dir / "backend" / ".env"
        
        # Isolated ports for project containers (avoiding common conflicts)
        self.isolated_ports = {
            'postgres': 18881,
            'redis': 18882,
            'backend': 18883,
            'frontend': 18884,
            'ollama': 18885,
            'mailhog_smtp': 18886,
            'mailhog_web': 18887,
            'prometheus': 18888,
            'grafana': 18889
        }
        
        # Generate secure random passwords
        self.passwords = self._generate_secure_passwords()
    
    def _generate_secure_passwords(self) -> Dict[str, str]:
        """Generate secure random passwords for all services"""
        print("🔐 Generating secure random passwords...")
        
        passwords = {}
        
        # Generate a 32-character random string for JWT
        jwt_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        passwords['jwt_secret'] = ''.join(secrets.choice(jwt_chars) for _ in range(32))
        
        # Generate a 16-character random string for PostgreSQL
        passwords['postgres'] = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        # Generate a 16-character random string for Redis
        passwords['redis'] = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        # Generate a 16-character random string for Grafana
        passwords['grafana'] = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        # Generate a 16-character random string for admin user
        passwords['admin'] = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        print("  ✅ Generated secure passwords for all services")
        return passwords
    
    def create_main_env_file(self):
        """Create the main .env file with isolated ports and secure passwords"""
        print("\n⚙️  Creating main environment configuration...")
        
        env_content = f"""# Zippy Suna Local Development Environment
# Generated automatically - DO NOT commit to version control

# Database Configuration
POSTGRES_PASSWORD={self.passwords['postgres']}
DATABASE_URL=postgresql://suna:{self.passwords['postgres']}@localhost:{self.isolated_ports['postgres']}/suna

# JWT Authentication
JWT_SECRET_KEY={self.passwords['jwt_secret']}

# Admin User Configuration
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD={self.passwords['admin']}

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT={self.isolated_ports['redis']}
REDIS_PASSWORD={self.passwords['redis']}
REDIS_SSL=False

# Email Configuration (MailHog for local testing)
SMTP_HOST=localhost
SMTP_PORT={self.isolated_ports['mailhog_smtp']}
SMTP_USER=
SMTP_PASSWORD=

# CORS Configuration
CORS_ORIGINS=["http://localhost:{self.isolated_ports['frontend']}", "http://127.0.0.1:{self.isolated_ports['frontend']}"]

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development

# Monitoring
GRAFANA_PASSWORD={self.passwords['grafana']}

# AI/ML Configuration
# Use local Ollama if available, otherwise containerized
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CONTAINER_URL=http://localhost:{self.isolated_ports['ollama']}

# External LLM API Keys (Optional - for fallback)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# File Storage Configuration
MAX_UPLOAD_SIZE=100MB
FILE_STORAGE_PATH=/data/files

# Usage and Billing Configuration
DEFAULT_FREE_CREDITS=1000
DEFAULT_PRO_CREDITS=5000
DEFAULT_ENTERPRISE_CREDITS=10000

# Security Settings
SESSION_TIMEOUT_MINUTES=480
MAX_LOGIN_ATTEMPTS=10
ACCOUNT_LOCKOUT_MINUTES=15

# Sandbox Configuration
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_COUNT=2
SANDBOX_TIMEOUT_SECONDS=300

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_REQUESTS_PER_HOUR=2000

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE=0 2 * * *

# Monitoring and Observability
PROMETHEUS_RETENTION=48h
GRAFANA_ADMIN_USER=admin

# Network Configuration
INTERNAL_NETWORK=zippy-suna-network
EXTERNAL_DOMAIN=localhost

# Isolated Port Configuration
POSTGRES_PORT={self.isolated_ports['postgres']}
REDIS_PORT={self.isolated_ports['redis']}
BACKEND_PORT={self.isolated_ports['backend']}
FRONTEND_PORT={self.isolated_ports['frontend']}
OLLAMA_PORT={self.isolated_ports['ollama']}
MAILHOG_SMTP_PORT={self.isolated_ports['mailhog_smtp']}
MAILHOG_WEB_PORT={self.isolated_ports['mailhog_web']}
PROMETHEUS_PORT={self.isolated_ports['prometheus']}
GRAFANA_PORT={self.isolated_ports['grafana']}

# Resource Limits
POSTGRES_MAX_CONNECTIONS=100
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
REDIS_MAX_MEMORY=4gb

# Feature Flags
ENABLE_WEB_SEARCH=true
ENABLE_FILE_UPLOAD=true
ENABLE_SANDBOX_EXECUTION=true
ENABLE_AI_MODELS=true
ENABLE_MONITORING=true
ENABLE_EMAIL_NOTIFICATIONS=true

# Development Settings
DEBUG=true
AUTO_RELOAD=true
"""
        
        try:
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            print(f"  ✅ Created main .env file: {self.env_file}")
        except Exception as e:
            print(f"  ❌ Error creating .env file: {e}")
            return False
        
        return True
    
    def create_backend_env_file(self):
        """Create the backend .env file"""
        print("\n⚙️  Creating backend environment configuration...")
        
        backend_env_content = f"""# Backend Environment Configuration
# Generated automatically - DO NOT commit to version control

# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql://suna:{self.passwords['postgres']}@localhost:{self.isolated_ports['postgres']}/suna
POSTGRES_PASSWORD={self.passwords['postgres']}

# Redis
REDIS_HOST=localhost
REDIS_PORT={self.isolated_ports['redis']}
REDIS_PASSWORD={self.passwords['redis']}
REDIS_SSL=False

# JWT
JWT_SECRET_KEY={self.passwords['jwt_secret']}

# CORS
CORS_ORIGINS=http://localhost:{self.isolated_ports['frontend']}

# Ollama (use local if available, fallback to container)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CONTAINER_URL=http://localhost:{self.isolated_ports['ollama']}

# SMTP
SMTP_HOST=localhost
SMTP_PORT={self.isolated_ports['mailhog_smtp']}

# Admin
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD={self.passwords['admin']}

# Logging
LOG_LEVEL=DEBUG
"""
        
        try:
            # Ensure backend directory exists
            backend_dir = self.project_dir / "backend"
            backend_dir.mkdir(exist_ok=True)
            
            with open(self.backend_env_file, 'w') as f:
                f.write(backend_env_content)
            print(f"  ✅ Created backend .env file: {self.backend_env_file}")
        except Exception as e:
            print(f"  ❌ Error creating backend .env file: {e}")
            return False
        
        return True
    
    def create_isolated_compose_file(self):
        """Create a docker-compose file with isolated ports and secure configuration"""
        print("\n🔧 Creating isolated docker-compose configuration...")
        
        compose_content = f"""version: '3.8'

services:
  # Database Layer - Isolated Ports
  postgres:
    image: pgvector/pgvector:pg16
    container_name: zippy-suna-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: suna
      POSTGRES_USER: suna
      POSTGRES_PASSWORD: {self.passwords['postgres']}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d:ro
      - ./backend/database/migrations:/migrations:ro
    ports:
      - "127.0.0.1:{self.isolated_ports['postgres']}:5432"
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U suna -d suna"]
      interval: 10s
      timeout: 5s
      retries: 5
    command:
      - postgres
      - -c
      - max_connections=100
      - -c
      - shared_buffers=256MB
      - -c
      - effective_cache_size=1GB
      - -c
      - maintenance_work_mem=64MB
      - -c
      - checkpoint_completion_target=0.9
      - -c
      - wal_buffers=16MB
      - -c
      - default_statistics_target=100

  redis:
    image: redis:8-alpine
    container_name: zippy-suna-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 4gb --maxmemory-policy allkeys-lru --save 60 1 --loglevel warning --requirepass {self.passwords['redis']}
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:{self.isolated_ports['redis']}:6379"
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "{self.passwords['redis']}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Application Layer
  backend:
    container_name: zippy-suna-backend
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://suna:{self.passwords['postgres']}@postgres:5432/suna
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD={self.passwords['redis']}
      - REDIS_SSL=False
      - JWT_SECRET_KEY={self.passwords['jwt_secret']}
      - ADMIN_EMAIL=admin@localhost
      - ADMIN_PASSWORD={self.passwords['admin']}
      - SMTP_HOST=mailhog
      - SMTP_PORT=1025
      - SMTP_USER=
      - SMTP_PASSWORD=
      - LOG_LEVEL=DEBUG
      - CORS_ORIGINS=["http://localhost:{self.isolated_ports['frontend']}", "http://127.0.0.1:{self.isolated_ports['frontend']}"]
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    volumes:
      - backend_logs:/app/logs
      - ./backend/.env:/app/.env:ro
    ports:
      - "127.0.0.1:{self.isolated_ports['backend']}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    container_name: zippy-suna-frontend
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_API_URL=http://localhost:{self.isolated_ports['backend']}
      - NEXT_PUBLIC_OLLAMA_URL=http://localhost:11434
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "127.0.0.1:{self.isolated_ports['frontend']}:3000"
    depends_on:
      - backend
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health", "||", "exit", "1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # AI/ML Services (Optional - for users without local Ollama)
  ollama:
    image: ollama/ollama:latest
    container_name: zippy-suna-ollama
    restart: unless-stopped
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_MAX_LOADED_MODELS=3
      - OLLAMA_MAX_QUEUE=512
      - OLLAMA_RUNNERS_DIR=/tmp/ollama-runners
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "127.0.0.1:{self.isolated_ports['ollama']}:11434"
    networks:
      - zippy-suna-network
    profiles:
      - ollama-container
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Supporting Services
  mailhog:
    image: mailhog/mailhog:latest
    container_name: zippy-suna-mailhog
    restart: unless-stopped
    ports:
      - "127.0.0.1:{self.isolated_ports['mailhog_smtp']}:1025"  # SMTP server
      - "127.0.0.1:{self.isolated_ports['mailhog_web']}:8025"   # Web interface
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8025"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring and Observability
  prometheus:
    image: prom/prometheus:latest
    container_name: zippy-suna-prometheus
    restart: unless-stopped
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --web.console.libraries=/etc/prometheus/console_libraries
      - --web.console.templates=/etc/prometheus/consoles
      - --storage.tsdb.retention.time=48h
      - --web.enable-lifecycle
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "127.0.0.1:{self.isolated_ports['prometheus']}:9090"
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3

  grafana:
    image: grafana/grafana:latest
    container_name: zippy-suna-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD={self.passwords['grafana']}
      - GF_SECURITY_ADMIN_USER=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "127.0.0.1:{self.isolated_ports['grafana']}:3000"
    depends_on:
      - prometheus
    networks:
      - zippy-suna-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health", "||", "exit", "1"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  zippy-suna-network:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.21.0.0/16

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  ollama_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  backend_logs:
    driver: local
"""
        
        compose_file = self.project_dir / "docker-compose.local-isolated.yml"
        try:
            with open(compose_file, 'w') as f:
                f.write(compose_content)
            print(f"  ✅ Created isolated compose file: {compose_file}")
        except Exception as e:
            print(f"  ❌ Error creating compose file: {e}")
            return False
        
        return True
    
    def create_setup_documentation(self):
        """Create setup documentation with passwords and configuration"""
        print("\n📚 Creating setup documentation...")
        
        doc_content = f"""# Zippy Suna Local Development Setup

## 🔐 Generated Credentials (SAVE THESE!)

**⚠️  IMPORTANT: These credentials are for local development only. Do not use in production!**

### Database Access
- **PostgreSQL Host**: localhost
- **PostgreSQL Port**: {self.isolated_ports['postgres']}
- **Database**: suna
- **Username**: suna
- **Password**: {self.passwords['postgres']}

### Redis Access
- **Redis Host**: localhost
- **Redis Port**: {self.isolated_ports['redis']}
- **Password**: {self.passwords['redis']}

### Admin User
- **Email**: admin@localhost
- **Password**: {self.passwords['admin']}

### Grafana
- **URL**: http://localhost:{self.isolated_ports['grafana']}
- **Username**: admin
- **Password**: {self.passwords['grafana']}

### Service URLs
- **Frontend**: http://localhost:{self.isolated_ports['frontend']}
- **Backend API**: http://localhost:{self.isolated_ports['backend']}
- **PostgreSQL**: localhost:{self.isolated_ports['postgres']}
- **Redis**: localhost:{self.isolated_ports['redis']}
- **Ollama (Container)**: http://localhost:{self.isolated_ports['ollama']}
- **MailHog Web**: http://localhost:{self.isolated_ports['mailhog_web']}
- **Prometheus**: http://localhost:{self.isolated_ports['prometheus']}

## 🚀 Quick Start

### 1. Start All Services
```bash
docker-compose -f docker-compose.local-isolated.yml up -d
```

### 2. Start Only Core Services (Skip Ollama if you have local)
```bash
docker-compose -f docker-compose.local-isolated.yml --profile ollama-container up -d
```

### 3. Check Service Health
```bash
docker-compose -f docker-compose.local-isolated.yml ps
```

### 4. View Logs
```bash
docker-compose -f docker-compose.local-isolated.yml logs -f
```

## 🔧 Configuration Options

### Using Local Ollama (Recommended)
If you have Ollama running locally on port 11434:
- The backend will automatically use your local Ollama installation
- No need to start the containerized Ollama service
- Your existing models will be available

### Using Containerized Ollama
If you want to use the containerized version:
```bash
docker-compose -f docker-compose.local-isolated.yml --profile ollama-container up -d
```

## 🗄️ Database Initialization

The PostgreSQL container will automatically:
1. Create the `suna` database
2. Run initialization scripts from `./database/init/`
3. Apply migrations from `./backend/database/migrations/`

## 📊 Monitoring

- **Grafana**: http://localhost:{self.isolated_ports['grafana']} (admin/{self.passwords['grafana']})
- **Prometheus**: http://localhost:{self.isolated_ports['prometheus']}

## 🧹 Cleanup

### Stop All Services
```bash
docker-compose -f docker-compose.local-isolated.yml down
```

### Remove All Data (WARNING: This will delete all data!)
```bash
docker-compose -f docker-compose.local-isolated.yml down -v
docker volume prune -f
```

## 🔒 Security Notes

- All services are bound to localhost (127.0.0.1) only
- Isolated network: zippy-suna-network (172.21.0.0/16)
- Random passwords generated for each service
- No external access by default

## 🆘 Troubleshooting

### Port Conflicts
If you get port conflicts, check what's using the ports:
```bash
# Windows
netstat -an | findstr :{self.isolated_ports['postgres']}

# Linux/macOS
lsof -i :{self.isolated_ports['postgres']}
```

### Service Health
Check if services are healthy:
```bash
docker-compose -f docker-compose.local-isolated.yml ps
```

### Database Connection
Test PostgreSQL connection:
```bash
psql -h localhost -p {self.isolated_ports['postgres']} -U suna -d suna
```

### Redis Connection
Test Redis connection:
```bash
redis-cli -h localhost -p {self.isolated_ports['redis']} -a {self.passwords['redis']} ping
```

## 📝 Next Steps

1. **Start the services** using the commands above
2. **Access the frontend** at http://localhost:{self.isolated_ports['frontend']}
3. **Login with admin** credentials above
4. **Configure Ollama models** if using local installation
5. **Start building** your AI agents!

---
*Generated on: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}*
*Environment: Local Development*
"""
        
        doc_file = self.project_dir / "LOCAL_SETUP_GUIDE.md"
        try:
            with open(doc_file, 'w') as f:
                f.write(doc_content)
            print(f"  ✅ Created setup documentation: {doc_file}")
        except Exception as e:
            print(f"  ❌ Error creating documentation: {e}")
            return False
        
        return True
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🚀 Zippy Suna Local Environment Setup")
        print("=" * 50)
        
        # Create environment files
        if not self.create_main_env_file():
            return False
        
        if not self.create_backend_env_file():
            return False
        
        # Create isolated compose file
        if not self.create_isolated_compose_file():
            return False
        
        # Create documentation
        if not self.create_setup_documentation():
            return False
        
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Summary of what was created:")
        print(f"  • Main .env file: {self.env_file}")
        print(f"  • Backend .env file: {self.backend_env_file}")
        print(f"  • Isolated compose file: docker-compose.local-isolated.yml")
        print(f"  • Setup documentation: LOCAL_SETUP_GUIDE.md")
        
        print(f"\n🔐 Generated Credentials:")
        print(f"  • PostgreSQL Password: {self.passwords['postgres']}")
        print(f"  • Redis Password: {self.passwords['redis']}")
        print(f"  • Admin Password: {self.passwords['admin']}")
        print(f"  • Grafana Password: {self.passwords['grafana']}")
        
        print(f"\n🌐 Service URLs:")
        print(f"  • Frontend: http://localhost:{self.isolated_ports['frontend']}")
        print(f"  • Backend: http://localhost:{self.isolated_ports['backend']}")
        print(f"  • PostgreSQL: localhost:{self.isolated_ports['postgres']}")
        print(f"  • Redis: localhost:{self.isolated_ports['redis']}")
        
        print(f"\n📚 Next Steps:")
        print(f"  1. Review LOCAL_SETUP_GUIDE.md for complete instructions")
        print(f"  2. Start services: docker-compose -f docker-compose.local-isolated.yml up -d")
        print(f"  3. Access frontend at http://localhost:{self.isolated_ports['frontend']}")
        
        return True

def main():
    """Main entry point"""
    try:
        setup = LocalEnvironmentSetup()
        success = setup.run_setup()
        
        if success:
            print("\n🎉 Local environment setup completed successfully!")
            print("Check LOCAL_SETUP_GUIDE.md for complete instructions.")
        else:
            print("\n❌ Setup failed. Check the output above for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


