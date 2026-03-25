# Zippy Suna Local Development Setup

This guide sets up Zippy Suna for local development with **isolated containers**, **secure random passwords**, and **local Ollama integration**. All services run on isolated ports to avoid conflicts with your existing development environment.

## 🎯 Key Features

- **🚫 No Port 3000** - All services use isolated ports (18881-18889)
- **🔐 Secure Random Passwords** - Automatically generated for each service
- **🐳 Isolated Containers** - Project-specific containers, separate from system services
- **🤖 Local Ollama Integration** - Uses your existing Ollama installation by default
- **📊 Full Monitoring Stack** - Prometheus + Grafana for development insights
- **🧪 Local Testing** - MailHog for email testing, isolated database

## 🚀 Quick Setup

### Windows Users
```cmd
# Double-click or run:
setup-local.bat
```

### Unix/Linux/macOS Users
```bash
# Make executable and run:
chmod +x setup-local.sh
./setup-local.sh
```

### Manual Setup
```bash
# Run the Python script directly:
python setup-local-environment.py
```

## 🔧 What Gets Created

The setup script automatically creates:

1. **`.env`** - Main environment configuration with isolated ports
2. **`backend/.env`** - Backend-specific configuration
3. **`docker-compose.local-isolated.yml`** - Isolated container configuration
4. **`LOCAL_SETUP_GUIDE.md`** - Complete setup documentation with credentials

## 🌐 Isolated Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 18881 | Database with pgvector |
| Redis | 18882 | Caching and sessions |
| Backend API | 18883 | FastAPI server |
| Frontend | 18884 | Next.js application |
| Ollama (Container) | 18885 | AI model server (optional) |
| MailHog SMTP | 18886 | Email testing server |
| MailHog Web | 18887 | Email web interface |
| Prometheus | 18888 | Metrics collection |
| Grafana | 18889 | Monitoring dashboard |

## 🤖 Ollama Integration

### Using Your Local Ollama (Recommended)
- **Backend automatically detects** your local Ollama on port 11434
- **Uses existing models** you already have installed
- **No container needed** for Ollama
- **Faster startup** and better performance

### Using Containerized Ollama (Optional)
- **Profile-based startup** - only starts when needed
- **GPU support** with NVIDIA drivers
- **Isolated environment** for testing different models
- **Start with**: `--profile ollama-container`

## 🔐 Security Features

- **Random passwords** generated for each service
- **Localhost binding** - no external access
- **Isolated network** - separate from other Docker projects
- **Secure defaults** - production-ready security settings

## 📊 Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   PostgreSQL    │
│  (Port 18884)   │◄──►│   (Port 18883)  │◄──►│   (Port 18881)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Redis       │    │    Monitoring   │
                       │   (Port 18882)  │    │  (Port 18888/89)│
                       └─────────────────┘    └─────────────────┘
```

## 🚀 Starting Services

### Start All Services (Recommended)
```bash
docker-compose -f docker-compose.local-isolated.yml up -d
```

### Start Without Ollama (Use Local)
```bash
docker-compose -f docker-compose.local-isolated.yml up -d
# Ollama container won't start (uses your local installation)
```

### Start With Containerized Ollama
```bash
docker-compose -f docker-compose.local-isolated.yml --profile ollama-container up -d
```

## 📋 Service Management

### Check Status
```bash
docker-compose -f docker-compose.local-isolated.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.local-isolated.yml logs -f

# Specific service
docker-compose -f docker-compose.local-isolated.yml logs -f backend
```

### Stop Services
```bash
docker-compose -f docker-compose.local-isolated.yml down
```

### Clean Slate (WARNING: Deletes all data!)
```bash
docker-compose -f docker-compose.local-isolated.yml down -v
docker volume prune -f
```

## 🗄️ Database Setup

The PostgreSQL container automatically:

1. **Creates the `suna` database**
2. **Runs initialization scripts** from `./database/init/`
3. **Applies migrations** from `./backend/database/migrations/`
4. **Enables pgvector extension** for AI embeddings

### Manual Database Access
```bash
# Connect to PostgreSQL
psql -h localhost -p 18881 -U suna -d suna

