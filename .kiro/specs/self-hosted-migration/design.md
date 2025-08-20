# Design Document

## Overview

This design document outlines the architecture for migrating Suna from a third-party service dependent platform to a fully self-hosted, open-source solution. The migration will replace Supabase, Daytona, Stripe, and other external services with local alternatives while maintaining all existing functionality and improving deployment flexibility on Proxmox infrastructure.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Nginx/Traefik Load Balancer]
    end
    
    subgraph "Application Layer"
        FE[Next.js Frontend]
        BE[FastAPI Backend]
        WK[Dramatiq Workers]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL + pgvector)]
        RD[(Redis)]
        FS[Local File Storage]
    end
    
    subgraph "Container Orchestration"
        DM[Docker Manager]
        SB1[Agent Sandbox 1]
        SB2[Agent Sandbox 2]
        SBN[Agent Sandbox N]
    end
    
    subgraph "AI/ML Services"
        LLM[Local LLM Server<br/>Ollama/vLLM]
        EMB[Embedding Service<br/>sentence-transformers]
    end
    
    subgraph "Supporting Services"
        SM[SMTP Server]
        MQ[Message Queue<br/>Redis/RabbitMQ]
        MON[Monitoring<br/>Prometheus/Grafana]
    end
    
    LB --> FE
    LB --> BE
    BE --> PG
    BE --> RD
    BE --> FS
    BE --> DM
    WK --> PG
    WK --> RD
    WK --> MQ
    DM --> SB1
    DM --> SB2
    DM --> SBN
    BE --> LLM
    BE --> EMB
    BE --> SM
```

### Component Replacement Strategy

| Current Service | Replacement | Implementation |
|----------------|-------------|----------------|
| Supabase Database | PostgreSQL + pgvector | Local PostgreSQL with vector extension |
| Supabase Auth | Custom JWT Auth | FastAPI-based authentication |
| Supabase Storage | Local File System | Docker volume-based file storage |
| Supabase Realtime | WebSocket Server | FastAPI WebSocket endpoints |
| Daytona Sandbox | Docker Containers | Local Docker container management |
| Stripe Billing | Local User Management | Role-based access control |
| Tavily Search | Local Search Engine | Elasticsearch or SearXNG |
| Firecrawl | Local Web Scraping | Playwright + BeautifulSoup |
| Redis (Upstash) | Local Redis | Redis container |
| Email Services | Local SMTP | Postfix/MailHog |

## Components and Interfaces

### 1. Database Layer

#### PostgreSQL with pgvector
- **Purpose**: Replace Supabase database functionality
- **Components**:
  - PostgreSQL 16+ with pgvector extension
  - TimescaleDB extension for time-series data
  - Custom migration scripts from Supabase schema
- **Configuration**:
  ```yaml
  postgresql:
    version: "16"
    extensions:
      - pgvector
      - timescaledb
      - uuid-ossp
    max_connections: 200
    shared_buffers: "256MB"
    effective_cache_size: "1GB"
  ```

#### Vector Database Integration
- **Primary**: pgvector for PostgreSQL integration
- **Alternative**: Qdrant for dedicated vector operations
- **Features**:
  - Embedding storage and similarity search
  - Hybrid search (text + vector)
  - Metadata filtering
  - Batch operations

### 2. Authentication and Authorization

#### Custom JWT Authentication Service
- **Components**:
  - User registration and login endpoints
  - JWT token generation and validation
  - Password hashing with bcrypt
  - Role-based access control (RBAC)
- **Database Schema**:
  ```sql
  CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  
  CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```

### 3. Container Orchestration

#### Docker-based Sandbox Management
- **Purpose**: Replace Daytona sandbox functionality
- **Components**:
  - Docker API integration
  - Container lifecycle management
  - Resource isolation and limits
  - VNC server for GUI access
- **Implementation**:
  ```python
  class LocalSandboxManager:
      def __init__(self):
          self.docker_client = docker.from_env()
      
      async def create_sandbox(self, project_id: str) -> Container:
          container = self.docker_client.containers.run(
              image="suna/agent-sandbox:latest",
              detach=True,
              mem_limit="2g",
              cpu_count=2,
              network_mode="bridge",
              volumes={
                  f"sandbox_{project_id}": {"bind": "/workspace", "mode": "rw"}
              }
          )
          return container
  ```

#### Sandbox Image Configuration
- **Base Image**: Ubuntu 22.04 LTS
- **Installed Tools**:
  - Python 3.11+ with common packages
  - Node.js 20+ with npm/yarn
  - Git, curl, wget, vim
  - Browser automation tools (Playwright)
  - VNC server (TigerVNC)
  - Supervisor for process management

### 4. Search and Web Scraping

#### Local Search Engine
- **Primary Option**: SearXNG (privacy-focused metasearch)
- **Alternative**: Elasticsearch with web crawler
- **Features**:
  - Multiple search engine aggregation
  - Result caching and deduplication
  - Rate limiting and proxy support

#### Web Scraping Service
- **Components**:
  - Playwright for browser automation
  - BeautifulSoup for HTML parsing
  - Scrapy for large-scale scraping
  - Proxy rotation and rate limiting
- **API Interface**:
  ```python
  class LocalScrapingService:
      async def scrape_url(self, url: str, options: dict) -> dict:
          async with async_playwright() as p:
              browser = await p.chromium.launch()
              page = await browser.new_page()
              await page.goto(url)
              content = await page.content()
              await browser.close()
              return {"content": content, "url": url}
  ```

### 5. AI/ML Services

#### Local LLM Integration
- **Primary**: Ollama for easy model management
- **Alternative**: vLLM for high-performance inference
- **Supported Models**:
  - Llama 3.1/3.2 (8B, 70B)
  - Mistral 7B/22B
  - CodeLlama for code generation
  - Embedding models (all-MiniLM-L6-v2)

#### Model Management
```yaml
ollama_config:
  models:
    - name: "llama3.1:8b"
      pull_on_start: true
    - name: "codellama:7b"
      pull_on_start: false
  gpu_layers: 35
  context_length: 4096
