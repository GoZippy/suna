# Product Overview

Kortix is an open-source platform for building, managing, and training autonomous AI agents. The flagship product is Suna, a generalist AI worker that demonstrates the platform's capabilities.

## Core Product Features

- **Agent Platform**: Complete infrastructure for creating custom AI agents
- **Suna AI Worker**: Flagship generalist agent for research, automation, and workflows
- **Browser Automation**: Web navigation, data extraction, form filling
- **File Management**: Document creation, editing, organization across formats
- **System Operations**: Command-line execution, DevOps tasks, system administration
- **API Integrations**: Connect with external services and automate workflows
- **Agent Builder**: Visual tools for configuring and deploying agents

## Target Use Cases

- **Research & Analysis**: Web research, document analysis, market intelligence
- **Content Creation**: Marketing copy, documentation, educational materials
- **Customer Service**: Support tickets, FAQ responses, user onboarding
- **Sales & Marketing**: Lead qualification, CRM management, outreach campaigns
- **Industry-Specific**: Healthcare, finance, legal, education applications

## Architecture

Four-component platform:
1. **Backend API** (Python/FastAPI) - Agent orchestration and LLM integration
2. **Frontend Dashboard** (Next.js/React) - Management interface and chat
3. **Agent Runtime** (Docker) - Isolated execution environments
4. **Database & Storage** (Supabase/PostgreSQL) - Data persistence and auth

## Deployment Options

- **Cloud Hosted**: Managed service at suna.so
- **Self-Hosted**: Complete setup wizard for local deployment
- **Docker Compose**: Containerized deployment for development/production