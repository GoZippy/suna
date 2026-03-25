# Suna Self-Hosted Installation Guide

This guide provides step-by-step instructions for installing and configuring Suna as a self-hosted AI Worker platform.

## 📋 Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores (2.4 GHz or higher)
- **RAM**: 8 GB
- **Storage**: 50 GB available space
- **Network**: Stable internet connection
- **OS**: Linux (Ubuntu 20.04+ recommended) or Docker Desktop

#### Recommended Requirements
- **CPU**: 8+ cores (3.0 GHz or higher)
- **RAM**: 16+ GB
- **Storage**: 100+ GB SSD
- **GPU**: NVIDIA GPU with 8+ GB VRAM (for LLM acceleration)
- **Network**: 100+ Mbps connection

### Software Requirements

#### Required Software
- **Docker**: 20.10+ with Docker Compose
- **Git**: 2.30+
- **Python**: 3.11+ (for migration tools)
- **Node.js**: 18+ (for development tools)

#### Optional Software
- **NVIDIA Docker**: For GPU acceleration
- **Make**: For build automation
- **jq**: For JSON processing

## 🚀 Quick Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/suna.git
cd suna
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables:**
```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5491
POSTGRES_DB=suna
POSTGRES_USER=suna_user
POSTGRES_PASSWORD=your_secure_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6391
REDIS_PASSWORD=your_redis_password

# Application Configuration
SECRET_KEY=your_secret_key_here
ENVIRONMENT=production
DOMAIN=your-domain.com

# Admin Configuration
ADMIN_EMAIL=admin@your-domain.com
ADMIN_PASSWORD=your_admin_password
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec backend python -m alembic upgrade head

# Create admin user
docker-compose exec backend python -m suna.cli create-admin
```

### 5. Verify Installation

```bash
# Check service health
curl http://localhost:8091/health

# Access admin panel
open http://localhost:9091
```

## 🔧 Detailed Installation

### Step 1: System Preparation

#### Ubuntu/Debian Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### CentOS/RHEL Setup

```bash
# Update system
sudo yum update -y

# Install EPEL repository
sudo yum install -y epel-release

# Install required packages
sudo yum install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv

# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### Step 2: Project Setup

```bash
# Clone repository
git clone https://github.com/your-org/suna.git
cd suna

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

### Step 3: Configuration

#### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Generate secure secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Update environment file
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" .env
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" .env
```

#### Port Configuration (XX91 Scheme)

The installation uses the following port scheme:

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3091 | Web application |
| Backend API | 8091 | REST API |
| PostgreSQL | 5491 | Database |
| Redis | 6391 | Cache |
| Admin Panel | 9091 | Administration |
| Nginx | 80/443 | Reverse proxy |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboards |

#### SSL/TLS Configuration

```bash
# Create SSL certificates directory
sudo mkdir -p /etc/ssl/suna
sudo chown $USER:$USER /etc/ssl/suna

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/suna/private.key \
    -out /etc/ssl/suna/certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# For production, use Let's Encrypt or commercial certificates
```

### Step 4: Database Setup

```bash
# Start database services
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 30

# Run database migrations
docker-compose exec backend python -m alembic upgrade head

# Create initial admin user
docker-compose exec backend python -m suna.cli create-admin \
    --email admin@your-domain.com \
    --password your_admin_password \
    --role super_admin
```

### Step 5: Service Deployment

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View service logs
docker-compose logs -f
```

### Step 6: Verification

#### Health Checks

```bash
# Check API health
curl -f http://localhost:8091/health

# Check database connectivity
docker-compose exec backend python -c "
import asyncio
from suna.database import get_database
async def check_db():
    db = get_database()
    await db.execute('SELECT 1')
    print('Database connection successful')
asyncio.run(check_db())
"

# Check Redis connectivity
docker-compose exec backend python -c "
import redis
r = redis.Redis(host='localhost', port=6391, password='your_redis_password')
r.ping()
print('Redis connection successful')
"
```

#### Service Verification

```bash
# Test frontend
curl -f http://localhost:3091

# Test admin panel
curl -f http://localhost:9091/health

# Test API endpoints
curl -f http://localhost:8091/api/v1/health
```

## 🔒 Security Configuration

### Firewall Setup

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow Suna ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3091/tcp
sudo ufw allow 8091/tcp
sudo ufw allow 9091/tcp

# Allow internal ports (optional)
sudo ufw allow from 127.0.0.1 to any port 5491
sudo ufw allow from 127.0.0.1 to any port 6391

# Reload firewall
sudo ufw reload
```

### SSL/TLS Configuration

```bash
# Update Nginx configuration for SSL
sudo cp nginx/ssl.conf /etc/nginx/sites-available/suna
sudo ln -s /etc/nginx/sites-available/suna /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 📊 Monitoring Setup

### Prometheus Configuration

```bash
# Verify Prometheus is running
curl http://localhost:9090/-/healthy

# Check targets
curl http://localhost:9090/api/v1/targets
```

### Grafana Setup

```bash
# Access Grafana
open http://localhost:3000

# Default credentials
# Username: admin
# Password: admin

# Import dashboards
# 1. Go to Dashboards > Import
# 2. Import dashboard IDs: 1860, 315, 7249
```

## 🚀 Production Deployment

### Environment Optimization

```bash
# Optimize Docker daemon
sudo tee /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
EOF

sudo systemctl restart docker
```

### System Optimization

```bash
# Optimize system settings
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
echo 'net.core.somaxconn=65535' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Backup Configuration

```bash
# Create backup directory
sudo mkdir -p /opt/suna/backups
sudo chown $USER:$USER /opt/suna/backups

# Configure automated backups
sudo crontab -e

# Add backup schedule
0 2 * * * /opt/suna/scripts/backup.sh
```

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service logs
docker-compose logs service_name

# Check resource usage
docker stats

# Check port conflicts
sudo netstat -tulpn | grep :port_number
```

#### Database Connection Issues

```bash
# Check database status
docker-compose exec postgres pg_isready

# Check database logs
docker-compose logs postgres

# Reset database (development only)
docker-compose down -v
docker-compose up -d postgres
```

#### Memory Issues

```bash
# Check memory usage
free -h

# Optimize memory settings
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Log Analysis

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Search logs
docker-compose logs | grep ERROR
```

## 📚 Next Steps

After successful installation:

1. **Configure Users**: Set up user accounts and permissions
2. **Import Data**: Migrate existing data if applicable
3. **Configure Monitoring**: Set up alerts and dashboards
4. **Security Hardening**: Implement additional security measures
5. **Backup Strategy**: Configure automated backups
6. **Performance Tuning**: Optimize for your workload

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review [FAQ](faq.md)
3. Check [Log Collection](log-collection.md) for diagnostic information
4. Open an issue with detailed information

---

**Installation Complete!** 🎉

Your Suna self-hosted instance is now ready for use. Access the application at `http://your-domain.com` or `http://localhost:3091`.