```

### 6. File Storage and Management

#### Local File Storage
- **Implementation**: Docker volumes with organized directory structure
- **Features**:
  - Project-based file organization
  - Version control integration
  - Backup and restore capabilities
- **Directory Structure**:
  ```
  /data/
  ├── projects/
  │   ├── {project_id}/
  │   │   ├── files/
  │   │   ├── uploads/
  │   │   └── backups/
  ├── users/
  │   └── {user_id}/
  └── system/
      ├── logs/
      └── config/
  ```

### 7. Real-time Communication

#### WebSocket Server
- **Implementation**: FastAPI WebSocket endpoints
- **Features**:
  - Real-time agent status updates
  - Live chat functionality
  - File system change notifications
- **Connection Management**:
  ```python
  class WebSocketManager:
      def __init__(self):
          self.active_connections: Dict[str, WebSocket] = {}
      
      async def connect(self, websocket: WebSocket, user_id: str):
          await websocket.accept()
          self.active_connections[user_id] = websocket
      
      async def broadcast_to_user(self, user_id: str, message: dict):
          if user_id in self.active_connections:
              await self.active_connections[user_id].send_json(message)
  ```

## Data Models

### Core Database Schema

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects (replacing Supabase projects)
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sandbox_config JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Threads and Messages
CREATE TABLE threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(thread_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector Storage for Knowledge Base
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage Tracking (replacing Stripe billing)
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10,4) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Local User Tiers
CREATE TABLE user_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    max_monthly_usage DECIMAL(10,2),
    max_concurrent_agents INTEGER,
    features JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Error Handling

### Database Connection Resilience
- Connection pooling with automatic retry
- Graceful degradation when database is unavailable
- Transaction rollback and recovery mechanisms

### Container Management Error Handling
- Automatic container restart on failure
- Resource cleanup on container termination
- Fallback to alternative container images

### Service Discovery and Health Checks
- Health check endpoints for all services
- Automatic service registration and deregistration
- Circuit breaker pattern for external dependencies

## Testing Strategy

### Unit Testing
- Database layer testing with test containers
- API endpoint testing with FastAPI TestClient
- Container management testing with Docker test environments

### Integration Testing
- End-to-end workflow testing
- Multi-service interaction testing
- Performance testing under load

### Migration Testing
- Data migration validation scripts
- Schema compatibility testing
- Rollback procedure testing

### Deployment Testing
- Docker Compose deployment validation
- Kubernetes deployment testing (optional)
- Proxmox VM/LXC deployment verification

## Security Considerations

### Authentication Security
- JWT token expiration and refresh mechanisms
- Password strength requirements and hashing
- Rate limiting on authentication endpoints
- Session management and invalidation

### Container Security
- Non-root user execution in containers
- Resource limits and isolation
- Network segmentation between services
- Regular security updates for base images

### Data Protection
- Encryption at rest for sensitive data
- TLS/SSL for all network communications
- Input validation and sanitization
- SQL injection prevention

### Access Control
- Role-based permissions system
- API key management for service-to-service communication
- Audit logging for administrative actions
- Principle of least privilege

## Performance Optimization

### Database Performance
- Proper indexing strategy for frequent queries
- Connection pooling and query optimization
- Vector index optimization for similarity searches
- Partitioning for large tables

### Container Performance
- Resource allocation optimization
- Container image size minimization
- Efficient container startup and shutdown
- Shared volume optimization

### Caching Strategy
- Redis caching for frequently accessed data
- Application-level caching for expensive operations
- CDN-like caching for static assets
- Query result caching

## Monitoring and Observability

### Metrics Collection
- Prometheus metrics for all services
- Custom business metrics (usage, performance)
- Container resource utilization
- Database performance metrics

### Logging Strategy
- Structured logging with JSON format
- Centralized log aggregation
- Log retention and rotation policies
- Error tracking and alerting

### Health Monitoring
- Service health checks and status pages
- Automated alerting for service failures
- Performance threshold monitoring
- Capacity planning metrics

## Deployment Architecture

### Development Environment
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: suna_dev
      POSTGRES_USER: suna
      POSTGRES_PASSWORD: dev_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://suna:dev_password@postgres:5432/suna_dev
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

### Production Deployment on Proxmox

#### VM/LXC Distribution Strategy
1. **Database VM**: PostgreSQL + Redis + Monitoring
2. **Application VM**: Backend + Frontend + Workers
3. **AI/ML VM**: Ollama + Embedding services (GPU-enabled)
4. **Sandbox VM**: Docker containers for agent execution
5. **Load Balancer VM**: Nginx/Traefik + SSL termination

#### Resource Allocation
- **Database VM**: 8GB RAM, 4 vCPU, 100GB SSD
- **Application VM**: 16GB RAM, 8 vCPU, 50GB SSD
- **AI/ML VM**: 32GB RAM, 16 vCPU, 200GB SSD, GPU passthrough
- **Sandbox VM**: 32GB RAM, 16 vCPU, 500GB SSD
- **Load Balancer VM**: 4GB RAM, 2 vCPU, 20GB SSD

#### Network Configuration
- Internal network for service communication
- External network for user access
- Isolated network for sandbox containers
- VPN access for administrative tasks