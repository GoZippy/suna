# Technology Stack

## Backend (Python)

- **Framework**: FastAPI with Uvicorn
- **Package Manager**: uv (modern Python package manager)
- **Database**: PostgreSQL with pgvector extension
- **ORM**: SQLAlchemy with asyncpg
- **Cache/Queue**: Redis with Dramatiq for background jobs
- **Authentication**: JWT with Supabase Auth
- **LLM Integration**: LiteLLM (supports OpenAI, Anthropic, OpenRouter, Gemini)
- **Agent Execution**: Daytona SDK for sandboxed environments
- **Web Scraping**: Tavily, Firecrawl APIs
- **Monitoring**: Prometheus, Sentry, Langfuse

## Frontend (TypeScript/React)

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: Zustand, TanStack Query
- **Authentication**: Supabase Auth with SSR
- **Forms**: React Hook Form with Zod validation
- **Code Editor**: CodeMirror
- **Charts**: Recharts, Altair

## Infrastructure

- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose
- **Database**: PostgreSQL 16 with pgvector
- **Cache**: Redis 8 Alpine
- **Reverse Proxy**: Nginx (production)
- **Process Management**: Supervisor (sandbox containers)

## Development Tools

- **Python**: pytest, black, mypy for testing and code quality
- **Node.js**: ESLint, Prettier for code formatting
- **Git**: Conventional commits preferred
- **IDE**: VS Code configurations included

## Common Commands

### Backend Development
```bash
# Start backend services
cd backend
docker compose up --build

# Run API locally (with Redis in Docker)
uv run api.py

# Run background worker
uv run dramatiq --processes 4 --threads 4 run_agent_background

# Run tests
uv run pytest
```

### Frontend Development
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start
```

### Full Stack Development
```bash
# Complete setup wizard
python setup.py

# Start all services
python start.py

# Start database only
./start-database.sh  # or start-database.bat on Windows
```

### Docker Operations
```bash
# Build and start all services
docker compose up --build

# Start specific services
docker compose up redis api worker

# View logs
docker compose logs -f api

# Clean rebuild
docker compose down && docker compose up --build
```

## Environment Configuration

- **Backend**: `.env` file with API keys and database config
- **Frontend**: `.env.local` file with public environment variables
- **Setup**: Use `python setup.py` for guided configuration
- **Development**: Redis host should be `localhost` when running API locally, `redis` when in Docker

## Build System

- **Python**: uv for dependency management and virtual environments
- **Node.js**: npm for package management
- **Docker**: Multi-stage builds for optimized production images
- **CI/CD**: GitHub Actions workflows for testing and deployment