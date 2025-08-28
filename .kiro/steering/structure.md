# Project Structure

## Root Directory

```
├── backend/           # Python FastAPI backend
├── frontend/          # Next.js React frontend
├── database/          # PostgreSQL setup and migrations
├── sandbox/           # Docker agent execution environment
├── sdk/               # Python SDK for Kortix platform
├── services/          # Additional microservices
├── docs/              # Documentation
├── monitoring/        # Prometheus configuration
├── .kiro/             # Kiro IDE configuration and steering
├── docker-compose.yaml # Main orchestration file
├── setup.py           # Interactive setup wizard
└── start.py           # Service startup script
```

## Backend Structure (`backend/`)

```
├── api.py                    # FastAPI application entry point
├── pyproject.toml           # Python dependencies (uv)
├── docker-compose.yml       # Backend-specific services
├── Dockerfile               # Backend container build
├── agent/                   # Core agent logic
├── agentpress/             # Agent management system
├── database/               # Database models and connections
├── services/               # Business logic services
├── utils/                  # Shared utilities
├── triggers/               # Event triggers and webhooks
├── mcp_module/             # Model Context Protocol integration
├── knowledge_base/         # Vector database and embeddings
├── composio_integration/   # External tool integrations
├── credentials/            # Secure credential management
├── flags/                  # Feature flag system
├── templates/              # Email and notification templates
└── supabase/              # Supabase client and migrations
```

## Frontend Structure (`frontend/`)

```
├── package.json            # Node.js dependencies
├── next.config.ts         # Next.js configuration
├── tailwind.config.js     # Tailwind CSS configuration
├── components.json        # shadcn/ui configuration
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # Reusable React components
│   ├── lib/             # Utility functions and configurations
│   ├── hooks/           # Custom React hooks
│   ├── stores/          # Zustand state management
│   └── types/           # TypeScript type definitions
└── public/              # Static assets
```

## Database Structure (`database/`)

```
├── README.md              # Database setup instructions
├── docker-compose.db.yml  # Database services
├── config/               # PostgreSQL and Redis configurations
├── init/                 # Database initialization scripts
├── scripts/              # Migration and utility scripts
└── test_connection.py    # Connection testing utility
```

## Sandbox Structure (`sandbox/`)

```
├── Dockerfile            # Agent execution environment
├── docker-compose.yml    # Sandbox orchestration
├── supervisord.conf      # Process management
├── container_manager.py  # Container lifecycle management
├── find_ports.py        # Port availability checker
├── build.sh / build.ps1 # Build scripts
└── healthcheck.sh       # Container health monitoring
```

## Configuration Files

### Environment Files
- `backend/.env` - Backend API keys and database config
- `frontend/.env.local` - Frontend public environment variables
- `.env.example` - Template for environment setup

### Docker Files
- `docker-compose.yaml` - Main orchestration (all services)
- `docker-compose.local.yml` - Local development
- `docker-compose.db.yml` - Database-only services
- `backend/docker-compose.yml` - Backend services only

### Setup Files
- `setup.py` - Interactive configuration wizard
- `start.py` - Service startup automation
- `start-database.sh/.bat` - Database startup scripts

## Key Conventions

### File Naming
- Python: `snake_case` for files and functions
- TypeScript: `camelCase` for variables, `PascalCase` for components
- Configuration: `kebab-case` for Docker and config files

### Directory Organization
- **Separation of Concerns**: Clear boundaries between backend, frontend, database
- **Feature-Based**: Group related functionality together
- **Configuration Centralization**: Environment and Docker configs at appropriate levels
- **Documentation Co-location**: README files in each major directory

### Import Patterns
- **Backend**: Relative imports within modules, absolute for cross-module
- **Frontend**: Absolute imports using `@/` alias for src directory
- **Shared**: Common utilities in dedicated directories

### Development Workflow
1. Use `python setup.py` for initial configuration
2. Backend development: `cd backend && docker compose up redis` + local API
3. Frontend development: `npm run dev` in frontend directory
4. Full stack: `python start.py` or `docker compose up --build`
5. Database only: `./start-database.sh` or equivalent batch file

### Testing Structure
- **Backend**: `test_*.py` files alongside source code
- **Frontend**: `*.test.ts` files in `__tests__` directories
- **Integration**: End-to-end tests in dedicated test directories