# Connect to Redis
redis-cli -h localhost -p 18882 -a <generated_password> ping
```

## 📊 Monitoring & Observability

### Grafana Dashboard
- **URL**: http://localhost:18889
- **Username**: admin
- **Password**: Generated automatically (see LOCAL_SETUP_GUIDE.md)

### Prometheus Metrics
- **URL**: http://localhost:18888
- **Targets**: Backend, PostgreSQL, Redis health metrics

### MailHog Email Testing
- **Web Interface**: http://localhost:18887
- **SMTP Server**: localhost:18886

## 🔧 Development Workflow

### 1. Initial Setup
```bash
# Run setup script
./setup-local.sh

# Review generated credentials
cat LOCAL_SETUP_GUIDE.md
```

### 2. Start Development Environment
```bash
# Start all services
docker-compose -f docker-compose.local-isolated.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.local-isolated.yml ps
```

### 3. Access Applications
- **Frontend**: http://localhost:18884
- **Backend API**: http://localhost:18883
- **Admin Login**: admin@localhost / <generated_password>

### 4. Development
- **Code changes** automatically reload (volume mounts)
- **Database migrations** run automatically
- **Logs** available in real-time
- **Monitoring** shows service health

## 🆘 Troubleshooting

### Port Conflicts
```bash
# Check what's using a port
netstat -an | findstr :18881  # Windows
lsof -i :18881                # Linux/macOS
```

### Service Health Issues
```bash
# Check service status
docker-compose -f docker-compose.local-isolated.yml ps

# View service logs
docker-compose -f docker-compose.local-isolated.yml logs <service_name>
```

### Database Connection Issues
```bash
# Test PostgreSQL
psql -h localhost -p 18881 -U suna -d suna

# Test Redis
redis-cli -h localhost -p 18882 -a <password> ping
```

### Ollama Integration Issues
```bash
# Check if local Ollama is running
curl http://localhost:11434/api/tags

# Test containerized Ollama
curl http://localhost:18885/api/tags
```

## 🔄 Updating Services

### Rebuild After Code Changes
```bash
# Rebuild specific service
docker-compose -f docker-compose.local-isolated.yml build backend

# Restart service
docker-compose -f docker-compose.local-isolated.yml restart backend
```

### Update Dependencies
```bash
# Rebuild all services
docker-compose -f docker-compose.local-isolated.yml build --no-cache

# Restart all services
docker-compose -f docker-compose.local-isolated.yml up -d --force-recreate
```

## 📝 Environment Variables

Key environment variables you can customize:

```bash
# Database
POSTGRES_PASSWORD=<generated>
DATABASE_URL=postgresql://suna:<password>@localhost:18881/suna

# Redis
REDIS_HOST=localhost
REDIS_PORT=18882
REDIS_PASSWORD=<generated>

# Ollama
OLLAMA_BASE_URL=http://localhost:11434  # Your local installation
OLLAMA_CONTAINER_URL=http://localhost:18885  # Container fallback

# CORS
CORS_ORIGINS=["http://localhost:18884", "http://127.0.0.1:18884"]
```

## 🎯 Best Practices

### For Development
- **Use local Ollama** when available (faster, more models)
- **Monitor service health** with Grafana dashboard
- **Check logs** regularly for debugging
- **Use MailHog** for testing email functionality

### For Testing
- **Isolated containers** prevent conflicts with other projects
- **Random passwords** ensure security in shared environments
- **Volume mounts** preserve data between restarts
- **Health checks** ensure services are ready

### For Production Preparation
- **Review security settings** before deployment
- **Change default passwords** for production use
- **Configure external monitoring** and alerting
- **Set up proper backup** and recovery procedures

## 📚 Additional Resources

- **`LOCAL_SETUP_GUIDE.md`** - Complete setup documentation with credentials
- **`docker-compose.local-isolated.yml`** - Container configuration
- **`setup-local-environment.py`** - Setup script source code
- **`./database/init/`** - Database initialization scripts
- **`./monitoring/`** - Prometheus and Grafana configuration

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `docker-compose -f docker-compose.local-isolated.yml logs -f`
2. **Verify service health**: `docker-compose -f docker-compose.local-isolated.yml ps`
3. **Review setup guide**: Check `LOCAL_SETUP_GUIDE.md` for credentials
4. **Check port conflicts**: Ensure no other services use ports 18881-18889
5. **Verify Ollama**: Ensure local Ollama is running on port 11434

---

**🎉 Welcome to Zippy Suna Local Development!**

This setup gives you a fully isolated, secure, and feature-rich development environment that won't interfere with your existing development tools and services.


