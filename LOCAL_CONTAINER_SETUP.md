# Local Container Orchestration Setup

This guide explains how to set up and use the local Docker-based container orchestration system that replaces Daytona functionality.

## Overview

The local container orchestration system provides:

- **Docker-based sandbox management** - Replace Daytona with local Docker containers
- **Secure container isolation** - Network segmentation and resource limits
- **VNC server integration** - GUI access to sandbox containers via web browser
- **File system operations** - Upload, download, and manage files within containers
- **Health monitoring** - Automatic container health checks and restart capabilities
- **Resource management** - CPU, memory, and disk limits per container

## Prerequisites

1. **Docker and Docker Compose** installed on your system
2. **Docker daemon running** with API access
3. **Sufficient system resources** (recommended: 8GB RAM, 4 CPU cores)
4. **Port availability** for container services (15900-16900 range)

## Quick Start

### 1. Enable Local Container Mode

Set the environment variable to enable local containers:

```bash
# In your .env file or environment
USE_LOCAL_CONTAINERS=true
```

### 2. Build the Sandbox Image

First, build the agent sandbox image:

```bash
cd backend/sandbox/docker
docker compose build
docker tag kortix/suna:0.1.3.4 suna/agent-sandbox:latest
```

### 3. Start the System

Use the provided Docker Compose configuration:

```bash
# Start all services including local container orchestration
docker-compose -f docker-compose.local-containers.yml up -d

# Or start just the core services
docker-compose -f docker-compose.local-containers.yml up -d postgres redis backend
```

### 4. Verify Setup

Check that the container manager is working:

```bash
# Check system health
curl http://localhost:8000/system/health

# List running containers (should be empty initially)
curl http://localhost:8000/sandboxes
```

## Configuration

### Environment Variables

Key configuration options for local containers:

```bash
# Enable local container orchestration
USE_LOCAL_CONTAINERS=true

# Container image to use for sandboxes
LOCAL_CONTAINER_IMAGE=suna/agent-sandbox:latest

# Network name for sandbox isolation
LOCAL_CONTAINER_NETWORK=suna_sandbox_network

# Port range for container services
LOCAL_CONTAINER_PORT_RANGE_START=15900
LOCAL_CONTAINER_PORT_RANGE_END=16900

# Database configuration
DATABASE_URL=postgresql://suna_user:suna_password@localhost:5432/suna

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=suna_redis_password
REDIS_SSL=false
```

### Resource Limits

Default resource limits per container:

- **CPU**: 2 cores
- **Memory**: 4GB
- **Disk**: 10GB
- **Shared Memory**: 2GB

These can be customized when creating containers via the API.

## API Usage

### Create a Sandbox

```bash
curl -X POST http://localhost:8000/sandboxes \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project-123",
    "vnc_password": "mypassword",
    "cpu_limit": 2.0,
    "memory_limit": "4g"
  }'
```

### Get Sandbox Information

```bash
curl http://localhost:8000/sandboxes/my-project-123
```

### Access VNC Interface

The response includes `vnc_url` which you can open in a web browser to access the sandbox GUI.

### File Operations

```bash
# List files
curl "http://localhost:8000/sandboxes/my-project-123/files?path=/workspace"

# Upload a file
curl -X POST http://localhost:8000/sandboxes/my-project-123/files \
  -F "path=/workspace/test.txt" \
  -F "file=@local-file.txt"

# Download a file
curl "http://localhost:8000/sandboxes/my-project-123/files/content?path=/workspace/test.txt"

# Delete a file
curl -X DELETE "http://localhost:8000/sandboxes/my-project-123/files?path=/workspace/test.txt"
```

### Container Lifecycle

```bash
# Start a stopped container
curl -X POST http://localhost:8000/sandboxes/my-project-123/start

# Stop a running container
curl -X POST http://localhost:8000/sandboxes/my-project-123/stop

# Restart a container
curl -X POST http://localhost:8000/sandboxes/my-project-123/restart

# Delete a container
curl -X DELETE http://localhost:8000/sandboxes/my-project-123
```

