# Zippy Suna Smart Startup System

The Smart Startup System intelligently detects existing local services and only starts the containers you actually need. This gives you the flexibility to use your existing PostgreSQL, Redis, or Ollama installations while still getting the benefits of containerized Zippy Suna services.

## 🎯 How It Works

### 1. **Service Detection**
The system automatically detects:
- **Local PostgreSQL** instances (ports 5432, 5433, 5434, 5435)
- **Local Redis** instances (ports 6379, 6380, 6381, 6382)  
- **Local Ollama** instances (port 11434)
- **Existing project containers** (already running Zippy Suna services)

### 2. **Smart Configuration**
Based on what it finds, the system:
- **Recommends** the best service to use (local vs container)
- **Asks for your preference** when multiple options exist
- **Creates optimized** docker-compose files with only needed services
- **Updates environment** variables to point to the correct services

### 3. **Intelligent Startup**
- Only starts containers for services you don't have locally
- Automatically configures networking and dependencies
- Provides clear access information for all services

## 🚀 Quick Start

### Windows Users
```cmd
# Double-click or run:
start-zippy.bat
```

### Unix/Linux/macOS Users
```bash
# Make executable and run:
chmod +x start-zippy.sh
./start-zippy.sh
```

### Manual Python Execution
```bash
# Install dependencies first:
pip install -r requirements-startup.txt

# Run the script:
python start-zippy.py
```

## 🔍 What Gets Detected

### PostgreSQL Detection
- Checks common ports: 5432, 5433, 5434, 5435
- Attempts connection with default credentials
- Reports connection URL if successful

### Redis Detection  
- Checks common ports: 6379, 6380, 6381, 6382
- Tests connection with PING command
- Reports connection URL if successful

### Ollama Detection
- Checks port 11434 (default Ollama port)
- Tests API endpoint `/api/tags`
- Reports connection URL if successful

### Project Container Detection
- Scans for running containers with "suna" or "zippy" in the name
- Identifies which project services are already running
- Prevents duplicate service startup

## ⚙️ Configuration Options

### Service Preferences
When local services are detected, you can choose:

```
POSTGRESQL:
  Local service found at: localhost:5432
  Project container: Not running
  Use local service? (y/n) [default: y]: y

REDIS:
  Local service found at: localhost:6379
  Project container: Not running  
  Use local service? (y/n) [default: y]: y

OLLAMA:
  Local service found at: localhost:11434
  Project container: Not running
  Use local service? (y/n) [default: y]: y
```

### Automatic Recommendations
The system automatically recommends:
- **Local services** when they're available and working
- **Container services** when local alternatives aren't found
- **Container services** for core Zippy Suna components (backend, frontend, worker)

## 📁 Generated Files

### Smart Compose File
- **Location**: `docker-compose.smart.yml`
- **Purpose**: Contains only the services you need
- **Usage**: `docker-compose -f docker-compose.smart.yml up -d`

### Environment Files
- **Main**: `.env` (project root)
- **Backend**: `backend/.env`
- **Purpose**: Configured for your chosen service mix

## 🌐 Access Information

After startup, you'll see access details like:

```
🌐 Access Information:
========================================
Frontend: http://localhost:18884
Backend API: http://localhost:18883
Monitoring: http://localhost:18888 (Prometheus)
Grafana: http://localhost:18889
MailHog: http://localhost:18887

📚 Next Steps:
1. Wait for all services to be healthy
2. Access the frontend at http://localhost:18884
3. Check logs: docker-compose -f docker-compose.smart.yml logs -f
4. Stop services: docker-compose -f docker-compose.smart.yml down
```

## 🔧 Advanced Configuration

### Custom Port Detection
To add more ports for service detection, edit `start-zippy.py`:

```python
def check_local_postgres(self) -> Tuple[bool, str]:
    ports = [5432, 5433, 5434, 5435, 5436, 5437]  # Add more ports
```

### Service Health Checks
The system includes health checks for all services:
- **Database**: Connection test with timeout
- **Redis**: PING command test
- **Ollama**: HTTP API endpoint test
- **Containers**: Docker API status check

### Environment Variable Overrides
You can override any detected settings by editing the generated `.env` files before starting services.

## 🚨 Troubleshooting

### Common Issues

#### Python Dependencies
```bash
# If you get import errors:
pip install -r requirements-startup.txt

# Or install individually:
pip install docker psycopg2-binary redis requests
```

#### Docker Connection
```bash
# If Docker isn't responding:
docker info
# Make sure Docker Desktop is running
```

#### Port Conflicts
```bash
# Check what's using a port:
netstat -an | findstr :5432  # Windows
lsof -i :5432                # Unix/Linux/macOS
```

#### Service Connection Issues
```bash
# Test PostgreSQL:
psql -h localhost -p 5432 -U postgres

# Test Redis:
redis-cli -h localhost -p 6379 ping

# Test Ollama:
curl http://localhost:11434/api/tags
```

### Debug Mode
For detailed debugging, edit `start-zippy.py` and add:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📋 Service Matrix

| Service | Local Detection | Container Option | Required |
|---------|----------------|------------------|----------|
| PostgreSQL | ✅ Port scan + connection test | ✅ Container with pgvector | ✅ Yes |
| Redis | ✅ Port scan + PING test | ✅ Container with persistence | ✅ Yes |
| Ollama | ✅ Port scan + API test | ✅ Container with GPU support | ✅ Yes |
| Backend | ❌ Always containerized | ✅ FastAPI + dependencies | ✅ Yes |
| Frontend | ❌ Always containerized | ✅ Next.js + build tools | ✅ Yes |
| Worker | ❌ Always containerized | ✅ Background job processor | ✅ Yes |
| Monitoring | ❌ Always containerized | ✅ Prometheus + Grafana | ❌ Optional |

## 🎉 Benefits

### For Developers
- **No port conflicts** with existing services
- **Faster startup** (only needed containers)
- **Flexible configuration** (mix local + container)
- **Clear visibility** into what's running where

### For Production
- **Resource optimization** (no duplicate services)
- **Service isolation** (project containers separate)
- **Health monitoring** (built-in checks)
- **Easy scaling** (add/remove services as needed)

### For Testing
- **Local development** with existing databases
- **Container testing** without affecting system services
- **Quick iteration** (smart rebuilds)
- **Clean shutdown** (project-specific cleanup)

## 🔄 Updating Services

### Adding New Services
1. Add service definition to `docker-compose.self-hosted.yml`
2. Update detection logic in `ServiceDetector` class
3. Add preference handling in `SmartStartup` class

### Modifying Detection Logic
1. Edit the appropriate `check_local_*` method
2. Update port ranges or connection tests
3. Modify recommendation logic if needed

### Environment Variable Mapping
1. Update `update_environment_config` method
2. Add new variable replacements
3. Test with different service combinations

## 📞 Support

If you encounter issues:

1. **Check the logs**: `docker-compose -f docker-compose.smart.yml logs -f`
2. **Verify services**: Run the startup script again to re-detect
3. **Manual override**: Edit `.env` files and restart manually
4. **Clean restart**: `docker-compose -f docker-compose.smart.yml down && docker system prune -f`

The Smart Startup System makes Zippy Suna deployment intelligent, efficient, and user-friendly while maintaining the flexibility to work with your existing infrastructure!