## Monitoring and Health Checks

### System Health

```bash
# Overall system health
curl http://localhost:8000/system/health

# Specific container health
curl http://localhost:8000/sandboxes/my-project-123/health
```

### Prometheus Metrics

If you're running the monitoring stack:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

### Container Logs

```bash
# View container manager logs
docker logs suna_backend

# View specific sandbox container logs
docker logs suna_sandbox_my-project-123
```

## Troubleshooting

### Common Issues

1. **Docker Permission Denied**
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER
   # Restart shell or logout/login
   ```

2. **Port Conflicts**
   ```bash
   # Check if ports are in use
   netstat -tulpn | grep :15900
   # Adjust port range in configuration
   ```

3. **Container Creation Fails**
   ```bash
   # Check Docker daemon status
   docker info
   # Check available resources
   docker system df
   ```

4. **VNC Access Issues**
   ```bash
   # Check if VNC server is running in container
   docker exec suna_sandbox_my-project-123 nc -z localhost 5901
   ```

### Debug Mode

Enable debug logging:

```bash
# Set log level in environment
LOG_LEVEL=DEBUG

# Or in Docker Compose
environment:
  - LOG_LEVEL=DEBUG
```

### Container Cleanup

```bash
# Clean up stopped containers
docker container prune

# Clean up unused volumes
docker volume prune

# Clean up unused networks
docker network prune
```

## Security Considerations

### Network Isolation

- Sandbox containers run in isolated network (`suna_sandbox_network`)
- Inter-container communication disabled by default
- Only necessary ports exposed to host

### Resource Limits

- CPU and memory limits prevent resource exhaustion
- Disk quotas prevent storage abuse
- Automatic cleanup of old containers

### File System Security

- Path validation prevents directory traversal
- File operations restricted to workspace directory
- Secure file upload/download with validation

### Container Security

- Non-root user execution where possible
- Security profiles and capabilities restrictions
- Regular base image updates recommended

## Migration from Daytona

To migrate from Daytona to local containers:

1. **Set environment variable**: `USE_LOCAL_CONTAINERS=true`
2. **Update configuration**: Remove Daytona-specific settings
3. **Build sandbox image**: Use provided Dockerfile
4. **Test functionality**: Verify all features work as expected
5. **Monitor performance**: Check resource usage and adjust limits

The system provides the same API interface, so existing code should work without changes.

## Performance Tuning

### Container Resources

Adjust based on your workload:

```python
# In container creation request
{
    "cpu_limit": 4.0,      # More CPU for compute-intensive tasks
    "memory_limit": "8g",   # More memory for large applications
    "disk_limit": "20g"     # More disk for file-heavy operations
}
```

### System Resources

Monitor and adjust system resources:

```bash
# Check Docker resource usage
docker stats

# Check system resources
htop
df -h
```

### Scaling

For high-load scenarios:

1. **Increase port range** for more concurrent containers
2. **Add more worker nodes** (future enhancement)
3. **Use external storage** for better I/O performance
4. **Optimize container images** for faster startup

## Development

### Building Custom Sandbox Images

```bash
cd backend/sandbox/docker

# Modify Dockerfile as needed
vim Dockerfile

# Build new image
docker build -t suna/agent-sandbox:custom .

# Update configuration
LOCAL_CONTAINER_IMAGE=suna/agent-sandbox:custom
```

### Adding New Features

The container orchestration system is modular:

- **LocalContainerManager**: Core container lifecycle management
- **ContainerFileSystem**: File operations within containers
- **LocalSandboxAPI**: REST API endpoints
- **PortManager**: Port allocation and management

### Testing

```bash
# Run unit tests
cd backend
python -m pytest tests/test_container_manager.py

# Integration tests
python -m pytest tests/test_local_sandbox_integration.py
```

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify Docker daemon is running and accessible
3. Ensure sufficient system resources
4. Check network connectivity and port availability
5. Review security settings and permissions

The local container orchestration system provides a robust, self-hosted alternative to external sandbox services while maintaining security and performance.